from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from ..models import CalculationResult
from ..rules import RuleUnavailableError, TaxRuleBook, progressive_amount
from .common import bracket_label, require_decimal, source_is_calculable


def calculate_urban_area_tax(tax_base: Decimal | None, applicability_status: str, rules: TaxRuleBook) -> CalculationResult:
    tax_name = "재산세 도시지역분"
    if applicability_status == "verified_not_applicable":
        return CalculationResult(tax_name=tax_name, status="not_applicable", calculated_tax=Decimal("0"))
    if applicability_status != "verified_applicable":
        return CalculationResult.blocked(
            tax_name,
            "manual_review_required",
            "도시지역분 적용대상 고시 및 지방자치단체 조례 확인이 필요합니다.",
        )
    if tax_base is None:
        return CalculationResult.blocked(tax_name, "data_insufficient", "기초 재산세 과세표준이 없습니다.")
    try:
        rule = rules.one("urban_area_tax_standard")
        if rule.marginal_rate is None:
            raise RuleUnavailableError("도시지역분 적용 세율이 없습니다.")
    except RuleUnavailableError as exc:
        return CalculationResult.blocked(tax_name, "manual_review_required", str(exc))
    return CalculationResult(
        tax_name=tax_name,
        status="official_source_calculated",
        calculated_tax=tax_base * rule.marginal_rate,
        tax_base=tax_base,
        tax_rate=rule.marginal_rate,
        formula_text="검증된 재산세 과세표준 × 해당 지방자치단체 적용 세율",
        law_name=rule.law_name,
        article=rule.article,
        source_url=rule.source_url,
    )


def calculate_local_education_tax(property_tax: CalculationResult, rules: TaxRuleBook) -> CalculationResult:
    tax_name = "지방교육세"
    if not property_tax.is_calculated or property_tax.calculated_tax is None:
        return CalculationResult.blocked(tax_name, "data_insufficient", "재산세 본세가 확정 계산되지 않았습니다.")
    try:
        rule = rules.one("local_education_tax")
        if rule.marginal_rate is None:
            raise RuleUnavailableError("지방교육세율이 없습니다.")
    except RuleUnavailableError as exc:
        return CalculationResult.blocked(tax_name, "manual_review_required", str(exc))
    return CalculationResult(
        tax_name=tax_name,
        status="official_source_calculated",
        calculated_tax=property_tax.calculated_tax * rule.marginal_rate,
        tax_base=property_tax.calculated_tax,
        tax_rate=rule.marginal_rate,
        formula_text="재산세 본세(도시지역분 제외) × 지방교육세율",
        law_name=rule.law_name,
        article=rule.article,
        source_url=rule.source_url,
    )


def calculate_fire_resource_tax(building: Mapping, rules: TaxRuleBook) -> CalculationResult:
    tax_name = "소방분 지역자원시설세"
    ok, issues = source_is_calculable(building, ["building_standard_value", "fire_risk_category"])
    if not ok:
        return CalculationResult.blocked(tax_name, "data_insufficient", *issues)
    category = str(building.get("fire_risk_category", ""))
    multiplier_codes = {
        "standard": "fire_multiplier_standard",
        "fire_risk": "fire_multiplier_200",
        "large_fire_risk": "fire_multiplier_300",
    }
    if category not in multiplier_codes:
        return CalculationResult.blocked(
            tax_name,
            "manual_review_required",
            "건축물의 소방분 위험유형과 가중배율을 확인해야 합니다.",
        )
    official_value = require_decimal(building, "building_standard_value")
    try:
        tax, bracket_rule = progressive_amount(official_value, rules.brackets("fire_resource_tax"))
        multiplier_rule = rules.one(multiplier_codes[category])
        multiplier = multiplier_rule.multiplier
        if multiplier is None:
            raise RuleUnavailableError("소방분 가중배율이 없습니다.")
    except RuleUnavailableError as exc:
        return CalculationResult.blocked(tax_name, "manual_review_required", str(exc))
    return CalculationResult(
        tax_name=tax_name,
        status="official_source_calculated",
        calculated_tax=tax * multiplier,
        official_value=official_value,
        tax_base=official_value,
        tax_rate=bracket_rule.marginal_rate,
        multiplier=multiplier,
        base_amount=bracket_rule.base_amount,
        bracket=bracket_label(bracket_rule.bracket_start, bracket_rule.bracket_end),
        formula_text="공식 건축물 시가표준액에 소방분 누진세율 적용 후 검증된 위험유형 가중배율 적용",
        law_name=bracket_rule.law_name,
        article=bracket_rule.article,
        source_url=bracket_rule.source_url,
        input_source=str(building.get("source_document_name", building.get("calculation_source", ""))),
    )
