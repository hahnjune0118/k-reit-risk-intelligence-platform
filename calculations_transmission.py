import pandas as pd


def build_historical_panel(financials: pd.DataFrame, kpis: pd.DataFrame, macro_history: pd.DataFrame, dart_history: pd.DataFrame | None = None, krx_history: pd.DataFrame | None = None) -> pd.DataFrame:
    """Combine available REIT financials/KPIs with ECOS annual rates for a 5-year view."""
    if dart_history is not None and not dart_history.empty:
        fin = dart_history.copy()
    else:
        fin = financials.copy()
        fin["year"] = pd.to_datetime(fin["period_end"], errors="coerce").dt.year
        fin = fin.sort_values("period_end").groupby("year", as_index=False).tail(1)
    fin["year"] = pd.to_numeric(fin["year"], errors="coerce").astype("Int64")

    kpi = kpis.copy()
    kpi["year"] = pd.to_datetime(kpi["period_end"], errors="coerce").dt.year
    kpi = kpi.sort_values("period_end").groupby("year", as_index=False).tail(1)
    keep_kpi = [c for c in ["year", "ffo_mn_krw", "nav_mn_krw", "interest_coverage_x", "leverage_pct", "common_dividend_total_mn_krw"] if c in kpi.columns]
    panel = fin.merge(kpi[keep_kpi], on="year", how="outer", suffixes=("", "_kpi"))
    if macro_history is not None and not macro_history.empty:
        panel = panel.merge(macro_history, on="year", how="left")

    market_annual = pd.DataFrame()
    if krx_history is not None and not krx_history.empty:
        # Archived KRX path; not used by the public runtime.
        from api_krx import build_market_annual_history
        market_annual = build_market_annual_history(krx_history)
    if market_annual is not None and not market_annual.empty:
        panel = panel.merge(market_annual, on="year", how="left")

    for col in ["nav_mn_krw", "total_equity_mn_krw", "ffo_mn_krw", "operating_income_mn_krw", "net_income_mn_krw", "market_cap_mn_krw", "close_price_krw"]:
        if col in panel.columns:
            panel[col] = pd.to_numeric(panel[col], errors="coerce")

    panel["순자산가치_또는_자본"] = panel.get("nav_mn_krw", pd.Series(index=panel.index, dtype="float64")).combine_first(panel.get("total_equity_mn_krw", pd.Series(index=panel.index, dtype="float64")))
    panel["현금흐름_또는_이익"] = panel.get("ffo_mn_krw", pd.Series(index=panel.index, dtype="float64")).combine_first(panel.get("operating_income_mn_krw", pd.Series(index=panel.index, dtype="float64"))).combine_first(panel.get("net_income_mn_krw", pd.Series(index=panel.index, dtype="float64")))
    if "market_cap_mn_krw" in panel.columns:
        panel["시장가치"] = pd.to_numeric(panel["market_cap_mn_krw"], errors="coerce")
        panel["P_NAV"] = panel["시장가치"] / pd.to_numeric(panel["순자산가치_또는_자본"], errors="coerce")
        panel["NAV_할인율"] = (1 - panel["P_NAV"]) * 100
    if "close_price_krw" in panel.columns:
        panel["주가"] = pd.to_numeric(panel["close_price_krw"], errors="coerce")
    if "interest_bearing_debt_mn_krw" in panel.columns and "total_assets_mn_krw" in panel.columns:
        panel["부채비율_LTV추정"] = pd.to_numeric(panel["interest_bearing_debt_mn_krw"], errors="coerce") / pd.to_numeric(panel["total_assets_mn_krw"], errors="coerce") * 100
    panel = panel.sort_values("year")

    for col in ["기준금리", "국고채 3년", "회사채 AA- 3년", "순자산가치_또는_자본", "현금흐름_또는_이익", "시장가치", "주가", "P_NAV"]:
        if col in panel.columns:
            first = pd.to_numeric(panel[col], errors="coerce").dropna()
            if not first.empty and first.iloc[0] != 0:
                panel[f"{col}_index"] = panel[col] / first.iloc[0] * 100
    if "기준금리" in panel.columns:
        # Policy-rate levels are percentage values. Display changes as basis points (bp),
        # rounded to the nearest 25bp because Bank of Korea policy-rate decisions generally move in 25bp steps.
        panel["기준금리_변화_p"] = pd.to_numeric(panel["기준금리"], errors="coerce").diff()
        panel["기준금리_변화_bp_raw"] = panel["기준금리_변화_p"] * 100
        panel["기준금리_변화_bp"] = (panel["기준금리_변화_bp_raw"] / 25).round() * 25
    if "순자산가치_또는_자본" in panel.columns:
        panel["순자산가치_변화율"] = pd.to_numeric(panel["순자산가치_또는_자본"], errors="coerce").pct_change() * 100
    if "현금흐름_또는_이익" in panel.columns:
        panel["현금흐름_변화율"] = pd.to_numeric(panel["현금흐름_또는_이익"], errors="coerce").pct_change() * 100
    if "시장가치" in panel.columns:
        panel["시장가치_변화율"] = pd.to_numeric(panel["시장가치"], errors="coerce").pct_change() * 100
    if "P_NAV" in panel.columns:
        panel["P_NAV_변화"] = pd.to_numeric(panel["P_NAV"], errors="coerce").diff()
    return panel


def build_market_implied_gap_table(market_snapshot: dict, latest_nav_mn_krw, scenario: dict) -> pd.DataFrame:
    """Compare disclosed NAV, stressed NAV, market cap, and market-implied haircut."""
    rows = []
    nav = latest_nav_mn_krw
    market_cap = market_snapshot.get("market_cap_mn_krw", pd.NA) if market_snapshot.get("available") else pd.NA
    stressed_nav = nav + scenario.get("total_value_change", pd.NA) if pd.notna(nav) and pd.notna(scenario.get("total_value_change", pd.NA)) else pd.NA
    for label, nav_value in [("현재 공시 NAV", nav), ("선택 시나리오 후 NAV", stressed_nav)]:
        p_nav = market_cap / nav_value if pd.notna(market_cap) and pd.notna(nav_value) and nav_value else pd.NA
        discount = (1 - p_nav) * 100 if pd.notna(p_nav) else pd.NA
        rows.append({
            "기준": label,
            "NAV_백만원": nav_value,
            "시가총액_백만원": market_cap,
            "P_NAV": p_nav,
            "시장할인율_pct": discount,
        })
    if pd.notna(market_cap) and pd.notna(stressed_nav) and pd.notna(nav) and nav:
        model_downside = (1 - stressed_nav / nav) * 100
        market_discount = (1 - market_cap / nav) * 100 if nav else pd.NA
        excess_discount = market_discount - model_downside if pd.notna(market_discount) else pd.NA
        rows.append({
            "기준": "시장할인 - 시나리오 NAV 하락폭",
            "NAV_백만원": pd.NA,
            "시가총액_백만원": pd.NA,
            "P_NAV": pd.NA,
            "시장할인율_pct": excess_discount,
        })
    return pd.DataFrame(rows)


def interpret_market_gap(market_gap: pd.DataFrame) -> str:
    if market_gap is None or market_gap.empty or "시장할인율_pct" not in market_gap.columns:
        return "시장가격 시계열은 공개 런타임에서 비활성화되어 있습니다. v14 진단은 Tax workflow, 재무, 거시경제, Peer Benchmark 신호에 집중합니다."
    current = market_gap[market_gap["기준"] == "현재 공시 NAV"]
    stressed = market_gap[market_gap["기준"] == "선택 시나리오 후 NAV"]
    if current.empty:
        return "시장가격과 NAV를 연결할 데이터가 부족합니다."
    cur_disc = current["시장할인율_pct"].iloc[0]
    if pd.isna(cur_disc):
        return "시장가격과 NAV를 연결할 데이터가 부족합니다."
    if not stressed.empty and pd.notna(stressed["시장할인율_pct"].iloc[0]):
        st_disc = stressed["시장할인율_pct"].iloc[0]
        if cur_disc > 25 and st_disc > 10:
            return "시장은 현재 공시 NAV보다 상당히 낮은 가격을 적용하고 있습니다. 선택한 스트레스 이후에도 할인율이 남아 있다면, 시장은 단순 cap-rate 하락 외의 차환·배당·유동성 위험도 반영하고 있을 수 있습니다."
        if cur_disc < 10 and st_disc < 0:
            return "현재 시장가격은 공시 NAV 대비 할인폭이 크지 않습니다. 스트레스 NAV 기준으로는 오히려 프리미엄이 될 수 있으므로, downside 방어 논리가 충분한지 확인해야 합니다."
    if cur_disc > 25:
        return "현재 P/NAV 할인폭이 큽니다. 이는 저평가일 수도 있지만, 시장이 공시 NAV의 지속가능성이나 차환·배당위험을 의심한다는 신호일 수도 있습니다."
    if cur_disc < 0:
        return "시장가격이 공시 NAV보다 높습니다. 시장은 성장성, 배당 안정성, 스폰서 신뢰 등을 프리미엄으로 평가하고 있을 수 있습니다."
    return "현재 P/NAV 할인폭은 중간 수준입니다. 할인 원인이 금리, 차환, 자산가치, 배당 중 어디에 있는지 peer 비교가 필요합니다."


def build_macro_transmission_table(panel: pd.DataFrame) -> pd.DataFrame:
    """Create annual macro -> REIT -> market transmission diagnostics."""
    if panel is None or panel.empty:
        return pd.DataFrame()
    df = panel.copy().sort_values("year")
    required_any = ["기준금리_변화_bp", "기준금리_변화_p", "국고채 3년", "현금흐름_변화율", "순자산가치_변화율", "시장가치_변화율", "P_NAV_변화"]
    if not any(c in df.columns for c in required_any):
        return pd.DataFrame()
    out = pd.DataFrame({"연도": df["year"]})
    bp_series = df.get("기준금리_변화_bp", df.get("기준금리_변화_p", pd.Series(index=df.index, dtype="float64")) * 100)
    out["금리 국면"] = bp_series.apply(
        lambda x: "금리 상승" if pd.notna(x) and x >= 25 else ("금리 하락" if pd.notna(x) and x <= -25 else "금리 중립")
    )
    if "기준금리_변화_bp" in df.columns:
        out["기준금리 변화폭(bp)"] = df["기준금리_변화_bp"]
    if "현금흐름_변화율" in df.columns:
        out["FFO/이익 변화율(%)"] = df["현금흐름_변화율"]
    if "순자산가치_변화율" in df.columns:
        out["NAV/자본 변화율(%)"] = df["순자산가치_변화율"]
    if "시장가치_변화율" in df.columns:
        out["시가총액 변화율(%)"] = df["시장가치_변화율"]
    if "P_NAV_변화" in df.columns:
        out["P/NAV 변화"] = df["P_NAV_변화"]

    def signal(row):
        rate_up = row.get("금리 국면") == "금리 상승"
        ffo_down = pd.notna(row.get("FFO/이익 변화율(%)")) and row.get("FFO/이익 변화율(%)") < -5
        nav_down = pd.notna(row.get("NAV/자본 변화율(%)")) and row.get("NAV/자본 변화율(%)") < -5
        mcap_down = pd.notna(row.get("시가총액 변화율(%)")) and row.get("시가총액 변화율(%)") < -10
        pnav_down = pd.notna(row.get("P/NAV 변화")) and row.get("P/NAV 변화") < -0.05
        if rate_up and (ffo_down or nav_down or mcap_down or pnav_down):
            return "금리 상승 영향 의심"
        if (mcap_down or pnav_down) and not (ffo_down or nav_down):
            return "시장 선반영/심리 악화 가능"
        if (ffo_down or nav_down) and not (mcap_down or pnav_down):
            return "공시 지표 악화, 시장 반영 확인 필요"
        return "특이 신호 제한적"

    out["해석 신호"] = out.apply(signal, axis=1)
    return out.dropna(how="all", axis=1)


def build_transmission_correlation_table(panel: pd.DataFrame) -> pd.DataFrame:
    """Simple directional sensitivity diagnostics. Not causal inference."""
    if panel is None or panel.empty:
        return pd.DataFrame()
    pairs = [
        ("기준금리", "현금흐름_또는_이익", "기준금리 vs FFO/이익"),
        ("기준금리", "순자산가치_또는_자본", "기준금리 vs NAV/자본"),
        ("기준금리", "시장가치", "기준금리 vs 시가총액"),
        ("국고채 3년", "P_NAV", "국고채 3년 vs P/NAV"),
        ("회사채 AA- 3년", "시장가치", "회사채 AA- vs 시가총액"),
    ]
    rows = []
    for x, y, label in pairs:
        if x not in panel.columns or y not in panel.columns:
            continue
        temp = panel[[x, y]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(temp) < 3:
            continue
        corr = temp[x].corr(temp[y])
        if pd.isna(corr):
            continue
        if corr <= -0.5:
            interp = "강한 음의 관계: 금리 상승기 약화 가능성"
        elif corr < -0.2:
            interp = "약한 음의 관계: 금리 부담 가능성"
        elif corr >= 0.5:
            interp = "강한 양의 관계: 표본/자산편입 효과 확인 필요"
        elif corr > 0.2:
            interp = "약한 양의 관계: 단순 금리효과 외 요인 가능"
        else:
            interp = "관계 약함: 표본 수와 기타 이벤트 확인 필요"
        rows.append({"관계": label, "상관계수": corr, "표본 수": len(temp), "해석": interp})
    return pd.DataFrame(rows)


def build_transmission_narrative(transmission: pd.DataFrame, corr_table: pd.DataFrame) -> str:
    if transmission is None or transmission.empty:
        return "5년 시계열 데이터가 충분히 쌓이면 금리 변화가 리츠 재무지표와 시장가격으로 전이되는 경로를 해석할 수 있습니다."
    signals = transmission["해석 신호"].value_counts().to_dict() if "해석 신호" in transmission.columns else {}
    rate_flags = signals.get("금리 상승 영향 의심", 0)
    market_flags = signals.get("시장 선반영/심리 악화 가능", 0)
    if rate_flags >= 2:
        return "여러 연도에서 금리 상승과 리츠 지표/시장가격 약화가 같이 관찰됩니다. 이는 차입비용, cap rate, 배당여력 경로를 추가 실사해야 한다는 신호입니다."
    if market_flags >= 1:
        return "공시 NAV/FFO보다 시장가격이 먼저 약해진 구간이 있습니다. 시장이 미래 차환위험이나 평가가정 조정을 선반영했는지 확인해야 합니다."
    if corr_table is not None and not corr_table.empty and (corr_table["상관계수"] < -0.5).any():
        rel = corr_table.loc[corr_table["상관계수"].idxmin(), "관계"]
        return f"{rel}에서 비교적 강한 음의 관계가 관찰됩니다. 표본 수는 작지만, 금리 민감도를 설명하는 보조 근거로 사용할 수 있습니다."
    return "현재 표본에서는 금리와 리츠 지표 사이의 단순 관계가 뚜렷하지 않습니다. 자산 편입, 유상증자, 배당정책, 공정가치 평가가정 같은 개별 이벤트를 함께 봐야 합니다."
