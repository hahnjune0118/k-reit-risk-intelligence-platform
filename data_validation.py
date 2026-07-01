import pandas as pd


REQUIRED_TABLE_COLUMNS = {
    "financials": {
        "period_end",
        "source_document",
        "source_confidence",
    },
    "kpis": {
        "period_end",
        "ffo_mn_krw",
        "nav_mn_krw",
        "common_dividend_total_mn_krw",
        "leverage_pct",
        "interest_coverage_x",
        "avg_borrowing_rate_pct",
        "fixed_rate_debt_pct",
        "debt_weighted_average_maturity_yrs",
        "occupancy_pct",
        "wale_yrs",
        "source_document",
        "source_confidence",
    },
    "assets": {
        "asset_name",
        "asset_type",
        "location",
        "land_area_sqm",
        "gross_floor_area_sqm",
        "nla_or_leasable_area_sqm",
        "acquisition_date",
        "acquisition_price_mn_krw",
        "appraised_value_mn_krw_20251231",
        "value_uplift_pct",
        "major_tenant",
        "tenant_credit",
        "tenant_concentration_pct",
        "wale_yrs",
        "cap_rate_pct_20251231",
        "estimated_annual_rent_mn_krw",
        "source_document",
        "source_confidence",
    },
    "debt_schedule": {
        "period_end",
        "principal_mn_krw",
        "all_in_rate_pct",
        "borrowing_or_issue_date",
        "maturity_date",
        "fixed_rate_or_index",
        "source_document",
        "source_confidence",
    },
    "debt_summary": {
        "maturity_year",
        "principal_mn_krw",
        "weighted_avg_all_in_rate_pct",
        "number_of_facilities",
    },
    "source_plan": {
        "priority",
        "report_name",
        "where_to_find",
        "fields_to_extract",
        "project_use",
    },
    "data_dictionary": {
        "table",
        "field",
        "definition",
        "use",
    },
}


def missing_columns(df: pd.DataFrame, required_columns: set[str]) -> list[str]:
    return sorted(required_columns.difference(set(df.columns)))


def validate_bundle(bundle: dict[str, pd.DataFrame]) -> dict[str, list[str]]:
    errors = {}
    for table_name, required_columns in REQUIRED_TABLE_COLUMNS.items():
        df = bundle.get(table_name)
        if df is None:
            errors[table_name] = ["table is missing"]
            continue
        missing = missing_columns(df, required_columns)
        if missing:
            errors[table_name] = missing
    return errors
