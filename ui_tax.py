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
from config import REALTY_PRICE_API_ENDPOINT_DEFAULT
from formatting import format_bn_krw, format_pct_from_100
from api_manager import get_api_key, sanitize_secret_dataframe, sanitize_secret_text
from ui_common import compact_fig


def render_tax_mode(asset_risk: pd.DataFrame, scenario: dict, latest_kpi: pd.Series, assumptions: dict | None = None):
    st.markdown("## T. Tax: 보유세 분석")
    st.caption(
        "이 화면은 리츠 보유자산의 공시가격/기준시가, 토지·건물 시가표준액, 과세표준, 재산세, "
        "도시지역분, 지방교육세를 연결해 보유세 부담과 FFO 현금 유출 영향을 예비 분석합니다."
    )
    assumptions = assumptions or {}

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

    st.write("**공시가격·기준시가 데이터 연결**")
    st.caption("실제 API endpoint와 파라미터는 활용승인 받은 서비스별로 다를 수 있습니다. 승인받은 endpoint와 파라미터 템플릿을 입력하거나, CSV 업로드로 안정적으로 테스트할 수 있습니다.")

    default_template = '{"format":"json", "pnu":"{pnu}", "stdrYear":"{year}", "pageNo":"1", "numOfRows":"50"}'
    if "realty_price_api_key" not in st.session_state:
        st.session_state["realty_price_api_key"] = ""
    realty_conn = assumptions.get("realty_conn") or get_api_key("V-World", st.session_state.get("realty_price_api_key", ""))
    if not realty_conn.configured:
        st.warning("실시간 API Key가 없어 예시 데이터를 사용합니다.")
    with st.form("realty_price_api_form", clear_on_submit=True):
        c1, c2 = st.columns([0.95, 1.05])
        with c1:
            endpoint = st.text_input("공시가격 API endpoint", value=st.session_state.get("realty_price_endpoint", REALTY_PRICE_API_ENDPOINT_DEFAULT), placeholder="예: 활용승인 받은 공시가격/개별공시지가 조회 endpoint")
            selected_api_asset = st.selectbox("API 테스트 자산", asset_risk["asset_name"].tolist(), index=0)
            selected_row = asset_risk[asset_risk["asset_name"] == selected_api_asset].iloc[0]
            pnu_or_code = st.text_input("PNU/법정동코드/물건식별자", value=st.session_state.get("realty_price_pnu_or_code", ""), help="승인받은 API가 PNU, 법정동코드, 주소검색 키 등을 요구하면 입력하세요.")
        with c2:
            param_template = st.text_area("API 파라미터 템플릿(JSON)", value=st.session_state.get("realty_price_param_template", default_template), height=135)
            fetch_api = st.form_submit_button("선택 자산 공시가격 5년치 API 불러오기", width="stretch")
    uploaded_price_csv = st.file_uploader("공시가격/기준시가 CSV 업로드", type=["csv"], key="official_price_csv_upload")

    current_year = datetime.today().year
    start_year = current_year - 4
    api_price_history = st.session_state.get("realty_price_api_history", pd.DataFrame())
    api_status = sanitize_secret_text(st.session_state.get("realty_price_api_status", "API 미사용"))
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

    if uploaded_price_history is not None and not uploaded_price_history.empty:
        official_price_history = uploaded_price_history
        price_data_status = "CSV 업로드 공시가격/기준시가 사용"
    elif api_price_history is not None and not api_price_history.empty:
        official_price_history = api_price_history
        price_data_status = f"API 데이터 사용: {api_status}"
    else:
        if realty_conn.configured:
            st.warning("실시간 API 호출이 실패했거나 응답 데이터가 부족해 예시 데이터를 사용합니다.")
        official_price_history = build_proxy_official_price_history(
            asset_risk,
            years_back=5,
            latest_year=current_year,
            annual_land_growth_pct=assumptions.get("proxy_land_growth_pct", 3.0),
            official_to_appraisal_ratio_pct=assumptions.get("official_to_appraisal_ratio_pct", 55.0),
            building_standard_ratio_pct=assumptions.get("building_standard_ratio_pct", 20.0),
        )
        price_data_status = "공시가격 API/CSV 미연결: 평가액 기반 추정치(proxy) 사용 중"

    official_price_history = sanitize_secret_dataframe(official_price_history)

    if "land_area_sqm" in official_price_history.columns:
        # Uploaded area can override asset master only if present.
        pass

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
    annual_summary = summarize_holding_tax_history(tax_history)

    st.info(sanitize_secret_text(price_data_status))
    if tax_history is None or tax_history.empty:
        st.warning("보유세 계산에 필요한 공시가격/기준시가 데이터가 부족합니다. API endpoint, 파라미터, CSV 컬럼을 확인하세요.")
        return

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
    m4.metric("자료 기준", "API/CSV" if "proxy" not in price_data_status else "추정치(proxy)")

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
        fig_asset_tax = px.bar(
            latest_asset_tax.head(8),
            x="보유세_추정_백만원",
            y="asset_name",
            orientation="h",
            title=f"{latest_year}E 자산별 보유세",
            text="보유세_추정_백만원",
        )
        fig_asset_tax.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
        st.plotly_chart(compact_fig(fig_asset_tax, 260), width="stretch")

    cash_flow_scenarios = build_property_tax_cash_flow_scenarios(
        latest_kpi,
        annual_summary,
        scenario,
        assumptions.get("tax_ffo_annualization_factor", 4.0),
    )
    tax_workflow = build_reit_tax_workflow_checklist(latest_kpi, annual_summary, cash_flow_scenarios, price_data_status)
    tax_risk_register = build_tax_risk_register(tax_history, annual_summary, cash_flow_scenarios, price_data_status)
    tax_automation_backlog = build_tax_automation_backlog()

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
        "건물_시가표준액_백만원", "재산세본세_백만원", "도시지역분_백만원", "지방교육세_백만원", "보유세_추정_백만원", "보유세_5년누적증가_%", "official_price_source"
    ]].rename(columns={
        "asset_name": "자산",
        "location": "주소/권역",
        "official_land_price_per_sqm_krw": "개별공시지가_원_m2",
        "official_price_source": "공시가격_자료출처",
    })

    tab_cash, tab_workflow, tab_detail, tab_data = st.tabs(
        ["FFO 현금유출 스트레스", "세무업무 자동화", "보유세 상세 분석", "원천 데이터"]
    )

    with tab_cash:
        st.write("**보유세 인상 시나리오별 FFO·배당 여력**")
        st.caption(
            "최신 KPI의 FFO와 배당총액은 연환산 추정치(proxy)로 비교합니다. 실제 연간 예산이나 forecast가 있으면 별도 입력값으로 대체해야 합니다."
        )
        if cash_flow_scenarios.empty:
            st.warning("FFO 현금유출 시나리오를 계산할 수 없습니다. KPI와 보유세 요약 데이터를 확인하세요.")
        else:
            c1, c2 = st.columns([1.05, 0.95])
            with c1:
                st.dataframe(cash_flow_scenarios, width="stretch", hide_index=True, height=250)
            with c2:
                fig_cash = px.bar(
                    cash_flow_scenarios,
                    x="시나리오",
                    y="추가_현금유출_백만원",
                    color="판단",
                    title="보유세 인상 시 추가 현금유출",
                )
                st.plotly_chart(compact_fig(fig_cash, 250), width="stretch")

    with tab_workflow:
        st.write("**리츠 Tax 부서 업무 자동화 체크리스트**")
        disabled_cols = [col for col in tax_workflow.columns if col != "완료"]
        st.data_editor(
            tax_workflow,
            width="stretch",
            hide_index=True,
            height=360,
            disabled=disabled_cols,
            key="reit_tax_workflow_checklist",
        )

        st.write("**세무 리스크·환급기회 레지스터**")
        st.dataframe(tax_risk_register, width="stretch", hide_index=True, height=260)

        st.write("**Tax Technology 자동화 과제 목록**")
        st.dataframe(tax_automation_backlog, width="stretch", hide_index=True, height=240)

    with tab_detail:
        st.write("**연도별 보유세 증가 분석**")
        st.dataframe(annual_display, width="stretch", hide_index=True, height=190)

        st.write("**자산별 최신 보유세와 증가율**")
        st.dataframe(asset_display.head(12), width="stretch", hide_index=True, height=260)

    with tab_data:
        st.write("**공시가격/기준시가 원천 데이터**")
        st.dataframe(official_price_history, width="stretch", hide_index=True, height=260)
        st.caption("CSV 권장 컬럼: asset_name, year, official_land_price_per_sqm_krw, building_standard_value_mn_krw, land_area_sqm, source")

    st.warning(
        "본 보유세 계산은 신고 목적의 세액 산출이 아니라, 리츠 보유자산별 세금 부담의 방향성과 민감도를 파악하기 위한 예비 분석입니다. "
        "실제 고지세액은 과세대상 구분, 지자체 조례, 감면, 세부담상한, 건축물 시가표준액, 리츠별 보유 구조에 따라 달라질 수 있습니다."
    )
