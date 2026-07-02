import pandas as pd
import plotly.express as px
import streamlit as st

# Archived for future KRX-based Deals valuation module.
from calculations_valuation import build_deals_backtest_table, build_deals_valuation_summary
from ui_common import compact_fig


def render_deals_mode(latest_kpi: pd.Series, scenario: dict, market_snapshot: dict, historical_panel: pd.DataFrame, p_nav_multiple: float, p_ffo_multiple: float, required_dividend_yield_pct: float):
    st.markdown("## D. Deals 모드: NAV·FFO·배당 기반 시장가치 추정과 KRX 검증")
    st.caption("목적: Buy-side/Sell-side 관점에서 현재 시가총액이 공시 NAV와 FFO 대비 저평가인지, 아니면 리스크를 반영한 가격인지 확인합니다.")
    valuation = build_deals_valuation_summary(latest_kpi, scenario, market_snapshot, p_nav_multiple, p_ffo_multiple, required_dividend_yield_pct)
    backtest = build_deals_backtest_table(historical_panel, p_nav_multiple, p_ffo_multiple)

    d1, d2 = st.columns([0.9, 1.1])
    with d1:
        st.write("**시나리오 기준 가치평가 range**")
        st.dataframe(valuation, width="stretch", hide_index=True, height=210)
    with d2:
        if not valuation.empty:
            fig_val = px.bar(
                valuation,
                x="가치평가 방법",
                y="추정 시장가치_백만원",
                title="가치평가 방법별 추정 시장가치",
                text="추정 시장가치_백만원",
            )
            fig_val.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
            st.plotly_chart(compact_fig(fig_val, 240), width="stretch")

    st.write("**KRX 실제 시가총액 기반 backtesting**")
    if backtest is not None and not backtest.empty:
        st.dataframe(backtest.tail(5), width="stretch", hide_index=True, height=220)
        bt_long = backtest[["연도", "실제시가총액_백만원", "NAV모델_백만원", "FFO모델_백만원"]].melt("연도", var_name="구분", value_name="시장가치_백만원")
        fig_bt = px.line(bt_long.dropna(), x="연도", y="시장가치_백만원", color="구분", markers=True, title="실제 시가총액 vs 모델 추정가치")
        st.plotly_chart(compact_fig(fig_bt, 260), width="stretch")
        st.caption("금리 상승기에는 NAV 기반 모델이 실제 시장가치를 과대평가할 수 있습니다. 이 경우 시장은 차환위험, 요구수익률 상승, 배당 불확실성을 공시 NAV보다 빠르게 반영했을 수 있습니다.")
    else:
        st.info("KRX 주가·시가총액 데이터가 연결되면 실제 시장가치와 모델 추정가치의 backtesting이 표시됩니다.")

    st.success(
        "Deals 해석: Buy-side는 시나리오 후 NAV/FFO를 기준으로 가격 보정을 검토하고, Sell-side는 P/NAV 할인의 원인이 되는 차환·평가·배당 리스크를 사전에 설명해야 합니다."
    )
