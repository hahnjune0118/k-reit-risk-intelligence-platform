from pathlib import Path

import pandas as pd

from api_dart import fetch_dart_annual_financial_history
from config import DATA_DIR
from metric_definitions import derive_book_nav_proxy, derive_ffo_proxy, derive_net_debt


REIT_MASTER_PATH = DATA_DIR / "reit_master.csv"
PEER_SNAPSHOT_PATH = DATA_DIR / "reit_peer_snapshot.csv"


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_reit_master(path: Path = REIT_MASTER_PATH) -> pd.DataFrame:
    df = _read_csv(path)
    if df.empty:
        return df
    for col in ["market_cap_rank", "market_cap"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "stock_code" in df.columns:
        df["stock_code"] = df["stock_code"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
    if "dart_corp_code" in df.columns:
        df["dart_corp_code"] = df["dart_corp_code"].apply(
            lambda value: "" if pd.isna(value) else str(value).replace(".0", "").zfill(8)
        )
    sort_cols = [col for col in ["market_cap_rank", "market_cap", "company_name"] if col in df.columns]
    if "market_cap" in sort_cols:
        ascending = [True if col != "market_cap" else False for col in sort_cols]
        return df.sort_values(sort_cols, ascending=ascending).reset_index(drop=True)
    return df.sort_values(sort_cols).reset_index(drop=True) if sort_cols else df.reset_index(drop=True)


def format_company_option(row: pd.Series) -> str:
    rank = row.get("market_cap_rank", pd.NA)
    rank_label = f"{int(rank)}위 " if pd.notna(rank) else ""
    stock_code = str(row.get("stock_code", "")).zfill(6)
    return f"{rank_label}{row.get('company_name', '')} ({stock_code})"


def company_options(master_df: pd.DataFrame) -> list[str]:
    if master_df is None or master_df.empty:
        return ["1위 SK리츠 (395400)"]
    return [format_company_option(row) for _, row in master_df.iterrows()]


def _company_name_from_option(option: str) -> str:
    text = str(option)
    if "위 " in text:
        text = text.split("위 ", 1)[1]
    if " (" in text:
        text = text.split(" (", 1)[0]
    return text.strip()


def get_selected_company_profile(selected_company: str, master_df: pd.DataFrame | None = None, peer_snapshot: pd.DataFrame | None = None) -> dict:
    master = master_df if master_df is not None else load_reit_master()
    company_name = _company_name_from_option(selected_company)
    row = pd.Series(dtype="object")
    if master is not None and not master.empty and "company_name" in master.columns:
        matched = master[master["company_name"].astype(str).str.strip() == company_name]
        if not matched.empty:
            row = matched.iloc[0]
    if row.empty:
        row = pd.Series({"company_name": company_name or "SK리츠", "stock_code": "395400", "dart_corp_code": ""})

    latest_period = ""
    source_type = "sample_snapshot"
    if peer_snapshot is not None and not peer_snapshot.empty and "company_name" in peer_snapshot.columns:
        peer_rows = peer_snapshot[peer_snapshot["company_name"].astype(str).str.strip() == str(row.get("company_name", company_name)).strip()]
        if not peer_rows.empty:
            latest = peer_rows.sort_values([col for col in ["year", "period"] if col in peer_rows.columns]).iloc[-1]
            latest_period = str(latest.get("period", latest.get("year", "")))
            source_type = str(latest.get("source_type", source_type))

    dart_corp_code = row.get("dart_corp_code", "")
    dart_corp_code = "" if pd.isna(dart_corp_code) else str(dart_corp_code).strip()
    profile = {
        "company_name": str(row.get("company_name", company_name)),
        "stock_code": str(row.get("stock_code", "395400")).zfill(6),
        "dart_corp_code": dart_corp_code,
        "market_cap_rank": row.get("market_cap_rank", pd.NA),
        "market_cap": row.get("market_cap", pd.NA),
        "market": row.get("market", ""),
        "reit_type": row.get("reit_type", ""),
        "main_asset_type": row.get("main_asset_type", ""),
        "main_region": row.get("main_region", ""),
        "latest_period": latest_period,
        "source_type": source_type,
        "data_basis": "시가총액 순위 Snapshot 및 선택 회사 최근 가용 공시자료 기준",
    }
    return profile


def _to_recent_5y_from_snapshot(company_name: str, peer_snapshot: pd.DataFrame) -> pd.DataFrame:
    if peer_snapshot is None or peer_snapshot.empty:
        return pd.DataFrame()
    rows = peer_snapshot[peer_snapshot["company_name"].astype(str).str.strip() == str(company_name).strip()]
    if rows.empty:
        return pd.DataFrame()
    latest = rows.sort_values([col for col in ["year", "period"] if col in rows.columns]).iloc[-1]
    nav, nav_method = derive_book_nav_proxy(
        latest.get("total_assets", pd.NA),
        latest.get("total_liabilities", pd.NA),
    )
    ffo_proxy, ffo_method = derive_ffo_proxy(
        operating_cash_flow=latest.get("operating_cash_flow", pd.NA),
    )
    net_debt, net_debt_method = derive_net_debt(
        latest.get("borrowings_total", pd.NA),
        latest.get("cash_and_cash_equivalents", pd.NA),
        latest.get("short_term_financial_assets", pd.NA),
        short_term_financial_assets_unrestricted=bool(latest.get("short_term_financial_assets_unrestricted", False)),
    )
    record = latest.to_dict()
    record.update(
        {
            "company_name": company_name,
            "ffo_proxy": ffo_proxy,
            "nav": nav,
            "book_nav_proxy": nav,
            "net_debt": net_debt,
            "ffo_proxy_calculation_method": str(latest.get("ffo_method", ffo_method)),
            "nav_calculation_method": nav_method,
            "net_debt_calculation_method": net_debt_method,
            "source_note": str(latest.get("source_note", "최근 가용 Snapshot 기준")),
            "is_fallback": str(latest.get("source_type", "sample_estimate")) != "official_disclosure",
        }
    )
    return _add_compat_columns(pd.DataFrame([record]))


def _normalize_dart_history(dart_history: pd.DataFrame) -> pd.DataFrame:
    if dart_history is None or dart_history.empty:
        return pd.DataFrame()
    df = dart_history.copy()
    rename = {
        "reit_name": "company_name",
        "total_assets_mn_krw": "total_assets",
        "current_assets_mn_krw": "current_assets",
        "cash_and_cash_equivalents_mn_krw": "cash_and_cash_equivalents",
        "short_term_financial_assets_mn_krw": "short_term_financial_assets",
        "investment_property_mn_krw": "investment_property",
        "total_liabilities_mn_krw": "total_liabilities",
        "interest_bearing_debt_mn_krw": "borrowings_total",
        "short_term_borrowings_mn_krw": "short_term_borrowings",
        "current_portion_long_term_debt_mn_krw": "current_portion_long_term_debt",
        "long_term_borrowings_mn_krw": "long_term_borrowings",
        "bonds_mn_krw": "bonds",
        "lease_liabilities_mn_krw": "lease_liabilities",
        "provisions_mn_krw": "provisions",
        "deferred_tax_liabilities_mn_krw": "deferred_tax_liabilities",
        "net_debt_mn_krw": "net_debt",
        "revenue_mn_krw": "operating_revenue",
        "operating_income_mn_krw": "operating_income",
        "net_income_mn_krw": "net_income",
        "interest_expense_mn_krw": "interest_expense",
        "operating_cash_flow_mn_krw": "operating_cash_flow",
        "total_equity_mn_krw": "total_equity",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    ffo_values = []
    ffo_methods = []
    nav_values = []
    nav_methods = []
    net_debt_values = []
    net_debt_methods = []
    for _, row in df.iterrows():
        ffo_value, ffo_method = derive_ffo_proxy(
            operating_cash_flow=row.get("operating_cash_flow", pd.NA),
            operating_income=row.get("operating_income", pd.NA),
            net_income=row.get("net_income", pd.NA),
        )
        nav_value, nav_method = derive_book_nav_proxy(
            row.get("total_assets", pd.NA),
            row.get("total_liabilities", pd.NA),
            row.get("total_equity", pd.NA),
        )
        net_debt_value, net_debt_method = derive_net_debt(
            row.get("borrowings_total", pd.NA),
            row.get("cash_and_cash_equivalents", pd.NA),
            row.get("short_term_financial_assets", pd.NA),
            short_term_financial_assets_unrestricted=False,
        )
        ffo_values.append(ffo_value)
        ffo_methods.append(ffo_method)
        nav_values.append(nav_value)
        nav_methods.append(nav_method)
        net_debt_values.append(net_debt_value)
        net_debt_methods.append(net_debt_method)
    df["ffo_proxy"] = ffo_values
    df["ffo_proxy_calculation_method"] = ffo_methods
    df["nav"] = nav_values
    df["book_nav_proxy"] = nav_values
    df["nav_calculation_method"] = nav_methods
    df["net_debt"] = net_debt_values
    df["net_debt_calculation_method"] = net_debt_methods
    if "interest_expense" not in df.columns:
        df["interest_expense"] = pd.NA
    df["source_type"] = "official_disclosure"
    df["source_note"] = "DART 재무제표 API 기준. 연결재무제표(CFS)를 우선하고 자료가 없으면 별도재무제표(OFS)를 사용합니다."
    df["annualized"] = False
    df["annualization_factor"] = 1.0
    df["ffo_method"] = "operating_cash_flow_proxy"
    df["ffo_limitation"] = "공식 FFO가 아니며 영업활동현금흐름 기반 proxy입니다."
    df["is_fallback"] = False
    keep = [
        "company_name", "year", "total_assets", "investment_property", "borrowings_total",
        "current_assets", "cash_and_cash_equivalents", "short_term_financial_assets",
        "total_liabilities", "short_term_borrowings", "current_portion_long_term_debt",
        "long_term_borrowings", "bonds", "lease_liabilities", "provisions",
        "deferred_tax_liabilities", "net_debt", "operating_revenue", "operating_income",
        "net_income", "operating_cash_flow", "interest_expense", "ffo_proxy", "nav",
        "book_nav_proxy", "source_type", "source_note", "financial_statement_scope",
        "ffo_proxy_calculation_method", "nav_calculation_method", "net_debt_calculation_method",
        "annualized", "annualization_factor", "ffo_method", "ffo_limitation", "is_fallback",
    ]
    return _add_compat_columns(df[[col for col in keep if col in df.columns]])


def _add_compat_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    compat = {
        "total_assets": "total_assets_mn_krw",
        "investment_property": "investment_property_mn_krw",
        "borrowings_total": "interest_bearing_debt_mn_krw",
        "operating_revenue": "revenue_mn_krw",
        "operating_income": "operating_income_mn_krw",
        "net_income": "net_income_mn_krw",
        "ffo_proxy": "ffo_mn_krw",
        "book_nav_proxy": "nav_mn_krw",
    }
    for source, target in compat.items():
        if source in out.columns and target not in out.columns:
            out[target] = out[source]
    if "period_end" not in out.columns and "year" in out.columns:
        out["period_end"] = pd.to_datetime(out["year"].astype("Int64").astype(str) + "-12-31", errors="coerce")
    return out.sort_values("year").tail(5).reset_index(drop=True)


def get_recent_5y_financials(
    company_profile: dict,
    peer_snapshot: pd.DataFrame,
    dart_api_key: str = "",
) -> tuple[pd.DataFrame, str]:
    company_name = company_profile.get("company_name", "")
    if dart_api_key:
        dart_history, _reports, dart_status = fetch_dart_annual_financial_history(
            dart_api_key,
            company_profile.get("stock_code", ""),
            company_name,
            years_back=5,
        )
        normalized = _normalize_dart_history(dart_history)
        if not normalized.empty:
            return normalized, "DART 선택 회사 최근 5개 사업연도 기준"
        status = f"DART 조회 제한: {dart_status}"
    else:
        status = "DART 연결 설정 없음"

    snapshot_history = _to_recent_5y_from_snapshot(company_name, peer_snapshot)
    if not snapshot_history.empty:
        snapshot_history["source_note"] = snapshot_history.get("source_note", "Snapshot fallback")
        return snapshot_history, f"최근 가용 Snapshot 기준 / {status}"

    return pd.DataFrame(), "예시 데이터 기준"
