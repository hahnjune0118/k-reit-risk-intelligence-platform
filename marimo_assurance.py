"""Pure-Python assurance service used by the Marimo application.

This module deliberately has no Streamlit or Marimo dependency.  It adapts the
source-backed v15 tax engine into immutable containers that reactive UI cells
can consume without reloading the snapshot for every widget change.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import quote, quote_plus

import pandas as pd

from src.tax_v15.calculators.engine import calculate_holding_tax_detail
from src.tax_v15.case_study import (
    CALCULATED_STATUSES,
    GOLDEN_ASSET_ID,
    GOLDEN_TAXPAYER_ID,
    GoldenCaseData,
    build_case_kpis,
    build_case_request_list,
    build_sensitivity_scenarios,
    build_tax_issue_matrix,
    calculate_sensitivity_scenario,
    select_golden_case,
)
from src.tax_v15.constants import V15_DATA_DIR
from src.tax_v15.loaders import V15DataBundle, load_v15_bundle

SNAPSHOT_FILE = Path("golden_asset") / "sk_seorin_official_snapshot.json"
SNAPSHOT_SCHEMA_VERSION = "v15-golden-asset-2"
SNAPSHOT_TRUST_FILES = (
    "reit_master.csv",
    "coverage_manifest.csv",
    "source_document_manifest.csv",
    "asset_master.csv",
    "parcel_master.csv",
    "building_master.csv",
    "taxpayer_structure.csv",
    "tax_rule_master.csv",
    "tax_calculation_detail.csv",
    "reconciliation.csv",
    "request_list.csv",
    "validation_result.csv",
    SNAPSHOT_FILE.as_posix(),
)
# Trust anchor for the committed v15 bundle. Text is normalized for Windows/Linux
# line endings before hashing, so Git's autocrlf setting does not change the digest.
VERIFIED_SNAPSHOT_BUNDLE_SHA256 = (
    "a1b1c18d619d3ea38076a9a503e07df5fee891bf3ab395dd4d7a701bba9e58fa"
)

CALCULATION_KEY_COLUMNS = (
    "tax_year",
    "reit_name",
    "taxpayer_id",
    "asset_id",
    "parcel_id",
    "building_id",
    "tax_name",
    "tax_classification",
)
CALCULATION_NUMERIC_COLUMNS = (
    "official_value",
    "taxable_area",
    "ownership_share",
    "fair_market_value_ratio",
    "tax_base",
    "base_amount",
    "tax_rate",
    "multiplier",
    "calculated_tax",
)
CALCULATION_TEXT_COLUMNS = (
    "bracket",
    "calculation_status",
    "law_name",
    "article",
    "formula_text",
    "input_source",
    "source_url",
)

EVIDENCE_COLUMNS = [
    "evidence_id",
    "metric_or_fact",
    "value",
    "unit",
    "source_name",
    "source_url",
    "source_date",
    "source_page",
    "source_quote",
    "retrieved_at",
    "sha256",
    "reliability",
    "verification_status",
    "used_in_calculation",
    "limitation",
]

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:key|apiKey|api_key|serviceKey|service_key|crtfc_key|auth_key|"
    r"token|access_token)\b\s*[:=]\s*[\"']?)([^&\s\"',}<>]+)"
)
_TRACEBACK_MARKER = "Traceback (most recent call last)"

LiveBundleLoader = Callable[[str], V15DataBundle]


class AssuranceDataUnavailableError(RuntimeError):
    """Safe public error raised when neither live data nor Snapshot can load."""

    def __init__(self, code: str = "verified_snapshot_unavailable") -> None:
        self.code = code
        super().__init__(
            "검증된 Snapshot을 불러오지 못했습니다. data/v15 배포 파일을 확인해 주세요."
        )


@dataclass(frozen=True)
class AssuranceSnapshot:
    """Source data loaded once in a Marimo data cell."""

    case: GoldenCaseData
    coverage: pd.DataFrame
    source_lineage: pd.DataFrame
    evidence_matrix: pd.DataFrame
    snapshot_payload: dict[str, Any]
    source_status: str
    source_message: str
    fallback_reason: str | None = None

    @property
    def is_fallback(self) -> bool:
        return self.source_status == "snapshot_fallback"


@dataclass(frozen=True)
class AssuranceViewModel:
    """Calculated, presentation-neutral state for the three assurance pages."""

    case: GoldenCaseData
    coverage: pd.DataFrame
    source_lineage: pd.DataFrame
    evidence_matrix: pd.DataFrame
    snapshot_payload: dict[str, Any]
    scenario_summary: pd.DataFrame
    scenario_detail: pd.DataFrame
    verified_calculations: pd.DataFrame
    issue_matrix: pd.DataFrame
    request_list: pd.DataFrame
    kpis: dict[str, int | float | str]
    base_total: Decimal
    reconciliation_status: str
    source_status: str
    source_message: str
    fallback_reason: str | None = None

    @property
    def is_fallback(self) -> bool:
        return self.source_status == "snapshot_fallback"


def _redact_text(value: str, secrets: tuple[str, ...] = ()) -> str:
    """Remove credential-shaped values without importing Streamlit utilities."""
    text = str(value)
    if _TRACEBACK_MARKER in text:
        return "상세 오류는 공개하지 않습니다."
    text = _SECRET_ASSIGNMENT.sub(r"\1[REDACTED]", text)
    for secret in secrets:
        if len(secret) < 4:
            continue
        for candidate in {secret, quote(secret, safe=""), quote_plus(secret)}:
            if candidate:
                text = text.replace(candidate, "[REDACTED]")
    return text


def _public_value(value: Any, secrets: tuple[str, ...] = ()) -> Any:
    if isinstance(value, str):
        return _redact_text(value, secrets)
    if isinstance(value, Mapping):
        return {
            str(key): _public_value(item, secrets)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_public_value(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(_public_value(item, secrets) for item in value)
    return value


def _public_frame(
    frame: pd.DataFrame | None,
    secrets: tuple[str, ...] = (),
) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame()
    result = frame.copy(deep=True)
    for column in result.columns:
        if pd.api.types.is_object_dtype(result[column].dtype) or isinstance(
            result[column].dtype, pd.StringDtype
        ):
            result[column] = result[column].map(
                lambda value: _redact_text(value, secrets)
                if isinstance(value, str)
                else value
            )
    return result


def _public_case(
    case: GoldenCaseData,
    secrets: tuple[str, ...] = (),
) -> GoldenCaseData:
    return replace(
        case,
        assets=_public_frame(case.assets, secrets),
        parcels=_public_frame(case.parcels, secrets),
        buildings=_public_frame(case.buildings, secrets),
        taxpayers=_public_frame(case.taxpayers, secrets),
        rules=_public_frame(case.rules, secrets),
        calculations=_public_frame(case.calculations, secrets),
        validations=_public_frame(case.validations, secrets),
        requests=_public_frame(case.requests, secrets),
        reconciliation=_public_frame(case.reconciliation, secrets),
    )


def _snapshot_bundle_digest(data_dir: Path) -> str:
    digest = sha256()
    for relative_name in SNAPSHOT_TRUST_FILES:
        path = data_dir / relative_name
        text = path.read_text(encoding="utf-8-sig")
        canonical = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        digest.update(relative_name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(canonical)).encode("ascii"))
        digest.update(b"\0")
        digest.update(canonical)
    return digest.hexdigest()


def _clean_text(value: Any) -> str:
    if value is None or value is pd.NA:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _boolean(value: Any) -> bool | None:
    text = _clean_text(value).lower()
    if text in {"true", "1", "yes", "verified"}:
        return True
    if text in {"false", "0", "no", "unverified"}:
        return False
    return None


def _validate_snapshot_facts(
    case: GoldenCaseData,
    raw_snapshot: Mapping[str, Any],
) -> None:
    if raw_snapshot.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError("snapshot schema mismatch")
    if int(raw_snapshot.get("tax_year", -1)) != case.tax_year:
        raise ValueError("snapshot tax year mismatch")
    if _clean_text(raw_snapshot.get("retrieved_at")) == "":
        raise ValueError("snapshot retrieval timestamp missing")

    frames = {
        "asset": case.assets,
        "parcel": case.parcels,
        "building": case.buildings,
        "taxpayer": case.taxpayers,
    }
    if any(len(frame) != 1 for frame in frames.values()):
        raise ValueError("golden case cardinality mismatch")

    text_fields = {
        "asset": (
            "stock_code", "reit_name", "asset_id", "asset_name", "road_address",
            "lot_address", "acquisition_date", "purpose_use",
            "investment_holding_type", "title_holding_type", "registered_owner",
            "trustee", "trustor", "beneficial_owner", "property_taxpayer",
        ),
        "parcel": ("parcel_id", "pnu", "tax_urban_area_status"),
        "building": (
            "building_id", "main_use", "structure_type",
            "building_standard_value_nature", "property_tax_base_method",
            "fire_resource_tax_base_method", "fire_risk_category",
            "fire_tax_multiplier_status", "fire_tax_evidence_page",
            "fire_tax_evidence_quote", "urban_area_status",
        ),
        "taxpayer": (
            "taxpayer_id", "assessment_date_ownership_basis_status",
            "tax_classification", "statutory_eligibility_status",
            "actual_notice_classification", "legal_review_status",
            "notice_reconciliation_status",
        ),
    }
    numeric_fields = {
        "asset": ("ownership_share",),
        "parcel": (
            "parcel_area_m2", "taxable_area_m2", "ownership_share",
            "individual_land_price_per_m2", "official_price_year",
            "assessed_land_value",
        ),
        "building": (
            "building_register_id", "gross_floor_area_m2",
            "building_standard_value_year", "building_standard_value",
            "fire_tax_multiplier",
        ),
    }
    boolean_fields = {
        "taxpayer": (
            "public_reit_qualified", "purpose_business_use",
            "assessment_date_ownership_verified",
        )
    }

    for section, fields in text_fields.items():
        snapshot_row = raw_snapshot[section]
        case_row = frames[section].iloc[0]
        for field in fields:
            if _clean_text(snapshot_row.get(field)) != _clean_text(case_row.get(field)):
                raise ValueError(f"snapshot fact mismatch: {section}.{field}")
    for section, fields in numeric_fields.items():
        snapshot_row = raw_snapshot[section]
        case_row = frames[section].iloc[0]
        for field in fields:
            if _decimal(snapshot_row.get(field)) != _decimal(case_row.get(field)):
                raise ValueError(f"snapshot fact mismatch: {section}.{field}")
    for section, fields in boolean_fields.items():
        snapshot_row = raw_snapshot[section]
        case_row = frames[section].iloc[0]
        for field in fields:
            if _boolean(snapshot_row.get(field)) != _boolean(case_row.get(field)):
                raise ValueError(f"snapshot fact mismatch: {section}.{field}")


def _calculation_records(frame: pd.DataFrame) -> dict[tuple[str, ...], Mapping[str, Any]]:
    records: dict[tuple[str, ...], Mapping[str, Any]] = {}
    for row in frame.to_dict("records"):
        key_parts = []
        for column in CALCULATION_KEY_COLUMNS:
            value = row.get(column)
            if column == "tax_year":
                number = _decimal(value)
                key_parts.append("" if number is None else str(int(number)))
            else:
                key_parts.append(_clean_text(value))
        key = tuple(key_parts)
        if key in records:
            raise ValueError("duplicate calculation grain")
        records[key] = row
    return records


def _reperform_and_reconcile(case: GoldenCaseData) -> pd.DataFrame:
    if any(
        len(frame) != 1
        for frame in (case.assets, case.parcels, case.buildings, case.taxpayers)
    ):
        raise ValueError("golden case cardinality mismatch")
    reperformed = calculate_holding_tax_detail(
        case.reit_name,
        case.assets,
        case.parcels,
        case.buildings,
        case.taxpayers,
        case.rules,
        case.tax_year,
    )
    if len(reperformed) != 10:
        raise ValueError("reperformance calculation grain mismatch")
    blocked = ~reperformed["calculation_status"].isin(CALCULATED_STATUSES)
    tax_rows = reperformed["tax_name"].ne("토지 시가표준액")
    if blocked.any() or reperformed.loc[tax_rows, "calculated_tax"].isna().any():
        raise ValueError("reperformance contains blocked tax items")

    stored_records = _calculation_records(case.calculations)
    rerun_records = _calculation_records(reperformed)
    if stored_records.keys() != rerun_records.keys():
        raise ValueError("stored calculation grain mismatch")
    for key, rerun in rerun_records.items():
        stored = stored_records[key]
        for column in CALCULATION_NUMERIC_COLUMNS:
            if _decimal(stored.get(column)) != _decimal(rerun.get(column)):
                raise ValueError(f"stored calculation mismatch: {column}")
        for column in CALCULATION_TEXT_COLUMNS:
            if _clean_text(stored.get(column)) != _clean_text(rerun.get(column)):
                raise ValueError(f"stored calculation mismatch: {column}")
    return reperformed


def _validate_live_bundle(bundle: V15DataBundle, case: GoldenCaseData) -> None:
    coverage = bundle.coverage[
        bundle.coverage["stock_code"].fillna("").astype(str).eq(case.stock_code)
    ]
    lineage = bundle.documents[
        bundle.documents["reit_name"].fillna("").astype(str).eq(case.reit_name)
    ]
    if len(coverage) != 1 or case.validations.empty or lineage.empty:
        raise ValueError("live assurance evidence incomplete")
    if _clean_text(coverage.iloc[0].get("tax_calculation_status")) != (
        "official_source_calculated"
    ):
        raise ValueError("live calculation coverage incomplete")
    if not all(
        re.fullmatch(r"[0-9a-f]{64}", _clean_text(row.get("sha256")))
        and _clean_text(row.get("source_url")).startswith("https://")
        and _clean_text(row.get("extraction_status"))
        for row in lineage.to_dict("records")
    ):
        raise ValueError("live evidence integrity failed")


def _read_verified_snapshot(data_dir: Path) -> dict[str, Any]:
    try:
        if _snapshot_bundle_digest(data_dir) != VERIFIED_SNAPSHOT_BUNDLE_SHA256:
            raise ValueError("snapshot trust anchor mismatch")
        payload = json.loads((data_dir / SNAPSHOT_FILE).read_text(encoding="utf-8"))
        required_objects = ("asset", "parcel", "building", "taxpayer")
        if not all(isinstance(payload.get(name), dict) for name in required_objects):
            raise ValueError("snapshot objects missing")
        sources = payload.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ValueError("snapshot evidence missing")
        if not all(
            re.fullmatch(r"[0-9a-f]{64}", str(source.get("sha256", "")))
            and str(source.get("source_url", "")).startswith("https://")
            for source in sources
        ):
            raise ValueError("snapshot evidence integrity failed")
        return payload
    except Exception:  # noqa: BLE001 - normalize malformed evidence to fail-closed
        raise AssuranceDataUnavailableError() from None


def _snapshot_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return only fields intended for the public assurance UI."""
    return _public_value(
        {
            "asset": payload.get("asset", {}),
            "parcel": payload.get("parcel", {}),
            "building": payload.get("building", {}),
            "taxpayer": payload.get("taxpayer", {}),
            "retrieved_at": payload.get("retrieved_at", ""),
            "open_items": payload.get("open_items", []),
        }
    )


def _evidence_from_snapshot(payload: Mapping[str, Any]) -> pd.DataFrame:
    retrieved_at = payload.get("retrieved_at", "")
    rows = []
    for source in payload.get("sources", []):
        rows.append(
            {
                "evidence_id": source.get("source_id", ""),
                "metric_or_fact": source.get("metric_or_fact", ""),
                "value": source.get("value", ""),
                "unit": source.get("unit", ""),
                "source_name": source.get("document_name", ""),
                "source_url": source.get("source_url", ""),
                "source_date": source.get("document_date", ""),
                "source_page": source.get("relevant_pages", ""),
                "source_quote": source.get("source_quote", ""),
                "retrieved_at": source.get("retrieved_at", retrieved_at),
                "sha256": source.get("sha256", ""),
                "reliability": source.get("reliability", ""),
                "verification_status": source.get("verification_status", ""),
                "used_in_calculation": source.get("used_in_calculation", False),
                "limitation": source.get("limitation", ""),
            }
        )
    return _public_frame(pd.DataFrame(rows, columns=EVIDENCE_COLUMNS))


def _evidence_from_lineage(lineage: pd.DataFrame) -> pd.DataFrame:
    """Best-effort evidence view for a future live V15 bundle."""
    rows = []
    for _, source in lineage.iterrows():
        rows.append(
            {
                "evidence_id": source.get("sha256", ""),
                "metric_or_fact": source.get("document_type", ""),
                "value": "",
                "unit": "",
                "source_name": source.get("document_name", ""),
                "source_url": source.get("source_url", ""),
                "source_date": source.get("document_date", ""),
                "source_page": source.get("relevant_pages", ""),
                "source_quote": source.get("notes", ""),
                "retrieved_at": source.get("downloaded_at", ""),
                "sha256": source.get("sha256", ""),
                "reliability": "official_source_pending_reviewer",
                "verification_status": source.get("extraction_status", ""),
                "used_in_calculation": pd.NA,
                "limitation": source.get("notes", ""),
            }
        )
    return pd.DataFrame(rows, columns=EVIDENCE_COLUMNS)


def _payload_from_case(case: GoldenCaseData) -> dict[str, Any]:
    def first_record(frame: pd.DataFrame) -> dict[str, Any]:
        return {} if frame.empty else frame.iloc[0].dropna().to_dict()

    open_items = case.validations.loc[
        ~case.validations["validation_status"].fillna("").astype(str).isin(
            {"passed", "verified", "official_source_calculated"}
        ),
        "message",
    ].dropna().astype(str).tolist()
    return {
        "asset": first_record(case.assets),
        "parcel": first_record(case.parcels),
        "building": first_record(case.buildings),
        "taxpayer": first_record(case.taxpayers),
        "retrieved_at": "live",
        "open_items": open_items,
    }


def _decimal(value: Any) -> Decimal | None:
    if value is None or pd.isna(value):
        return None
    return Decimal(str(value))


def _validate_case_integrity(
    case: GoldenCaseData,
    raw_snapshot: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Fail closed if source facts, rules, and stored reconciliation diverge."""
    if raw_snapshot is not None:
        _validate_snapshot_facts(case, raw_snapshot)
        if str(raw_snapshot["asset"].get("asset_id", "")) != GOLDEN_ASSET_ID:
            raise ValueError("snapshot asset mismatch")
        if str(raw_snapshot["taxpayer"].get("taxpayer_id", "")) != GOLDEN_TAXPAYER_ID:
            raise ValueError("snapshot taxpayer mismatch")

    reperformed = _reperform_and_reconcile(case)
    base, _ = calculate_sensitivity_scenario(case, "Base", 0, 0)
    rows = case.reconciliation[
        case.reconciliation["metric"]
        .fillna("")
        .astype(str)
        .eq("holding_tax_notice_reconciliation")
    ]
    if len(rows) != 1:
        raise ValueError("holding-tax reconciliation row missing")
    stored_total = _decimal(rows.iloc[0].get("calculated_value"))
    if stored_total is None or stored_total != base["총 보유세"]:
        raise ValueError("snapshot calculation does not reconcile")
    return reperformed


def _build_snapshot(
    bundle: V15DataBundle,
    *,
    source_status: str,
    source_message: str,
    fallback_reason: str | None,
    raw_snapshot: Mapping[str, Any] | None,
    api_key: str = "",
) -> AssuranceSnapshot:
    case = select_golden_case(bundle)
    if source_status == "live_verified":
        _validate_live_bundle(bundle, case)
    reperformed = _validate_case_integrity(case, raw_snapshot)
    case = replace(case, calculations=reperformed)
    secrets = (api_key,) if api_key else ()
    case = _public_case(case, secrets)
    coverage = bundle.coverage[
        bundle.coverage["stock_code"].fillna("").astype(str).eq(case.stock_code)
    ].copy()
    lineage = bundle.documents[
        bundle.documents["reit_name"].fillna("").astype(str).eq(case.reit_name)
    ].copy()
    coverage = _public_frame(coverage, secrets)
    lineage = _public_frame(lineage, secrets)

    if raw_snapshot is None:
        payload = _public_value(_payload_from_case(case), secrets)
        evidence = _public_frame(_evidence_from_lineage(lineage), secrets)
    else:
        payload = _public_value(_snapshot_payload(raw_snapshot), secrets)
        evidence = _public_frame(_evidence_from_snapshot(raw_snapshot), secrets)

    return AssuranceSnapshot(
        case=case,
        coverage=coverage,
        source_lineage=lineage,
        evidence_matrix=evidence,
        snapshot_payload=payload,
        source_status=source_status,
        source_message=source_message,
        fallback_reason=fallback_reason,
    )


def _load_local_snapshot(
    data_dir: Path,
    *,
    source_status: str,
    source_message: str,
    fallback_reason: str | None,
) -> AssuranceSnapshot:
    try:
        raw_snapshot = _read_verified_snapshot(data_dir)
        bundle = load_v15_bundle(data_dir)
        return _build_snapshot(
            bundle,
            source_status=source_status,
            source_message=source_message,
            fallback_reason=fallback_reason,
            raw_snapshot=raw_snapshot,
        )
    except AssuranceDataUnavailableError:
        raise
    except Exception:  # noqa: BLE001 - preserve fail-closed public error boundary
        raise AssuranceDataUnavailableError() from None


def load_assurance_snapshot(
    data_dir: str | Path | None = None,
    *,
    live_loader: LiveBundleLoader | None = None,
    api_key: str | None = None,
) -> AssuranceSnapshot:
    """Load a verified live bundle when requested, otherwise the Git snapshot.

    Passing a ``live_loader`` opts into a live refresh.  A missing API key or
    any live validation error falls back to the repository Snapshot without
    retaining the exception text or credential in the public return value.
    """
    snapshot_dir = Path(data_dir) if data_dir is not None else V15_DATA_DIR
    clean_key = str(api_key or "").strip()

    if live_loader is not None and clean_key:
        try:
            bundle = live_loader(clean_key)
            return _build_snapshot(
                bundle,
                source_status="live_verified",
                source_message="공식 API 갱신 자료가 검증 통제를 통과했습니다.",
                fallback_reason=None,
                raw_snapshot=None,
                api_key=clean_key,
            )
        except Exception:  # noqa: BLE001 - live-source failure falls back safely
            return _load_local_snapshot(
                snapshot_dir,
                source_status="snapshot_fallback",
                source_message=(
                    "공식 API 갱신 자료를 검증하지 못해 GitHub 검증 Snapshot으로 "
                    "안전하게 전환했습니다."
                ),
                fallback_reason="live_source_unavailable",
            )

    if live_loader is not None:
        return _load_local_snapshot(
            snapshot_dir,
            source_status="snapshot_fallback",
            source_message=(
                "API 키가 없어 GitHub 검증 Snapshot으로 안전하게 전환했습니다."
            ),
            fallback_reason="api_key_not_configured",
        )

    return _load_local_snapshot(
        snapshot_dir,
        source_status="verified_snapshot",
        source_message=(
            "GitHub 검증 Snapshot(data/v15) 기반입니다. 공식 입력자료와 "
            "Tax Rule Master로 독립 재수행합니다."
        ),
        fallback_reason=None,
    )


def _reconciliation_status(case: GoldenCaseData) -> str:
    """Return reconciled only when both amount evidence and review are closed."""
    rows = case.reconciliation[
        case.reconciliation["metric"]
        .fillna("")
        .astype(str)
        .eq("holding_tax_notice_reconciliation")
    ]
    if len(rows) != 1:
        return "Not reconciled"
    row = rows.iloc[0]
    actual_amount = _decimal(row.get("disclosed_or_verified_value"))
    reviewer_status = str(row.get("reviewer_status", "")).strip().lower()
    closed = reviewer_status in {"closed", "reviewed", "approved", "reconciled"}
    return "Reconciled" if actual_amount is not None and closed else "Not reconciled"


def build_view_model_from_snapshot(
    snapshot: AssuranceSnapshot,
    custom_land_change_pct: int = 0,
    custom_building_change_pct: int = 0,
) -> AssuranceViewModel:
    """Recalculate only widget-dependent state from an already loaded snapshot."""
    reperformed = _validate_case_integrity(snapshot.case)
    case = replace(snapshot.case, calculations=reperformed)
    scenario_summary, scenario_detail = build_sensitivity_scenarios(
        case,
        custom_land_change_pct,
        custom_building_change_pct,
    )
    issue_matrix = build_tax_issue_matrix(case)
    request_list = build_case_request_list(issue_matrix, case.requests)
    kpis = build_case_kpis(case, issue_matrix)

    base_rows = scenario_summary[scenario_summary["Scenario"].eq("Base")]
    if len(base_rows) != 1:
        raise AssuranceDataUnavailableError("base_scenario_unavailable")
    base_total = base_rows.iloc[0]["총 보유세"]

    verified = case.calculations[
        case.calculations["calculation_status"].isin(CALCULATED_STATUSES)
        & case.calculations["tax_name"].ne("토지 시가표준액")
    ].copy()

    return AssuranceViewModel(
        case=case,
        coverage=snapshot.coverage.copy(),
        source_lineage=snapshot.source_lineage.copy(),
        evidence_matrix=snapshot.evidence_matrix.copy(),
        snapshot_payload=dict(snapshot.snapshot_payload),
        scenario_summary=scenario_summary,
        scenario_detail=scenario_detail,
        verified_calculations=verified,
        issue_matrix=issue_matrix,
        request_list=request_list,
        kpis=kpis,
        base_total=base_total,
        reconciliation_status=_reconciliation_status(case),
        source_status=snapshot.source_status,
        source_message=snapshot.source_message,
        fallback_reason=snapshot.fallback_reason,
    )


def build_assurance_view_model(
    custom_land_change_pct: int = 0,
    custom_building_change_pct: int = 0,
    *,
    snapshot: AssuranceSnapshot | None = None,
    data_dir: str | Path | None = None,
    live_loader: LiveBundleLoader | None = None,
    api_key: str | None = None,
) -> AssuranceViewModel:
    """Convenience entrypoint for non-reactive callers and tests."""
    loaded = snapshot or load_assurance_snapshot(
        data_dir,
        live_loader=live_loader,
        api_key=api_key,
    )
    return build_view_model_from_snapshot(
        loaded,
        custom_land_change_pct,
        custom_building_change_pct,
    )


__all__ = [
    "AssuranceDataUnavailableError",
    "AssuranceSnapshot",
    "AssuranceViewModel",
    "build_assurance_view_model",
    "build_view_model_from_snapshot",
    "load_assurance_snapshot",
]
