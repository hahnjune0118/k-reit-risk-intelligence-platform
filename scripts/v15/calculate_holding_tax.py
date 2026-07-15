from __future__ import annotations

import argparse

import pandas as pd

from src.tax_v15.calculators import calculate_holding_tax_detail
from src.tax_v15.constants import V15_DATA_DIR
from src.tax_v15.loaders import load_v15_bundle
from src.tax_v15.schemas import coerce_to_schema

from .common import add_common_arguments, utc_now, write_checkpoint


def run(*, tax_year: int = 2026, reit_code: str = "", dry_run: bool = False) -> pd.DataFrame:
    bundle = load_v15_bundle()
    reits = bundle.reits
    if reit_code:
        reits = reits[reits["stock_code"].astype(str).eq(str(reit_code))]
    outputs: list[pd.DataFrame] = []
    for _, reit in reits.iterrows():
        outputs.append(
            calculate_holding_tax_detail(
                str(reit["reit_name"]), bundle.assets, bundle.parcels, bundle.buildings,
                bundle.taxpayers, bundle.rules, tax_year,
            )
        )
    result = coerce_to_schema(pd.concat(outputs, ignore_index=True) if outputs else pd.DataFrame(), "tax_calculation_detail.csv")
    if not dry_run:
        target_path = V15_DATA_DIR / "tax_calculation_detail.csv"
        if reit_code and target_path.exists():
            existing = pd.read_csv(target_path)
            target_names = set(reits["reit_name"].dropna().astype(str))
            existing = existing[~existing["reit_name"].fillna("").astype(str).isin(target_names)]
            result = coerce_to_schema(pd.concat([existing, result], ignore_index=True), "tax_calculation_detail.csv")
        result.to_csv(target_path, index=False, encoding="utf-8-sig")
        write_checkpoint("calculate_holding_tax", {"completed_at": utc_now(), "tax_year": tax_year, "rows": len(result)})
    return result


def main() -> None:
    args = add_common_arguments(argparse.ArgumentParser(description="v15 자산·납세의무자 단위 보유세 계산")).parse_args()
    frame = run(tax_year=args.tax_year, reit_code=args.reit_code, dry_run=args.dry_run)
    print(f"Tax calculation detail: {len(frame)}행")


if __name__ == "__main__":
    main()
