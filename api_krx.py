from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st

from config import KRX_KOSPI_DAILY_TRADE_ENDPOINT


def _parse_krx_number(value):
    """Parse KRX strings such as '5,230' or '-' into float."""
    if value is None:
        return pd.NA
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "--", "nan", "None"}:
        return pd.NA
    try:
        return float(text)
    except Exception:
        return pd.NA


def _last_calendar_day_of_month(year: int, month: int) -> datetime:
    if month == 12:
        return datetime(year, 12, 31)
    return datetime(year, month + 1, 1) - timedelta(days=1)


@st.cache_data(ttl=60 * 60)
def fetch_krx_kospi_daily_trade(api_key: str, bas_dd: str, endpoint: str = KRX_KOSPI_DAILY_TRADE_ENDPOINT) -> tuple[pd.DataFrame, str]:
    """Fetch KRX KOSPI daily trading information for one base date.

    KRX endpoint returns all KOSPI stocks for the requested business date.
    The app filters the desired ticker afterwards.
    """
    if not api_key:
        return pd.DataFrame(), "KRX API key not provided"
    if not bas_dd:
        return pd.DataFrame(), "KRX base date not provided"
    try:
        response = requests.get(
            endpoint.strip(),
            params={"basDd": bas_dd},
            headers={"AUTH_KEY": api_key.strip()},
            timeout=15,
        )
        if response.status_code in {401, 403}:
            return pd.DataFrame(), f"KRX authorization failed: HTTP {response.status_code}. Check service approval and AUTH_KEY."
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("OutBlock_1", payload.get("output", payload.get("data", [])))
        if not rows:
            return pd.DataFrame(), payload.get("message", "No KRX rows returned")
        return pd.DataFrame(rows), "connected"
    except Exception as exc:
        return pd.DataFrame(), f"KRX daily trade fetch failed: {exc}"


@st.cache_data(ttl=60 * 60)
def fetch_krx_stock_monthly_history(
    api_key: str,
    stock_code: str = "395400",
    years_back: int = 5,
    endpoint: str = KRX_KOSPI_DAILY_TRADE_ENDPOINT,
) -> tuple[pd.DataFrame, str]:
    """Fetch monthly snapshots of one listed stock from KRX daily trade API.

    For speed and API quota control, this collects one month-end snapshot per month.
    If the exact month-end is a holiday, it searches backward for the latest available trading day.
    """
    if not api_key:
        return pd.DataFrame(), "KRX API key not provided"

    end = datetime.today()
    start_year = end.year - years_back + 1
    targets = []
    for year in range(start_year, end.year + 1):
        for month in range(1, 13):
            if year == end.year and month > end.month:
                continue
            targets.append(_last_calendar_day_of_month(year, month))

    rows = []
    messages = []
    code = str(stock_code).zfill(6)

    for target in targets:
        month_row = None
        month_msg = ""
        for back in range(0, 12):
            day = target - timedelta(days=back)
            bas_dd = day.strftime("%Y%m%d")
            daily, status = fetch_krx_kospi_daily_trade(api_key, bas_dd, endpoint)
            if daily.empty:
                month_msg = status
                continue
            # Typical KRX fields: ISU_CD, ISU_NM, TDD_CLSPRC, MKTCAP, ACC_TRDVOL.
            code_col = "ISU_CD" if "ISU_CD" in daily.columns else None
            if code_col is None:
                month_msg = "KRX response has no ISU_CD column"
                continue
            hit = daily[daily[code_col].astype(str).str.zfill(6) == code]
            if hit.empty:
                month_msg = f"Ticker {code} not found on {bas_dd}"
                continue
            month_row = hit.iloc[0].to_dict()
            month_row["date"] = pd.to_datetime(bas_dd, format="%Y%m%d")
            month_row["year"] = int(day.year)
            month_row["month"] = int(day.month)
            break
        if month_row is not None:
            rows.append(month_row)
        elif month_msg:
            messages.append(f"{target.strftime('%Y-%m')}: {month_msg}")

    if not rows:
        return pd.DataFrame(), "; ".join(messages[:5]) or "No KRX monthly rows fetched"

    out = pd.DataFrame(rows).sort_values("date")
    rename_map = {
        "ISU_CD": "stock_code",
        "ISU_NM": "stock_name",
        "TDD_CLSPRC": "close_price_krw",
        "ACC_TRDVOL": "trading_volume",
        "ACC_TRDVAL": "trading_value_krw",
        "MKTCAP": "market_cap_krw",
        "LIST_SHRS": "listed_shares",
        "FLUC_RT": "daily_return_pct",
    }
    out = out.rename(columns={k: v for k, v in rename_map.items() if k in out.columns})
    for col in ["close_price_krw", "trading_volume", "trading_value_krw", "market_cap_krw", "listed_shares", "daily_return_pct"]:
        if col in out.columns:
            out[col] = out[col].apply(_parse_krx_number)
    if "market_cap_krw" in out.columns:
        out["market_cap_mn_krw"] = pd.to_numeric(out["market_cap_krw"], errors="coerce") / 1_000_000
    out["source"] = "KRX Data Marketplace Open API"
    status = "connected" if not messages else "connected with partial gaps: " + "; ".join(messages[:3])
    return out, status


def build_market_annual_history(krx_history: pd.DataFrame) -> pd.DataFrame:
    """Collapse monthly KRX snapshots into annual last-observation market data."""
    if krx_history is None or krx_history.empty:
        return pd.DataFrame()
    df = krx_history.copy()
    if "date" not in df.columns:
        return pd.DataFrame()
    df["year"] = pd.to_datetime(df["date"], errors="coerce").dt.year
    df = df.dropna(subset=["year"]).sort_values("date")
    annual = df.groupby("year", as_index=False).tail(1).copy()
    keep = [c for c in ["year", "date", "close_price_krw", "market_cap_mn_krw", "trading_volume", "source"] if c in annual.columns]
    return annual[keep].reset_index(drop=True)


def market_snapshot_from_krx(krx_history: pd.DataFrame, latest_nav_mn_krw) -> dict:
    """Latest market price, market cap and P/NAV using KRX data."""
    if krx_history is None or krx_history.empty:
        return {"available": False}
    latest = krx_history.sort_values("date").iloc[-1]
    market_cap = latest.get("market_cap_mn_krw", pd.NA)
    close_price = latest.get("close_price_krw", pd.NA)
    p_nav = market_cap / latest_nav_mn_krw if pd.notna(market_cap) and pd.notna(latest_nav_mn_krw) and latest_nav_mn_krw else pd.NA
    nav_discount = (1 - p_nav) * 100 if pd.notna(p_nav) else pd.NA
    return {
        "available": True,
        "date": latest.get("date"),
        "close_price_krw": close_price,
        "market_cap_mn_krw": market_cap,
        "p_nav": p_nav,
        "nav_discount_pct": nav_discount,
        "source": latest.get("source", "KRX"),
    }


# ==================================================
# v9 Transmission / Market-Implied Risk Helpers
# ==================================================

def parse_uploaded_krx_csv(uploaded_file, stock_code: str = "395400") -> tuple[pd.DataFrame, str]:
    """Parse user-uploaded KRX-like daily/monthly price CSV as fallback.

    Expected columns can be English, KRX API names, or simple Korean labels:
    date/BAS_DD/일자, stock_code/ISU_CD/종목코드, close_price_krw/TDD_CLSPRC/종가,
    market_cap_krw/MKTCAP/시가총액, trading_volume/ACC_TRDVOL/거래량.
    """
    if uploaded_file is None:
        return pd.DataFrame(), "no uploaded KRX CSV"
    last_error = None
    for enc in ["utf-8-sig", "cp949", "euc-kr", "utf-8"]:
        try:
            uploaded_file.seek(0)
            raw = pd.read_csv(uploaded_file, encoding=enc)
            break
        except Exception as exc:
            raw = None
            last_error = exc
    if raw is None or raw.empty:
        return pd.DataFrame(), f"KRX CSV parse failed: {last_error}"

    df = raw.copy()
    rename_candidates = {
        "BAS_DD": "date", "basDd": "date", "bas_dd": "date", "일자": "date", "날짜": "date", "Date": "date",
        "ISU_CD": "stock_code", "isu_cd": "stock_code", "종목코드": "stock_code", "티커": "stock_code",
        "ISU_NM": "stock_name", "종목명": "stock_name", "Name": "stock_name",
        "TDD_CLSPRC": "close_price_krw", "종가": "close_price_krw", "close": "close_price_krw", "Close": "close_price_krw",
        "MKTCAP": "market_cap_krw", "시가총액": "market_cap_krw", "market_cap": "market_cap_krw", "MarketCap": "market_cap_krw",
        "ACC_TRDVOL": "trading_volume", "거래량": "trading_volume", "volume": "trading_volume", "Volume": "trading_volume",
        "ACC_TRDVAL": "trading_value_krw", "거래대금": "trading_value_krw",
    }
    df = df.rename(columns={c: rename_candidates.get(c, c) for c in df.columns})

    if "date" not in df.columns:
        return pd.DataFrame(), "KRX CSV has no date column"
    df["date"] = pd.to_datetime(df["date"].astype(str).str.replace("-", ""), errors="coerce")
    df = df.dropna(subset=["date"])

    if "stock_code" in df.columns:
        code = str(stock_code).zfill(6)
        df = df[df["stock_code"].astype(str).str.zfill(6) == code]
    if df.empty:
        return pd.DataFrame(), "KRX CSV parsed but no matching stock rows"

    for col in ["close_price_krw", "market_cap_krw", "trading_volume", "trading_value_krw"]:
        if col in df.columns:
            df[col] = df[col].apply(_parse_krx_number)
    if "market_cap_mn_krw" not in df.columns and "market_cap_krw" in df.columns:
        df["market_cap_mn_krw"] = pd.to_numeric(df["market_cap_krw"], errors="coerce") / 1_000_000
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["source"] = "user-uploaded KRX CSV"
    keep = [c for c in ["date", "year", "month", "stock_code", "stock_name", "close_price_krw", "market_cap_mn_krw", "trading_volume", "source"] if c in df.columns]
    return df[keep].sort_values("date"), "connected via uploaded KRX CSV"

