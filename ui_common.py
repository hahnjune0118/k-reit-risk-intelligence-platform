import pandas as pd
import streamlit as st

from formatting import _is_na, format_pct_from_100, format_ratio


USER_MODE_CONFIG = {
    "General Info & Scenario": {
        "title": "General Info & Scenario",
        "goal": "Review the REIT's baseline risk profile, macro scenario sensitivity, asset concentration, debt maturity, NAV, FFO, and distribution capacity.",
        "decision": "Use this view as the common analytical base before moving into Assurance or Tax workflows.",
        "questions": [
            "How sensitive are FFO, NAV, interest coverage, and leverage to the selected macro scenario?",
            "Which assets, tenants, debt maturities, or tax drivers create the most visible pressure points?",
            "Which disclosures or source documents should be reviewed first?",
        ],
    },
    "Assurance": {
        "title": "Assurance",
        "goal": "Translate REIT risk indicators into audit planning, RMM, KAM, going-concern, and internal-control review points.",
        "decision": "Prioritize fair-value, debt maturity, cash-flow, and control considerations for an audit-oriented workflow.",
        "questions": [
            "Which investment properties have the highest fair-value estimation risk?",
            "How do cap-rate and refinancing assumptions affect RMM and KAM candidates?",
            "Which controls should be tested around valuation, debt monitoring, and disclosure review?",
        ],
    },
    "Tax": {
        "title": "Tax",
        "goal": "Estimate holding-tax pressure using official land price / assessed value data, uploads, or proxy assumptions.",
        "decision": "Identify property-tax cost drivers, FFO cash-outflow pressure, data gaps, and automation opportunities.",
        "questions": [
            "Which assets create the largest holding-tax exposure?",
            "How much additional cash outflow could arise under official-price increases?",
            "Which source data should be reconciled before using the estimate in a professional workflow?",
        ],
    },
    "Methodology & Data Sources": {
        "title": "Methodology & Data Sources",
        "goal": "Explain the data sources, calculation logic, assumptions, limitations, and versioning convention behind the public portfolio app.",
        "decision": "Use this page to review source reliability, API handling, and roadmap boundaries before relying on the analysis.",
        "questions": [
            "Which data is sourced from APIs, bundled CSV files, or user uploads?",
            "Which calculations are screening estimates rather than formal opinions?",
            "What is included in v11, and what is deferred to future v12/v13 modules?",
        ],
    },
}


def render_user_mode_panel(selected_mode: str):
    cfg = USER_MODE_CONFIG[selected_mode]
    st.markdown("## 0. Mode Context")
    st.caption("Each mode frames the same REIT data for a different professional workflow.")
    c1, c2 = st.columns([0.9, 1.25])
    with c1:
        st.metric("Current Mode", cfg["title"])
        st.write(f"**Purpose**: {cfg['goal']}")
        st.write(f"**Decision Lens**: {cfg['decision']}")
    with c2:
        st.write("**Questions to Ask First**")
        for q in cfg["questions"]:
            st.write(f"- {q}")


def mode_specific_action_items(selected_mode: str) -> pd.DataFrame:
    rows = {
        "General Info & Scenario": [
            ("Baseline", "Review NAV, FFO, interest coverage, leverage, asset concentration, tenant exposure, and debt maturity profile."),
            ("Scenario", "Check how ECOS-informed macro assumptions affect FFO, NAV, interest coverage, and LTV proxy."),
            ("Next workflow", "Move to Assurance or Tax for audit-risk mapping or holding-tax cash-flow analysis."),
        ],
        "Assurance": [
            ("RMM", "Prioritize fair-value, refinancing, lease rollover, and disclosure risk areas."),
            ("KAM", "Assess whether valuation uncertainty, cap-rate sensitivity, debt maturity, or going-concern pressure could become KAM candidates."),
            ("Internal control", "Review controls over valuation inputs, debt covenant monitoring, and disclosure preparation."),
        ],
        "Tax": [
            ("Official price data", "Use official land price / assessed value APIs, CSV upload, or documented proxy assumptions."),
            ("Holding tax", "Separate land, building, urban area, and local education tax effects before interpreting total burden."),
            ("Cash flow", "Compare additional holding-tax outflow with FFO and distribution capacity."),
        ],
        "Methodology & Data Sources": [
            ("Source basis", "Review which tables come from DART, ECOS, official land price data, or bundled CSV files."),
            ("Limitations", "Treat results as preliminary screening outputs, not formal audit, tax, valuation, legal, or investment opinions."),
            ("Versioning", "Future material updates should increment sequentially to v12, v13, and so on."),
        ],
    }
    return pd.DataFrame(rows[selected_mode], columns=["Area", "Recommended Check"])


def compact_fig(fig, height=245):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=46, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def fmt_mn_to_bn(value):
    if _is_na(value):
        return "N/A"
    return f"{float(value)/1000:,.1f} bn KRW"


def fmt_metric_value(row, field):
    value = row[field]
    unit = row["unit"]
    if _is_na(value):
        return "N/A"
    if unit == "mn KRW":
        return fmt_mn_to_bn(value)
    if unit == "%":
        return format_pct_from_100(value)
    if unit == "x":
        return format_ratio(value)
    return str(value)
