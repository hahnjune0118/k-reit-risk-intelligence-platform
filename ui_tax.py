import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from api_real_estate_board import fetch_official_price_history_generic, parse_official_price_upload
from calculations_tax import (
    build_holding_tax_estimator,
    build_property_tax_cash_flow_scenarios,
    build_proxy_official_price_history,
    build_reit_tax_workflow_checklist,
    build_tax_automation_backlog,
    build_tax_risk_register,
    summarize_holding_tax_history,
)
from calculations_tax_review_pack import (
    build_ffo_cash_outflow_stress,
    build_holding_tax_reconciliation,
    build_source_detail,
    build_tax_automation_summary,
    build_tax_issue_matrix,
    build_tax_request_list,
    build_tax_review_memo,
)
from config import REALTY_PRICE_API_ENDPOINT_DEFAULT
from formatting import format_bn_krw, format_pct_from_100
from api_manager import get_api_key, sanitize_secret_dataframe, sanitize_secret_text
from tax_data_loader import build_company_tax_dataset, build_tax_history_from_company_tax_data, get_tax_source_status, get_tax_source_summary
from ui_common import compact_fig, render_data_scope_banner, render_selected_company_header
from ui_peer import build_peer_metric_table, flags_to_tax_review_table, render_overall_risk_message, style_risk_review_table


SHOW_DEVELOPER_API_INPUTS = os.getenv("SHOW_DEVELOPER_API_INPUTS", "false").lower() == "true"


def _render_tax_assumption_panel(assumptions: dict, scenario: dict) -> dict:
    st.markdown("### Tax 분석 가정")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            holding_tax_increase_pct = st.slider(
                "보유세 증가율 가정",
                min_value=0.0,
                max_value=50.0,
                value=float(assumptions.get("v13_holding_tax_increase_pct", 10.0)),
                step=2.5,
                key="v13_holding_tax_increase_pct",
                help="Tax Review Pack의 FFO 현금유출 스트레스에 사용하는 보유세 증가율입니다.",
            )
        with c2:
            default_ffo_stress = float(scenario.get("ffo_haircut_pct", 5.0) or 5.0)
            ffo_stress_pct = st.slider(
                "FFO 스트레스 가정",
                min_value=0.0,
                max_value=30.0,
                value=float(assumptions.get("v13_ffo_stress_pct", default_ffo_stress)),
                step=1.0,
                key="v13_ffo_stress_pct",
                help="보유세 증가와 동시에 FFO가 하락하는 경우의 현금 유출 부담을 검토합니다.",
            )
        with c3:
            sensitivity_pct = st.slider(
                "민감도 분석 기준",
                min_value=5.0,
                max_value=40.0,
                value=float(assumptions.get("v13_tax_sensitivity_pct", 20.0)),
                step=5.0,
                key="v13_tax_sensitivity_pct",
                help="요청자료와 검토 메모에서 주의가 필요한 변동률 기준으로 사용합니다.",
            )
        st.caption(
            "이 가정은 신고 목적 세액 계산이 아니라 보유세 부담의 방향성과 FFO 현금유출 민감도를 보기 위한 예비 분석 기준입니다. "
            f"토지 공정시장가액비율 {assumptions.get('land_fmv_ratio_pct', 70.0):.0f}% · "
            f"건축물 공정시장가액비율 {assumptions.get('building_fmv_ratio_pct', 70.0):.0f}% · "
            f"건축물 재산세율 추정치 {assumptions.get('building_tax_rate_pct', 0.25):.2f}%"
        )
    return {
        "holding_tax_increase_pct": holding_tax_increase_pct,
        "ffo_stress_pct": ffo_stress_pct,
        "sensitivity_pct": sensitivity_pct,
    }


def _render_peer_tax_section(peer_context: dict | None):
    if not peer_context:
        return
    flags = peer_context.get("tax_red_flags", [])
    peer_metrics = peer_context.get("peer_metrics", pd.DataFrame())
    target_company = peer_context.get("target_company", "선택 리츠")

    st.markdown("---")
    st.markdown("## Peer 기반 보유세 부담 분석")
    st.caption(
        "본 분석은 신고 목적의 세액 산출이 아닙니다. 리츠 보유자산별 세금 부담의 방향성과 "
        "민감도를 파악하기 위한 예비 분석입니다."
    )
    render_overall_risk_message("Tax 보유세 Red Flag", flags)

    metric_table = build_peer_metric_table(
        peer_metrics,
        target_company,
        {
            "holding_tax_to_ffo": "보유세/FFO",
            "holding_tax_to_operating_revenue": "보유세/영업수익",
            "official_price_to_investment_property": "공시가격/투자부동산",
            "dividend_to_ffo": "배당/FFO",
            "debt_to_assets": "차입금/총자산",
        },
    )

    review_table = flags_to_tax_review_table(flags)
    if review_table.empty:
        st.info("표시할 Tax Red Flag가 없습니다.")
    else:
        st.write("**Tax 검토사항 및 요청자료**")
        st.dataframe(
            style_risk_review_table(review_table),
            width="stretch",
            hide_index=True,
            height=300,
            column_config={
                "세무 위험영역": st.column_config.TextColumn("세무 위험영역", width="small"),
                "위험수준": st.column_config.TextColumn("위험수준", width="small"),
                "발생 근거": st.column_config.TextColumn("발생 근거", width="large"),
                "Tax 검토사항": st.column_config.TextColumn("Tax 검토사항", width="large"),
                "요청자료": st.column_config.TextColumn("요청자료", width="medium"),
                "관련 지표": st.column_config.TextColumn("관련 지표", width="small"),
            },
        )

    with st.expander("Peer 부담 비교 보기", expanded=False):
        if metric_table.empty:
            st.info("Peer 보유세 부담 비교를 만들 수 있는 데이터가 부족합니다.")
        else:
            st.dataframe(
                metric_table,
                width="stretch",
                hide_index=True,
                height=240,
                column_config={
                    "지표": st.column_config.TextColumn("지표", width="medium"),
                    "선택 리츠": st.column_config.TextColumn("선택 리츠", width="small"),
                    "Peer 중앙값": st.column_config.TextColumn("Peer 중앙값", width="small"),
                    "Peer 평균": st.column_config.TextColumn("Peer 평균", width="small"),
                    "Peer 위치": st.column_config.TextColumn("Peer 위치", width="small"),
                },
            )


def _render_tax_source_scope_banner(target_company: str, company_profile: dict, company_tax_data: pd.DataFrame):
    summary = get_tax_source_summary(target_company, company_tax_data)
    stock_code = company_profile.get("stock_code", "")
    company_label = f"{target_company} ({stock_code})" if stock_code else target_company
    latest_year = f"{summary['latest_year']}년" if summary["latest_year"] else "연도 미확인"

    with st.container(border=True):
        st.caption(f"현재 분석 대상: {company_label}")
        st.caption(f"분석 범위: {summary['scope_label']} / 데이터 기준: {latest_year}")
        st.caption(f"source_type: {summary['source_type']}")
        st.caption(f"source_note: {summary['source_note']}")


def render_tax_mode(
    asset_risk: pd.DataFrame,
    scenario: dict,
    latest_kpi: pd.Series,
    assumptions: dict | None = None,
    peer_context: dict | None = None,
):
    st.markdown("## T. Tax: 보유세 분석")
    render_selected_company_header(peer_context)
    render_data_scope_banner(peer_context)
    st.caption(
        "이 화면은 리츠 보유자산의 공시가격/기준시가, 토지·건물 시가표준액, 과세표준, 재산세, "
        "도시지역분, 지방교육세를 연결해 보유세 부담과 FFO 현금 유출 영향을 예비 분석합니다."
    )
    assumptions = assumptions or {}
    run_id = (peer_context or {}).get("analysis_run_id", 0)
    company_profile = (peer_context or {}).get("selected_company_profile", {}) or {}
    target_company = (peer_context or {}).get("target_company", company_profile.get("company_name", "선택 리츠"))
    peer_snapshot = (peer_context or {}).get("peer_snapshot", pd.DataFrame())
    peer_summary = (peer_context or {}).get("peer_summary", {})
    tax_flags = (peer_context or {}).get("tax_red_flags", [])
    company_tax_data = build_company_tax_dataset(target_company, peer_snapshot, company_profile)
    tax_source_status = get_tax_source_status(target_company, company_tax_data)
    _render_tax_source_scope_banner(target_company, company_profile, company_tax_data)
    tax_pack_assumptions = _render_tax_assumption_panel(assumptions, scenario)

    with st.expander("보유세 계산 산식, 과세표준, 세율 보기", expanded=False):
        st.markdown(
            """
            **이 화면의 기본 전제**
            보유 상업용 부동산은 일반적으로 토지분 재산세에서 **별도합산과세대상 토지**로 보는 것이 1차 추정치(proxy)입니다. 실제 세액은 자산별 용도, 면적기준, 지방자치단체 조례, 감면, 세부담상한, 건축물 시가표준액에 따라 달라질 수 있습니다.

            **1) 토지 시가표준액**
            `토지 시가표준액 = 1㎡당 개별공시지가 × 토지면적`  
            앱은 한국부동산원/부동산공시가격 계열 API 또는 CSV 업로드의 개별공시지가를 우선 사용합니다.

            **2) 토지 과세표준**
            `토지 과세표준 = 토지 시가표준액 × 공정시장가액비율`  
            기본값은 토지·건축물 70%입니다. 필요하면 좌측 사이드바에서 조정합니다.

            **3) 별도합산 토지분 재산세 본세**  
            - 과세표준 2억원 이하: `과세표준 × 0.2%`  
            - 2억원 초과 10억원 이하: `400,000원 + 2억원 초과분 × 0.3%`  
            - 10억원 초과: `2,800,000원 + 10억원 초과분 × 0.4%`

            **4) 건축물분 재산세 본세**  
            `건축물 과세표준 = 건물 기준시가 또는 시가표준액 × 공정시장가액비율`  
            `건축물분 재산세 = 건축물 과세표준 × 건축물 세율`  
            기본 세율은 일반 건축물 추정치(proxy) 0.25%로 두되, 실제 용도에 따라 조정해야 합니다.

            **5) 도시지역분과 지방교육세**  
            `도시지역분 = 과세표준 × 0.14%`  
            `지방교육세 = 재산세 본세 × 20%`

            **6) 세부담상한**  
            선택 시 직전연도 보유세 추정액의 일정 비율을 초과하지 않도록 단순 cap을 적용합니다. 실제 적용은 자산별 과세구분과 지자체 고지 구조에 따라 달라질 수 있습니다.
            """
        )

    st.write("**공시가격·기준시가 데이터**")
    realty_conn = assumptions.get("realty_conn") or get_api_key("V-World")
    if realty_conn.configured:
        st.success("공시가격 데이터 연결 준비 완료")
    else:
        st.warning("공시가격 실시간 조회가 제한되어 예시 데이터를 사용합니다.")
    st.caption("공개 리뷰 버전은 서버 측 데이터 연결 또는 내장 예시 데이터를 사용합니다. 사용자가 별도의 인증값을 입력할 필요는 없습니다.")

    has_detailed_asset_data = asset_risk is not None and not asset_risk.empty
    if not has_detailed_asset_data:
        st.warning(
            "이 회사는 자산별 상세 공시가격 데이터가 제한되어 회사 전체 Snapshot 기반 추정값을 사용합니다. "
            "해당 추정값은 신고 목적 세액이 아니라 Tax Review Pack 생성을 위한 예비 분석 입력값입니다."
        )

    fetch_api = False
    endpoint = ""
    param_template = ""
    pnu_or_code = ""
    selected_api_asset = asset_risk["asset_name"].iloc[0] if has_detailed_asset_data else ""
    selected_row = asset_risk[asset_risk["asset_name"] == selected_api_asset].iloc[0] if has_detailed_asset_data else pd.Series(dtype="object")
    if SHOW_DEVELOPER_API_INPUTS and has_detailed_asset_data:
        default_template = '{"format":"json", "pnu":"{pnu}", "stdrYear":"{year}", "pageNo":"1", "numOfRows":"50"}'
        with st.expander("개발자용 공시가격 API 테스트", expanded=False):
            st.caption("로컬 개발 환경에서만 사용하는 기술 설정입니다. 공개 배포 기본값에서는 표시되지 않습니다.")
            with st.form("realty_price_api_form", clear_on_submit=True):
                c1, c2 = st.columns([0.95, 1.05])
                with c1:
                    endpoint = st.text_input("공시가격 API endpoint", value=st.session_state.get("realty_price_endpoint", REALTY_PRICE_API_ENDPOINT_DEFAULT), placeholder="활용승인 받은 조회 endpoint")
                    selected_api_asset = st.selectbox("API 테스트 자산", asset_risk["asset_name"].tolist(), index=0)
                    selected_row = asset_risk[asset_risk["asset_name"] == selected_api_asset].iloc[0]
                    pnu_or_code = st.text_input("PNU/법정동코드/물건식별자", value=st.session_state.get("realty_price_pnu_or_code", ""))
                with c2:
                    param_template = st.text_area("API 파라미터 템플릿(JSON)", value=st.session_state.get("realty_price_param_template", default_template), height=135)
                    fetch_api = st.form_submit_button("선택 자산 공시가격 5년치 불러오기", width="stretch")
    uploaded_price_csv = None
    if has_detailed_asset_data:
        with st.expander("선택: 공시가격/기준시가 CSV 업로드", expanded=False):
            uploaded_price_csv = st.file_uploader("공시가격/기준시가 CSV 업로드", type=["csv"], key="official_price_csv_upload")

    current_year = datetime.today().year
    start_year = current_year - 4
    api_price_history = st.session_state.get("realty_price_api_history", pd.DataFrame())
    api_status = sanitize_secret_text(st.session_state.get("realty_price_api_status", "실시간 조회 미사용"))
    if fetch_api:
        st.session_state["realty_price_endpoint"] = endpoint.strip()
        st.session_state["realty_price_param_template"] = param_template
        st.session_state["realty_price_pnu_or_code"] = pnu_or_code.strip()
        api_price_history, api_status = fetch_official_price_history_generic(
            realty_conn.key, endpoint.strip(), param_template,
            selected_api_asset, str(selected_row.get("location", "")), pnu_or_code.strip(), start_year, current_year
        )
        st.session_state["realty_price_api_history"] = api_price_history
        st.session_state["realty_price_api_status"] = api_status

    uploaded_price_history, upload_status = parse_official_price_upload(uploaded_price_csv) if uploaded_price_csv is not None else (pd.DataFrame(), "업로드 없음")

    if not has_detailed_asset_data:
        official_price_history = pd.DataFrame()
        tax_history = build_tax_history_from_company_tax_data(company_tax_data, years_back=5, default_latest_year=current_year)
        price_data_status = tax_source_status
    elif uploaded_price_history is not None and not uploaded_price_history.empty:
        official_price_history = uploaded_price_history
        price_data_status = "CSV 업로드 공시가격/기준시가 사용"
    elif api_price_history is not None and not api_price_history.empty:
        official_price_history = api_price_history
        price_data_status = f"공시가격 실시간 조회 데이터 사용: {api_status}"
    else:
        if fetch_api:
            st.warning("공시가격 실시간 조회 결과가 부족해 예시 데이터를 사용합니다.")
        elif not realty_conn.configured:
            st.warning("공시가격 실시간 조회가 제한되어 예시 데이터를 사용합니다.")
        official_price_history = build_proxy_official_price_history(
            asset_risk,
            years_back=5,
            latest_year=current_year,
            annual_land_growth_pct=assumptions.get("proxy_land_growth_pct", 3.0),
            official_to_appraisal_ratio_pct=assumptions.get("official_to_appraisal_ratio_pct", 55.0),
            building_standard_ratio_pct=assumptions.get("building_standard_ratio_pct", 20.0),
        )
        price_data_status = "공시가격 예시 데이터 사용: 평가액 기반 추정치(proxy) 적용"

    official_price_history = sanitize_secret_dataframe(official_price_history)

    if "land_area_sqm" in official_price_history.columns:
        # Uploaded area can override asset master only if present.
        pass

    if has_detailed_asset_data:
        tax_history = build_holding_tax_estimator(
            asset_risk,
            official_price_history,
            land_fmv_ratio_pct=assumptions.get("land_fmv_ratio_pct", 70.0),
            building_fmv_ratio_pct=assumptions.get("building_fmv_ratio_pct", 70.0),
            building_tax_rate_pct=assumptions.get("building_tax_rate_pct", 0.25),
            include_urban_area_tax=assumptions.get("include_urban_area_tax", True),
            include_local_education_tax=assumptions.get("include_local_education_tax", True),
            apply_tax_burden_cap=assumptions.get("apply_tax_burden_cap", False),
            tax_burden_cap_pct=assumptions.get("tax_burden_cap_pct", 150.0),
        )
    st.session_state["selected_company_tax_data"] = tax_history.copy()
    annual_summary = summarize_holding_tax_history(tax_history)

    st.info(sanitize_secret_text(price_data_status))
    if tax_history is None or tax_history.empty:
        st.warning("보유세 계산에 필요한 공시가격/기준시가 데이터가 부족합니다. 예시 데이터 또는 업로드 CSV의 자료 구조를 확인하세요.")
        return

    st.markdown("### Tax Summary")
    latest_year = int(tax_history["year"].max())
    first_year = int(tax_history["year"].min())
    latest_total_tax = annual_summary.loc[annual_summary["year"] == latest_year, "보유세_추정_백만원"].iloc[0]
    first_total_tax = annual_summary.loc[annual_summary["year"] == first_year, "보유세_추정_백만원"].iloc[0]
    cumulative_increase = (latest_total_tax / first_total_tax - 1) * 100 if first_total_tax else pd.NA
    latest_tax_base = annual_summary.loc[annual_summary["year"] == latest_year, "토지_과세표준_백만원"].iloc[0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"{latest_year}E 보유세", format_bn_krw(latest_total_tax))
    m2.metric("5년 누적 증가율", format_pct_from_100(cumulative_increase))
    m3.metric("토지 과세표준", format_bn_krw(latest_tax_base))
    estimated_basis = any(keyword in price_data_status for keyword in ["estimate", "추정", "Snapshot", "proxy"])
    m4.metric("자료 기준", "추정치/Snapshot" if estimated_basis else "실시간/CSV")

    left, right = st.columns([1.15, 0.85])
    with left:
        fig_tax_trend = px.line(
            annual_summary,
            x="year",
            y="보유세_추정_백만원",
            markers=True,
            title="최근 5년 보유세 추정액 추이",
        )
        st.plotly_chart(compact_fig(fig_tax_trend, 260), width="stretch")
    with right:
        latest_asset_tax = tax_history[tax_history["year"] == latest_year].copy().sort_values("보유세_추정_백만원", ascending=False)
        tax_chart_title = f"{latest_year}E 자산별 보유세" if has_detailed_asset_data else f"{latest_year}E 회사 전체 보유세 추정"
        fig_asset_tax = px.bar(
            latest_asset_tax.head(8),
            x="보유세_추정_백만원",
            y="asset_name",
            orientation="h",
            title=tax_chart_title,
            text="보유세_추정_백만원",
        )
        fig_asset_tax.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
        st.plotly_chart(compact_fig(fig_asset_tax, 260), width="stretch")
        if not has_detailed_asset_data:
            st.caption("자산별 상세자료가 제한된 회사는 회사 전체 추정 row를 사용합니다.")

    _render_peer_tax_section(peer_context)

    cash_flow_scenarios = build_property_tax_cash_flow_scenarios(
        latest_kpi,
        annual_summary,
        scenario,
        assumptions.get("tax_ffo_annualization_factor", 4.0),
    )
    tax_workflow = build_reit_tax_workflow_checklist(latest_kpi, annual_summary, cash_flow_scenarios, price_data_status)
    tax_risk_register = build_tax_risk_register(tax_history, annual_summary, cash_flow_scenarios, price_data_status)
    tax_automation_backlog = build_tax_automation_backlog()
    reconciliation = build_holding_tax_reconciliation(tax_history, latest_kpi)
    ffo_pack_stress = build_ffo_cash_outflow_stress(
        latest_kpi,
        annual_summary,
        tax_pack_assumptions["holding_tax_increase_pct"],
        tax_pack_assumptions["ffo_stress_pct"],
    )
    issue_matrix = build_tax_issue_matrix(tax_flags, reconciliation, ffo_pack_stress, price_data_status)
    request_list = build_tax_request_list(issue_matrix)
    automation_summary = build_tax_automation_summary(issue_matrix, request_list, reconciliation)
    memo_text = build_tax_review_memo(company_profile, price_data_status, issue_matrix, reconciliation, request_list, ffo_pack_stress, peer_summary)

    annual_display = annual_summary.copy().rename(columns={
        "year": "연도",
        "보유세_추정_백만원": "보유세_추정_백만원",
        "토지_시가표준액_백만원": "토지_시가표준액_백만원",
        "토지_과세표준_백만원": "토지_과세표준_백만원",
        "재산세본세_백만원": "재산세본세_백만원",
        "도시지역분_백만원": "도시지역분_백만원",
        "지방교육세_백만원": "지방교육세_백만원",
        "전년대비증가율_%": "보유세_전년대비_%",
        "누적증가율_%": "보유세_누적증가_%",
    })
    asset_display = latest_asset_tax[[
        "asset_name", "location", "official_land_price_per_sqm_krw", "토지_시가표준액_백만원", "토지_과세표준_백만원",
        "건물_시가표준액_백만원", "재산세본세_백만원", "도시지역분_백만원", "지방교육세_백만원", "보유세_추정_백만원", "보유세_5년누적증가_%"
    ]].rename(columns={
        "asset_name": "자산",
        "location": "주소/권역",
        "official_land_price_per_sqm_krw": "개별공시지가_원_m2",
    })
    source_detail = build_source_detail(tax_history)

    st.markdown("---")
    with st.expander("Tax 데이터 기준 보기", expanded=False):
        st.caption("Tax Review Pack에서 사용한 데이터 범위와 추정 근거입니다.")
        st.dataframe(
            source_detail,
            width="stretch",
            hide_index=True,
            height=180,
            column_config={
                "자산명": st.column_config.TextColumn("자산명", width="medium"),
                "기준연도": st.column_config.TextColumn("연도", width="small"),
                "source_type": st.column_config.TextColumn("source_type", width="small"),
                "source_note": st.column_config.TextColumn("source_note", width="large"),
                "식별자/주소": st.column_config.TextColumn("식별자/주소", width="medium"),
                "비고": st.column_config.TextColumn("비고", width="medium"),
            },
        )

    st.markdown("## Tax Issue Matrix")
    st.caption("Tax Red Flag, 보유세 정합성, FFO 현금유출 스트레스 결과를 실무 검토 항목으로 변환합니다.")
    st.dataframe(
        style_risk_review_table(issue_matrix),
        width="stretch",
        hide_index=True,
        height=310,
        column_config={
            "세무 이슈": st.column_config.TextColumn("세무 이슈", width="medium"),
            "위험수준": st.column_config.TextColumn("위험", width="small"),
            "발생 근거": st.column_config.TextColumn("발생 근거", width="large"),
            "영향받는 지표": st.column_config.TextColumn("영향 지표", width="small"),
            "검토 방향": st.column_config.TextColumn("검토 방향", width="large"),
            "요청자료": st.column_config.TextColumn("요청자료", width="large"),
            "업무유형": st.column_config.TextColumn("업무유형", width="small"),
            "데이터 기준": st.column_config.TextColumn("데이터 기준", width="small"),
        },
    )

    st.markdown("## 보유세 정합성 검토")
    st.caption("회계상 투자부동산 장부가액과 공시가격·과세표준·추정 보유세를 연결한 예비 대사표입니다.")
    st.dataframe(
        reconciliation,
        width="stretch",
        hide_index=True,
        height=230,
        column_config={
            "자산명": st.column_config.TextColumn("자산명", width="medium"),
            "지역": st.column_config.TextColumn("지역", width="small"),
            "장부가액(억원)": st.column_config.NumberColumn("장부가액", width="small", format="%.1f"),
            "공시가격(억원)": st.column_config.NumberColumn("공시가격", width="small", format="%.1f"),
            "공시가격 / 장부가액": st.column_config.NumberColumn("공시/장부", width="small", format="%.1%"),
            "추정 과세표준(억원)": st.column_config.NumberColumn("추정 과표", width="small", format="%.1f"),
            "추정 보유세(억원)": st.column_config.NumberColumn("추정 보유세", width="small", format="%.1f"),
            "보유세 / FFO": st.column_config.NumberColumn("보유세/FFO", width="small", format="%.1%"),
            "최근 5년 공시가격 증가율": st.column_config.NumberColumn("5년 증가", width="small", format="%.1%"),
            "검토 필요 여부": st.column_config.TextColumn("검토", width="small"),
        },
    )
    with st.expander("공시가격 자료 출처 보기", expanded=False):
        st.dataframe(
            source_detail,
            width="stretch",
            hide_index=True,
            height=180,
            column_config={
                "자산명": st.column_config.TextColumn("자산명", width="medium"),
                "기준연도": st.column_config.TextColumn("연도", width="small"),
                "source_type": st.column_config.TextColumn("source_type", width="small"),
                "source_note": st.column_config.TextColumn("source_note", width="large"),
                "식별자/주소": st.column_config.TextColumn("식별자/주소", width="medium"),
                "비고": st.column_config.TextColumn("비고", width="medium"),
            },
        )

    st.markdown("## 요청자료 리스트")
    st.dataframe(
        request_list,
        width="stretch",
        hide_index=True,
        height=260,
        column_config={
            "요청자료": st.column_config.TextColumn("요청자료", width="medium"),
            "요청 목적": st.column_config.TextColumn("요청 목적", width="large"),
            "관련 이슈": st.column_config.TextColumn("관련 이슈", width="medium"),
            "우선순위": st.column_config.TextColumn("우선", width="small"),
            "비고": st.column_config.TextColumn("비고", width="large"),
        },
    )

    tab_cash, tab_workflow, tab_detail, tab_memo, tab_data = st.tabs(
        ["FFO 현금유출 스트레스", "세무업무 자동화", "보유세 상세 분석", "Tax Review Memo 초안", "원천 데이터"]
    )

    with tab_cash:
        st.write("**FFO 현금유출 스트레스**")
        st.caption(
            "선택 회사의 FFO와 추정 보유세를 사용해 보유세 증가와 FFO 하락이 동시에 발생하는 경우를 검토합니다."
        )
        if ffo_pack_stress.empty:
            st.warning("FFO 현금유출 시나리오를 계산할 수 없습니다. KPI와 보유세 요약 데이터를 확인하세요.")
        else:
            c1, c2 = st.columns([1.05, 0.95])
            with c1:
                st.dataframe(
                    ffo_pack_stress,
                    width="stretch",
                    hide_index=True,
                    height=250,
                    column_config={
                        "항목": st.column_config.TextColumn("항목", width="small"),
                        "금액(억원)": st.column_config.NumberColumn("금액", width="small", format="%.1f"),
                        "FFO 대비": st.column_config.NumberColumn("FFO 대비", width="small", format="%.1%"),
                        "주요 해석": st.column_config.TextColumn("주요 해석", width="large"),
                    },
                )
            with c2:
                fig_cash = px.bar(
                    ffo_pack_stress,
                    x="항목",
                    y="금액(억원)",
                    title="보유세 스트레스 금액",
                )
                st.plotly_chart(compact_fig(fig_cash, 250), width="stretch")
            with st.expander("기존 보유세 인상 시나리오별 FFO·배당 여력 보기", expanded=False):
                st.dataframe(cash_flow_scenarios, width="stretch", hide_index=True, height=240)

    with tab_workflow:
        st.write("**v13 Tax Review Pack 자동화 요약**")
        st.dataframe(
            automation_summary,
            width="stretch",
            hide_index=True,
            height=170,
            column_config={
                "항목": st.column_config.TextColumn("항목", width="medium"),
                "상태": st.column_config.TextColumn("상태", width="small"),
                "비고": st.column_config.TextColumn("비고", width="large"),
            },
        )
        st.write("**리츠 Tax 부서 업무 자동화 체크리스트**")
        disabled_cols = [col for col in tax_workflow.columns if col != "완료"]
        st.data_editor(
            tax_workflow,
            width="stretch",
            hide_index=True,
            height=360,
            disabled=disabled_cols,
            key=f"reit_tax_workflow_checklist_{run_id}",
            column_config={
                "완료": st.column_config.CheckboxColumn("완료", width="small"),
                "업무영역": st.column_config.TextColumn("업무영역", width="small"),
                "우선순위": st.column_config.TextColumn("우선", width="small"),
                "자동화 툴": st.column_config.TextColumn("자동화 툴", width="medium"),
                "리츠 실무 체크": st.column_config.TextColumn("리츠 실무 체크", width="large"),
                "데이터 입력": st.column_config.TextColumn("데이터 입력", width="medium"),
                "자동 산출물": st.column_config.TextColumn("자동 산출물", width="medium"),
            },
        )

        st.write("**세무 리스크·환급기회 레지스터**")
        st.dataframe(
            tax_risk_register,
            width="stretch",
            hide_index=True,
            height=260,
            column_config={
                "리스크/기회": st.column_config.TextColumn("리스크/기회", width="medium"),
                "등급": st.column_config.TextColumn("등급", width="small"),
                "신호": st.column_config.TextColumn("신호", width="medium"),
                "영향": st.column_config.TextColumn("영향", width="large"),
                "권장 자동화": st.column_config.TextColumn("권장 자동화", width="large"),
            },
        )

        st.write("**Tax Technology 자동화 과제 목록**")
        st.dataframe(
            tax_automation_backlog,
            width="stretch",
            hide_index=True,
            height=240,
            column_config={
                "순서": st.column_config.TextColumn("순서", width="small"),
                "자동화 과제": st.column_config.TextColumn("자동화 과제", width="medium"),
                "구현 내용": st.column_config.TextColumn("구현 내용", width="large"),
                "기대효과": st.column_config.TextColumn("기대효과", width="large"),
            },
        )

    with tab_detail:
        st.write("**연도별 보유세 증가 분석**")
        st.dataframe(
            annual_display,
            width="stretch",
            hide_index=True,
            height=190,
            column_config={
                "연도": st.column_config.TextColumn("연도", width="small"),
                "보유세_전년대비_%": st.column_config.NumberColumn("전년대비", width="small", format="%.1f%%"),
                "보유세_누적증가_%": st.column_config.NumberColumn("누적증가", width="small", format="%.1f%%"),
            },
        )

        st.write("**자산별 최신 보유세와 증가율**")
        st.dataframe(
            asset_display.head(12),
            width="stretch",
            hide_index=True,
            height=260,
            column_config={
                "자산": st.column_config.TextColumn("자산", width="medium"),
                "주소/권역": st.column_config.TextColumn("주소/권역", width="small"),
                "개별공시지가_원_m2": st.column_config.NumberColumn("공시지가", width="small", format="%.0f"),
                "토지_시가표준액_백만원": st.column_config.NumberColumn("토지 시가표준액", width="small", format="%.0f"),
                "토지_과세표준_백만원": st.column_config.NumberColumn("토지 과표", width="small", format="%.0f"),
                "건물_시가표준액_백만원": st.column_config.NumberColumn("건물 시가표준액", width="small", format="%.0f"),
                "재산세본세_백만원": st.column_config.NumberColumn("재산세", width="small", format="%.1f"),
                "도시지역분_백만원": st.column_config.NumberColumn("도시지역분", width="small", format="%.1f"),
                "지방교육세_백만원": st.column_config.NumberColumn("지방교육세", width="small", format="%.1f"),
                "보유세_추정_백만원": st.column_config.NumberColumn("추정 보유세", width="small", format="%.1f"),
                "보유세_5년누적증가_%": st.column_config.NumberColumn("5년 증가", width="small", format="%.1f%%"),
            },
        )
        with st.expander("공시가격 자료 출처 보기", expanded=False):
            st.dataframe(
                source_detail,
                width="stretch",
                hide_index=True,
                height=180,
                column_config={
                    "자산명": st.column_config.TextColumn("자산명", width="medium"),
                    "기준연도": st.column_config.TextColumn("연도", width="small"),
                    "source_type": st.column_config.TextColumn("source_type", width="small"),
                    "source_note": st.column_config.TextColumn("source_note", width="large"),
                    "식별자/주소": st.column_config.TextColumn("식별자/주소", width="medium"),
                    "비고": st.column_config.TextColumn("비고", width="medium"),
                },
            )

    with tab_memo:
        st.write("**Tax Review Memo 초안**")
        st.markdown(memo_text)
        safe_company = str(target_company).replace(" ", "_").replace("/", "_")
        st.download_button(
            "Tax Review Memo 다운로드",
            data=memo_text.encode("utf-8-sig"),
            file_name=f"tax_review_memo_{safe_company}.md",
            mime="text/markdown",
            width="stretch",
        )

    with tab_data:
        source_summary = get_tax_source_summary(target_company, company_tax_data)
        st.caption(
            f"source_type: {source_summary['source_type']} / "
            f"source_note: {source_summary['source_note']}"
        )
        st.write("**공시가격/기준시가 원천 데이터**")
        if has_detailed_asset_data and official_price_history is not None and not official_price_history.empty:
            st.dataframe(official_price_history, width="stretch", hide_index=True, height=260)
            st.caption("CSV 권장 컬럼: asset_name, year, official_land_price_per_sqm_krw, building_standard_value_mn_krw, land_area_sqm, source")
        else:
            st.dataframe(company_tax_data, width="stretch", hide_index=True, height=220)
            st.caption("자산별 상세자료가 제한된 회사는 회사 전체 Snapshot 기반 예시 추정값을 표시합니다.")

    st.warning(
        "본 보유세 계산은 신고 목적의 세액 산출이 아니라, 리츠 보유자산별 세금 부담의 방향성과 민감도를 파악하기 위한 예비 분석입니다. "
        "실제 고지세액은 과세대상 구분, 지자체 조례, 감면, 세부담상한, 건축물 시가표준액, 리츠별 보유 구조에 따라 달라질 수 있습니다."
    )
