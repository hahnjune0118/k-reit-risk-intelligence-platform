import pandas as pd


# Archived for future KRX-based Deals valuation module.
def build_deals_valuation_summary(latest_kpi: pd.Series, scenario: dict, market_snapshot: dict, p_nav_multiple: float, p_ffo_multiple: float, required_dividend_yield_pct: float) -> pd.DataFrame:
    nav = scenario.get("stressed_nav", latest_kpi.get("nav_mn_krw", pd.NA))
    ffo = scenario.get("stressed_ffo", latest_kpi.get("ffo_mn_krw", pd.NA))
    dividend = latest_kpi.get("common_dividend_total_mn_krw", pd.NA)
    market_cap = market_snapshot.get("market_cap_mn_krw", pd.NA) if market_snapshot else pd.NA
    rows = []
    nav_value = nav * p_nav_multiple if pd.notna(nav) else pd.NA
    ffo_value = ffo * p_ffo_multiple if pd.notna(ffo) else pd.NA
    dividend_value = dividend / (required_dividend_yield_pct / 100) if pd.notna(dividend) and required_dividend_yield_pct else pd.NA
    for method, value, explanation in [
        ("NAV 기반", nav_value, "시나리오 후 순자산가치 × 적용 P/NAV multiple"),
        ("FFO 기반", ffo_value, "시나리오 후 FFO × 적용 P/FFO multiple"),
        ("배당수익률 기반", dividend_value, "예상 배당총액 ÷ 요구 배당수익률"),
    ]:
        rows.append({
            "가치평가 방법": method,
            "추정 시장가치_백만원": value,
            "현재 시가총액 대비 차이_%": (value / market_cap - 1) * 100 if pd.notna(value) and pd.notna(market_cap) and market_cap else pd.NA,
            "계산 논리": explanation,
        })
    return pd.DataFrame(rows)


def build_deals_backtest_table(historical_panel: pd.DataFrame, p_nav_multiple: float, p_ffo_multiple: float) -> pd.DataFrame:
    if historical_panel is None or historical_panel.empty:
        return pd.DataFrame()
    df = historical_panel.copy()
    nav = pd.to_numeric(df.get("순자산가치_또는_자본", pd.Series(index=df.index, dtype="float64")), errors="coerce")
    ffo = pd.to_numeric(df.get("현금흐름_또는_이익", pd.Series(index=df.index, dtype="float64")), errors="coerce")
    mcap = pd.to_numeric(df.get("시장가치", pd.Series(index=df.index, dtype="float64")), errors="coerce")
    out = pd.DataFrame({
        "연도": df.get("year"),
        "실제시가총액_백만원": mcap,
        "NAV모델_백만원": nav * p_nav_multiple,
        "FFO모델_백만원": ffo * p_ffo_multiple,
        "기준금리_%": df.get("기준금리"),
        "P_NAV": df.get("P_NAV"),
    })
    out["NAV모델_오차율_%"] = (out["NAV모델_백만원"] / out["실제시가총액_백만원"] - 1) * 100
    out["FFO모델_오차율_%"] = (out["FFO모델_백만원"] / out["실제시가총액_백만원"] - 1) * 100
    return out.dropna(subset=["실제시가총액_백만원"], how="all")
