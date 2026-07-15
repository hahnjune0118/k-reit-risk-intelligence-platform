import io
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st

from config import DART_CORP_CODE_ENDPOINT, DART_LIST_ENDPOINT, DART_SINGLE_FS_ENDPOINT
from api_manager import sanitize_secret_text
from metric_definitions import derive_interest_bearing_debt


def _to_mn_krw_from_dart_amount(value):
    """Convert DART amount, generally KRW, into mn KRW."""
    if value is None or pd.isna(value):
        return pd.NA
    try:
        cleaned = str(value).replace(",", "").replace(" ", "")
        if cleaned in ["", "-", "nan", "None"]:
            return pd.NA
        return float(cleaned) / 1_000_000
    except Exception:
        return pd.NA


@st.cache_data(ttl=60 * 60 * 6)
def fetch_dart_corp_code_table(api_key: str) -> tuple[pd.DataFrame, str]:
    """Download DART corporate-code ZIP and parse CORPCODE.xml."""
    if not api_key:
        return pd.DataFrame(), "실시간 데이터 연결이 제한되어 예시 데이터를 사용합니다."
    try:
        response = requests.get(DART_CORP_CODE_ENDPOINT, params={"crtfc_key": api_key.strip()}, timeout=20)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            xml_name = next((n for n in zf.namelist() if n.lower().endswith(".xml")), zf.namelist()[0])
            xml_bytes = zf.read(xml_name)
        root = ET.fromstring(xml_bytes)
        rows = []
        for item in root.findall("list"):
            rows.append({
                "corp_code": item.findtext("corp_code"),
                "corp_name": item.findtext("corp_name"),
                "stock_code": item.findtext("stock_code"),
                "modify_date": item.findtext("modify_date"),
            })
        return pd.DataFrame(rows), "connected"
    except Exception as exc:
        return pd.DataFrame(), f"DART 고유번호 조회 실패: {sanitize_secret_text(exc)}"


def resolve_dart_corp_code(api_key: str, stock_code: str = "395400", corp_name_keyword: str = "SK리츠") -> tuple[str, str, str]:
    corp_table, status = fetch_dart_corp_code_table(api_key)
    if corp_table.empty:
        return "", "", status
    stock_code = str(stock_code).strip()
    corp_name_keyword = str(corp_name_keyword).strip()
    matched = corp_table[corp_table["stock_code"].astype(str).str.zfill(6) == stock_code.zfill(6)]
    if matched.empty and corp_name_keyword:
        matched = corp_table[corp_table["corp_name"].astype(str).str.contains(corp_name_keyword, case=False, na=False)]
    if matched.empty:
        return "", "", "DART 고유번호 목록에서 일치하는 회사를 찾지 못했습니다."
    row = matched.iloc[0]
    return str(row["corp_code"]), str(row["corp_name"]), "connected"


def _account_match_text(df: pd.DataFrame) -> pd.Series:
    cols = [col for col in ["account_id", "account_nm", "account_detail", "sj_nm"] if col in df.columns]
    if not cols:
        return pd.Series("", index=df.index, dtype="object")
    text = df[cols].fillna("").astype(str).agg(" ".join, axis=1)
    return text.str.replace(r"\s+", " ", regex=True)


def _match_account_rows(df: pd.DataFrame, patterns: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    account_text = _account_match_text(df)
    mask = pd.Series(False, index=df.index)
    for pattern in patterns:
        mask = mask | account_text.str.fullmatch(pattern, case=False, na=False)
        mask = mask | account_text.str.contains(pattern, case=False, na=False, regex=True)
    return df[mask]


def _select_single_account_amount(df: pd.DataFrame, patterns: list[str]):
    if df.empty:
        return pd.NA
    for pattern in patterns:
        for column in ["account_id", "account_nm", "account_detail"]:
            if column not in df.columns:
                continue
            text = df[column].fillna("").astype(str)
            matched = df[text.str.fullmatch(pattern, case=False, na=False)]
            if matched.empty:
                matched = df[text.str.contains(pattern, case=False, na=False, regex=True)]
            if not matched.empty:
                return _to_mn_krw_from_dart_amount(matched.iloc[0].get("thstrm_amount"))
    return pd.NA


def _sum_account_amounts(df: pd.DataFrame, patterns: list[str]):
    if df.empty:
        return pd.NA
    matched = _match_account_rows(df, patterns)
    if matched.empty:
        return pd.NA
    values = matched["thstrm_amount"].apply(_to_mn_krw_from_dart_amount)
    values = pd.to_numeric(values, errors="coerce").dropna()
    return values.sum() if not values.empty else pd.NA


def _sum_values(values: list):
    numeric = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    return numeric.sum() if not numeric.empty else pd.NA


def _select_interest_bearing_debt_components(rows: pd.DataFrame) -> dict:
    short_term_borrowings = _select_single_account_amount(
        rows,
        ["ifrs.*ShorttermBorrowings", "^단기차입금$", "Short.?term borrowings"],
    )
    current_portion_long_term_debt = _sum_account_amounts(
        rows,
        ["유동성장기.*차입", "유동성.*사채", "Current portion.*borrowings", "Current portion.*bonds"],
    )
    long_term_borrowings = _select_single_account_amount(
        rows,
        ["ifrs.*LongtermBorrowings", "^장기차입금$", "Long.?term borrowings"],
    )
    bonds = _sum_account_amounts(
        rows,
        ["^사채$", "일반사채", "Bonds issued", "Debentures"],
    )
    lease_liabilities = _sum_account_amounts(
        rows,
        ["리스부채", "Lease liabilities"],
    )
    reported_total_debt = _select_single_account_amount(
        rows,
        ["이자부.*부채", "총차입금", "Interest.?bearing debt", "Total borrowings"],
    )
    interest_bearing_debt, debt_method = derive_interest_bearing_debt(
        short_term_borrowings=short_term_borrowings,
        current_portion_long_term_debt=current_portion_long_term_debt,
        long_term_borrowings=long_term_borrowings,
        bonds=bonds,
        lease_liabilities=lease_liabilities,
        fallback_interest_bearing_debt=reported_total_debt,
    )
    completeness = "complete_components" if all(
        pd.notna(value)
        for value in [
            short_term_borrowings,
            current_portion_long_term_debt,
            long_term_borrowings,
            bonds,
            lease_liabilities,
        ]
    ) else "reported_total_fallback" if pd.notna(reported_total_debt) else "data_insufficient"
    return {
        "short_term_borrowings_mn_krw": short_term_borrowings,
        "current_portion_long_term_debt_mn_krw": current_portion_long_term_debt,
        "long_term_borrowings_mn_krw": long_term_borrowings,
        "bonds_mn_krw": bonds,
        "lease_liabilities_mn_krw": lease_liabilities,
        "interest_bearing_debt_mn_krw": interest_bearing_debt,
        "interest_bearing_debt_method": debt_method,
        "interest_bearing_debt_completeness": completeness,
    }


@st.cache_data(ttl=60 * 60 * 6)
def fetch_dart_single_year_financials(api_key: str, corp_code: str, year: int, fs_div: str = "CFS") -> tuple[pd.DataFrame, str]:
    """Fetch one year's annual-report financial statement rows from OpenDART."""
    if not api_key or not corp_code:
        return pd.DataFrame(), "DART 데이터 연결 설정 또는 회사 고유번호가 없어 예시 데이터를 사용합니다."
    params = {
        "crtfc_key": api_key.strip(),
        "corp_code": corp_code,
        "bsns_year": str(year),
        "reprt_code": "11011",  # annual report
        "fs_div": fs_div,
    }
    try:
        response = requests.get(DART_SINGLE_FS_ENDPOINT, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "000":
            return pd.DataFrame(), sanitize_secret_text(payload.get("message", "DART 재무제표 응답 상태가 정상(000)이 아닙니다."))
        rows = payload.get("list", [])
        if not rows:
            return pd.DataFrame(), "DART 재무제표 응답에 사용할 수 있는 행이 없습니다."
        return pd.DataFrame(rows), "connected"
    except Exception as exc:
        return pd.DataFrame(), f"DART 재무제표 조회 실패: {sanitize_secret_text(exc)}"


@st.cache_data(ttl=60 * 60 * 6)
def fetch_dart_recent_report_list(api_key: str, corp_code: str, years_back: int = 5) -> tuple[pd.DataFrame, str]:
    """Fetch recent DART disclosure list and keep annual reports."""
    if not api_key or not corp_code:
        return pd.DataFrame(), "DART 데이터 연결 설정 또는 회사 고유번호가 없어 예시 데이터를 사용합니다."
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=365 * years_back + 45)).strftime("%Y%m%d")
    params = {
        "crtfc_key": api_key.strip(),
        "corp_code": corp_code,
        "bgn_de": start_date,
        "end_de": end_date,
        "page_no": 1,
        "page_count": 100,
    }
    try:
        response = requests.get(DART_LIST_ENDPOINT, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "000":
            return pd.DataFrame(), sanitize_secret_text(payload.get("message", "DART 공시 목록 응답 상태가 정상(000)이 아닙니다."))
        rows = pd.DataFrame(payload.get("list", []))
        if rows.empty:
            return rows, "DART 공시 목록 응답에 사용할 수 있는 행이 없습니다."
        if "report_nm" in rows.columns:
            rows = rows[rows["report_nm"].astype(str).str.contains("사업보고서", na=False)].copy()
        return rows, "connected"
    except Exception as exc:
        return pd.DataFrame(), f"DART 공시 목록 조회 실패: {sanitize_secret_text(exc)}"


@st.cache_data(ttl=60 * 60 * 6)
def fetch_dart_annual_financial_history(api_key: str, stock_code: str = "395400", corp_name_keyword: str = "SK리츠", years_back: int = 5) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Fetch recent annual K-IFRS financials and annual-report list for one listed company."""
    if not api_key:
        return pd.DataFrame(), pd.DataFrame(), "실시간 데이터 연결이 제한되어 예시 데이터를 사용합니다."
    corp_code, corp_name, status = resolve_dart_corp_code(api_key, stock_code, corp_name_keyword)
    if not corp_code:
        return pd.DataFrame(), pd.DataFrame(), status

    reports, report_status = fetch_dart_recent_report_list(api_key, corp_code, years_back)
    end_year = datetime.today().year - 1
    start_year = end_year - years_back + 1
    records = []
    messages = []
    for year in range(start_year, end_year + 1):
        fs_div_used = "CFS"
        rows, row_status = fetch_dart_single_year_financials(api_key, corp_code, year, "CFS")
        if rows.empty:
            fs_div_used = "OFS"
            rows, row_status = fetch_dart_single_year_financials(api_key, corp_code, year, "OFS")
        if rows.empty:
            messages.append(f"{year}: {row_status}")
            continue
        debt_components = _select_interest_bearing_debt_components(rows)
        cash = _select_single_account_amount(
            rows,
            ["ifrs.*CashAndCashEquivalents", "현금및현금성자산", "Cash and cash equivalents"],
        )
        short_term_financial_assets = _sum_account_amounts(
            rows,
            ["단기금융", "단기투자", "유동금융자산", "Short.?term financial assets", "Current financial assets"],
        )
        total_assets = _select_single_account_amount(rows, ["ifrs-full_Assets\\b", "자산총계", "^자산$"])
        total_liabilities = _select_single_account_amount(rows, ["ifrs-full_Liabilities\\b", "부채총계", "^부채$"])
        investment_property = _select_single_account_amount(
            rows,
            ["ifrs.*InvestmentProperty", "투자부동산", "Investment property"],
        )
        operating_cash_flow = _select_single_account_amount(
            rows,
            ["영업활동.*현금흐름", "영업활동.*순현금", "Cash flows from operating activities"],
        )
        records.append({
            "reit_name": corp_name,
            "ticker": stock_code,
            "year": int(year),
            "period_end": pd.Timestamp(year=year, month=12, day=31),
            "basis": "DART annual report K-IFRS auto-fetch",
            "financial_statement_scope": "연결재무제표(CFS)" if fs_div_used == "CFS" else "별도재무제표(OFS)",
            "fs_div": fs_div_used,
            "source_document": "OpenDART fnlttSinglAcntAll annual report",
            "total_assets_mn_krw": total_assets,
            "current_assets_mn_krw": _select_single_account_amount(rows, ["ifrs-full_CurrentAssets\\b", "유동자산", "Current assets"]),
            "cash_and_cash_equivalents_mn_krw": cash,
            "short_term_financial_assets_mn_krw": short_term_financial_assets,
            "investment_property_mn_krw": investment_property,
            "total_liabilities_mn_krw": total_liabilities,
            "current_liabilities_mn_krw": _select_single_account_amount(rows, ["ifrs-full_CurrentLiabilities\\b", "유동부채", "Current liabilities"]),
            "total_equity_mn_krw": _select_single_account_amount(rows, ["자본총계", "^자본$", "Equity"]),
            **debt_components,
            "provisions_mn_krw": _sum_account_amounts(rows, ["충당부채", "Provision"]),
            "deferred_tax_liabilities_mn_krw": _select_single_account_amount(rows, ["이연법인세부채", "Deferred tax liabilities"]),
            "revenue_mn_krw": _select_single_account_amount(rows, ["영업수익", "매출액", "^수익$", "Revenue"]),
            "operating_income_mn_krw": _select_single_account_amount(rows, ["영업이익", "Operating income"]),
            "net_income_mn_krw": _select_single_account_amount(rows, ["당기순이익", "분기순이익", "Profit"]),
            "interest_expense_mn_krw": _select_single_account_amount(rows, ["이자비용", "Interest expense", "Finance costs"]),
            "operating_cash_flow_mn_krw": operating_cash_flow,
            "source_confidence": "dart_api_auto_fetched",
        })
    history = pd.DataFrame(records)
    if not history.empty:
        history["gross_ltv_interest_debt_to_assets_pct"] = history["interest_bearing_debt_mn_krw"] / history["total_assets_mn_krw"] * 100
        cash = pd.to_numeric(history.get("cash_and_cash_equivalents_mn_krw", pd.Series(pd.NA, index=history.index)), errors="coerce")
        debt = pd.to_numeric(history["interest_bearing_debt_mn_krw"], errors="coerce")
        history["net_debt_mn_krw"] = debt - cash
        history.loc[cash.isna() | debt.isna(), "net_debt_mn_krw"] = pd.NA
        history["net_debt_method"] = "이자부 차입부채 - 현금및현금성자산; 단기금융자산은 사용제한 미확인으로 차감 제외"
    status_msg = "connected" if not history.empty else "; ".join(messages)
    if report_status != "connected":
        status_msg = f"{status_msg}; report-list: {report_status}"
    return history, reports, status_msg

