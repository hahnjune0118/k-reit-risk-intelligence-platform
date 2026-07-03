import pandas as pd
import streamlit as st

from api_ecos import build_ecos_annual_rate_history
from api_manager import get_api_key
from calculations_peer import calculate_peer_metrics, load_peer_snapshot, summarize_peer_position
from calculations_risk import (
    build_asset_concentration_table,
    build_asset_risk_table,
    build_debt_stress_table,
    build_due_diligence_questions,
    build_interactive_scenario_outputs,
    build_reit_score_decomposition,
    build_tenant_exposure_table,
    build_watchlist,
    calculate_reit_level_risk,
    scenario_verdict,
)
from calculations_transmission import (
    build_historical_panel,
    build_macro_transmission_table,
    build_transmission_correlation_table,
    build_transmission_narrative,
)
from data_loader import load_data
from red_flag_engine import build_assurance_red_flags, build_tax_red_flags, load_red_flag_rules
from ui_general import render_general_dashboard
from ui_layout import apply_page_config, render_intro, render_mode_selector
from ui_professional import render_professional_page
from ui_sidebar import render_data_sidebar


apply_page_config()
selected_user_mode = render_mode_selector()
render_intro(selected_user_mode)

today_key = pd.Timestamp.today().normalize().strftime("%Y-%m-%d")
bundle = load_data(today_key)
financials = bundle["financials"]
kpis = bundle["kpis"]
assets = bundle["assets"]
direct_assets = bundle["direct_assets"]
debt_schedule = bundle["debt_schedule"]
debt_summary = bundle["debt_summary"]
source_plan = bundle["source_plan"]
data_dictionary = bundle["data_dictionary"]
peer_snapshot = load_peer_snapshot()
peer_metrics = calculate_peer_metrics(peer_snapshot)
red_flag_rules = load_red_flag_rules()

asset_risk = build_asset_risk_table(assets)
concentration_table = build_asset_concentration_table(asset_risk)
tenant_exposure = build_tenant_exposure_table(asset_risk)

sidebar_state = render_data_sidebar(kpis, financials, selected_user_mode, peer_metrics, peer_snapshot)
selected_period = sidebar_state["selected_period"]
latest_kpi = sidebar_state["latest_kpi"]
latest_fin = sidebar_state["latest_fin"]
target_company = sidebar_state["target_company"]
peer_group = sidebar_state["peer_group"]
selected_company_profile = sidebar_state["selected_company_profile"]
recent_5y_financials = sidebar_state["recent_5y_financials"]
recent_5y_status = sidebar_state["recent_5y_status"]
ecos_conn = sidebar_state.get("ecos_conn") or get_api_key("ECOS")
macro_context = sidebar_state["macro_context"]
dart_history = sidebar_state["dart_history"]
dart_reports = sidebar_state["dart_reports"]
dart_status = sidebar_state["dart_status"]
macro_scenario = sidebar_state["macro_scenario"]
rate_shock_bp = sidebar_state["rate_shock_bp"]
refinancing_share_pct = sidebar_state["refinancing_share_pct"]
ffo_haircut_pct = sidebar_state["ffo_haircut_pct"]
cap_rate_shock_bp = sidebar_state["cap_rate_shock_bp"]
professional_assumptions = sidebar_state["professional_assumptions"]

if recent_5y_financials is not None and not recent_5y_financials.empty:
    selected_latest_fin = recent_5y_financials.sort_values("year").iloc[-1]
    latest_kpi = latest_kpi.copy()
    latest_fin = latest_fin.copy()
    if pd.notna(selected_latest_fin.get("ffo_proxy", pd.NA)):
        latest_kpi["ffo_mn_krw"] = selected_latest_fin.get("ffo_proxy")
    if pd.notna(selected_latest_fin.get("nav", pd.NA)):
        latest_kpi["nav_mn_krw"] = selected_latest_fin.get("nav")
    if pd.notna(selected_latest_fin.get("total_assets", pd.NA)):
        latest_fin["total_assets_mn_krw"] = selected_latest_fin.get("total_assets")
    if pd.notna(selected_latest_fin.get("investment_property", pd.NA)):
        latest_fin["investment_property_mn_krw"] = selected_latest_fin.get("investment_property")
    if pd.notna(selected_latest_fin.get("borrowings_total", pd.NA)):
        latest_fin["interest_bearing_debt_mn_krw"] = selected_latest_fin.get("borrowings_total")
    total_assets_for_ltv = pd.to_numeric(pd.Series([selected_latest_fin.get("total_assets", pd.NA)]), errors="coerce").iloc[0]
    borrowings_for_ltv = pd.to_numeric(pd.Series([selected_latest_fin.get("borrowings_total", pd.NA)]), errors="coerce").iloc[0]
    if pd.notna(total_assets_for_ltv) and total_assets_for_ltv:
        latest_kpi["leverage_pct"] = borrowings_for_ltv / total_assets_for_ltv * 100

risk_scores, total_risk, risk_level, risk_flags = calculate_reit_level_risk(latest_kpi, debt_schedule, asset_risk)
risk_decomposition = build_reit_score_decomposition(latest_kpi, debt_schedule, asset_risk)
debt_stress = build_debt_stress_table(latest_kpi, debt_schedule)
watchlist = build_watchlist(asset_risk, debt_schedule, latest_kpi)
dd_questions = build_due_diligence_questions(risk_scores, latest_kpi)
scenario = build_interactive_scenario_outputs(
    latest_kpi,
    debt_schedule,
    asset_risk,
    rate_shock_bp,
    refinancing_share_pct,
    ffo_haircut_pct,
    cap_rate_shock_bp,
    macro_scenario,
)
verdict_text, verdict_level, verdict_reason = scenario_verdict(scenario)
macro_history, macro_history_status = build_ecos_annual_rate_history(ecos_conn.key, years_back=5)
historical_panel = build_historical_panel(financials, kpis, macro_history, recent_5y_financials)
market_snapshot = {"available": False}
market_gap = pd.DataFrame()
market_gap_narrative = ""
transmission_table = build_macro_transmission_table(historical_panel)
transmission_corr = build_transmission_correlation_table(historical_panel)
transmission_narrative = build_transmission_narrative(transmission_table, transmission_corr)
assurance_red_flags = build_assurance_red_flags(target_company, peer_metrics, red_flag_rules)
tax_red_flags = build_tax_red_flags(target_company, peer_metrics, red_flag_rules)
peer_summary = summarize_peer_position(peer_metrics, target_company)
peer_context = {
    "target_company": target_company,
    "peer_group": peer_group,
    "selected_company_profile": selected_company_profile,
    "recent_5y_financials": recent_5y_financials,
    "recent_5y_status": recent_5y_status,
    "peer_snapshot": peer_snapshot,
    "peer_metrics": peer_metrics,
    "peer_summary": peer_summary,
    "assurance_red_flags": assurance_red_flags,
    "tax_red_flags": tax_red_flags,
    "red_flag_rules": red_flag_rules,
}

if selected_user_mode != "General Info & Scenario":
    render_professional_page(
        selected_user_mode,
        asset_risk,
        debt_schedule,
        latest_kpi,
        scenario,
        professional_assumptions,
        macro_context,
        macro_history_status,
        dart_status,
        financials,
        kpis,
        source_plan,
        data_dictionary,
        peer_context,
    )
    st.stop()

render_general_dashboard(
    verdict_level,
    verdict_text,
    verdict_reason,
    macro_scenario,
    macro_context,
    risk_level,
    total_risk,
    scenario,
    market_snapshot,
    market_gap,
    market_gap_narrative,
    historical_panel,
    transmission_narrative,
    transmission_table,
    transmission_corr,
    selected_user_mode,
    risk_scores,
    watchlist,
    risk_decomposition,
    asset_risk,
    concentration_table,
    tenant_exposure,
    debt_schedule,
    debt_summary,
    cap_rate_shock_bp,
    source_plan,
    data_dictionary,
    financials,
    kpis,
    macro_history_status,
    dart_status,
    dart_reports,
    peer_context,
)
