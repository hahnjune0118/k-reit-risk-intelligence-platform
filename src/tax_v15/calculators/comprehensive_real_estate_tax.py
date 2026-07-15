from __future__ import annotations

from decimal import Decimal

from ..models import CalculationResult
from ..rules import RuleUnavailableError, TaxRuleBook, progressive_amount
from .common import bracket_label


def calculate_comprehensive_land_tax(
    official_value: Decimal | None,
    classification: str,
    property_tax_credit: Decimal | None,
    rules: TaxRuleBook,
    *,
    nationwide_aggregation_verified: bool,
    classification_verified: bool,
) -> CalculationResult:
    tax_name = "토지분 종합부동산세"
    if not classification_verified:
        return CalculationResult.blocked(
            tax_name,
            "manual_review_required",
            "토지 과세구분의 법적 판정이 공식 검증되지 않았습니다.",
        )
    if classification in {"separated_public_reit", "separated_other", "exempt"}:
        return CalculationResult(
            tax_name=tax_name,
            status="not_applicable",
            calculated_tax=Decimal("0"),
            formula_text="분리과세 또는 비과세 토지는 토지분 종합부동산세 합산대상에서 제외",
            issues=("분리과세 판정 자체는 별도 법적 검증을 전제로 합니다.",),
        )
    if classification not in {"aggregate", "separate_aggregate"}:
        return CalculationResult.blocked(tax_name, "manual_review_required", "종합부동산세 토지 과세구분이 확정되지 않았습니다.")
    if official_value is None or not nationwide_aggregation_verified:
        return CalculationResult.blocked(
            tax_name,
            "manual_review_required",
            "납세의무자별 전국 합산 공시가격이 확인되지 않았습니다.",
        )
    if property_tax_credit is None:
        return CalculationResult.blocked(
            tax_name,
            "manual_review_required",
            "토지분 재산세 공제액이 확인되지 않았습니다.",
        )
    prefix = "comprehensive_land_aggregate" if classification == "aggregate" else "comprehensive_land_separate_aggregate"
    try:
        deduction_rule = rules.one(f"{prefix}_deduction")
        brackets = rules.brackets(prefix)
        deduction = deduction_rule.base_amount
        ratio = deduction_rule.fair_market_value_ratio
        if deduction is None or ratio is None:
            raise RuleUnavailableError("종합부동산세 공제액 또는 공정시장가액비율이 없습니다.")
        tax_base = max(official_value - deduction, Decimal("0")) * ratio
        gross_tax, bracket_rule = progressive_amount(tax_base, brackets)
    except RuleUnavailableError as exc:
        return CalculationResult.blocked(tax_name, "manual_review_required", str(exc))
    net_tax = max(gross_tax - property_tax_credit, Decimal("0"))
    return CalculationResult(
        tax_name=tax_name,
        status="official_source_calculated",
        calculated_tax=net_tax,
        official_value=official_value,
        tax_base=tax_base,
        tax_rate=bracket_rule.marginal_rate,
        fair_market_value_ratio=ratio,
        base_amount=bracket_rule.base_amount,
        bracket=bracket_label(bracket_rule.bracket_start, bracket_rule.bracket_end),
        formula_text="(납세의무자별 전국 합산 공시가격 - 법정 공제액) × 공정시장가액비율에 누진세율 적용 - 재산세 공제액",
        law_name=bracket_rule.law_name,
        article=bracket_rule.article,
        source_url=bracket_rule.source_url,
    )


def calculate_rural_special_tax(comprehensive_tax: CalculationResult, rules: TaxRuleBook) -> CalculationResult:
    tax_name = "종합부동산세분 농어촌특별세"
    if comprehensive_tax.status == "not_applicable":
        return CalculationResult(tax_name=tax_name, status="not_applicable", calculated_tax=Decimal("0"))
    if not comprehensive_tax.is_calculated or comprehensive_tax.calculated_tax is None:
        return CalculationResult.blocked(tax_name, "data_insufficient", "종합부동산세가 확정 계산되지 않았습니다.")
    try:
        rule = rules.one("rural_special_tax")
        if rule.marginal_rate is None:
            raise RuleUnavailableError("농어촌특별세율이 없습니다.")
    except RuleUnavailableError as exc:
        return CalculationResult.blocked(tax_name, "manual_review_required", str(exc))
    return CalculationResult(
        tax_name=tax_name,
        status="official_source_calculated",
        calculated_tax=comprehensive_tax.calculated_tax * rule.marginal_rate,
        tax_base=comprehensive_tax.calculated_tax,
        tax_rate=rule.marginal_rate,
        formula_text="납부할 토지분 종합부동산세액 × 농어촌특별세율",
        law_name=rule.law_name,
        article=rule.article,
        source_url=rule.source_url,
    )


def aggregate_official_land_values(parcels: list[dict], taxpayer_id: str) -> Decimal | None:
    """Aggregate only source-backed parcel values for one legal taxpayer."""
    total = Decimal("0")
    matched = 0
    for parcel in parcels:
        if str(parcel.get("taxpayer_id", "")) != str(taxpayer_id):
            continue
        if str(parcel.get("validation_status", "")) not in {"verified_notice", "official_source_calculated"}:
            return None
        if not str(parcel.get("source_url", "") or "").strip():
            return None
        value = parcel.get("assessed_land_value")
        try:
            amount = Decimal(str(value))
        except Exception:
            return None
        total += amount
        matched += 1
    return total if matched else None
