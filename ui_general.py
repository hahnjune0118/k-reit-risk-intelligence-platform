import pandas as pd
import plotly.express as px
import streamlit as st

from calculations_scenario import korean_metric_label, korean_risk_label
from formatting import format_pct_from_100, format_ratio, format_score, format_trn_krw_from_mn
from security import sanitize_secret_text
from ui_common import compact_fig, fmt_metric_value, fmt_mn_to_bn, mode_specific_action_items


def render_general_dashboard(
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
    debt_schedule,
    debt_summary,
    cap_rate_shock_bp,
    source_plan,
    data_dictionary,
    financials,
    kpis,
    macro_history_status,
    dart_status,
    krx_status,
    dart_reports,
    krx_history,
):
    st.markdown("## 1. 한눈에 보는 결론")

    if verdict_level == "High":
        st.error(f"{verdict_text} — {verdict_reason}")
    elif verdict_level == "Medium":
        st.warning(f"{verdict_text} — {verdict_reason}")
    else:
        st.success(f"{verdict_text} — {verdict_reason}")

    st.caption(
        f"선택 시나리오: {macro_scenario['selected_scenario']} | "
        f"기준금리 {macro_scenario['base_rate_pct']:.2f}% → {macro_scenario['scenario_base_rate_pct']:.2f}% | "
        f"차입금리 충격 +{macro_scenario['rate_shock_bp']}bp | "
        f"Cap rate +{macro_scenario['cap_rate_shock_bp']}bp | "
        f"자료 기준: {macro_context['source']}"
    )

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("종합 위험도", {"High":"높음", "Medium":"보통", "Low":"낮음"}.get(risk_level, risk_level), format_score(total_risk))
    k2.metric("시나리오 후 현금흐름", fmt_mn_to_bn(scenario["stressed_ffo"]), f"{scenario['ffo_decline_pct']:.1f}%" if pd.notna(scenario["ffo_decline_pct"]) else "N/A")
    k3.metric("이자 감당력", format_ratio(scenario["stressed_icr"]), f"현재 {format_ratio(scenario['reported_icr'])}")
    k4.metric("순자산가치 영향", format_pct_from_100(scenario["nav_change_pct"]), fmt_mn_to_bn(scenario["total_value_change"]))
    k5.metric("부채비율 추정", format_pct_from_100(scenario["stressed_ltv_proxy"]), f"현재 {format_pct_from_100(scenario['base_ltv_proxy'])}")

    if market_snapshot.get("available"):
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("최근 주가", f"{market_snapshot['close_price_krw']:,.0f}원" if pd.notna(market_snapshot['close_price_krw']) else "N/A")
        m2.metric("시가총액", fmt_mn_to_bn(market_snapshot.get("market_cap_mn_krw")))
        m3.metric("P/NAV", format_ratio(market_snapshot.get("p_nav")))
        m4.metric("NAV 할인율", format_pct_from_100(market_snapshot.get("nav_discount_pct")))
        st.caption(f"시장가격 기준일: {pd.to_datetime(market_snapshot.get('date')).strftime('%Y-%m-%d') if market_snapshot.get('date') is not None else 'N/A'} / 자료: {market_snapshot.get('source')}")
    else:
        st.caption("KRX API를 연결하면 최근 주가, 시가총액, P/NAV, NAV 할인율이 이 위치에 표시됩니다.")

    if market_gap is not None and not market_gap.empty:
        st.write("**시장가격이 공시 NAV와 스트레스 NAV를 어떻게 평가하는가**")
        mg = market_gap.copy()
        for c in ["NAV_백만원", "시가총액_백만원"]:
            if c in mg.columns:
                mg[c] = mg[c].apply(lambda x: fmt_mn_to_bn(x) if pd.notna(x) else "-")
        if "P_NAV" in mg.columns:
            mg["P_NAV"] = mg["P_NAV"].apply(lambda x: format_ratio(x) if pd.notna(x) else "-")
        if "시장할인율_pct" in mg.columns:
            mg["시장할인율_pct"] = mg["시장할인율_pct"].apply(lambda x: format_pct_from_100(x) if pd.notna(x) else "-")
        mg = mg.rename(columns={"기준": "비교 기준", "NAV_백만원": "NAV", "시가총액_백만원": "시가총액", "P_NAV": "P/NAV", "시장할인율_pct": "할인율/차이"})
        st.dataframe(mg, width="stretch", hide_index=True, height=142)
        st.caption(market_gap_narrative)

    st.markdown("---")
    st.markdown("## 2. 현재 상태와 선택한 시나리오 비교")
    st.caption("좌측 사이드바에서 거시경제 시나리오를 바꾸면 현금흐름, 이자 감당력, 배당 여력, 순자산가치가 즉시 바뀝니다.")

    left, right = st.columns([1.05, 1.0])

    with left:
        fig_ffo = px.bar(
            scenario["ffo_bridge"].sort_values("display_order"),
            x="step",
            y="mn_krw",
            title="현금흐름 변화: 현재 → 시나리오 후",
            text="mn_krw",
        )
        fig_ffo.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
        st.plotly_chart(compact_fig(fig_ffo, 255), width="stretch")

    with right:
        kpi_display = scenario["kpi_summary"].copy()
        kpi_display["지표"] = kpi_display["metric"].apply(korean_metric_label)
        kpi_display["현재"] = kpi_display.apply(lambda r: fmt_metric_value(r, "baseline"), axis=1)
        kpi_display["시나리오 후"] = kpi_display.apply(lambda r: fmt_metric_value(r, "stressed"), axis=1)
        kpi_display = kpi_display[["지표", "현재", "시나리오 후"]]
        st.dataframe(kpi_display, width="stretch", hide_index=True, height=245)

    st.markdown("---")
    st.markdown("## 3. 최근 5년 흐름: 금리와 리츠 지표가 같이 어떻게 움직였나")
    st.caption(
        "DART API가 연결되면 최근 5개 사업연도 재무제표를 사용하고, 연결되지 않으면 현재 프로젝트의 로컬 공시 CSV를 사용합니다. "
        "ECOS API가 연결되면 기준금리·시장금리 시계열을 사용하고, KRX API가 연결되면 주가·시가총액·P/NAV도 함께 표시합니다."
    )

    h_left, h_right = st.columns([1.2, 1.0])

    with h_left:
        index_cols = [c for c in ["기준금리_index", "국고채 3년_index", "순자산가치_또는_자본_index", "현금흐름_또는_이익_index", "시장가치_index", "주가_index", "P_NAV_index"] if c in historical_panel.columns]
        hist_long = historical_panel[["year"] + index_cols].melt("year", var_name="지표", value_name="지수") if index_cols else pd.DataFrame()
        if not hist_long.empty:
            hist_long["지표"] = hist_long["지표"].replace({
                "기준금리_index": "기준금리",
                "국고채 3년_index": "국고채 3년",
                "순자산가치_또는_자본_index": "순자산가치/NAV proxy",
                "현금흐름_또는_이익_index": "현금흐름/이익 proxy",
                "시장가치_index": "시가총액",
                "주가_index": "주가",
                "P_NAV_index": "P/NAV",
            })
            fig_hist_index = px.line(
                hist_long.dropna(),
                x="year",
                y="지수",
                color="지표",
                markers=True,
                title="최근 5년 금리와 리츠 핵심지표 비교, 첫해=100",
            )
            st.plotly_chart(compact_fig(fig_hist_index, 255), width="stretch")
        else:
            st.info("시계열 지표를 만들 수 있는 데이터가 아직 부족합니다.")

    with h_right:
        hist_display_cols = [c for c in ["year", "기준금리", "국고채 3년", "회사채 AA- 3년", "순자산가치_또는_자본", "현금흐름_또는_이익", "시장가치", "주가", "P_NAV", "NAV_할인율", "부채비율_LTV추정"] if c in historical_panel.columns]
        hist_display = historical_panel[hist_display_cols].copy() if hist_display_cols else pd.DataFrame()
        if not hist_display.empty:
            rename_hist = {
                "year": "연도",
                "기준금리": "기준금리",
                "국고채 3년": "국고채 3년",
                "회사채 AA- 3년": "회사채 AA- 3년",
                "순자산가치_또는_자본": "NAV/자본(백만원)",
                "현금흐름_또는_이익": "FFO/이익(백만원)",
                "시장가치": "시가총액(백만원)",
                "주가": "주가(원)",
                "P_NAV": "P/NAV",
                "NAV_할인율": "NAV 할인율(%)",
                "부채비율_LTV추정": "부채비율 추정",
            }
            st.write("**연도별 핵심 데이터**")
            st.dataframe(hist_display.rename(columns=rename_hist), width="stretch", hide_index=True, height=250)

    if all(c in historical_panel.columns for c in ["기준금리_변화_bp", "순자산가치_변화율", "현금흐름_변화율"]):
        reaction = historical_panel[["year", "기준금리_변화_bp", "순자산가치_변화율", "현금흐름_변화율"]].dropna().copy()
        if not reaction.empty:
            reaction = reaction.rename(columns={
                "year": "연도",
                "기준금리_변화_bp": "기준금리 변화폭(bp)",
                "순자산가치_변화율": "NAV/자본 변화율(%)",
                "현금흐름_변화율": "FFO/이익 변화율(%)",
            })
            st.write("**기준금리 변화와 리츠 지표 변화**")
            st.dataframe(reaction, width="stretch", hide_index=True, height=160)
            st.caption(
                "주의: 이 표는 인과관계를 확정하지 않습니다. 리츠의 NAV·FFO는 금리 외에도 자산 편입, 유상증자, 임대차 계약, 회계 기준, 평가가정에 영향을 받습니다."
            )

    if all(c in historical_panel.columns for c in ["기준금리_변화_bp", "시장가치_변화율", "P_NAV_변화"]):
        market_reaction = historical_panel[["year", "기준금리_변화_bp", "시장가치_변화율", "P_NAV_변화"]].dropna().copy()
        if not market_reaction.empty:
            market_reaction = market_reaction.rename(columns={
                "year": "연도",
                "기준금리_변화_bp": "기준금리 변화폭(bp)",
                "시장가치_변화율": "시가총액 변화율(%)",
                "P_NAV_변화": "P/NAV 변화",
            })
            st.write("**기준금리 변화와 시장가격 반응**")
            st.dataframe(market_reaction, width="stretch", hide_index=True, height=150)
            st.caption(
                "P/NAV 하락은 시장이 공시 순자산가치보다 더 큰 할인율을 적용하기 시작했다는 신호일 수 있습니다. "
                "단, 주가는 시장 전체 리스크 선호, 유상증자, 배당정책, 거래량에도 영향을 받습니다."
            )

    st.markdown("### 3-1. 위험 전이 진단: 금리 → FFO/NAV → 시장가격")
    st.caption(
        "이 섹션은 금리가 바뀐 해에 리츠의 현금흐름, 순자산가치, 시가총액, P/NAV가 어떻게 움직였는지 요약합니다. "
        "인과관계 확정이 아니라, Deals/Assurance 초기검토에서 어디를 더 봐야 하는지 알려주는 신호입니다."
    )
    st.info(transmission_narrative)

    t_left, t_right = st.columns([1.15, 0.85])
    with t_left:
        if transmission_table is not None and not transmission_table.empty:
            st.write("**연도별 전이 신호**")
            st.dataframe(transmission_table.tail(5), width="stretch", hide_index=True, height=220)
        else:
            st.caption("금리·재무·시장가격 시계열이 충분히 연결되면 연도별 전이 신호가 표시됩니다.")

    with t_right:
        if transmission_corr is not None and not transmission_corr.empty:
            st.write("**단순 민감도 참고표**")
            corr_display = transmission_corr.copy()
            corr_display["상관계수"] = corr_display["상관계수"].map(lambda x: f"{x:.2f}")
            st.dataframe(corr_display, width="stretch", hide_index=True, height=220)
        else:
            st.caption("상관계수는 최소 3개 이상의 연도별 관측치가 있을 때 표시됩니다.")

    if transmission_table is not None and not transmission_table.empty and {"기준금리 변화폭(bp)", "시가총액 변화율(%)"}.issubset(transmission_table.columns):
        scatter_data = transmission_table[["연도", "기준금리 변화폭(bp)", "시가총액 변화율(%)", "해석 신호"]].dropna().copy()
        if not scatter_data.empty:
            fig_trans = px.scatter(
                scatter_data,
                x="기준금리 변화폭(bp)",
                y="시가총액 변화율(%)",
                color="해석 신호",
                text="연도",
                title="금리 변화와 시가총액 반응",
            )
            fig_trans.update_traces(textposition="top center")
            st.plotly_chart(compact_fig(fig_trans, 250), width="stretch")

    st.write("**현재 사용자 모드의 권장 확인사항**")
    st.dataframe(mode_specific_action_items(selected_user_mode), width="stretch", hide_index=True, height=140)

    st.markdown("---")
    st.info("Assurance, Tax, Deals 상세 분석은 좌측 사용자 모드에서 해당 전문가 모드를 선택하면 별도 화면으로 표시됩니다.")

    st.markdown("---")
    st.markdown("## 4. 위험 점수와 우선 확인 항목")

    r1, r2 = st.columns([0.9, 1.25])

    with r1:
        risk_chart = pd.DataFrame({
            "위험 유형": [korean_risk_label(k) for k in risk_scores.keys()],
            "점수": list(risk_scores.values()),
        })
        fig_risk = px.bar(
            risk_chart,
            x="점수",
            y="위험 유형",
            orientation="h",
            title="위험 유형별 점수",
            range_x=[0, 100],
            text="점수",
        )
        fig_risk.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
        st.plotly_chart(compact_fig(fig_risk, 255), width="stretch")

    with r2:
        wl_cols = ["watch_item", "category", "priority_score", "why_it_matters"]
        watch_display = watchlist[wl_cols].head(6).rename(columns={
            "watch_item": "확인 항목",
            "category": "구분",
            "priority_score": "우선순위 점수",
            "why_it_matters": "왜 중요한가",
        })
        st.write("**먼저 확인할 항목**")
        st.dataframe(watch_display, width="stretch", hide_index=True, height=245)

    triggered_decomp = risk_decomposition[risk_decomposition["triggered"]].copy()
    if not triggered_decomp.empty:
        st.write("**점수를 높인 주요 원인**")
        decomp_display = triggered_decomp[["risk_category", "driver", "score_delta", "weighted_score_delta", "interpretation"]].head(8).copy()
        decomp_display["risk_category"] = decomp_display["risk_category"].apply(korean_risk_label)
        decomp_display = decomp_display.rename(columns={
            "risk_category": "위험 유형",
            "driver": "원인",
            "score_delta": "점수 영향",
            "weighted_score_delta": "가중 영향",
            "interpretation": "해석",
        })
        st.dataframe(
            decomp_display,
            width="stretch",
            hide_index=True,
            height=190,
        )

    st.markdown("---")
    st.markdown("## 5. 자산·임차인·임대 안정성")

    total_appraised = asset_risk["appraised_value_mn_krw_20251231"].sum()
    office_value = asset_risk[asset_risk["asset_type"].str.contains("office", case=False, na=False)]["appraised_value_mn_krw_20251231"].sum()
    top_asset = concentration_table.sort_values("appraised_value_mn_krw_20251231", ascending=False).iloc[0]
    top3_share = concentration_table.head(3)["portfolio_value_share_pct"].sum()
    hhi = concentration_table["hhi_component"].sum()

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("부동산 평가액", format_trn_krw_from_mn(total_appraised))
    p2.metric("상위 3개 자산 비중", format_pct_from_100(top3_share))
    p3.metric("최대 자산 비중", format_pct_from_100(top_asset["portfolio_value_share_pct"]))
    p4.metric("자산 집중도", f"{hhi:.3f}")

    c_left, c_mid, c_right = st.columns([1.0, 1.0, 1.0])

    with c_left:
        top_assets = concentration_table[[
            "asset_name",
            "appraised_value_mn_krw_20251231",
            "portfolio_value_share_pct",
            "major_tenant",
            "wale_yrs",
            "cap_rate_pct_20251231",
            "asset_risk_score",
        ]].head(7).copy()
        top_assets = top_assets.rename(columns={
            "asset_name": "자산",
            "appraised_value_mn_krw_20251231": "평가액_백만원",
            "portfolio_value_share_pct": "포트폴리오_비중_%",
            "major_tenant": "주요_임차인",
            "wale_yrs": "남은_임대기간_년",
            "cap_rate_pct_20251231": "Cap_rate_%",
            "asset_risk_score": "위험점수",
        })
        st.write("**핵심 자산**")
        st.dataframe(top_assets, width="stretch", hide_index=True, height=245)

    with c_mid:
        tenant_simple = tenant_exposure[["major_tenant", "tenant_credit", "portfolio_value_share_pct"]].head(7).copy()
        tenant_simple = tenant_simple.rename(columns={
            "major_tenant": "임차인",
            "tenant_credit": "신용도",
            "portfolio_value_share_pct": "포트폴리오_비중_%",
        })
        st.write("**주요 임차인 비중**")
        st.dataframe(tenant_simple, width="stretch", hide_index=True, height=245)

    with c_right:
        fig_wale = px.bar(
            asset_risk.sort_values("wale_yrs", ascending=True).dropna(subset=["wale_yrs"]),
            x="wale_yrs",
            y="asset_name",
            orientation="h",
            title="자산별 남은 임대기간",
            text="wale_yrs",
        )
        fig_wale.update_traces(texttemplate="%{text:.1f}y", textposition="outside", cliponaxis=False)
        st.plotly_chart(compact_fig(fig_wale, 245), width="stretch")

    st.markdown("---")
    st.markdown("## 6. 부채 만기와 차환 부담")

    total_principal = debt_schedule["principal_mn_krw"].sum()
    fixed_principal = debt_schedule[debt_schedule["rate_type"] == "고정"]["principal_mn_krw"].sum()
    floating_principal = debt_schedule[debt_schedule["rate_type"] == "변동"]["principal_mn_krw"].sum()
    near_1y = debt_schedule[debt_schedule["days_to_maturity"].between(0, 365, inclusive="both")]["principal_mn_krw"].sum()

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("공시 차입금", format_trn_krw_from_mn(total_principal))
    b2.metric("고정금리 비중", format_pct_from_100(fixed_principal / total_principal * 100 if total_principal else pd.NA))
    b3.metric("변동금리 비중", format_pct_from_100(floating_principal / total_principal * 100 if total_principal else pd.NA))
    b4.metric("1년 내 만기", format_pct_from_100(near_1y / total_principal * 100 if total_principal else pd.NA))

    d_left, d_right = st.columns([1.15, 0.85])

    with d_left:
        debt_by_year = debt_summary.groupby("maturity_year", as_index=False).agg(
            principal_mn_krw=("principal_mn_krw", "sum"),
            weighted_avg_all_in_rate_pct=("weighted_avg_all_in_rate_pct", "mean"),
            number_of_facilities=("number_of_facilities", "sum"),
        )
        fig_wall = px.bar(
            debt_by_year.sort_values("maturity_year"),
            x="maturity_year",
            y="principal_mn_krw",
            title="연도별 부채 만기",
            text="principal_mn_krw",
        )
        fig_wall.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
        st.plotly_chart(compact_fig(fig_wall, 250), width="stretch")

    with d_right:
        debt_simple = debt_by_year.rename(columns={
            "maturity_year": "만기연도",
            "principal_mn_krw": "원금_백만원",
            "weighted_avg_all_in_rate_pct": "평균금리_%",
            "number_of_facilities": "건수",
        })
        st.write("**만기 요약**")
        st.dataframe(debt_simple, width="stretch", hide_index=True, height=250)

    st.markdown("---")
    st.markdown("## 7. 부동산 가치와 순자산가치 변화")
    st.caption("Cap rate는 부동산 수익률입니다. 이 수치가 오르면 같은 임대수익을 가진 부동산의 평가가치는 내려갑니다.")

    v1, v2, v3, v4 = st.columns(4)
    v1.metric("현재 순자산가치", format_trn_krw_from_mn(scenario["base_nav"]))
    v2.metric("시나리오 후 순자산가치", format_trn_krw_from_mn(scenario["stressed_nav"]))
    v3.metric("순자산가치 변화", format_pct_from_100(scenario["nav_change_pct"]))
    v4.metric("배당 후 남는 여력", fmt_mn_to_bn(scenario["dividend_cushion"]))

    asset_sens = scenario["asset_sensitivity"].copy().sort_values("value_change_pct")
    val_left, val_right = st.columns([1.15, 0.85])

    with val_left:
        fig_nav = px.bar(
            asset_sens,
            x="value_change_pct",
            y="asset_name",
            orientation="h",
            title=f"자산별 가치 변화: Cap rate +{cap_rate_shock_bp}bp",
            text="value_change_pct",
        )
        fig_nav.update_traces(texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
        st.plotly_chart(compact_fig(fig_nav, 270), width="stretch")

    with val_right:
        sens_simple = asset_sens[[
            "asset_name",
            "cap_rate_pct_20251231",
            "appraised_value_mn_krw_20251231",
            "value_under_cap_rate_shock_mn_krw",
            "value_change_pct",
        ]].copy()
        sens_simple = sens_simple.rename(columns={
            "asset_name": "자산",
            "cap_rate_pct_20251231": "현재_Cap_rate_%",
            "appraised_value_mn_krw_20251231": "현재가치_백만원",
            "value_under_cap_rate_shock_mn_krw": "시나리오후_가치_백만원",
            "value_change_pct": "가치변화_%",
        })
        st.write("**자산가치 변화 표**")
        st.dataframe(sens_simple, width="stretch", hide_index=True, height=270)

    st.markdown("---")
    st.markdown("## 8. 자료 출처와 계산 기준")
    st.caption("공시자료와 API 자료의 출처는 하단에서 필요한 경우만 확인합니다.")

    with st.expander("자료 출처, 데이터 사전, 추가 확인 자료 보기", expanded=False):
        s1, s2 = st.columns(2)
        with s1:
            st.write("**자료 신뢰도 요약**")
            source_conf = pd.concat([
                asset_risk[["source_document", "source_confidence"]],
                debt_schedule[["source_document", "source_confidence"]],
                financials[["source_document", "source_confidence"]],
                kpis[["source_document", "source_confidence"]],
            ], ignore_index=True).drop_duplicates()
            st.dataframe(source_conf, width="stretch", hide_index=True, height=170)
            st.caption(
                "거시경제 지표: "
                f"{sanitize_secret_text(macro_context['source'])} / "
                f"과거 금리: {sanitize_secret_text(macro_history_status)} / "
                f"DART: {sanitize_secret_text(dart_status)} / "
                f"KRX: {sanitize_secret_text(krx_status)}"
            )
        with s2:
            st.write("**추가 수집 자료 계획**")
            st.dataframe(source_plan, width="stretch", hide_index=True, height=170)

        if dart_reports is not None and not dart_reports.empty:
            st.write("**DART에서 확인한 최근 사업보고서**")
            report_cols = [c for c in ["rcept_dt", "report_nm", "rcept_no"] if c in dart_reports.columns]
            st.dataframe(dart_reports[report_cols].head(10), width="stretch", hide_index=True, height=150)

        if krx_history is not None and not krx_history.empty:
            st.write("**KRX에서 불러온 주가·시가총액 월별 표본**")
            krx_cols = [c for c in ["date", "stock_code", "stock_name", "close_price_krw", "market_cap_mn_krw", "trading_volume"] if c in krx_history.columns]
            st.dataframe(krx_history[krx_cols].tail(12), width="stretch", hide_index=True, height=170)

        st.write("**데이터 사전**")
        st.dataframe(data_dictionary, width="stretch", hide_index=True, height=160)

        st.write("**불러온 CSV 표**")
        loaded = pd.DataFrame({
            "table": [
                "sk_reit_consolidated_financials.csv",
                "sk_reit_latest_kpis.csv",
                "sk_reit_asset_metrics.csv",
                "sk_reit_parent_direct_assets_20260331.csv",
                "sk_reit_debt_schedule_20260331.csv",
                "sk_reit_debt_summary_20260331.csv",
                "sk_reit_additional_source_plan.csv",
                "sk_reit_data_dictionary.csv",
            ],
            "purpose": [
                "Financial trend and K-IFRS leverage",
                "NAV, FFO, dividend, leverage and coverage KPIs",
                "Asset valuation, lease and tenant exposure",
                "Investment-report direct ownership details",
                "Facility-level debt maturity and rate analysis",
                "Aggregated refinancing wall",
                "Next source collection roadmap",
                "Definitions and basis-control notes",
            ],
        })
        st.dataframe(loaded, width="stretch", hide_index=True, height=170)

    st.divider()
    st.caption(
        "주의: 이 Streamlit 프로토타입은 리츠 위험을 빠르게 확인하기 위한 예비 분석 도구입니다. "
        "KRX·DART·ECOS API 결과는 각 기관의 제공 범위와 승인 상태에 따라 달라질 수 있으며, "
        "투자추천, 정식 가치평가, 감사의견, 신용등급, 법률·세무 자문을 제공하지 않습니다."
    )
