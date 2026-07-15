from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.tax_v15.loaders import load_v15_bundle


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ASSET_ID = "SKR-SEOUL-SEORIN-001"
GOLDEN_TAXPAYER_ID = "SKR-TP-001"


@pytest.fixture(scope="module")
def bundle():
    return load_v15_bundle()


@pytest.fixture(scope="module")
def snapshot() -> dict:
    path = ROOT / "data" / "v15" / "golden_asset" / "sk_seorin_official_snapshot.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _one(frame: pd.DataFrame, **filters) -> pd.Series:
    selected = frame.copy()
    for column, value in filters.items():
        selected = selected[selected[column].fillna("").astype(str).eq(str(value))]
    assert len(selected) == 1
    return selected.iloc[0]


def test_golden_asset_official_inputs_are_connected(bundle, snapshot):
    asset = _one(bundle.assets, asset_id=GOLDEN_ASSET_ID)
    parcel = _one(bundle.parcels, asset_id=GOLDEN_ASSET_ID)
    building = _one(bundle.buildings, asset_id=GOLDEN_ASSET_ID)

    assert asset["stock_code"] == "395400"
    assert asset["road_address"] == "서울특별시 종로구 종로 26"
    assert parcel["pnu"] == "1111012300100990000"
    assert float(parcel["parcel_area_m2"]) == pytest.approx(5773.5)
    assert float(parcel["individual_land_price_per_m2"]) == 63_950_000
    assert float(parcel["assessed_land_value"]) == 369_215_325_000
    assert float(building["building_standard_value"]) == 40_221_752_104
    assert building["fire_risk_category"] == "large_fire_risk"
    assert float(building["fire_tax_multiplier"]) == 3
    assert snapshot["building"]["building_component_value"] + snapshot["building"][
        "facility_component_value"
    ] == snapshot["building"]["building_standard_value"]


def test_golden_asset_taxpayer_and_separation_are_source_calculated(bundle):
    taxpayer = _one(bundle.taxpayers, taxpayer_id=GOLDEN_TAXPAYER_ID)

    assert taxpayer["legal_owner"] == "대한토지신탁(주)"
    assert taxpayer["trustor"] == "에스케이위탁관리부동산투자회사(주)"
    assert taxpayer["tax_obligor"] == "에스케이위탁관리부동산투자회사(주)"
    assert taxpayer["tax_classification"] == "separated_public_reit"
    assert taxpayer["validation_status"] == "official_source_calculated"


def test_golden_asset_tax_results_match_official_inputs(bundle):
    calculations = bundle.calculations[
        bundle.calculations["reit_name"].eq("SK리츠")
        & pd.to_numeric(bundle.calculations["tax_year"], errors="coerce").eq(2026)
    ]

    expected = {
        ("토지 재산세", "parcel"): 516_901_455.0,
        ("재산세 도시지역분", "parcel"): 361_831_018.5,
        ("지방교육세", "parcel"): 103_380_291.0,
        ("건축물 재산세", "building"): 70_388_066.182,
        ("재산세 도시지역분", "building"): 39_417_317.06192,
        ("지방교육세", "building"): 14_077_613.2364,
        ("소방분 지역자원시설세", "building"): 144_715_207.5744,
        ("토지분 종합부동산세", "taxpayer"): 0.0,
        ("종합부동산세분 농어촌특별세", "taxpayer"): 0.0,
    }
    for (tax_name, scope), amount in expected.items():
        selected = calculations[calculations["tax_name"].eq(tax_name)]
        if scope == "parcel":
            selected = selected[selected["parcel_id"].fillna("").ne("")]
        elif scope == "building":
            selected = selected[selected["building_id"].fillna("").ne("")]
        else:
            selected = selected[
                selected["parcel_id"].fillna("").eq("")
                & selected["building_id"].fillna("").eq("")
            ]
        assert len(selected) == 1
        assert float(selected.iloc[0]["calculated_tax"]) == pytest.approx(amount)

    tax_rows = calculations[calculations["tax_name"].ne("토지 시가표준액")].copy()
    total = pd.to_numeric(tax_rows["calculated_tax"], errors="coerce").sum()
    assert total == pytest.approx(1_250_710_968.55472)


def test_golden_asset_is_not_mislabelled_as_notice_verified(bundle):
    calculations = bundle.calculations[bundle.calculations["reit_name"].eq("SK리츠")]
    reconciliation = _one(
        bundle.reconciliation,
        reit_name="SK리츠",
        metric="holding_tax_notice_reconciliation",
    )

    assert calculations["verified_tax"].isna().all()
    assert not calculations["calculation_status"].eq("verified_notice").any()
    assert pd.isna(reconciliation["disclosed_or_verified_value"])
    assert reconciliation["reviewer_status"] == "open"


def test_attached_lot_difference_remains_open(bundle, snapshot):
    reconciliation = _one(
        bundle.reconciliation,
        reit_name="SK리츠",
        metric="parcel_area_register_to_building_ledger",
    )

    assert snapshot["attached_lot_reconciliation"]["current_land_registry_status"] == "not_found"
    assert float(reconciliation["variance"]) == pytest.approx(-5.3)
    assert reconciliation["reviewer_status"] == "open"


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
