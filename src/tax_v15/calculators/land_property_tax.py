from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from ..models import CalculationResult
from ..rules import RuleUnavailableError, TaxRuleBook, progressive_amount
from .common import bracket_label, require_decimal, source_is_calculable


LAND_RULE_CODES = {
    "separated_public_reit": "property_tax_land_separated",
    "separated_other": "property_tax_land_separated",
    "aggregate": "property_tax_land_aggregate",
    "separate_aggregate": "property_tax_land_separate_aggregate",
}


def calculate_land_assessed_value(parcel: Mapping) -> CalculationResult:
    tax_name = "토지 시가표준액"
    ok, issues = source_is_calculable(
        parcel,
        ["individual_land_price_per_m2", "taxable_area_m2", "ownership_share"],
    )
    if not ok:
        return CalculationResult.blocked(tax_name, "data_insufficient", *issues)
    price = require_decimal(parcel, "individual_land_price_per_m2")
    area = require_decimal(parcel, "taxable_area_m2")
    share = require_decimal(parcel, "ownership_share")
    if price < 0 or area < 0 or share <= 0 or share > 1:
        return CalculationResult.blocked(
            tax_name,
            "manual_review_required",
            "개별공시지가·과세면적·소유지분 입력 범위를 검토해야 합니다.",
        )
    assessed = price * area * share
    return CalculationResult(
        tax_name=tax_name,
        status="official_source_calculated",
        official_value=assessed,
        formula_text="개별공시지가 × 과세면적 × 소유지분",
        source_url=str(parcel.get("source_url", parcel.get("data_source", ""))),
        input_source=str(parcel.get("source_document_name", parcel.get("data_source", ""))),
    )


def calculate_land_property_tax(parcel: Mapping, taxpayer: Mapping, rules: TaxRuleBook) -> CalculationResult:
    tax_name = "토지 재산세"
    classification = str(taxpayer.get("tax_classification", "undetermined") or "undetermined")
    if classification in {"housing", "exempt"}:
        return CalculationResult(
            tax_name=tax_name,
            status="not_applicable",
            calculated_tax=Decimal("0"),
            issues=(f"토지 분류가 {classification}이므로 이 계산 경로를 적용하지 않습니다.",),
        )
    if classification not in LAND_RULE_CODES:
        return CalculationResult.blocked(
            tax_name,
            "manual_review_required",
            "토지 과세구분이 확정되지 않았습니다.",
        )
    taxpayer_ok, taxpayer_issues = source_is_calculable(
        taxpayer,
        ["tax_obligor", "tax_classification", "assessment_date_ownership_verified"],
    )
    ownership_verified = str(
        taxpayer.get("assessment_date_ownership_verified", "")
    ).lower() in {"true", "1", "verified", "yes"}
    ownership_supported = (
        str(taxpayer.get("assessment_date_ownership_basis_status", ""))
        == "public_disclosure_continuity_supported_registry_unverified"
        and str(taxpayer.get("statutory_eligibility_status", ""))
        == "eligible_separated_public_reit"
    )
    if not taxpayer_ok or not (ownership_verified or ownership_supported):
        return CalculationResult.blocked(
            tax_name,
            "manual_review_required",
            *taxpayer_issues,
            "6월 1일 현재 소유 및 납세의무자 확인이 필요합니다.",
        )
    assessed = calculate_land_assessed_value(parcel)
    if assessed.status != "official_source_calculated" or assessed.official_value is None:
        return CalculationResult.blocked(tax_name, assessed.status, *assessed.issues)
    try:
        if classification in {"separated_public_reit", "separated_other"}:
            rule = rules.one(LAND_RULE_CODES[classification])
            ratio = rule.fair_market_value_ratio
            if ratio is None or rule.marginal_rate is None:
                raise RuleUnavailableError("분리과세 공정시장가액비율 또는 세율이 없습니다.")
            tax_base = assessed.official_value * ratio
            tax = tax_base * rule.marginal_rate
        else:
            brackets = rules.brackets(LAND_RULE_CODES[classification])
            ratio = brackets[0].fair_market_value_ratio
            if ratio is None:
                raise RuleUnavailableError("토지 재산세 공정시장가액비율이 없습니다.")
            tax_base = assessed.official_value * ratio
            tax, rule = progressive_amount(tax_base, brackets)
    except RuleUnavailableError as exc:
        return CalculationResult.blocked(tax_name, "manual_review_required", str(exc))
    return CalculationResult(
        tax_name=tax_name,
        status="official_source_calculated",
        calculated_tax=tax,
        official_value=assessed.official_value,
        tax_base=tax_base,
        tax_rate=rule.marginal_rate,
        fair_market_value_ratio=ratio,
        base_amount=rule.base_amount,
        bracket=bracket_label(rule.bracket_start, rule.bracket_end),
        formula_text="(개별공시지가 × 과세면적 × 소유지분) × 공정시장가액비율 × 적용세율",
        law_name=rule.law_name,
        article=rule.article,
        source_url=rule.source_url,
        input_source=str(parcel.get("source_document_name", parcel.get("data_source", ""))),
    )
