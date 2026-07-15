from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .constants import CALCULABLE_SOURCE_STATUSES


@dataclass(frozen=True)
class TaxpayerDecision:
    tax_obligor: str
    status: str
    reason: str


def determine_tax_obligor(facts: Mapping) -> TaxpayerDecision:
    status = str(facts.get("validation_status", ""))
    if status not in CALCULABLE_SOURCE_STATUSES or not str(facts.get("source_url", "") or "").strip():
        return TaxpayerDecision("", "manual_review_required", "소유·신탁관계의 공식 출처가 확인되지 않았습니다.")
    trustee = str(facts.get("trustee", "") or "").strip()
    trustor = str(facts.get("trustor", "") or "").strip()
    legal_owner = str(facts.get("legal_owner", "") or "").strip()
    if trustee:
        if trustor:
            return TaxpayerDecision(trustor, "official_source_calculated", "신탁재산의 위탁자를 재산세 납세의무자로 판정")
        return TaxpayerDecision("", "manual_review_required", "신탁재산의 위탁자가 확인되지 않았습니다.")
    if legal_owner:
        return TaxpayerDecision(legal_owner, "official_source_calculated", "과세기준일 현재 법적 소유자를 납세의무자로 판정")
    return TaxpayerDecision("", "data_insufficient", "법적 소유자가 확인되지 않았습니다.")


def classify_public_reit_land(facts: Mapping) -> tuple[str, str, str]:
    required_true = [
        "legal_reit_entity",
        "public_reit_qualified",
        "assessment_date_ownership_verified",
        "purpose_business_use",
        "non_housing_land",
        "no_special_exclusion",
    ]
    if str(facts.get("validation_status", "")) not in CALCULABLE_SOURCE_STATUSES:
        return "undetermined", "manual_review_required", "법적 판정 사실의 출처 검증이 완료되지 않았습니다."
    missing = [field for field in required_true if facts.get(field) is not True]
    if missing:
        return "undetermined", "manual_review_required", f"분리과세 필수요건 미확인: {', '.join(missing)}"
    return "separated_public_reit", "official_source_calculated", "공모리츠 목적사업용 토지 분리과세 필수요건 확인"
