from __future__ import annotations

import json
import shutil
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

import marimo_assurance as assurance_service
from marimo_assurance import (
    AssuranceDataUnavailableError,
    build_assurance_view_model,
    build_view_model_from_snapshot,
    load_assurance_snapshot,
)
from src.tax_v15.case_study import calculate_sensitivity_scenario
from src.tax_v15.loaders import load_v15_bundle

ROOT = Path(__file__).resolve().parents[1]


def _copy_v15(tmp_path: Path) -> Path:
    target = tmp_path / "v15"
    shutil.copytree(ROOT / "data" / "v15", target)
    return target


@pytest.fixture(scope="module")
def snapshot():
    return load_assurance_snapshot()


@pytest.fixture(scope="module")
def view_model(snapshot):
    return build_view_model_from_snapshot(snapshot, 0, 0)


def _scenario(model, name: str):
    rows = model.scenario_summary[model.scenario_summary["Scenario"].eq(name)]
    assert len(rows) == 1
    return rows.iloc[0]


def test_reference_scenarios_reconcile_to_streamlit_baseline(view_model):
    base = _scenario(view_model, "Base")
    moderate = _scenario(view_model, "Moderate")
    severe = _scenario(view_model, "Severe")

    assert base["총 보유세"] == Decimal("1250710968.55472")
    assert moderate["총 보유세"] == Decimal("1313250671.982456")
    assert severe["총 보유세"] == Decimal("1375790375.410192")
    assert moderate["Base 대비 증감액"] == Decimal("62539703.427736")
    assert severe["Base 대비 증감액"] == Decimal("125079406.855472")
    assert view_model.base_total == base["총 보유세"]


def test_open_issues_and_notice_reconciliation_are_fail_closed(view_model):
    open_issues = view_model.issue_matrix[
        view_model.issue_matrix["resolution_status"].eq("Open")
    ]

    assert view_model.kpis["p0_open"] == 3
    assert view_model.kpis["p1_open"] == 3
    assert view_model.kpis["notice_coverage"] == "0%"
    assert open_issues["priority"].value_counts().to_dict() == {"P0": 3, "P1": 3}
    assert view_model.reconciliation_status == "Not reconciled"
    assert len(view_model.verified_calculations) == 9
    assert view_model.verified_calculations["verified_tax"].isna().all()


def test_custom_scenario_reacts_from_same_snapshot_and_reuses_tax_engine(snapshot):
    unchanged = build_view_model_from_snapshot(snapshot, 0, 0)
    changed = build_view_model_from_snapshot(snapshot, 7, -3)
    expected, expected_detail = calculate_sensitivity_scenario(
        snapshot.case,
        "Custom",
        7,
        -3,
    )

    assert _scenario(changed, "Custom")["총 보유세"] == expected["총 보유세"]
    actual_detail = changed.scenario_detail[
        changed.scenario_detail["Scenario"].eq("Custom")
    ].reset_index(drop=True)
    assert actual_detail["계산세액"].tolist() == expected_detail["계산세액"].tolist()
    assert _scenario(changed, "Custom")["총 보유세"] != _scenario(
        unchanged, "Custom"
    )["총 보유세"]
    assert _scenario(changed, "Base")["총 보유세"] == _scenario(
        unchanged, "Base"
    )["총 보유세"]


def test_custom_scenario_keeps_existing_input_controls(snapshot):
    with pytest.raises(ValueError, match=r"-10%부터 \+20%"):
        build_view_model_from_snapshot(snapshot, -11, 0)
    with pytest.raises(ValueError, match="1% 단위"):
        build_assurance_view_model(0, 1.5, snapshot=snapshot)


def test_verified_snapshot_exposes_public_lineage_and_raw_workpaper(view_model):
    assert view_model.source_status == "verified_snapshot"
    assert view_model.fallback_reason is None
    assert set(view_model.snapshot_payload) == {
        "asset",
        "parcel",
        "building",
        "taxpayer",
        "retrieved_at",
        "open_items",
    }
    assert view_model.snapshot_payload["asset"]["asset_name"] == "SK서린빌딩"
    assert len(view_model.evidence_matrix) >= 16
    assert view_model.evidence_matrix["source_url"].str.startswith("https://").all()
    assert view_model.evidence_matrix["sha256"].str.fullmatch(r"[0-9a-f]{64}").all()
    assert "formula_text" in view_model.verified_calculations.columns
    assert "calculated_tax" in view_model.verified_calculations.columns


def test_missing_api_key_uses_snapshot_without_invoking_live_loader():
    calls: list[str] = []

    def must_not_run(api_key: str):
        calls.append(api_key)
        raise AssertionError("live loader must not run without an API key")

    loaded = load_assurance_snapshot(live_loader=must_not_run, api_key=None)
    model = build_view_model_from_snapshot(loaded, 0, 0)

    assert calls == []
    assert loaded.source_status == "snapshot_fallback"
    assert loaded.fallback_reason == "api_key_not_configured"
    assert model.is_fallback
    assert model.base_total == Decimal("1250710968.55472")


def test_live_failure_does_not_expose_secret_exception_or_trace():
    secret = "TOP-SECRET-API-KEY-987654"

    def failing_loader(api_key: str):
        raise RuntimeError(
            f"Traceback (most recent call last): serviceKey={api_key}; host failed"
        )

    loaded = load_assurance_snapshot(live_loader=failing_loader, api_key=secret)
    model = build_view_model_from_snapshot(loaded, 0, 0)
    public_text = "\n".join(
        [
            loaded.source_status,
            loaded.source_message,
            str(loaded.fallback_reason),
            model.source_lineage.to_string(index=False),
            model.evidence_matrix.to_string(index=False),
        ]
    )

    assert loaded.source_status == "snapshot_fallback"
    assert loaded.fallback_reason == "live_source_unavailable"
    assert secret not in public_text
    assert "Traceback" not in public_text
    assert "host failed" not in public_text


def test_missing_snapshot_raises_only_safe_public_error(tmp_path):
    with pytest.raises(AssuranceDataUnavailableError) as captured:
        load_assurance_snapshot(data_dir=tmp_path)

    public_error = str(captured.value)
    assert str(tmp_path) not in public_error
    assert "Traceback" not in public_error
    assert captured.value.code == "verified_snapshot_unavailable"


def test_snapshot_bundle_digest_rejects_semantic_tampering(tmp_path):
    target = _copy_v15(tmp_path)
    path = target / "golden_asset" / "sk_seorin_official_snapshot.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["asset"]["asset_name"] = "FORGED ASSET"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(AssuranceDataUnavailableError):
        load_assurance_snapshot(data_dir=target)


def test_snapshot_core_facts_must_match_csv_even_with_updated_digest(
    tmp_path,
    monkeypatch,
):
    target = _copy_v15(tmp_path)
    path = target / "golden_asset" / "sk_seorin_official_snapshot.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["parcel"]["individual_land_price_per_m2"] = 1
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(
        assurance_service,
        "VERIFIED_SNAPSHOT_BUNDLE_SHA256",
        assurance_service._snapshot_bundle_digest(target),
    )

    with pytest.raises(AssuranceDataUnavailableError):
        load_assurance_snapshot(data_dir=target)


def test_stored_calculation_detail_must_match_engine_reperformance(
    tmp_path,
    monkeypatch,
):
    target = _copy_v15(tmp_path)
    path = target / "tax_calculation_detail.csv"
    calculations = pd.read_csv(path, dtype=str, keep_default_na=False)
    mask = calculations["tax_name"].eq("토지 재산세") & calculations[
        "asset_id"
    ].eq("SKR-SEOUL-SEORIN-001")
    calculations.loc[mask, "calculated_tax"] = "999999999999999"
    calculations.loc[mask, "formula_text"] = "FORGED FORMULA"
    calculations.to_csv(path, index=False, encoding="utf-8-sig")
    monkeypatch.setattr(
        assurance_service,
        "VERIFIED_SNAPSHOT_BUNDLE_SHA256",
        assurance_service._snapshot_bundle_digest(target),
    )

    with pytest.raises(AssuranceDataUnavailableError):
        load_assurance_snapshot(data_dir=target)


def test_incomplete_live_bundle_is_not_labeled_live_verified():
    bundle = load_v15_bundle()
    incomplete = replace(
        bundle,
        coverage=bundle.coverage.iloc[0:0].copy(),
        documents=bundle.documents.iloc[0:0].copy(),
        validations=bundle.validations.iloc[0:0].copy(),
    )

    loaded = load_assurance_snapshot(
        live_loader=lambda _api_key: incomplete,
        api_key="LIVE-SECRET-1234",
    )

    assert loaded.source_status == "snapshot_fallback"
    assert loaded.fallback_reason == "live_source_unavailable"


@pytest.mark.parametrize("missing", ["taxpayer", "blocked_building"])
def test_view_model_rejects_missing_or_blocked_required_tax_items(snapshot, missing):
    case = snapshot.case
    if missing == "taxpayer":
        unsafe_case = replace(case, taxpayers=case.taxpayers.iloc[0:0].copy())
    else:
        buildings = case.buildings.copy()
        buildings.loc[:, "validation_status"] = "unverified"
        unsafe_case = replace(case, buildings=buildings)

    with pytest.raises(ValueError):
        build_view_model_from_snapshot(replace(snapshot, case=unsafe_case))


def test_service_module_has_no_ui_runtime_dependency():
    source = (ROOT / "marimo_assurance.py").read_text(encoding="utf-8")

    assert "import streamlit" not in source
    assert "import marimo" not in source
    assert "import traceback" not in source
