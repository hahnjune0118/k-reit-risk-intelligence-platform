from io import BytesIO
import zipfile

import pandas as pd
import plotly.express as px
import streamlit as st

from calculations_holding_tax_bridge import build_holding_tax_bridge
from calculations_tax import summarize_holding_tax_history
from calculations_tax_review_pack import (
    build_ffo_cash_outflow_stress,
    build_holding_tax_reconciliation,
    build_source_detail,
    build_tax_automation_summary,
    build_tax_issue_matrix,
    build_tax_request_list,
    build_tax_review_memo,
)
from data_source_policy import get_source_policy
from formatting import format_bn_krw, format_pct_from_100
from tax_data_loader import build_company_tax_dataset, build_tax_history_from_company_tax_data, get_tax_source_status, get_tax_source_summary
from tax_validation import validate_tax_inputs
from ui_common import compact_fig, render_data_scope_banner, render_selected_company_header
from ui_peer import build_peer_metric_table, render_overall_risk_message, style_risk_review_table


def _to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def _safe_filename(value: str) -> str:
    return str(value).replace(" ", "_").replace("/", "_").replace("\\", "_")


def _zip_review_pack(company_name: str, memo_text: str, issue_matrix: pd.DataFrame, reconciliation: pd.DataFrame, request_list: pd.DataFrame) -> bytes:
    safe_company = _safe_filename(company_name)
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"tax_review_memo_{safe_company}_v14.md", memo_text.encode("utf-8-sig"))
        zf.writestr(f"tax_issue_matrix_{safe_company}_v14.csv", _to_csv_bytes(issue_matrix))
        zf.writestr(f"holding_tax_reconciliation_{safe_company}_v14.csv", _to_csv_bytes(reconciliation))
        zf.writestr(f"tax_request_list_{safe_company}_v14.csv", _to_csv_bytes(request_list))
    return buffer.getvalue()


def _render_tax_assumption_panel(assumptions: dict, scenario: dict) -> dict:
    with st.expander("Tax 분석 가정", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            fair_market_value_ratio = st.slider(
                "공정시장가액비율",
                min_value=40.0,
                max_value=100.0,
                value=float(assumptions.get("fair_market_value_ratio", assumptions.get("land_fmv_ratio_pct", 70.0))),
                step=5.0,
                key="v14_fair_market_value_ratio",
            )
        with c2:
            effective_holding_tax_rate = st.slider(
                "실효 보유세율",
                min_value=0.1,
                max_value=3.0,
                value=float(assumptions.get("effective_holding_tax_rate", 1.1)),
                step=0.1,
                key="v14_effective_holding_tax_rate",
            )
        with c3:
            official_price_growth_assumption = st.slider(
                "공시가격 상승 가정",
                min_value=-10.0,
                max_value=30.0,
                value=float(assumptions.get("official_price_growth_assumption", 10.0)),
                step=2.5,
                key="v14_official_price_growth_assumption",
            )
        with c4:
            holding_tax_increase_pct = st.slider(
                "보유세 증가율",
                min_value=0.0,
                max_value=50.0,
                value=float(assumptions.get("holding_tax_increase_pct", 10.0)),
                step=2.5,
                key="v14_holding_tax_increase_pct",
            )
        with c5:
            default_ffo_stress = float(scenario.get("ffo_haircut_pct", 5.0) or 5.0)
            ffo_stress_pct = st.slider(
                "FFO 스트레스",
                min_value=0.0,
                max_value=30.0,
                value=float(assumptions.get("ffo_stress_assumption", default_ffo_stress)),
                step=1.0,
                key="v14_ffo_stress_assumption",
            )
        st.caption(
            "가정은 신고 목적 세액 계산이 아니라 보유세 부담 방향성, FFO 현금유출, 요청자료 우선순위를 보기 위한 예비 분석 기준입니다."
        )
    return {
        "fair_market_value_ratio": fair_market_value_ratio,
        "effective_holding_tax_rate": effective_holding_tax_rate,
        "official_price_growth_assumption": official_price_growth_assumption,
        "holding_tax_increase_assumption": holding_tax_increase_pct,
        "holding_tax_increase_pct": holding_tax_increase_pct,
        "ffo_stress_assumption": ffo_stress_pct,
        "ffo_stress_pct": ffo_stress_pct,
        "sensitivity_pct": official_price_growth_assumption,
    }


def _render_tax_source_scope_banner(target_company: str, company_profile: dict, source_summary: dict):
    stock_code = company_profile.get("stock_code", "")
    company_label = f"{target_company} ({stock_code})" if stock_code else target_company
    latest_year = f"{source_summary['latest_year']}년" if source_summary["latest_year"] else "연도 미확인"
    policy = get_source_policy(source_summary.get("source_type"))

    with st.container(border=True):
        st.caption(f"현재 분석 대상: {company_label}")
        st.caption(
            f"분석 범위: {source_summary['scope_label']} / 데이터 기준: {latest_year} / "
            f"source_type: {source_summary['source_type']} / {source_summary.get('korean_label', policy.korean_label)} / "
            f"신뢰수준: {source_summary.get('reliability_level', policy.reliability_level)}"
        )
        st.caption(f"source_note: {source_summary['source_note']}")
        st.caption(source_summary.get("ui_warning_text", policy.ui_warning_text))


def _render_peer_tax_section(peer_context: dict | None):
    if not peer_context:
        return
    flags = peer_context.get("tax_red_flags", [])
    peer_metrics = peer_context.get("peer_metrics", pd.DataFrame())
    target_company = peer_context.get("target_company", "선택 리츠")

    with st.expander("Peer 기반 보유세 부담 비교", expanded=False):
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
        if metric_table.empty:
            st.info("Peer 보유세 부담 비교를 만들 수 있는 데이터가 부족합니다.")
        else:
            st.dataframe(metric_table, width="stretch", hide_index=True, height=240)


def _render_validation_panel(validation: dict):
    with st.expander("데이터 검증 및 한계", expanded=False):
        st.dataframe(
            pd.DataFrame(
                [
                    {"항목": "검증 상태", "값": validation.get("validation_status", "검토 필요")},
                    {"항목": "회사 전체 fallback 사용", "값": "예" if validation.get("fallback_used") else "아니오"},
                    {"항목": "자산별 보유세 자료", "값": "있음" if validation.get("asset_level_tax_data_exists") else "부족"},
                    {"항목": "FFO denominator", "값": "있음" if validation.get("ffo_exists") else "부족"},
                    {"항목": "공시가격 입력값", "값": "있음" if validation.get("official_price_exists") else "부족"},
                ]
            ),
            width="stretch",
            hide_index=True,
            height=190,
        )
        warnings = validation.get("warnings", [])
        if warnings:
            st.write("**검증 경고**")
            for item in warnings:
                st.write(f"- {item}")
        missing = validation.get("missing_fields", [])
        if missing:
            st.write("**부족 입력값**")
            st.write(", ".join(missing))
        limitations = validation.get("calculation_limitations", [])
        if limitations:
            st.write("**계산 한계**")
            for item in limitations:
                st.write(f"- {item}")


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
        "공시가격, 장부가액, Peer Snapshot, FFO를 연결해 보유세 부담과 요청자료 우선순위를 예비 검토합니다."
    )

    assumptions = assumptions or {}
    company_profile = (peer_context or {}).get("selected_company_profile", {}) or {}
    target_company = (peer_context or {}).get("target_company", company_profile.get("company_name", "선택 리츠"))
    peer_snapshot = (peer_context or {}).get("peer_snapshot", pd.DataFrame())
    peer_summary = (peer_context or {}).get("peer_summary", {})
    tax_flags = (peer_context or {}).get("tax_red_flags", [])

    company_tax_data = build_company_tax_dataset(target_company, peer_snapshot, company_profile)
    source_summary = get_tax_source_summary(target_company, company_tax_data)
    _render_tax_source_scope_banner(target_company, company_profile, source_summary)
    tax_pack_assumptions = _render_tax_assumption_panel(assumptions, scenario)

    tax_history = build_tax_history_from_company_tax_data(company_tax_data)
    if tax_history is None or tax_history.empty:
        st.warning("보유세 분석에 필요한 Tax Snapshot 또는 Peer Snapshot 데이터가 부족합니다.")
        return

    annual_summary = summarize_holding_tax_history(tax_history)
    tax_bridge = build_holding_tax_bridge(target_company, company_tax_data, peer_snapshot, tax_pack_assumptions)
    validation = validate_tax_inputs(target_company, company_tax_data, peer_snapshot)
    source_detail = build_source_detail(tax_history)
    reconciliation = build_holding_tax_reconciliation(tax_history, latest_kpi)
    ffo_pack_stress = build_ffo_cash_outflow_stress(
        latest_kpi,
        annual_summary,
        tax_pack_assumptions["holding_tax_increase_pct"],
        tax_pack_assumptions["ffo_stress_pct"],
    )
    tax_source_status = get_tax_source_status(target_company, company_tax_data)
    issue_matrix = build_tax_issue_matrix(tax_flags, reconciliation, ffo_pack_stress, tax_source_status)
    request_list = build_tax_request_list(
        issue_matrix,
        source_summary["source_type"],
        {
            "fallback_used": validation.get("fallback_used"),
            "asset_level_tax_data_exists": validation.get("asset_level_tax_data_exists"),
        },
    )
    automation_summary = build_tax_automation_summary(issue_matrix, request_list, reconciliation)
    memo_text = build_tax_review_memo(
        company_profile,
        tax_source_status,
        issue_matrix,
        reconciliation,
        request_list,
        ffo_pack_stress,
        peer_summary,
        source_summary=source_summary,
        bridge=tax_bridge,
        validation=validation,
    )

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
    m3.metric("추정 과세표준", format_bn_krw(latest_tax_base))
    m4.metric("자료 기준", source_summary.get("korean_label", source_summary["source_type"]))

    c1, c2 = st.columns([1.05, 0.95])
    with c1:
        fig_tax_trend = px.line(annual_summary, x="year", y="보유세_추정_백만원", markers=True, title="최근 5년 보유세 추정액")
        st.plotly_chart(compact_fig(fig_tax_trend, 260), width="stretch")
    with c2:
        latest_asset_tax = tax_history[tax_history["year"] == latest_year].copy().sort_values("보유세_추정_백만원", ascending=False)
        fig_asset_tax = px.bar(
            latest_asset_tax.head(8),
            x="보유세_추정_백만원",
            y="asset_name",
            orientation="h",
            title=f"{latest_year}E 자산/회사 단위 보유세",
        )
        fig_asset_tax.update_traces(texttemplate="%{x:,.0f}", textposition="outside", cliponaxis=False)
        st.plotly_chart(compact_fig(fig_asset_tax, 260), width="stretch")

    st.markdown("## 보유세 추정 브리지")
    st.caption("source_type별 신뢰수준과 계산 한계를 함께 표시합니다. 회사 전체 추정 행은 자산별 고지세액 대사 전까지 예비 분석입니다.")
    st.dataframe(tax_bridge, width="stretch", hide_index=True, height=230)

    _render_peer_tax_section(peer_context)

    st.markdown("## Tax Issue Matrix")
    st.caption("Tax Red Flag, 보유세 정합성, FFO 현금유출 스트레스 결과를 실무 검토 항목으로 변환합니다.")
    st.dataframe(style_risk_review_table(issue_matrix), width="stretch", hide_index=True, height=310)

    st.markdown("## 보유세 정합성 검토")
    st.caption("투자부동산 장부가액, 공시가격, 과세표준, 추정 보유세를 연결한 예비 대사표입니다.")
    st.dataframe(reconciliation, width="stretch", hide_index=True, height=240)

    st.markdown("## FFO 현금유출 스트레스")
    if ffo_pack_stress.empty:
        st.warning("FFO 현금유출 시나리오를 계산할 수 없습니다. KPI와 보유세 요약 데이터를 확인하세요.")
    else:
        c1, c2 = st.columns([1.05, 0.95])
        with c1:
            st.dataframe(ffo_pack_stress, width="stretch", hide_index=True, height=240)
        with c2:
            fig_cash = px.bar(ffo_pack_stress, x="항목", y="금액(억원)", title="보유세 스트레스 금액")
            st.plotly_chart(compact_fig(fig_cash, 250), width="stretch")

    st.markdown("## Tax Request List")
    st.dataframe(request_list, width="stretch", hide_index=True, height=280)

    st.markdown("## Tax Review Memo Draft")
    st.markdown(memo_text)

    st.markdown("## Export Tax Review Pack")
    safe_company = _safe_filename(target_company)
    e1, e2, e3, e4, e5 = st.columns(5)
    with e1:
        st.download_button(
            "Memo MD",
            data=memo_text.encode("utf-8-sig"),
            file_name=f"tax_review_memo_{safe_company}_v14.md",
            mime="text/markdown",
            width="stretch",
        )
    with e2:
        st.download_button(
            "Issue CSV",
            data=_to_csv_bytes(issue_matrix),
            file_name=f"tax_issue_matrix_{safe_company}_v14.csv",
            mime="text/csv",
            width="stretch",
        )
    with e3:
        st.download_button(
            "Recon CSV",
            data=_to_csv_bytes(reconciliation),
            file_name=f"holding_tax_reconciliation_{safe_company}_v14.csv",
            mime="text/csv",
            width="stretch",
        )
    with e4:
        st.download_button(
            "Request CSV",
            data=_to_csv_bytes(request_list),
            file_name=f"tax_request_list_{safe_company}_v14.csv",
            mime="text/csv",
            width="stretch",
        )
    with e5:
        st.download_button(
            "ZIP",
            data=_zip_review_pack(target_company, memo_text, issue_matrix, reconciliation, request_list),
            file_name=f"tax_review_pack_{safe_company}_v14.zip",
            mime="application/zip",
            width="stretch",
        )

    _render_validation_panel(validation)

    with st.expander("Tax 데이터 기준 및 source detail", expanded=False):
        st.caption(f"source_type: {source_summary['source_type']} / source_note: {source_summary['source_note']}")
        st.dataframe(source_detail, width="stretch", hide_index=True, height=220)

    with st.expander("원천 데이터", expanded=False):
        st.write("**Tax Snapshot / fallback 입력값**")
        st.dataframe(company_tax_data, width="stretch", hide_index=True, height=220)
        st.write("**Workflow 자동화 요약**")
        st.dataframe(automation_summary, width="stretch", hide_index=True, height=170)

    st.warning(
        "본 보유세 분석은 신고 목적의 확정 세액 산출, 법률의견, 투자 추천이 아니라 예비 검토입니다. "
        "실제 고지세액은 자산별 과세구분, 지자체 조례, 감면, 세부담상한, 건축물 시가표준액, 리츠별 보유 구조에 따라 달라질 수 있습니다."
    )
