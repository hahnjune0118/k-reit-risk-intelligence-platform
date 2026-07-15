from __future__ import annotations

import argparse
import json

import pandas as pd
import requests

from src.tax_v15.constants import V15_DATA_DIR
from src.tax_v15.schemas import coerce_to_schema, ensure_v15_csv_files

from .common import add_common_arguments, request_with_retry, sha256_bytes, utc_now, write_checkpoint


LIST_PAGE = "https://reits.molit.go.kr/pub/invt/lsted/lstedReitsSearch?pmn=7"
LIST_ENDPOINT = "https://reits.molit.go.kr/pub/invt/lsted/searchLstedReits"


def _fetch() -> tuple[list[dict], bytes]:
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; K-REIT-Risk-Intelligence/15.0; research)",
        "Referer": LIST_PAGE,
        "Origin": "https://reits.molit.go.kr",
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
    }
    request_with_retry("GET", LIST_PAGE, session=session, headers=headers)
    payload = {"token": "", "data": json.dumps({"pageSize": 100, "pageNum": 1}, ensure_ascii=False, separators=(",", ":"))}
    response = request_with_retry(
        "POST",
        LIST_ENDPOINT,
        session=session,
        headers=headers,
        data=json.dumps(payload, ensure_ascii=False),
    )
    body = response.json()
    if body.get("code") != "SCC" or not isinstance(body.get("data", {}).get("list"), list):
        raise RuntimeError("리츠정보시스템 상장리츠 응답 스키마가 예상과 다릅니다.")
    return body["data"]["list"], response.content


def run(*, offline: bool = False, dry_run: bool = False, reit_code: str = "") -> pd.DataFrame:
    ensure_v15_csv_files()
    target = V15_DATA_DIR / "reit_master.csv"
    if offline:
        frame = pd.read_csv(target, dtype={"stock_code": "string"})
        return frame[frame["stock_code"].eq(reit_code)] if reit_code else frame
    items, raw = _fetch()
    retrieved_at = utc_now()
    source_hash = sha256_bytes(raw)
    rows = []
    for item in items:
        stock_code = str(item.get("stockCd", "")).strip()
        if reit_code and stock_code != reit_code:
            continue
        evidence_time = str(item.get("stockDtTitle1", "")).strip()
        rows.append({
            "stock_code": stock_code,
            "reit_name": str(item.get("stockNm", "")).strip(),
            "legal_name": str(item.get("cmpnyNm", "")).strip(),
            "listed_status": "listed_verified",
            "listing_date": item.get("lstDt", ""),
            "reit_type": "",
            "public_reit_status": "manual_review_required",
            "public_reit_evidence": "상장 사실과 공모부동산투자회사 분리과세 요건은 별도 검토",
            "official_website": item.get("hmpg", ""),
            "ir_page_url": "",
            "dart_corp_code": "",
            "asset_management_company": "",
            "latest_reporting_date": evidence_time[:10],
            "source_url": LIST_PAGE,
            "verification_status": "verified_notice",
            "source_type": "official_reit_information_system",
            "source_document_name": "상장리츠 현황",
            "source_document_date": evidence_time[:10],
            "source_page": "HTML dynamic table",
            "source_quote_or_evidence": f"{stock_code} {item.get('stockNm', '')} / 상장일 {item.get('lstDt', '')}",
            "retrieved_at": retrieved_at,
            "source_hash": source_hash,
            "source_reliability": "tier_2_official_industry_system",
            "reviewer_status": "reviewed",
        })
    frame = coerce_to_schema(pd.DataFrame(rows), "reit_master.csv")
    if not dry_run and not reit_code:
        frame.to_csv(target, index=False, encoding="utf-8-sig")
        coverage = pd.DataFrame([
            {
                "reit_name": row["reit_name"],
                "stock_code": row["stock_code"],
                "official_website_found": bool(str(row["official_website"]).strip()),
                "ir_documents_checked": False,
                "dart_documents_checked": False,
                "asset_count_identified": 0,
                "address_count_verified": 0,
                "parcel_count_verified": 0,
                "land_price_coverage": "0%",
                "building_value_coverage": "0%",
                "taxpayer_coverage": "0%",
                "tax_calculation_status": "data_insufficient",
                "blocking_reason": "자산·필지·납세의무자 공식자료 수집 필요",
                "next_action": "공식 홈페이지·DART 투자보고서에서 Asset Registry 구축",
            }
            for _, row in frame.iterrows()
        ])
        coerce_to_schema(coverage, "coverage_manifest.csv").to_csv(
            V15_DATA_DIR / "coverage_manifest.csv", index=False, encoding="utf-8-sig"
        )
        write_checkpoint("discover_listed_reits", {"retrieved_at": retrieved_at, "count": len(frame), "source_hash": source_hash})
    return frame


def main() -> None:
    parser = add_common_arguments(argparse.ArgumentParser(description="공식 리츠정보시스템 상장리츠 목록 수집"))
    args = parser.parse_args()
    frame = run(offline=args.offline, dry_run=args.dry_run, reit_code=args.reit_code)
    print(f"공식 상장리츠 수집 결과: {len(frame)}개")


if __name__ == "__main__":
    main()
