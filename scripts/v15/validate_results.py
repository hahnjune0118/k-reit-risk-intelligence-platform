from __future__ import annotations

import argparse

import pandas as pd

from src.tax_v15.constants import V15_DATA_DIR
from src.tax_v15.loaders import load_v15_bundle
from src.tax_v15.reporting import build_request_list
from src.tax_v15.schemas import coerce_to_schema
from src.tax_v15.validation import build_validation_results

from .common import add_common_arguments, utc_now, write_checkpoint


def _reconciliation_rows(reits: pd.DataFrame, calculations: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for _, reit in reits.iterrows():
        reit_name = str(reit["reit_name"])
        selected = calculations[
            calculations["reit_name"].fillna("").astype(str).eq(reit_name)
            & calculations["calculation_status"].isin(["verified_notice", "official_source_calculated"])
            & calculations["tax_name"].ne("토지 시가표준액")
        ]
        amounts = pd.to_numeric(selected["calculated_tax"], errors="coerce").dropna()
        tax_years = pd.to_numeric(selected["tax_year"], errors="coerce").dropna().astype(int).unique()
        rows.append({
            "reit_name": reit_name,
            "taxpayer_id": "ALL_VERIFIED_TAXPAYERS",
            "tax_year": int(tax_years[0]) if len(tax_years) == 1 else pd.NA,
            "metric": "holding_tax_notice_reconciliation",
            "calculated_value": amounts.sum() if not amounts.empty else pd.NA,
            "disclosed_or_verified_value": pd.NA,
            "variance": pd.NA,
            "variance_percent": pd.NA,
            "reconciliation_reason": (
                "실제 재산세·종합부동산세 고지서 또는 과세내역서가 없어 대사 미완료. "
                "재무제표 세금과공과 전체는 보유세 Ground Truth로 사용하지 않음."
            ),
            "reviewer_status": "open",
        })
    return coerce_to_schema(pd.DataFrame(rows), "reconciliation.csv")


def run(*, reit_code: str = "", dry_run: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    bundle = load_v15_bundle()
    reits = bundle.reits
    if reit_code:
        reits = reits[reits["stock_code"].astype(str).eq(str(reit_code))]
    validation_frames: list[pd.DataFrame] = []
    for _, reit in reits.iterrows():
        name = str(reit["reit_name"])
        assets = bundle.assets[bundle.assets["reit_name"].astype(str).eq(name)]
        asset_ids = set(assets["asset_id"].astype(str))
        validation_frames.append(build_validation_results(
            name,
            assets,
            bundle.parcels[bundle.parcels["asset_id"].astype(str).isin(asset_ids)],
            bundle.buildings[bundle.buildings["asset_id"].astype(str).isin(asset_ids)],
            bundle.taxpayers[bundle.taxpayers["asset_id"].astype(str).isin(asset_ids)],
            bundle.calculations[bundle.calculations["reit_name"].astype(str).eq(name)],
        ))
    validations = coerce_to_schema(pd.concat(validation_frames, ignore_index=True) if validation_frames else pd.DataFrame(), "validation_result.csv")
    requests = coerce_to_schema(build_request_list(validations), "request_list.csv")
    reconciliation = _reconciliation_rows(reits, bundle.calculations)
    if not dry_run:
        if reit_code:
            target_names = set(reits["reit_name"].dropna().astype(str))
            for file_name, current in [
                ("validation_result.csv", validations),
                ("request_list.csv", requests),
                ("reconciliation.csv", reconciliation),
            ]:
                path = V15_DATA_DIR / file_name
                existing = pd.read_csv(path) if path.exists() else pd.DataFrame()
                if not existing.empty:
                    existing = existing[~existing["reit_name"].fillna("").astype(str).isin(target_names)]
                merged = coerce_to_schema(pd.concat([existing, current], ignore_index=True), file_name)
                merged.to_csv(path, index=False, encoding="utf-8-sig")
        else:
            validations.to_csv(V15_DATA_DIR / "validation_result.csv", index=False, encoding="utf-8-sig")
            requests.to_csv(V15_DATA_DIR / "request_list.csv", index=False, encoding="utf-8-sig")
            reconciliation.to_csv(V15_DATA_DIR / "reconciliation.csv", index=False, encoding="utf-8-sig")
        write_checkpoint(
            "validate_results",
            {
                "completed_at": utc_now(),
                "validation_rows": len(validations),
                "request_rows": len(requests),
                "reconciliation_rows": len(reconciliation),
            },
        )
    return validations, requests


def main() -> None:
    args = add_common_arguments(argparse.ArgumentParser(description="v15 출처·스키마·계산 결과 검증")).parse_args()
    validations, requests = run(reit_code=args.reit_code, dry_run=args.dry_run)
    print(f"Validation: {len(validations)}건 / Request: {len(requests)}건")


if __name__ == "__main__":
    main()
