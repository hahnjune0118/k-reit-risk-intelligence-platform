from __future__ import annotations

import argparse

from src.tax_v15.constants import PROJECT_ROOT, V15_DATA_DIR
from src.tax_v15.loaders import load_v15_bundle
from src.tax_v15.validation.coverage import build_coverage_manifest, build_coverage_report

from .common import add_common_arguments, utc_now, write_checkpoint


def run(*, dry_run: bool = False):
    bundle = load_v15_bundle()
    coverage = build_coverage_manifest(bundle)
    report = build_coverage_report(bundle, coverage)
    if not dry_run:
        coverage.to_csv(V15_DATA_DIR / "coverage_manifest.csv", index=False, encoding="utf-8-sig")
        report_path = PROJECT_ROOT / "docs" / "v15" / "COVERAGE_REPORT.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        write_checkpoint("generate_coverage_report", {"completed_at": utc_now(), "rows": len(coverage)})
    return coverage, report


def main() -> None:
    args = add_common_arguments(argparse.ArgumentParser(description="v15 Coverage Manifest와 보고서 생성")).parse_args()
    coverage, _ = run(dry_run=args.dry_run)
    print(f"Coverage Manifest: {len(coverage)}개 리츠")


if __name__ == "__main__":
    main()
