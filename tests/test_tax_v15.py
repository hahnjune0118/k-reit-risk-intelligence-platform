from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from src.tax_v15.calculators.building_property_tax import calculate_building_property_tax
from src.tax_v15.calculators.comprehensive_real_estate_tax import (
    aggregate_official_land_values,
    calculate_comprehensive_land_tax,
    calculate_rural_special_tax,
)
from src.tax_v15.calculators.land_property_tax import calculate_land_assessed_value, calculate_land_property_tax
from src.tax_v15.calculators.supplementary_taxes import (
    calculate_fire_resource_tax,
    calculate_local_education_tax,
    calculate_urban_area_tax,
)
from src.tax_v15.models import CalculationResult
from src.tax_v15.rules import RuleUnavailableError, TaxRuleBook
from src.tax_v15.schemas import CSV_SCHEMAS
from src.tax_v15.taxpayer import classify_public_reit_land, determine_tax_obligor
from src.tax_v15.validation import validate_no_forbidden_tax_fallback


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def rules() -> TaxRuleBook:
    return TaxRuleBook(pd.read_csv(ROOT / "data" / "v15" / "tax_rule_master.csv"), 2026)


def _parcel(**updates) -> dict:
    row = {
        "individual_land_price_per_m2": 1_000_000,
        "taxable_area_m2": 100_000,
        "ownership_share": 1,
        "validation_status": "verified_notice",
        "source_url": "https://official.example/parcel",
        "source_document_name": "official parcel record",
        "tax_urban_area_status": "verified_applicable",
    }
    row.update(updates)
    return row


def _taxpayer(**updates) -> dict:
    row = {
        "tax_obligor": "테스트리츠",
        "tax_classification": "separated_public_reit",
        "assessment_date_ownership_verified": True,
        "validation_status": "verified_notice",
        "source_url": "https://official.example/taxpayer",
    }
    row.update(updates)
    return row


def _building(**updates) -> dict:
    row = {
        "building_standard_value": 30_000_000_000,
        "fire_risk_category": "standard",
        "validation_status": "verified_notice",
        "source_url": "https://official.example/building",
        "source_document_name": "official building value",
    }
    row.update(updates)
    return row


def test_01_parcel_land_value_calculation():
    result = calculate_land_assessed_value(_parcel())
    assert result.status == "official_source_calculated"
    assert result.official_value == Decimal("100000000000")
    assert result.calculated_tax is None


def test_02_ownership_share_is_applied():
    result = calculate_land_assessed_value(_parcel(ownership_share=Decimal("0.25")))
    assert result.official_value == Decimal("25000000000.00")


def test_03_separated_land_property_tax_uses_rule_master(rules):
    result = calculate_land_property_tax(_parcel(), _taxpayer(), rules)
    assert result.tax_base == Decimal("70000000000.00")
    assert result.calculated_tax == Decimal("140000000.00000")


def test_04_urban_area_tax(rules):
    result = calculate_urban_area_tax(Decimal("70000000000"), "verified_applicable", rules)
    assert result.calculated_tax == Decimal("98000000.0000")


def test_05_local_education_tax_excludes_urban_component(rules):
    property_tax = calculate_land_property_tax(_parcel(), _taxpayer(), rules)
    result = calculate_local_education_tax(property_tax, rules)
    assert result.tax_base == property_tax.calculated_tax
    assert result.calculated_tax == Decimal("28000000.0000000")


def test_06_building_property_tax(rules):
    result = calculate_building_property_tax(_building(), rules)
    assert result.tax_base == Decimal("21000000000.00")
    assert result.calculated_tax == Decimal("52500000.000000")


def test_07_fire_resource_progressive_rate(rules):
    result = calculate_fire_resource_tax(_building(), rules)
    assert result.calculated_tax == Decimal("35972300.0000")


@pytest.mark.parametrize(("category", "multiplier"), [("fire_risk", Decimal("2")), ("large_fire_risk", Decimal("3"))])
def test_08_fire_risk_multipliers(rules, category, multiplier):
    base = calculate_fire_resource_tax(_building(), rules)
    result = calculate_fire_resource_tax(_building(fire_risk_category=category), rules)
    assert result.calculated_tax == base.calculated_tax * multiplier


def test_09_separated_land_is_not_subject_to_comprehensive_tax(rules):
    result = calculate_comprehensive_land_tax(
        Decimal("100000000000"), "separated_public_reit", None, rules,
        nationwide_aggregation_verified=False, classification_verified=True,
    )
    assert result.status == "not_applicable"
    assert result.calculated_tax == Decimal("0")


@pytest.mark.parametrize(
    ("classification", "official_value", "expected"),
    [
        ("aggregate", Decimal("5000000000"), Decimal("75000000.00")),
        ("separate_aggregate", Decimal("28000000000"), Decimal("100000000.000")),
    ],
)
def test_10_comprehensive_tax_progressive_brackets(rules, classification, official_value, expected):
    result = calculate_comprehensive_land_tax(
        official_value, classification, Decimal("0"), rules,
        nationwide_aggregation_verified=True, classification_verified=True,
    )
    assert result.calculated_tax == expected


def test_11_comprehensive_tax_property_tax_credit(rules):
    result = calculate_comprehensive_land_tax(
        Decimal("5000000000"), "aggregate", Decimal("10000000"), rules,
        nationwide_aggregation_verified=True, classification_verified=True,
    )
    assert result.calculated_tax == Decimal("65000000.00")


def test_12_rural_special_tax(rules):
    comprehensive = calculate_comprehensive_land_tax(
        Decimal("5000000000"), "aggregate", Decimal("0"), rules,
        nationwide_aggregation_verified=True, classification_verified=True,
    )
    result = calculate_rural_special_tax(comprehensive, rules)
    assert result.calculated_tax == Decimal("15000000.000")


def test_13_trustor_is_taxpayer_when_officially_verified():
    decision = determine_tax_obligor({
        "legal_owner": "수탁자", "trustee": "수탁자", "trustor": "위탁자",
        "validation_status": "verified_notice", "source_url": "https://official.example/trust",
    })
    assert decision.tax_obligor == "위탁자"
    assert decision.status == "official_source_calculated"


def test_14_ambiguous_separation_classification_is_blocked(rules):
    classification, status, _ = classify_public_reit_land({
        "legal_reit_entity": True,
        "public_reit_qualified": True,
        "validation_status": "official_partial",
    })
    assert classification == "undetermined"
    assert status == "manual_review_required"
    result = calculate_land_property_tax(_parcel(), _taxpayer(tax_classification=classification), rules)
    assert result.status == "manual_review_required"
    assert result.calculated_tax is None


def test_15_book_value_fallback_is_forbidden():
    result = calculate_land_assessed_value({
        "book_value": 999_999_999_999,
        "taxable_area_m2": 100,
        "ownership_share": 1,
        "validation_status": "verified_notice",
        "source_url": "https://official.example/book",
    })
    assert result.status == "data_insufficient"
    assert result.official_value is None


def test_16_peer_snapshot_fallback_is_forbidden():
    result = calculate_land_assessed_value({
        "peer_official_price": 999_999_999_999,
        "taxable_area_m2": 100,
        "ownership_share": 1,
        "validation_status": "verified_notice",
        "source_url": "https://official.example/peer",
    })
    assert result.status == "data_insufficient"
    active_paths = [ROOT / "ui_tax_v15.py", *sorted((ROOT / "src" / "tax_v15").rglob("*.py"))]
    assert validate_no_forbidden_tax_fallback(active_paths) == []


def test_17_source_less_number_is_blocked():
    result = calculate_land_assessed_value(_parcel(source_url=""))
    assert result.status == "data_insufficient"
    assert result.calculated_tax is None


def test_18_multiple_parcels_can_be_aggregated_without_cross_taxpayer_leakage():
    rows = [
        {"taxpayer_id": "TP1", "assessed_land_value": 100, "validation_status": "verified_notice", "source_url": "https://official/1"},
        {"taxpayer_id": "TP1", "assessed_land_value": 200, "validation_status": "official_source_calculated", "source_url": "https://official/2"},
        {"taxpayer_id": "TP2", "assessed_land_value": 900, "validation_status": "verified_notice", "source_url": "https://official/3"},
    ]
    assert aggregate_official_land_values(rows, "TP1") == Decimal("300")


def test_19_taxpayer_nationwide_aggregation_requires_all_verified_rows():
    rows = [
        {"taxpayer_id": "TP1", "assessed_land_value": 100, "validation_status": "verified_notice", "source_url": "https://official/1"},
        {"taxpayer_id": "TP1", "assessed_land_value": 200, "validation_status": "official_partial", "source_url": "https://official/2"},
    ]
    assert aggregate_official_land_values(rows, "TP1") is None


def test_20_data_insufficient_status_has_no_calculated_amount(rules):
    building = calculate_building_property_tax(_building(building_standard_value=None), rules)
    urban = calculate_urban_area_tax(None, "unknown", rules)
    assert building.status == "data_insufficient" and building.calculated_tax is None
    assert urban.status == "manual_review_required" and urban.calculated_tax is None


def test_21_golden_land_total_is_266_million(rules):
    property_tax = calculate_land_property_tax(_parcel(), _taxpayer(), rules)
    urban = calculate_urban_area_tax(property_tax.tax_base, "verified_applicable", rules)
    education = calculate_local_education_tax(property_tax, rules)
    comprehensive = calculate_comprehensive_land_tax(
        property_tax.official_value, "separated_public_reit", None, rules,
        nationwide_aggregation_verified=False, classification_verified=True,
    )
    assert property_tax.calculated_tax + urban.calculated_tax + education.calculated_tax == Decimal("266000000.0000000")
    assert comprehensive.calculated_tax == 0


def test_22_golden_building_values_are_rule_driven(rules):
    building = calculate_building_property_tax(_building(), rules)
    urban = calculate_urban_area_tax(building.tax_base, "verified_applicable", rules)
    education = calculate_local_education_tax(building, rules)
    assert building.calculated_tax == Decimal("52500000.000000")
    assert urban.calculated_tax == Decimal("29400000.0000")
    assert education.calculated_tax == Decimal("10500000.00000000")


def test_23_unverified_separated_label_does_not_force_zero_comprehensive_tax(rules):
    result = calculate_comprehensive_land_tax(
        Decimal("100000000000"), "separated_public_reit", None, rules,
        nationwide_aggregation_verified=False, classification_verified=False,
    )
    assert result.status == "manual_review_required"
    assert result.calculated_tax is None


def test_24_calculation_result_rejects_unverified_amount():
    with pytest.raises(ValueError, match="검증되지 않은 상태"):
        CalculationResult(tax_name="오류", status="data_insufficient", calculated_tax=Decimal("1"))


def test_25_tax_calculation_schema_preserves_tax_year():
    assert CSV_SCHEMAS["tax_calculation_detail.csv"][0] == "tax_year"


def test_26_rule_without_official_url_is_rejected():
    frame = pd.read_csv(ROOT / "data" / "v15" / "tax_rule_master.csv")
    frame.loc[frame["rule_code"].eq("local_education_tax"), "source_url"] = ""
    unsafe_rules = TaxRuleBook(frame, 2026)
    with pytest.raises(RuleUnavailableError):
        unsafe_rules.one("local_education_tax")
