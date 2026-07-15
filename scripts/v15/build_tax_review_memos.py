from __future__ import annotations

import argparse

from src.tax_v15.constants import PROJECT_ROOT
from src.tax_v15.loaders import load_v15_bundle
from src.tax_v15.reporting import build_tax_review_memo

from .common import add_common_arguments, utc_now, write_checkpoint


def run(*, tax_year: int = 2026, reit_code: str = "", dry_run: bool = False) -> list[str]:
    bundle = load_v15_bundle()
    reits = bundle.reits
    if reit_code:
        reits = reits[reits["stock_code"].astype(str).eq(str(reit_code))]
    output_dir = PROJECT_ROOT / ".cache" / "v15" / "memos"
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    for _, reit in reits.iterrows():
        name = str(reit["reit_name"])
        assets = bundle.assets[bundle.assets["reit_name"].astype(str).eq(name)]
        asset_ids = set(assets["asset_id"].astype(str))
        memo = build_tax_review_memo(
            name, tax_year, assets,
            bundle.parcels[bundle.parcels["asset_id"].astype(str).isin(asset_ids)],
            bundle.buildings[bundle.buildings["asset_id"].astype(str).isin(asset_ids)],
            bundle.taxpayers[bundle.taxpayers["asset_id"].astype(str).isin(asset_ids)],
            bundle.calculations[bundle.calculations["reit_name"].astype(str).eq(name)],
            bundle.validations[bundle.validations["reit_name"].astype(str).eq(name)],
            bundle.requests[bundle.requests["reit_name"].astype(str).eq(name)],
        )
        path = output_dir / f"{str(reit['stock_code'])}_{tax_year}_tax_review_memo.md"
        if not dry_run:
            path.write_text(memo, encoding="utf-8")
        outputs.append(str(path))
    if not dry_run:
        write_checkpoint("build_tax_review_memos", {"completed_at": utc_now(), "count": len(outputs)})
    return outputs


def main() -> None:
    args = add_common_arguments(argparse.ArgumentParser(description="v15 Tax Review Memo 생성")).parse_args()
    outputs = run(tax_year=args.tax_year, reit_code=args.reit_code, dry_run=args.dry_run)
    print(f"Tax Review Memo: {len(outputs)}개")


if __name__ == "__main__":
    main()
