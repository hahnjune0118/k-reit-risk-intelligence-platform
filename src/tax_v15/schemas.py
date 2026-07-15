from __future__ import annotations

from pathlib import Path

import pandas as pd

from .constants import V15_DATA_DIR


CSV_SCHEMAS: dict[str, list[str]] = {
    "reit_master.csv": [
        "stock_code", "reit_name", "legal_name", "listed_status", "listing_date", "reit_type",
        "public_reit_status", "public_reit_evidence", "official_website", "ir_page_url",
        "dart_corp_code", "asset_management_company", "latest_reporting_date", "source_url",
        "verification_status", "source_type", "source_document_name", "source_document_date",
        "source_page", "source_quote_or_evidence", "retrieved_at", "source_hash",
        "source_reliability", "reviewer_status",
    ],
    "coverage_manifest.csv": [
        "reit_name", "stock_code", "official_website_found", "ir_documents_checked",
        "dart_documents_checked", "asset_count_identified", "address_count_verified",
        "parcel_count_verified", "land_price_coverage", "building_value_coverage",
        "taxpayer_coverage", "tax_calculation_status", "blocking_reason", "next_action",
    ],
    "source_document_manifest.csv": [
        "reit_name", "document_type", "document_name", "document_date", "source_url",
        "local_cache_path", "sha256", "downloaded_at", "extraction_status", "relevant_pages", "notes",
    ],
    "asset_master.csv": [
        "asset_id", "stock_code", "reit_name", "asset_name", "asset_class", "asset_subclass",
        "direct_or_indirect", "listed_parent", "legal_owner_name", "legal_owner_type",
        "ownership_vehicle_type", "subsidiary_reit_name", "spc_or_pfv_name", "fund_name",
        "trustee_name", "trustor_name", "ownership_share", "acquisition_date", "purpose_use",
        "road_address", "lot_address", "city", "district", "source_document", "source_page",
        "source_url", "address_confidence", "owner_confidence", "verification_status",
        "source_type", "source_document_name", "source_document_date", "source_quote_or_evidence",
        "retrieved_at", "source_hash", "source_reliability", "reviewer_status",
    ],
    "parcel_master.csv": [
        "parcel_id", "asset_id", "taxpayer_id", "pnu", "road_address", "lot_address", "latitude", "longitude",
        "parcel_area_m2", "ownership_share", "taxable_area_m2", "individual_land_price_per_m2",
        "official_price_year", "assessed_land_value", "land_use", "urban_area_status",
        "tax_urban_area_status", "data_source", "source_date", "validation_status", "source_type",
        "source_url", "source_document_name", "source_document_date", "source_page",
        "source_quote_or_evidence", "retrieved_at", "source_hash", "source_reliability", "reviewer_status",
    ],
    "building_master.csv": [
        "building_id", "asset_id", "building_name", "building_address", "building_register_id",
        "gross_floor_area_m2", "main_use", "structure_type", "completion_year", "floor_count",
        "building_standard_value", "building_standard_value_year", "calculation_source",
        "fire_risk_category", "fire_tax_multiplier", "urban_area_status", "source_url", "source_page",
        "validation_status", "source_type", "source_document_name", "source_document_date",
        "source_quote_or_evidence", "retrieved_at", "source_hash", "source_reliability", "reviewer_status",
    ],
    "taxpayer_structure.csv": [
        "taxpayer_id", "asset_id", "legal_owner", "beneficial_owner", "trustee", "trustor",
        "ownership_share", "tax_obligor", "taxpayer_evidence", "public_reit_qualified",
        "qualifying_subsidiary_reit", "purpose_business_use", "separation_tax_eligible",
        "separation_tax_reason", "tax_classification", "assessment_date_ownership_verified",
        "nationwide_land_aggregation_verified", "property_tax_credit", "property_tax_credit_source_url",
        "manual_review_flag", "source_url", "source_page", "validation_status", "source_type",
        "source_document_name", "source_document_date", "source_quote_or_evidence", "retrieved_at",
        "source_hash", "source_reliability", "reviewer_status",
    ],
    "tax_rule_master.csv": [
        "tax_year", "rule_code", "tax_name", "asset_type", "tax_classification", "bracket_start",
        "bracket_end", "base_amount", "marginal_rate", "fair_market_value_ratio", "multiplier",
        "effective_from", "effective_to", "law_name", "article", "paragraph", "exact_clause_summary",
        "source_url", "retrieved_at", "validation_status",
    ],
    "tax_calculation_detail.csv": [
        "tax_year", "reit_name", "taxpayer_id", "asset_id", "parcel_id", "building_id", "tax_name",
        "tax_classification", "official_value", "taxable_area", "ownership_share",
        "fair_market_value_ratio", "tax_base", "bracket", "base_amount", "tax_rate", "multiplier",
        "calculated_tax", "verified_tax", "variance", "calculation_status", "law_name", "article",
        "formula_text", "input_source", "source_url", "calculation_timestamp",
    ],
    "reconciliation.csv": [
        "reit_name", "taxpayer_id", "tax_year", "metric", "calculated_value",
        "disclosed_or_verified_value", "variance", "variance_percent", "reconciliation_reason",
        "reviewer_status",
    ],
    "request_list.csv": [
        "request_id", "reit_name", "taxpayer_id", "asset_id", "issue_code", "issue",
        "request_document", "request_reason", "priority", "calculation_status", "reviewer_status",
    ],
    "validation_result.csv": [
        "validation_id", "reit_name", "taxpayer_id", "asset_id", "parcel_id", "building_id",
        "check_name", "severity", "validation_status", "message", "source_url", "reviewer_status",
    ],
}


def empty_frame(file_name: str) -> pd.DataFrame:
    return pd.DataFrame(columns=CSV_SCHEMAS[file_name])


def ensure_v15_csv_files(data_dir: Path = V15_DATA_DIR) -> list[Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for file_name, columns in CSV_SCHEMAS.items():
        path = data_dir / file_name
        if not path.exists():
            pd.DataFrame(columns=columns).to_csv(path, index=False, encoding="utf-8-sig")
            created.append(path)
    return created


def coerce_to_schema(frame: pd.DataFrame, file_name: str) -> pd.DataFrame:
    result = frame.copy()
    for column in CSV_SCHEMAS[file_name]:
        if column not in result.columns:
            result[column] = pd.NA
    return result[CSV_SCHEMAS[file_name]]
