import pandas as pd
import streamlit as st

from ui_assurance import render_assurance_mode
from ui_deals import render_deals_mode
from api_manager import sanitize_secret_text
from ui_tax import render_tax_mode


def render_professional_mode_section(selected_mode: str, asset_risk: pd.DataFrame, debt_schedule: pd.DataFrame, latest_kpi: pd.Series, scenario: dict, market_snapshot: dict, historical_panel: pd.DataFrame, assumptions: dict):
    if selected_mode == "Assurance":
        render_assurance_mode(asset_risk, debt_schedule, latest_kpi, scenario, assumptions.get("assurance_materiality_pct", 10.0))
    elif selected_mode == "Tax":
        render_tax_mode(asset_risk, scenario, latest_kpi, assumptions)
    elif selected_mode == "Deals":
        render_deals_mode(
            latest_kpi,
            scenario,
            market_snapshot,
            historical_panel,
            assumptions.get("p_nav_multiple", 0.80),
            assumptions.get("p_ffo_multiple", 16.0),
            assumptions.get("required_dividend_yield_pct", 7.0),
        )


def render_professional_page(
    selected_user_mode,
    asset_risk,
    debt_schedule,
    latest_kpi,
    scenario,
    market_snapshot,
    historical_panel,
    professional_assumptions,
    macro_context,
    macro_history_status,
    dart_status,
    krx_status,
    financials,
    kpis,
):
    st.markdown("## 전문가 모드별 분석")
    st.caption("공통 지표와 시나리오는 'General Info & Scenario' 모드에서, 현재 화면에서는 선택한 전문가 관점의 분석만 보여줍니다.")
    render_professional_mode_section(
        selected_user_mode,
        asset_risk,
        debt_schedule,
        latest_kpi,
        scenario,
        market_snapshot,
        historical_panel,
        professional_assumptions,
    )
    st.markdown("---")
    with st.expander("자료 출처와 계산 기준 보기", expanded=False):
        st.caption(
            "거시경제 지표: "
            f"{sanitize_secret_text(macro_context['source'])} / "
            f"과거 금리: {sanitize_secret_text(macro_history_status)} / "
            f"DART: {sanitize_secret_text(dart_status)} / "
            f"KRX: {sanitize_secret_text(krx_status)}"
        )
        st.write("자료 신뢰도 요약")
        source_conf = pd.concat([
            asset_risk[["source_document", "source_confidence"]],
            debt_schedule[["source_document", "source_confidence"]],
            financials[["source_document", "source_confidence"]],
            kpis[["source_document", "source_confidence"]],
        ], ignore_index=True).drop_duplicates()
        st.dataframe(source_conf, width="stretch", hide_index=True, height=180)
    st.caption(
        "주의: 이 Streamlit 프로토타입은 예비 분석 도구이며, 투자추천, 정식 가치평가, 감사의견, 법률·세무 자문을 제공하지 않습니다."
    )
