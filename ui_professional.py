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
        st.info("Select Assurance or Tax for workflow-specific analysis.")


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

    st.markdown("## Professional Workflow Analysis")
    st.caption("General scenario assumptions are shared across Assurance and Tax workflow views.")
    render_professional_mode_section(
        selected_user_mode,
        asset_risk,
        debt_schedule,
        latest_kpi,
        scenario,
        professional_assumptions,
    )
    st.markdown("---")
    with st.expander("Methodology and source basis", expanded=False):
        st.caption(
            "Macro indicators: "
            f"{sanitize_secret_text(macro_context['source'])} / "
            f"Historical rates: {sanitize_secret_text(macro_history_status)} / "
            f"DART: {sanitize_secret_text(dart_status)}"
        )
        st.write("Source confidence summary")
        source_conf = pd.concat([
            asset_risk[["source_document", "source_confidence"]],
            debt_schedule[["source_document", "source_confidence"]],
            financials[["source_document", "source_confidence"]],
            kpis[["source_document", "source_confidence"]],
        ], ignore_index=True).drop_duplicates()
        st.dataframe(source_conf, width="stretch", hide_index=True, height=180)
    st.caption(
        "This Streamlit prototype is a preliminary analytics tool and does not provide investment, audit, tax, legal, credit, or valuation opinions."
    )
