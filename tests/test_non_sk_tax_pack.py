from calculations_peer import calculate_peer_metrics, load_peer_snapshot
from calculations_tax import summarize_holding_tax_history
from calculations_tax_review_pack import (
    build_ffo_cash_outflow_stress,
    build_holding_tax_reconciliation,
    build_tax_issue_matrix,
    build_tax_request_list,
    build_tax_review_memo,
)
from dart_financials import company_options, get_recent_5y_financials, get_selected_company_profile, load_reit_master
from data_loader import load_data
from red_flag_engine import build_tax_red_flags, load_red_flag_rules
from tax_data_loader import build_company_tax_dataset, build_tax_history_from_company_tax_data, get_tax_source_status


def _first_non_sk_profile():
    master = load_reit_master()
    peer_snapshot = load_peer_snapshot()
    option = next(option for option in company_options(master) if "(395400)" not in option)
    return get_selected_company_profile(option, master, peer_snapshot), peer_snapshot


def test_non_sk_tax_pack_generates_all_core_outputs():
    profile, peer_snapshot = _first_non_sk_profile()
    recent_5y, _ = get_recent_5y_financials(profile, peer_snapshot, "")
    latest_kpi = load_data("2026-07-01")["kpis"].sort_values("period_end").iloc[-1].copy()
    latest_kpi["ffo_mn_krw"] = recent_5y.sort_values("year").iloc[-1]["ffo_proxy"]

    company_tax = build_company_tax_dataset(profile["company_name"], peer_snapshot, profile)
    tax_history = build_tax_history_from_company_tax_data(company_tax)
    annual_summary = summarize_holding_tax_history(tax_history)
    reconciliation = build_holding_tax_reconciliation(tax_history, latest_kpi)
    ffo_stress = build_ffo_cash_outflow_stress(latest_kpi, annual_summary, 10.0, 5.0)
    metrics = calculate_peer_metrics(peer_snapshot)
    flags = build_tax_red_flags(profile["company_name"], metrics, load_red_flag_rules())
    data_basis = get_tax_source_status(profile["company_name"], company_tax)
    issue_matrix = build_tax_issue_matrix(flags, reconciliation, ffo_stress, data_basis)
    request_list = build_tax_request_list(issue_matrix)
    memo = build_tax_review_memo(profile, data_basis, issue_matrix, reconciliation, request_list, ffo_stress)

    assert not company_tax.empty
    assert company_tax["company_name"].eq(profile["company_name"]).all()
    assert {"source_type", "source_note"}.issubset(company_tax.columns)
    assert company_tax["source_type"].notna().all()
    assert company_tax["source_note"].notna().all()
    assert len(company_tax) > 1 or "회사 전체 추정" in company_tax["asset_name"].astype(str).tolist()
    assert not tax_history.empty
    assert not annual_summary.empty
    assert not reconciliation.empty
    assert not ffo_stress.empty
    assert not issue_matrix.empty
    assert not request_list.empty
    assert "Tax Review Memo 초안" in memo
    assert profile["company_name"] in memo
