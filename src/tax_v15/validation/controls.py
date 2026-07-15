from __future__ import annotations

import re
import hashlib
from pathlib import Path

import pandas as pd

from ..constants import CALCULABLE_SOURCE_STATUSES
from ..schemas import CSV_SCHEMAS


FORBIDDEN_TAX_FALLBACK_PATTERNS = (
    r"peer[_ ]snapshot.*(tax|official_price)",
    r"investment_property.*(tax|official_price)",
    r"book_value.*(tax|official_price)",
    r"effective_holding_tax_rate",
)


def validate_no_forbidden_tax_fallback(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if path.resolve() == Path(__file__).resolve():
            continue
        if not path.exists() or path.suffix.lower() not in {".py", ".json", ".csv"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN_TAX_FALLBACK_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
                findings.append(f"{path}: {pattern}")
    return findings


def _validation_row(
    check_name: str,
    status: str,
    message: str,
    *,
    reit_name: str = "",
    taxpayer_id: str = "",
    asset_id: str = "",
    parcel_id: str = "",
    building_id: str = "",
    severity: str = "high",
    source_url: str = "",
) -> dict:
    key = "|".join([reit_name, taxpayer_id, asset_id, parcel_id, building_id, check_name])
    return {
        "validation_id": hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
        "reit_name": reit_name,
        "taxpayer_id": taxpayer_id,
        "asset_id": asset_id,
        "parcel_id": parcel_id,
        "building_id": building_id,
        "check_name": check_name,
        "severity": severity,
        "validation_status": status,
        "message": message,
        "source_url": source_url,
        "reviewer_status": "open" if status != "passed" else "reviewed",
    }


def build_validation_results(
    reit_name: str,
    assets: pd.DataFrame,
    parcels: pd.DataFrame,
    buildings: pd.DataFrame,
    taxpayers: pd.DataFrame,
    calculations: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict] = []
    selected_assets = assets[assets["reit_name"].fillna("").astype(str).eq(str(reit_name))]
    asset_ids = set(selected_assets["asset_id"].dropna().astype(str))
    if not asset_ids:
        rows.append(_validation_row("asset_registry", "failed", "공식자료에서 식별된 자산이 없습니다.", reit_name=reit_name, severity="critical"))
    for _, asset in selected_assets.iterrows():
        asset_id = str(asset.get("asset_id", ""))
        if not str(asset.get("source_url", "") or "").strip():
            rows.append(_validation_row("asset_source", "failed", "자산의 공식 출처 URL이 없습니다.", reit_name=reit_name, asset_id=asset_id))
        related_taxpayers = taxpayers[taxpayers["asset_id"].fillna("").astype(str).eq(asset_id)]
        if len(related_taxpayers) != 1:
            rows.append(_validation_row("taxpayer_cardinality", "failed", f"납세의무자 행이 {len(related_taxpayers)}건입니다.", reit_name=reit_name, asset_id=asset_id, severity="critical"))
        elif str(related_taxpayers.iloc[0].get("validation_status", "")) not in CALCULABLE_SOURCE_STATUSES:
            rows.append(_validation_row(
                "taxpayer_verification",
                "failed",
                "과세기준일 현재 법적 납세의무자가 공식 검증되지 않았습니다.",
                reit_name=reit_name,
                taxpayer_id=str(related_taxpayers.iloc[0].get("taxpayer_id", "")),
                asset_id=asset_id,
                severity="critical",
            ))
        if related_taxpayers.empty or str(related_taxpayers.iloc[0].get("tax_classification", "")) == "undetermined":
            rows.append(_validation_row(
                "separation_tax_eligibility",
                "failed",
                "공모리츠 분리과세 요건과 목적사업 사용 여부가 확인되지 않았습니다.",
                reit_name=reit_name,
                asset_id=asset_id,
            ))
        related_parcels = parcels[parcels["asset_id"].fillna("").astype(str).eq(asset_id)]
        if related_parcels.empty:
            rows.append(_validation_row(
                "parcel_registry",
                "failed",
                "자산에 연결된 공식 PNU·필지 목록이 없습니다.",
                reit_name=reit_name,
                asset_id=asset_id,
                severity="critical",
            ))

    selected_parcels = parcels[parcels["asset_id"].fillna("").astype(str).isin(asset_ids)]
    for _, parcel in selected_parcels.iterrows():
        parcel_id = str(parcel.get("parcel_id", ""))
        pnu = str(parcel.get("pnu", "") or "").strip()
        if not pnu:
            rows.append(_validation_row("pnu_required", "failed", "PNU가 확인되지 않았습니다.", reit_name=reit_name, asset_id=str(parcel.get("asset_id", "")), parcel_id=parcel_id))
        if str(parcel.get("validation_status", "")) in CALCULABLE_SOURCE_STATUSES and not str(parcel.get("source_url", "") or "").strip():
            rows.append(_validation_row("parcel_source", "failed", "계산 허용 필지에 source_url이 없습니다.", reit_name=reit_name, parcel_id=parcel_id, severity="critical"))
    duplicate_pnu = selected_parcels[selected_parcels["pnu"].fillna("").astype(str).ne("")].duplicated("pnu", keep=False)
    for _, parcel in selected_parcels[duplicate_pnu].iterrows():
        rows.append(_validation_row("duplicate_pnu", "failed", "동일 PNU가 복수 필지 행에 존재합니다.", reit_name=reit_name, parcel_id=str(parcel.get("parcel_id", "")), severity="medium"))

    selected_buildings = buildings[buildings["asset_id"].fillna("").astype(str).isin(asset_ids)]
    for _, building in selected_buildings.iterrows():
        building_id = str(building.get("building_id", ""))
        if pd.isna(pd.to_numeric(pd.Series([building.get("building_standard_value")]), errors="coerce").iloc[0]):
            rows.append(_validation_row("building_standard_value", "failed", "공식 건축물 시가표준액이 없습니다.", reit_name=reit_name, asset_id=str(building.get("asset_id", "")), building_id=building_id))
        if str(building.get("fire_risk_category", "")) not in {"standard", "fire_risk", "large_fire_risk"}:
            rows.append(_validation_row(
                "fire_risk_classification",
                "failed",
                "소방분 지역자원시설세의 건축물 위험유형과 가중배율이 확인되지 않았습니다.",
                reit_name=reit_name,
                asset_id=str(building.get("asset_id", "")),
                building_id=building_id,
            ))
        if str(building.get("urban_area_status", "")) not in {"verified_applicable", "verified_not_applicable"}:
            rows.append(_validation_row(
                "urban_area_applicability",
                "failed",
                "도시지역분 적용대상 고시와 조례 적용 여부가 확인되지 않았습니다.",
                reit_name=reit_name,
                asset_id=str(building.get("asset_id", "")),
                building_id=building_id,
                severity="medium",
            ))

    if calculations is not None and not calculations.empty:
        unsupported = calculations[
            ~calculations["calculation_status"].isin(
                ["verified_notice", "official_source_calculated", "official_partial", "manual_review_required", "data_insufficient", "not_applicable"]
            )
        ]
        if not unsupported.empty:
            rows.append(_validation_row("calculation_status_domain", "failed", "허용되지 않은 계산 상태가 존재합니다.", reit_name=reit_name, severity="critical"))
        leaked = calculations[
            calculations["calculation_status"].isin(["manual_review_required", "data_insufficient", "official_partial"])
            & pd.to_numeric(calculations["calculated_tax"], errors="coerce").notna()
        ]
        if not leaked.empty:
            rows.append(_validation_row("unverified_number_block", "failed", "검증되지 않은 행에 계산 세액이 표시되었습니다.", reit_name=reit_name, severity="critical"))

    rows.append(_validation_row(
        "tax_notice",
        "failed",
        "실제 재산세·종합부동산세 고지서 또는 과세내역서 대사가 완료되지 않았습니다.",
        reit_name=reit_name,
        severity="high",
    ))

    if not rows:
        rows.append(_validation_row("v15_core_controls", "passed", "핵심 출처·관계·계산상태 검증을 통과했습니다.", reit_name=reit_name, severity="info"))
    return pd.DataFrame(rows, columns=CSV_SCHEMAS["validation_result.csv"])


def summarize_coverage(
    assets: pd.DataFrame,
    parcels: pd.DataFrame,
    buildings: pd.DataFrame,
    taxpayers: pd.DataFrame,
    calculations: pd.DataFrame,
) -> dict[str, int | float | str]:
    asset_count = int(len(assets))
    verified_addresses = int(assets["address_confidence"].fillna("").astype(str).isin(["verified", "high"]).sum()) if not assets.empty else 0
    pnu_count = int(parcels["pnu"].fillna("").astype(str).str.len().eq(19).sum()) if not parcels.empty else 0
    land_price_count = int(pd.to_numeric(parcels.get("individual_land_price_per_m2"), errors="coerce").notna().sum()) if not parcels.empty else 0
    building_value_count = int(pd.to_numeric(buildings.get("building_standard_value"), errors="coerce").notna().sum()) if not buildings.empty else 0
    taxpayer_count = int(taxpayers["validation_status"].fillna("").astype(str).isin(CALCULABLE_SOURCE_STATUSES).sum()) if not taxpayers.empty else 0
    if not calculations.empty:
        numeric_tax = pd.to_numeric(calculations["calculated_tax"], errors="coerce")
        completed = int(
            (
                calculations["calculation_status"].isin(
                    ["verified_notice", "official_source_calculated", "not_applicable"]
                )
                & numeric_tax.notna()
                & calculations["tax_name"].ne("토지 시가표준액")
            ).sum()
        )
    else:
        completed = 0
    blocked = int(calculations["calculation_status"].isin(["manual_review_required", "data_insufficient", "official_partial"]).sum()) if not calculations.empty else 0
    return {
        "asset_count": asset_count,
        "verified_address_count": verified_addresses,
        "verified_pnu_count": pnu_count,
        "verified_land_price_count": land_price_count,
        "verified_building_value_count": building_value_count,
        "verified_taxpayer_count": taxpayer_count,
        "completed_calculation_rows": completed,
        "blocked_calculation_rows": blocked,
        "final_status": "부분 검증 / 추가자료 필요" if blocked or completed == 0 else "공식자료 계산",
    }
