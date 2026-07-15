from __future__ import annotations

import argparse

import pandas as pd

from src.tax_v15.constants import V15_DATA_DIR
from src.tax_v15.schemas import coerce_to_schema, ensure_v15_csv_files

from .common import add_common_arguments, utc_now, write_checkpoint


def run(*, offline: bool = False, dry_run: bool = False, reit_code: str = "") -> pd.DataFrame:
    """Preserve verified land-price snapshots and block incomplete rows.

    The public V-World service contract differs by approved product. This stage consumes only
    already-normalized official responses; it never substitutes book value or peer values.
    """
    ensure_v15_csv_files()
    path = V15_DATA_DIR / "parcel_master.csv"
    parcels = pd.read_csv(path, dtype={"pnu": "string"})
    if not parcels.empty:
        price = pd.to_numeric(parcels["individual_land_price_per_m2"], errors="coerce")
        area = pd.to_numeric(parcels["taxable_area_m2"], errors="coerce")
        share = pd.to_numeric(parcels["ownership_share"], errors="coerce")
        source_ok = parcels["source_url"].fillna("").astype(str).str.strip().ne("")
        pnu_ok = parcels["pnu"].fillna("").astype(str).str.fullmatch(r"\d{19}")
        eligible = price.notna() & area.notna() & share.gt(0) & share.le(1) & source_ok & pnu_ok
        parcels.loc[~eligible, "validation_status"] = "data_insufficient"
        parcels.loc[~eligible, "assessed_land_value"] = pd.NA
        parcels.loc[eligible, "assessed_land_value"] = price[eligible] * area[eligible] * share[eligible]
        parcels.loc[eligible, "validation_status"] = parcels.loc[eligible, "validation_status"].where(
            parcels.loc[eligible, "validation_status"].isin(["verified_notice", "official_source_calculated"]),
            "official_source_calculated",
        )
    if not dry_run:
        coerce_to_schema(parcels, "parcel_master.csv").to_csv(path, index=False, encoding="utf-8-sig")
        write_checkpoint(
            "fetch_official_land_prices",
            {
                "completed_at": utc_now(),
                "verified_rows": int(eligible.sum()) if not parcels.empty else 0,
            },
        )
    return parcels


def main() -> None:
    args = add_common_arguments(argparse.ArgumentParser(description="공식 개별공시지가 Snapshot 검증")).parse_args()
    frame = run(offline=args.offline, dry_run=args.dry_run, reit_code=args.reit_code)
    print(f"필지 Snapshot: {len(frame)}건")


if __name__ == "__main__":
    main()
