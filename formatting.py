import re

import pandas as pd
import streamlit as st


def _is_na(value) -> bool:
    try:
        return pd.isna(value)
    except Exception:
        return value is None


def format_mn_krw(value):
    if _is_na(value):
        return "N/A"
    return f"{float(value):,.0f}백만원"


def format_bn_krw(value):
    if _is_na(value):
        return "N/A"
    return f"{float(value) / 1000:,.1f}십억원"


def format_trn_krw_from_mn(value):
    if _is_na(value):
        return "N/A"
    return f"{float(value) / 1_000_000:,.2f}조원"


def format_pct_from_100(value):
    if _is_na(value):
        return "N/A"
    return f"{float(value):.1f}%"


def format_ratio(value):
    if _is_na(value):
        return "N/A"
    return f"{float(value):.2f}x"


def format_years(value):
    if _is_na(value):
        return "N/A"
    return f"{float(value):.2f}년"


def format_score(value):
    if _is_na(value):
        return "N/A"
    return f"{float(value):.1f}"


def extract_number(value):
    """Extract the first numeric token from disclosed fields that mix numbers and notes."""
    if _is_na(value):
        return pd.NA
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "")
    match = re.search(r"[-+]?\d*\.?\d+", text)
    if not match:
        return pd.NA
    return float(match.group())


def add_download_button(df: pd.DataFrame, label: str, file_name: str):
    st.download_button(
        label=label,
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=file_name,
        mime="text/csv",
        width="stretch",
    )


def _safe_float(value):
    try:
        if value is None or pd.isna(value):
            return pd.NA
        return float(str(value).replace(",", ""))
    except Exception:
        return pd.NA


def format_bp(value):
    if _is_na(value):
        return "N/A"
    return f"{float(value):+.0f}bp"


def nearest_25bp(value):
    if _is_na(value):
        return pd.NA
    return round(float(value) / 25) * 25
