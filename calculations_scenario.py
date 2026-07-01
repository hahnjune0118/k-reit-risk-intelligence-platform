import math


FORECAST_WEIGHTED_SCENARIO_NAME = "전망 기반 확률가중: 주요 지표 자동 반영"


DEFAULT_MACRO_FORECAST = {
    "gdp_growth_2026_pct": 2.6,
    "cpi_2026_pct": 2.7,
    "policy_rate_12m_pct": 2.50,
    "credit_spread_change_bp": 25,
}


SCENARIO_RULES = {
    "호황: 금리 높지만 임대수익 방어": {
        "policy_rate_change_bp": 25,
        "credit_spread_change_bp": -25,
        "cap_rate_spread_bp": 20,
        "ffo_haircut_pct": 0,
        "refinancing_share_pct": 25,
        "probability": 0.25,
        "explain": "성장률은 양호하고 임대수익은 방어되지만, 물가·금리 수준은 완전히 낮아지지 않는 상황입니다.",
    },
    "중립: 현재와 유사한 금융환경": {
        "policy_rate_change_bp": 0,
        "credit_spread_change_bp": 0,
        "cap_rate_spread_bp": 10,
        "ffo_haircut_pct": 2,
        "refinancing_share_pct": 30,
        "probability": 0.50,
        "explain": "현재 금리·신용스프레드가 큰 충격 없이 유지되는 기본 상황입니다. Cap rate 충격은 보수적 screening 목적의 +10bp만 반영합니다.",
    },
    "불황: 금리 인하에도 신용위험 확대": {
        "policy_rate_change_bp": -25,
        "credit_spread_change_bp": 100,
        "cap_rate_spread_bp": 100,
        "ffo_haircut_pct": 12,
        "refinancing_share_pct": 50,
        "probability": 0.25,
        "explain": "기준금리는 내려가더라도 경기둔화로 신용스프레드와 부동산 위험프리미엄이 커지는 상황입니다.",
    },
}


def _softmax(scores: dict[str, float]) -> dict[str, float]:
    max_score = max(scores.values())
    exps = {key: math.exp(value - max_score) for key, value in scores.items()}
    total = sum(exps.values())
    return {key: value / total for key, value in exps.items()}


def build_forecast_scenario_probabilities(macro: dict, forecast: dict | None = None) -> dict[str, float]:
    """Turn forward-looking macro assumptions into simple scenario probabilities."""
    forecast = {**DEFAULT_MACRO_FORECAST, **(forecast or {})}
    gdp = float(forecast.get("gdp_growth_2026_pct", DEFAULT_MACRO_FORECAST["gdp_growth_2026_pct"]))
    cpi = float(forecast.get("cpi_2026_pct", DEFAULT_MACRO_FORECAST["cpi_2026_pct"]))
    policy_rate_12m = float(forecast.get("policy_rate_12m_pct", DEFAULT_MACRO_FORECAST["policy_rate_12m_pct"]))
    spread_change = float(forecast.get("credit_spread_change_bp", DEFAULT_MACRO_FORECAST["credit_spread_change_bp"]))
    current_policy = float(macro.get("base_rate_pct", 2.50))

    expansion_score = (
        0.9 * max(gdp - 2.1, 0)
        + 0.4 * max(2.4 - cpi, 0)
        + 0.3 * max(current_policy - policy_rate_12m, 0)
        + 0.003 * max(-spread_change, 0)
    )
    neutral_score = 1.0 - 0.15 * abs(gdp - 2.1) - 0.10 * abs(cpi - 2.3) - 0.002 * abs(spread_change)
    downside_score = (
        0.9 * max(2.0 - gdp, 0)
        + 0.7 * max(cpi - 2.5, 0)
        + 0.4 * max(policy_rate_12m - current_policy, 0)
        + 0.006 * max(spread_change, 0)
    )

    probabilities = _softmax({
        "호황": expansion_score,
        "중립": neutral_score,
        "불황": downside_score,
    })
    return {key: round(value, 4) for key, value in probabilities.items()}


def _weighted_rule(macro: dict, forecast: dict | None = None) -> dict:
    probabilities = build_forecast_scenario_probabilities(macro, forecast)
    rule_by_short_name = {
        "호황": SCENARIO_RULES["호황: 금리 높지만 임대수익 방어"],
        "중립": SCENARIO_RULES["중립: 현재와 유사한 금융환경"],
        "불황": SCENARIO_RULES["불황: 금리 인하에도 신용위험 확대"],
    }
    weighted = {}
    for field in ["policy_rate_change_bp", "credit_spread_change_bp", "cap_rate_spread_bp", "ffo_haircut_pct", "refinancing_share_pct"]:
        weighted[field] = sum(probabilities[name] * rule_by_short_name[name][field] for name in probabilities)
    weighted["probabilities"] = probabilities
    weighted["explain"] = (
        "BOK/KDI/IMF/OECD 등 주요 전망치를 입력값으로 받아 호황·중립·불황 확률을 계산하고, "
        "각 시나리오의 금리·신용스프레드·Cap rate·FFO 충격을 확률가중 평균으로 반영합니다."
    )
    return weighted


def macro_scenario_parameters(macro: dict, scenario_name: str, forecast: dict | None = None) -> dict:
    """
    Convert ECOS-grounded macro baseline into REIT stress assumptions.
    ECOS gives current/recent macro data. Forecast-weighted mode adds forward-looking assumptions.
    """
    if scenario_name == FORECAST_WEIGHTED_SCENARIO_NAME:
        rule = _weighted_rule(macro, forecast)
    else:
        rule = SCENARIO_RULES[scenario_name].copy()
        rule["probabilities"] = None

    funding_shock_bp = rule["policy_rate_change_bp"] + rule["credit_spread_change_bp"]
    cap_rate_shock_bp = max(0, rule["policy_rate_change_bp"] + rule["cap_rate_spread_bp"])
    scenario_rate_pct = macro["base_rate_pct"] + rule["policy_rate_change_bp"] / 100
    scenario_credit_spread_pct = macro["credit_spread_pct"] + rule["credit_spread_change_bp"] / 100

    return {
        "selected_scenario": scenario_name,
        "scenario_explain": rule["explain"],
        "base_rate_pct": macro["base_rate_pct"],
        "scenario_base_rate_pct": scenario_rate_pct,
        "credit_spread_pct": macro["credit_spread_pct"],
        "scenario_credit_spread_pct": scenario_credit_spread_pct,
        "rate_shock_bp": int(round(max(0, funding_shock_bp))),
        "cap_rate_shock_bp": int(round(max(0, cap_rate_shock_bp))),
        "ffo_haircut_pct": round(rule["ffo_haircut_pct"], 1),
        "refinancing_share_pct": round(rule["refinancing_share_pct"], 1),
        "policy_rate_change_bp": round(rule["policy_rate_change_bp"], 1),
        "credit_spread_change_bp": round(rule["credit_spread_change_bp"], 1),
        "scenario_probabilities": rule.get("probabilities"),
    }


def korean_risk_label(name: str) -> str:
    mapping = {
        "Income / Lease Stability Risk": "임대수익 안정성 위험",
        "Refinancing / Debt Service Risk": "차환·이자부담 위험",
        "Valuation / NAV Sensitivity Risk": "부동산가치·순자산 위험",
        "Disclosure / Data Basis Risk": "공시자료 기준 차이 위험",
    }
    return mapping.get(name, name)


def korean_metric_label(name: str) -> str:
    mapping = {
        "FFO": "현금흐름(FFO)",
        "Interest coverage": "이자 감당력",
        "Dividend payout": "배당 부담률",
        "NAV": "순자산가치(NAV)",
        "LTV proxy": "부채비율 추정치",
    }
    return mapping.get(name, name)
