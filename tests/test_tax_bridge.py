import pandas as pd
import pytest

from calculations_holding_tax_bridge import (
    build_holding_tax_bridge,
    calculate_estimated_holding_tax,
    calculate_estimated_tax_base,
    classify_holding_tax_burden,
    safe_ratio,
)
from calculations_peer import load_peer_snapshot
from dart_financials import company_options, get_selected_company_profile, load_reit_master
from tax_data_loader import build_company_tax_dataset


def test_bridge_pure_calculations_are_stable():
    assert safe_ratio(10, 0) is pd.NA
    assert safe_ratio(10, 5) == 2
    assert calculate_estimated_tax_base(1000, 70) == pytest.approx(700)
    assert calculate_estimated_tax_base(1000, 0.7) == pytest.approx(700)
    assert calculate_estimated_holding_tax(700, 1.1) == pytest.approx(7.7)
    assert calculate_estimated_holding_tax(700, 0.011) == pytest.approx(7.7)


def test_bridge_classifies_high_peer_burden():
    peers = pd.Series([0.05, 0.10, 0.20, 0.30])
    assert classify_holding_tax_burden(0.31, peers, "peer_snapshot_estimate") == "높음"
    assert classify_holding_tax_burden(pd.NA, peers, "peer_snapshot_estimate") == "데이터 부족"


def test_non_sk_bridge_uses_company_level_fallback_not_sk_assets():
    master = load_reit_master()
    peer_snapshot = load_peer_snapshot()
    option = next(option for option in company_options(master) if "(395400)" not in option)
    profile = get_selected_company_profile(option, master, peer_snapshot)
    company_tax = build_company_tax_dataset(profile["company_name"], peer_snapshot, profile)

    bridge = build_holding_tax_bridge(
        profile["company_name"],
        company_tax,
        peer_snapshot,
        {"fair_market_value_ratio": 70.0, "effective_holding_tax_rate": 1.1},
    )

    assert not bridge.empty
    assert bridge["회사명"].eq(profile["company_name"]).all()
    assert bridge["자산명"].tolist() == ["회사 전체 추정"]
    assert bridge["지역"].tolist() == ["회사 전체"]
    assert "peer estimated_holding_tax" in bridge["데이터 기준"].tolist()
    assert bridge["source_type"].iloc[0] == "peer_snapshot_estimate"
