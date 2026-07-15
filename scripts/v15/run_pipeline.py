from __future__ import annotations

import argparse

from . import (
    build_asset_registry,
    build_tax_review_memos,
    build_taxpayer_structure,
    calculate_holding_tax,
    collect_reit_documents,
    discover_listed_reits,
    enrich_addresses_and_pnu,
    fetch_official_land_prices,
    generate_coverage_report,
    initialize_v15_data,
    validate_results,
)
from .common import add_common_arguments, read_checkpoint


def main() -> None:
    parser = add_common_arguments(argparse.ArgumentParser(description="v15 전체 Tax 데이터 파이프라인"))
    parser.add_argument("--all-reits", action="store_true")
    args = parser.parse_args()
    reit_code = "" if args.all_reits else args.reit_code
    initialize_v15_data.run()
    resume_sources = args.resume and not args.refresh_sources
    if not resume_sources or not read_checkpoint("discover_listed_reits"):
        discover_listed_reits.run(offline=args.offline, dry_run=args.dry_run, reit_code=reit_code)
    if not resume_sources or not read_checkpoint("collect_reit_documents"):
        collect_reit_documents.run(
            offline=args.offline,
            dry_run=args.dry_run,
            reit_code=reit_code,
            refresh_sources=args.refresh_sources,
        )
    if not resume_sources or not read_checkpoint("build_asset_registry"):
        build_asset_registry.run(offline=args.offline, dry_run=args.dry_run, reit_code=reit_code)
    if not resume_sources or not read_checkpoint("enrich_addresses_and_pnu"):
        enrich_addresses_and_pnu.run(offline=args.offline, dry_run=args.dry_run, reit_code=reit_code)
    if not resume_sources or not read_checkpoint("fetch_official_land_prices"):
        fetch_official_land_prices.run(offline=args.offline, dry_run=args.dry_run, reit_code=reit_code)
    build_taxpayer_structure.run(dry_run=args.dry_run, reit_code=reit_code)
    calculate_holding_tax.run(tax_year=args.tax_year, reit_code=reit_code, dry_run=args.dry_run)
    validate_results.run(reit_code=reit_code, dry_run=args.dry_run)
    build_tax_review_memos.run(tax_year=args.tax_year, reit_code=reit_code, dry_run=args.dry_run)
    generate_coverage_report.run(dry_run=args.dry_run)
    print("v15 pipeline 완료")


if __name__ == "__main__":
    main()
