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


DETAILED_SAMPLE_STOCK_CODE = "395400"
DETAILED_SAMPLE_COMPANY = "SK리츠"


def _has_detailed_company_sample(company_profile: dict) -> bool:
    return (
        str(company_profile.get("stock_code", "")).zfill(6) == DETAILED_SAMPLE_STOCK_CODE
        or str(company_profile.get("company_name", "")).strip() == DETAILED_SAMPLE_COMPANY
    )


def _empty_like(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[0:0].copy()


def _selected_company_detail_data(bundle: dict, company_profile: dict) -> dict:
    has_detail = _has_detailed_company_sample(company_profile)
    if has_detail:
        return {
            "assets": bundle["assets"],
            "debt_schedule": bundle["debt_schedule"],
            "debt_summary": bundle["debt_summary"],
            "detail_available": True,
            "detail_basis": "회사별 상세 자산·차입금 CSV 기준",
        }
    return {
        "assets": _empty_like(bundle["assets"]),
        "debt_schedule": _empty_like(bundle["debt_schedule"]),
        "debt_summary": _empty_like(bundle["debt_summary"]),
        "detail_available": False,
        "detail_basis": "회사별 상세 자산·보유세 데이터 부족 / Peer 및 재무 Snapshot 중심",
    }


def _apply_selected_company_financials(
    latest_kpi: pd.Series,
    latest_fin: pd.Series,
    selected_latest_fin: pd.Series,
    company_profile: dict,
    keep_detail_metrics: bool,
) -> tuple[pd.Series, pd.Series]:
    kpi = latest_kpi.copy()
    fin = latest_fin.copy()
    if not keep_detail_metrics:
        stale_detail_fields = [
            "occupancy_pct",
            "wale_yrs",
            "avg_borrowing_rate_pct",
            "fixed_rate_debt_pct",
            "debt_weighted_average_maturity_yrs",
            "dps_krw",
        ]
        for field in stale_detail_fields:
            if field in kpi.index:
                kpi[field] = pd.NA

    kpi["reit_name"] = company_profile.get("company_name", "")
    kpi["ticker"] = company_profile.get("stock_code", "")
    kpi["source_confidence"] = selected_latest_fin.get("source_type", "sample_snapshot")
    kpi["source_document"] = "선택 회사 Peer Snapshot / 최근 5년 재무 흐름"

    fin["reit_name"] = company_profile.get("company_name", "")
    fin["ticker"] = company_profile.get("stock_code", "")
    fin["source_confidence"] = selected_latest_fin.get("source_type", "sample_snapshot")
    fin["source_document"] = "선택 회사 Peer Snapshot / 최근 5년 재무 흐름"

    kpi_mapping = {
        "ffo_proxy": "ffo_mn_krw",
        "nav": "nav_mn_krw",
        "dividends": "common_dividend_total_mn_krw",
        "operating_revenue": "revenue_mn_krw",
        "net_income": "net_income_mn_krw",
    }
    fin_mapping = {
        "total_assets": "total_assets_mn_krw",
        "investment_property": "investment_property_mn_krw",
        "borrowings_total": "interest_bearing_debt_mn_krw",
        "operating_revenue": "revenue_mn_krw",
        "operating_income": "operating_income_mn_krw",
        "net_income": "net_income_mn_krw",
        "nav": "total_equity_mn_krw",
    }
    for source, target in kpi_mapping.items():
        if pd.notna(selected_latest_fin.get(source, pd.NA)):
            kpi[target] = selected_latest_fin.get(source)
    for source, target in fin_mapping.items():
        if pd.notna(selected_latest_fin.get(source, pd.NA)):
            fin[target] = selected_latest_fin.get(source)

    total_assets = pd.to_numeric(pd.Series([selected_latest_fin.get("total_assets", pd.NA)]), errors="coerce").iloc[0]
    borrowings = pd.to_numeric(pd.Series([selected_latest_fin.get("borrowings_total", pd.NA)]), errors="coerce").iloc[0]
    interest_expense = pd.to_numeric(pd.Series([selected_latest_fin.get("interest_expense", pd.NA)]), errors="coerce").iloc[0]
    ffo = pd.to_numeric(pd.Series([selected_latest_fin.get("ffo_proxy", pd.NA)]), errors="coerce").iloc[0]
    if pd.notna(total_assets) and total_assets:
        kpi["leverage_pct"] = borrowings / total_assets * 100 if pd.notna(borrowings) else pd.NA
    if pd.notna(ffo) and pd.notna(interest_expense) and interest_expense:
        kpi["interest_coverage_x"] = ffo / interest_expense
    elif not keep_detail_metrics:
        kpi["interest_coverage_x"] = pd.NA
    return kpi, fin


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

sidebar_state = render_data_sidebar(kpis, financials, selected_user_mode, peer_metrics, peer_snapshot)
selected_period = sidebar_state["selected_period"]
latest_kpi = sidebar_state["latest_kpi"]
latest_fin = sidebar_state["latest_fin"]
target_company = sidebar_state["target_company"]
peer_group = sidebar_state["peer_group"]
selected_company_profile = sidebar_state["selected_company_profile"]
recent_5y_financials = sidebar_state["recent_5y_financials"]
recent_5y_status = sidebar_state["recent_5y_status"]
analysis_run_id = sidebar_state["analysis_run_id"]
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

selected_detail = _selected_company_detail_data(bundle, selected_company_profile)
selected_assets = selected_detail["assets"]
selected_debt_schedule = selected_detail["debt_schedule"]
selected_debt_summary = selected_detail["debt_summary"]
detail_data_available = selected_detail["detail_available"]
detail_data_basis = selected_detail["detail_basis"]

if recent_5y_financials is not None and not recent_5y_financials.empty:
    selected_latest_fin = recent_5y_financials.sort_values("year").iloc[-1]
    latest_kpi, latest_fin = _apply_selected_company_financials(
        latest_kpi,
        latest_fin,
        selected_latest_fin,
        selected_company_profile,
        detail_data_available,
    )

asset_risk = build_asset_risk_table(selected_assets)
concentration_table = build_asset_concentration_table(asset_risk)
tenant_exposure = build_tenant_exposure_table(asset_risk)
st.session_state["selected_company_assets"] = asset_risk
st.session_state["selected_company_tax_data"] = pd.DataFrame()

risk_scores, total_risk, risk_level, risk_flags = calculate_reit_level_risk(latest_kpi, selected_debt_schedule, asset_risk)
risk_decomposition = build_reit_score_decomposition(latest_kpi, selected_debt_schedule, asset_risk)
debt_stress = build_debt_stress_table(latest_kpi, selected_debt_schedule)
watchlist = build_watchlist(asset_risk, selected_debt_schedule, latest_kpi)
dd_questions = build_due_diligence_questions(risk_scores, latest_kpi)
scenario = build_interactive_scenario_outputs(
    latest_kpi,
    selected_debt_schedule,
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
    "detail_data_available": detail_data_available,
    "detail_data_basis": detail_data_basis,
    "analysis_run_id": analysis_run_id,
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
        selected_debt_schedule,
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
    selected_debt_schedule,
    selected_debt_summary,
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
