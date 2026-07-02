import pandas as pd
import streamlit as st

from api_manager import sanitize_secret_text
from config import APP_VERSION, APP_VERSION_NAME


def render_methodology_page(
    macro_context,
    macro_history_status,
    dart_status,
    financials,
    kpis,
    asset_risk,
    debt_schedule,
    source_plan,
    data_dictionary,
):
    st.markdown("## Methodology & Data Sources")
    st.caption(f"Current stable public version: {APP_VERSION} - {APP_VERSION_NAME}")

    st.markdown("### Active v11 Scope")
    st.dataframe(
        pd.DataFrame([
            {"Mode": "General Info & Scenario", "Purpose": "Common risk profile, macro scenario stress, asset/debt overview"},
            {"Mode": "Assurance", "Purpose": "Audit planning, RMM mapping, KAM candidates, control-response checklists"},
            {"Mode": "Tax", "Purpose": "Holding-tax estimator, official-price data workflow, FFO cash-outflow stress"},
            {"Mode": "Methodology & Data Sources", "Purpose": "Source basis, limitations, security posture, roadmap"},
        ]),
        hide_index=True,
        width="stretch",
        height=176,
    )

    st.markdown("### Data Sources")
    source_status = pd.DataFrame([
        {"Source": "DART", "Use": "Financial statements and recent disclosure list", "Status": sanitize_secret_text(dart_status)},
        {"Source": "ECOS", "Use": "Macro indicators and annual rate history", "Status": sanitize_secret_text(macro_history_status)},
        {"Source": "V-World / official land price API", "Use": "Official land price / assessed value inputs for Tax mode", "Status": "Available when configured"},
        {"Source": "Internal CSV files", "Use": "Bundled disclosure-based tables for stable public demo operation", "Status": "Bundled"},
    ])
    st.dataframe(source_status, hide_index=True, width="stretch", height=190)

    st.markdown("### Calculation Basis")
    st.write(
        "The app is a screening and workflow-support tool. It links disclosed financials, KPIs, asset data, debt schedules, "
        "macroeconomic indicators, and official-price inputs into scenario outputs and professional review checklists."
    )
    st.write(
        "Outputs should be interpreted as preliminary analytical signals. They are not audit opinions, tax filings, legal advice, "
        "investment recommendations, credit ratings, or formal valuation opinions."
    )

    st.markdown("### Security")
    st.write(
        "API keys are loaded through Streamlit Secrets, environment variables, or optional manual password fields. "
        "Secrets are never populated into widget values and all debug/status text is sanitized before display."
    )

    with st.expander("Source confidence summary", expanded=False):
        source_conf = pd.concat([
            asset_risk[["source_document", "source_confidence"]],
            debt_schedule[["source_document", "source_confidence"]],
            financials[["source_document", "source_confidence"]],
            kpis[["source_document", "source_confidence"]],
        ], ignore_index=True).drop_duplicates()
        st.dataframe(source_conf, width="stretch", hide_index=True, height=220)

    with st.expander("Data dictionary", expanded=False):
        st.dataframe(data_dictionary, width="stretch", hide_index=True, height=220)

    with st.expander("Additional source collection plan", expanded=False):
        st.dataframe(source_plan, width="stretch", hide_index=True, height=220)

    st.markdown("### Roadmap")
    st.write(
        "Future v12/v13 modules may reintroduce market-implied valuation and transaction analysis after the data connection "
        "and workflow are hardened for public deployment."
    )
