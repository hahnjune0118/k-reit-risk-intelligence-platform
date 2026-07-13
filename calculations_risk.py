import re

import pandas as pd

from formatting import format_pct_from_100, format_ratio, format_years


def calculate_reit_level_risk(latest_kpi: pd.Series, debt_schedule: pd.DataFrame, assets: pd.DataFrame):
    """REITs 예비 검토용 규칙 기반 점수입니다. 정식 신용등급이 아닙니다."""
    scores = {}
    flags = []

    # Income / lease stability
    income_score = 0
    occupancy = latest_kpi.get("occupancy_pct", pd.NA)
    wale = latest_kpi.get("wale_yrs", pd.NA)
    if pd.notna(occupancy) and occupancy < 95:
        income_score += 35
        flags.append("포트폴리오 임대율 95% 미만")
    if pd.notna(wale):
        if wale < 2.0:
            income_score += 30
            flags.append("WALE 2.0년 미만")
        elif wale < 3.0:
            income_score += 15
            flags.append("WALE 3.0년 미만")
    if "single_tenant_or_master_lease" in assets.columns:
        single_tenant_share = assets[assets["single_tenant_or_master_lease"]]["appraised_value_mn_krw_20251231"].sum() / assets["appraised_value_mn_krw_20251231"].sum()
        if single_tenant_share > 0.65:
            income_score += 20
            flags.append("평가액 기준 마스터리스 또는 단일 임차인 노출 높음")
    scores["Income / Lease Stability Risk"] = min(income_score, 100)

    # Refinancing / debt service
    debt_score = 0
    leverage = latest_kpi.get("leverage_pct", pd.NA)
    icr = latest_kpi.get("interest_coverage_x", pd.NA)
    avg_rate = latest_kpi.get("avg_borrowing_rate_pct", pd.NA)
    wam = latest_kpi.get("debt_weighted_average_maturity_yrs", pd.NA)
    fixed_pct = latest_kpi.get("fixed_rate_debt_pct", pd.NA)

    if pd.notna(leverage):
        if leverage >= 55:
            debt_score += 30
            flags.append("부채비율 55% 이상")
        elif leverage >= 50:
            debt_score += 15
            flags.append("부채비율 50% 이상")
    if pd.notna(icr):
        if icr < 2.0:
            debt_score += 30
            flags.append("FFO 이자감당력 proxy 2.0배 미만")
        elif icr < 2.5:
            debt_score += 20
            flags.append("FFO 이자감당력 proxy 2.5배 미만")
    if pd.notna(wam):
        if wam < 1.5:
            debt_score += 25
            flags.append("차입금 가중평균 만기 1.5년 미만")
        elif wam < 2.0:
            debt_score += 15
            flags.append("차입금 가중평균 만기 2.0년 미만")
    if pd.notna(fixed_pct) and fixed_pct < 50:
        debt_score += 15
        flags.append("고정금리 차입금 비중 50% 미만")
    if pd.notna(avg_rate) and avg_rate > 4.5:
        debt_score += 10
        flags.append("기말잔액 기준 차입비용률 proxy 4.5% 초과")

    near_term_debt = debt_schedule[debt_schedule["days_to_maturity"].between(0, 365, inclusive="both")]["principal_mn_krw"].sum()
    total_debt = debt_schedule["principal_mn_krw"].sum()
    near_term_share = near_term_debt / total_debt if total_debt else 0
    if near_term_share > 0.25:
        debt_score += 20
        flags.append("공시 차입금의 25% 초과가 1년 내 만기")
    scores["Refinancing / Debt Service Risk"] = min(debt_score, 100)

    # Valuation / NAV risk
    valuation_score = 0
    uplift = assets["value_uplift_pct"].mean()
    cap_rate_mean = assets["cap_rate_pct_20251231"].mean()
    if pd.notna(cap_rate_mean) and cap_rate_mean < 4.0:
        valuation_score += 20
        flags.append("평균 자산 Cap rate 4% 미만")
    if pd.notna(uplift) and uplift > 20:
        valuation_score += 15
        flags.append("취득가 대비 평균 평가상승률 20% 초과")
    office_share = assets[assets["asset_type"].str.contains("office", case=False, na=False)]["appraised_value_mn_krw_20251231"].sum() / assets["appraised_value_mn_krw_20251231"].sum()
    if office_share > 0.65:
        valuation_score += 10
        flags.append("오피스 자산 집중도 높음")
    scores["Valuation / NAV Sensitivity Risk"] = min(valuation_score, 100)

    # Data quality / basis risk
    data_score = 0
    derived_rent_count = assets["estimated_annual_rent_mn_krw"].astype(str).str.contains("derived", case=False, na=False).sum()
    missing_nla_count = assets["nla_or_leasable_area_sqm"].isna().sum()
    if derived_rent_count > 0:
        data_score += min(derived_rent_count * 10, 40)
        flags.append("일부 자산별 연 임대수익이 직접 공시값이 아닌 추정치")
    if missing_nla_count > 0:
        data_score += min(missing_nla_count * 5, 25)
        flags.append("일부 자산의 임대가능면적 정보 부족")
    data_score += 15
    flags.append("투자보고서 KPI와 연결 K-IFRS 수치는 기준이 서로 다름")
    scores["Disclosure / Data Basis Risk"] = min(data_score, 100)

    total_score = (
        scores["Income / Lease Stability Risk"] * 0.25
        + scores["Refinancing / Debt Service Risk"] * 0.35
        + scores["Valuation / NAV Sensitivity Risk"] * 0.25
        + scores["Disclosure / Data Basis Risk"] * 0.15
    )

    if total_score >= 70:
        level = "High"
    elif total_score >= 40:
        level = "Medium"
    else:
        level = "Low"

    return scores, total_score, level, flags


def add_score_rule(rows, category, driver, triggered, score_delta, weight, current_value="", threshold="", interpretation=""):
    """점수 산정 원인을 표 형태로 남깁니다."""
    rows.append({
        "risk_category": category,
        "driver": driver,
        "triggered": bool(triggered),
        "score_delta": float(score_delta) if triggered else 0.0,
        "weight_pct": weight * 100,
        "weighted_score_delta": (float(score_delta) * weight) if triggered else 0.0,
        "current_value": current_value,
        "threshold": threshold,
        "interpretation": interpretation,
    })


def build_reit_score_decomposition(latest_kpi: pd.Series, debt_schedule: pd.DataFrame, assets: pd.DataFrame) -> pd.DataFrame:
    """REITs 수준 규칙 기반 점수의 산정 원인을 설명합니다."""
    rows = []
    weights = {
        "Income / Lease Stability Risk": 0.25,
        "Refinancing / Debt Service Risk": 0.35,
        "Valuation / NAV Sensitivity Risk": 0.25,
        "Disclosure / Data Basis Risk": 0.15,
    }

    occupancy = latest_kpi.get("occupancy_pct", pd.NA)
    wale = latest_kpi.get("wale_yrs", pd.NA)
    single_tenant_share = pd.NA
    total_asset_value = assets["appraised_value_mn_krw_20251231"].sum()
    if "single_tenant_or_master_lease" in assets.columns and total_asset_value:
        single_tenant_share = (
            assets.loc[assets["single_tenant_or_master_lease"], "appraised_value_mn_krw_20251231"].sum()
            / total_asset_value
            * 100
        )

    add_score_rule(
        rows,
        "Income / Lease Stability Risk",
        "포트폴리오 임대율 95% 미만",
        pd.notna(occupancy) and occupancy < 95,
        35,
        weights["Income / Lease Stability Risk"],
        format_pct_from_100(occupancy),
        "< 95.0%",
        "임대율 하락은 반복 임대수익을 약화시키고 재임대 위험을 높입니다.",
    )
    add_score_rule(
        rows,
        "Income / Lease Stability Risk",
        "WALE 2.0년 미만",
        pd.notna(wale) and wale < 2.0,
        30,
        weights["Income / Lease Stability Risk"],
        format_years(wale),
        "< 2.0년",
        "WALE가 짧으면 단기 임대차 갱신 위험이 커지고 수익 예측 가능성이 낮아집니다.",
    )
    add_score_rule(
        rows,
        "Income / Lease Stability Risk",
        "WALE 2.0년 이상 3.0년 미만",
        pd.notna(wale) and 2.0 <= wale < 3.0,
        15,
        weights["Income / Lease Stability Risk"],
        format_years(wale),
        "2.0년 이상 3.0년 미만",
        "즉시 위험은 아니지만 주요 임차인의 갱신 가능성을 계속 모니터링해야 합니다.",
    )
    add_score_rule(
        rows,
        "Income / Lease Stability Risk",
        "마스터리스 또는 단일 임차인 노출 65% 초과",
        pd.notna(single_tenant_share) and single_tenant_share > 65,
        20,
        weights["Income / Lease Stability Risk"],
        format_pct_from_100(single_tenant_share),
        "> 65.0%",
        "우량 임차인이라도 집중도가 높으면 거래상대방 의존도와 재협상 리스크가 커집니다.",
    )

    leverage = latest_kpi.get("leverage_pct", pd.NA)
    icr = latest_kpi.get("interest_coverage_x", pd.NA)
    avg_rate = latest_kpi.get("avg_borrowing_rate_pct", pd.NA)
    wam = latest_kpi.get("debt_weighted_average_maturity_yrs", pd.NA)
    fixed_pct = latest_kpi.get("fixed_rate_debt_pct", pd.NA)
    total_debt = debt_schedule["principal_mn_krw"].sum()
    near_term_debt = debt_schedule[debt_schedule["days_to_maturity"].between(0, 365, inclusive="both")]["principal_mn_krw"].sum()
    near_term_share = near_term_debt / total_debt * 100 if total_debt else pd.NA

    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "부채비율 55% 이상",
        pd.notna(leverage) and leverage >= 55,
        30,
        weights["Refinancing / Debt Service Risk"],
        format_pct_from_100(leverage),
        ">= 55.0%",
        "부채비율이 높으면 자기자본 완충력이 줄고 Cap rate 상승 및 차환 조건 악화에 더 민감해집니다.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "부채비율 50% 이상 55% 미만",
        pd.notna(leverage) and 50 <= leverage < 55,
        15,
        weights["Refinancing / Debt Service Risk"],
        format_pct_from_100(leverage),
        "50.0% 이상 55.0% 미만",
        "중간 수준의 차입 부담이 있으므로 차환 조건과 담보여력을 모니터링해야 합니다.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "FFO 이자감당력 proxy 2.0배 미만",
        pd.notna(icr) and icr < 2.0,
        30,
        weights["Refinancing / Debt Service Risk"],
        format_ratio(icr),
        "< 2.0x",
        "FFO 이자감당력 proxy가 낮으면 금리 상승 시 차입금 이자 부담을 흡수할 여력이 제한됩니다.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "FFO 이자감당력 proxy 2.0배 이상 2.5배 미만",
        pd.notna(icr) and 2.0 <= icr < 2.5,
        20,
        weights["Refinancing / Debt Service Risk"],
        format_ratio(icr),
        "2.0배 이상 2.5배 미만",
        "현재는 감당 가능해도 차환 스프레드 확대나 FFO 하락에 노출됩니다.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "차입금 가중평균 만기 1.5년 미만",
        pd.notna(wam) and wam < 1.5,
        25,
        weights["Refinancing / Debt Service Risk"],
        format_years(wam),
        "< 1.5년",
        "만기가 짧으면 단기 차환 부담이 집중될 수 있습니다.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "차입금 가중평균 만기 1.5년 이상 2.0년 미만",
        pd.notna(wam) and 1.5 <= wam < 2.0,
        15,
        weights["Refinancing / Debt Service Risk"],
        format_years(wam),
        "1.5년 이상 2.0년 미만",
        "만기 구조를 분산하고 차환 일정 관리를 강화해야 합니다.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "고정금리 차입금 비중 50% 미만",
        pd.notna(fixed_pct) and fixed_pct < 50,
        15,
        weights["Refinancing / Debt Service Risk"],
        format_pct_from_100(fixed_pct),
        "< 50.0%",
        "고정금리 보호가 낮으면 시장금리 변동에 따른 이자비용 변동성이 커집니다.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "기말잔액 기준 차입비용률 proxy 4.5% 초과",
        pd.notna(avg_rate) and avg_rate > 4.5,
        10,
        weights["Refinancing / Debt Service Risk"],
        format_pct_from_100(avg_rate),
        "> 4.5%",
        "차입비용이 높으면 FFO와 배당 여력이 줄어들 수 있습니다.",
    )
    add_score_rule(
        rows,
        "Refinancing / Debt Service Risk",
        "공시 차입금의 25% 초과가 1년 내 만기",
        pd.notna(near_term_share) and near_term_share > 25,
        20,
        weights["Refinancing / Debt Service Risk"],
        format_pct_from_100(near_term_share),
        "> 25.0%",
        "1년 내 만기가 집중되면 신용시장 변동성이 큰 상황에서 차환 실행 위험이 커집니다.",
    )

    uplift = assets["value_uplift_pct"].mean()
    cap_rate_mean = assets["cap_rate_pct_20251231"].mean()
    office_share = pd.NA
    if total_asset_value:
        office_share = (
            assets.loc[assets["asset_type"].str.contains("office", case=False, na=False), "appraised_value_mn_krw_20251231"].sum()
            / total_asset_value
            * 100
        )

    add_score_rule(
        rows,
        "Valuation / NAV Sensitivity Risk",
        "평균 자산 Cap rate 4% 미만",
        pd.notna(cap_rate_mean) and cap_rate_mean < 4.0,
        20,
        weights["Valuation / NAV Sensitivity Risk"],
        format_pct_from_100(cap_rate_mean),
        "< 4.0%",
        "낮은 Cap rate proxy는 가치 민감도가 높다는 뜻이며, 수익률 상승 시 장부NAV proxy 하락 폭이 커질 수 있습니다.",
    )
    add_score_rule(
        rows,
        "Valuation / NAV Sensitivity Risk",
        "취득가 대비 평균 평가상승률 20% 초과",
        pd.notna(uplift) and uplift > 20,
        15,
        weights["Valuation / NAV Sensitivity Risk"],
        format_pct_from_100(uplift),
        "> 20.0%",
        "큰 평가상승은 임대료 상승, 임차인 신용도, 위험프리미엄 하락 등으로 설명되어야 합니다.",
    )
    add_score_rule(
        rows,
        "Valuation / NAV Sensitivity Risk",
        "오피스 자산 평가액 비중 65% 초과",
        pd.notna(office_share) and office_share > 65,
        10,
        weights["Valuation / NAV Sensitivity Risk"],
        format_pct_from_100(office_share),
        "> 65.0%",
        "오피스 집중도는 권역별 공실, 임대료 스프레드, Cap rate 사이클 위험에 대한 노출을 높입니다.",
    )

    derived_rent_count = assets["estimated_annual_rent_mn_krw"].astype(str).str.contains("derived", case=False, na=False).sum()
    missing_nla_count = assets["nla_or_leasable_area_sqm"].isna().sum()
    add_score_rule(
        rows,
        "Disclosure / Data Basis Risk",
        "자산별 연 임대수익이 직접 공시값이 아닌 추정치",
        derived_rent_count > 0,
        min(derived_rent_count * 10, 40),
        weights["Disclosure / Data Basis Risk"],
        f"{derived_rent_count}개 자산",
        "> 0",
        "추정 임대수익은 예비 분석에는 유용하지만, 정식 검토 전 원천 공시자료와 대사해야 합니다.",
    )
    add_score_rule(
        rows,
        "Disclosure / Data Basis Risk",
        "임대가능면적 정보가 명시되지 않은 자산 존재",
        missing_nla_count > 0,
        min(missing_nla_count * 5, 25),
        weights["Disclosure / Data Basis Risk"],
        f"{missing_nla_count}개 자산",
        "> 0",
        "임대가능면적이 없으면 면적당 임대료, 생산성, 비교가능성 분석이 약해집니다.",
    )
    add_score_rule(
        rows,
        "Disclosure / Data Basis Risk",
        "투자보고서 KPI와 연결 K-IFRS 수치의 기준 차이",
        True,
        15,
        weights["Disclosure / Data Basis Risk"],
        "항상 확인 필요",
        "기준 차이 존재",
        "서로 다른 기준의 비율은 예비 신호일 뿐이며 정식 사용 전 대사가 필요합니다.",
    )

    out = pd.DataFrame(rows)
    out["category_score"] = out.groupby("risk_category")["score_delta"].transform("sum").clip(upper=100)
    out["category_weighted_score"] = out.groupby("risk_category")["weighted_score_delta"].transform("sum")
    out["trigger_status"] = out["triggered"].map({True: "해당", False: "미해당"})
    return out


def build_asset_score_decomposition(asset_row: pd.Series) -> pd.DataFrame:
    """자산별 위험 점수 산정 원인을 설명합니다."""
    rows = []

    def add(driver, triggered, score_delta, current_value="", threshold="", interpretation=""):
        rows.append({
            "driver": driver,
            "triggered": bool(triggered),
            "score_delta": float(score_delta) if triggered else 0.0,
            "current_value": current_value,
            "threshold": threshold,
            "interpretation": interpretation,
        })

    add(
        "단일 임차인 또는 마스터리스 집중",
        str(asset_row.get("tenant_concentration_pct", "")).lower().find("100") >= 0 or str(asset_row.get("tenant_concentration_pct", "")).lower().find("master") >= 0,
        20,
        str(asset_row.get("tenant_concentration_pct", "N/A")),
        "100% 또는 마스터리스 문구",
        "우량 임차인이라도 거래상대방 집중위험은 남습니다.",
    )
    add(
        "복합·리테일·주유소 등 자산 유형",
        bool(pd.notna(asset_row.get("asset_type")) and re.search("mixed|retail|gas", str(asset_row.get("asset_type")), flags=re.IGNORECASE)),
        15,
        str(asset_row.get("asset_type", "N/A")),
        "복합, 리테일, 주유소 포함",
        "오피스가 아닌 자산은 임대차 조건과 대체사용 가능성을 별도로 확인할 필요가 있습니다.",
    )
    add(
        "WALE 3년 미만",
        pd.notna(asset_row.get("wale_yrs")) and asset_row["wale_yrs"] < 3,
        25,
        format_years(asset_row.get("wale_yrs")),
        "< 3.0년",
        "잔여 임대차기간이 짧으면 갱신과 임대료 조정 위험이 커집니다.",
    )
    add(
        "Cap rate 4% 미만",
        pd.notna(asset_row.get("cap_rate_pct_20251231")) and asset_row["cap_rate_pct_20251231"] < 4.0,
        15,
        format_pct_from_100(asset_row.get("cap_rate_pct_20251231")),
        "< 4.0%",
        "낮은 Cap rate는 가치 민감도가 높다는 신호입니다.",
    )
    add(
        "평가상승률 25% 초과",
        pd.notna(asset_row.get("value_uplift_pct")) and asset_row["value_uplift_pct"] > 25,
        10,
        format_pct_from_100(asset_row.get("value_uplift_pct")),
        "> 25.0%",
        "큰 평가상승은 임대료, Cap rate, 자산 품질 증거와 연결해 확인해야 합니다.",
    )
    add(
        "연 임대수익이 추정치",
        str(asset_row.get("estimated_annual_rent_mn_krw", "")).lower().find("derived") >= 0,
        15,
        str(asset_row.get("estimated_annual_rent_mn_krw", "N/A")),
        "derived 문구 포함",
        "추정 임대수익은 원 공시자료 또는 평가보고서 근거와 대사해야 합니다.",
    )

    out = pd.DataFrame(rows)
    out["trigger_status"] = out["triggered"].map({True: "해당", False: "미해당"})
    out["asset_risk_score_recomputed"] = min(float(out["score_delta"].sum()), 100.0)
    return out


def build_asset_risk_table(assets: pd.DataFrame) -> pd.DataFrame:
    df = assets.copy()
    if df.empty:
        df["asset_risk_score"] = pd.Series(dtype="float64")
        df["asset_risk_level"] = pd.Series(dtype="object")
        return df
    df["asset_risk_score"] = 0

    # High tenant concentration is stable when credit is strong but concentration still matters for DD.
    df.loc[df["tenant_concentration_pct"].astype(str).str.contains("100|master", case=False, na=False), "asset_risk_score"] += 20
    df.loc[df["asset_type"].str.contains("mixed|retail|gas", case=False, na=False), "asset_risk_score"] += 15
    df.loc[df["wale_yrs"].fillna(99) < 3, "asset_risk_score"] += 25
    df.loc[df["cap_rate_pct_20251231"].fillna(0) < 4.0, "asset_risk_score"] += 15
    df.loc[df["value_uplift_pct"].fillna(0) > 25, "asset_risk_score"] += 10
    df.loc[df["estimated_annual_rent_mn_krw"].astype(str).str.contains("derived", case=False, na=False), "asset_risk_score"] += 15
    df["asset_risk_score"] = df["asset_risk_score"].clip(upper=100)
    df["asset_risk_level"] = pd.cut(
        df["asset_risk_score"],
        bins=[-1, 39, 69, 100],
        labels=["Low", "Medium", "High"],
    ).astype(str)
    return df


def build_debt_stress_table(latest_kpi: pd.Series, debt_schedule: pd.DataFrame) -> pd.DataFrame:
    principal = debt_schedule["principal_mn_krw"].sum()
    floating = debt_schedule.loc[debt_schedule["rate_type"] == "변동", "principal_mn_krw"].sum()
    fixed = debt_schedule.loc[debt_schedule["rate_type"] == "고정", "principal_mn_krw"].sum()
    base_rate = latest_kpi.get("avg_borrowing_rate_pct", pd.NA) / 100
    ffo = latest_kpi.get("ffo_mn_krw", pd.NA)
    icr = latest_kpi.get("interest_coverage_x", pd.NA)
    base_interest = principal * base_rate if pd.notna(base_rate) else pd.NA

    rows = []
    for name, add_bp, affected in [
        ("Base", 0.00, "none"),
        ("Floating debt +100bp", 0.01, "floating"),
        ("All refinancing +100bp", 0.01, "all"),
        ("All refinancing +200bp", 0.02, "all"),
    ]:
        if affected == "none":
            incremental_interest = 0
        elif affected == "floating":
            incremental_interest = floating * add_bp
        else:
            incremental_interest = principal * add_bp

        stressed_interest = base_interest + incremental_interest if pd.notna(base_interest) else pd.NA
        ffo_after_incremental_interest = ffo - incremental_interest if pd.notna(ffo) else pd.NA
        rows.append({
            "scenario": name,
            "total_principal_mn_krw": principal,
            "fixed_principal_mn_krw": fixed,
            "floating_principal_mn_krw": floating,
            "base_avg_rate_pct": latest_kpi.get("avg_borrowing_rate_pct", pd.NA),
            "incremental_interest_mn_krw": incremental_interest,
            "stressed_interest_mn_krw": stressed_interest,
            "reported_interest_coverage_x": icr,
            "ffo_mn_krw": ffo,
            "ffo_after_incremental_interest_mn_krw": ffo_after_incremental_interest,
            "ffo_decline_pct": incremental_interest / ffo * 100 if pd.notna(ffo) and ffo else pd.NA,
        })

    return pd.DataFrame(rows)



def build_custom_stress_table(latest_kpi: pd.Series, debt_schedule: pd.DataFrame, rate_shock_bp: int, refinancing_share_pct: float, ffo_haircut_pct: float) -> pd.DataFrame:
    """User-controlled debt stress. Values are in mn KRW and percentage-point units."""
    principal = debt_schedule["principal_mn_krw"].sum()
    floating = debt_schedule.loc[debt_schedule["rate_type"] == "변동", "principal_mn_krw"].sum()
    ffo = latest_kpi.get("ffo_mn_krw", pd.NA)
    current_icr = latest_kpi.get("interest_coverage_x", pd.NA)
    avg_rate = latest_kpi.get("avg_borrowing_rate_pct", pd.NA) / 100
    base_interest = principal * avg_rate if pd.notna(avg_rate) else pd.NA

    rate_shock = rate_shock_bp / 10_000
    refinancing_principal = principal * refinancing_share_pct / 100
    stressed_principal = floating + refinancing_principal
    incremental_interest = stressed_principal * rate_shock
    ffo_after_operating_haircut = ffo * (1 - ffo_haircut_pct / 100) if pd.notna(ffo) else pd.NA
    stressed_ffo = ffo_after_operating_haircut - incremental_interest if pd.notna(ffo_after_operating_haircut) else pd.NA
    stressed_interest = base_interest + incremental_interest if pd.notna(base_interest) else pd.NA
    estimated_stressed_icr = stressed_ffo / stressed_interest if pd.notna(stressed_ffo) and pd.notna(stressed_interest) and stressed_interest else pd.NA

    rows = [
        {
            "scenario": "Current disclosed baseline",
            "rate_shock_bp": 0,
            "refinancing_share_pct": 0,
            "ffo_haircut_pct": 0,
            "affected_principal_mn_krw": 0,
            "incremental_interest_mn_krw": 0,
            "ffo_after_haircut_and_interest_mn_krw": ffo,
            "estimated_interest_coverage_x": current_icr,
        },
        {
            "scenario": "User-defined stress",
            "rate_shock_bp": rate_shock_bp,
            "refinancing_share_pct": refinancing_share_pct,
            "ffo_haircut_pct": ffo_haircut_pct,
            "affected_principal_mn_krw": stressed_principal,
            "incremental_interest_mn_krw": incremental_interest,
            "ffo_after_haircut_and_interest_mn_krw": stressed_ffo,
            "estimated_interest_coverage_x": estimated_stressed_icr,
        },
    ]
    return pd.DataFrame(rows)



def build_interactive_scenario_outputs(
    latest_kpi: pd.Series,
    debt_schedule: pd.DataFrame,
    assets: pd.DataFrame,
    rate_shock_bp: int,
    refinancing_share_pct: float,
    ffo_haircut_pct: float,
    cap_rate_shock_bp: int,
    scenario_metadata: dict | None = None,
) -> dict:
    """Build scenario outputs for FFO proxy, ICR, dividend cushion, book NAV proxy and cap-rate sensitivity."""
    principal = debt_schedule["principal_mn_krw"].sum()
    floating = debt_schedule.loc[debt_schedule["rate_type"] == "변동", "principal_mn_krw"].sum()
    avg_rate_pct = latest_kpi.get("avg_borrowing_rate_pct", pd.NA)
    reported_icr = latest_kpi.get("interest_coverage_x", pd.NA)
    base_ffo = latest_kpi.get("ffo_mn_krw", pd.NA)
    base_nav = latest_kpi.get("nav_mn_krw", pd.NA)
    common_dividend = latest_kpi.get("common_dividend_total_mn_krw", pd.NA)

    # Use disclosed interest coverage when possible because it ties directly to reported KPI basis.
    if pd.notna(base_ffo) and pd.notna(reported_icr) and reported_icr:
        base_interest = base_ffo / reported_icr
        interest_basis = "FFO 이자감당력 proxy"
    elif pd.notna(avg_rate_pct):
        base_interest = principal * avg_rate_pct / 100
        interest_basis = "기말잔액 기준 차입비용률 proxy"
    else:
        base_interest = pd.NA
        interest_basis = "확인 불가"

    affected_refi_principal = principal * refinancing_share_pct / 100
    affected_principal = floating + affected_refi_principal
    incremental_interest = affected_principal * rate_shock_bp / 10_000

    operating_ffo_loss = base_ffo * ffo_haircut_pct / 100 if pd.notna(base_ffo) else pd.NA
    stressed_ffo = base_ffo - operating_ffo_loss - incremental_interest if pd.notna(base_ffo) and pd.notna(operating_ffo_loss) else pd.NA
    stressed_interest = base_interest + incremental_interest if pd.notna(base_interest) else pd.NA
    stressed_icr = stressed_ffo / stressed_interest if pd.notna(stressed_ffo) and pd.notna(stressed_interest) and stressed_interest else pd.NA

    base_payout = common_dividend / base_ffo * 100 if pd.notna(common_dividend) and pd.notna(base_ffo) and base_ffo else pd.NA
    stressed_payout = common_dividend / stressed_ffo * 100 if pd.notna(common_dividend) and pd.notna(stressed_ffo) and stressed_ffo > 0 else pd.NA
    dividend_cushion = stressed_ffo - common_dividend if pd.notna(common_dividend) and pd.notna(stressed_ffo) else pd.NA

    asset_cols = [
        "asset_name",
        "asset_type",
        "appraised_value_mn_krw_20251231",
        "cap_rate_pct_20251231",
        "source_confidence",
    ]
    asset_sensitivity = assets[[col for col in asset_cols if col in assets.columns]].copy()
    for col in asset_cols:
        if col not in asset_sensitivity.columns:
            asset_sensitivity[col] = pd.Series(dtype="object")

    if asset_sensitivity.empty:
        for col in [
            "current_noi_proxy_mn_krw",
            "stressed_cap_rate_pct",
            "value_under_cap_rate_shock_mn_krw",
            "value_change_mn_krw",
            "value_change_pct",
        ]:
            asset_sensitivity[col] = pd.Series(dtype="float64")
        total_appraised_value = pd.NA
        total_value_change = pd.NA
        stressed_nav = pd.NA
        nav_change_pct = pd.NA
        base_ltv_proxy = latest_kpi.get("leverage_pct", pd.NA)
        stressed_ltv_proxy = pd.NA
    else:
        asset_sensitivity["current_noi_proxy_mn_krw"] = (
            asset_sensitivity["appraised_value_mn_krw_20251231"]
            * asset_sensitivity["cap_rate_pct_20251231"]
            / 100
        )
        asset_sensitivity["stressed_cap_rate_pct"] = asset_sensitivity["cap_rate_pct_20251231"] + cap_rate_shock_bp / 100
        asset_sensitivity["value_under_cap_rate_shock_mn_krw"] = (
            asset_sensitivity["current_noi_proxy_mn_krw"]
            / (asset_sensitivity["stressed_cap_rate_pct"] / 100)
        )
        asset_sensitivity["value_change_mn_krw"] = (
            asset_sensitivity["value_under_cap_rate_shock_mn_krw"]
            - asset_sensitivity["appraised_value_mn_krw_20251231"]
        )
        asset_sensitivity["value_change_pct"] = (
            asset_sensitivity["value_change_mn_krw"]
            / asset_sensitivity["appraised_value_mn_krw_20251231"]
            * 100
        )

        total_appraised_value = asset_sensitivity["appraised_value_mn_krw_20251231"].sum()
        total_value_change = asset_sensitivity["value_change_mn_krw"].sum()
        stressed_asset_value = total_appraised_value + total_value_change
        stressed_nav = base_nav + total_value_change if pd.notna(base_nav) else pd.NA
        nav_change_pct = total_value_change / base_nav * 100 if pd.notna(base_nav) and base_nav else pd.NA
        base_ltv_proxy = principal / total_appraised_value * 100 if total_appraised_value else latest_kpi.get("leverage_pct", pd.NA)
        stressed_ltv_proxy = principal / stressed_asset_value * 100 if stressed_asset_value else pd.NA

    ffo_bridge = pd.DataFrame([
        {"step": "현재 FFO proxy", "mn_krw": base_ffo, "display_order": 1},
        {"step": "FFO proxy stress", "mn_krw": -operating_ffo_loss, "display_order": 2},
        {"step": "추가 이자비용", "mn_krw": -incremental_interest, "display_order": 3},
        {"step": "시나리오 후 FFO proxy", "mn_krw": stressed_ffo, "display_order": 4},
    ])

    kpi_summary = pd.DataFrame([
        {"metric": "FFO", "baseline": base_ffo, "stressed": stressed_ffo, "unit": "mn KRW"},
        {"metric": "Interest coverage", "baseline": reported_icr, "stressed": stressed_icr, "unit": "x"},
        {"metric": "Dividend payout", "baseline": base_payout, "stressed": stressed_payout, "unit": "%"},
        {"metric": "NAV", "baseline": base_nav, "stressed": stressed_nav, "unit": "mn KRW"},
        {"metric": "LTV proxy", "baseline": base_ltv_proxy, "stressed": stressed_ltv_proxy, "unit": "%"},
    ])
    scenario_label = (scenario_metadata or {}).get("selected_scenario", "사용자 정의 시나리오")
    valuation_note = f"좌측 사이드바 '{scenario_label}'의 Cap rate +{cap_rate_shock_bp}bp 가정에서 계산"

    return {
        "scenario_label": scenario_label,
        "valuation_scenario_note": valuation_note,
        "rate_shock_bp": rate_shock_bp,
        "refinancing_share_pct": refinancing_share_pct,
        "ffo_haircut_pct": ffo_haircut_pct,
        "cap_rate_shock_bp": cap_rate_shock_bp,
        "policy_rate_change_bp": (scenario_metadata or {}).get("policy_rate_change_bp", pd.NA),
        "credit_spread_change_bp": (scenario_metadata or {}).get("credit_spread_change_bp", pd.NA),
        "rate_shock_formula": (scenario_metadata or {}).get("rate_shock_formula", "기준금리 변화 + 추가 신용스프레드 변화"),
        "affected_debt_basis": "변동금리 차입금 + 차환 대상 이자부 차입부채",
        "base_ffo": base_ffo,
        "stressed_ffo": stressed_ffo,
        "ffo_decline_pct": (stressed_ffo / base_ffo - 1) * 100 if pd.notna(stressed_ffo) and pd.notna(base_ffo) and base_ffo else pd.NA,
        "operating_ffo_loss": operating_ffo_loss,
        "incremental_interest": incremental_interest,
        "base_interest": base_interest,
        "stressed_interest": stressed_interest,
        "interest_basis": interest_basis,
        "reported_icr": reported_icr,
        "stressed_icr": stressed_icr,
        "base_payout": base_payout,
        "stressed_payout": stressed_payout,
        "dividend_cushion": dividend_cushion,
        "base_nav": base_nav,
        "stressed_nav": stressed_nav,
        "total_value_change": total_value_change,
        "nav_change_pct": nav_change_pct,
        "base_ltv_proxy": base_ltv_proxy,
        "stressed_ltv_proxy": stressed_ltv_proxy,
        "asset_sensitivity": asset_sensitivity,
        "ffo_bridge": ffo_bridge,
        "kpi_summary": kpi_summary,
    }


def scenario_verdict(scenario: dict) -> tuple[str, str, str]:
    """Return an easy-to-read traffic-light verdict for beginner users."""
    stressed_ffo = scenario.get("stressed_ffo", pd.NA)
    stressed_icr = scenario.get("stressed_icr", pd.NA)
    stressed_payout = scenario.get("stressed_payout", pd.NA)
    nav_change_pct = scenario.get("nav_change_pct", pd.NA)

    red_flags = []
    yellow_flags = []

    if pd.notna(stressed_ffo) and stressed_ffo <= 0:
        red_flags.append("시나리오 후 현금흐름이 음수로 전환")
    if pd.notna(stressed_icr):
        if stressed_icr < 1.5:
            red_flags.append("FFO 이자감당력 proxy가 1.5배 미만으로 하락")
        elif stressed_icr < 2.0:
            yellow_flags.append("FFO 이자감당력 proxy가 2.0배 미만으로 하락")
    if pd.notna(stressed_payout):
        if stressed_payout > 100:
            red_flags.append("배당금이 시나리오 후 현금흐름을 초과")
        elif stressed_payout > 85:
            yellow_flags.append("배당 부담률이 높아짐")
    if pd.notna(nav_change_pct):
        if nav_change_pct <= -15:
            red_flags.append("장부NAV proxy 하락폭이 15% 초과")
        elif nav_change_pct <= -8:
            yellow_flags.append("장부NAV proxy 하락폭이 8% 초과")

    if red_flags:
        return "압박이 큼", "High", "; ".join(red_flags)
    if yellow_flags:
        return "주의 필요", "Medium", "; ".join(yellow_flags)
    return "현재 시나리오에서는 비교적 안정", "Low", "주요 경고 기준을 넘지 않았습니다."


def build_asset_concentration_table(assets: pd.DataFrame) -> pd.DataFrame:
    df = assets.copy()
    if df.empty:
        return df
    total_value = df["appraised_value_mn_krw_20251231"].sum()
    df["portfolio_value_share_pct"] = df["appraised_value_mn_krw_20251231"] / total_value * 100
    df["hhi_component"] = (df["portfolio_value_share_pct"] / 100) ** 2
    df["rank_by_value"] = df["appraised_value_mn_krw_20251231"].rank(ascending=False, method="dense").astype(int)
    return df.sort_values("appraised_value_mn_krw_20251231", ascending=False)


def build_tenant_exposure_table(assets: pd.DataFrame) -> pd.DataFrame:
    df = assets.copy()
    if df.empty:
        return pd.DataFrame(columns=["major_tenant", "tenant_credit", "appraised_value_mn_krw_20251231", "portfolio_value_share_pct"])
    total_value = df["appraised_value_mn_krw_20251231"].sum()
    tenant = (
        df.groupby(["major_tenant", "tenant_credit"], dropna=False)["appraised_value_mn_krw_20251231"]
        .sum()
        .reset_index()
        .sort_values("appraised_value_mn_krw_20251231", ascending=False)
    )
    tenant["portfolio_value_share_pct"] = tenant["appraised_value_mn_krw_20251231"] / total_value * 100
    return tenant


def build_watchlist(asset_risk: pd.DataFrame, debt_schedule: pd.DataFrame, latest_kpi: pd.Series) -> pd.DataFrame:
    rows = []
    for _, row in asset_risk.iterrows():
        reasons = []
        if row.get("asset_risk_score", 0) >= 40:
            reasons.append("자산 위험점수 40 이상")
        if pd.notna(row.get("wale_yrs")) and row["wale_yrs"] < 2.0:
            reasons.append("WALE 짧음")
        if pd.notna(row.get("cap_rate_pct_20251231")) and row["cap_rate_pct_20251231"] < 4.0:
            reasons.append("낮은 Cap rate / 가치평가 민감도")
        if str(row.get("tenant_concentration_pct", "")).lower().find("100") >= 0:
            reasons.append("단일 임차인 또는 마스터리스 집중")
        if str(row.get("estimated_annual_rent_mn_krw", "")).lower().find("derived") >= 0:
            reasons.append("임대수익이 Cap rate 표시값에서 역산된 추정치")

        if reasons:
            rows.append({
                "watch_item": row["asset_name"],
                "category": "자산 / 임대차",
                "priority_score": min(row.get("asset_risk_score", 0) + len(reasons) * 5, 100),
                "why_it_matters": "; ".join(reasons),
                "recommended_next_step": "원 임대차 스케줄, 임차인 신용도, 평가가정, 갱신 옵션의 경제성을 확인합니다.",
                "source_confidence": row.get("source_confidence", "unknown"),
            })

    near_term = debt_schedule[debt_schedule["days_to_maturity"].between(0, 730, inclusive="both")].copy()
    if not near_term.empty:
        by_year = near_term.groupby("maturity_year")["principal_mn_krw"].sum().reset_index()
        for _, row in by_year.iterrows():
            rows.append({
                "watch_item": f"{int(row['maturity_year'])}년 차입금 만기",
                "category": "차입금 / 차환",
                "priority_score": min(row["principal_mn_krw"] / debt_schedule["principal_mn_krw"].sum() * 100 + 35, 100),
                "why_it_matters": f"단기 만기 구간에 {row['principal_mn_krw']:,.0f}백만원의 차입금 만기가 도래합니다.",
                "recommended_next_step": "약정별 만기, 담보, 조달원, 스프레드 step-up, 차환 기준금리 Scenario를 연결해 확인합니다.",
                "source_confidence": "high_disclosed_table",
            })

    if pd.notna(latest_kpi.get("interest_coverage_x")) and latest_kpi["interest_coverage_x"] < 2.5:
        rows.append({
            "watch_item": "FFO 이자감당력 proxy",
            "category": "차입금 상환능력",
            "priority_score": 75 if latest_kpi["interest_coverage_x"] < 2.0 else 60,
            "why_it_matters": f"FFO 이자감당력 proxy는 {latest_kpi['interest_coverage_x']:.2f}배입니다.",
            "recommended_next_step": "FFO proxy 하락과 차환 스프레드 민감도를 계산하고 내부 허용수준과 비교합니다.",
            "source_confidence": latest_kpi.get("source_confidence", "high_disclosed_kpi"),
        })

    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=["watch_item", "category", "priority_score", "why_it_matters", "recommended_next_step", "source_confidence"])
    return out.sort_values("priority_score", ascending=False)


def build_due_diligence_questions(risk_scores: dict, latest_kpi: pd.Series) -> pd.DataFrame:
    rows = []
    question_bank = {
        "거래 / FDD": [
            "FFO proxy에 일회성 취득, 차환, 매각, 임차인 교체 효과가 포함되어 있나요?",
            "포트폴리오 가치와 임대수익을 주도하는 자산은 무엇이며, 해당 현금흐름은 장기 임대차계약으로 뒷받침되나요?",
            "특수관계자 또는 마스터리스 조건이 시장조건에 부합하나요, 아니면 스폰서 지원 효과가 포함되어 있나요?",
        ],
        "가치평가": [
            "자산별 Cap rate가 취득일 또는 평가일 가정뿐 아니라 현재 시장 근거와도 일관되나요?",
            "자산 유형별 Cap rate proxy가 +50bp 또는 +100bp 상승할 때 장부NAV proxy 민감도는 어느 정도인가요?",
            "평가상승은 실제 임대료 상승, 위험프리미엄 하락, 또는 단순 시장 Cap rate 하락 중 무엇으로 설명되나요?",
        ],
        "차환 / 신용": [
            "임대차 갱신 또는 주요 임차인 이슈가 해소되기 전에 차환해야 하는 차입금 비중은 얼마인가요?",
            "차환 스프레드가 확대된 뒤에도 스트레스 FFO로 이자를 감당할 수 있나요?",
            "배당을 제한할 수 있는 담보, DSCR, LTV, cash sweep, 등급 trigger가 있나요?",
        ],
        "Assurance": [
            "K-IFRS 연결 재무제표 수치와 투자보고서 KPI가 비율 계산 전에 대사되었나요?",
            "공정가치 가정, 평가 불확실성, 주요 외부 입력변수가 충분히 공시되었나요?",
            "임대차 갱신, 차환, 임차인 신용도 변화가 손상 또는 공정가치 검토 포인트가 되나요?",
        ],
    }
    for perspective, questions in question_bank.items():
        for question in questions:
            rows.append({"perspective": perspective, "review_question": question})
    return pd.DataFrame(rows)
