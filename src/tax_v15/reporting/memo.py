from __future__ import annotations

from decimal import Decimal

import pandas as pd

from ..constants import DISCLAIMER_KO, SOURCE_BADGES
from ..validation.controls import summarize_coverage


SECTIONS = [
    "검토 결론",
    "검토대상 및 한계",
    "공모부동산투자회사 법적 지위",
    "소유·신탁 구조 및 재산세 납세의무자",
    "목적사업용 토지의 분리과세 적용요건",
    "토지분 재산세",
    "건축물분 재산세",
    "재산세 도시지역분 및 지방교육세",
    "소방분 지역자원시설세",
    "토지분 종합부동산세 및 농어촌특별세",
    "세목별 끝수 처리",
    "보유세 민감도 분석",
    "주요 세무쟁점",
    "추가 요청자료 목록",
    "고지세액 대사",
    "검토자 서명",
]

PUBLIC_STATUS_LABELS = {
    "eligible_separated_public_reit": "분리과세 적용요건 충족 판단",
    "unverified": "미확인",
    "statutory_basis_reviewed_registry_and_notice_open": (
        "법령 검토 완료·등기 및 과세내역 확인 필요"
    ),
    "not_reconciled": "미대사",
}


def _calculated_tax_rows(calculations: pd.DataFrame) -> pd.DataFrame:
    if calculations is None or calculations.empty:
        return pd.DataFrame()
    return calculations[
        calculations["calculation_status"].isin(
            ["verified_notice", "official_source_calculated"]
        )
        & calculations["tax_name"].ne("토지 시가표준액")
    ].copy()


def _decimal_total(frame: pd.DataFrame, column: str) -> Decimal | None:
    if frame is None or frame.empty or column not in frame.columns:
        return None
    values = frame[column].dropna()
    if values.empty:
        return None
    return sum((Decimal(str(value)) for value in values), Decimal("0"))


def _status_summary(frame: pd.DataFrame, column: str, fallback: str) -> str:
    if frame is None or frame.empty or column not in frame.columns:
        return fallback
    values = sorted(
        {
            PUBLIC_STATUS_LABELS.get(str(value).strip(), str(value).strip())
            for value in frame[column]
            if not pd.isna(value) and str(value).strip()
        }
    )
    return ", ".join(values) if values else fallback


def _markdown_value(value) -> str:
    if value is None or value is pd.NA:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = _format_decimal(value) if isinstance(value, Decimal) else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _format_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    whole, dot, fraction = text.partition(".")
    return f"{int(whole):,}{dot}{fraction}"


def _markdown_table(frame: pd.DataFrame | None, columns: list[str]) -> str:
    if frame is None or frame.empty:
        return "- 현재 표시할 행이 없습니다."
    available = [column for column in columns if column in frame.columns]
    if not available:
        return "- 현재 표시할 열이 없습니다."
    lines = [
        "| " + " | ".join(available) + " |",
        "|" + "|".join("---" for _ in available) + "|",
    ]
    for row in frame[available].itertuples(index=False, name=None):
        lines.append("| " + " | ".join(_markdown_value(value) for value in row) + " |")
    return "\n".join(lines)


def _end_digit_table(calculations: pd.DataFrame) -> pd.DataFrame:
    rows = calculations[
        calculations["end_digit_treatment_method"].fillna("").astype(str).ne("")
    ].copy()
    result = rows[
        [
            "tax_name",
            "calculated_tax_before_end_digit_treatment",
            "end_digit_treatment_unit",
            "end_digit_treatment_method",
            "calculated_tax_after_end_digit_treatment",
            "end_digit_treatment_difference",
        ]
    ].copy()

    def tax_line_label(row: pd.Series) -> str:
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

    result["tax_name"] = rows.apply(tax_line_label, axis=1)
    return result.rename(
        columns={
            "tax_name": "세목",
            "calculated_tax_before_end_digit_treatment": "끝수 처리 전 산출세액",
            "end_digit_treatment_unit": "끝수 처리 단위",
            "end_digit_treatment_method": "끝수 처리 방법",
            "calculated_tax_after_end_digit_treatment": "끝수 처리 후 재계산액",
            "end_digit_treatment_difference": "끝수 처리 차이",
        }
    )


def _issue_table(issue_matrix: pd.DataFrame | None) -> pd.DataFrame | None:
    if issue_matrix is None or issue_matrix.empty:
        return issue_matrix
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


def _request_table(requests: pd.DataFrame | None) -> pd.DataFrame | None:
    if requests is None or requests.empty:
        return requests
    request_document_column = (
        "required_document"
        if "required_document" in requests.columns
        else "request_document"
    )
    request_issue_column = "tax_issue" if "tax_issue" in requests.columns else "issue"
    result = requests[
        [
            "priority",
            request_issue_column,
            request_document_column,
            "request_reason",
            "reviewer_status",
        ]
    ].copy()
    result["reviewer_status"] = result["reviewer_status"].replace(
        {"open": "미검토", "reviewed": "검토 완료"}
    )
    return result.rename(
        columns={
            "priority": "우선순위",
            request_issue_column: "주요 세무쟁점",
            request_document_column: "추가 요청자료",
            "request_reason": "요청 사유",
            "reviewer_status": "검토 상태",
        }
    )


def build_tax_review_memo(
    reit_name: str,
    tax_year: int,
    assets: pd.DataFrame,
    parcels: pd.DataFrame,
    buildings: pd.DataFrame,
    taxpayers: pd.DataFrame,
    calculations: pd.DataFrame,
    validations: pd.DataFrame,
    requests: pd.DataFrame,
    sensitivity_summary: pd.DataFrame | None = None,
    issue_matrix: pd.DataFrame | None = None,
) -> str:
    del validations
    coverage = summarize_coverage(
        assets,
        parcels,
        buildings,
        taxpayers,
        calculations,
    )
    tax_rows = _calculated_tax_rows(calculations)
    before_total = _decimal_total(
        tax_rows,
        "calculated_tax_before_end_digit_treatment",
    )
    after_total = _decimal_total(tax_rows, "calculated_tax")
    completed = int(coverage["completed_calculation_rows"])
    blocked = int(coverage["blocked_calculation_rows"])
    statutory_status = _status_summary(
        taxpayers,
        "statutory_eligibility_status",
        "미판정",
    )
    notice_status = _status_summary(
        taxpayers,
        "actual_notice_classification",
        "미확인",
    )
    legal_status = _status_summary(taxpayers, "legal_review_status", "검토 필요")
    reconciliation_status = _status_summary(
        taxpayers,
        "notice_reconciliation_status",
        "미대사",
    )
    asset_name = (
        str(assets.iloc[0].get("asset_name", ""))
        if assets is not None and not assets.empty
        else "분석대상 자산"
    )
    conclusion = (
        "공개자료와 현행 법령에 따른 검토 결과, "
        f"{reit_name}가 위탁자이자 재산세 납세의무자인 {asset_name}의 토지는 "
        "공모부동산투자회사의 목적사업용 토지로서 분리과세 적용요건을 충족하는 "
        "것으로 판단됩니다. 이에 따라 해당 토지는 토지분 종합부동산세의 "
        "과세대상에서 제외되는 것으로 분석했습니다. "
        + (
            f"{tax_year}년 공식 과세기초자료와 확인된 법정 산식에 따른 "
            "보유세 재계산액은 "
            f"{after_total:,}원입니다. "
            if after_total is not None
            else "공개자료만으로 재계산할 수 있는 보유세 금액은 없습니다. "
        )
        + "다만 실제 고지세액이 아니며, 과세내역서상 분리과세 코드, 감면, "
        "세부담상한, 지방자치단체 조정과 소방분 위험유형 코드 대사는 미완료입니다."
    )
    scenario_text = (
        "개별공시지가 및 건축물 시가표준액의 기계적 변동을 가정한 분석이며, "
        "미래 결정세액 또는 과세관청의 고지세액 예측이 아닙니다. 각 세목에는 "
        "지방회계법 제55조에 따른 10원 미만 끝수 미계산 기준을 적용했습니다.\n\n"
        + _markdown_table(
            sensitivity_summary,
            [
                "민감도 분석",
                "토지 개별공시지가 변동률",
                "건축물 시가표준액 변동률",
                "끝수 처리 전 합계",
                "끝수 처리 후 합계",
                "기준 대비 증감액",
                "기준 대비 증감률",
            ],
        )
    )
    issue_text = _markdown_table(
        _issue_table(issue_matrix),
        [
            "우선순위",
            "주요 세무쟁점",
            "검증근거 상태",
            "잠재 세무영향",
            "정량 영향",
            "추가 필요자료",
            "조치 상태",
        ],
    )
    request_text = _markdown_table(
        _request_table(requests),
        [
            "우선순위",
            "주요 세무쟁점",
            "추가 요청자료",
            "요청 사유",
            "검토 상태",
        ],
    )
    end_digit_text = (
        "본 분석에서는 지방회계법 제55조에 따른 10원 미만 끝수 미계산 기준을 "
        "세율·배율 적용 후 각 세목의 산출세액에 적용했습니다. 지방회계법 시행령 "
        "제67조의 분할 징수·수납 예외와 실제 과세관청의 처리 방식은 과세내역서로 "
        "추가 확인해야 합니다. 시가표준액, 재산세 과세표준, 세율, 배율 및 "
        "과세대상 제외·해당 없음 행에는 적용하지 않았습니다.\n\n"
        + _markdown_table(
            _end_digit_table(calculations),
            [
                "세목",
                "끝수 처리 전 산출세액",
                "끝수 처리 단위",
                "끝수 처리 방법",
                "끝수 처리 후 재계산액",
                "끝수 처리 차이",
            ],
        )
    )
    section_text = {
        "검토 결론": conclusion,
        "검토대상 및 한계": (
            f"본 Tax 모듈은 {reit_name} 전체 자산의 확정 세액을 산출하는 도구가 "
            f"아니라, 핵심 분석대상인 {asset_name}을 대상으로 공개자료 기반의 "
            f"단일 자산 보유세 검토 흐름을 구현합니다.\n\n{DISCLAIMER_KO}"
        ),
        "공모부동산투자회사 법적 지위": (
            "공식 투자보고서상 공모 의무와 공모 실시 사실을 부동산투자회사법상 "
            "요건과 연결했습니다. 최신 영업인가·등록 상태는 별도 확인이 필요합니다."
        ),
        "소유·신탁 구조 및 재산세 납세의무자": (
            f"자산 {coverage['asset_count']}건 중 공개자료와 지방세법 제107조를 "
            f"연결해 재산세 납세의무자를 판정한 행은 "
            f"{coverage['verified_taxpayer_count']}건입니다. 투자 보유형태, 등기 명의, "
            "위탁자·수탁자, 경제적 보유주체와 재산세 납세의무자를 구분합니다."
        ),
        "목적사업용 토지의 분리과세 적용요건": (
            f"법정 적용요건 상태는 {statutory_status}, 실제 고지 재산세 과세구분은 "
            f"{notice_status}, 법률 검토 상태는 {legal_status}입니다. 분리과세 판단은 "
            "토지에만 적용하며 건축물분 재산세, 재산세 도시지역분, 지방교육세와 "
            "소방분 지역자원시설세는 각각 별도로 과세합니다."
        ),
        "토지분 재산세": (
            "필지별 개별공시지가 × 과세면적 × 소유지분으로 토지 시가표준액을 "
            "계산하고 공정시장가액비율과 분리과세 토지 표준세율을 적용했습니다."
        ),
        "건축물분 재산세": (
            f"공식 건축물 시가표준액 확인 건은 "
            f"{coverage['verified_building_value_count']}건입니다. 시가표준액, 재산세 "
            "과세표준과 끝수 처리 전·후 산출세액을 구분합니다."
        ),
        "재산세 도시지역분 및 지방교육세": (
            "재산세 도시지역분은 확인된 적용대상과 과세표준을 기준으로 계산하고, "
            "지방교육세는 도시지역분을 제외한 재산세 본세를 기준으로 계산했습니다."
        ),
        "소방분 지역자원시설세": (
            "업무시설·지상 36층이라는 공개자료와 지방세법 시행령 제138조를 "
            "연결하여 법정 요건상 대형 화재위험 건축물 해당 판단에 따른 300% "
            "배율을 적용했습니다. 실제 고지서상 위험유형 코드는 미확인이고 대사 "
            "상태는 미대사입니다."
        ),
        "토지분 종합부동산세 및 농어촌특별세": (
            "토지분 종합부동산세: 과세대상 제외. 분리과세대상 토지는 토지분 "
            "종합부동산세의 종합합산·별도합산 과세대상에 포함되지 않으므로 계산상 "
            "세액을 0원으로 처리합니다. 종합부동산세분 농어촌특별세: 해당 없음. "
            "과세대상 제외는 감면·면제와 구분합니다."
        ),
        "세목별 끝수 처리": end_digit_text,
        "보유세 민감도 분석": scenario_text,
        "주요 세무쟁점": issue_text,
        "추가 요청자료 목록": request_text,
        "고지세액 대사": (
            f"고지세액 대사 상태는 {reconciliation_status}입니다. 실제 고지세액은 "
            "과세내역서 미확보로 확인하지 못했습니다. 세금과공과 전체를 보유세 "
            "검증값으로 사용하지 않으며 실제 고지서 또는 과세내역서와 세목별로 "
            "대사해야 합니다."
        ),
        "검토자 서명": (
            "검토자: ____________________  검토일: ____________________  "
            "승인: ____________________"
        ),
    }
    before_label = (
        f"{_format_decimal(before_total)}원"
        if before_total is not None
        else "재계산 불가"
    )
    after_label = (
        f"{_format_decimal(after_total)}원"
        if after_total is not None
        else "재계산 불가"
    )
    lines = [
        f"# {reit_name} - {asset_name} {tax_year}년 보유세 세무검토 메모",
        "",
        f"계산 상태: {SOURCE_BADGES.get(coverage['final_status'], coverage['final_status'])}",
        f"재계산 가능 세목: {completed}건 / 추가자료 필요 행: {blocked}건",
        f"끝수 처리 전 산식상 산출세액: {before_label}",
        f"끝수 처리 후 보유세 재계산액: {after_label}",
        "실제 고지세액: 과세내역서 미확보",
        "고지세액 대사 상태: 미대사",
        "",
    ]
    for number, title in enumerate(SECTIONS, start=1):
        lines.extend([f"## {number}. {title}", "", section_text[title], ""])
    return "\n".join(lines).strip() + "\n"
