from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from calculations_holding_tax_bridge import build_holding_tax_bridge
from calculations_peer import calculate_peer_metrics, load_peer_snapshot
from calculations_scenario import korean_metric_label
from calculations_tax import summarize_holding_tax_history
from calculations_tax_review_pack import (
    build_ffo_cash_outflow_stress,
    build_holding_tax_reconciliation,
    build_tax_issue_matrix,
    build_tax_request_list,
    build_tax_review_memo,
)
from dart_financials import get_recent_5y_financials, get_selected_company_profile, load_reit_master
from metric_definitions import derive_book_nav_proxy, derive_ffo_proxy, derive_interest_bearing_debt
from red_flag_engine import build_tax_red_flags, load_red_flag_rules
from scripts.validation.run_v14_1_acceptance import run_acceptance
from tax_data_loader import build_company_tax_dataset, build_tax_history_from_company_tax_data
from tax_validation import validate_tax_inputs


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("company", "period", "current_debt", "total_debt"),
    [
        ("SK리츠", "2026Q1", 1_243_689.893284, 3_103_854.820967),
        ("롯데리츠", "2025H2", 603_273.619875, 1_307_019.777689),
        ("ESR켄달스퀘어리츠", "2025H2", 156_770.141523, 1_586_961.428286),
    ],
)
def test_validated_current_debt_and_period_mapping(company, period, current_debt, total_debt):
    peer = load_peer_snapshot()
    row = peer.loc[peer["company_name"].eq(company)].iloc[0]

    assert row["period"] == period
    assert row["borrowings_current"] == pytest.approx(current_debt)
    assert row["borrowings_total"] == pytest.approx(total_debt)
    assert row["interest_bearing_debt_completeness"] == "official_total_reconciled"


def test_snapshot_history_does_not_fabricate_prior_years():
    master = load_reit_master()
    peer = load_peer_snapshot()
    profile = get_selected_company_profile("1위 SK리츠 (395400)", master, peer)

    history, _ = get_recent_5y_financials(profile, peer, "")

    assert len(history) == 1
    assert history["period"].tolist() == ["2026Q1"]
    assert history["source_type"].tolist() == ["official_disclosure"]


def test_ffo_proxy_uses_operating_cash_flow_only():
    value, method = derive_ffo_proxy(
        snapshot_ffo_proxy=999,
        operating_cash_flow=120,
        operating_income=300,
        net_income=200,
    )
    missing, missing_method = derive_ffo_proxy(
        snapshot_ffo_proxy=999,
        operating_cash_flow=pd.NA,
        operating_income=300,
        net_income=200,
    )

    assert value == 120
    assert "영업활동현금흐름" in method
    assert pd.isna(missing)
    assert "미산정" in missing_method


def test_partial_debt_components_are_not_treated_as_total_debt():
    debt, method = derive_interest_bearing_debt(short_term_borrowings=100)
    fallback, fallback_method = derive_interest_bearing_debt(
        short_term_borrowings=100,
        fallback_interest_bearing_debt=650,
    )

    assert pd.isna(debt)
    assert "완전성 부족" in method
    assert fallback == 650
    assert "완전성 미확인" in fallback_method


def test_book_nav_requires_total_liabilities_even_when_equity_is_present():
    nav, method = derive_book_nav_proxy(1_000, pd.NA, total_equity=600)

    assert pd.isna(nav)
    assert "총부채 부족" in method


def test_holding_tax_bridge_reconciles_tax_base_rate_and_tax_amount():
    master = load_reit_master()
    peer = load_peer_snapshot()
    profile = get_selected_company_profile("1위 SK리츠 (395400)", master, peer)
    tax_data = build_company_tax_dataset(profile["company_name"], peer, profile)

    bridge = build_holding_tax_bridge(
        profile["company_name"],
        tax_data,
        peer,
        {"fair_market_value_ratio": 70.0, "effective_holding_tax_rate": 1.1},
    )
    row = bridge.iloc[0]

    assert row["계산 모델"] == "effective-rate estimate"
    assert row["과세표준 추정(억원)"] * row["적용 세율"] == pytest.approx(row["추정 보유세(억원)"])
    assert row["적용 세율"] == pytest.approx(29_500 / 2_014_579)
    assert row["세율 기준"] == "Snapshot 세액 / 추정 과세표준 역산"


def test_company_tax_history_keeps_only_observed_snapshot_and_no_fake_components():
    master = load_reit_master()
    peer = load_peer_snapshot()
    profile = get_selected_company_profile("1위 SK리츠 (395400)", master, peer)
    tax_data = build_company_tax_dataset(profile["company_name"], peer, profile)

    history = build_tax_history_from_company_tax_data(tax_data)
    summary = summarize_holding_tax_history(history)

    assert len(history) == 1
    assert history["history_kind"].eq("snapshot_single_period").all()
    assert history[["재산세본세_백만원", "도시지역분_백만원", "지방교육세_백만원"]].isna().all().all()
    assert pd.isna(summary.loc[0, "재산세본세_백만원"])
    assert pd.isna(history.loc[0, "보유세_5년누적증가_%"])


def test_official_price_growth_rule_no_longer_uses_holding_tax_to_ffo():
    rules = json.loads((PROJECT_ROOT / "data" / "red_flag_rules.json").read_text(encoding="utf-8"))
    rule = next(item for item in rules["tax"] if item["id"] == "official_price_growth_placeholder")

    assert rule["metric"] == "official_price_growth_5y"


def test_overseas_reit_does_not_receive_domestic_holding_tax_estimate():
    master = load_reit_master()
    peer = load_peer_snapshot()
    profile = get_selected_company_profile("4위 제이알글로벌리츠 (348950)", master, peer)

    tax_data = build_company_tax_dataset(profile["company_name"], peer, profile)
    validation = validate_tax_inputs(profile["company_name"], tax_data, peer)

    assert tax_data["source_type"].eq("data_insufficient").all()
    assert tax_data["estimated_holding_tax"].isna().all()
    assert tax_data["official_price"].isna().all()
    assert validation["validation_status"] == "자료 부족"


def test_request_list_is_issue_driven_and_unique_by_document_name():
    master = load_reit_master()
    peer = load_peer_snapshot()
    metrics = calculate_peer_metrics(peer)
    profile = get_selected_company_profile("3위 롯데리츠 (330590)", master, peer)
    tax_data = build_company_tax_dataset(profile["company_name"], peer, profile)
    history = build_tax_history_from_company_tax_data(tax_data)
    summary = summarize_holding_tax_history(history)
    latest_kpi = pd.Series({"ffo_mn_krw": metrics.loc[metrics["company_name"].eq(profile["company_name"]), "ffo_proxy"].iloc[0]})
    reconciliation = build_holding_tax_reconciliation(history, latest_kpi)
    stress = build_ffo_cash_outflow_stress(latest_kpi, summary, 10.0, 5.0)
    flags = build_tax_red_flags(profile["company_name"], metrics, load_red_flag_rules())
    issue_matrix = build_tax_issue_matrix(flags, reconciliation, stress, "peer_snapshot_estimate")
    requests = build_tax_request_list(issue_matrix, "peer_snapshot_estimate", {"fallback_used": True})

    assert requests["요청자료"].is_unique
    assert "종합부동산세 고지서 및 과세내역" in requests["요청자료"].tolist()
    assert "자산별 법적 소유자·납세의무자 확인자료" in requests["요청자료"].tolist()
    assert requests["관련 이슈"].str.len().gt(0).all()


def test_tax_memo_uses_nine_section_ground_truth_structure():
    memo = build_tax_review_memo(
        {"company_name": "테스트리츠", "stock_code": "000000"},
        "peer_snapshot_estimate",
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        source_summary={"source_type": "data_insufficient", "source_note": "자료 부족"},
    )

    for section in range(1, 10):
        assert f"## {section}." in memo
    assert "확정 세액" in memo
    assert "데이터가 부족한 항목" in memo


def test_representative_company_acceptance_pack_passes():
    result = run_acceptance(write_output=False)

    assert set(result["company_name"]) == {
        "SK리츠",
        "롯데리츠",
        "ESR켄달스퀘어리츠",
        "제이알글로벌리츠",
    }
    assert result["status"].eq("passed").all(), result[
        ["company_name", "errors"]
    ].to_dict("records")


def test_property_value_leverage_is_not_exposed_as_generic_ltv():
    assert korean_metric_label("LTV proxy") == "투자부동산 가치 기준 차입비율 proxy"
    assert "LTV proxy" not in (PROJECT_ROOT / "ui_general.py").read_text(encoding="utf-8")


def test_public_peer_caption_does_not_expose_internal_source_type_code():
    ui_text = (PROJECT_ROOT / "ui_general.py").read_text(encoding="utf-8")

    assert "source_type=" not in ui_text
    assert "데이터 출처:" in ui_text
