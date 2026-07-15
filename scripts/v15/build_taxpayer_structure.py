from __future__ import annotations

import argparse
import hashlib

import pandas as pd

from src.tax_v15.constants import V15_DATA_DIR
from src.tax_v15.schemas import coerce_to_schema, ensure_v15_csv_files

from .common import add_common_arguments, utc_now, write_checkpoint


def run(*, dry_run: bool = False, reit_code: str = "") -> pd.DataFrame:
    ensure_v15_csv_files()
    assets = pd.read_csv(V15_DATA_DIR / "asset_master.csv", dtype={"stock_code": "string"})
    if reit_code:
        assets = assets[assets["stock_code"].eq(reit_code)]
    rows: list[dict] = []
    for _, asset in assets.iterrows():
        asset_id = str(asset.get("asset_id", ""))
        owner = str(asset.get("legal_owner_name", "") or "").strip()
        owner_verified = owner and str(asset.get("owner_confidence", "")) in {"verified", "high"}
        trustee = str(asset.get("trustee_name", "") or "").strip()
        trustor = str(asset.get("trustor_name", "") or "").strip()
        tax_obligor = trustor if trustee and trustor and owner_verified else owner if owner_verified else ""
        taxpayer_key = tax_obligor if tax_obligor else f"UNRESOLVED|{asset_id}"
        rows.append({
            "taxpayer_id": f"TP-{hashlib.sha256(taxpayer_key.encode('utf-8')).hexdigest()[:12]}",
            "asset_id": asset_id,
            "legal_owner": owner,
            "beneficial_owner": str(asset.get("listed_parent", "") or ""),
            "trustee": trustee,
            "trustor": trustor,
            "ownership_share": asset.get("ownership_share", ""),
            "tax_obligor": tax_obligor,
            "taxpayer_evidence": str(asset.get("source_quote_or_evidence", "") or ""),
            "public_reit_qualified": "undetermined",
            "qualifying_subsidiary_reit": "undetermined",
            "purpose_business_use": "undetermined",
            "separation_tax_eligible": "undetermined",
            "separation_tax_reason": "상장 사실만으로 공모리츠 목적사업용 토지 분리과세를 확정하지 않음",
            "tax_classification": "undetermined",
            "assessment_date_ownership_verified": False,
            "nationwide_land_aggregation_verified": False,
            "property_tax_credit": "",
            "property_tax_credit_source_url": "",
            "manual_review_flag": True,
            "source_url": str(asset.get("source_url", "") or ""),
            "source_page": str(asset.get("source_page", "") or ""),
            "validation_status": "official_partial" if owner_verified else "manual_review_required",
            "source_type": str(asset.get("source_type", "") or ""),
            "source_document_name": str(asset.get("source_document_name", "") or ""),
            "source_document_date": str(asset.get("source_document_date", "") or ""),
            "source_quote_or_evidence": str(asset.get("source_quote_or_evidence", "") or ""),
            "retrieved_at": str(asset.get("retrieved_at", "") or utc_now()),
            "source_hash": str(asset.get("source_hash", "") or ""),
            "source_reliability": str(asset.get("source_reliability", "") or ""),
            "reviewer_status": "legal_owner_and_taxpayer_open",
        })
    result = coerce_to_schema(pd.DataFrame(rows), "taxpayer_structure.csv")
    if not dry_run:
        target_path = V15_DATA_DIR / "taxpayer_structure.csv"
        if reit_code and target_path.exists():
            existing = pd.read_csv(target_path)
            target_asset_ids = set(assets["asset_id"].dropna().astype(str))
            existing = existing[~existing["asset_id"].fillna("").astype(str).isin(target_asset_ids)]
            result = coerce_to_schema(pd.concat([existing, result], ignore_index=True), "taxpayer_structure.csv")
        result.to_csv(target_path, index=False, encoding="utf-8-sig")
        write_checkpoint("build_taxpayer_structure", {"completed_at": utc_now(), "rows": len(result), "verified": int(result["validation_status"].isin(["verified_notice", "official_source_calculated"]).sum()) if not result.empty else 0})
    return result


def main() -> None:
    args = add_common_arguments(argparse.ArgumentParser(description="자산별 법적 납세의무자·분리과세 판정 구조 생성")).parse_args()
    frame = run(dry_run=args.dry_run, reit_code=args.reit_code)
    print(f"납세의무자 검토 행: {len(frame)}건")


if __name__ == "__main__":
    main()
