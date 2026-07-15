from __future__ import annotations

import argparse
import html
import re
from urllib.parse import urljoin

import pandas as pd

from src.tax_v15.constants import V15_DATA_DIR
from src.tax_v15.schemas import coerce_to_schema, ensure_v15_csv_files

from .common import add_common_arguments, request_with_retry, sha256_bytes, utc_now, write_checkpoint


ESR_CODE = "365550"
ESR_LIST_URL = "https://www.esrks-reit.com/en/portfolio/assets"
ASSET_LINK_PATTERN = re.compile(r'href="(?P<href>/en/portfolio/map/[^"]+)"[^>]*>(?P<name>[^<]+)</a>')
META_DESCRIPTION_PATTERN = re.compile(r'<meta name="description" content="([^"]+)"')
AREA_PATTERN = re.compile(r'href="(?P<href>/en/portfolio/map/[^"]+)"[^>]*>[^<]+</a></td><td[^>]*>(?P<area>[\d,]+)</td><td[^>]*>(?P<year>[\d.]+)</td>', re.DOTALL)


def _fetch_esr_assets() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; K-REIT-Risk-Intelligence/15.0; research)"}
    list_response = request_with_retry("GET", ESR_LIST_URL, headers=headers)
    list_text = list_response.text
    area_by_href = {
        match.group("href"): (match.group("area").replace(",", ""), match.group("year"))
        for match in AREA_PATTERN.finditer(list_text)
    }
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    for match in ASSET_LINK_PATTERN.finditer(list_text):
        href = match.group("href")
        if href in seen:
            continue
        seen.add(href)
        links.append((href, html.unescape(match.group("name")).strip()))
    if not links:
        raise RuntimeError("ESR 공식 포트폴리오 페이지에서 자산 링크를 찾지 못했습니다.")

    asset_rows: list[dict] = []
    building_rows: list[dict] = []
    document_rows: list[dict] = []
    retrieved_at = utc_now()
    for index, (href, asset_name) in enumerate(links, start=1):
        url = urljoin(ESR_LIST_URL, href)
        response = request_with_retry("GET", url, headers=headers)
        description_match = META_DESCRIPTION_PATTERN.search(response.text)
        address = html.unescape(description_match.group(1)).strip() if description_match else ""
        address_confidence = "verified" if address else "data_insufficient"
        status = "official_partial" if address else "data_insufficient"
        asset_id = f"365550-ESR-{index:03d}"
        area, completion = area_by_href.get(href, ("", ""))
        evidence = f"{asset_name} / {address}" if address else asset_name
        asset_rows.append({
            "asset_id": asset_id,
            "stock_code": ESR_CODE,
            "reit_name": "ESR켄달스퀘어리츠",
            "asset_name": asset_name,
            "asset_class": "logistics",
            "asset_subclass": "",
            "direct_or_indirect": "undetermined",
            "listed_parent": "ESR켄달스퀘어리츠",
            "legal_owner_name": "",
            "legal_owner_type": "undetermined",
            "ownership_vehicle_type": "undetermined",
            "subsidiary_reit_name": "",
            "spc_or_pfv_name": "",
            "fund_name": "",
            "trustee_name": "",
            "trustor_name": "",
            "ownership_share": "",
            "acquisition_date": "",
            "purpose_use": "logistics",
            "road_address": address,
            "lot_address": "",
            "city": "",
            "district": "",
            "source_document": "ESR KendallSquare REIT Portfolio Asset Detail",
            "source_page": "HTML meta description",
            "source_url": url,
            "address_confidence": address_confidence,
            "owner_confidence": "data_insufficient",
            "verification_status": status,
            "source_type": "official_reit_website",
            "source_document_name": "Portfolio Asset Detail",
            "source_document_date": "",
            "source_quote_or_evidence": evidence,
            "retrieved_at": retrieved_at,
            "source_hash": sha256_bytes(response.content),
            "source_reliability": "tier_1_official_reit_website",
            "reviewer_status": "address_reviewed_owner_open",
        })
        building_rows.append({
            "building_id": f"{asset_id}-B001",
            "asset_id": asset_id,
            "building_name": asset_name,
            "building_address": address,
            "building_register_id": "",
            "gross_floor_area_m2": area,
            "main_use": "logistics",
            "structure_type": "",
            "completion_year": completion,
            "floor_count": "",
            "building_standard_value": "",
            "building_standard_value_year": "",
            "calculation_source": "",
            "fire_risk_category": "undetermined",
            "fire_tax_multiplier": "",
            "urban_area_status": "unknown",
            "source_url": url,
            "source_page": "HTML portfolio detail",
            "validation_status": "official_partial",
            "source_type": "official_reit_website",
            "source_document_name": "Portfolio Asset Detail",
            "source_document_date": "",
            "source_quote_or_evidence": f"{asset_name} / GFA {area} sqm / completion {completion}",
            "retrieved_at": retrieved_at,
            "source_hash": sha256_bytes(response.content),
            "source_reliability": "tier_1_official_reit_website",
            "reviewer_status": "building_value_open",
        })
        document_rows.append({
            "reit_name": "ESR켄달스퀘어리츠", "document_type": "portfolio_asset_detail",
            "document_name": asset_name, "document_date": "", "source_url": url, "local_cache_path": "",
            "sha256": sha256_bytes(response.content), "downloaded_at": retrieved_at,
            "extraction_status": status, "relevant_pages": "HTML", "notes": "주소·연면적 확인; 소유자·필지·시가표준액 미확인",
        })
    return pd.DataFrame(asset_rows), pd.DataFrame(building_rows), pd.DataFrame(document_rows)


def run(*, offline: bool = False, dry_run: bool = False, reit_code: str = "") -> pd.DataFrame:
    ensure_v15_csv_files()
    asset_path = V15_DATA_DIR / "asset_master.csv"
    if offline:
        frame = pd.read_csv(asset_path, dtype={"stock_code": "string"})
        return frame[frame["stock_code"].eq(reit_code)] if reit_code else frame
    if reit_code and reit_code != ESR_CODE:
        return pd.DataFrame(columns=coerce_to_schema(pd.DataFrame(), "asset_master.csv").columns)
    assets, buildings, documents = _fetch_esr_assets()
    assets = coerce_to_schema(assets, "asset_master.csv")
    buildings = coerce_to_schema(buildings, "building_master.csv")
    documents = coerce_to_schema(documents, "source_document_manifest.csv")
    if not dry_run:
        existing_assets = pd.read_csv(asset_path, dtype={"stock_code": "string"})
        existing_assets = existing_assets[~existing_assets["stock_code"].fillna("").astype(str).eq(ESR_CODE)]
        all_assets = coerce_to_schema(pd.concat([existing_assets, assets], ignore_index=True), "asset_master.csv")
        all_assets.to_csv(asset_path, index=False, encoding="utf-8-sig")

        building_path = V15_DATA_DIR / "building_master.csv"
        existing_buildings = pd.read_csv(building_path)
        existing_buildings = existing_buildings[
            ~existing_buildings["asset_id"].fillna("").astype(str).str.startswith(f"{ESR_CODE}-ESR-")
        ]
        all_buildings = coerce_to_schema(
            pd.concat([existing_buildings, buildings], ignore_index=True),
            "building_master.csv",
        )
        all_buildings.to_csv(building_path, index=False, encoding="utf-8-sig")
        existing_docs = pd.read_csv(V15_DATA_DIR / "source_document_manifest.csv")
        all_docs = coerce_to_schema(pd.concat([existing_docs, documents], ignore_index=True), "source_document_manifest.csv")
        all_docs.drop_duplicates(["reit_name", "document_type", "source_url"], keep="last").to_csv(
            V15_DATA_DIR / "source_document_manifest.csv", index=False, encoding="utf-8-sig"
        )
        coverage = pd.read_csv(V15_DATA_DIR / "coverage_manifest.csv", dtype={"stock_code": "string"})
        mask = coverage["stock_code"].eq(ESR_CODE)
        coverage.loc[mask, "asset_count_identified"] = len(assets)
        coverage.loc[mask, "address_count_verified"] = assets["address_confidence"].eq("verified").sum()
        coverage.loc[mask, "building_value_coverage"] = "0%"
        coverage.loc[mask, "tax_calculation_status"] = "official_partial"
        coverage.loc[mask, "blocking_reason"] = "법적 소유자·PNU·개별공시지가·건축물 시가표준액 미확인"
        coverage.loc[mask, "next_action"] = "등기·신탁·과세내역서 및 공식 필지자료 확보"
        coverage.to_csv(V15_DATA_DIR / "coverage_manifest.csv", index=False, encoding="utf-8-sig")
        write_checkpoint("build_asset_registry", {"completed_at": utc_now(), "asset_count": len(assets)})
    return assets


def main() -> None:
    args = add_common_arguments(argparse.ArgumentParser(description="공식 리츠 홈페이지 Asset Registry 구축")).parse_args()
    frame = run(offline=args.offline, dry_run=args.dry_run, reit_code=args.reit_code)
    print(f"공식자료 식별 자산: {len(frame)}건")


if __name__ == "__main__":
    main()
