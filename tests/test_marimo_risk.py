from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pandas as pd

from marimo_risk import build_risk_view, load_risk_snapshot

DEFAULT_INPUTS = {
    "gdp_growth_pct": 2.6,
    "cpi_pct": 2.7,
    "policy_rate_pct": 2.5,
    "credit_spread_change_bp": 25,
    "refinancing_share_pct": 30,
    "cap_rate_shock_bp": 50,
}


def test_marimo_risk_loader_has_no_streamlit_runtime_dependency():
    source = Path("marimo_risk.py").read_text(encoding="utf-8")

    assert "import streamlit" not in source
    assert "from data_loader" not in source
    assert "from formatting" not in source


def test_marimo_risk_import_succeeds_when_streamlit_is_unavailable():
    script = """
import importlib.abc
import sys

class BlockStreamlit(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "streamlit" or fullname.startswith("streamlit."):
            raise ModuleNotFoundError("streamlit is intentionally unavailable")
        return None

sys.meta_path.insert(0, BlockStreamlit())
import marimo_risk
print(marimo_risk.scenario_presets())
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert "기준" in completed.stdout


def test_sk_risk_view_reuses_detailed_calculation_contract():
    snapshot = load_risk_snapshot()
    view = build_risk_view(
        snapshot,
        company_name="SK리츠",
        peer_group="전체 상장리츠",
        preset="기준",
        inputs=DEFAULT_INPUTS,
    )

    assert view.detail_available
    assert view.total_risk == 56.5
    assert pd.notna(view.scenario["stressed_ffo"])
    assert pd.notna(view.scenario["stressed_icr"])
    assert pd.notna(view.scenario["nav_change_pct"])
    assert pd.notna(view.scenario["stressed_ltv_proxy"])
    assert len(view.peer_comparison) == 5
    assert len(view.rmm) == 4
    assert len(view.sensitivity) == 25
    assert set(view.maturity_profile["maturity_year"].astype(int)) == {2026, 2027, 2028}


def test_other_reit_does_not_fabricate_asset_or_debt_detail():
    snapshot = load_risk_snapshot()
    other = snapshot.reit_master.loc[
        snapshot.reit_master["company_name"].ne("SK리츠"), "company_name"
    ].iloc[0]
    view = build_risk_view(
        snapshot,
        company_name=other,
        peer_group="전체 상장리츠",
        preset="확률가중",
        inputs=DEFAULT_INPUTS,
    )

    assert not view.detail_available
    assert view.assets.empty
    assert view.debt_schedule.empty
    assert view.maturity_profile.empty
    assert pd.isna(view.scenario["nav_change_pct"])
    assert pd.isna(view.scenario["stressed_ltv_proxy"])
    assert "상세 자산" in view.risk_flags[0]
