from __future__ import annotations

from decimal import Decimal

import pandas as pd
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
from src.tax_v15.constants import DISCLAIMER_KO, PROJECT_ROOT, SOURCE_BADGES
from src.tax_v15.loaders import load_v15_bundle
from src.tax_v15.reporting import (
    build_tax_review_memo,
    dataframe_csv_bytes,
    review_document_html,
    review_pack_excel_bytes,
)


GOLDEN_RECALCULATION_LABEL = "2026년 공식 입력자료 기반 보유세 산식 재계산액"
GOLDEN_OWNERSHIP_DISPLAY = (
    "SK리츠가 위탁자이자 재산세 납세의무자인 신탁보유 오피스 자산"
)
EVIDENCE_MATRIX_PATH = (
    PROJECT_ROOT
    / "docs"
    / "v15"
    / "golden_asset"
    / "SK_SEORIN_EVIDENCE_MATRIX.csv"
)


@st.cache_data(ttl=3600, show_spinner=False)
def _load_tax_v15_data():
    return load_v15_bundle()


@st.cache_data(ttl=3600, show_spinner=False)
def _load_evidence_matrix() -> pd.DataFrame:
    return pd.read_csv(
        EVIDENCE_MATRIX_PATH,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )


def _safe_text(value, fallback: str = "데이터 부족") -> str:
    if value is None or value is pd.NA:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text or fallback


def _status_label(status: str) -> str:
    return f"[{SOURCE_BADGES.get(status, '데이터 부족')}]"


def _decimal_tax_total(frame: pd.DataFrame) -> Decimal | None:
    total = Decimal("0")
    found = False
    for value in frame.get("calculated_tax", pd.Series(dtype="object")):
        if pd.isna(value):
            continue
        total += Decimal(str(value))
        found = True
    return total if found else None


def _format_eok(value: Decimal) -> str:
    return f"약 {value / Decimal('100000000'):.2f}억원"


def _display_calculations(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "tax_name",
        "tax_classification",
        "official_value",
        "tax_base",
        "tax_rate",
        "multiplier",
        "calculated_tax",
        "calculation_status",
        "formula_text",
        "article",
        "source_url",
    ]
    if frame is None or frame.empty:
        return pd.DataFrame(
            columns=[
                "세목",
                "과세구분",
                "공식 입력값(원)",
                "과세표준(원)",
                "세율",
                "배율",
                "계산세액(원)",
                "근거 상태",
                "계산식",
                "법적 근거",
                "출처",
            ]
        )
    result = frame[columns].copy()
    result["calculation_status"] = result["calculation_status"].map(
        lambda value: _status_label(str(value))
    )
    return result.rename(
        columns={
            "tax_name": "세목",
            "tax_classification": "과세구분",
            "official_value": "공식 입력값(원)",
            "tax_base": "과세표준(원)",
            "tax_rate": "세율",
            "multiplier": "배율",
            "calculated_tax": "계산세액(원)",
            "calculation_status": "근거 상태",
            "formula_text": "계산식",
            "article": "법적 근거",
            "source_url": "출처",
        }
    )


def _render_frame(frame: pd.DataFrame, *, height: int = 230) -> None:
    if frame is None or frame.empty:
        st.info("현재 공개자료에서 확인 가능한 행이 없습니다. 검증되지 않은 값은 계산하지 않습니다.")
        return
    config = {}
    for column in ["출처", "source_url", "공식 홈페이지"]:
        if column in frame.columns:
            config[column] = st.column_config.LinkColumn(column, display_text="원문")
    st.dataframe(
        frame,
        hide_index=True,
        width="stretch",
        height=height,
        column_config=config,
    )


def _rule_rows(rules: pd.DataFrame, codes: list[str]) -> pd.DataFrame:
    selected = rules[rules["rule_code"].isin(codes)].copy()
    if selected.empty:
        return pd.DataFrame()
    columns = [
        "tax_name",
        "tax_classification",
        "bracket_start",
        "bracket_end",
        "marginal_rate",
        "fair_market_value_ratio",
        "law_name",
        "article",
        "exact_clause_summary",
        "source_url",
    ]
    return selected[columns].drop_duplicates().rename(
        columns={
            "tax_name": "세목",
            "tax_classification": "구분",
            "bracket_start": "구간 시작",
            "bracket_end": "구간 종료",
            "marginal_rate": "세율",
            "fair_market_value_ratio": "공정시장가액비율",
            "law_name": "법령",
            "article": "조문",
            "exact_clause_summary": "검증 요약",
            "source_url": "출처",
        }
    )


def _render_stage(
    number: int,
    title: str,
    *,
    conclusion: str,
    legal_basis: pd.DataFrame | None = None,
    requirements: list[str] | None = None,
    formula: str = "",
    calculation_rows: pd.DataFrame | None = None,
    source_rows: pd.DataFrame | None = None,
    limitation: str = "",
    expanded: bool = False,
) -> None:
    with st.expander(f"{number}. {title}", expanded=expanded):
        st.markdown("**A. 결론**")
        st.write(conclusion)
        if legal_basis is not None and not legal_basis.empty:
            st.markdown("**B-C. 적용 법규와 근거**")
            _render_frame(legal_basis, height=min(270, 80 + len(legal_basis) * 35))
        if requirements:
            st.markdown("**D. 적용 요건**")
            for item in requirements:
                st.write(f"- {item}")
        if formula:
            st.markdown("**E. 계산 공식**")
            st.code(formula, language="text")
        if calculation_rows is not None:
            st.markdown("**F-G. 실제 숫자 대입 및 계산 결과**")
            _render_frame(_display_calculations(calculation_rows), height=290)
        if source_rows is not None:
            st.markdown("**H. 출처**")
            _render_frame(source_rows, height=235)
        if limitation:
            st.markdown("**I. 한계 및 검토 필요사항**")
            st.warning(limitation)


def _scenario_display(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in [
        "토지 시가표준액",
        "건축물 시가표준액",
        "토지 관련 세액",
        "건축물 관련 세액",
        "소방분",
        "총 보유세",
        "Base 대비 증감액",
        "Base 대비 증감률",
    ]:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result


def _issue_style(frame: pd.DataFrame):
    def priority_color(value: str) -> str:
        if value == "P0":
            return "background-color: #f8d7da; color: #7a1620; font-weight: 700"
        if value == "P1":
            return "background-color: #fff3cd; color: #6c5200; font-weight: 700"
        return ""

    def status_color(value: str) -> str:
        if value == "Open":
            return "background-color: #f1f3f5; color: #343a40; font-weight: 600"
        return "background-color: #d1e7dd; color: #0f5132; font-weight: 600"

    return frame.style.map(priority_color, subset=["priority"]).map(
        status_color,
        subset=["resolution_status"],
    )


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
        st.error("Golden Asset Base 계산액이 검증된 raw 합계와 일치하지 않아 표시를 차단했습니다.")
        return

    st.markdown("## Tax Case Study")
    st.markdown("### SK리츠 — SK서린빌딩")
    st.caption(
        "공모리츠 대표 자산의 주소·PNU·시가표준액·신탁구조·납세의무자를 "
        "공식자료로 연결하여 보유세를 자산 단위로 재계산한 Golden Asset 사례"
    )
    st.info(
        "본 Tax 모듈은 SK리츠 전체 자산의 확정 세액을 산출하는 도구가 아니라, "
        "SK리츠의 대표 자산인 SK서린빌딩을 대상으로 공모리츠 보유세 검토 "
        "프로세스를 구현한 심층 Case Study입니다."
    )

    st.markdown("### 1. Executive Conclusion")
    st.success(
        "SK서린빌딩의 확인된 공식 입력자료와 현행 표준 산식에 따른 2026년 "
        "보유세 재계산액은 약 12.51억원입니다. 이는 실제 고지세액이 아니며, "
        "실제 과세내역서상 분리과세 코드, 법정 절사, 감면, 세부담상한, "
        "지방자치단체 조정 및 고지서 대사는 미완료 상태입니다."
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("공식 입력자료 기반 재계산액", _format_eok(base_total))
    c2.metric("Raw statutory recalculation", f"{base_total:,}원")
    c3.metric("Actual assessed amount", "미확인")
    c4.metric("Notice reconciliation", "미완료")
    st.markdown(f"**Raw statutory recalculation:** `{base_total:,}원`")
    st.caption(
        "실제 고지세액 대사 미완료 · 법정 절사 미반영 · 세부담상한 미반영 · "
        "감면·조례 미확인 · 실제 과세내역서 미확인"
    )

    case_scope = pd.DataFrame(
        [
            {"항목": "분석유형", "내용": "Golden Asset Tax Case Study"},
            {"항목": "리츠", "내용": "SK리츠 (395400)"},
            {"항목": "자산", "내용": "SK서린빌딩"},
            {"항목": "Asset ID", "내용": GOLDEN_ASSET_ID},
            {"항목": "Taxpayer ID", "내용": "SKR-TP-001"},
            {"항목": "기준연도", "내용": "2026년"},
        ]
    )
    _render_stage(
        2,
        "SK리츠·SK서린빌딩 Case Scope",
        conclusion="분석범위는 SK리츠의 SK서린빌딩 단일 자산과 2026년 기준연도로 고정했습니다.",
        source_rows=case_scope,
        limitation="SK리츠 전체 자산의 총 보유세 또는 다른 상장리츠에 자동 적용한 결과가 아닙니다.",
        expanded=True,
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
    _render_stage(
        3,
        "Ownership & Taxpayer Structure",
        conclusion=GOLDEN_OWNERSHIP_DISPLAY,
        legal_basis=_rule_rows(case.rules, ["property_tax_obligor"]),
        requirements=[
            "투자 보유형태와 등기 명의를 구분",
            "신탁재산의 위탁자·수탁자 확인",
            "과세기준일 현재 재산세 납세의무자 확인",
        ],
        source_rows=ownership,
        limitation="2026년 6월 1일 현재 등기부등본·신탁원부 원문 대사는 미완료입니다.",
    )

    eligibility = taxpayers[
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
    _render_stage(
        4,
        "Public REIT Separate-Tax Eligibility",
        conclusion="공개자료와 현행 법령상 분리과세 적격성은 충족 판단이지만 실제 고지 과세구분은 미확인입니다.",
        legal_basis=_rule_rows(case.rules, ["public_reit_land_separation"]),
        requirements=[
            "공모부동산투자회사 법적 요건",
            "목적사업 직접 사용",
            "비주거 토지",
            "과세기준일 소유관계",
        ],
        source_rows=eligibility,
        limitation="실제 재산세 과세내역서의 분리과세 코드를 확인한 verified_notice가 아닙니다.",
    )

    official_values = pd.DataFrame(
        [
            {
                "구분": "주소·PNU",
                "공식 입력값": f"{assets.iloc[0]['road_address']} / {parcels.iloc[0]['pnu']}",
                "기준": "현행 공식 주소·토지대장",
                "출처": parcels.iloc[0]["source_url"],
            },
            {
                "구분": "토지",
                "공식 입력값": f"{parcels.iloc[0]['individual_land_price_per_m2']:,.0f}원/㎡ × {parcels.iloc[0]['taxable_area_m2']:,.1f}㎡",
                "기준": "2026년 개별공시지가·현행 면적",
                "출처": parcels.iloc[0]["source_url"],
            },
            {
                "구분": "건축물",
                "공식 입력값": f"{buildings.iloc[0]['building_standard_value']:,.0f}원",
                "기준": "2026년 주택 외 건물 시가표준액",
                "출처": buildings.iloc[0]["source_url"],
            },
        ]
    )
    _render_stage(
        5,
        "Address·PNU·Official Values",
        conclusion="주소, 19자리 PNU, 현행 토지면적, 개별공시지가와 건축물 시가표준액을 단일 자산에 연결했습니다.",
        source_rows=official_values,
        limitation="건축물대장 대지면적과 현행 토지대장 면적의 5.3㎡ 차이는 별도 Reconciliation 항목입니다.",
    )

    land_rows = calculations[
        calculations["tax_name"].isin(["토지 시가표준액", "토지 재산세"])
    ]
    _render_stage(
        6,
        "Land Property Tax",
        conclusion="현행 유효 PNU의 토지 시가표준액과 분리과세 토지 재산세를 공식 산식으로 재계산했습니다.",
        legal_basis=_rule_rows(case.rules, ["property_tax_land_separated"]),
        formula=(
            "토지 시가표준액 = 개별공시지가 × 과세면적 × 소유지분\n"
            "토지 재산세 = 토지 시가표준액 × 공정시장가액비율 × 분리과세 세율"
        ),
        calculation_rows=land_rows,
        limitation="법정 절사, 감면, 세부담상한과 실제 고지 과세구분은 반영하지 않았습니다.",
    )

    building_rows = calculations[calculations["tax_name"].eq("건축물 재산세")]
    _render_stage(
        7,
        "Building Property Tax",
        conclusion="ETAX 주택 외 건물 시가표준액에 Tax Rule Master의 70%와 일반 건축물 세율을 적용했습니다.",
        legal_basis=_rule_rows(case.rules, ["property_tax_building_general"]),
        formula="건축물 재산세 = 공식 건축물 시가표준액 × 공정시장가액비율 × 일반 건축물 세율",
        calculation_rows=building_rows,
        limitation="ETAX 조회값은 시가표준액이며 실제 재산세 과세표준 또는 고지세액이 아닙니다.",
    )

    local_rows = calculations[
        calculations["tax_name"].isin(["재산세 도시지역분", "지방교육세"])
    ]
    _render_stage(
        8,
        "Urban Area·Local Education Tax",
        conclusion="토지와 건축물의 도시지역분 및 지방교육세를 각 본세와 과세표준에 연결했습니다.",
        legal_basis=_rule_rows(case.rules, ["urban_area_tax_standard", "local_education_tax"]),
        formula=(
            "도시지역분 = 재산세 과세표준 × 적용 세율\n"
            "지방교육세 = 재산세 본세(도시지역분 제외) × 지방교육세율"
        ),
        calculation_rows=local_rows,
        limitation="지방자치단체 조례와 실제 고지서상 절사·조정 내역은 미대사입니다.",
    )

    fire_rows = calculations[
        calculations["tax_name"].eq("소방분 지역자원시설세")
    ]
    _render_stage(
        9,
        "Fire Resource Facility Tax",
        conclusion="업무시설·지상 36층 공식자료와 법정 대형 화재위험 요건을 연결해 300% 배율을 적용했습니다.",
        legal_basis=_rule_rows(
            case.rules,
            ["fire_resource_tax", "fire_multiplier_300"],
        ),
        formula="소방분 = 건축물 시가표준액 누진세액 × 법정 300% 배율",
        calculation_rows=fire_rows,
        limitation="실제 고지내역의 위험유형 코드와 300% 배율 대사는 미완료입니다.",
    )

    comprehensive_rows = calculations[
        calculations["tax_name"].isin(
            ["토지분 종합부동산세", "종합부동산세분 농어촌특별세"]
        )
    ]
    _render_stage(
        10,
        "Comprehensive Real Estate Holding Tax",
        conclusion="법정 분리과세 판단을 고정한 민감도 경로에서는 토지분 종합부동산세와 농어촌특별세를 해당 없음으로 유지합니다.",
        legal_basis=_rule_rows(
            case.rules,
            [
                "comprehensive_land_aggregate",
                "comprehensive_land_separate_aggregate",
                "rural_special_tax",
            ],
        ),
        calculation_rows=comprehensive_rows,
        limitation="실제 고지 과세구분이 확인되지 않았으므로 종부세 제외의 실제 적용은 미대사 상태입니다.",
    )

    _render_stage(
        11,
        "Total Statutory Recalculation",
        conclusion=(
            f"{GOLDEN_RECALCULATION_LABEL}은 {base_total:,}원({_format_eok(base_total)})입니다."
        ),
        calculation_rows=verified_rows,
        limitation="실제 고지세액이 아니며 법정 절사·감면·세부담상한·과세관청 조정을 반영하지 않았습니다.",
        expanded=True,
    )

    st.markdown("### 12. Tax Sensitivity Scenario")
    s1, s2 = st.columns(2)
    custom_land_change = s1.slider(
        "Custom 토지 개별공시지가 변동",
        min_value=-10,
        max_value=20,
        value=0,
        step=1,
        format="%d%%",
    )
    custom_building_change = s2.slider(
        "Custom 건축물 시가표준액 변동",
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
    sensitivity_display = _scenario_display(sensitivity_summary)
    st.dataframe(
        sensitivity_display,
        hide_index=True,
        width="stretch",
        height=250,
        column_config={
            column: st.column_config.NumberColumn(column, format="%,.0f원")
            for column in [
                "토지 시가표준액",
                "건축물 시가표준액",
                "토지 관련 세액",
                "건축물 관련 세액",
                "소방분",
                "총 보유세",
                "Base 대비 증감액",
            ]
        }
        | {
            "Base 대비 증감률": st.column_config.NumberColumn(
                "Base 대비 증감률",
                format="%.2f%%",
            )
        },
    )
    with st.expander("세목별 Breakdown", expanded=False):
        breakdown_display = sensitivity_breakdown.copy()
        breakdown_display["계산세액"] = pd.to_numeric(
            breakdown_display["계산세액"],
            errors="coerce",
        )
        _render_frame(breakdown_display, height=410)
    st.warning(
        "본 시나리오는 공시가격 및 시가표준액 변화에 대한 기계적 민감도 분석이며, "
        "미래 세액 예측이나 과세관청의 결정세액이 아닙니다."
    )

    st.markdown("### 13. Tax Issue Matrix")
    k1, k2, k3 = st.columns(3)
    k1.metric("P0 Open", kpis["p0_open"])
    k2.metric("P1 Open", kpis["p1_open"])
    k3.metric("계산 완료 세목", kpis["completed_tax_items"])
    k4, k5, k6 = st.columns(3)
    k4.metric("미대사 항목", kpis["unreconciled_items"])
    k5.metric("실제 고지서 Coverage", kpis["notice_coverage"])
    k6.metric("공식 입력 Evidence Coverage", kpis["evidence_coverage"])
    st.dataframe(
        _issue_style(issue_matrix),
        hide_index=True,
        width="stretch",
        height=360,
    )
    st.caption("Priority와 Open/Resolved 상태를 기준으로 표시하며 숫자의 크기만으로 위험도를 단정하지 않습니다.")

    st.markdown("### 14. Request List")
    _render_frame(request_list, height=330)

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
    st.markdown("### 15. Tax Review Memo")
    with st.expander("Memo 전문 보기", expanded=False):
        st.markdown(memo)

    st.markdown("### 16. Evidence & Limitations")
    _render_frame(reconciliation, height=230)
    with st.expander("Source Evidence Matrix", expanded=False):
        _render_frame(evidence_matrix, height=410)
    st.warning(DISCLAIMER_KO)

    st.markdown("### 17. Downloads")
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

    d1, d2, d3, d4 = st.columns(4)
    d1.download_button(
        "계산내역 CSV",
        dataframe_csv_bytes(calculations),
        file_name=f"{safe_prefix}_calculation_detail.csv",
        mime="text/csv",
        width="stretch",
    )
    d2.download_button(
        "Scenario CSV",
        dataframe_csv_bytes(sensitivity_summary),
        file_name=f"{safe_prefix}_sensitivity.csv",
        mime="text/csv",
        width="stretch",
    )
    d3.download_button(
        "Issue Matrix CSV",
        dataframe_csv_bytes(issue_matrix),
        file_name=f"{safe_prefix}_tax_issue_matrix.csv",
        mime="text/csv",
        width="stretch",
    )
    d4.download_button(
        "Request List CSV",
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
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=not excel_available,
        width="stretch",
    )
    d6.download_button(
        "Memo Markdown",
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
        st.caption("Excel 내보내기 패키지를 설치하면 검토팩 Excel 다운로드가 활성화됩니다.")
