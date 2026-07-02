import json
from pathlib import Path
from typing import Any

import pandas as pd

from calculations_peer import classify_metric_risk, get_company_peer_profile


DEFAULT_RULE_PATH = Path(__file__).resolve().parent / "data" / "red_flag_rules.json"


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return Path(__file__).resolve().parent / candidate


def load_red_flag_rules(path: str | Path = DEFAULT_RULE_PATH) -> dict:
    resolved = _resolve_path(path)
    if not resolved.exists():
        return {"assurance": [], "tax": []}
    with resolved.open("r", encoding="utf-8") as f:
        return json.load(f)


def _to_float_or_na(value: Any):
    converted = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return converted if pd.notna(converted) else pd.NA


def evaluate_rule(company_row, peer_df: pd.DataFrame, rule: dict) -> dict:
    metric = rule.get("metric")
    value = _to_float_or_na(company_row.get(metric, pd.NA))
    percentile = _to_float_or_na(company_row.get(f"{metric}_percentile", pd.NA))
    level = classify_metric_risk(value, percentile, rule)

    peer_values = pd.to_numeric(peer_df.get(metric, pd.Series(dtype="float64")), errors="coerce")
    peer_median = peer_values.median(skipna=True) if not peer_values.empty else pd.NA
    peer_average = peer_values.mean(skipna=True) if not peer_values.empty else pd.NA

    return {
        "id": rule.get("id"),
        "label": rule.get("label", metric),
        "metric": metric,
        "value": value,
        "percentile": percentile,
        "peer_median": peer_median,
        "peer_average": peer_average,
        "risk_level": level,
        "risk_label": risk_level_to_korean_label(level),
        "risk_icon": risk_level_to_icon(level),
        "area": rule.get("area", ""),
        "explanation_ko": rule.get("explanation_ko", ""),
        "audit_response": rule.get("audit_response", []),
        "tax_review_points": rule.get("tax_review_points", []),
        "evidence_request": rule.get("evidence_request", []),
    }


def _build_flags(company_name: str, peer_df: pd.DataFrame, rules: dict, category: str) -> list[dict]:
    if peer_df is None or peer_df.empty:
        return []
    company_row = get_company_peer_profile(peer_df, company_name)
    if isinstance(company_row, dict) and not company_row:
        return []
    evaluated = [evaluate_rule(company_row, peer_df, rule) for rule in rules.get(category, [])]
    return sorted(evaluated, key=lambda row: {"red": 0, "yellow": 1, "gray": 2, "green": 3}.get(row["risk_level"], 9))


def build_assurance_red_flags(company_name: str, peer_df: pd.DataFrame, rules: dict) -> list[dict]:
    return _build_flags(company_name, peer_df, rules, "assurance")


def build_tax_red_flags(company_name: str, peer_df: pd.DataFrame, rules: dict) -> list[dict]:
    return _build_flags(company_name, peer_df, rules, "tax")


def risk_level_to_korean_label(level: str) -> str:
    return {
        "green": "정상",
        "yellow": "주의",
        "red": "높음",
        "gray": "데이터 부족",
    }.get(level, "데이터 부족")


def risk_level_to_icon(level: str) -> str:
    return {
        "green": "[정상]",
        "yellow": "[주의]",
        "red": "[높음]",
        "gray": "[데이터 부족]",
    }.get(level, "[데이터 부족]")


def risk_level_to_color_style(level: str) -> str:
    return {
        "green": "success",
        "yellow": "warning",
        "red": "error",
        "gray": "info",
    }.get(level, "info")
