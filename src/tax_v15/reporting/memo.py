from __future__ import annotations

from decimal import Decimal

import pandas as pd

from ..constants import DISCLAIMER_KO, SOURCE_BADGES
from ..validation.controls import summarize_coverage


SECTIONS = [
    "Executive Conclusion",
    "Scope and Limitation",
    "REIT Legal Status",
    "Ownership and Taxpayer Structure",
    "Asset and Parcel Coverage",
    "Public REIT Separate-Tax Eligibility",
    "Land Property Tax Calculation",
    "Building Property Tax Calculation",
    "Urban Area Tax and Local Education Tax",
    "Fire Resource Facility Tax",
    "Comprehensive Real Estate Holding Tax",
    "Rural Special Tax",
    "Total Tax Burden",
    "Reconciliation",
    "Key Tax Risks",
    "Additional Document Request List",
    "Reviewer Sign-off",
]


def _verified_total(calculations: pd.DataFrame) -> Decimal | None:
    if calculations is None or calculations.empty:
        return None
    eligible = calculations[
        calculations["calculation_status"].isin(["verified_notice", "official_source_calculated"])
        & calculations["tax_name"].ne("토지 시가표준액")
    ]
    values = eligible["calculated_tax"].dropna()
    if values.empty:
        return None
    return sum((Decimal(str(value)) for value in values), Decimal("0"))


def _status_summary(frame: pd.DataFrame, column: str, fallback: str) -> str:
    if frame is None or frame.empty or column not in frame.columns:
        return fallback
    values = sorted(
        {
            str(value).strip()
            for value in frame[column]
            if not pd.isna(value) and str(value).strip()
        }
    )
    return ", ".join(values) if values else fallback


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
) -> str:
    coverage = summarize_coverage(assets, parcels, buildings, taxpayers, calculations)
    verified_total = _verified_total(calculations)
    completed = int(coverage["completed_calculation_rows"])
    blocked = int(coverage["blocked_calculation_rows"])
    recalculation_label = f"{tax_year}년 공식 입력자료 기반 보유세 산식 재계산액"
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
    conclusion = (
        f"{reit_name}의 {tax_year}년 공개자료 기반 검토에서 산식 재계산 가능한 세목 행은 {completed}건, "
        f"추가자료가 필요한 행은 {blocked}건입니다. "
        + (
            f"{recalculation_label}은 {verified_total:,}원입니다. "
            if verified_total is not None
            else "공개자료만으로 산식 재계산할 수 있는 금액은 없습니다. "
        )
        + "이 금액은 법정 절사·세부담상한·감면·실제 고지세액 대사 전이며 "
        "신고·납부 목적 금액이 아닙니다."
    )
    section_text = {
        "Executive Conclusion": conclusion,
        "Scope and Limitation": DISCLAIMER_KO,
        "REIT Legal Status": "상장 여부와 공모부동산투자회사 요건은 서로 구분해 검토합니다. 상장 사실만으로 분리과세를 확정하지 않습니다.",
        "Ownership and Taxpayer Structure": (
            f"자산 {coverage['asset_count']}건 중 공개자료와 법령을 연결해 납세의무자를 "
            f"판정한 행은 {coverage['verified_taxpayer_count']}건입니다. 투자 보유형태, "
            "등기 보유형태, 등기명의자, 위탁자·수탁자, 경제적 보유주체와 "
            "재산세 납세의무자를 서로 구분합니다."
        ),
        "Asset and Parcel Coverage": f"주소 검증 {coverage['verified_address_count']}건, PNU 검증 {coverage['verified_pnu_count']}건, 개별공시지가 확인 {coverage['verified_land_price_count']}건입니다.",
        "Public REIT Separate-Tax Eligibility": (
            f"법정 적격성은 {statutory_status}, 실제 고지 과세구분은 {notice_status}, "
            f"법률 검토 상태는 {legal_status}입니다. 법정 적용 가능성과 실제 고지 "
            "과세구분을 동일한 상태로 표시하지 않습니다."
        ),
        "Land Property Tax Calculation": "필지별 개별공시지가 × 과세면적 × 소유지분으로 토지 시가표준액을 계산하고 Tax Rule Master의 공정시장가액비율과 세율을 적용합니다.",
        "Building Property Tax Calculation": (
            f"공식 건축물 시가표준액 확인 건은 {coverage['verified_building_value_count']}건입니다. "
            "시가표준액은 재산세 과세표준이나 실제 고지세액과 구분하며, 미확인 건은 계산하지 않습니다."
        ),
        "Urban Area Tax and Local Education Tax": "도시지역분은 적용대상 고시와 조례가 확인된 자산만 계산하며, 지방교육세는 도시지역분을 제외한 재산세 본세를 기준으로 계산합니다.",
        "Fire Resource Facility Tax": "공식 건축물 시가표준액과 위험유형이 모두 확인된 경우에만 누진세율 및 100%·200%·300% 배율을 적용합니다.",
        "Comprehensive Real Estate Holding Tax": "분리과세 토지는 not_applicable로 표시합니다. 종합·별도합산 토지는 납세의무자별 전국 합산 공시가격과 재산세 공제액이 없으면 계산을 차단합니다.",
        "Rural Special Tax": "검증된 종합부동산세가 있는 경우에만 Tax Rule Master의 농어촌특별세율을 적용합니다.",
        "Total Tax Burden": conclusion,
        "Reconciliation": (
            f"고지 대사 상태는 {reconciliation_status}입니다. 세금과공과 전체를 보유세 "
            "Ground Truth로 사용하지 않으며 실제 고지서 또는 과세내역서와 세목별로 대사해야 합니다."
        ),
        "Key Tax Risks": "\n".join(f"- {row.message}" for row in validations.itertuples()) if validations is not None and not validations.empty else "- 추가 검증 결과 없음",
        "Additional Document Request List": "\n".join(f"- [{row.priority}] {row.request_document}: {row.request_reason}" for row in requests.itertuples()) if requests is not None and not requests.empty else "- 현재 자동 생성된 요청자료 없음",
        "Reviewer Sign-off": "검토자: ____________________  검토일: ____________________  승인: ____________________",
    }
    lines = [f"# {reit_name} {tax_year} Tax Review Memo", "", f"상태: {SOURCE_BADGES.get(coverage['final_status'], coverage['final_status'])}", ""]
    for number, title in enumerate(SECTIONS, start=1):
        lines.extend([f"## {number}. {title}", "", section_text[title], ""])
    return "\n".join(lines).strip() + "\n"
