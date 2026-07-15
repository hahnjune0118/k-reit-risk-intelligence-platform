from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_PEER_SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "reit_peer_snapshot.csv"

PEER_METRIC_COLUMNS = [
    "total_assets",
    "investment_property_to_total_assets",
    "debt_to_assets",
    "current_debt_to_total_debt",
    "interest_expense_to_ffo",
    "dividend_to_ffo",
    "holding_tax_to_ffo",
    "holding_tax_to_operating_revenue",
    "official_price_to_investment_property",
    "official_price_growth_5y",
    "operating_cash_flow_to_dividends",
]


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return Path(__file__).resolve().parent / candidate


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    numerator = pd.to_numeric(numerator, errors="coerce")
    denominator = pd.to_numeric(denominator, errors="coerce")
    result = numerator / denominator.where(denominator.ne(0))
    return result.replace([float("inf"), float("-inf")], pd.NA).astype("Float64")


def _latest_per_company(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    sort_cols = [col for col in ["company_name", "year", "period"] if col in df.columns]
    latest = df.sort_values(sort_cols).groupby("company_name", as_index=False, sort=False).tail(1)
    return latest.reset_index(drop=True)


def load_peer_snapshot(path: str | Path = DEFAULT_PEER_SNAPSHOT_PATH) -> pd.DataFrame:
    resolved = _resolve_path(path)
    if not resolved.exists():
        return pd.DataFrame()
    df = pd.read_csv(resolved)
    numeric_cols = [
        "year",
        "total_assets",
        "total_liabilities",
        "current_assets",
        "cash_and_cash_equivalents",
        "short_term_financial_assets",
        "investment_property",
        "current_liabilities",
        "borrowings_total",
        "borrowings_current",
        "short_term_borrowings",
        "current_portion_long_term_debt",
        "long_term_borrowings",
        "bonds",
        "lease_liabilities",
        "provisions",
        "deferred_tax_liabilities",
        "interest_expense",
        "operating_revenue",
        "operating_income",
        "net_income",
        "operating_cash_flow",
        "ffo_proxy",
        "dividends",
        "estimated_holding_tax",
        "official_price_total",
        "official_price_growth_5y",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "stock_code" in df.columns:
        df["stock_code"] = df["stock_code"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
    return df


def calculate_peer_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    metrics = _latest_per_company(df).copy()
    metrics["investment_property_to_total_assets"] = _safe_divide(metrics["investment_property"], metrics["total_assets"])
    metrics["debt_to_assets"] = _safe_divide(metrics["borrowings_total"], metrics["total_assets"])
    total_liabilities = pd.to_numeric(
        metrics.get("total_liabilities", pd.Series(pd.NA, index=metrics.index)), errors="coerce"
    )
    metrics["book_nav_proxy"] = pd.to_numeric(metrics["total_assets"], errors="coerce") - total_liabilities
    metrics.loc[total_liabilities.isna(), "book_nav_proxy"] = pd.NA
    metrics["current_debt_to_total_debt"] = _safe_divide(metrics["borrowings_current"], metrics["borrowings_total"])
    metrics["interest_expense_to_ffo"] = _safe_divide(metrics["interest_expense"], metrics["ffo_proxy"])
    metrics["dividend_to_ffo"] = _safe_divide(metrics["dividends"], metrics["ffo_proxy"])
    metrics["holding_tax_to_ffo"] = _safe_divide(metrics["estimated_holding_tax"], metrics["ffo_proxy"])
    metrics["holding_tax_to_operating_revenue"] = _safe_divide(metrics["estimated_holding_tax"], metrics["operating_revenue"])
    metrics["official_price_to_investment_property"] = _safe_divide(metrics["official_price_total"], metrics["investment_property"])
    metrics["operating_cash_flow_to_dividends"] = _safe_divide(metrics["operating_cash_flow"], metrics["dividends"])
    return calculate_percentile_ranks(metrics, PEER_METRIC_COLUMNS)


def calculate_percentile_ranks(df: pd.DataFrame, metric_cols: list[str]) -> pd.DataFrame:
    ranked = df.copy()
    for col in metric_cols:
        if col not in ranked.columns:
            continue
        ranked[f"{col}_percentile"] = pd.to_numeric(ranked[col], errors="coerce").rank(pct=True, method="average")
    return ranked


def get_company_peer_profile(df: pd.DataFrame, company_name: str) -> dict | pd.Series:
    if df is None or df.empty or not company_name:
        return {}
    matched = df[df["company_name"].astype(str).str.strip() == str(company_name).strip()]
    if matched.empty:
        return {}
    return matched.sort_values([col for col in ["year", "period"] if col in matched.columns]).iloc[-1]


def classify_metric_risk(value: Any, percentile: Any, rule: dict) -> str:
    value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    percentile = pd.to_numeric(pd.Series([percentile]), errors="coerce").iloc[0]
    if pd.isna(value):
        return "gray"

    direction = rule.get("risk_direction", "high_is_bad")
    yellow_abs = rule.get("yellow_absolute")
    red_abs = rule.get("red_absolute")
    yellow_pct = rule.get("yellow_percentile")
    red_pct = rule.get("red_percentile")

    if direction == "low_is_bad":
        if red_abs is not None and value <= float(red_abs):
            return "red"
        if yellow_abs is not None and value <= float(yellow_abs):
            return "yellow"
        if pd.notna(percentile):
            if red_pct is not None and percentile <= float(red_pct):
                return "red"
            if yellow_pct is not None and percentile <= float(yellow_pct):
                return "yellow"
        return "green"

    if red_abs is not None and value >= float(red_abs):
        return "red"
    if yellow_abs is not None and value >= float(yellow_abs):
        return "yellow"
    if pd.notna(percentile):
        if red_pct is not None and percentile >= float(red_pct):
            return "red"
        if yellow_pct is not None and percentile >= float(yellow_pct):
            return "yellow"
    return "green"


def _rules_for_category(rules: dict | list[dict], category: str) -> list[dict]:
    if isinstance(rules, dict):
        return list(rules.get(category, []))
    return [rule for rule in rules if str(rule.get("area", "")).lower() == category.lower()]


def generate_red_flags(metrics_df: pd.DataFrame, company_name: str, rules: dict | list[dict], category: str = "assurance") -> list[dict]:
    company_row = get_company_peer_profile(metrics_df, company_name)
    if isinstance(company_row, dict) and not company_row:
        return []

    flags = []
    for rule in _rules_for_category(rules, category):
        metric = rule.get("metric")
        value = company_row.get(metric, pd.NA)
        percentile = company_row.get(f"{metric}_percentile", pd.NA)
        level = classify_metric_risk(value, percentile, rule)
        metric_source_type = company_row.get(
            "tax_source_type" if category.lower() == "tax" else "source_type",
            company_row.get("source_type", "data_insufficient"),
        )
        threshold = (
            f"주의 {rule.get('yellow_absolute')} / 높음 {rule.get('red_absolute')}"
            if rule.get("yellow_absolute") is not None or rule.get("red_absolute") is not None
            else "Peer percentile 기준"
        )
        flags.append({
            "id": rule.get("id"),
            "label": rule.get("label", metric),
            "metric": metric,
            "value": value,
            "percentile": percentile,
            "risk_level": level,
            "threshold": threshold,
            "source_type": metric_source_type,
            "source_limitation": (
                "회사 전체 Snapshot 또는 추정 입력을 사용하므로 원자료 대사 전 수치 결론을 확정하지 않습니다."
                if metric_source_type in {"peer_snapshot_estimate", "sample_estimate", "data_insufficient"}
                else "공식 공시 기반이라도 기간·재무제표 범위와 계산방법을 확인해야 합니다."
            ),
            "explanation_ko": rule.get("explanation_ko", ""),
            "audit_response": rule.get("audit_response", []),
            "tax_review_points": rule.get("tax_review_points", []),
            "evidence_request": rule.get("evidence_request", []),
        })
    return flags


def summarize_peer_position(metrics_df: pd.DataFrame, company_name: str) -> dict:
    company_row = get_company_peer_profile(metrics_df, company_name)
    if isinstance(company_row, dict) and not company_row:
        peer_count = 0 if metrics_df is None else int(len(metrics_df))
        return {"company_name": company_name, "available": False, "peer_count": peer_count}

    summary_metrics = [
        "total_assets",
        "debt_to_assets",
        "interest_expense_to_ffo",
        "holding_tax_to_ffo",
        "official_price_to_investment_property",
    ]
    metric_summary = {}
    for metric in summary_metrics:
        if metric not in metrics_df.columns:
            continue
        values = pd.to_numeric(metrics_df[metric], errors="coerce")
        target_value = company_row.get(metric, pd.NA)
        metric_summary[metric] = {
            "value": target_value,
            "peer_median": values.median(skipna=True),
            "peer_average": values.mean(skipna=True),
            "percentile": company_row.get(f"{metric}_percentile", pd.NA),
            "rank_high_to_low": values.rank(ascending=False, method="min").loc[company_row.name]
            if pd.notna(target_value) else pd.NA,
        }

    return {
        "available": True,
        "company_name": company_name,
        "peer_count": int(metrics_df["company_name"].nunique()) if "company_name" in metrics_df.columns else int(len(metrics_df)),
        "source_type": company_row.get("source_type", "unknown"),
        "last_updated": company_row.get("last_updated", ""),
        "metrics": metric_summary,
    }
