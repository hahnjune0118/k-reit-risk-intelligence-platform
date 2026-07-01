import pandas as pd
import streamlit as st

from api_ecos import build_ecos_annual_rate_history
from api_krx import market_snapshot_from_krx
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
    build_market_implied_gap_table,
    build_transmission_correlation_table,
    build_transmission_narrative,
    interpret_market_gap,
)
from data_loader import load_data
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

asset_risk = build_asset_risk_table(assets)
concentration_table = build_asset_concentration_table(asset_risk)
tenant_exposure = build_tenant_exposure_table(asset_risk)

sidebar_state = render_data_sidebar(kpis, financials, selected_user_mode)
selected_period = sidebar_state["selected_period"]
latest_kpi = sidebar_state["latest_kpi"]
latest_fin = sidebar_state["latest_fin"]
ecos_conn = sidebar_state["ecos_conn"]
macro_context = sidebar_state["macro_context"]
dart_history = sidebar_state["dart_history"]
dart_reports = sidebar_state["dart_reports"]
dart_status = sidebar_state["dart_status"]
krx_history = sidebar_state["krx_history"]
krx_status = sidebar_state["krx_status"]
macro_scenario = sidebar_state["macro_scenario"]
rate_shock_bp = sidebar_state["rate_shock_bp"]
refinancing_share_pct = sidebar_state["refinancing_share_pct"]
ffo_haircut_pct = sidebar_state["ffo_haircut_pct"]
cap_rate_shock_bp = sidebar_state["cap_rate_shock_bp"]
professional_assumptions = sidebar_state["professional_assumptions"]

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
historical_panel = build_historical_panel(financials, kpis, macro_history, dart_history, krx_history)
market_snapshot = market_snapshot_from_krx(krx_history, latest_kpi.get("nav_mn_krw", pd.NA))
market_gap = build_market_implied_gap_table(market_snapshot, latest_kpi.get("nav_mn_krw", pd.NA), scenario)
market_gap_narrative = interpret_market_gap(market_gap)
transmission_table = build_macro_transmission_table(historical_panel)
transmission_corr = build_transmission_correlation_table(historical_panel)
transmission_narrative = build_transmission_narrative(transmission_table, transmission_corr)

if selected_user_mode != "General Info & Scenario":
    render_professional_page(
        selected_user_mode,
        asset_risk,
        debt_schedule,
        latest_kpi,
        scenario,
        market_snapshot,
        historical_panel,
        professional_assumptions,
        macro_context,
        macro_history_status,
        dart_status,
        krx_status,
        financials,
        kpis,
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
    krx_status,
    dart_reports,
    krx_history,
)
