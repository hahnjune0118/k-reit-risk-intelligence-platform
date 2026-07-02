from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st

from config import (
    ECOS_KEY_INDICATOR_ENDPOINT,
    ECOS_RATE_SERIES,
    ECOS_STAT_SEARCH_ENDPOINT,
    FALLBACK_MACRO,
)
from formatting import _safe_float
from api_manager import sanitize_secret_text


@st.cache_data(ttl=60 * 60 * 6)
def fetch_ecos_key_indicators(api_key: str) -> tuple[pd.DataFrame, str]:
    """한국은행 ECOS 100대 통계지표를 조회합니다."""
    if not api_key:
        return pd.DataFrame(), "실시간 데이터 연결이 제한되어 예시 데이터를 사용합니다."

    try:
        url = ECOS_KEY_INDICATOR_ENDPOINT.format(api_key=api_key.strip())
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        payload = response.json()
        root = payload.get("KeyStatisticList", {})
        rows = root.get("row", [])
        if not rows:
            message = payload.get("RESULT", {}).get("MESSAGE", "ECOS 응답에 사용할 수 있는 행이 없습니다.")
            return pd.DataFrame(), sanitize_secret_text(message)
        df = pd.DataFrame(rows)
        return df, "connected"
    except Exception as exc:
        return pd.DataFrame(), f"ECOS 호출 실패: {sanitize_secret_text(exc)}"


def macro_value_from_ecos(df: pd.DataFrame, indicator_name: str):
    """Return latest value by matching ECOS key indicator name."""
    if df.empty:
        return pd.NA
    name_cols = [c for c in ["KEYSTAT_NAME", "STAT_NAME", "ITEM_NAME1", "통계명"] if c in df.columns]
    value_cols = [c for c in ["DATA_VALUE", "값"] if c in df.columns]
    if not name_cols or not value_cols:
        return pd.NA
    name_col, value_col = name_cols[0], value_cols[0]
    matched = df[df[name_col].astype(str).str.contains(indicator_name, regex=False, na=False)]
    if matched.empty:
        return pd.NA
    return _safe_float(matched.iloc[0][value_col])


def macro_value_from_ecos_aliases(df: pd.DataFrame, aliases: list[str]):
    for alias in aliases:
        value = macro_value_from_ecos(df, alias)
        if pd.notna(value):
            return value
    return pd.NA


def latest_ecos_rate_from_stat_series(api_key: str, label: str):
    if not api_key or label not in ECOS_RATE_SERIES:
        return pd.NA
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=45)).strftime("%Y%m%d")
    meta = ECOS_RATE_SERIES[label]
    series, status = fetch_ecos_stat_series(
        api_key,
        meta["stat_code"],
        meta["cycle"],
        meta["item_code"],
        start_date,
        end_date,
        count=100,
    )
    if status != "connected" or series.empty:
        return pd.NA
    return _safe_float(series.sort_values("date").iloc[-1]["DATA_VALUE"])


def build_macro_context(api_key: str) -> dict:
    """Build a macro baseline from ECOS when possible, otherwise use labeled fallback values."""
    raw, status = fetch_ecos_key_indicators(api_key)
    base_rate = macro_value_from_ecos_aliases(raw, ["한국은행 기준금리", "기준금리", "Base Rate"])
    gov3y = macro_value_from_ecos_aliases(raw, ["국고채수익률(3년)", "국고채(3년)", "국고채 3년", "Treasury Bond 3"])
    gov5y = macro_value_from_ecos_aliases(raw, ["국고채수익률(5년)", "국고채(5년)", "국고채 5년", "Treasury Bond 5"])
    corp_aa = macro_value_from_ecos_aliases(raw, ["회사채수익률(3년, AA-)", "회사채(3년, AA-)", "회사채 AA-", "Corporate Bond 3"])

    if status == "connected":
        if pd.isna(base_rate):
            base_rate = latest_ecos_rate_from_stat_series(api_key, "기준금리")
        if pd.isna(gov3y):
            gov3y = latest_ecos_rate_from_stat_series(api_key, "국고채 3년")
        if pd.isna(gov5y):
            gov5y = latest_ecos_rate_from_stat_series(api_key, "국고채 5년")
        if pd.isna(corp_aa):
            corp_aa = latest_ecos_rate_from_stat_series(api_key, "회사채 AA- 3년")

    values = {
        "한국은행 기준금리": base_rate,
        "국고채수익률(3년)": gov3y,
        "국고채수익률(5년)": gov5y,
        "회사채수익률(3년, AA-)": corp_aa,
    }
    used_fallback = False
    used_critical_fallback = False
    for key, fallback in FALLBACK_MACRO.items():
        if pd.isna(values.get(key)):
            values[key] = fallback
            used_fallback = True
            if key != "국고채수익률(5년)":
                used_critical_fallback = True

    credit_spread = values["회사채수익률(3년, AA-)"] - values["국고채수익률(3년)"]
    source = "한국은행 ECOS API" if status == "connected" and not used_critical_fallback else "예시 데이터 / ECOS 미연결"
    return {
        "raw": raw,
        "status": status,
        "source": source,
        "base_rate_pct": values["한국은행 기준금리"],
        "gov3y_pct": values["국고채수익률(3년)"],
        "gov5y_pct": values["국고채수익률(5년)"],
        "corp_aa_3y_pct": values["회사채수익률(3년, AA-)"],
        "credit_spread_pct": credit_spread,
        "used_fallback": used_fallback,
        "used_critical_fallback": used_critical_fallback,
    }


@st.cache_data(ttl=60 * 60 * 6)
def fetch_ecos_stat_series(api_key: str, stat_code: str, cycle: str, item_code: str, start_date: str, end_date: str, count: int = 10000) -> tuple[pd.DataFrame, str]:
    """Fetch one ECOS time series with StatisticSearch."""
    if not api_key:
        return pd.DataFrame(), "실시간 데이터 연결이 제한되어 예시 데이터를 사용합니다."
    try:
        url = ECOS_STAT_SEARCH_ENDPOINT.format(
            api_key=api_key.strip(),
            count=count,
            stat_code=stat_code,
            cycle=cycle,
            start_date=start_date,
            end_date=end_date,
            item_code=item_code,
        )
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        payload = response.json()
        root = payload.get("StatisticSearch", {})
        rows = root.get("row", [])
        if not rows:
            msg = payload.get("RESULT", {}).get("MESSAGE", "ECOS 시계열 응답에 사용할 수 있는 행이 없습니다.")
            return pd.DataFrame(), sanitize_secret_text(msg)
        df = pd.DataFrame(rows)
        df["DATA_VALUE"] = pd.to_numeric(df.get("DATA_VALUE"), errors="coerce")
        df["TIME"] = df.get("TIME").astype(str)
        if cycle == "D":
            df["date"] = pd.to_datetime(df["TIME"], format="%Y%m%d", errors="coerce")
        elif cycle == "M":
            df["date"] = pd.to_datetime(df["TIME"] + "01", format="%Y%m%d", errors="coerce")
        else:
            df["date"] = pd.to_datetime(df["TIME"], errors="coerce")
        return df.dropna(subset=["date", "DATA_VALUE"]), "connected"
    except Exception as exc:
        return pd.DataFrame(), f"ECOS 시계열 호출 실패: {sanitize_secret_text(exc)}"


def fallback_macro_annual_history() -> pd.DataFrame:
    """Small labeled fallback so the app remains usable without API keys."""
    return pd.DataFrame([
        {"year": 2021, "기준금리": 0.75, "국고채 3년": 1.80, "회사채 AA- 3년": 2.25},
        {"year": 2022, "기준금리": 2.25, "국고채 3년": 3.20, "회사채 AA- 3년": 4.15},
        {"year": 2023, "기준금리": 3.50, "국고채 3년": 3.60, "회사채 AA- 3년": 4.40},
        {"year": 2024, "기준금리": 3.25, "국고채 3년": 3.10, "회사채 AA- 3년": 3.70},
        {"year": 2025, "기준금리": 2.75, "국고채 3년": 2.60, "회사채 AA- 3년": 3.10},
        {"year": 2026, "기준금리": 2.50, "국고채 3년": 2.75, "회사채 AA- 3년": 3.40},
    ]).assign(source="fallback_sample")


def build_ecos_annual_rate_history(api_key: str, years_back: int = 5) -> tuple[pd.DataFrame, str]:
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=365 * years_back + 45)).strftime("%Y%m%d")
    pieces = []
    messages = []
    for label, meta in ECOS_RATE_SERIES.items():
        series, status = fetch_ecos_stat_series(
            api_key,
            meta["stat_code"],
            meta["cycle"],
            meta["item_code"],
            start_date,
            end_date,
        )
        if series.empty:
            messages.append(f"{label}: {status}")
            continue
        annual = series.assign(year=series["date"].dt.year).groupby("year", as_index=False)["DATA_VALUE"].mean()
        annual = annual.rename(columns={"DATA_VALUE": label})
        pieces.append(annual)
    if not pieces:
        return fallback_macro_annual_history(), "예시 데이터 / ECOS 과거 금리 시계열 미연결"
    out = pieces[0]
    for p in pieces[1:]:
        out = out.merge(p, on="year", how="outer")
    out = out.sort_values("year")
    out["source"] = "한국은행 ECOS StatisticSearch API"
    return out, "connected" if not messages else "; ".join(messages)
