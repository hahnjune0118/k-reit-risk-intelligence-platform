import ast
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from api_ecos import build_macro_context
from api_real_estate_board import parse_official_price_upload
from calculations_assurance import (
    build_assurance_asset_priority,
    build_audit_workflow_checklist,
    build_company_level_asset_tenant_proxy,
    build_company_level_refinancing_proxy,
    build_company_level_valuation_proxy,
    build_rmm_assertion_checklist,
)
from calculations_peer import calculate_peer_metrics, classify_metric_risk, load_peer_snapshot, summarize_peer_position
from calculations_risk import (
    build_asset_concentration_table,
    build_asset_risk_table,
    build_interactive_scenario_outputs,
    build_tenant_exposure_table,
    calculate_reit_level_risk,
)
from calculations_scenario import FORECAST_WEIGHTED_SCENARIO_NAME, macro_scenario_parameters
from calculations_tax import (
    build_holding_tax_estimator,
    build_property_tax_cash_flow_scenarios,
    build_proxy_official_price_history,
    build_reit_tax_workflow_checklist,
    build_tax_risk_register,
    summarize_holding_tax_history,
)
from calculations_tax_review_pack import (
    build_ffo_cash_outflow_stress,
    build_holding_tax_reconciliation,
    build_tax_issue_matrix,
    build_tax_request_list,
    build_tax_review_memo,
)
from dart_financials import company_options, get_recent_5y_financials, get_selected_company_profile, load_reit_master
from data_loader import load_data
from data_availability import get_company_data_availability, has_asset_level_data, has_tax_asset_data
from metric_definitions import (
    derive_book_nav_proxy,
    derive_interest_bearing_debt,
    derive_net_debt,
    is_quarter_point_rate,
    metric_definition_table,
)
from red_flag_engine import build_assurance_red_flags, build_tax_red_flags, load_red_flag_rules
from tax_data_loader import (
    build_company_tax_dataset,
    build_tax_history_from_company_tax_data,
    get_tax_source_status,
    load_tax_snapshot,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _sidebar_state_direct_keys() -> set[str]:
    tree = ast.parse((PROJECT_ROOT / "app.py").read_text(encoding="utf-8"))
    keys = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        if not isinstance(node.value, ast.Name) or node.value.id != "sidebar_state":
            continue
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            keys.add(node.slice.value)
    return keys


def _render_data_sidebar_return_keys() -> set[str]:
    tree = ast.parse((PROJECT_ROOT / "ui_sidebar.py").read_text(encoding="utf-8"))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "render_data_sidebar")
    keys = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Dict):
            continue
        for key in node.value.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                keys.add(key.value)
    return keys


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
    assert "FFO proxy·배당 현금세무 계획" in workflow["업무영역"].tolist()
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
    assert status == "Snapshot 기준 / DART 연결 설정 없음"
    assert recent_5y.shape[0] == 5
    assert recent_5y["year"].is_monotonic_increasing
    assert {"total_assets", "investment_property", "borrowings_total", "ffo_proxy", "nav", "source_type"}.issubset(recent_5y.columns)
    assert recent_5y["nav"].isna().all()
    assert recent_5y["nav_calculation_method"].str.contains("총부채 또는 nav 컬럼 부족", na=False).all()


def test_v12_empty_company_asset_detail_does_not_reuse_sample_assets():
    bundle, _, latest_kpi, _ = _base_case()
    empty_assets = build_asset_risk_table(bundle["assets"].iloc[0:0].copy())
    empty_debt = bundle["debt_schedule"].iloc[0:0].copy()

    scenario = build_interactive_scenario_outputs(
        latest_kpi,
        empty_debt,
        empty_assets,
        rate_shock_bp=50,
        refinancing_share_pct=25,
        ffo_haircut_pct=5,
        cap_rate_shock_bp=50,
    )

    assert empty_assets.empty
    assert build_asset_concentration_table(empty_assets).empty
    assert build_tenant_exposure_table(empty_assets).empty
    assert scenario["asset_sensitivity"].empty
    assert pd.isna(scenario["nav_change_pct"])


def test_v12_sidebar_state_contract_covers_app_direct_access_keys():
    app_direct_keys = _sidebar_state_direct_keys()
    sidebar_return_keys = _render_data_sidebar_return_keys()
    required_contract_keys = {
        "mode",
        "selected_mode",
        "selected_company",
        "selected_stock_code",
        "selected_dart_corp_code",
        "selected_company_profile",
        "recent_5y_financials",
        "selected_company_assets",
        "selected_company_tax_data",
        "selected_scenario",
        "scenario",
        "analysis_run_id",
        "data_connection_status",
    }

    assert app_direct_keys.issubset(sidebar_return_keys)
    assert required_contract_keys.issubset(sidebar_return_keys)


def test_v13_tax_snapshot_covers_all_master_reits():
    master = load_reit_master()
    tax_snapshot = load_tax_snapshot()

    assert set(master["company_name"]).issubset(set(tax_snapshot["company_name"]))
    assert {"company_name", "asset_name", "estimated_holding_tax", "source_type", "source_note"}.issubset(tax_snapshot.columns)


def test_v13_non_sk_tax_review_pack_uses_snapshot_estimate_without_sample_assets():
    master = load_reit_master()
    peer_snapshot = load_peer_snapshot()
    profile = get_selected_company_profile("2위 ESR켄달스퀘어리츠 (365550)", master, peer_snapshot)
    recent_5y, _ = get_recent_5y_financials(profile, peer_snapshot, "")
    latest_kpi = load_data("2026-07-01")["kpis"].sort_values("period_end").iloc[-1].copy()
    latest_kpi["ffo_mn_krw"] = recent_5y.sort_values("year").iloc[-1]["ffo_proxy"]
    company_tax = build_company_tax_dataset(profile["company_name"], peer_snapshot, profile)
    tax_history = build_tax_history_from_company_tax_data(company_tax)
    annual_summary = summarize_holding_tax_history(tax_history)
    reconciliation = build_holding_tax_reconciliation(tax_history, latest_kpi)
    ffo_stress = build_ffo_cash_outflow_stress(latest_kpi, annual_summary, 10.0, 5.0)
    rules = load_red_flag_rules()
    metrics = calculate_peer_metrics(peer_snapshot)
    flags = build_tax_red_flags(profile["company_name"], metrics, rules)
    data_basis = get_tax_source_status(profile["company_name"], company_tax)
    issue_matrix = build_tax_issue_matrix(flags, reconciliation, ffo_stress, data_basis)
    request_list = build_tax_request_list(issue_matrix)
    memo = build_tax_review_memo(profile, data_basis, issue_matrix, reconciliation, request_list, ffo_stress)

    assert not company_tax.empty
    assert company_tax["asset_name"].tolist() == ["회사 전체 추정"]
    assert company_tax["source_type"].iloc[0] == "peer_snapshot_estimate"
    assert not tax_history.empty
    assert "SK서린빌딩" not in tax_history["asset_name"].astype(str).tolist()
    assert not reconciliation.empty
    assert not issue_matrix.empty
    assert not request_list.empty
    assert "Tax Review Memo 초안" in memo
    assert "ESR켄달스퀘어리츠" in memo
    assert "회사 전체 Snapshot 기반 추정값" in memo
    assert request_list["관련 이슈"].str.contains("자산별 상세자료 부족 보완", na=False).any()


def test_v13_data_availability_marks_non_sk_as_company_level_fallback():
    master = load_reit_master()
    peer_snapshot = load_peer_snapshot()
    sk_profile = get_selected_company_profile("1위 SK리츠 (395400)", master, peer_snapshot)
    esr_profile = get_selected_company_profile("2위 ESR켄달스퀘어리츠 (365550)", master, peer_snapshot)

    sk_availability = get_company_data_availability(sk_profile["company_name"], sk_profile, peer_snapshot)
    esr_availability = get_company_data_availability(esr_profile["company_name"], esr_profile, peer_snapshot)

    assert has_asset_level_data(sk_profile["company_name"], sk_profile) is True
    assert has_tax_asset_data(sk_profile["company_name"], sk_profile) is True
    assert has_asset_level_data(esr_profile["company_name"], esr_profile) is False
    assert has_tax_asset_data(esr_profile["company_name"], esr_profile) is False
    assert sk_availability["asset_level_real_estate_available"] is True
    assert esr_availability["asset_level_real_estate_available"] is False
    assert "회사 전체 Snapshot" in esr_availability["scope_label"]
    assert "재사용하지 않습니다" in esr_availability["source_note"]


def test_v13_assurance_company_level_proxy_tables_render_for_non_sk():
    master = load_reit_master()
    peer_snapshot = load_peer_snapshot()
    metrics = calculate_peer_metrics(peer_snapshot)
    profile = get_selected_company_profile("2위 ESR켄달스퀘어리츠 (365550)", master, peer_snapshot)
    recent_5y, _ = get_recent_5y_financials(profile, peer_snapshot, "")
    row = metrics[metrics["company_name"] == profile["company_name"]].iloc[-1]
    availability = get_company_data_availability(profile["company_name"], profile, peer_snapshot)

    asset_proxy = build_company_level_asset_tenant_proxy(row, recent_5y, availability["scope_label"])
    debt_proxy = build_company_level_refinancing_proxy(row, recent_5y, availability["scope_label"])
    valuation_proxy = build_company_level_valuation_proxy(row, availability, availability["scope_label"])

    for table in [asset_proxy, debt_proxy, valuation_proxy]:
        assert not table.empty
        assert {"구분", "지표", "값", "위험수준", "주요 해석", "데이터 기준"}.issubset(table.columns)
        assert table["데이터 기준"].str.contains("회사 전체 Snapshot", na=False).any()

    assert asset_proxy["지표"].str.contains("투자부동산 / 총자산", na=False).any()
    assert debt_proxy["지표"].str.contains("유동성 차입금 / 총차입금", na=False).any()
    assert valuation_proxy["지표"].str.contains("valuation detail availability", na=False).any()


def test_v14_1_metric_definitions_include_proxy_limitations():
    table = metric_definition_table()
    ffo = table[table["지표"].eq("FFO proxy")].iloc[0]
    nav = table[table["지표"].eq("장부기준 NAV proxy")].iloc[0]
    ltv = table[table["지표"].eq("Gross LTV")].iloc[0]

    assert "공식적으로 공시한 FFO와 동일하지 않을 수" in ffo["제한사항"]
    assert "총자산 - 총부채" in nav["계산식"]
    assert "시가평가 NAV" in nav["제한사항"]
    assert "충당부채" in ltv["제외"]


def test_v14_1_book_nav_uses_total_liabilities_not_debt_only():
    nav, method = derive_book_nav_proxy(total_assets=1_000, total_liabilities=420, total_equity=pd.NA)
    missing_nav, missing_method = derive_book_nav_proxy(total_assets=1_000, total_liabilities=pd.NA, total_equity=pd.NA)

    assert nav == 580
    assert method == "총자산 - 총부채"
    assert pd.isna(missing_nav)
    assert "부족" in missing_method


def test_v14_1_provisions_are_excluded_from_interest_bearing_debt_and_net_debt():
    debt, method = derive_interest_bearing_debt(
        short_term_borrowings=100,
        current_portion_long_term_debt=50,
        long_term_borrowings=300,
        bonds=200,
        lease_liabilities=25,
    )
    net_debt, net_method = derive_net_debt(debt, cash_and_cash_equivalents=80, short_term_financial_assets=20)

    assert debt == 675
    assert "충당부채" not in method
    assert net_debt == 575
    assert "현금및현금성자산" in net_method


def test_v14_1_rate_step_and_weighted_label_are_explicit():
    macro = build_macro_context("")
    weighted = macro_scenario_parameters(macro, FORECAST_WEIGHTED_SCENARIO_NAME)
    neutral = macro_scenario_parameters(macro, "중립: 현재와 유사한 금융환경")

    assert weighted["scenario_base_rate_label"] == "확률가중 예상 기준금리"
    assert "연속값" in weighted["scenario_base_rate_note"]
    assert neutral["scenario_base_rate_label"] == "시나리오 기준금리"
    assert is_quarter_point_rate(neutral["scenario_base_rate_pct"])
