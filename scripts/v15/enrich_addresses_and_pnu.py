from __future__ import annotations

import argparse
import os

import pandas as pd

from src.tax_v15.constants import V15_DATA_DIR
from src.tax_v15.schemas import coerce_to_schema, ensure_v15_csv_files

from .common import add_common_arguments, utc_now, write_checkpoint


def run(*, offline: bool = False, dry_run: bool = False, reit_code: str = "") -> pd.DataFrame:
    """Validate existing parcel mappings; never infer one parcel from one road address."""
    ensure_v15_csv_files()
    path = V15_DATA_DIR / "parcel_master.csv"
    parcels = pd.read_csv(path, dtype={"pnu": "string"})
    if not parcels.empty:
        valid_pnu = parcels["pnu"].fillna("").astype(str).str.fullmatch(r"\d{19}")
        parcels.loc[~valid_pnu, "validation_status"] = "data_insufficient"
        parcels.loc[~valid_pnu, "reviewer_status"] = "pnu_manual_review_required"
    configured = bool(os.getenv("VWORLD_API_KEY", "").strip() or os.getenv("REALTY_PRICE_API_KEY", "").strip())
    # Geocoding alone is not proof of parcel completeness. New parcel rows are therefore not created automatically.
    if not dry_run:
        coerce_to_schema(parcels, "parcel_master.csv").to_csv(path, index=False, encoding="utf-8-sig")
        write_checkpoint(
            "enrich_addresses_and_pnu",
            {
                "completed_at": utc_now(),
                "parcel_rows": len(parcels),
                "address_api_configured": configured,
                "note": "주소 1건을 필지 1건으로 간주하지 않아 공식 PNU 원천이 없는 신규 행은 생성하지 않음",
            },
        )
    return parcels


def main() -> None:
    args = add_common_arguments(argparse.ArgumentParser(description="주소/PNU 매핑 검증(추정 금지)")).parse_args()
    frame = run(offline=args.offline, dry_run=args.dry_run, reit_code=args.reit_code)
    print(f"검증 대상 필지: {len(frame)}건")


if __name__ == "__main__":
    main()
