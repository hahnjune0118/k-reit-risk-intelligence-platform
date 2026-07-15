from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from src.tax_v15.loaders import load_v15_bundle
from src.tax_v15.reporting import build_tax_review_memo


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ASSET_ID = "SKR-SEOUL-SEORIN-001"
GOLDEN_TAXPAYER_ID = "SKR-TP-001"
RAW_TOTAL = Decimal("1250710968.55472")
AFTER_TOTAL = Decimal("1250710930")
CALCULATION_LABEL = "2026년 공식 과세기초자료와 확인된 법정 산식에 따른 보유세 재계산액"
SNAPSHOT_PATH = (
    ROOT / "data" / "v15" / "golden_asset" / "sk_seorin_official_snapshot.json"
)
CALCULATION_PATH = ROOT / "data" / "v15" / "tax_calculation_detail.csv"
RECONCILIATION_PATH = ROOT / "data" / "v15" / "reconciliation.csv"
EVIDENCE_MATRIX_PATH = (
    ROOT / "docs" / "v15" / "golden_asset" / "SK_SEORIN_EVIDENCE_MATRIX.csv"
)
AREA_RECONCILIATION_PATH = (
    ROOT / "docs" / "v15" / "golden_asset" / "SK_SEORIN_AREA_RECONCILIATION.csv"
)
MEMO_PATH = ROOT / "docs" / "v15" / "golden_asset" / "GOLDEN_ASSET_TAX_REVIEW.md"
UI_PATH = ROOT / "ui_tax_v15.py"


@pytest.fixture(scope="module")
def bundle():
    return load_v15_bundle()


@pytest.fixture(scope="module")
def snapshot() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def raw_calculations() -> pd.DataFrame:
    return pd.read_csv(
        CALCULATION_PATH,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )


def _one(frame: pd.DataFrame, **filters) -> pd.Series:
    selected = frame.copy()
    for column, value in filters.items():
        selected = selected[selected[column].fillna("").astype(str).eq(str(value))]
    assert len(selected) == 1
    return selected.iloc[0]


def _raw_tax_row(
    frame: pd.DataFrame,
    tax_name: str,
    *,
    scope: str,
) -> pd.Series:
    selected = frame[
        frame["reit_name"].eq("SK리츠")
        & frame["tax_year"].eq("2026")
        & frame["tax_name"].eq(tax_name)
    ]
    if scope == "parcel":
        selected = selected[selected["parcel_id"].ne("")]
    elif scope == "building":
        selected = selected[selected["building_id"].ne("")]
    else:
        selected = selected[selected["parcel_id"].eq("") & selected["building_id"].eq("")]
    assert len(selected) == 1
    return selected.iloc[0]


def test_golden_asset_official_inputs_are_connected(bundle, snapshot):
    asset = _one(bundle.assets, asset_id=GOLDEN_ASSET_ID)
    parcel = _one(bundle.parcels, asset_id=GOLDEN_ASSET_ID)
    building = _one(bundle.buildings, asset_id=GOLDEN_ASSET_ID)

    assert asset["stock_code"] == "395400"
    assert asset["road_address"] == "서울특별시 종로구 종로 26"
    assert parcel["pnu"] == "1111012300100990000"
    assert Decimal(str(parcel["parcel_area_m2"])) == Decimal("5773.5")
    assert Decimal(str(parcel["individual_land_price_per_m2"])) == Decimal("63950000")
    assert Decimal(str(parcel["assessed_land_value"])) == Decimal("369215325000")
    assert Decimal(str(building["building_standard_value"])) == Decimal("40221752104")
    assert snapshot["building"]["building_component_value"] + snapshot["building"][
        "facility_component_value"
    ] == snapshot["building"]["building_standard_value"]


def test_direct_investment_and_trust_title_are_not_conflated(bundle, snapshot):
    asset = _one(bundle.assets, asset_id=GOLDEN_ASSET_ID)

    assert asset["direct_or_indirect"] == "direct_investment_trust_title"
    assert asset["investment_holding_type"] == "direct_real_estate_investment"
    assert asset["title_holding_type"] == "trustee_registered_trust_property"
    assert asset["registered_owner"] == "대한토지신탁(주)"
    assert asset["trustee"] == "대한토지신탁(주)"
    assert asset["trustor"] == "에스케이위탁관리부동산투자회사(주)"
    assert asset["beneficial_owner"] == "에스케이위탁관리부동산투자회사(주)"
    assert asset["property_taxpayer"] == "에스케이위탁관리부동산투자회사(주)"
    assert snapshot["asset"]["ownership_display_ko"] == (
        "SK리츠가 위탁자이자 재산세 납세의무자인 신탁보유 오피스 자산"
    )


def test_statutory_eligibility_and_actual_notice_are_separate(bundle):
    taxpayer = _one(bundle.taxpayers, taxpayer_id=GOLDEN_TAXPAYER_ID)

    assert taxpayer["tax_classification"] == "separated_public_reit"
    assert taxpayer["statutory_eligibility_status"] == "eligible_separated_public_reit"
    assert taxpayer["actual_notice_classification"] == "unverified"
    assert taxpayer["legal_review_status"] == (
        "statutory_basis_reviewed_registry_and_notice_open"
    )
    assert taxpayer["notice_reconciliation_status"] == "not_reconciled"
    assert taxpayer["assessment_date_ownership_basis_status"] == (
        "public_disclosure_continuity_supported_registry_unverified"
    )
    assert not bool(taxpayer["assessment_date_ownership_verified"])


def test_each_formula_and_raw_total_are_exact_decimal(raw_calculations, snapshot):
    land_value = Decimal(str(snapshot["parcel"]["individual_land_price_per_m2"])) * Decimal(
        str(snapshot["parcel"]["taxable_area_m2"])
    )
    land_base = land_value * Decimal("0.70")
    land_property_tax = land_base * Decimal("0.002")
    land_urban_tax = land_base * Decimal("0.0014")
    land_education_tax = land_property_tax * Decimal("0.20")

    building_value = Decimal(str(snapshot["building"]["building_component_value"])) + Decimal(
        str(snapshot["building"]["facility_component_value"])
    )
    building_base = building_value * Decimal("0.70")
    building_property_tax = building_base * Decimal("0.0025")
    building_urban_tax = building_base * Decimal("0.0014")
    building_education_tax = building_property_tax * Decimal("0.20")
    fire_tax = (
        Decimal("49100")
        + (building_value - Decimal("64000000")) * Decimal("0.0012")
    ) * Decimal("3")

    expected = {
        ("토지 재산세", "parcel"): (land_property_tax, Decimal("516901450")),
        ("재산세 도시지역분", "parcel"): (land_urban_tax, Decimal("361831010")),
        ("지방교육세", "parcel"): (land_education_tax, Decimal("103380290")),
        ("건축물 재산세", "building"): (building_property_tax, Decimal("70388060")),
        ("재산세 도시지역분", "building"): (building_urban_tax, Decimal("39417310")),
        ("지방교육세", "building"): (building_education_tax, Decimal("14077610")),
        ("소방분 지역자원시설세", "building"): (fire_tax, Decimal("144715200")),
        ("토지분 종합부동산세", "taxpayer"): (None, Decimal("0")),
        ("종합부동산세분 농어촌특별세", "taxpayer"): (None, Decimal("0")),
    }
    for (tax_name, scope), (expected_before, expected_after) in expected.items():
        row = _raw_tax_row(raw_calculations, tax_name, scope=scope)
        if expected_before is None:
            assert row["calculated_tax_before_end_digit_treatment"] == ""
            assert row["calculated_tax_after_end_digit_treatment"] == ""
        else:
            assert Decimal(row["calculated_tax_before_end_digit_treatment"]) == expected_before
            assert Decimal(row["calculated_tax_after_end_digit_treatment"]) == expected_after
        assert Decimal(row["calculated_tax"]) == expected_after

    assert land_value == Decimal("369215325000.0")
    assert building_value == Decimal("40221752104")
    assert sum((before for before, _ in expected.values() if before is not None), Decimal("0")) == RAW_TOTAL
    assert sum((after for _, after in expected.values()), Decimal("0")) == AFTER_TOTAL


def test_raw_recalculation_is_not_actual_notice_amount(bundle):
    reconciliation = _one(
        bundle.reconciliation,
        reit_name="SK리츠",
        metric="holding_tax_notice_reconciliation",
    )
    raw_reconciliation = pd.read_csv(
        RECONCILIATION_PATH,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )
    raw_row = _one(
        raw_reconciliation,
        reit_name="SK리츠",
        metric="holding_tax_notice_reconciliation",
    )

    assert raw_row["calculated_value"] == "1250710930"
    assert raw_row["disclosed_or_verified_value"] == ""
    assert pd.isna(reconciliation["disclosed_or_verified_value"])
    assert reconciliation["reviewer_status"] == "open"


def test_verified_notice_is_forbidden_without_notice(bundle):
    calculations = bundle.calculations[bundle.calculations["reit_name"].eq("SK리츠")]
    taxpayer = _one(bundle.taxpayers, taxpayer_id=GOLDEN_TAXPAYER_ID)

    assert calculations["verified_tax"].isna().all()
    assert not calculations["calculation_status"].eq("verified_notice").any()
    assert taxpayer["actual_notice_classification"] == "unverified"
    assert taxpayer["notice_reconciliation_status"] == "not_reconciled"


def test_fire_300_percent_has_building_and_statutory_evidence(bundle):
    building = _one(bundle.buildings, building_id="SKR-SEORIN-B-001")
    fire_row = _one(
        bundle.calculations,
        reit_name="SK리츠",
        tax_name="소방분 지역자원시설세",
    )

    assert building["main_use"] == "업무시설"
    assert building["floor_count"] == "지상 36 / 지하 7"
    assert building["fire_risk_category"] == "large_fire_risk"
    assert Decimal(str(building["fire_tax_multiplier"])) == Decimal("3")
    assert building["fire_tax_multiplier_status"] == "official_source_calculated"
    assert "제138조제2항제1호" in building["fire_tax_evidence_page"]
    assert "11층" in building["fire_tax_evidence_quote"]
    assert Decimal(str(fire_row["tax_base"])) == Decimal("40221752104.0")
    assert Decimal(str(fire_row["calculated_tax_before_end_digit_treatment"])) == Decimal("144715207.5744")
    assert Decimal(str(fire_row["calculated_tax"])) == Decimal("144715200")


def test_etax_value_is_standard_value_not_property_tax_base(bundle):
    building = _one(bundle.buildings, building_id="SKR-SEORIN-B-001")
    property_tax = _one(
        bundle.calculations,
        reit_name="SK리츠",
        tax_name="건축물 재산세",
    )

    assert building["building_standard_value_nature"] == (
        "official_non_residential_building_standard_value_total"
    )
    assert building["property_tax_base_method"] == "building_standard_value_x_70_percent"
    assert building["fire_resource_tax_base_method"] == (
        "building_standard_value_without_70_percent_ratio"
    )
    assert Decimal(str(property_tax["official_value"])) == Decimal("40221752104.0")
    assert Decimal(str(property_tax["tax_base"])) == Decimal("28155226472.8")
    assert property_tax["verified_tax"] is pd.NA or pd.isna(property_tax["verified_tax"])


def test_area_5_3_reconciliation_and_sensitivity_are_preserved(bundle, snapshot):
    reconciliation = _one(
        bundle.reconciliation,
        reit_name="SK리츠",
        metric="parcel_area_register_to_building_ledger",
    )
    sensitivity = _one(
        bundle.reconciliation,
        reit_name="SK리츠",
        metric="parcel_area_difference_tax_sensitivity",
    )
    area_table = pd.read_csv(
        AREA_RECONCILIATION_PATH,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    ).iloc[0]

    assert snapshot["attached_lot_reconciliation"]["current_land_registry_status"] == "not_found"
    assert Decimal(str(reconciliation["variance"])) == Decimal("-5.3")
    assert Decimal(str(sensitivity["calculated_value"])) == Decimal("901567.1")
    assert area_table["reported_or_historical_area_m2"] == "5778.8"
    assert area_table["current_land_register_area_m2"] == "5773.5"
    assert area_table["difference_m2"] == "5.3"
    assert area_table["attached_lot_91_inclusion_status"] == "unverified"
    assert area_table["calculation_area_m2"] == "5773.5"
    assert area_table["estimated_pre_rounding_tax_effect_krw"] == "901567.1"


def test_evidence_matrix_has_all_sources_hashes_and_limitations(snapshot):
    matrix = pd.read_csv(
        EVIDENCE_MATRIX_PATH,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )
    required_columns = [
        "evidence_id", "metric_or_fact", "value", "unit", "source_name", "source_url",
        "source_date", "source_page", "source_quote", "retrieved_at", "sha256",
        "reliability", "verification_status", "used_in_calculation", "limitation",
    ]

    assert list(matrix.columns) == required_columns
    assert len(matrix) >= 16
    assert set(matrix["evidence_id"]) == {source["source_id"] for source in snapshot["sources"]}
    assert matrix["source_url"].str.startswith("https://").all()
    assert matrix["sha256"].map(lambda value: bool(re.fullmatch(r"[0-9a-f]{64}", value))).all()
    assert matrix["limitation"].str.strip().ne("").all()
    assert _one(matrix, evidence_id="seoul_land_use_99")["verification_status"] == (
        "cached_official_response_requery_degraded"
    )
    assert _one(matrix, evidence_id="seoul_etax_building_value")["verification_status"] == (
        "cached_official_response_hash_tls_legacy"
    )


def test_ui_uses_about_12_51_eok_and_safe_calculation_name(bundle):
    from ui_tax_v15 import _decimal_tax_total, _format_eok

    ui_text = UI_PATH.read_text(encoding="utf-8")
    memo_text = MEMO_PATH.read_text(encoding="utf-8")
    assets = bundle.assets[bundle.assets["reit_name"].eq("SK리츠")]
    asset_ids = set(assets["asset_id"].astype(str))
    dynamic_memo = build_tax_review_memo(
        "SK리츠",
        2026,
        assets,
        bundle.parcels[bundle.parcels["asset_id"].astype(str).isin(asset_ids)],
        bundle.buildings[bundle.buildings["asset_id"].astype(str).isin(asset_ids)],
        bundle.taxpayers[bundle.taxpayers["asset_id"].astype(str).isin(asset_ids)],
        bundle.calculations[bundle.calculations["reit_name"].eq("SK리츠")],
        bundle.validations[bundle.validations["reit_name"].eq("SK리츠")],
        bundle.requests[bundle.requests["reit_name"].eq("SK리츠")],
    )
    eligible = bundle.calculations[
        bundle.calculations["reit_name"].eq("SK리츠")
        & bundle.calculations["calculation_status"].isin(
            ["verified_notice", "official_source_calculated"]
        )
        & bundle.calculations["tax_name"].ne("토지 시가표준액")
    ]

    assert _decimal_tax_total(eligible) == AFTER_TOTAL
    assert _format_eok(AFTER_TOTAL) == "약 12.51억원"
    assert CALCULATION_LABEL in ui_text
    assert "행 단순 합계" not in ui_text
    assert CALCULATION_LABEL in memo_text
    assert CALCULATION_LABEL in dynamic_memo
    assert "1,250,710,968.55472원" in memo_text
    assert "1,250,710,968.55472원" in dynamic_memo
    assert "1,250,710,930원" in dynamic_memo
    assert "분리과세 적용요건 충족 판단" in dynamic_memo
    assert "실제 고지세액: 과세내역서 미확보" in dynamic_memo
    assert "고지세액 대사 상태: 미대사" in dynamic_memo
    assert "eligible_separated_public_reit" not in dynamic_memo
    assert "not_reconciled" not in dynamic_memo


def test_public_wording_avoids_confirmed_payment_claims(bundle):
    assets = bundle.assets[bundle.assets["reit_name"].eq("SK리츠")]
    asset_ids = set(assets["asset_id"].astype(str))
    dynamic_memo = build_tax_review_memo(
        "SK리츠",
        2026,
        assets,
        bundle.parcels[bundle.parcels["asset_id"].astype(str).isin(asset_ids)],
        bundle.buildings[bundle.buildings["asset_id"].astype(str).isin(asset_ids)],
        bundle.taxpayers[bundle.taxpayers["asset_id"].astype(str).isin(asset_ids)],
        bundle.calculations[bundle.calculations["reit_name"].eq("SK리츠")],
        bundle.validations[bundle.validations["reit_name"].eq("SK리츠")],
        bundle.requests[bundle.requests["reit_name"].eq("SK리츠")],
    )
    text = (
        UI_PATH.read_text(encoding="utf-8")
        + MEMO_PATH.read_text(encoding="utf-8")
        + dynamic_memo
    )
    banned = [
        "실제 보유세",
        "확정 보유세",
        "확정 납부세액",
        "신고 목적 확정세액",
    ]

    assert not any(term in text for term in banned)


def test_golden_values_are_not_reused_for_other_assets(bundle):
    other = bundle.calculations[bundle.calculations["reit_name"].ne("SK리츠")].copy()
    official_values = pd.to_numeric(other["official_value"], errors="coerce")

    assert not official_values.eq(369_215_325_000).any()
    assert not official_values.eq(40_221_752_104).any()
    assert not bundle.assets.loc[
        bundle.assets["reit_name"].ne("SK리츠"), "asset_id"
    ].eq(GOLDEN_ASSET_ID).any()


def test_golden_coverage_and_legal_rules_are_valid(bundle):
    coverage = _one(bundle.coverage, stock_code="395400")
    rules = bundle.rules[
        bundle.rules["rule_code"].isin(
            [
                "public_reit_definition",
                "public_reit_land_separation",
                "property_tax_obligor",
            ]
        )
    ]

    assert coverage["land_price_coverage"] == "100.0%"
    assert coverage["building_value_coverage"] == "100.0%"
    assert coverage["taxpayer_coverage"] == "100.0%"
    assert coverage["tax_calculation_status"] == "official_source_calculated"
    assert len(rules) == 3
    assert rules["validation_status"].eq("official_verified").all()
    assert rules["source_url"].str.startswith("https://").all()
