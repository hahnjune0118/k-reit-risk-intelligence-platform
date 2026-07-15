from __future__ import annotations

from decimal import Decimal

import pandas as pd
import streamlit as st

from src.tax_v15.case_study import (
    CORE_RECALCULATION_AFTER_END_DIGIT_TREATMENT,
    CORE_RECALCULATION_BEFORE_END_DIGIT_TREATMENT,
    build_case_kpis,
    build_case_request_list,
    build_sensitivity_scenarios,
    build_tax_issue_matrix,
    select_core_asset_tax_case,
)
from src.tax_v15.constants import DISCLAIMER_KO, PROJECT_ROOT, SOURCE_BADGES
from src.tax_v15.loaders import load_v15_bundle
from src.tax_v15.reporting import (
    build_tax_review_memo,
    dataframe_csv_bytes,
    review_document_html,
    review_pack_excel_bytes,
)


CORE_RECALCULATION_LABEL = (
    "2026년 공식 과세기초자료와 확인된 법정 산식에 따른 보유세 재계산액"
)
CORE_OWNERSHIP_DISPLAY = (
    "SK리츠가 위탁자이자 재산세 납세의무자인 신탁보유 오피스 자산"
)
EVIDENCE_MATRIX_PATH = (
    PROJECT_ROOT
    / "docs"
    / "v15"
    / "golden_asset"
    / "SK_SEORIN_EVIDENCE_MATRIX.csv"
)

PUBLIC_VALUE_LABELS = {
    "direct_real_estate_investment": "직접 부동산 투자",
    "trustee_registered_trust_property": "수탁자 명의 신탁재산",
    "separated_public_reit": "공모부동산투자회사 목적사업용 토지 분리과세",
    "eligible_separated_public_reit": "분리과세 적용요건 충족 판단",
    "unverified": "미확인",
    "statutory_basis_reviewed_registry_and_notice_open": (
        "법령 검토 완료·등기 및 과세내역 확인 필요"
    ),
    "not_reconciled": "미대사",
    "not_reflected": "미반영",
    "open": "미검토",
    "reviewed": "검토 완료",
    "parcel": "필지",
    "building": "건축물",
    "taxpayer": "납세의무자",
}


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


def _public_value(value):
    if value is None or value is pd.NA:
        return value
    return PUBLIC_VALUE_LABELS.get(str(value), value)


def _decimal_sum(frame: pd.DataFrame, column: str) -> Decimal:
    total = Decimal("0")
    if frame is None or frame.empty or column not in frame.columns:
        return total
    for value in frame[column]:
        if pd.isna(value):
            continue
        total += Decimal(str(value))
    return total


def _decimal_tax_total(frame: pd.DataFrame) -> Decimal | None:
    if frame is None or frame.empty:
        return None
    return _decimal_sum(frame, "calculated_tax")


def _format_eok(value: Decimal) -> str:
    return f"약 {value / Decimal('100000000'):.2f}억원"


def _format_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    whole, dot, fraction = text.partition(".")
    return f"{int(whole):,}{dot}{fraction}"


def _tax_line_label(row: pd.Series) -> str:
    tax_name = str(row.get("tax_name", ""))
    if tax_name == "토지 재산세":
        return "토지분 재산세"
    if tax_name == "건축물 재산세":
        return "건축물분 재산세"
    if tax_name in {"재산세 도시지역분", "지방교육세"}:
        if str(row.get("parcel_id", "")).strip():
            return f"토지분 {tax_name}"
        if str(row.get("building_id", "")).strip():
            return f"건축물분 {tax_name}"
    return tax_name


def _display_calculations(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "tax_name",
        "tax_classification",
        "official_value",
        "tax_base",
        "tax_rate",
        "multiplier",
        "calculated_tax_before_end_digit_treatment",
        "calculated_tax_after_end_digit_treatment",
        "end_digit_treatment_difference",
        "calculation_status",
        "formula_text",
        "article",
        "source_url",
    ]
    display_columns = [
        "세목",
        "재산세 과세구분",
        "공식 과세기초가액(원)",
        "재산세 과세표준(원)",
        "세율",
        "배율",
        "끝수 처리 전 산출세액(원)",
        "끝수 처리 후 재계산액(원)",
        "끝수 처리 차이(원)",
        "검증 상태",
        "계산식",
        "법적 근거",
        "출처",
    ]
    if frame is None or frame.empty:
        return pd.DataFrame(columns=display_columns)
    result = frame[columns].copy()
    result["tax_name"] = frame.apply(_tax_line_label, axis=1)
    result["tax_classification"] = result["tax_classification"].map(_public_value)
    result["calculation_status"] = result["calculation_status"].map(
        lambda value: _status_label(str(value))
    )
    result.columns = display_columns
    return result


def _calculation_export_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return _display_calculations(frame).rename(
        columns={"출처": "과세근거자료 URL"}
    )


def _render_frame(frame: pd.DataFrame, *, height: int = 230) -> None:
    if frame is None or frame.empty:
        st.info("현재 공개자료에서 확인 가능한 행이 없습니다. 검증되지 않은 값은 계산하지 않습니다.")
        return
    config = {}
    for column in ["출처", "source_url", "공식 홈페이지", "과세근거자료 URL"]:
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
    result = selected[columns].drop_duplicates()
    result["tax_classification"] = result["tax_classification"].map(_public_value)
    return result.rename(
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
        st.markdown("**검토 결론**")
        st.write(conclusion)
        if legal_basis is not None and not legal_basis.empty:
            st.markdown("**적용 법규와 근거**")
            _render_frame(legal_basis, height=min(270, 80 + len(legal_basis) * 35))
        if requirements:
            st.markdown("**적용요건**")
            for item in requirements:
                st.write(f"- {item}")
        if formula:
            st.markdown("**계산 공식**")
            st.code(formula, language="text")
        if calculation_rows is not None:
            st.markdown("**공식 숫자 대입 및 산출 결과**")
            _render_frame(_display_calculations(calculation_rows), height=290)
        if source_rows is not None:
            st.markdown("**과세근거자료**")
            _render_frame(source_rows, height=260)
        if limitation:
            st.markdown("**검토 한계 및 추가 확인사항**")
            st.warning(limitation)


def _eligibility_comparison(assets: pd.DataFrame, taxpayers: pd.DataFrame) -> pd.DataFrame:
    asset = assets.iloc[0]
    taxpayer = taxpayers.iloc[0]
    report_url = _safe_text(asset.get("source_url"), "")
    return pd.DataFrame(
        [
            {
                "법정 요건": "공모부동산투자회사 해당 여부",
                "확인된 사실관계": "공식 투자보고서상 공모 의무·공모 실시 확인",
                "과세근거자료": report_url,
                "검토 판단": "공개자료 기준 충족 판단",
                "실제 고지 확인": "해당 없음",
                "추가 필요자료": "최신 영업인가·등록 상태 확인자료",
            },
            {
                "법정 요건": "목적사업용 토지 해당 여부",
                "확인된 사실관계": _safe_text(taxpayer.get("purpose_business_use")),
                "과세근거자료": report_url,
                "검토 판단": "공개자료 기준 충족 판단",
                "실제 고지 확인": "과세내역서 대사 필요",
                "추가 필요자료": "자산 운영현황 및 실제 사용 증빙",
            },
            {
                "법정 요건": "2026년 6월 1일 현재 소유관계",
                "확인된 사실관계": "공시 연속성으로 소유관계를 추정하되 등기 원문 미대사",
                "과세근거자료": report_url,
                "검토 판단": "부분 확인",
                "실제 고지 확인": "과세내역서 대사 필요",
                "추가 필요자료": "2026년 6월 1일 현재 등기부등본",
            },
            {
                "법정 요건": "신탁재산의 위탁자·수탁자",
                "확인된 사실관계": (
                    f"위탁자 {_safe_text(asset.get('trustor'))}, "
                    f"수탁자 {_safe_text(asset.get('trustee'))}"
                ),
                "과세근거자료": report_url,
                "검토 판단": "부분 확인",
                "실제 고지 확인": "과세내역서 대사 필요",
                "추가 필요자료": "신탁원부 및 신탁계약서",
            },
            {
                "법정 요건": "재산세 납세의무자",
                "확인된 사실관계": _safe_text(taxpayer.get("tax_obligor")),
                "과세근거자료": _safe_text(taxpayer.get("source_url"), ""),
                "검토 판단": "공개자료 기준 충족 판단",
                "실제 고지 확인": "과세내역서 대사 필요",
                "추가 필요자료": "재산세 과세내역서의 납세의무자 표시",
            },
            {
                "법정 요건": "비주거용 토지 여부",
                "확인된 사실관계": "업무시설 임대용 오피스 자산의 부속토지",
                "과세근거자료": report_url,
                "검토 판단": "공개자료 기준 충족 판단",
                "실제 고지 확인": "과세내역서 대사 필요",
                "추가 필요자료": "건축물대장 및 토지이용계획확인서 최신본",
            },
            {
                "법정 요건": "실제 과세내역서상 분리과세 코드",
                "확인된 사실관계": "과세내역서 미확보",
                "과세근거자료": "",
                "검토 판단": "미확인",
                "실제 고지 확인": "과세내역서 대사 필요",
                "추가 필요자료": "분리과세 코드가 표시된 2026년 과세내역서",
            },
            {
                "법정 요건": "지방자치단체 조례 및 감면 여부",
                "확인된 사실관계": "실제 적용 내역 미확인",
                "과세근거자료": "",
                "검토 판단": "미확인",
                "실제 고지 확인": "과세내역서 대사 필요",
                "추가 필요자료": "감면·세부담상한·지방자치단체 조정자료",
            },
        ]
    )


def _end_digit_table(calculations: pd.DataFrame) -> pd.DataFrame:
    applied = calculations[
        calculations["end_digit_treatment_method"].fillna("").astype(str).ne("")
    ].copy()
    columns = [
        "tax_name",
        "calculated_tax_before_end_digit_treatment",
        "end_digit_treatment_unit",
        "end_digit_treatment_method",
        "end_digit_treatment_legal_basis",
        "calculated_tax_after_end_digit_treatment",
        "end_digit_treatment_difference",
    ]
    result = applied[columns].copy()
    result["tax_name"] = applied.apply(_tax_line_label, axis=1)
    return result.rename(
        columns={
            "tax_name": "세목",
            "calculated_tax_before_end_digit_treatment": "끝수 처리 전 산출세액",
            "end_digit_treatment_unit": "끝수 처리 단위",
            "end_digit_treatment_method": "끝수 처리 방법",
            "end_digit_treatment_legal_basis": "끝수 처리 법적 근거",
            "calculated_tax_after_end_digit_treatment": "끝수 처리 후 재계산액",
            "end_digit_treatment_difference": "끝수 처리 차이",
        }
    )


def _issue_display(issue_matrix: pd.DataFrame) -> pd.DataFrame:
    result = issue_matrix[
        [
            "priority",
            "tax_issue",
            "evidence_status",
            "potential_tax_effect",
            "quantitative_sensitivity",
            "required_document",
            "resolution_status",
        ]
    ].copy()
    result["resolution_status"] = result["resolution_status"].replace(
        {"Open": "미해결", "Resolved": "조치 완료"}
    )
    result["evidence_status"] = result["evidence_status"].map(_public_value)
    return result.rename(
        columns={
            "priority": "우선순위",
            "tax_issue": "주요 세무쟁점",
            "evidence_status": "검증근거 상태",
            "potential_tax_effect": "잠재 세무영향",
            "quantitative_sensitivity": "정량 영향",
            "required_document": "추가 필요자료",
            "resolution_status": "조치 상태",
        }
    )


def _issue_style(frame: pd.DataFrame):
    def priority_color(value: str) -> str:
        if value == "P0":
            return "background-color: #f8d7da; color: #7a1620; font-weight: 700"
        if value == "P1":
            return "background-color: #fff3cd; color: #6c5200; font-weight: 700"
        return ""

    def status_color(value: str) -> str:
        if value == "미해결":
            return "background-color: #f1f3f5; color: #343a40; font-weight: 600"
        return "background-color: #d1e7dd; color: #0f5132; font-weight: 600"

    return frame.style.map(priority_color, subset=["우선순위"]).map(
        status_color,
        subset=["조치 상태"],
    )


def _request_display(request_list: pd.DataFrame) -> pd.DataFrame:
    result = request_list[
        [
            "priority",
            "tax_issue",
            "required_document",
            "request_reason",
            "reviewer_status",
            "resolution_status",
        ]
    ].copy()
    result["reviewer_status"] = result["reviewer_status"].replace(
        {"open": "미검토", "reviewed": "검토 완료"}
    )
    result["resolution_status"] = result["resolution_status"].replace(
        {"Open": "미해결", "Resolved": "조치 완료"}
    )
    return result.rename(
        columns={
            "priority": "우선순위",
            "tax_issue": "주요 세무쟁점",
            "required_document": "추가 요청자료",
            "request_reason": "요청 사유",
            "reviewer_status": "검토 상태",
            "resolution_status": "조치 상태",
        }
    )


def _reconciliation_display(frame: pd.DataFrame) -> pd.DataFrame:
    metric_labels = {
        "holding_tax_notice_reconciliation": "고지세액 대사",
        "parcel_area_register_to_building_ledger": "토지대장·건축물대장 면적 대사",
        "parcel_area_difference_tax_sensitivity": "면적 차이 세액 민감도",
        "building_value_component_reconciliation": "건축물 시가표준액 구성요소 대사",
    }
    result = frame.copy()
    result["metric"] = result["metric"].replace(metric_labels)
    result["reviewer_status"] = result["reviewer_status"].map(_public_value)
    columns = [
        "metric",
        "calculated_value",
        "disclosed_or_verified_value",
        "variance",
        "reconciliation_reason",
        "reviewer_status",
    ]
    return result[columns].rename(
        columns={
            "metric": "대사항목",
            "calculated_value": "재계산값",
            "disclosed_or_verified_value": "공시·검증값",
            "variance": "차이",
            "reconciliation_reason": "대사 설명",
            "reviewer_status": "검토 상태",
        }
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
        case = select_core_asset_tax_case(_load_tax_v15_data())
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
    tax_rows = calculations[
        calculations["calculation_status"].isin(
            ["verified_notice", "official_source_calculated"]
        )
        & calculations["tax_name"].ne("토지 시가표준액")
    ]
    before_total = _decimal_sum(
        tax_rows,
        "calculated_tax_before_end_digit_treatment",
    )
    after_total = _decimal_sum(tax_rows, "calculated_tax")
    if (
        before_total != CORE_RECALCULATION_BEFORE_END_DIGIT_TREATMENT
        or after_total != CORE_RECALCULATION_AFTER_END_DIGIT_TREATMENT
    ):
        st.error("SK서린빌딩 기준 재계산액이 검증된 끝수 처리 전·후 합계와 일치하지 않아 표시를 차단했습니다.")
        return

    st.markdown("## SK리츠 핵심 자산 보유세 세무검토")
    st.markdown("### SK서린빌딩")
    st.caption(
        "주소·필지고유번호(PNU)·시가표준액·신탁구조·재산세 납세의무자를 "
        "공식자료로 연결한 단일 자산 보유세 세무검토입니다."
    )

    st.markdown("### 1. 검토 결론")
    st.success(
        "공개자료와 현행 법령에 따른 검토 결과, SK리츠가 위탁자이자 재산세 "
        "납세의무자인 SK서린빌딩의 토지는 공모부동산투자회사의 목적사업용 "
        "토지로서 분리과세 적용요건을 충족하는 것으로 판단됩니다. 이에 따라 "
        "해당 토지는 토지분 종합부동산세의 과세대상에서 제외되는 것으로 "
        "분석하였습니다. 확인된 개별공시지가, 필지면적 및 건축물 시가표준액에 "
        "표준세율을 적용하고 지방회계법 제55조에 따른 10원 미만 끝수 미계산 "
        "기준을 반영한 2026년 보유세 재계산액은 1,250,710,930원입니다. 다만 "
        "실제 결정세액이나 고지세액이 아니며, 과세내역서, 과세기준일 현재 "
        "등기·신탁관계, 감면, 세부담상한, 지방자치단체 조정 및 소방분 "
        "위험유형 코드의 대사는 미완료입니다."
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "끝수 처리 후 보유세 재계산액",
        f"{_format_decimal(after_total)}원",
    )
    c2.metric(
        "끝수 처리 전 산식상 산출세액",
        f"{_format_decimal(before_total)}원",
    )
    c3.metric("실제 고지세액", "과세내역서 미확보")
    c4.metric("고지세액 대사 상태", "미대사")
    st.caption(
        "지방회계법 제55조에 따른 10원 미만 끝수 미계산 기준을 반영하였습니다. "
        "이는 실제 과세관청의 결정세액 또는 고지세액 검증 결과가 아닙니다."
    )

    case_scope = pd.DataFrame(
        [
            {"항목": "검토유형", "내용": "단일 자산 보유세 세무검토"},
            {"항목": "리츠", "내용": "SK리츠 (395400)"},
            {"항목": "자산", "내용": "SK서린빌딩"},
            {"항목": "기준연도", "내용": "2026년"},
            {"항목": "자료 범위", "내용": "공개자료 및 공식 과세기초자료"},
        ]
    )
    _render_stage(
        2,
        "검토대상 및 범위",
        conclusion="검토범위는 SK리츠의 SK서린빌딩 단일 자산과 2026년 기준연도로 고정했습니다.",
        source_rows=case_scope,
        limitation="SK리츠 전체 자산의 총 보유세 또는 다른 상장리츠에 자동 적용한 결과가 아닙니다.",
        expanded=True,
    )

    public_reit_status = pd.DataFrame(
        [
            {
                "검토항목": "공모부동산투자회사 해당 여부",
                "확인된 사실": "공식 투자보고서상 공모 의무·공모 실시 확인",
                "검토 판단": "공개자료 기준 충족 판단",
                "출처": assets.iloc[0]["source_url"],
            }
        ]
    )
    _render_stage(
        3,
        "공모부동산투자회사 법적 지위",
        conclusion="공식 투자보고서와 부동산투자회사법상 요건을 연결하여 공모부동산투자회사 해당 여부를 확인했습니다.",
        legal_basis=_rule_rows(case.rules, ["public_reit_definition"]),
        source_rows=public_reit_status,
        limitation="최신 영업인가·등록 상태는 별도 원문 확인이 필요합니다.",
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
    for column in ["투자 보유형태", "등기 보유형태"]:
        ownership[column] = ownership[column].map(_public_value)
    _render_stage(
        4,
        "소유·신탁 구조 및 재산세 납세의무자",
        conclusion=CORE_OWNERSHIP_DISPLAY,
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
            "statutory_eligibility_status": "법정 적용요건 충족 여부",
            "actual_notice_classification": "실제 고지 재산세 과세구분",
            "legal_review_status": "법률 검토 상태",
            "notice_reconciliation_status": "고지세액 대사 상태",
            "source_url": "출처",
        }
    )
    for column in [
        "법정 적용요건 충족 여부",
        "실제 고지 재산세 과세구분",
        "법률 검토 상태",
        "고지세액 대사 상태",
    ]:
        eligibility[column] = eligibility[column].map(_public_value)
    _render_stage(
        5,
        "공모부동산투자회사 목적사업용 토지의 분리과세 적용요건",
        conclusion=(
            "공개자료 기준 분리과세 적용요건은 충족 판단입니다. 이 판단은 토지에만 "
            "적용하며 건축물분 재산세, 재산세 도시지역분, 지방교육세와 소방분 "
            "지역자원시설세는 각각 별도로 과세합니다."
        ),
        legal_basis=_rule_rows(case.rules, ["public_reit_land_separation"]),
        requirements=[
            "공모부동산투자회사 법적 요건",
            "목적사업에 직접 사용하는 토지",
            "비주거용 토지",
            "과세기준일 현재 소유관계",
        ],
        source_rows=eligibility,
        limitation="실제 과세내역서의 분리과세 코드를 확인한 상태가 아닙니다.",
    )

    _render_stage(
        6,
        "법정 요건과 SK서린빌딩 사실관계 대조",
        conclusion="법정 요건, 공개자료상 사실관계와 실제 고지 확인 여부를 분리하여 검토했습니다.",
        source_rows=_eligibility_comparison(assets, taxpayers),
        limitation="실제 고지서가 없으므로 과세내역서 확인 완료 상태로 분류하지 않습니다.",
    )

    official_values = pd.DataFrame(
        [
            {
                "구분": "주소·PNU",
                "공식 과세기초자료": f"{assets.iloc[0]['road_address']} / {parcels.iloc[0]['pnu']}",
                "기준": "현행 공식 주소·토지대장",
                "출처": parcels.iloc[0]["source_url"],
            },
            {
                "구분": "토지",
                "공식 과세기초자료": f"{parcels.iloc[0]['individual_land_price_per_m2']:,.0f}원/㎡ × {parcels.iloc[0]['taxable_area_m2']:,.1f}㎡",
                "기준": "2026년 개별공시지가·현행 면적",
                "출처": parcels.iloc[0]["source_url"],
            },
            {
                "구분": "건축물",
                "공식 과세기초자료": f"{buildings.iloc[0]['building_standard_value']:,.0f}원",
                "기준": "2026년 주택 외 건물 시가표준액",
                "출처": buildings.iloc[0]["source_url"],
            },
        ]
    )
    _render_stage(
        7,
        "자산 소재지·필지고유번호(PNU) 및 공식 과세기초자료",
        conclusion="주소, 19자리 PNU, 현행 토지면적, 개별공시지가와 건축물 시가표준액을 단일 자산에 연결했습니다.",
        source_rows=official_values,
        limitation="건축물대장 대지면적과 현행 토지대장 면적의 5.3㎡ 차이는 별도 자료 대사항목입니다.",
    )

    land_rows = calculations[
        calculations["tax_name"].isin(["토지 시가표준액", "토지 재산세"])
    ]
    _render_stage(
        8,
        "토지 시가표준액 및 토지분 재산세",
        conclusion="현행 유효 PNU의 토지 시가표준액과 분리과세 토지분 재산세를 공식 산식으로 재계산했습니다.",
        legal_basis=_rule_rows(case.rules, ["property_tax_land_separated"]),
        formula=(
            "토지 시가표준액 = 개별공시지가 × 과세면적 × 소유지분\n"
            "토지분 재산세 = 토지 시가표준액 × 공정시장가액비율 × 분리과세 세율"
        ),
        calculation_rows=land_rows,
        limitation="감면, 세부담상한과 실제 고지 과세구분은 대사하지 않았습니다.",
    )

    building_rows = calculations[calculations["tax_name"].eq("건축물 재산세")]
    _render_stage(
        9,
        "건축물 시가표준액 및 건축물분 재산세",
        conclusion="공식 건축물 시가표준액에 공정시장가액비율과 일반 건축물 표준세율을 적용했습니다.",
        legal_basis=_rule_rows(case.rules, ["property_tax_building_general"]),
        formula="건축물분 재산세 = 공식 건축물 시가표준액 × 공정시장가액비율 × 일반 건축물 세율",
        calculation_rows=building_rows,
        limitation="조회값은 건축물 시가표준액이며 실제 재산세 과세표준 또는 고지세액이 아닙니다.",
    )

    local_rows = calculations[
        calculations["tax_name"].isin(["재산세 도시지역분", "지방교육세"])
    ]
    _render_stage(
        10,
        "재산세 도시지역분 및 지방교육세",
        conclusion="토지와 건축물의 재산세 도시지역분 및 지방교육세를 각 과세표준과 재산세 본세에 연결했습니다.",
        legal_basis=_rule_rows(case.rules, ["urban_area_tax_standard", "local_education_tax"]),
        formula=(
            "재산세 도시지역분 = 재산세 과세표준 × 적용 세율\n"
            "지방교육세 = 재산세 본세(도시지역분 제외) × 지방교육세율"
        ),
        calculation_rows=local_rows,
        limitation="지방자치단체 조례와 실제 고지서상 조정 내역은 미대사입니다.",
    )

    fire_rows = calculations[calculations["tax_name"].eq("소방분 지역자원시설세")]
    fire_status = pd.DataFrame(
        [
            {"검토항목": "법정 요건상 판단", "검토 결과": "업무시설·지상 36층에 따른 대형 화재위험 건축물 해당 판단"},
            {"검토항목": "분석 적용 배율", "검토 결과": "300%"},
            {"검토항목": "실제 고지서상 위험유형 코드", "검토 결과": "미확인"},
            {"검토항목": "대사 상태", "검토 결과": "미대사"},
        ]
    )
    _render_stage(
        11,
        "소방분 지역자원시설세",
        conclusion="법정 요건상 대형 화재위험 건축물 해당 판단에 따른 소방분 지역자원시설세 300% 배율을 적용했습니다.",
        legal_basis=_rule_rows(case.rules, ["fire_resource_tax", "fire_multiplier_300"]),
        formula="소방분 지역자원시설세 = 건축물 시가표준액 누진세액 × 법정 300% 배율",
        calculation_rows=fire_rows,
        source_rows=fire_status,
        limitation="실제 고지내역의 위험유형 코드와 300% 배율 적용 여부는 미대사입니다.",
    )

    comprehensive_status = pd.DataFrame(
        [
            {
                "세목": "토지분 종합부동산세",
                "검토 결과": "과세대상 제외",
                "보조 설명": "분리과세대상 토지는 종합합산·별도합산 과세대상에 포함되지 않아 계산상 세액을 0원으로 처리",
            },
            {
                "세목": "종합부동산세분 농어촌특별세",
                "검토 결과": "해당 없음",
                "보조 설명": "납부할 토지분 종합부동산세가 없음",
            },
        ]
    )
    _render_stage(
        12,
        "토지분 종합부동산세 및 농어촌특별세",
        conclusion="토지분 종합부동산세는 과세대상 제외, 종합부동산세분 농어촌특별세는 해당 없음으로 검토했습니다.",
        legal_basis=_rule_rows(
            case.rules,
            [
                "comprehensive_land_aggregate",
                "comprehensive_land_separate_aggregate",
                "rural_special_tax",
            ],
        ),
        source_rows=comprehensive_status,
        limitation="분리과세의 실제 고지 적용은 과세내역서 미확보로 대사하지 못했습니다. 과세대상 제외는 감면·면제와 구분합니다.",
    )

    _render_stage(
        13,
        "세목별 끝수 처리",
        conclusion="세율과 배율을 적용한 각 세목의 산출세액마다 10원 미만 끝수 미계산 기준을 적용한 후 합산했습니다.",
        formula="끝수 처리 후 재계산액 = (끝수 처리 전 산출세액 // 10원) × 10원",
        source_rows=_end_digit_table(calculations),
        limitation=(
            "본 분석에서는 지방회계법 제55조의 선택 규정에 따른 10원 미만 끝수 "
            "미계산 기준을 적용했습니다. 시행령 제67조의 분할 징수·수납 예외와 실제 "
            "과세관청의 처리 방식은 과세내역서로 추가 확인해야 합니다. 시가표준액, "
            "과세표준, 세율, 배율 및 과세대상 제외 행에는 적용하지 않았습니다."
        ),
        expanded=True,
    )

    _render_stage(
        14,
        "법정 산식에 따른 보유세 재계산",
        conclusion=(
            f"{CORE_RECALCULATION_LABEL}은 {_format_decimal(after_total)}원"
            f"({_format_eok(after_total)})입니다. "
            f"끝수 처리 전 산식상 산출세액은 {_format_decimal(before_total)}원이며 "
            f"끝수 처리 차이는 {_format_decimal(before_total - after_total)}원입니다."
        ),
        calculation_rows=tax_rows,
        limitation="실제 고지세액이 아니며 감면·세부담상한·지방자치단체 조정은 반영하지 않았습니다.",
        expanded=True,
    )

    st.markdown("### 15. 보유세 민감도 분석")
    s1, s2 = st.columns(2)
    custom_land_change = s1.slider(
        "사용자 설정 토지 개별공시지가 변동률",
        min_value=-10,
        max_value=20,
        value=0,
        step=1,
        format="%d%%",
    )
    custom_building_change = s2.slider(
        "사용자 설정 건축물 시가표준액 변동률",
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
    sensitivity_display = sensitivity_summary.copy()
    numeric_columns = [
        "토지 개별공시지가 변동률",
        "건축물 시가표준액 변동률",
        "끝수 처리 전 합계",
        "끝수 처리 후 합계",
        "기준 대비 증감액",
        "기준 대비 증감률",
    ]
    for column in numeric_columns:
        sensitivity_display[column] = pd.to_numeric(
            sensitivity_display[column], errors="coerce"
        )
    st.dataframe(
        sensitivity_display,
        hide_index=True,
        width="stretch",
        height=250,
        column_config={
            "토지 개별공시지가 변동률": st.column_config.NumberColumn(
                "토지 개별공시지가 변동률", format="%.0f%%"
            ),
            "건축물 시가표준액 변동률": st.column_config.NumberColumn(
                "건축물 시가표준액 변동률", format="%.0f%%"
            ),
            "끝수 처리 전 합계": st.column_config.NumberColumn(
                "끝수 처리 전 합계", format="%,.5f원"
            ),
            "끝수 처리 후 합계": st.column_config.NumberColumn(
                "끝수 처리 후 합계", format="%,.0f원"
            ),
            "기준 대비 증감액": st.column_config.NumberColumn(
                "기준 대비 증감액", format="%,.0f원"
            ),
            "기준 대비 증감률": st.column_config.NumberColumn(
                "기준 대비 증감률", format="%.2f%%"
            ),
        },
    )
    with st.expander("세목별 산출내역", expanded=False):
        breakdown_display = sensitivity_breakdown.copy()
        for column in [
            "끝수 처리 전 산출세액",
            "끝수 처리 후 재계산액",
            "끝수 처리 차이",
        ]:
            breakdown_display[column] = pd.to_numeric(
                breakdown_display[column], errors="coerce"
            )
        _render_frame(breakdown_display, height=410)
    st.warning(
        "본 민감도 분석은 개별공시지가 및 건축물 시가표준액의 기계적 변동을 "
        "가정한 분석이며, 미래 결정세액 또는 과세관청의 고지세액을 예측한 "
        "결과가 아닙니다. 각 세목에는 지방회계법 제55조에 따른 10원 미만 "
        "끝수 미계산 기준을 적용하였습니다."
    )

    st.markdown("### 16. 주요 세무쟁점 및 추가 확인사항")
    k1, k2, k3 = st.columns(3)
    k1.metric("P0 미해결", kpis["p0_open"])
    k2.metric("P1 미해결", kpis["p1_open"])
    k3.metric("재계산 가능 세목", kpis["completed_tax_items"])
    k4, k5, k6 = st.columns(3)
    k4.metric("미대사 항목", kpis["unreconciled_items"])
    k5.metric("실제 고지서 자료 확인 범위", kpis["notice_coverage"])
    k6.metric("공식 과세기초자료 확인 범위", kpis["evidence_coverage"])
    st.dataframe(
        _issue_style(_issue_display(issue_matrix)),
        hide_index=True,
        width="stretch",
        height=360,
    )
    st.caption("우선순위와 미해결·조치 완료 상태를 기준으로 표시하며 숫자의 크기만으로 위험도를 단정하지 않습니다.")

    st.markdown("### 17. 추가 요청자료 목록")
    request_display = _request_display(request_list)
    _render_frame(request_display, height=330)

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
    st.markdown("### 18. 보유세 세무검토 메모")
    with st.expander("메모 전문 보기", expanded=False):
        st.markdown(memo)

    st.markdown("### 19. 과세근거자료 및 검토 한계")
    _render_frame(_reconciliation_display(reconciliation), height=250)
    with st.expander("과세근거자료 목록", expanded=False):
        _render_frame(evidence_matrix, height=410)
    st.warning(DISCLAIMER_KO)

    st.markdown("### 20. 검토자료 내려받기")
    safe_prefix = "395400_SK서린빌딩_2026"
    calculation_export = _calculation_export_frame(calculations)
    try:
        excel_bytes = review_pack_excel_bytes(
            {
                "검토대상": case_scope,
                "과세기초자료": official_values,
                "소유신탁구조": ownership,
                "분리과세요건": _eligibility_comparison(assets, taxpayers),
                "세액계산": calculation_export,
                "끝수처리": _end_digit_table(calculations),
                "민감도분석": sensitivity_summary,
                "세목별민감도": sensitivity_breakdown,
                "주요세무쟁점": _issue_display(issue_matrix),
                "추가요청자료": request_display,
                "고지세액대사": _reconciliation_display(reconciliation),
                "과세근거자료": evidence_matrix,
            }
        )
        excel_available = True
    except (ImportError, ModuleNotFoundError):
        excel_bytes = b""
        excel_available = False

    d1, d2, d3, d4 = st.columns(4)
    d1.download_button(
        "보유세 계산내역 CSV",
        dataframe_csv_bytes(calculation_export),
        file_name=f"{safe_prefix}_보유세계산내역.csv",
        mime="text/csv",
        width="stretch",
    )
    d2.download_button(
        "보유세 민감도 CSV",
        dataframe_csv_bytes(sensitivity_summary),
        file_name=f"{safe_prefix}_보유세민감도분석.csv",
        mime="text/csv",
        width="stretch",
    )
    d3.download_button(
        "주요 세무쟁점 CSV",
        dataframe_csv_bytes(_issue_display(issue_matrix)),
        file_name=f"{safe_prefix}_주요세무쟁점.csv",
        mime="text/csv",
        width="stretch",
    )
    d4.download_button(
        "추가 요청자료 CSV",
        dataframe_csv_bytes(request_display),
        file_name=f"{safe_prefix}_추가요청자료.csv",
        mime="text/csv",
        width="stretch",
    )
    d5, d6, d7 = st.columns(3)
    d5.download_button(
        "세무검토팩 Excel",
        excel_bytes,
        file_name=f"{safe_prefix}_세무검토팩.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=not excel_available,
        width="stretch",
    )
    d6.download_button(
        "세무검토 메모",
        memo.encode("utf-8-sig"),
        file_name=f"{safe_prefix}_보유세세무검토.md",
        mime="text/markdown",
        width="stretch",
    )
    d7.download_button(
        "세무검토 문서",
        review_document_html("SK리츠 SK서린빌딩 보유세 세무검토", memo),
        file_name=f"{safe_prefix}_보유세세무검토.html",
        mime="text/html",
        width="stretch",
    )
    if not excel_available:
        st.caption("Excel 내보내기 패키지를 설치하면 세무검토팩 Excel 다운로드가 활성화됩니다.")
