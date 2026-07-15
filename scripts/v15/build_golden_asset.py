from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd

from src.tax_v15.calculators.engine import calculate_holding_tax_detail
from src.tax_v15.constants import PROJECT_ROOT, V15_DATA_DIR
from src.tax_v15.loaders import load_csv, load_v15_bundle
from src.tax_v15.reporting import build_request_list
from src.tax_v15.schemas import CSV_SCHEMAS, coerce_to_schema
from src.tax_v15.taxpayer import classify_public_reit_land, determine_tax_obligor
from src.tax_v15.validation import build_validation_results
from src.tax_v15.validation.coverage import build_coverage_manifest, build_coverage_report


SNAPSHOT_PATH = V15_DATA_DIR / "golden_asset" / "sk_seorin_official_snapshot.json"
GOLDEN_STOCK_CODE = "395400"
GOLDEN_REIT_NAME = "SK리츠"
GOLDEN_DOC_DIR = PROJECT_ROOT / "docs" / "v15" / "golden_asset"
EVIDENCE_MATRIX_PATH = GOLDEN_DOC_DIR / "SK_SEORIN_EVIDENCE_MATRIX.csv"
AREA_RECONCILIATION_PATH = GOLDEN_DOC_DIR / "SK_SEORIN_AREA_RECONCILIATION.csv"
STATUTORY_RECALCULATION_LABEL = "2026년 공식 입력자료 기반 보유세 산식 재계산액"
EVIDENCE_MATRIX_COLUMNS = [
    "evidence_id",
    "metric_or_fact",
    "value",
    "unit",
    "source_name",
    "source_url",
    "source_date",
    "source_page",
    "source_quote",
    "retrieved_at",
    "sha256",
    "reliability",
    "verification_status",
    "used_in_calculation",
    "limitation",
]


def _read_snapshot() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def _row_key(row: dict, keys: list[str]) -> tuple[str, ...]:
    return tuple("" if pd.isna(row.get(key)) else str(row.get(key, "")) for key in keys)


def _read_raw_rows(
    file_name: str,
) -> tuple[list[str], list[dict[str, str]], bool]:
    path = V15_DATA_DIR / file_name
    has_bom = path.read_bytes().startswith(b"\xef\xbb\xbf")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    columns.extend(
        column for column in CSV_SCHEMAS[file_name] if column not in columns
    )
    return columns, rows, has_bom


def _stringify_row(row: dict, columns: list[str]) -> dict[str, str]:
    return {
        column: "" if pd.isna(row.get(column)) else str(row.get(column, ""))
        for column in columns
    }


def _write_raw_rows(
    file_name: str,
    columns: list[str],
    rows: list[dict[str, str]],
    *,
    with_bom: bool,
) -> None:
    path = V15_DATA_DIR / file_name
    encoding = "utf-8-sig" if with_bom else "utf-8"
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _upsert(file_name: str, rows: list[dict], keys: list[str]) -> pd.DataFrame:
    columns, existing, has_bom = _read_raw_rows(file_name)
    incoming = coerce_to_schema(pd.DataFrame(rows), file_name)
    incoming_by_key = {
        _row_key(row, keys): _stringify_row(row, columns)
        for row in incoming.to_dict("records")
    }
    merged_rows: list[dict[str, str]] = []
    consumed: set[tuple[str, ...]] = set()
    for row in existing:
        key = _row_key(row, keys)
        if key in incoming_by_key:
            if key not in consumed:
                merged_rows.append(incoming_by_key[key])
                consumed.add(key)
        else:
            merged_rows.append(row)
    for key, row in incoming_by_key.items():
        if key not in consumed:
            merged_rows.append(row)
    _write_raw_rows(file_name, columns, merged_rows, with_bom=has_bom)
    return load_csv(file_name)


def _replace_reit_rows(file_name: str, rows: pd.DataFrame) -> pd.DataFrame:
    columns, existing, has_bom = _read_raw_rows(file_name)
    preserved = [row for row in existing if row.get("reit_name", "") != GOLDEN_REIT_NAME]
    incoming = coerce_to_schema(rows, file_name)
    preserved.extend(_stringify_row(row, columns) for row in incoming.to_dict("records"))
    _write_raw_rows(file_name, columns, preserved, with_bom=has_bom)
    return load_csv(file_name)


def _rule_rows(retrieved_at: str) -> list[dict]:
    common = {
        "tax_year": 2026,
        "bracket_start": pd.NA,
        "bracket_end": pd.NA,
        "base_amount": pd.NA,
        "marginal_rate": pd.NA,
        "fair_market_value_ratio": pd.NA,
        "multiplier": pd.NA,
        "effective_from": "2026-01-01",
        "effective_to": "2026-12-31",
        "retrieved_at": retrieved_at[:10],
        "validation_status": "official_verified",
    }
    return [
        {
            **common,
            "rule_code": "public_reit_definition",
            "tax_name": "공모부동산투자회사 요건",
            "asset_type": "legal",
            "tax_classification": "public_reit",
            "law_name": "부동산투자회사법",
            "article": "제49조의3",
            "paragraph": "제1항",
            "exact_clause_summary": (
                "사모집합투자기구에 해당하지 않는 부동산투자회사인지 "
                "공식 인가·공모자료로 확인"
            ),
            "source_url": (
                "https://law.go.kr/LSW/lsLinkCommonInfo.do?"
                "lsJoLnkSeq=1024384319"
            ),
        },
        {
            **common,
            "rule_code": "public_reit_land_separation",
            "tax_name": "공모리츠 목적사업용 토지 분리과세 요건",
            "asset_type": "land",
            "tax_classification": "separated_public_reit",
            "law_name": "지방세법·지방세법 시행령",
            "article": "제106조제1항제3호아목·시행령 제102조제8항제3호",
            "paragraph": "",
            "exact_clause_summary": (
                "공모부동산투자회사가 목적사업에 사용하기 위하여 소유하는 토지는 "
                "주체·소유·사용 요건을 개별 확인"
            ),
            "source_url": (
                "https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&"
                "joBrNo=00&joNo=0102&lsiSeq=286395&urlMode=lsScJoRltInfoR"
            ),
        },
        {
            **common,
            "rule_code": "property_tax_obligor",
            "tax_name": "재산세 납세의무자",
            "asset_type": "land_building",
            "tax_classification": "taxpayer",
            "law_name": "지방세법",
            "article": "제107조",
            "paragraph": "제2항제5호",
            "exact_clause_summary": (
                "신탁재산으로서 수탁자 명의로 등기된 재산은 위탁자를 "
                "재산세 납세의무자로 확인"
            ),
            "source_url": (
                "https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&"
                "joBrNo=00&joNo=0107&lsiSeq=282559&urlMode=lsScJoRltInfoR"
            ),
        },
    ]


def _source_manifest_rows(snapshot: dict) -> list[dict]:
    rows = []
    for source in snapshot["sources"]:
        extraction_status = "extracted_normalized_facts"
        if source["document_type"] == "official_pdf":
            extraction_status = "extracted_text"
        elif source["document_type"] == "dart_filings":
            extraction_status = "extracted_html"
        rows.append(
            {
                "reit_name": GOLDEN_REIT_NAME,
                "document_type": source["document_type"],
                "document_name": source["document_name"],
                "document_date": source["document_date"],
                "source_url": source["source_url"],
                "local_cache_path": SNAPSHOT_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": source["sha256"],
                "downloaded_at": snapshot["retrieved_at"],
                "extraction_status": extraction_status,
                "relevant_pages": source["relevant_pages"],
                "notes": source["evidence"] + (
                    f" | 한계: {source['limitation']}"
                    if source.get("limitation")
                    else ""
                ),
            }
        )
    return rows


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _area_difference_tax_effect(snapshot: dict) -> dict[str, Decimal]:
    attached = snapshot["attached_lot_reconciliation"]
    parcel = snapshot["parcel"]
    difference = Decimal(str(attached["area_difference_m2"]))
    price = Decimal(str(parcel["individual_land_price_per_m2"]))
    assessed_value = difference * price
    property_tax_base = assessed_value * Decimal("0.70")
    property_tax = property_tax_base * Decimal("0.002")
    urban_area_tax = property_tax_base * Decimal("0.0014")
    local_education_tax = property_tax * Decimal("0.20")
    total = property_tax + urban_area_tax + local_education_tax
    expected = Decimal(str(attached["estimated_pre_rounding_tax_effect_krw"]))
    if total != expected:
        raise ValueError("Golden Asset 5.3㎡ 차이 세액 민감도가 스냅샷과 일치하지 않습니다.")
    return {
        "assessed_land_value": assessed_value,
        "property_tax_base": property_tax_base,
        "property_tax": property_tax,
        "urban_area_tax": urban_area_tax,
        "local_education_tax": local_education_tax,
        "total": total,
    }


def _write_evidence_artifacts(snapshot: dict) -> None:
    GOLDEN_DOC_DIR.mkdir(parents=True, exist_ok=True)
    evidence_rows: list[dict] = []
    for source in snapshot["sources"]:
        sha256 = str(source.get("sha256", ""))
        if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256.lower()):
            raise ValueError(f"유효한 SHA-256이 없는 Golden Asset 출처: {source['source_id']}")
        evidence_rows.append(
            {
                "evidence_id": source["source_id"],
                "metric_or_fact": source["metric_or_fact"],
                "value": source["value"],
                "unit": source["unit"],
                "source_name": source["document_name"],
                "source_url": source["source_url"],
                "source_date": source["document_date"],
                "source_page": source["relevant_pages"],
                "source_quote": source["source_quote"],
                "retrieved_at": snapshot["retrieved_at"],
                "sha256": sha256.lower(),
                "reliability": source["reliability"],
                "verification_status": source["verification_status"],
                "used_in_calculation": source["used_in_calculation"],
                "limitation": source["limitation"],
            }
        )
    if len(evidence_rows) < 16:
        raise ValueError("Golden Asset Evidence Matrix에는 최소 16개 출처가 필요합니다.")
    pd.DataFrame(evidence_rows, columns=EVIDENCE_MATRIX_COLUMNS).to_csv(
        EVIDENCE_MATRIX_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    attached = snapshot["attached_lot_reconciliation"]
    effect = _area_difference_tax_effect(snapshot)
    area_row = {
        "asset_id": snapshot["asset"]["asset_id"],
        "reported_or_historical_source": "제20기 투자보고서·건축물대장 표제부",
        "reported_or_historical_area_m2": attached["historical_or_reported_area_m2"],
        "current_land_register_source": "서울 부동산정보광장 현행 토지대장",
        "current_land_register_area_m2": attached["current_land_register_area_m2"],
        "difference_m2": attached["area_difference_m2"],
        "attached_lot_91_inclusion_status": attached["attached_lot_inclusion_status"],
        "calculation_area_m2": attached["calculation_area_m2"],
        "estimated_pre_rounding_tax_effect_krw": _decimal_text(effect["total"]),
        "tax_effect_formula": (
            "5.3㎡ × 63,950,000원/㎡ × 70% × "
            "[재산세 0.2% + 도시지역분 0.14% + 재산세 본세의 지방교육세 20%]"
        ),
        "calculation_treatment": attached["calculation_treatment"],
        "limitation": attached["tax_effect_limitation"],
    }
    pd.DataFrame([area_row]).to_csv(
        AREA_RECONCILIATION_PATH,
        index=False,
        encoding="utf-8-sig",
    )


def _master_rows(snapshot: dict) -> tuple[dict, dict, dict, dict, dict]:
    asset = snapshot["asset"]
    parcel = snapshot["parcel"]
    building = snapshot["building"]
    taxpayer = snapshot["taxpayer"]
    report = next(
        source
        for source in snapshot["sources"]
        if source["source_id"] == "skreit_investment_report_20"
    )
    land_source = next(
        source
        for source in snapshot["sources"]
        if source["source_id"] == "seoul_land_price_99"
    )
    building_source = next(
        source
        for source in snapshot["sources"]
        if source["source_id"] == "seoul_etax_building_value"
    )
    decree_source = next(
        source
        for source in snapshot["sources"]
        if source["source_id"] == "local_tax_enforcement_decree_2026"
    )

    obligor = determine_tax_obligor(
        {
            "legal_owner": taxpayer["registered_trustee"],
            "trustee": taxpayer["registered_trustee"],
            "trustor": taxpayer["trustor_and_tax_obligor"],
            "validation_status": "official_source_calculated",
            "source_url": report["source_url"],
        }
    )
    classification, classification_status, classification_reason = classify_public_reit_land(
        {
            "legal_reit_entity": True,
            "public_reit_qualified": taxpayer["public_reit_qualified"],
            "assessment_date_ownership_verified": taxpayer[
                "assessment_date_ownership_verified"
            ],
            "assessment_date_ownership_supported": taxpayer[
                "assessment_date_ownership_basis_status"
            ] == "public_disclosure_continuity_supported_registry_unverified",
            "purpose_business_use": taxpayer["purpose_business_use"],
            "non_housing_land": True,
            "no_special_exclusion": True,
            "validation_status": "official_source_calculated",
        }
    )
    if obligor.status != "official_source_calculated":
        raise ValueError(obligor.reason)
    if classification_status != "official_source_calculated":
        raise ValueError(classification_reason)

    assessed_land_value = (
        Decimal(str(parcel["individual_land_price_per_m2"]))
        * Decimal(str(parcel["taxable_area_m2"]))
        * Decimal(str(parcel["ownership_share"]))
    )
    if assessed_land_value != Decimal(str(parcel["assessed_land_value"])):
        raise ValueError("Golden Asset 토지 시가표준액 입력이 공식 원천값과 일치하지 않습니다.")
    component_total = Decimal(str(building["building_component_value"])) + Decimal(
        str(building["facility_component_value"])
    )
    if component_total != Decimal(str(building["building_standard_value"])):
        raise ValueError("Golden Asset 건축물 시가표준액 구성요소 합계가 일치하지 않습니다.")

    reit_row = {
        "stock_code": asset["stock_code"],
        "reit_name": asset["reit_name"],
        "legal_name": asset["legal_name"],
        "listed_status": "listed_verified",
        "listing_date": "2021-09-14",
        "reit_type": "위탁관리부동산투자회사",
        "public_reit_status": "official_source_calculated",
        "public_reit_evidence": (
            "제20기 투자보고서 p.25: 공모 의무 O, 공모 실시 O, "
            "30% 이상 공모충족일 2021-09-14"
        ),
        "official_website": "https://www.skreit.co.kr",
        "ir_page_url": "https://www.skreit.co.kr/ir/notice.php",
        "dart_corp_code": "",
        "asset_management_company": "에스케이리츠운용(주)",
        "latest_reporting_date": "2026-03-31",
        "source_url": report["source_url"],
        "verification_status": "official_source_calculated",
        "source_type": "official_reit_investment_report",
        "source_document_name": report["document_name"],
        "source_document_date": report["document_date"],
        "source_page": report["relevant_pages"],
        "source_quote_or_evidence": report["evidence"],
        "retrieved_at": snapshot["retrieved_at"],
        "source_hash": report["sha256"],
        "source_reliability": "tier_1_issuer_official_report",
        "reviewer_status": "reviewed",
    }
    asset_row = {
        "asset_id": asset["asset_id"],
        "stock_code": asset["stock_code"],
        "reit_name": asset["reit_name"],
        "asset_name": asset["asset_name"],
        "asset_class": "office",
        "asset_subclass": "corporate_office",
        "direct_or_indirect": "direct_investment_trust_title",
        "investment_holding_type": asset["investment_holding_type"],
        "title_holding_type": asset["title_holding_type"],
        "registered_owner": asset["registered_owner"],
        "trustee": asset["trustee"],
        "trustor": asset["trustor"],
        "beneficial_owner": asset["beneficial_owner"],
        "property_taxpayer": asset["property_taxpayer"],
        "listed_parent": asset["reit_name"],
        "legal_owner_name": taxpayer["registered_trustee"],
        "legal_owner_type": "trustee_for_reit",
        "ownership_vehicle_type": "listed_public_reit_trust",
        "subsidiary_reit_name": "",
        "spc_or_pfv_name": "",
        "fund_name": "",
        "trustee_name": taxpayer["registered_trustee"],
        "trustor_name": taxpayer["trustor_and_tax_obligor"],
        "ownership_share": asset["ownership_share"],
        "acquisition_date": asset["acquisition_date"],
        "purpose_use": asset["purpose_use"],
        "road_address": asset["road_address"],
        "lot_address": asset["lot_address"],
        "city": "서울특별시",
        "district": "종로구",
        "source_document": report["document_name"],
        "source_page": "6, 12, 14, 25",
        "source_url": report["source_url"],
        "address_confidence": "verified",
        "owner_confidence": "official_report_supported_registry_open",
        "verification_status": "official_source_calculated",
        "source_type": "official_reit_investment_report",
        "source_document_name": report["document_name"],
        "source_document_date": report["document_date"],
        "source_quote_or_evidence": (
            "p.6 서린빌딩 취득 및 신탁, p.12 종로26·대지 5,778.80㎡·"
            "연면적 83,827.66㎡, p.14 임대율 100%"
        ),
        "retrieved_at": snapshot["retrieved_at"],
        "source_hash": report["sha256"],
        "source_reliability": "tier_1_issuer_official_report",
        "reviewer_status": "reviewed",
    }
    parcel_row = {
        "parcel_id": parcel["parcel_id"],
        "asset_id": asset["asset_id"],
        "taxpayer_id": taxpayer["taxpayer_id"],
        "pnu": parcel["pnu"],
        "road_address": asset["road_address"],
        "lot_address": asset["lot_address"],
        "latitude": pd.NA,
        "longitude": pd.NA,
        "parcel_area_m2": parcel["parcel_area_m2"],
        "ownership_share": parcel["ownership_share"],
        "taxable_area_m2": parcel["taxable_area_m2"],
        "individual_land_price_per_m2": parcel["individual_land_price_per_m2"],
        "official_price_year": parcel["official_price_year"],
        "assessed_land_value": parcel["assessed_land_value"],
        "land_use": f"{parcel['land_category']} / {parcel['land_use']}",
        "urban_area_status": parcel["land_use"],
        "tax_urban_area_status": parcel["tax_urban_area_status"],
        "data_source": "서울 부동산정보광장 토지대장·개별공시지가·토지이용계획",
        "source_date": parcel["official_price_announcement_date"],
        "validation_status": "official_source_calculated",
        "source_type": "official_seoul_land_api",
        "source_url": land_source["source_url"],
        "source_document_name": land_source["document_name"],
        "source_document_date": land_source["document_date"],
        "source_page": f"PNU {parcel['pnu']}",
        "source_quote_or_evidence": (
            f"면적 {parcel['parcel_area_m2']:,.1f}㎡, 개별공시지가 "
            f"{parcel['individual_land_price_per_m2']:,}원/㎡, 도시지역"
        ),
        "retrieved_at": snapshot["retrieved_at"],
        "source_hash": land_source["sha256"],
        "source_reliability": "tier_1_municipal_land_system",
        "reviewer_status": "reviewed",
    }
    building_row = {
        "building_id": building["building_id"],
        "asset_id": asset["asset_id"],
        "building_name": building["official_building_name"],
        "building_address": asset["road_address"],
        "building_register_id": building["building_register_id"],
        "gross_floor_area_m2": building["gross_floor_area_m2"],
        "main_use": building["main_use"],
        "structure_type": building["structure_type"],
        "completion_year": building["completion_date"][:4],
        "floor_count": (
            f"지상 {building['above_ground_floors']} / "
            f"지하 {building['below_ground_floors']}"
        ),
        "building_standard_value": building["building_standard_value"],
        "building_standard_value_year": building["building_standard_value_year"],
        "building_standard_value_nature": building["building_standard_value_nature"],
        "property_tax_base_method": building["property_tax_base_method"],
        "fire_resource_tax_base_method": building["fire_resource_tax_base_method"],
        "calculation_source": (
            "서울시 ETAX 2026 주택외건물 시가표준액조회: "
            f"건물 {building['building_component_value']:,}원 + "
            f"시설 {building['facility_component_value']:,}원"
        ),
        "fire_risk_category": building["fire_risk_category"],
        "fire_tax_multiplier": building["fire_tax_multiplier"],
        "fire_tax_multiplier_status": building["fire_tax_multiplier_status"],
        "fire_tax_evidence_source_url": decree_source["source_url"],
        "fire_tax_evidence_page": building["fire_tax_evidence_page"],
        "fire_tax_evidence_quote": building["fire_tax_evidence_quote"],
        "urban_area_status": building["urban_area_status"],
        "source_url": building_source["source_url"],
        "source_page": building_source["relevant_pages"],
        "validation_status": "official_source_calculated",
        "source_type": "official_seoul_etax",
        "source_document_name": building_source["document_name"],
        "source_document_date": building_source["document_date"],
        "source_quote_or_evidence": (
            f"시가표준액 합계 {building['building_standard_value']:,}원; "
            "건축물대장상 업무시설·지상 36층으로 시행령 제138조 대형 화재위험 건축물"
        ),
        "retrieved_at": snapshot["retrieved_at"],
        "source_hash": building_source["sha256"],
        "source_reliability": "tier_1_municipal_tax_system",
        "reviewer_status": "reviewed",
    }
    taxpayer_row = {
        "taxpayer_id": taxpayer["taxpayer_id"],
        "asset_id": asset["asset_id"],
        "legal_owner": taxpayer["registered_trustee"],
        "beneficial_owner": taxpayer["trustor_and_tax_obligor"],
        "trustee": taxpayer["registered_trustee"],
        "trustor": taxpayer["trustor_and_tax_obligor"],
        "ownership_share": asset["ownership_share"],
        "tax_obligor": obligor.tax_obligor,
        "taxpayer_evidence": (
            "제20기 투자보고서 p.6 취득 및 신탁(수탁자 대한토지신탁)과 "
            "지방세법 제107조제2항제5호"
        ),
        "public_reit_qualified": taxpayer["public_reit_qualified"],
        "qualifying_subsidiary_reit": False,
        "purpose_business_use": taxpayer["purpose_business_use"],
        "separation_tax_eligible": True,
        "separation_tax_reason": classification_reason,
        "tax_classification": classification,
        "statutory_eligibility_status": taxpayer["statutory_eligibility_status"],
        "actual_notice_classification": taxpayer["actual_notice_classification"],
        "legal_review_status": taxpayer["legal_review_status"],
        "notice_reconciliation_status": taxpayer["notice_reconciliation_status"],
        "assessment_date_ownership_basis_status": taxpayer[
            "assessment_date_ownership_basis_status"
        ],
        "assessment_date_ownership_verified": taxpayer[
            "assessment_date_ownership_verified"
        ],
        "nationwide_land_aggregation_verified": False,
        "property_tax_credit": pd.NA,
        "property_tax_credit_source_url": "",
        "manual_review_flag": True,
        "source_url": report["source_url"],
        "source_page": "6, 10, 12, 14, 25",
        "validation_status": "official_source_calculated",
        "source_type": "official_report_and_law",
        "source_document_name": report["document_name"],
        "source_document_date": report["document_date"],
        "source_quote_or_evidence": (
            "공식 보고서상 직접취득·신탁·오피스 임대·공모 이행 및 "
            "현행 법령을 결합한 공식자료 판정"
        ),
        "retrieved_at": snapshot["retrieved_at"],
        "source_hash": report["sha256"],
        "source_reliability": "tier_1_official_report_and_statute",
        "reviewer_status": "reviewed_notice_open",
    }
    return reit_row, asset_row, parcel_row, building_row, taxpayer_row


def _custom_validation_row(snapshot: dict) -> dict:
    asset = snapshot["asset"]
    attached = snapshot["attached_lot_reconciliation"]
    key = f"{GOLDEN_REIT_NAME}|{asset['asset_id']}|parcel_area_reconciliation"
    return {
        "validation_id": hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
        "reit_name": GOLDEN_REIT_NAME,
        "taxpayer_id": snapshot["taxpayer"]["taxpayer_id"],
        "asset_id": asset["asset_id"],
        "parcel_id": snapshot["parcel"]["parcel_id"],
        "building_id": snapshot["building"]["building_id"],
        "check_name": "parcel_area_reconciliation",
        "severity": "medium",
        "validation_status": "failed",
        "message": (
            "건축물대장 대지면적과 현행 토지대장 면적 간 "
            f"{attached['area_difference_m2']}㎡ 차이 및 부속지번 91의 현재 상태를 "
            "최신 토지대장·지적도 또는 과세내역서로 대사해야 합니다."
        ),
        "source_url": "https://land.seoul.go.kr/land/wskras/generalInfo.do",
        "reviewer_status": "open",
    }


def _request_rows(validations: pd.DataFrame, snapshot: dict) -> pd.DataFrame:
    requests = build_request_list(validations)
    requests = requests[requests["issue_code"].ne("parcel_area_reconciliation")]
    extras = [
        {
            "request_id": hashlib.sha256(
                f"{GOLDEN_REIT_NAME}|parcel_area_reconciliation".encode("utf-8")
            ).hexdigest()[:16],
            "reit_name": GOLDEN_REIT_NAME,
            "taxpayer_id": snapshot["taxpayer"]["taxpayer_id"],
            "asset_id": snapshot["asset"]["asset_id"],
            "issue_code": "parcel_area_reconciliation",
            "issue": "건축물대장 부속지번 서린동 91과 현행 토지대장 간 5.3㎡ 차이",
            "request_document": "최신 토지대장·지적도 및 필지별 재산세 과세내역서",
            "request_reason": "현행 과세대상 필지 완전성과 5.3㎡ 차이 원인 확인",
            "priority": "P1",
            "calculation_status": "manual_review_required",
            "reviewer_status": "open",
        },
        {
            "request_id": hashlib.sha256(
                f"{GOLDEN_REIT_NAME}|trust_registry".encode("utf-8")
            ).hexdigest()[:16],
            "reit_name": GOLDEN_REIT_NAME,
            "taxpayer_id": snapshot["taxpayer"]["taxpayer_id"],
            "asset_id": snapshot["asset"]["asset_id"],
            "issue_code": "trust_registry_reconciliation",
            "issue": "공식 투자보고서 기반 신탁·납세의무자 판정",
            "request_document": "2026년 6월 1일 현재 등기부등본·신탁원부",
            "request_reason": "수탁자·위탁자와 과세기준일 현재 소유관계 원문 대사",
            "priority": "P1",
            "calculation_status": "manual_review_required",
            "reviewer_status": "open",
        },
    ]
    return coerce_to_schema(
        pd.concat([requests, pd.DataFrame(extras)], ignore_index=True),
        "request_list.csv",
    ).drop_duplicates("request_id")


def _reconciliation_rows(calculations: pd.DataFrame, snapshot: dict) -> pd.DataFrame:
    calculated = calculations[
        calculations["calculation_status"].isin(
            ["verified_notice", "official_source_calculated", "not_applicable"]
        )
        & calculations["tax_name"].ne("토지 시가표준액")
    ].copy()
    total = sum(
        (
            Decimal(str(value))
            for value in calculated["calculated_tax"]
            if not pd.isna(value)
        ),
        Decimal("0"),
    )
    attached = snapshot["attached_lot_reconciliation"]
    area_effect = _area_difference_tax_effect(snapshot)
    building = snapshot["building"]
    building_components = (
        building["building_component_value"] + building["facility_component_value"]
    )
    rows = [
        {
            "reit_name": GOLDEN_REIT_NAME,
            "taxpayer_id": snapshot["taxpayer"]["taxpayer_id"],
            "tax_year": snapshot["tax_year"],
            "metric": "holding_tax_notice_reconciliation",
            "calculated_value": total,
            "disclosed_or_verified_value": pd.NA,
            "variance": pd.NA,
            "variance_percent": pd.NA,
            "reconciliation_reason": (
                f"{STATUTORY_RECALCULATION_LABEL}과 실제 고지세액의 대사. "
                "2026년 재산세 고지서·과세내역서가 없어 실제 고지액은 미확인"
            ),
            "reviewer_status": "open",
        },
        {
            "reit_name": GOLDEN_REIT_NAME,
            "taxpayer_id": snapshot["taxpayer"]["taxpayer_id"],
            "tax_year": snapshot["tax_year"],
            "metric": "parcel_area_register_to_building_ledger",
            "calculated_value": snapshot["parcel"]["parcel_area_m2"],
            "disclosed_or_verified_value": building["building_register_site_area_m2"],
            "variance": -Decimal(str(attached["area_difference_m2"])),
            "variance_percent": (
                -attached["area_difference_m2"]
                / building["building_register_site_area_m2"]
                * 100
            ),
            "reconciliation_reason": attached["calculation_treatment"],
            "reviewer_status": "open",
        },
        {
            "reit_name": GOLDEN_REIT_NAME,
            "taxpayer_id": snapshot["taxpayer"]["taxpayer_id"],
            "tax_year": snapshot["tax_year"],
            "metric": "parcel_area_difference_tax_sensitivity",
            "calculated_value": area_effect["total"],
            "disclosed_or_verified_value": pd.NA,
            "variance": pd.NA,
            "variance_percent": pd.NA,
            "reconciliation_reason": (
                "5.3㎡ 전부를 동일 지가·분리과세·도시지역분 대상으로 가정한 "
                "법정 절사 전 민감도이며 실제 고지 차이가 아님"
            ),
            "reviewer_status": "open",
        },
        {
            "reit_name": GOLDEN_REIT_NAME,
            "taxpayer_id": snapshot["taxpayer"]["taxpayer_id"],
            "tax_year": snapshot["tax_year"],
            "metric": "building_value_component_reconciliation",
            "calculated_value": building_components,
            "disclosed_or_verified_value": building["building_standard_value"],
            "variance": building_components - building["building_standard_value"],
            "variance_percent": 0,
            "reconciliation_reason": "서울시 ETAX 건물분과 시설분 합계가 조회 합계와 일치",
            "reviewer_status": "reviewed",
        },
    ]
    return coerce_to_schema(pd.DataFrame(rows), "reconciliation.csv")


def run() -> dict:
    snapshot = _read_snapshot()
    _write_evidence_artifacts(snapshot)
    retrieved_at = snapshot["retrieved_at"]
    reit_row, asset_row, parcel_row, building_row, taxpayer_row = _master_rows(snapshot)

    _upsert("reit_master.csv", [reit_row], ["stock_code"])
    source_rows = coerce_to_schema(
        pd.DataFrame(_source_manifest_rows(snapshot)),
        "source_document_manifest.csv",
    )
    _replace_reit_rows("source_document_manifest.csv", source_rows)
    _upsert("asset_master.csv", [asset_row], ["asset_id"])
    _upsert("parcel_master.csv", [parcel_row], ["parcel_id"])
    _upsert("building_master.csv", [building_row], ["building_id"])
    _upsert("taxpayer_structure.csv", [taxpayer_row], ["taxpayer_id", "asset_id"])
    _upsert("tax_rule_master.csv", _rule_rows(retrieved_at), ["tax_year", "rule_code"])

    bundle = load_v15_bundle()
    calculations = calculate_holding_tax_detail(
        GOLDEN_REIT_NAME,
        bundle.assets,
        bundle.parcels,
        bundle.buildings,
        bundle.taxpayers,
        bundle.rules,
        int(snapshot["tax_year"]),
    )
    calculations["calculation_timestamp"] = retrieved_at
    calculations = coerce_to_schema(calculations, "tax_calculation_detail.csv")
    all_calculations = _replace_reit_rows("tax_calculation_detail.csv", calculations)

    bundle = load_v15_bundle()
    assets = bundle.assets[bundle.assets["reit_name"].astype(str).eq(GOLDEN_REIT_NAME)]
    asset_ids = set(assets["asset_id"].dropna().astype(str))
    parcels = bundle.parcels[bundle.parcels["asset_id"].astype(str).isin(asset_ids)]
    buildings = bundle.buildings[bundle.buildings["asset_id"].astype(str).isin(asset_ids)]
    taxpayers = bundle.taxpayers[bundle.taxpayers["asset_id"].astype(str).isin(asset_ids)]
    validations = build_validation_results(
        GOLDEN_REIT_NAME,
        assets,
        parcels,
        buildings,
        taxpayers,
        calculations,
    )
    validations = coerce_to_schema(
        pd.concat(
            [validations, pd.DataFrame([_custom_validation_row(snapshot)])],
            ignore_index=True,
        ),
        "validation_result.csv",
    ).drop_duplicates("validation_id")
    _replace_reit_rows("validation_result.csv", validations)
    _replace_reit_rows("request_list.csv", _request_rows(validations, snapshot))
    _replace_reit_rows(
        "reconciliation.csv", _reconciliation_rows(calculations, snapshot)
    )

    bundle = load_v15_bundle()
    coverage = build_coverage_manifest(bundle)
    coverage.to_csv(
        V15_DATA_DIR / "coverage_manifest.csv", index=False, encoding="utf-8-sig"
    )
    report = build_coverage_report(bundle, coverage)
    report_timestamp = (
        datetime.fromisoformat(retrieved_at).astimezone(timezone.utc).isoformat()
    )
    report = "\n".join(
        f"생성시각(UTC): {report_timestamp}"
        if line.startswith("생성시각(UTC):")
        else line
        for line in report.splitlines()
    )
    report += "\n"
    report_path = PROJECT_ROOT / "docs" / "v15" / "COVERAGE_REPORT.md"
    report_path.write_text(report, encoding="utf-8")

    numeric = pd.to_numeric(calculations["calculated_tax"], errors="coerce")
    source_calculated = calculations[
        calculations["calculation_status"].isin(
            ["verified_notice", "official_source_calculated", "not_applicable"]
        )
        & calculations["tax_name"].ne("토지 시가표준액")
    ]
    total = sum(
        (
            Decimal(str(value))
            for value in source_calculated["calculated_tax"]
            if not pd.isna(value)
        ),
        Decimal("0"),
    )
    return {
        "asset_id": snapshot["asset"]["asset_id"],
        "calculation_rows": len(calculations),
        "calculated_rows": int(numeric.notna().sum()),
        "official_source_total": float(total),
        "statutory_recalculation_label": STATUTORY_RECALCULATION_LABEL,
        "statutory_recalculation_raw": _decimal_text(total),
        "actual_notice_amount": None,
        "all_calculation_rows": len(all_calculations),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="공식자료가 연결된 첫 v15 Golden Asset 계산을 재현합니다."
    )
    parser.parse_args()
    print(json.dumps(run(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
