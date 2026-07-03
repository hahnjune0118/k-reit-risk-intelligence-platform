from io import BytesIO

import pandas as pd
import pytest

from api_ecos import build_macro_context
from api_real_estate_board import parse_official_price_upload
from calculations_assurance import (
    build_assurance_asset_priority,
    build_audit_workflow_checklist,
    build_rmm_assertion_checklist,
)
from calculations_peer import calculate_peer_metrics, classify_metric_risk, load_peer_snapshot, summarize_peer_position
from calculations_risk import (
    build_asset_risk_table,
    build_interactive_scenario_outputs,
    calculate_reit_level_risk,
)
from calculations_scenario import FORECAST_WEIGHTED_SCENARIO_NAME, macro_scenario_parameters
from calculations_tax import (
    build_holding_tax_estimator,
    build_property_tax_cash_flow_scenarios,
    build_proxy_official_price_history,
    build_reit_tax_workflow_checklist,
    build_tax_risk_register,
)
from dart_financials import company_options, get_recent_5y_financials, get_selected_company_profile, load_reit_master
from data_loader import load_data
from red_flag_engine import build_assurance_red_flags, build_tax_red_flags, load_red_flag_rules


def _base_case():
    bundle = load_data("2026-07-01")
    asset_risk = build_asset_risk_table(bundle["assets"])
    latest_kpi = bundle["kpis"].sort_values("period_end").iloc[-1]
    macro = build_macro_context("")
    scenario_params = macro_scenario_parameters(macro, "중립: 현재와 유사한 금융환경")
    scenario = build_interactive_scenario_outputs(
        latest_kpi,
        bundle["debt_schedule"],
        asset_risk,
        scenario_params["rate_shock_bp"],
        scenario_params["refinancing_share_pct"],
        scenario_params["ffo_haircut_pct"],
        scenario_params["cap_rate_shock_bp"],
    )
    return bundle, asset_risk, latest_kpi, scenario


def test_neutral_scenario_outputs_are_stable():
    _, _, _, scenario = _base_case()

    assert scenario["stressed_ffo"] == pytest.approx(21691.32)
    assert scenario["stressed_icr"] == pytest.approx(2.2246)
    assert scenario["nav_change_pct"] == pytest.approx(-6.4653263886)
    assert scenario["stressed_ltv_proxy"] == pytest.approx(34.5125589127)
    assert scenario["cap_rate_shock_bp"] == 10


def test_reit_level_risk_score_is_stable():
    bundle, asset_risk, latest_kpi, _ = _base_case()

    scores, total_risk, risk_level, _ = calculate_reit_level_risk(
        latest_kpi,
        bundle["debt_schedule"],
        asset_risk,
    )

    assert scores["Income / Lease Stability Risk"] == 50
    assert scores["Refinancing / Debt Service Risk"] == 45
    assert scores["Valuation / NAV Sensitivity Risk"] == 0
    assert scores["Disclosure / Data Basis Risk"] == 60
    assert total_risk == pytest.approx(37.25)
    assert risk_level == "Low"


def test_holding_tax_proxy_estimator_builds_five_year_asset_history():
    _, asset_risk, _, _ = _base_case()

    official_price_history = build_proxy_official_price_history(asset_risk, latest_year=2026)
    tax_history = build_holding_tax_estimator(asset_risk, official_price_history)

    assert tax_history.shape[0] == 35
    assert tax_history["year"].min() == 2022
    assert tax_history["year"].max() == 2026
    assert "보유세_추정_백만원" in tax_history.columns
    assert tax_history["보유세_추정_백만원"].sum() > 0
    assert tax_history["official_price_source"].str.contains("proxy").all()


def test_tax_cash_flow_and_workflow_automation_tables_are_built():
    bundle, asset_risk, latest_kpi, scenario = _base_case()

    official_price_history = build_proxy_official_price_history(asset_risk, latest_year=2026)
    tax_history = build_holding_tax_estimator(asset_risk, official_price_history)
    annual_summary = tax_history.groupby("year", as_index=False).agg(보유세_추정_백만원=("보유세_추정_백만원", "sum"))
    annual_summary["토지_시가표준액_백만원"] = 0
    annual_summary["토지_과세표준_백만원"] = 0
    annual_summary["재산세본세_백만원"] = 0
    annual_summary["도시지역분_백만원"] = 0
    annual_summary["지방교육세_백만원"] = 0
    annual_summary["누적증가율_%"] = 0
    annual_summary["전년대비증가율_%"] = annual_summary["보유세_추정_백만원"].pct_change() * 100

    cash = build_property_tax_cash_flow_scenarios(latest_kpi, annual_summary, scenario)
    workflow = build_reit_tax_workflow_checklist(latest_kpi, annual_summary, cash, "proxy")
    risk_register = build_tax_risk_register(tax_history, annual_summary, cash, "proxy")

    assert cash["시나리오"].tolist() == [
        "현재 추정",
        "공시가격/과표 +5%",
        "공시가격/과표 +10%",
        "공시가격/과표 +20%",
        "공시가격/과표 +30%",
    ]
    assert cash["추가_현금유출_백만원"].max() > 0
    assert "FFO·배당 현금세무 계획" in workflow["업무영역"].tolist()
    assert workflow["완료"].eq(False).all()
    assert "공시가격·기준시가 원천 신뢰도" in risk_register["리스크/기회"].tolist()


def test_official_price_upload_accepts_cp949_korean_csv():
    raw = pd.DataFrame(
        [
            {
                "자산명": "테스트자산",
                "연도": 2026,
                "개별공시지가_원_m2": 1234567,
                "토지면적_sqm": 1000,
                "건물기준시가_백만원": 2500,
                "출처": "sample",
            }
        ]
    )
    payload = BytesIO(raw.to_csv(index=False).encode("cp949"))

    parsed, status = parse_official_price_upload(payload)

    assert status == "uploaded"
    assert parsed.loc[0, "asset_name"] == "테스트자산"
    assert parsed.loc[0, "year"] == 2026
    assert parsed.loc[0, "official_land_price_per_sqm_krw"] == 1234567


def test_assurance_workflow_checklist_follows_audit_sequence():
    bundle, asset_risk, latest_kpi, scenario = _base_case()
    assurance_assets = build_assurance_asset_priority(asset_risk, scenario, 10.0)

    checklist = build_audit_workflow_checklist(latest_kpi, bundle["debt_schedule"], scenario, assurance_assets)
    rmm_checklist = build_rmm_assertion_checklist(latest_kpi, bundle["debt_schedule"], scenario, assurance_assets)

    assert checklist["감사단계"].drop_duplicates().tolist() == [
        "기업과 기업환경 이해",
        "위험평가절차",
        "통제테스트",
        "실증절차",
        "보고·KAM·커뮤니케이션",
    ]
    assert checklist["완료"].eq(False).all()
    assert checklist["기준서 근거"].str.contains("감사기준서 315").any()
    assert checklist["기준서 근거"].str.contains("감사기준서 330").any()
    assert "투자부동산 공정가치" in rmm_checklist["계정/공시"].tolist()
    assert rmm_checklist["실증절차"].str.contains("외부평가보고서").any()
    assert "가치변화 산정 메모" in assurance_assets.columns


def test_forecast_weighted_macro_scenario_builds_probabilities():
    macro = build_macro_context("")
    scenario = macro_scenario_parameters(
        macro,
        FORECAST_WEIGHTED_SCENARIO_NAME,
        {
            "gdp_growth_2026_pct": 2.6,
            "cpi_2026_pct": 2.7,
            "policy_rate_12m_pct": 2.5,
            "credit_spread_change_bp": 25,
        },
    )

    probabilities = scenario["scenario_probabilities"]
    assert probabilities is not None
    assert sum(probabilities.values()) == pytest.approx(1.0, abs=0.001)
    assert scenario["cap_rate_shock_bp"] >= 0


def test_v12_peer_snapshot_and_red_flags_are_built():
    snapshot = load_peer_snapshot()
    metrics = calculate_peer_metrics(snapshot)
    rules = load_red_flag_rules()
    company = metrics.loc[metrics["company_name"].str.contains("SK", na=False), "company_name"].iloc[0]

    summary = summarize_peer_position(metrics, company)
    assurance_flags = build_assurance_red_flags(company, metrics, rules)
    tax_flags = build_tax_red_flags(company, metrics, rules)

    assert summary["available"] is True
    assert summary["peer_count"] >= 5
    assert "debt_to_assets" in metrics.columns
    assert "holding_tax_to_ffo" in metrics.columns
    assert assurance_flags
    assert tax_flags
    assert {flag["risk_level"] for flag in assurance_flags}.issubset({"green", "yellow", "red", "gray"})
    assert {flag["risk_level"] for flag in tax_flags}.issubset({"green", "yellow", "red", "gray"})


def test_v12_peer_metric_missing_value_is_gray():
    rule = {
        "metric": "missing_metric",
        "risk_direction": "high_is_bad",
        "yellow_percentile": 0.7,
        "red_percentile": 0.9,
    }

    assert classify_metric_risk(pd.NA, pd.NA, rule) == "gray"


def test_v12_company_selector_uses_market_cap_rank_snapshot():
    master = load_reit_master()
    options = company_options(master)

    assert options[0].startswith("1위 ")
    assert "(395400)" in options[0]
    assert master["market_cap_rank"].is_monotonic_increasing


def test_v12_selected_company_profile_and_recent_5y_snapshot_are_built():
    master = load_reit_master()
    snapshot = load_peer_snapshot()
    profile = get_selected_company_profile("1위 SK리츠 (395400)", master, snapshot)
    recent_5y, status = get_recent_5y_financials(profile, snapshot, "")

    assert profile["company_name"] == "SK리츠"
    assert profile["stock_code"] == "395400"
    assert profile["market_cap_rank"] == 1
    assert status == "Snapshot 기준"
    assert recent_5y.shape[0] == 5
    assert recent_5y["year"].is_monotonic_increasing
    assert {"total_assets", "investment_property", "borrowings_total", "ffo_proxy", "nav", "source_type"}.issubset(recent_5y.columns)
