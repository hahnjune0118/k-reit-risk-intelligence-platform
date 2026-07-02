import pandas as pd
import streamlit as st

from api_manager import sanitize_secret_text
from ui_assurance import render_assurance_mode
from ui_methodology import render_methodology_page
from ui_tax import render_tax_mode


def render_professional_mode_section(
    selected_mode: str,
    asset_risk: pd.DataFrame,
    debt_schedule: pd.DataFrame,
    latest_kpi: pd.Series,
    scenario: dict,
    assumptions: dict,
):
    if selected_mode == "Assurance":
        render_assurance_mode(
            asset_risk,
            debt_schedule,
            latest_kpi,
            scenario,
            assumptions.get("assurance_materiality_pct", 10.0),
        )
    elif selected_mode == "Tax":
        render_tax_mode(asset_risk, scenario, latest_kpi, assumptions)
    else:
        st.info("업무별 상세 분석은 Assurance 또는 Tax 화면에서 확인할 수 있습니다.")


def render_professional_page(
    selected_user_mode,
    asset_risk,
    debt_schedule,
    latest_kpi,
    scenario,
    professional_assumptions,
    macro_context,
    macro_history_status,
    dart_status,
    financials,
    kpis,
    source_plan=None,
    data_dictionary=None,
):
    if selected_user_mode == "Methodology & Data Sources":
        render_methodology_page(
            macro_context,
            macro_history_status,
            dart_status,
            financials,
            kpis,
            asset_risk,
            debt_schedule,
            source_plan if source_plan is not None else pd.DataFrame(),
            data_dictionary if data_dictionary is not None else pd.DataFrame(),
        )
        return

    st.markdown("## 업무별 리스크 분석")
    st.caption("좌측 사이드바에서 선택한 거시경제 Scenario 가정은 Assurance와 Tax 화면에 동일하게 적용됩니다.")
    render_professional_mode_section(
        selected_user_mode,
        asset_risk,
        debt_schedule,
        latest_kpi,
        scenario,
        professional_assumptions,
    )
    st.markdown("---")
    with st.expander("분석 방법론과 자료 기준", expanded=False):
        st.caption(
            "거시경제 지표: "
            f"{sanitize_secret_text(macro_context['source'])} / "
            f"과거 금리: {sanitize_secret_text(macro_history_status)} / "
            f"DART: {sanitize_secret_text(dart_status)}"
        )
        st.write("자료 신뢰도 요약")
        source_conf = pd.concat([
            asset_risk[["source_document", "source_confidence"]],
            debt_schedule[["source_document", "source_confidence"]],
            financials[["source_document", "source_confidence"]],
            kpis[["source_document", "source_confidence"]],
        ], ignore_index=True).drop_duplicates()
        source_conf = source_conf.rename(columns={
            "source_document": "자료 문서",
            "source_confidence": "자료 신뢰도",
        })
        st.dataframe(source_conf, width="stretch", hide_index=True, height=180)
    st.caption(
        "이 Streamlit 프로토타입은 예비 분석 도구이며 투자판단, 감사의견, 세무신고, 법률 자문, 신용등급, 정식 가치평가 의견을 제공하지 않습니다."
    )
