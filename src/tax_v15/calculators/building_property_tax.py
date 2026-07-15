from __future__ import annotations

from typing import Mapping

from ..models import CalculationResult
from ..rules import RuleUnavailableError, TaxRuleBook
from .common import require_decimal, source_is_calculable


def calculate_building_property_tax(building: Mapping, rules: TaxRuleBook) -> CalculationResult:
    tax_name = "건축물 재산세"
    ok, issues = source_is_calculable(building, ["building_standard_value"])
    if not ok:
        return CalculationResult.blocked(tax_name, "data_insufficient", *issues)
    official_value = require_decimal(building, "building_standard_value")
    if official_value < 0:
        return CalculationResult.blocked(tax_name, "manual_review_required", "건축물 시가표준액이 음수입니다.")
    try:
        rule = rules.one("property_tax_building_general")
        if rule.fair_market_value_ratio is None or rule.marginal_rate is None:
            raise RuleUnavailableError("건축물 공정시장가액비율 또는 세율이 없습니다.")
    except RuleUnavailableError as exc:
        return CalculationResult.blocked(tax_name, "manual_review_required", str(exc))
    tax_base = official_value * rule.fair_market_value_ratio
    tax = tax_base * rule.marginal_rate
    return CalculationResult(
        tax_name=tax_name,
        status="official_source_calculated",
        calculated_tax=tax,
        official_value=official_value,
        tax_base=tax_base,
        tax_rate=rule.marginal_rate,
        fair_market_value_ratio=rule.fair_market_value_ratio,
        formula_text="공식 건축물 시가표준액 × 공정시장가액비율 × 일반 건축물 세율",
        law_name=rule.law_name,
        article=rule.article,
        source_url=rule.source_url,
        input_source=str(building.get("calculation_source", building.get("source_document_name", ""))),
    )
