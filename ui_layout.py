import streamlit as st

from config import APP_TITLE, APP_VERSION, APP_VERSION_NAME
from ui_common import render_user_mode_panel


PUBLIC_MODES = [
    "General Info & Scenario",
    "Assurance",
    "Tax",
    "Methodology & Data Sources",
]


def apply_page_config():
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.3rem; padding-bottom: 2rem; max-width: 1380px;}
        div[data-testid="stMetric"] {background: rgba(128,128,128,0.06); border: 1px solid rgba(128,128,128,0.18); border-radius: 12px; padding: 0.65rem 0.75rem;}
        div[data-testid="stMetricLabel"] {font-size: 0.78rem;}
        div[data-testid="stMetricValue"] {font-size: 1.25rem;}
        div[data-testid="stDataFrame"] {font-size: 0.82rem;}
        h2, h3 {margin-top: 0.35rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_mode_selector():
    st.sidebar.header("Analysis Mode")
    selected_user_mode = st.sidebar.radio(
        "Select a view",
        PUBLIC_MODES,
        index=0,
    )
    st.sidebar.caption("v11 focuses the public portfolio UI on scenario, assurance, tax, and methodology views.")
    st.sidebar.divider()
    return selected_user_mode


def render_intro(selected_user_mode: str):
    st.title(APP_TITLE)
    st.caption(f"{APP_VERSION} - {APP_VERSION_NAME}")

    st.info(
        "This public portfolio application links REIT disclosures, macroeconomic indicators, asset-level data, "
        "debt schedules, and official land price / assessed value inputs to support Tax and Assurance-oriented "
        "risk analysis."
    )

    if selected_user_mode != "General Info & Scenario":
        render_user_mode_panel(selected_user_mode)
        return

    with st.expander("What this tool does", expanded=True):
        st.markdown(
            """
            **Purpose**
            The platform organizes disclosure-based REIT data into a practical risk workflow for accounting and consulting use cases.

            **Current v11 scope**
            The public version focuses on General Info & Scenario, Assurance, Tax, and Methodology & Data Sources. Market-implied valuation and transaction analysis are archived for a future roadmap module.

            **How to read the analysis**
            Start with the scenario view to understand macro sensitivity, debt maturity pressure, asset concentration, and NAV/FFO stress. Then move to Assurance or Tax for workflow-specific checklists and calculations.
            """
        )

    with st.expander("Core terms", expanded=False):
        st.markdown(
            """
            - **FFO**: Funds from operations, used here as a cash-flow proxy for distribution capacity.
            - **NAV**: Net asset value, a proxy for equity value after liabilities.
            - **Cap rate**: Property yield. When cap rates rise, property values generally fall for the same income stream.
            - **Interest coverage**: Cash-flow capacity to cover interest cost.
            - **LTV**: Debt relative to asset or property value.
            """
        )

    with st.expander("Scenario model", expanded=True):
        st.markdown(
            """
            The scenario model is a screening model, not a formal valuation opinion. It links macro assumptions to:

            - FFO downside from operating stress and refinancing cost
            - NAV sensitivity from cap-rate expansion
            - debt maturity and interest-coverage pressure
            - asset-level concentration and lease-risk indicators
            """
        )

    render_user_mode_panel(selected_user_mode)
