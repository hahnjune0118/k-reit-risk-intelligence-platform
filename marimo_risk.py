from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from calculations_assurance import (
    build_assurance_asset_priority,
    build_icfr_control_points,
    build_kam_candidate_table,
    build_rmm_mapping,
)
from calculations_peer import (
    calculate_peer_metrics,
    load_peer_snapshot,
    summarize_peer_position,
)
from calculations_risk import (
    build_asset_concentration_table,
    build_asset_risk_table,
    build_debt_stress_table,
    build_interactive_scenario_outputs,
    build_reit_score_decomposition,
    build_tenant_exposure_table,
    calculate_reit_level_risk,
    scenario_verdict,
)
from calculations_scenario import (
    FORECAST_WEIGHTED_SCENARIO_NAME,
    SCENARIO_RULES,
    macro_scenario_parameters,
)
from data_validation import validate_bundle
from formatting import extract_number
from red_flag_engine import build_assurance_red_flags, load_red_flag_rules

DATA_DIR = Path(__file__).resolve().parent / "data"
SNAPSHOT_AS_OF = pd.Timestamp("2026-07-15")


class RiskDataUnavailableError(RuntimeError):
    """Safe public error for an incomplete local risk snapshot."""


@dataclass(frozen=True)
class RiskSnapshot:
    bundle: dict[str, pd.DataFrame]
    reit_master: pd.DataFrame
    peer_snapshot: pd.DataFrame
    peer_metrics: pd.DataFrame
    red_flag_rules: dict[str, Any]
    retrieved_at: str


@dataclass(frozen=True)
class RiskView:
    company_name: str
    stock_code: str
    peer_group: str
    detail_available: bool
    detail_basis: str
    latest_kpi: pd.Series
    latest_financial: pd.Series
    recent_financials: pd.DataFrame
    assets: pd.DataFrame
    debt_schedule: pd.DataFrame
    scenario_parameters: dict[str, Any]
    scenario: dict[str, Any]
    verdict: tuple[str, str, str]
    risk_scores: dict[str, float]
    total_risk: float | None
    risk_level: str
    risk_flags: list[str]
    risk_decomposition: pd.DataFrame
    peer_summary: dict[str, Any]
    peer_comparison: pd.DataFrame
    peer_red_flags: pd.DataFrame
    asset_concentration: pd.DataFrame
    tenant_exposure: pd.DataFrame
    debt_stress: pd.DataFrame
    maturity_profile: pd.DataFrame
    assurance_assets: pd.DataFrame
    rmm: pd.DataFrame
    kam_candidates: pd.DataFrame
    icfr_controls: pd.DataFrame
    sensitivity: pd.DataFrame


@dataclass(frozen=True)
class DashboardCharts:
    risk_heatmap: Any
    risk_composition: Any
    tax_heatmap: Any
    tax_scenario: Any


@dataclass(frozen=True)
class DetailCharts:
    historical: Any
    asset_concentration: Any
    maturity: Any


def _load_csv(data_dir: Path, name: str) -> pd.DataFrame:
    path = data_dir / name
    if not path.exists():
        raise RiskDataUnavailableError(f"필수 저장 시점 자료가 없습니다: {name}")
    return pd.read_csv(path)


def load_risk_snapshot(data_dir: str | Path = DATA_DIR) -> RiskSnapshot:
    """Load the Streamlit analysis bundle without importing Streamlit."""
    base = Path(data_dir)
    bundle = {
        "financials": _load_csv(base, "sk_reit_consolidated_financials.csv"),
        "kpis": _load_csv(base, "sk_reit_latest_kpis.csv"),
        "assets": _load_csv(base, "sk_reit_asset_metrics.csv"),
        "direct_assets": _load_csv(base, "sk_reit_parent_direct_assets_20260331.csv"),
        "debt_schedule": _load_csv(base, "sk_reit_debt_schedule_20260331.csv"),
        "debt_summary": _load_csv(base, "sk_reit_debt_summary_20260331.csv"),
        "source_plan": _load_csv(base, "sk_reit_additional_source_plan.csv"),
        "data_dictionary": _load_csv(base, "sk_reit_data_dictionary.csv"),
    }
    errors = validate_bundle(bundle)
    if errors:
        names = ", ".join(sorted(errors))
        raise RiskDataUnavailableError(f"저장 시점 자료의 필수 열 검증에 실패했습니다: {names}")

    for frame, columns in [
        (bundle["financials"], ["period_end"]),
        (bundle["kpis"], ["period_end"]),
        (bundle["assets"], ["acquisition_date"]),
        (bundle["debt_schedule"], ["borrowing_or_issue_date", "maturity_date", "period_end"]),
        (bundle["debt_summary"], ["period_end"]),
    ]:
        for column in columns:
            if column in frame:
                frame[column] = pd.to_datetime(frame[column], errors="coerce")

    assets = bundle["assets"]
    assets["estimated_annual_rent_mn_krw_num"] = assets[
        "estimated_annual_rent_mn_krw"
    ].apply(extract_number)
    assets["annual_rent_yield_on_acquisition_pct"] = (
        assets["estimated_annual_rent_mn_krw_num"]
        / assets["acquisition_price_mn_krw"]
        * 100
    )
    assets["annual_rent_yield_on_appraisal_pct"] = (
        assets["estimated_annual_rent_mn_krw_num"]
        / assets["appraised_value_mn_krw_20251231"]
        * 100
    )
    assets["asset_value_per_sqm_mn_krw"] = (
        assets["appraised_value_mn_krw_20251231"] / assets["gross_floor_area_sqm"]
    )
    assets["single_tenant_or_master_lease"] = assets[
        "tenant_concentration_pct"
    ].astype(str).str.contains("100|master", case=False, na=False)

    debt = bundle["debt_schedule"]
    debt["maturity_year"] = debt["maturity_date"].dt.year.astype("Int64")
    debt["days_to_maturity"] = (debt["maturity_date"] - SNAPSHOT_AS_OF).dt.days
    debt["rate_type"] = debt["fixed_rate_or_index"].apply(
        lambda value: "변동" if "변동" in str(value) else "고정"
    )

    peer_snapshot = load_peer_snapshot(base / "reit_peer_snapshot.csv")
    return RiskSnapshot(
        bundle=bundle,
        reit_master=_load_csv(base, "reit_master.csv"),
        peer_snapshot=peer_snapshot,
        peer_metrics=calculate_peer_metrics(peer_snapshot),
        red_flag_rules=load_red_flag_rules(base / "red_flag_rules.json"),
        retrieved_at="2026-07-15",
    )


def _latest_peer_row(snapshot: RiskSnapshot, company_name: str) -> pd.Series:
    rows = snapshot.peer_snapshot[
        snapshot.peer_snapshot["company_name"].astype(str).eq(company_name)
    ]
    if rows.empty:
        raise RiskDataUnavailableError("선택한 리츠의 Peer Snapshot이 없습니다.")
    return rows.sort_values(["year", "period"]).iloc[-1]


def _selected_kpi(snapshot: RiskSnapshot, company_name: str) -> tuple[pd.Series, pd.Series]:
    base_kpi = snapshot.bundle["kpis"].sort_values("period_end").iloc[-1].copy()
    base_fin = snapshot.bundle["financials"].sort_values("period_end").iloc[-1].copy()
    peer = _latest_peer_row(snapshot, company_name)
    master = snapshot.reit_master[
        snapshot.reit_master["company_name"].astype(str).eq(company_name)
    ]
    stock_code = str(master.iloc[0]["stock_code"]).replace(".0", "") if not master.empty else str(peer.get("stock_code", ""))

    base_kpi["reit_name"] = company_name
    base_kpi["ticker"] = stock_code.zfill(6)
    base_fin["reit_name"] = company_name
    base_fin["ticker"] = stock_code.zfill(6)
    mappings = {
        "ffo_proxy": "ffo_mn_krw",
        "book_nav_proxy": "nav_mn_krw",
        "dividends": "common_dividend_total_mn_krw",
        "operating_revenue": "revenue_mn_krw",
        "net_income": "net_income_mn_krw",
    }
    for source, target in mappings.items():
        if pd.notna(peer.get(source, pd.NA)):
            base_kpi[target] = peer[source]
    total_assets = pd.to_numeric(pd.Series([peer.get("total_assets")]), errors="coerce").iloc[0]
    debt = pd.to_numeric(pd.Series([peer.get("borrowings_total")]), errors="coerce").iloc[0]
    interest = pd.to_numeric(pd.Series([peer.get("interest_expense")]), errors="coerce").iloc[0]
    ffo = pd.to_numeric(pd.Series([peer.get("ffo_proxy")]), errors="coerce").iloc[0]
    base_kpi["leverage_pct"] = debt / total_assets * 100 if pd.notna(debt) and total_assets else pd.NA
    base_kpi["interest_coverage_x"] = ffo / interest if pd.notna(ffo) and interest else pd.NA

    fin_map = {
        "total_assets": "total_assets_mn_krw",
        "investment_property": "investment_property_mn_krw",
        "total_liabilities": "total_liabilities_mn_krw",
        "borrowings_total": "interest_bearing_debt_mn_krw",
        "operating_revenue": "revenue_mn_krw",
        "operating_income": "operating_income_mn_krw",
        "net_income": "net_income_mn_krw",
        "book_nav_proxy": "total_equity_mn_krw",
    }
    for source, target in fin_map.items():
        if pd.notna(peer.get(source, pd.NA)):
            base_fin[target] = peer[source]
    return base_kpi, base_fin


def _peer_table(metrics: pd.DataFrame, company_name: str) -> pd.DataFrame:
    target = metrics[metrics["company_name"].astype(str).eq(company_name)]
    if target.empty:
        return pd.DataFrame()
    row = target.iloc[0]
    definitions = [
        ("FFO proxy", "ffo_proxy", "백만원", False),
        ("FFO 이자감당력", "interest_expense_to_ffo", "배", True),
        ("총자산 대비 차입금", "debt_to_assets", "%", True),
        ("배당 부담", "dividend_to_ffo", "%", True),
        ("보유세 / FFO", "holding_tax_to_ffo", "%", True),
    ]
    rows: list[dict[str, Any]] = []
    for label, metric, unit, ratio in definitions:
        values = pd.to_numeric(metrics.get(metric), errors="coerce")
        value = pd.to_numeric(pd.Series([row.get(metric)]), errors="coerce").iloc[0]
        median = values.median(skipna=True)
        if ratio and unit == "%":
            value = value * 100 if pd.notna(value) else value
            median = median * 100 if pd.notna(median) else median
        if metric == "interest_expense_to_ffo":
            value = 1 / value if pd.notna(value) and value else pd.NA
            median = 1 / median if pd.notna(median) and median else pd.NA
        rows.append(
            {
                "지표": label,
                "현재": value,
                "Peer 중앙값": median,
                "백분위": row.get(f"{metric}_percentile", pd.NA) * 100,
                "단위": unit,
            }
        )
    return pd.DataFrame(rows)


def _custom_scenario_parameters(inputs: dict[str, float]) -> dict[str, Any]:
    current_rate = 2.50
    policy_change_bp = (float(inputs["policy_rate_pct"]) - current_rate) * 100
    spread_change_bp = float(inputs["credit_spread_change_bp"])
    funding_shock = max(0.0, policy_change_bp + spread_change_bp)
    gdp_shortfall = max(0.0, 2.1 - float(inputs["gdp_growth_pct"]))
    inflation_pressure = max(0.0, float(inputs["cpi_pct"]) - 2.3)
    return {
        "selected_scenario": "사용자 설정",
        "scenario_explain": "입력한 기준금리·신용스프레드는 차입충격에, 성장률·물가는 FFO 압력에 반영했습니다.",
        "base_rate_pct": current_rate,
        "scenario_base_rate_pct": float(inputs["policy_rate_pct"]),
        "credit_spread_pct": 1.90,
        "scenario_credit_spread_pct": 1.90 + spread_change_bp / 100,
        "rate_shock_bp": round(funding_shock),
        "cap_rate_shock_bp": round(float(inputs["cap_rate_shock_bp"])),
        "ffo_haircut_pct": round(min(25.0, gdp_shortfall * 4 + inflation_pressure * 2), 1),
        "refinancing_share_pct": float(inputs["refinancing_share_pct"]),
        "policy_rate_change_bp": policy_change_bp,
        "credit_spread_change_bp": spread_change_bp,
        "rate_shock_formula": "기준금리 변화 + 신용스프레드 변화(음수 합계는 0)",
        "scenario_probabilities": None,
    }


def _scenario_parameters(preset: str, inputs: dict[str, float]) -> dict[str, Any]:
    if preset == "사용자 설정":
        return _custom_scenario_parameters(inputs)
    scenario_name = {
        "기준": "중립: 현재와 유사한 금융환경",
        "호황": "호황: 금리 높지만 임대수익 방어",
        "중립": "중립: 현재와 유사한 금융환경",
        "불황": "불황: 금리 인하에도 신용위험 확대",
        "확률가중": FORECAST_WEIGHTED_SCENARIO_NAME,
    }.get(preset, "중립: 현재와 유사한 금융환경")
    macro = {"base_rate_pct": 2.50, "credit_spread_pct": 1.90}
    forecast = {
        "gdp_growth_2026_pct": float(inputs["gdp_growth_pct"]),
        "cpi_2026_pct": float(inputs["cpi_pct"]),
        "policy_rate_12m_pct": float(inputs["policy_rate_pct"]),
        "credit_spread_change_bp": float(inputs["credit_spread_change_bp"]),
    }
    return macro_scenario_parameters(macro, scenario_name, forecast)


def _risk_proxy(peer_metrics: pd.DataFrame, company_name: str) -> tuple[dict[str, float], float, str, list[str]]:
    row = peer_metrics[
        peer_metrics["company_name"].astype(str).eq(company_name)
    ].iloc[0]
    debt_pct = float(row.get("debt_to_assets_percentile", 0.5) or 0.5) * 100
    interest_pct = float(row.get("interest_expense_to_ffo_percentile", 0.5) or 0.5) * 100
    payout_pct = float(row.get("dividend_to_ffo_percentile", 0.5) or 0.5) * 100
    scores = {
        "Income / Lease Stability Risk": payout_pct,
        "Refinancing / Debt Service Risk": (debt_pct + interest_pct) / 2,
        "Valuation / NAV Sensitivity Risk": float(row.get("official_price_to_investment_property_percentile", 0.5) or 0.5) * 100,
        "Disclosure / Data Basis Risk": 55.0,
    }
    total = scores["Income / Lease Stability Risk"] * 0.25 + scores["Refinancing / Debt Service Risk"] * 0.35 + scores["Valuation / NAV Sensitivity Risk"] * 0.25 + scores["Disclosure / Data Basis Risk"] * 0.15
    level = "High" if total >= 70 else "Medium" if total >= 40 else "Low"
    return scores, total, level, ["회사별 상세 자산·차입금이 없어 Peer Snapshot 백분위 proxy 사용"]


def build_risk_view(
    snapshot: RiskSnapshot,
    *,
    company_name: str,
    peer_group: str,
    preset: str,
    inputs: dict[str, float],
    materiality_pct: float = 10.0,
) -> RiskView:
    latest_kpi, latest_fin = _selected_kpi(snapshot, company_name)
    peer_metrics = snapshot.peer_metrics
    if peer_group == "동일 자산유형":
        selected_master = snapshot.reit_master[
            snapshot.reit_master["company_name"].astype(str).eq(company_name)
        ]
        if not selected_master.empty:
            asset_type = selected_master.iloc[0].get("main_asset_type")
            peer_names = snapshot.reit_master.loc[
                snapshot.reit_master["main_asset_type"].eq(asset_type), "company_name"
            ].astype(str)
            peer_metrics = peer_metrics[
                peer_metrics["company_name"].astype(str).isin(peer_names)
            ].copy()
    detail_available = company_name == "SK리츠"
    assets = snapshot.bundle["assets"].copy() if detail_available else snapshot.bundle["assets"].iloc[0:0].copy()
    debt = snapshot.bundle["debt_schedule"].copy() if detail_available else snapshot.bundle["debt_schedule"].iloc[0:0].copy()
    detail_basis = "회사별 상세 자산·차입금 CSV" if detail_available else "Peer Snapshot proxy · 상세 자산 수치 미제공"
    params = _scenario_parameters(preset, inputs)
    scenario = build_interactive_scenario_outputs(
        latest_kpi,
        debt,
        assets,
        params["rate_shock_bp"],
        params["refinancing_share_pct"],
        params["ffo_haircut_pct"],
        params["cap_rate_shock_bp"],
        params,
    )

    if detail_available:
        asset_risk = build_asset_risk_table(assets)
        risk_scores, total_risk, risk_level, risk_flags = calculate_reit_level_risk(latest_kpi, debt, asset_risk)
        risk_decomposition = build_reit_score_decomposition(latest_kpi, debt, asset_risk)
    else:
        asset_risk = assets.copy()
        risk_scores, total_risk, risk_level, risk_flags = _risk_proxy(peer_metrics, company_name)
        risk_decomposition = pd.DataFrame(
            {"risk_category": list(risk_scores), "weighted_score_delta": list(risk_scores.values())}
        )

    asset_concentration = build_asset_concentration_table(asset_risk)
    tenant_exposure = build_tenant_exposure_table(asset_risk)
    debt_stress = build_debt_stress_table(latest_kpi, debt) if detail_available else pd.DataFrame()
    maturity_profile = (
        debt.groupby("maturity_year", dropna=False)["principal_mn_krw"].sum().reset_index()
        if not debt.empty
        else pd.DataFrame(columns=["maturity_year", "principal_mn_krw"])
    )
    assurance_assets = (
        build_assurance_asset_priority(asset_risk, scenario, materiality_pct)
        if not asset_risk.empty
        else pd.DataFrame()
    )
    rmm = build_rmm_mapping(latest_kpi, debt, scenario, assurance_assets)
    rmm_contract = {
        "투자부동산 공정가치": ("투자부동산·평가손익", "평가·정확성", "높음", "높음", "외부평가·IPE 검증 필요"),
        "차입금·유동성·계속기업": ("차입금·이자비용·유동성 공시", "완전성·분류·기간귀속", "중간", "높음", "차입약정·차환계획 요청"),
        "임대수익·임대채권": ("임대수익·미수임대료", "발생·정확성·기간귀속", "중간", "중간", "계약서·수금내역 검증"),
        "특수관계자 거래·공시": ("특수관계자 거래·주석", "완전성·분류", "중간", "중간", "관계자 목록·승인자료 요청"),
    }
    rmm["관련 계정과목"] = rmm["감사영역"].map(lambda value: rmm_contract[value][0])
    rmm["경영진 주장"] = rmm["감사영역"].map(lambda value: rmm_contract[value][1])
    rmm["발생가능성"] = rmm["감사영역"].map(lambda value: rmm_contract[value][2])
    rmm["영향"] = rmm["감사영역"].map(lambda value: rmm_contract[value][3])
    rmm["감사증거 상태"] = rmm["감사영역"].map(lambda value: rmm_contract[value][4])
    kam = build_kam_candidate_table(scenario, assurance_assets, debt, latest_kpi)
    flags = pd.DataFrame(build_assurance_red_flags(company_name, peer_metrics, snapshot.red_flag_rules))

    sensitivity_rows = []
    for rate_bp in [0, 50, 100, 150, 200]:
        for cap_bp in [0, 25, 50, 100, 150]:
            point = build_interactive_scenario_outputs(
                latest_kpi,
                debt,
                assets,
                rate_bp,
                params["refinancing_share_pct"],
                params["ffo_haircut_pct"],
                cap_bp,
                {"selected_scenario": "민감도"},
            )
            sensitivity_rows.append(
                {
                    "금리충격_bp": rate_bp,
                    "Cap_rate_충격_bp": cap_bp,
                    "FFO_변화율": point["ffo_decline_pct"],
                    "NAV_변화율": point["nav_change_pct"],
                }
            )

    master = snapshot.reit_master[snapshot.reit_master["company_name"].astype(str).eq(company_name)]
    stock_code = str(master.iloc[0]["stock_code"]).replace(".0", "").zfill(6) if not master.empty else str(latest_kpi.get("ticker", ""))
    recent = snapshot.bundle["financials"].copy() if detail_available else snapshot.peer_snapshot[snapshot.peer_snapshot["company_name"].astype(str).eq(company_name)].copy()
    return RiskView(
        company_name=company_name,
        stock_code=stock_code,
        peer_group=peer_group,
        detail_available=detail_available,
        detail_basis=detail_basis,
        latest_kpi=latest_kpi,
        latest_financial=latest_fin,
        recent_financials=recent,
        assets=asset_risk,
        debt_schedule=debt,
        scenario_parameters=params,
        scenario=scenario,
        verdict=scenario_verdict(scenario),
        risk_scores=risk_scores,
        total_risk=total_risk,
        risk_level=risk_level,
        risk_flags=risk_flags,
        risk_decomposition=risk_decomposition,
        peer_summary=summarize_peer_position(peer_metrics, company_name),
        peer_comparison=_peer_table(peer_metrics, company_name),
        peer_red_flags=flags,
        asset_concentration=asset_concentration,
        tenant_exposure=tenant_exposure,
        debt_stress=debt_stress,
        maturity_profile=maturity_profile,
        assurance_assets=assurance_assets,
        rmm=rmm,
        kam_candidates=kam,
        icfr_controls=build_icfr_control_points(),
        sensitivity=pd.DataFrame(sensitivity_rows),
    )


def scenario_presets() -> list[str]:
    return ["기준", "호황", "중립", "불황", "확률가중", "사용자 설정"]


def streamlit_scenario_names() -> list[str]:
    return list(SCENARIO_RULES) + [FORECAST_WEIGHTED_SCENARIO_NAME]
