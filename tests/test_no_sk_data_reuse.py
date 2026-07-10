from pathlib import Path

import pandas as pd

from calculations_peer import load_peer_snapshot
from dart_financials import company_options, get_selected_company_profile, load_reit_master
from tax_data_loader import build_company_tax_dataset, build_tax_history_from_company_tax_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _non_sk_profile():
    master = load_reit_master()
    peer_snapshot = load_peer_snapshot()
    option = next(option for option in company_options(master) if "(395400)" not in option)
    return get_selected_company_profile(option, master, peer_snapshot), peer_snapshot


def _sk_asset_names() -> list[str]:
    asset_path = PROJECT_ROOT / "data" / "sk_reit_asset_metrics.csv"
    if not asset_path.exists():
        return []
    assets = pd.read_csv(asset_path)
    return assets.get("asset_name", pd.Series(dtype="object")).dropna().astype(str).tolist()


def test_non_sk_tax_dataset_never_reuses_sk_company_or_asset_rows():
    profile, peer_snapshot = _non_sk_profile()
    company_tax = build_company_tax_dataset(profile["company_name"], peer_snapshot, profile)
    tax_history = build_tax_history_from_company_tax_data(company_tax)
    rendered_text = "\n".join(
        [
            company_tax.astype(str).to_csv(index=False),
            tax_history.astype(str).to_csv(index=False),
        ]
    )

    assert not company_tax.empty
    assert company_tax["company_name"].eq(profile["company_name"]).all()
    assert "SK리츠" not in company_tax["company_name"].astype(str).tolist()
    assert company_tax.iloc[0]["company_name"] == profile["company_name"]

    for asset_name in _sk_asset_names():
        assert asset_name not in rendered_text
