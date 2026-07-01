import re

import pandas as pd

from formatting import format_pct_from_100, format_ratio, format_years


def calculate_reit_level_risk(latest_kpi: pd.Series, debt_schedule: pd.DataFrame, assets: pd.DataFrame):
    """Rule-based scoring designed for REIT screening, not formal credit rating."""
    scores = {}
    flags = []

    # Income / lease stability
    income_score = 0
    occupancy = latest_kpi.get("occupancy_pct", pd.NA)
    wale = latest_kpi.get("wale_yrs", pd.NA)
    if pd.notna(occupancy) and occupancy < 95:
        income_score += 35
        flags.append("Portfolio occupancy below 95%")
    if pd.notna(wale):
        if wale < 2.0:
            income_score += 30
            flags.append("WALE below 2.0 years")
        elif wale < 3.0:
            income_score += 15
            flags.append("WALE below 3.0 years")
    if "single_tenant_or_master_lease" in assets.columns:
        single_tenant_share = assets[assets["single_tenant_or_master_lease"]]["appraised_value_mn_krw_20251231"].sum() / assets["appraised_value_mn_krw_20251231"].sum()
        if single_tenant_share > 0.65:
            income_score += 20
            flags.append("High master-lease / single-tenant exposure by appraised value")
    scores["Income / Lease Stability Risk"] = min(income_score, 100)

    # Refinancing / debt service
    debt_score = 0
    leverage = latest_kpi.get("leverage_pct", pd.NA)
    icr = latest_kpi.get("interest_coverage_x", pd.NA)
    avg_rate = latest_kpi.get("avg_borrowing_rate_pct", pd.NA)
    wam = latest_kpi.get("debt_weighted_average_maturity_yrs", pd.NA)
    fixed_pct = latest_kpi.get("fixed_rate_debt_pct", pd.NA)

    if pd.notna(leverage):
        if leverage >= 55:
            debt_score += 30
            flags.append("Leverage at or above 55%")
        elif leverage >= 50:
            debt_score += 15
            flags.append("Leverage at or above 50%")
    if pd.notna(icr):
        if icr < 2.0:
            debt_score += 30
            flags.append("Interest coverage below 2.0x")
        elif icr < 2.5:
            debt_score += 20
            flags.append("Interest coverage below 2.5x")
    if pd.notna(wam):
        if wam < 1.5:
            debt_score += 25
            flags.append("Debt weighted average maturity below 1.5 years")
        elif wam < 2.0:
            debt_score += 15
            flags.append("Debt weighted average maturity below 2.0 years")
    if pd.notna(fixed_pct) and fixed_pct < 50:
        debt_score += 15
        flags.append("Fixed-rate debt ratio below 50%")
    if pd.notna(avg_rate) and avg_rate > 4.5:
        debt_score += 10
        flags.append("Average borrowing rate above 4.5%")

    near_term_debt = debt_schedule[debt_schedule["days_to_maturity"].between(0, 365, inclusive="both")]["principal_mn_krw"].sum()
    total_debt = debt_schedule["principal_mn_krw"].sum()
    near_term_share = near_term_debt / total_debt if total_debt else 0
    if near_term_share > 0.25:
        debt_score += 20
        flags.append("More than 25% of disclosed debt matures within one year")
    scores["Refinancing / Debt Service Risk"] = min(debt_score, 100)

    # Valuation / NAV risk
    valuation_score = 0
    uplift = assets["value_uplift_pct"].mean()
    cap_rate_mean = assets["cap_rate_pct_20251231"].mean()
    if pd.notna(cap_rate_mean) and cap_rate_mean < 4.0:
        valuation_score += 20
        flags.append("Average asset cap rate below 4%")
    if pd.notna(uplift) and uplift > 20:
        valuation_score += 15
        flags.append("Average valuation uplift above 20% vs acquisition price")
    office_share = assets[assets["asset_type"].str.contains("office", case=False, na=False)]["appraised_value_mn_krw_20251231"].sum() / assets["appraised_value_mn_krw_20251231"].sum()
    if office_share > 0.65:
        valuation_score += 10
        flags.append("Office-concentrated portfolio")
    scores["Valuation / NAV Sensitivity Risk"] = min(valuation_score, 100)

    # Data quality / basis risk
    data_score = 0
    derived_rent_count = assets["estimated_annual_rent_mn_krw"].astype(str).str.contains("derived", case=False, na=False).sum()
    missing_nla_count = assets["nla_or_leasable_area_sqm"].isna().sum()
    if derived_rent_count > 0:
        data_score += min(derived_rent_count * 10, 40)
        flags.append("Some asset-level annual rent figures are derived rather than directly disclosed")
    if missing_nla_count > 0:
        data_score += min(missing_nla_count * 5, 25)
        flags.append("Some assets lack explicit NLA / leasable area")
    data_score += 15
    flags.append("Parent investment-report KPIs and consolidated K-IFRS figures are separate bases")
    scores["Disclosure / Data Basis Risk"] = min(data_score, 100)

    total_score = (
        scores["Income / Lease Stability Risk"] * 0.25
        + scores["Refinancing / Debt Service Risk"] * 0.35
        + scores["Valuation / NAV Sensitivity Risk"] * 0.25
        + scores["Disclosure / Data Basis Risk"] * 0.15
    )

    if total_score >= 70:
        level = "High"
    elif total_score >= 40:
        level = "Medium"
    else:
        level = "Low"

    return scores, total_score, level, flags


def add_score_rule(rows, category, driver, triggered, score_delta, weight, current_value="", threshold="", interpretation=""):
    """Append one transparent rule row for score decomposition."""
    rows.append({
        "risk_category": category,
        "driver": driver,
        "triggered": bool(triggered),
        "score_delta": float(score_delta) if triggered else 0.0,
        "weight_pct": weight * 100,
        "weighted_score_delta": (float(score_delta) * weight) if triggered else 0.0,
        "current_value": current_value,
        "threshold": threshold,
        "interpretation": interpretation,
    })


def build_reit_score_decomposition(latest_kpi: pd.Series, debt_schedule: pd.DataFrame, assets: pd.DataFrame) -> pd.DataFrame:
    """Create a rating-agency style decomposition of the REIT-level rule-based score."""
    rows = []
    weights = {
        "Income / Lease Stability Risk": 0.25,
        "Refinancing / Debt Service Risk": 0.35,
        "Valuation / NAV Sensitivity Risk": 0.25,
        "Disclosure / Data Basis Risk": 0.15,
    }

    occupancy = latest_kpi.get("occupancy_pct", pd.NA)
    wale = latest_kpi.get("wale_yrs", pd.NA)
    single_tenant_share = pd.NA
    total_asset_value = assets["appraised_value_mn_krw_20251231"].sum()
    if "single_tenant_or_master_lease" in assets.columns and total_asset_value:
        single_tenant_share = (
            assets.loc[assets["single_tenant_or_master_lease"], "appraised_value_mn_krw_20251231"].sum()
            / total_asset_value
            * 100
        )

    add_score_rule(
        rows,
        "Income / Lease Stability Risk",
        "Portfolio occupancy below 95%",
        pd.notna(occupancy) and occupancy < 95,
        35,
        weights["Income / Lease Stability Risk"],
        format_pct_from_100(occupancy),
        "< 95.0%",
        "Lower occupancy directly weakens recurring rental income and signals reletting risk.",
    )
    add_score_rule(
        rows,
        "Income / Lease Stability Risk",
        "WALE below 2.0 years",
        pd.notna(wale) and wale < 2.0,
        30,
        weights["Income / Lease Stability Risk"],
        format_years(wale),
        "< 2.0 years",
        "Short WALE increases near-term lease rollover risk and weakens income visibility.",
    )
    add_score_rule(
        rows,
        "Income / Lease Stability Risk",
        "WALE between 2.0 and 3.0 years",
        pd.notna(wale) and 2.0 <= wale < 3.0,
        15,
        weights["Income / Lease Stability Risk"],
        format_years(wale),
        "2.0–3.0 years",
        "Medium WALE is not critical but still requires tenant renewal monitoring.",
    )
    add_score_rule(
        rows,
        "Income / Lease Stability Risk",
        "Master-lease / single-tenant exposure above 65% of appraised value",
        pd.notna(single_tenant_share) and single_tenant_share > 65,
        20,
        weights["Income / Lease Stability Risk"],
        format_pct_from_100(single_tenant_share),
        "> 65.0%",
        "Concentration can be stable when tenants are strong, but it raises counterparty and renegotiation dependency.",
    )

    leverage = latest_kpi.get("leverage_pct", pd.NA)
    icr = latest_kpi.get("interest_coverage_x", pd.NA)
    avg_rate = latest_kpi.get("avg_borrowing_rate_pct", pd.NA)
    wam = latest_kpi.get("debt_weighted_average_maturity_yrs", pd.NA)
    fixed_pct = latest_kpi.get("fixed_rate_debt_pct", pd.NA)
    total_debt = debt_schedule["principal_mn_krw"].sum()
    near_term_debt = debt_schedule[debt_schedule["days_to_maturity"].between(0, 365, inclusive="both")]["principal_mn_krw"].sum()
    near_term_share = near_term_debt / total_debt * 100 if total_debt else pd.NA

    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "Leverage at or above 55%",
        pd.notna(leverage) and leverage >= 55,
        30,
        weights["Refinancing / Debt Service Risk"],
        format_pct_from_100(leverage),
        ">= 55.0%",
        "Higher leverage reduces the equity cushion and increases sensitivity to cap-rate expansion and refinancing haircuts.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "Leverage between 50% and 55%",
        pd.notna(leverage) and 50 <= leverage < 55,
        15,
        weights["Refinancing / Debt Service Risk"],
        format_pct_from_100(leverage),
        "50.0%–55.0%",
        "Moderate leverage pressure; refinancing terms should be monitored.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "Interest coverage below 2.0x",
        pd.notna(icr) and icr < 2.0,
        30,
        weights["Refinancing / Debt Service Risk"],
        format_ratio(icr),
        "< 2.0x",
        "Weak interest coverage indicates limited debt-service headroom under rate shocks.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "Interest coverage between 2.0x and 2.5x",
        pd.notna(icr) and 2.0 <= icr < 2.5,
        20,
        weights["Refinancing / Debt Service Risk"],
        format_ratio(icr),
        "2.0x–2.5x",
        "Coverage is acceptable but exposed to refinancing spread widening or FFO downside.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "Debt weighted average maturity below 1.5 years",
        pd.notna(wam) and wam < 1.5,
        25,
        weights["Refinancing / Debt Service Risk"],
        format_years(wam),
        "< 1.5 years",
        "Short WAM creates near-term refinancing wall risk.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "Debt weighted average maturity between 1.5 and 2.0 years",
        pd.notna(wam) and 1.5 <= wam < 2.0,
        15,
        weights["Refinancing / Debt Service Risk"],
        format_years(wam),
        "1.5–2.0 years",
        "Medium WAM requires maturity ladder management.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "Fixed-rate debt ratio below 50%",
        pd.notna(fixed_pct) and fixed_pct < 50,
        15,
        weights["Refinancing / Debt Service Risk"],
        format_pct_from_100(fixed_pct),
        "< 50.0%",
        "Low fixed-rate protection increases exposure to rate volatility.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "Average borrowing rate above 4.5%",
        pd.notna(avg_rate) and avg_rate > 4.5,
        10,
        weights["Refinancing / Debt Service Risk"],
        format_pct_from_100(avg_rate),
        "> 4.5%",
        "Elevated funding cost can compress FFO and distribution capacity.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "More than 25% of disclosed debt matures within one year",
        pd.notna(near_term_share) and near_term_share > 25,
        20,
        weights["Refinancing / Debt Service Risk"],
        format_pct_from_100(near_term_share),
        "> 25.0%",
        "A concentrated one-year maturity wall raises execution risk under volatile credit-market conditions.",
    )

    uplift = assets["value_uplift_pct"].mean()
    cap_rate_mean = assets["cap_rate_pct_20251231"].mean()
    office_share = pd.NA
    if total_asset_value:
        office_share = (
            assets.loc[assets["asset_type"].str.contains("office", case=False, na=False), "appraised_value_mn_krw_20251231"].sum()
            / total_asset_value
            * 100
        )

    add_score_rule(
        rows,
        "Valuation / NAV Sensitivity Risk",
        "Average asset cap rate below 4%",
        pd.notna(cap_rate_mean) and cap_rate_mean < 4.0,
        20,
        weights["Valuation / NAV Sensitivity Risk"],
        format_pct_from_100(cap_rate_mean),
        "< 4.0%",
        "Low cap rates imply higher value duration and greater NAV sensitivity to yield expansion.",
    )
    add_score_rule(
        rows,
        "Valuation / NAV Sensitivity Risk",
        "Average valuation uplift above 20% vs acquisition price",
        pd.notna(uplift) and uplift > 20,
        15,
        weights["Valuation / NAV Sensitivity Risk"],
        format_pct_from_100(uplift),
        "> 20.0%",
        "Large appraisal uplift should be supported by rent growth, tenant credit, or lower risk premium.",
    )
    add_score_rule(
        rows,
        "Valuation / NAV Sensitivity Risk",
        "Office-concentrated portfolio above 65% of appraised value",
        pd.notna(office_share) and office_share > 65,
        10,
        weights["Valuation / NAV Sensitivity Risk"],
        format_pct_from_100(office_share),
        "> 65.0%",
        "Office concentration increases exposure to submarket vacancy, leasing spreads, and cap-rate cycle risk.",
    )

    derived_rent_count = assets["estimated_annual_rent_mn_krw"].astype(str).str.contains("derived", case=False, na=False).sum()
    missing_nla_count = assets["nla_or_leasable_area_sqm"].isna().sum()
    add_score_rule(
        rows,
        "Disclosure / Data Basis Risk",
        "Asset-level annual rent figures are derived rather than directly disclosed",
        derived_rent_count > 0,
        min(derived_rent_count * 10, 40),
        weights["Disclosure / Data Basis Risk"],
        f"{derived_rent_count} asset(s)",
        "> 0",
        "Derived rent figures are useful proxies but need source-document reconciliation before formal valuation.",
    )
    add_score_rule(
        rows,
        "Disclosure / Data Basis Risk",
        "Assets lack explicit NLA / leasable area",
        missing_nla_count > 0,
        min(missing_nla_count * 5, 25),
        weights["Disclosure / Data Basis Risk"],
        f"{missing_nla_count} asset(s)",
        "> 0",
        "Missing NLA weakens rent-per-area, productivity, and comparability analysis.",
    )
    add_score_rule(
        rows,
        "Disclosure / Data Basis Risk",
        "Parent investment-report KPIs and consolidated K-IFRS figures are separate bases",
        True,
        15,
        weights["Disclosure / Data Basis Risk"],
        "Always applicable",
        "Basis difference exists",
        "Cross-basis ratios are screening signals only and require reconciliation before formal use.",
    )

    out = pd.DataFrame(rows)
    out["category_score"] = out.groupby("risk_category")["score_delta"].transform("sum").clip(upper=100)
    out["category_weighted_score"] = out.groupby("risk_category")["weighted_score_delta"].transform("sum")
    out["trigger_status"] = out["triggered"].map({True: "Triggered", False: "Not triggered"})
    return out


def build_asset_score_decomposition(asset_row: pd.Series) -> pd.DataFrame:
    """Explain one asset-level risk score."""
    rows = []

    def add(driver, triggered, score_delta, current_value="", threshold="", interpretation=""):
        rows.append({
            "driver": driver,
            "triggered": bool(triggered),
            "score_delta": float(score_delta) if triggered else 0.0,
            "current_value": current_value,
            "threshold": threshold,
            "interpretation": interpretation,
        })

    add(
        "Single tenant / master lease concentration",
        str(asset_row.get("tenant_concentration_pct", "")).lower().find("100") >= 0 or str(asset_row.get("tenant_concentration_pct", "")).lower().find("master") >= 0,
        20,
        str(asset_row.get("tenant_concentration_pct", "N/A")),
        "100% or master lease wording",
        "Stable for strong tenants but still creates counterparty concentration.",
    )
    add(
        "Mixed / retail / gas-station asset type",
        bool(pd.notna(asset_row.get("asset_type")) and re.search("mixed|retail|gas", str(asset_row.get("asset_type")), flags=re.IGNORECASE)),
        15,
        str(asset_row.get("asset_type", "N/A")),
        "Contains mixed, retail, or gas",
        "Non-office assets often require more bespoke lease and alternative-use diligence.",
    )
    add(
        "WALE below 3 years",
        pd.notna(asset_row.get("wale_yrs")) and asset_row["wale_yrs"] < 3,
        25,
        format_years(asset_row.get("wale_yrs")),
        "< 3.0 years",
        "Shorter remaining lease tenor raises rollover and rental reversion risk.",
    )
    add(
        "Cap rate below 4%",
        pd.notna(asset_row.get("cap_rate_pct_20251231")) and asset_row["cap_rate_pct_20251231"] < 4.0,
        15,
        format_pct_from_100(asset_row.get("cap_rate_pct_20251231")),
        "< 4.0%",
        "Low cap rate implies higher duration and valuation sensitivity.",
    )
    add(
        "Valuation uplift above 25%",
        pd.notna(asset_row.get("value_uplift_pct")) and asset_row["value_uplift_pct"] > 25,
        10,
        format_pct_from_100(asset_row.get("value_uplift_pct")),
        "> 25.0%",
        "Large appraisal uplift should be traced to rent, cap-rate, or asset-quality evidence.",
    )
    add(
        "Annual rent figure is derived",
        str(asset_row.get("estimated_annual_rent_mn_krw", "")).lower().find("derived") >= 0,
        15,
        str(asset_row.get("estimated_annual_rent_mn_krw", "N/A")),
        "Contains derived note",
        "Derived rent is a proxy and should be tied back to original disclosure or appraisal support.",
    )

    out = pd.DataFrame(rows)
    out["trigger_status"] = out["triggered"].map({True: "Triggered", False: "Not triggered"})
    out["asset_risk_score_recomputed"] = min(float(out["score_delta"].sum()), 100.0)
    return out


def build_asset_risk_table(assets: pd.DataFrame) -> pd.DataFrame:
    df = assets.copy()
    df["asset_risk_score"] = 0

    # High tenant concentration is stable when credit is strong but concentration still matters for DD.
    df.loc[df["tenant_concentration_pct"].astype(str).str.contains("100|master", case=False, na=False), "asset_risk_score"] += 20
    df.loc[df["asset_type"].str.contains("mixed|retail|gas", case=False, na=False), "asset_risk_score"] += 15
    df.loc[df["wale_yrs"].fillna(99) < 3, "asset_risk_score"] += 25
    df.loc[df["cap_rate_pct_20251231"].fillna(0) < 4.0, "asset_risk_score"] += 15
    df.loc[df["value_uplift_pct"].fillna(0) > 25, "asset_risk_score"] += 10
    df.loc[df["estimated_annual_rent_mn_krw"].astype(str).str.contains("derived", case=False, na=False), "asset_risk_score"] += 15
    df["asset_risk_score"] = df["asset_risk_score"].clip(upper=100)
    df["asset_risk_level"] = pd.cut(
        df["asset_risk_score"],
        bins=[-1, 39, 69, 100],
        labels=["Low", "Medium", "High"],
    ).astype(str)
    return df


def build_debt_stress_table(latest_kpi: pd.Series, debt_schedule: pd.DataFrame) -> pd.DataFrame:
    principal = debt_schedule["principal_mn_krw"].sum()
    floating = debt_schedule.loc[debt_schedule["rate_type"] == "변동", "principal_mn_krw"].sum()
    fixed = debt_schedule.loc[debt_schedule["rate_type"] == "고정", "principal_mn_krw"].sum()
    base_rate = latest_kpi.get("avg_borrowing_rate_pct", pd.NA) / 100
    ffo = latest_kpi.get("ffo_mn_krw", pd.NA)
    icr = latest_kpi.get("interest_coverage_x", pd.NA)
    base_interest = principal * base_rate if pd.notna(base_rate) else pd.NA

    rows = []
    for name, add_bp, affected in [
        ("Base", 0.00, "none"),
        ("Floating debt +100bp", 0.01, "floating"),
        ("All refinancing +100bp", 0.01, "all"),
        ("All refinancing +200bp", 0.02, "all"),
    ]:
        if affected == "none":
            incremental_interest = 0
        elif affected == "floating":
            incremental_interest = floating * add_bp
        else:
            incremental_interest = principal * add_bp

        stressed_interest = base_interest + incremental_interest if pd.notna(base_interest) else pd.NA
        ffo_after_incremental_interest = ffo - incremental_interest if pd.notna(ffo) else pd.NA
        rows.append({
            "scenario": name,
            "total_principal_mn_krw": principal,
            "fixed_principal_mn_krw": fixed,
            "floating_principal_mn_krw": floating,
            "base_avg_rate_pct": latest_kpi.get("avg_borrowing_rate_pct", pd.NA),
            "incremental_interest_mn_krw": incremental_interest,
            "stressed_interest_mn_krw": stressed_interest,
            "reported_interest_coverage_x": icr,
            "ffo_mn_krw": ffo,
            "ffo_after_incremental_interest_mn_krw": ffo_after_incremental_interest,
            "ffo_decline_pct": incremental_interest / ffo * 100 if pd.notna(ffo) and ffo else pd.NA,
        })

    return pd.DataFrame(rows)



def build_custom_stress_table(latest_kpi: pd.Series, debt_schedule: pd.DataFrame, rate_shock_bp: int, refinancing_share_pct: float, ffo_haircut_pct: float) -> pd.DataFrame:
    """User-controlled debt stress. Values are in mn KRW and percentage-point units."""
    principal = debt_schedule["principal_mn_krw"].sum()
    floating = debt_schedule.loc[debt_schedule["rate_type"] == "변동", "principal_mn_krw"].sum()
    ffo = latest_kpi.get("ffo_mn_krw", pd.NA)
    current_icr = latest_kpi.get("interest_coverage_x", pd.NA)
    avg_rate = latest_kpi.get("avg_borrowing_rate_pct", pd.NA) / 100
    base_interest = principal * avg_rate if pd.notna(avg_rate) else pd.NA

    rate_shock = rate_shock_bp / 10_000
    refinancing_principal = principal * refinancing_share_pct / 100
    stressed_principal = floating + refinancing_principal
    incremental_interest = stressed_principal * rate_shock
    ffo_after_operating_haircut = ffo * (1 - ffo_haircut_pct / 100) if pd.notna(ffo) else pd.NA
    stressed_ffo = ffo_after_operating_haircut - incremental_interest if pd.notna(ffo_after_operating_haircut) else pd.NA
    stressed_interest = base_interest + incremental_interest if pd.notna(base_interest) else pd.NA
    estimated_stressed_icr = stressed_ffo / stressed_interest if pd.notna(stressed_ffo) and pd.notna(stressed_interest) and stressed_interest else pd.NA

    rows = [
        {
            "scenario": "Current disclosed baseline",
            "rate_shock_bp": 0,
            "refinancing_share_pct": 0,
            "ffo_haircut_pct": 0,
            "affected_principal_mn_krw": 0,
            "incremental_interest_mn_krw": 0,
            "ffo_after_haircut_and_interest_mn_krw": ffo,
            "estimated_interest_coverage_x": current_icr,
        },
        {
            "scenario": "User-defined stress",
            "rate_shock_bp": rate_shock_bp,
            "refinancing_share_pct": refinancing_share_pct,
            "ffo_haircut_pct": ffo_haircut_pct,
            "affected_principal_mn_krw": stressed_principal,
            "incremental_interest_mn_krw": incremental_interest,
            "ffo_after_haircut_and_interest_mn_krw": stressed_ffo,
            "estimated_interest_coverage_x": estimated_stressed_icr,
        },
    ]
    return pd.DataFrame(rows)



def build_interactive_scenario_outputs(
    latest_kpi: pd.Series,
    debt_schedule: pd.DataFrame,
    assets: pd.DataFrame,
    rate_shock_bp: int,
    refinancing_share_pct: float,
    ffo_haircut_pct: float,
    cap_rate_shock_bp: int,
    scenario_metadata: dict | None = None,
) -> dict:
    """Build beginner-friendly scenario outputs for FFO, ICR, dividend cushion, NAV and cap-rate sensitivity."""
    principal = debt_schedule["principal_mn_krw"].sum()
    floating = debt_schedule.loc[debt_schedule["rate_type"] == "변동", "principal_mn_krw"].sum()
    avg_rate_pct = latest_kpi.get("avg_borrowing_rate_pct", pd.NA)
    reported_icr = latest_kpi.get("interest_coverage_x", pd.NA)
    base_ffo = latest_kpi.get("ffo_mn_krw", pd.NA)
    base_nav = latest_kpi.get("nav_mn_krw", pd.NA)
    common_dividend = latest_kpi.get("common_dividend_total_mn_krw", pd.NA)

    # Use disclosed interest coverage when possible because it ties directly to reported KPI basis.
    if pd.notna(base_ffo) and pd.notna(reported_icr) and reported_icr:
        base_interest = base_ffo / reported_icr
        interest_basis = "reported ICR"
    elif pd.notna(avg_rate_pct):
        base_interest = principal * avg_rate_pct / 100
        interest_basis = "average borrowing rate"
    else:
        base_interest = pd.NA
        interest_basis = "not available"

    affected_refi_principal = principal * refinancing_share_pct / 100
    affected_principal = floating + affected_refi_principal
    incremental_interest = affected_principal * rate_shock_bp / 10_000

    operating_ffo_loss = base_ffo * ffo_haircut_pct / 100 if pd.notna(base_ffo) else pd.NA
    stressed_ffo = base_ffo - operating_ffo_loss - incremental_interest if pd.notna(base_ffo) and pd.notna(operating_ffo_loss) else pd.NA
    stressed_interest = base_interest + incremental_interest if pd.notna(base_interest) else pd.NA
    stressed_icr = stressed_ffo / stressed_interest if pd.notna(stressed_ffo) and pd.notna(stressed_interest) and stressed_interest else pd.NA

    base_payout = common_dividend / base_ffo * 100 if pd.notna(common_dividend) and pd.notna(base_ffo) and base_ffo else pd.NA
    stressed_payout = common_dividend / stressed_ffo * 100 if pd.notna(common_dividend) and pd.notna(stressed_ffo) and stressed_ffo > 0 else pd.NA
    dividend_cushion = stressed_ffo - common_dividend if pd.notna(common_dividend) and pd.notna(stressed_ffo) else pd.NA

    asset_sensitivity = assets[[
        "asset_name",
        "asset_type",
        "appraised_value_mn_krw_20251231",
        "cap_rate_pct_20251231",
        "source_confidence",
    ]].copy()
    asset_sensitivity["current_noi_proxy_mn_krw"] = (
        asset_sensitivity["appraised_value_mn_krw_20251231"]
        * asset_sensitivity["cap_rate_pct_20251231"]
        / 100
    )
    asset_sensitivity["stressed_cap_rate_pct"] = asset_sensitivity["cap_rate_pct_20251231"] + cap_rate_shock_bp / 100
    asset_sensitivity["value_under_cap_rate_shock_mn_krw"] = (
        asset_sensitivity["current_noi_proxy_mn_krw"]
        / (asset_sensitivity["stressed_cap_rate_pct"] / 100)
    )
    asset_sensitivity["value_change_mn_krw"] = (
        asset_sensitivity["value_under_cap_rate_shock_mn_krw"]
        - asset_sensitivity["appraised_value_mn_krw_20251231"]
    )
    asset_sensitivity["value_change_pct"] = (
        asset_sensitivity["value_change_mn_krw"]
        / asset_sensitivity["appraised_value_mn_krw_20251231"]
        * 100
    )

    total_appraised_value = asset_sensitivity["appraised_value_mn_krw_20251231"].sum()
    total_value_change = asset_sensitivity["value_change_mn_krw"].sum()
    stressed_asset_value = total_appraised_value + total_value_change
    stressed_nav = base_nav + total_value_change if pd.notna(base_nav) else pd.NA
    nav_change_pct = total_value_change / base_nav * 100 if pd.notna(base_nav) and base_nav else pd.NA
    base_ltv_proxy = principal / total_appraised_value * 100 if total_appraised_value else pd.NA
    stressed_ltv_proxy = principal / stressed_asset_value * 100 if stressed_asset_value else pd.NA

    ffo_bridge = pd.DataFrame([
        {"step": "현재 현금흐름", "mn_krw": base_ffo, "display_order": 1},
        {"step": "영업 하락", "mn_krw": -operating_ffo_loss, "display_order": 2},
        {"step": "추가 이자비용", "mn_krw": -incremental_interest, "display_order": 3},
        {"step": "시나리오 후 현금흐름", "mn_krw": stressed_ffo, "display_order": 4},
    ])

    kpi_summary = pd.DataFrame([
        {"metric": "FFO", "baseline": base_ffo, "stressed": stressed_ffo, "unit": "mn KRW"},
        {"metric": "Interest coverage", "baseline": reported_icr, "stressed": stressed_icr, "unit": "x"},
        {"metric": "Dividend payout", "baseline": base_payout, "stressed": stressed_payout, "unit": "%"},
        {"metric": "NAV", "baseline": base_nav, "stressed": stressed_nav, "unit": "mn KRW"},
        {"metric": "LTV proxy", "baseline": base_ltv_proxy, "stressed": stressed_ltv_proxy, "unit": "%"},
    ])
    scenario_label = (scenario_metadata or {}).get("selected_scenario", "사용자 정의 시나리오")
    valuation_note = f"좌측 사이드바 '{scenario_label}'의 Cap rate +{cap_rate_shock_bp}bp 가정에서 계산"

    return {
        "scenario_label": scenario_label,
        "valuation_scenario_note": valuation_note,
        "rate_shock_bp": rate_shock_bp,
        "refinancing_share_pct": refinancing_share_pct,
        "ffo_haircut_pct": ffo_haircut_pct,
        "cap_rate_shock_bp": cap_rate_shock_bp,
        "base_ffo": base_ffo,
        "stressed_ffo": stressed_ffo,
        "ffo_decline_pct": (stressed_ffo / base_ffo - 1) * 100 if pd.notna(stressed_ffo) and pd.notna(base_ffo) and base_ffo else pd.NA,
        "operating_ffo_loss": operating_ffo_loss,
        "incremental_interest": incremental_interest,
        "base_interest": base_interest,
        "stressed_interest": stressed_interest,
        "interest_basis": interest_basis,
        "reported_icr": reported_icr,
        "stressed_icr": stressed_icr,
        "base_payout": base_payout,
        "stressed_payout": stressed_payout,
        "dividend_cushion": dividend_cushion,
        "base_nav": base_nav,
        "stressed_nav": stressed_nav,
        "total_value_change": total_value_change,
        "nav_change_pct": nav_change_pct,
        "base_ltv_proxy": base_ltv_proxy,
        "stressed_ltv_proxy": stressed_ltv_proxy,
        "asset_sensitivity": asset_sensitivity,
        "ffo_bridge": ffo_bridge,
        "kpi_summary": kpi_summary,
    }


def scenario_verdict(scenario: dict) -> tuple[str, str, str]:
    """Return an easy-to-read traffic-light verdict for beginner users."""
    stressed_ffo = scenario.get("stressed_ffo", pd.NA)
    stressed_icr = scenario.get("stressed_icr", pd.NA)
    stressed_payout = scenario.get("stressed_payout", pd.NA)
    nav_change_pct = scenario.get("nav_change_pct", pd.NA)

    red_flags = []
    yellow_flags = []

    if pd.notna(stressed_ffo) and stressed_ffo <= 0:
        red_flags.append("시나리오 후 현금흐름이 음수로 전환")
    if pd.notna(stressed_icr):
        if stressed_icr < 1.5:
            red_flags.append("이자 감당력이 1.5배 미만으로 하락")
        elif stressed_icr < 2.0:
            yellow_flags.append("이자 감당력이 2.0배 미만으로 하락")
    if pd.notna(stressed_payout):
        if stressed_payout > 100:
            red_flags.append("배당금이 시나리오 후 현금흐름을 초과")
        elif stressed_payout > 85:
            yellow_flags.append("배당 부담률이 높아짐")
    if pd.notna(nav_change_pct):
        if nav_change_pct <= -15:
            red_flags.append("순자산가치 하락폭이 15% 초과")
        elif nav_change_pct <= -8:
            yellow_flags.append("순자산가치 하락폭이 8% 초과")

    if red_flags:
        return "🔴 압박이 큼", "High", "; ".join(red_flags)
    if yellow_flags:
        return "🟡 주의 필요", "Medium", "; ".join(yellow_flags)
    return "🟢 현재 시나리오에서는 비교적 안정", "Low", "주요 경고 기준을 넘지 않았습니다."


def build_asset_concentration_table(assets: pd.DataFrame) -> pd.DataFrame:
    df = assets.copy()
    total_value = df["appraised_value_mn_krw_20251231"].sum()
    df["portfolio_value_share_pct"] = df["appraised_value_mn_krw_20251231"] / total_value * 100
    df["hhi_component"] = (df["portfolio_value_share_pct"] / 100) ** 2
    df["rank_by_value"] = df["appraised_value_mn_krw_20251231"].rank(ascending=False, method="dense").astype(int)
    return df.sort_values("appraised_value_mn_krw_20251231", ascending=False)


def build_tenant_exposure_table(assets: pd.DataFrame) -> pd.DataFrame:
    df = assets.copy()
    total_value = df["appraised_value_mn_krw_20251231"].sum()
    tenant = (
        df.groupby(["major_tenant", "tenant_credit"], dropna=False)["appraised_value_mn_krw_20251231"]
        .sum()
        .reset_index()
        .sort_values("appraised_value_mn_krw_20251231", ascending=False)
    )
    tenant["portfolio_value_share_pct"] = tenant["appraised_value_mn_krw_20251231"] / total_value * 100
    return tenant


def build_watchlist(asset_risk: pd.DataFrame, debt_schedule: pd.DataFrame, latest_kpi: pd.Series) -> pd.DataFrame:
    rows = []
    for _, row in asset_risk.iterrows():
        reasons = []
        if row.get("asset_risk_score", 0) >= 40:
            reasons.append("asset score >= 40")
        if pd.notna(row.get("wale_yrs")) and row["wale_yrs"] < 2.0:
            reasons.append("short WALE")
        if pd.notna(row.get("cap_rate_pct_20251231")) and row["cap_rate_pct_20251231"] < 4.0:
            reasons.append("low cap rate / valuation sensitivity")
        if str(row.get("tenant_concentration_pct", "")).lower().find("100") >= 0:
            reasons.append("single tenant / master lease concentration")
        if str(row.get("estimated_annual_rent_mn_krw", "")).lower().find("derived") >= 0:
            reasons.append("rent figure derived from cap-rate label")

        if reasons:
            rows.append({
                "watch_item": row["asset_name"],
                "category": "Asset / lease",
                "priority_score": min(row.get("asset_risk_score", 0) + len(reasons) * 5, 100),
                "why_it_matters": "; ".join(reasons),
                "recommended_next_step": "Check original lease schedule, tenant credit, appraisal assumptions and renewal option economics.",
                "source_confidence": row.get("source_confidence", "unknown"),
            })

    near_term = debt_schedule[debt_schedule["days_to_maturity"].between(0, 730, inclusive="both")].copy()
    if not near_term.empty:
        by_year = near_term.groupby("maturity_year")["principal_mn_krw"].sum().reset_index()
        for _, row in by_year.iterrows():
            rows.append({
                "watch_item": f"Debt maturities in {int(row['maturity_year'])}",
                "category": "Debt / refinancing",
                "priority_score": min(row["principal_mn_krw"] / debt_schedule["principal_mn_krw"].sum() * 100 + 35, 100),
                "why_it_matters": f"{row['principal_mn_krw']:,.0f} mn KRW matures within the near-term maturity window.",
                "recommended_next_step": "Map facility-level maturity to collateral, funding source, spread step-up and refinancing base-rate scenario.",
                "source_confidence": "high_disclosed_table",
            })

    if pd.notna(latest_kpi.get("interest_coverage_x")) and latest_kpi["interest_coverage_x"] < 2.5:
        rows.append({
            "watch_item": "Interest coverage",
            "category": "Debt service",
            "priority_score": 75 if latest_kpi["interest_coverage_x"] < 2.0 else 60,
            "why_it_matters": f"Reported interest coverage is {latest_kpi['interest_coverage_x']:.2f}x.",
            "recommended_next_step": "Run FFO downside and refinancing spread sensitivity; compare with rating-agency tolerance bands.",
            "source_confidence": latest_kpi.get("source_confidence", "high_disclosed_kpi"),
        })

    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=["watch_item", "category", "priority_score", "why_it_matters", "recommended_next_step", "source_confidence"])
    return out.sort_values("priority_score", ascending=False)


def build_due_diligence_questions(risk_scores: dict, latest_kpi: pd.Series) -> pd.DataFrame:
    rows = []
    question_bank = {
        "Deals / FDD": [
            "Is disclosed FFO normalized for one-off acquisition, refinancing, disposition, or tenant transition items?",
            "Which assets drive most of the portfolio value and rent, and are those cash flows backed by enforceable long-term leases?",
            "Are related-party/master leases economically at market, or do they embed sponsor support?",
        ],
        "Valuation": [
            "Are asset cap rates consistent with current market evidence, not only acquisition-date or appraisal-date assumptions?",
            "How much NAV sensitivity results from +50bp/+100bp cap-rate expansion by asset type?",
            "Are appraisal uplifts supported by actual rent escalation, lower risk premium, or merely market cap-rate compression?",
        ],
        "Restructuring / Credit": [
            "What portion of debt must be refinanced before lease rollover or tenant renewal is resolved?",
            "Does stressed FFO still cover interest after refinancing spread widening?",
            "Are there collateral, DSCR, LTV, cash sweep, or rating triggers that could constrain distributions?",
        ],
        "Assurance": [
            "Are K-IFRS consolidated figures reconciled to statutory investment-report KPIs before being used in ratios?",
            "Are fair-value assumptions, valuation uncertainty, and key external inputs disclosed sufficiently?",
            "Do lease rollover, refinancing, or tenant-credit changes indicate impairment or fair-value review points?",
        ],
    }
    for perspective, questions in question_bank.items():
        for question in questions:
            rows.append({"perspective": perspective, "review_question": question})
    return pd.DataFrame(rows)
