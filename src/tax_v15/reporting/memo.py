from __future__ import annotations

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


def _verified_total(calculations: pd.DataFrame) -> float | None:
    if calculations is None or calculations.empty:
        return None
    eligible = calculations[
        calculations["calculation_status"].isin(["verified_notice", "official_source_calculated"])
        & calculations["tax_name"].ne("토지 시가표준액")
    ]
    values = pd.to_numeric(eligible["calculated_tax"], errors="coerce").dropna()
    return float(values.sum()) if not values.empty else None


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
    conclusion = (
        f"{reit_name}의 {tax_year}년 공개자료 기반 검토에서 공식자료로 계산 가능한 세목 행은 {completed}건, "
        f"추가자료가 필요한 행은 {blocked}건입니다. "
        + (f"검증된 계산 행의 단순 합계는 {verified_total:,.0f}원입니다. " if verified_total is not None else "확정 표시할 수 있는 세액 합계는 없습니다. ")
        + "이 합계는 중복·세부담상한·감면·실제 고지세액 대사 전의 검토값이며 신고세액이 아닙니다."
    )
    section_text = {
        "Executive Conclusion": conclusion,
        "Scope and Limitation": DISCLAIMER_KO,
        "REIT Legal Status": "상장 여부와 공모부동산투자회사 요건은 서로 구분해 검토합니다. 상장 사실만으로 분리과세를 확정하지 않습니다.",
        "Ownership and Taxpayer Structure": f"자산 {coverage['asset_count']}건 중 공식 근거로 납세의무자 행이 계산 허용 상태인 건은 {coverage['verified_taxpayer_count']}건입니다.",
        "Asset and Parcel Coverage": f"주소 검증 {coverage['verified_address_count']}건, PNU 검증 {coverage['verified_pnu_count']}건, 개별공시지가 확인 {coverage['verified_land_price_count']}건입니다.",
        "Public REIT Separate-Tax Eligibility": "법적 주체, 공모 요건, 과세기준일 소유, 목적사업 사용, 신탁관계를 모두 확인한 경우에만 separated_public_reit로 판정합니다.",
        "Land Property Tax Calculation": "필지별 개별공시지가 × 과세면적 × 소유지분으로 토지 시가표준액을 계산하고 Tax Rule Master의 공정시장가액비율과 세율을 적용합니다.",
        "Building Property Tax Calculation": f"공식 건축물 시가표준액 확인 건은 {coverage['verified_building_value_count']}건입니다. 미확인 건은 계산하지 않습니다.",
        "Urban Area Tax and Local Education Tax": "도시지역분은 적용대상 고시와 조례가 확인된 자산만 계산하며, 지방교육세는 도시지역분을 제외한 재산세 본세를 기준으로 계산합니다.",
        "Fire Resource Facility Tax": "공식 건축물 시가표준액과 위험유형이 모두 확인된 경우에만 누진세율 및 100%·200%·300% 배율을 적용합니다.",
        "Comprehensive Real Estate Holding Tax": "분리과세 토지는 not_applicable로 표시합니다. 종합·별도합산 토지는 납세의무자별 전국 합산 공시가격과 재산세 공제액이 없으면 계산을 차단합니다.",
        "Rural Special Tax": "검증된 종합부동산세가 있는 경우에만 Tax Rule Master의 농어촌특별세율을 적용합니다.",
        "Total Tax Burden": conclusion,
        "Reconciliation": "세금과공과 전체를 보유세 Ground Truth로 사용하지 않습니다. 실제 고지서 또는 과세내역서와 세목별로 대사해야 합니다.",
        "Key Tax Risks": "\n".join(f"- {row.message}" for row in validations.itertuples()) if validations is not None and not validations.empty else "- 추가 검증 결과 없음",
        "Additional Document Request List": "\n".join(f"- [{row.priority}] {row.request_document}: {row.request_reason}" for row in requests.itertuples()) if requests is not None and not requests.empty else "- 현재 자동 생성된 요청자료 없음",
        "Reviewer Sign-off": "검토자: ____________________  검토일: ____________________  승인: ____________________",
    }
    lines = [f"# {reit_name} {tax_year} Tax Review Memo", "", f"상태: {SOURCE_BADGES.get(coverage['final_status'], coverage['final_status'])}", ""]
    for number, title in enumerate(SECTIONS, start=1):
        lines.extend([f"## {number}. {title}", "", section_text[title], ""])
    return "\n".join(lines).strip() + "\n"
