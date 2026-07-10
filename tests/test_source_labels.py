import pandas as pd

from calculations_peer import load_peer_snapshot
from dart_financials import company_options, get_selected_company_profile, load_reit_master
from tax_data_loader import build_company_tax_dataset, get_tax_source_summary


def test_tax_dataset_exposes_source_type_and_source_note_for_fallback_rows():
    master = load_reit_master()
    peer_snapshot = load_peer_snapshot()
    option = next(option for option in company_options(master) if "(395400)" not in option)
    profile = get_selected_company_profile(option, master, peer_snapshot)

    company_tax = build_company_tax_dataset(profile["company_name"], peer_snapshot, profile)
    summary = get_tax_source_summary(profile["company_name"], company_tax)

    assert {"source_type", "source_note"}.issubset(company_tax.columns)
    assert company_tax["source_type"].notna().all()
    assert company_tax["source_note"].notna().all()
    assert summary["source_type"]
    assert summary["source_note"]
    assert summary["scope_label"] in {"회사 전체 Snapshot 기반 추정", "예비 추정", "데이터 부족", "자산별 상세"}


def test_missing_asset_level_data_is_labeled_as_estimate_or_data_insufficient():
    company_tax = build_company_tax_dataset(
        "테스트데이터부족리츠",
        peer_snapshot=pd.DataFrame(),
        company_profile={"stock_code": "000000", "dart_corp_code": "sample_missing"},
        tax_snapshot=pd.DataFrame(columns=["company_name"]),
    )
    summary = get_tax_source_summary("테스트데이터부족리츠", company_tax)

    assert not company_tax.empty
    assert company_tax["asset_name"].iloc[0] == "회사 전체 추정"
    assert company_tax["source_type"].notna().all()
    assert company_tax["source_type"].iloc[0] == "data_insufficient"
    assert "부족" in summary["scope_label"] or "data_insufficient" in summary["source_type"]
    assert summary["korean_label"] == "데이터 부족"
    assert summary["reliability_level"] == "부족"
