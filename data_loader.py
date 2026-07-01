import pandas as pd
import streamlit as st

from config import DATA_DIR
from data_validation import validate_bundle
from formatting import extract_number


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        st.error(f"Required data file is missing: {path}")
        st.stop()
    return pd.read_csv(path)


@st.cache_data
def load_data(as_of_date: str | None = None):
    bundle = {
        "financials": load_csv("sk_reit_consolidated_financials.csv"),
        "kpis": load_csv("sk_reit_latest_kpis.csv"),
        "assets": load_csv("sk_reit_asset_metrics.csv"),
        "direct_assets": load_csv("sk_reit_parent_direct_assets_20260331.csv"),
        "debt_schedule": load_csv("sk_reit_debt_schedule_20260331.csv"),
        "debt_summary": load_csv("sk_reit_debt_summary_20260331.csv"),
        "source_plan": load_csv("sk_reit_additional_source_plan.csv"),
        "data_dictionary": load_csv("sk_reit_data_dictionary.csv"),
    }

    validation_errors = validate_bundle(bundle)
    if validation_errors:
        for table_name, missing in validation_errors.items():
            st.error(f"Data validation failed for {table_name}: missing columns {', '.join(missing)}")
        st.stop()

    financials = bundle["financials"]
    kpis = bundle["kpis"]
    assets = bundle["assets"]
    direct_assets = bundle["direct_assets"]
    debt_schedule = bundle["debt_schedule"]
    debt_summary = bundle["debt_summary"]
    source_plan = bundle["source_plan"]
    data_dictionary = bundle["data_dictionary"]

    # Dates
    for df, cols in [
        (financials, ["period_end"]),
        (kpis, ["period_end"]),
        (assets, ["acquisition_date"]),
        (debt_schedule, ["borrowing_or_issue_date", "maturity_date", "period_end"]),
        (debt_summary, ["period_end"]),
    ]:
        for col in cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

    # Numeric hygiene
    if "estimated_annual_rent_mn_krw" in assets.columns:
        assets["estimated_annual_rent_mn_krw_num"] = assets["estimated_annual_rent_mn_krw"].apply(extract_number)
        assets["annual_rent_yield_on_acquisition_pct"] = (
            assets["estimated_annual_rent_mn_krw_num"] / assets["acquisition_price_mn_krw"] * 100
        )
        assets["annual_rent_yield_on_appraisal_pct"] = (
            assets["estimated_annual_rent_mn_krw_num"] / assets["appraised_value_mn_krw_20251231"] * 100
        )

    if "gross_floor_area_sqm" in assets.columns:
        assets["asset_value_per_sqm_mn_krw"] = (
            assets["appraised_value_mn_krw_20251231"] / assets["gross_floor_area_sqm"]
        )

    if "tenant_concentration_pct" in assets.columns:
        assets["single_tenant_or_master_lease"] = assets["tenant_concentration_pct"].astype(str).str.contains(
            "100|master", case=False, na=False
        )

    debt_schedule["maturity_year"] = debt_schedule["maturity_date"].dt.year.astype("Int64")
    as_of = pd.Timestamp(as_of_date).normalize() if as_of_date else pd.Timestamp.today().normalize()
    debt_schedule["days_to_maturity"] = (debt_schedule["maturity_date"] - as_of).dt.days
    debt_schedule["rate_type"] = debt_schedule["fixed_rate_or_index"].apply(
        lambda x: "변동" if "변동" in str(x) else "고정"
    )

    return {
        "financials": financials,
        "kpis": kpis,
        "assets": assets,
        "direct_assets": direct_assets,
        "debt_schedule": debt_schedule,
        "debt_summary": debt_summary,
        "source_plan": source_plan,
        "data_dictionary": data_dictionary,
    }
