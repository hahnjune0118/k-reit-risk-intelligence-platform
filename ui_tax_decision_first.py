from __future__ import annotations

from decimal import Decimal

import pandas as pd
import plotly.express as px
import streamlit as st

from src.tax_v15.case_study import (
    GOLDEN_ASSET_ID,
    GOLDEN_RECALCULATION_RAW,
    build_case_kpis,
    build_case_request_list,
    build_sensitivity_scenarios,
    build_tax_issue_matrix,
    select_golden_case,
)
from src.tax_v15.constants import DISCLAIMER_KO
from src.tax_v15.reporting import (
    build_tax_review_memo,
    dataframe_csv_bytes,
    review_document_html,
    review_pack_excel_bytes,
)
from ui_common import compact_fig
from ui_tax_case_study import (
    GOLDEN_OWNERSHIP_DISPLAY,
    _decimal_tax_total,
    _display_calculations,
    _format_eok,
    _load_evidence_matrix,
    _load_tax_v15_data,
    _render_frame,
    _rule_rows,
    _status_label,
)


SCENARIO_LABELS = {
    "Base": "Base",
    "Moderate": "+5%",
    "Severe": "+10%",
    "Custom": "사용자 설정",
}

EVIDENCE_CATEGORY_BY_ISSUE = {
    "assessment_date_trust_status_unverified": "등기·신탁·담보 근거",
    "parcel_area_difference_5_3": "공식가액·계산입력",
}


def _scenario_display(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    numeric_columns = [
        "토지 시가표준액",
        "건축물 시가표준액",
        "토지 관련 세액",
        "건축물 관련 세액",
        "소방분",
        "총 보유세",
        "Base 대비 증감액",
        "Base 대비 증감률",
    ]
    for column in numeric_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result["시나리오"] = result["Scenario"].map(SCENARIO_LABELS)
    return result


def _evidence_category(issue_code: str) -> str:
    return EVIDENCE_CATEGORY_BY_ISSUE.get(issue_code, "실제 고지서·대사")


def _build_issue_request_table(
    issue_matrix: pd.DataFrame,
    request_list: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    request_links = request_list[
        ["issue_code", "linked_request_id", "reviewer_status"]
    ].drop_duplicates("issue_code")
    merged = issue_matrix.merge(request_links, on="issue_code", how="left")
    merged["증빙 구분"] = merged["issue_code"].map(_evidence_category)
    merged["현재 상태"] = merged["resolution_status"].map(
        {"Open": "미해결", "Resolved": "해결"}
    ).fillna(merged["resolution_status"])

    review = merged[
        [
            "priority",
            "증빙 구분",
            "tax_issue",
            "현재 상태",
            "required_document",
            "potential_tax_effect",
            "request_reason",
        ]
    ].rename(
        columns={
            "priority": "우선순위",
            "tax_issue": "주요 이슈",
            "required_document": "필요 증빙",
            "potential_tax_effect": "예상 영향",
            "request_reason": "다음 조치",
        }
    )
    detail = merged[
        [
            "priority",
            "issue_code",
            "evidence_status",
            "quantitative_sensitivity",
            "linked_request_id",
            "reviewer_status",
        ]
    ].rename(
        columns={
            "priority": "우선순위",
            "issue_code": "이슈 코드",
            "evidence_status": "근거 상태",
            "quantitative_sensitivity": "정량 민감도",
            "linked_request_id": "연결 요청 ID",
            "reviewer_status": "검토 상태",
        }
    )
    return review, detail


def _issue_style(frame: pd.DataFrame):
    def priority_color(value: str) -> str:
        if value == "P0":
            return "background-color: #f5d7d9; color: #702027; font-weight: 700"
        if value == "P1":
            return "background-color: #f8edc7; color: #654f0b; font-weight: 700"
        return ""

    def status_color(value: str) -> str:
        if value == "미해결":
            return "background-color: #f1f3f5; color: #343a40; font-weight: 600"
        return "background-color: #d1e7dd; color: #0f5132; font-weight: 600"

    return frame.style.map(priority_color, subset=["우선순위"]).map(
        status_color,
        subset=["현재 상태"],
    )


def _format_decimal_value(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{Decimal(str(value)):,}원"


def _rate_summary(row: pd.Series) -> str:
    parts = []
    fair_value_ratio = row.get("fair_market_value_ratio")
    tax_rate = row.get("tax_rate")
    multiplier = row.get("multiplier")
    if pd.notna(fair_value_ratio):
        percentage = Decimal(str(fair_value_ratio)) * Decimal("100")
        parts.append(f"공정시장가액비율 {percentage:g}%")
    if pd.notna(tax_rate):
        percentage = Decimal(str(tax_rate)) * Decimal("100")
        parts.append(f"세율 {percentage:g}%")
    if pd.notna(multiplier):
        parts.append(f"배율 {Decimal(str(multiplier)):g}배")
    return " · ".join(parts) or "해당 없음"


def _build_workpaper_table(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in frame.iterrows():
        tax_base = row.get("tax_base")
        official_value = row.get("official_value")
        if pd.notna(tax_base):
            input_value = f"과세표준 {_format_decimal_value(tax_base)}"
        elif pd.notna(official_value):
            input_value = f"공식 입력값 {_format_decimal_value(official_value)}"
        else:
            input_value = "해당 없음"
        not_applicable = row.get("calculation_status") == "not_applicable"
        rows.append(
            {
                "세목": row.get("tax_name"),
                "입력값 또는 과세표준": input_value,
                "적용률·세율": _rate_summary(row),
                "재계산액": _format_decimal_value(row.get("calculated_tax")),
                "근거 상태": _status_label(str(row.get("calculation_status"))),
                "고지서 대사상태": "해당 없음" if not_applicable else "미대사",
                "검토사항": (
                    "실제 과세구분 확인 필요"
                    if not_applicable
                    else "산식 재계산 완료·실제 고지서 대사 필요"
                ),
            }
        )
    return pd.DataFrame(rows)


def _render_scenario_charts(
    summary: pd.DataFrame,
    breakdown: pd.DataFrame,
) -> None:
    chart_data = _scenario_display(summary)
    chart_data["총 보유세(억원)"] = chart_data["총 보유세"] / 100_000_000
    chart_data["증감액(억원)"] = chart_data["Base 대비 증감액"] / 100_000_000
    chart_data["증감률 표시"] = chart_data["Base 대비 증감률"].map(
        lambda value: f"{value:.2f}%"
    )
    colors = {
        "Base": "#2F5D62",
        "+5%": "#6F8F72",
        "+10%": "#A6652A",
        "사용자 설정": "#59636E",
    }

    left, right = st.columns(2)
    with left:
        total_chart = px.bar(
            chart_data,
            x="시나리오",
            y="총 보유세(억원)",
            color="시나리오",
            color_discrete_map=colors,
            text="총 보유세(억원)",
            title="시나리오별 보유세 재계산액",
        )
        total_chart.update_traces(
            texttemplate="%{text:.2f}",
            textposition="outside",
            cliponaxis=False,
        )
        total_chart.update_layout(showlegend=False)
        st.plotly_chart(compact_fig(total_chart, 285), width="stretch")

    with right:
        delta_chart = px.bar(
            chart_data,
            x="시나리오",
            y="증감액(억원)",
            color="시나리오",
            color_discrete_map=colors,
            text="증감률 표시",
            title="Base 대비 증감액 및 증감률",
            hover_data={"Base 대비 증감률": ":.2f"},
        )
        delta_chart.update_traces(
            texttemplate="%{text}",
            textposition="outside",
            cliponaxis=False,
        )
        delta_chart.update_layout(showlegend=False)
        st.plotly_chart(compact_fig(delta_chart, 285), width="stretch")

    composition = breakdown[
        breakdown["Scenario"].eq("Base") & breakdown["세목"].ne("총계")
    ].copy()
    composition["재계산액(억원)"] = (
        pd.to_numeric(composition["계산세액"], errors="coerce") / 100_000_000
    )
    composition = composition[composition["재계산액(억원)"].gt(0)]
    composition_chart = px.bar(
        composition.sort_values("재계산액(억원)"),
        x="재계산액(억원)",
        y="세목",
        orientation="h",
        text="재계산액(억원)",
        title="Base 세목별 구성",
        color="세목",
        color_discrete_sequence=[
            "#2F5D62",
            "#A6652A",
            "#6F8F72",
            "#667085",
            "#8B6F47",
            "#4D7C8A",
            "#7A6F9B",
        ],
    )
    composition_chart.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside",
        cliponaxis=False,
    )
    composition_chart.update_layout(showlegend=False)
    st.plotly_chart(compact_fig(composition_chart, 310), width="stretch")


def _render_downloads(
    *,
    calculations: pd.DataFrame,
    sensitivity_summary: pd.DataFrame,
    sensitivity_breakdown: pd.DataFrame,
    issue_matrix: pd.DataFrame,
    request_list: pd.DataFrame,
    reconciliation: pd.DataFrame,
    evidence_matrix: pd.DataFrame,
    case_scope: pd.DataFrame,
    assets: pd.DataFrame,
    parcels: pd.DataFrame,
    buildings: pd.DataFrame,
    taxpayers: pd.DataFrame,
    memo: str,
) -> None:
    safe_prefix = "395400_SK_Seorin_2026"
    try:
        excel_bytes = review_pack_excel_bytes(
            {
                "CaseScope": case_scope,
                "Assets": assets,
                "Parcels": parcels,
                "Buildings": buildings,
                "Taxpayers": taxpayers,
                "Calculations": calculations,
                "ScenarioSummary": sensitivity_summary,
                "ScenarioBreakdown": sensitivity_breakdown,
                "TaxIssueMatrix": issue_matrix,
                "RequestList": request_list,
                "Reconciliation": reconciliation,
                "Evidence": evidence_matrix,
            }
        )
        excel_available = True
    except (ImportError, ModuleNotFoundError):
        excel_bytes = b""
        excel_available = False

    d1, d2 = st.columns(2)
    d1.download_button(
        "계산내역 CSV",
        dataframe_csv_bytes(calculations),
        file_name=f"{safe_prefix}_calculation_detail.csv",
        mime="text/csv",
        width="stretch",
    )
    d2.download_button(
        "시나리오 CSV",
        dataframe_csv_bytes(sensitivity_summary),
        file_name=f"{safe_prefix}_sensitivity.csv",
        mime="text/csv",
        width="stretch",
    )
    d3, d4 = st.columns(2)
    d3.download_button(
        "이슈 목록 CSV",
        dataframe_csv_bytes(issue_matrix),
        file_name=f"{safe_prefix}_tax_issue_matrix.csv",
        mime="text/csv",
        width="stretch",
    )
    d4.download_button(
        "요청자료 CSV",
        dataframe_csv_bytes(request_list),
        file_name=f"{safe_prefix}_request_list.csv",
        mime="text/csv",
        width="stretch",
    )
    d5, d6, d7 = st.columns(3)
    d5.download_button(
        "검토팩 Excel",
        excel_bytes,
        file_name=f"{safe_prefix}_tax_review_pack.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        disabled=not excel_available,
        width="stretch",
    )
    d6.download_button(
        "검토메모 Markdown",
        memo.encode("utf-8-sig"),
        file_name=f"{safe_prefix}_tax_review_memo.md",
        mime="text/markdown",
        width="stretch",
    )
    d7.download_button(
        "검토문서 HTML",
        review_document_html("SK리츠 — SK서린빌딩 Tax Review", memo),
        file_name=f"{safe_prefix}_tax_review_document.html",
        mime="text/html",
        width="stretch",
    )
    if not excel_available:
        st.caption("Excel 내보내기 패키지를 설치하면 검토팩 다운로드가 활성화됩니다.")


def render_tax_mode(
    asset_risk: pd.DataFrame,
    scenario: dict,
    latest_kpi: pd.Series,
    assumptions: dict | None = None,
    peer_context: dict | None = None,
):
    del asset_risk, scenario, latest_kpi, assumptions, peer_context
    try:
        case = select_golden_case(_load_tax_v15_data())
    except ValueError as exc:
        st.error(str(exc))
        return

    assets = case.assets
    parcels = case.parcels
    buildings = case.buildings
    taxpayers = case.taxpayers
    calculations = case.calculations
    reconciliation = case.reconciliation
    evidence_matrix = _load_evidence_matrix()
    issue_matrix = build_tax_issue_matrix(case)
    request_list = build_case_request_list(issue_matrix, case.requests)
    kpis = build_case_kpis(case, issue_matrix)
    verified_rows = calculations[
        calculations["calculation_status"].isin(
            ["verified_notice", "official_source_calculated", "not_applicable"]
        )
        & calculations["tax_name"].ne("토지 시가표준액")
    ]
    base_total = _decimal_tax_total(verified_rows)
    if base_total != GOLDEN_RECALCULATION_RAW:
        st.error(
            "기준 재계산액이 검증된 원시 합계와 일치하지 않아 표시를 차단했습니다."
        )
        return

    case_scope = pd.DataFrame(
        [
            {"항목": "분석 대상", "내용": "SK리츠 (395400) / SK서린빌딩"},
            {"항목": "Asset ID", "내용": GOLDEN_ASSET_ID},
            {"항목": "Taxpayer ID", "내용": "SKR-TP-001"},
            {"항목": "기준연도", "내용": "2026년"},
            {"항목": "보유구조", "내용": GOLDEN_OWNERSHIP_DISPLAY},
        ]
    )
    ownership = assets[
        [
            "investment_holding_type",
            "title_holding_type",
            "registered_owner",
            "trustee",
            "trustor",
            "beneficial_owner",
            "property_taxpayer",
            "source_url",
        ]
    ].rename(
        columns={
            "investment_holding_type": "투자 보유형태",
            "title_holding_type": "등기 보유형태",
            "registered_owner": "등기명의자",
            "trustee": "수탁자",
            "trustor": "위탁자",
            "beneficial_owner": "경제적 보유주체",
            "property_taxpayer": "재산세 납세의무자",
            "source_url": "출처",
        }
    )
    taxpayer_status = taxpayers[
        [
            "statutory_eligibility_status",
            "actual_notice_classification",
            "legal_review_status",
            "notice_reconciliation_status",
            "source_url",
        ]
    ].rename(
        columns={
            "statutory_eligibility_status": "법정 적격성",
            "actual_notice_classification": "실제 고지 과세구분",
            "legal_review_status": "법률 검토 상태",
            "notice_reconciliation_status": "고지 대사 상태",
            "source_url": "출처",
        }
    )
    source_lineage = calculations[
        [
            "tax_name",
            "input_source",
            "calculation_status",
            "law_name",
            "article",
            "source_url",
        ]
    ].drop_duplicates().rename(
        columns={
            "tax_name": "세목",
            "input_source": "입력자료",
            "calculation_status": "계산 상태",
            "law_name": "법령",
            "article": "조문",
            "source_url": "출처",
        }
    )

    st.markdown("## Tax: 의사결정 중심 보유세 검토")
    st.caption(
        "SK리츠 · SK서린빌딩 · 2026년 | 공식 입력근거, 재계산 결과, "
        "미해결 이슈와 추가 요청자료를 함께 검토합니다."
    )

    conclusion_tab, issue_tab, workpaper_tab, evidence_tab = st.tabs(
        [
            "결론 및 시나리오",
            "주요 이슈 및 요청자료",
            "계산조서",
            "근거 및 다운로드",
        ]
    )

    with conclusion_tab:
        st.warning(
            "공식 과세기초자료를 이용한 재계산 결과이며, 실제 고지서와의 "
            "대사는 완료되지 않았습니다."
        )
        k1, k2, k3 = st.columns(3)
        k1.metric("2026 보유세 재계산액", _format_eok(base_total))
        k2.metric("공식 입력근거 Coverage", kpis["evidence_coverage"])
        k3.metric("실제 고지서 대사 Coverage", kpis["notice_coverage"])
        k4, k5, k6 = st.columns(3)
        k4.metric("미해결 P0", kpis["p0_open"])
        k5.metric("미해결 P1", kpis["p1_open"])
        k6.metric("재계산 세목", kpis["completed_tax_items"])

        st.markdown("#### 공시가격·시가표준액 민감도")
        s1, s2 = st.columns(2)
        custom_land_change = s1.slider(
            "사용자 설정: 토지 개별공시지가 변동",
            min_value=-10,
            max_value=20,
            value=0,
            step=1,
            format="%d%%",
        )
        custom_building_change = s2.slider(
            "사용자 설정: 건축물 시가표준액 변동",
            min_value=-10,
            max_value=20,
            value=0,
            step=1,
            format="%d%%",
        )
        sensitivity_summary, sensitivity_breakdown = build_sensitivity_scenarios(
            case,
            custom_land_change,
            custom_building_change,
        )
        _render_scenario_charts(sensitivity_summary, sensitivity_breakdown)

        scenario_table = _scenario_display(sensitivity_summary)[
            ["시나리오", "총 보유세", "Base 대비 증감액", "Base 대비 증감률"]
        ]
        st.dataframe(
            scenario_table,
            hide_index=True,
            width="stretch",
            column_config={
                "총 보유세": st.column_config.NumberColumn(
                    "재계산액",
                    format="%,.0f원",
                ),
                "Base 대비 증감액": st.column_config.NumberColumn(
                    "Base 대비 증감액",
                    format="%,.0f원",
                ),
                "Base 대비 증감률": st.column_config.NumberColumn(
                    "Base 대비 증감률",
                    format="%.2f%%",
                ),
            },
        )
        st.caption(
            "시나리오는 공식 입력값의 기계적 민감도이며 미래 세액이나 "
            "과세관청의 결정세액을 예측하지 않습니다."
        )

    memo = build_tax_review_memo(
        case.reit_name,
        case.tax_year,
        assets,
        parcels,
        buildings,
        taxpayers,
        calculations,
        case.validations,
        request_list,
        sensitivity_summary,
        issue_matrix,
    )

    with issue_tab:
        st.markdown("### 우선 검토할 이슈와 요청자료")
        st.caption(
            "P0는 결론 또는 납세의무자 판단에 직접 필요한 미해결 항목, "
            "P1은 계산 정교화와 고지 대사에 필요한 후속 항목입니다."
        )
        issue_review, issue_detail = _build_issue_request_table(
            issue_matrix,
            request_list,
        )
        st.dataframe(
            _issue_style(issue_review),
            hide_index=True,
            width="stretch",
            height=380,
            column_config={
                "우선순위": st.column_config.TextColumn(width="small"),
                "증빙 구분": st.column_config.TextColumn(width="medium"),
                "주요 이슈": st.column_config.TextColumn(width="medium"),
                "현재 상태": st.column_config.TextColumn(width="small"),
                "필요 증빙": st.column_config.TextColumn(width="large"),
                "예상 영향": st.column_config.TextColumn(width="large"),
                "다음 조치": st.column_config.TextColumn(width="large"),
            },
        )
        st.info(
            "등기·신탁·담보 근거는 소유·권리관계, 공식가액·계산입력은 "
            "과세표준 산정, 실제 고지서는 재계산액 대사 목적으로 구분합니다."
        )
        with st.expander("이슈별 근거상태와 연결 요청 ID", expanded=False):
            _render_frame(issue_detail, height=300)

    with workpaper_tab:
        st.markdown("### 세목별 보유세 재계산조서")
        st.markdown(f"**Raw statutory recalculation:** `{base_total:,}원`")
        st.caption(
            "정밀 금액은 계산조서와 다운로드에서 유지하며, 결론 화면은 "
            "가독성을 위해 억원 단위로 반올림합니다."
        )
        workpaper = _build_workpaper_table(verified_rows)
        st.dataframe(
            workpaper,
            hide_index=True,
            width="stretch",
            height=390,
            column_config={
                "세목": st.column_config.TextColumn(width="medium"),
                "입력값 또는 과세표준": st.column_config.TextColumn(width="large"),
                "적용률·세율": st.column_config.TextColumn(width="large"),
                "재계산액": st.column_config.TextColumn(width="large"),
                "근거 상태": st.column_config.TextColumn(width="medium"),
                "고지서 대사상태": st.column_config.TextColumn(width="medium"),
                "검토사항": st.column_config.TextColumn(width="large"),
            },
        )
        with st.expander("세목별 산식·법적 근거·출처", expanded=False):
            _render_frame(_display_calculations(verified_rows), height=430)
        with st.expander("자산·납세의무자·과세구분", expanded=False):
            _render_frame(case_scope, height=220)
            _render_frame(ownership, height=180)
            _render_frame(taxpayer_status, height=180)
        with st.expander("Tax Rule Master", expanded=False):
            rule_codes = case.rules["rule_code"].dropna().astype(str).unique().tolist()
            _render_frame(_rule_rows(case.rules, rule_codes), height=420)
        with st.expander("시나리오별 세목 상세", expanded=False):
            breakdown_display = sensitivity_breakdown.copy()
            breakdown_display["계산세액"] = pd.to_numeric(
                breakdown_display["계산세액"],
                errors="coerce",
            )
            _render_frame(breakdown_display, height=430)

    with evidence_tab:
        st.markdown("### 근거, 검증통제 및 결과 내려받기")
        st.warning(
            "실제 고지서가 확인되기 전에는 재계산 결과를 확정세액 또는 "
            "verified_notice 상태로 표시하지 않는 Fail-closed 원칙을 적용합니다."
        )
        st.caption(
            "토지·건축물대장, 신탁원부, 공동담보목록 및 임대차 공시는 "
            "소유·권리 또는 거래구조 분석을 지원하지만, 공시가격·시가표준액 등 "
            "공식가액이나 실제 세금 고지서를 대체하지 않습니다."
        )
        st.caption(
            "비공개 등기·신탁 원문은 공개 앱에 노출하지 않으며, 공개된 출처와 "
            "검증상태만 표시합니다."
        )

        st.markdown("#### 실제 고지서 및 주요 입력값 대사")
        _render_frame(reconciliation, height=230)
        with st.expander("Source Lineage", expanded=False):
            _render_frame(source_lineage, height=390)
        with st.expander("Evidence Matrix", expanded=False):
            _render_frame(evidence_matrix, height=430)
        with st.expander("Tax Review Memo", expanded=False):
            st.markdown(memo)

        st.warning(DISCLAIMER_KO)
        st.markdown("#### 결과 내려받기")
        _render_downloads(
            calculations=calculations,
            sensitivity_summary=sensitivity_summary,
            sensitivity_breakdown=sensitivity_breakdown,
            issue_matrix=issue_matrix,
            request_list=request_list,
            reconciliation=reconciliation,
            evidence_matrix=evidence_matrix,
            case_scope=case_scope,
            assets=assets,
            parcels=parcels,
            buildings=buildings,
            taxpayers=taxpayers,
            memo=memo,
        )
