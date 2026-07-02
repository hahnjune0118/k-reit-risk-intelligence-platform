"""Optional local script to refresh the REIT peer snapshot from DART.

This script is intentionally not imported or executed by the Streamlit app.
It preserves the existing snapshot if DART is unavailable or a fetch fails.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api_dart import fetch_dart_annual_financial_history  # noqa: E402
from api_manager import sanitize_secret_text  # noqa: E402


DATA_DIR = PROJECT_ROOT / "data"
MASTER_PATH = DATA_DIR / "reit_master.csv"
SNAPSHOT_PATH = DATA_DIR / "reit_peer_snapshot.csv"


def _load_existing_snapshot() -> pd.DataFrame:
    if SNAPSHOT_PATH.exists():
        return pd.read_csv(SNAPSHOT_PATH)
    return pd.DataFrame()


def _snapshot_row_from_dart(master_row: pd.Series, history: pd.DataFrame) -> dict | None:
    if history is None or history.empty:
        return None
    latest = history.sort_values("year").iloc[-1]
    total_assets = latest.get("total_assets_mn_krw")
    investment_property = latest.get("investment_property_mn_krw")
    borrowings_total = latest.get("interest_bearing_debt_mn_krw")
    operating_revenue = latest.get("revenue_mn_krw")
    operating_income = latest.get("operating_income_mn_krw")
    net_income = latest.get("net_income_mn_krw")
    ffo_proxy = net_income
    return {
        "company_name": master_row["company_name"],
        "year": int(latest.get("year")),
        "period": f"{int(latest.get('year'))}A",
        "total_assets": total_assets,
        "investment_property": investment_property,
        "borrowings_total": borrowings_total,
        "borrowings_current": pd.NA,
        "interest_expense": pd.NA,
        "operating_revenue": operating_revenue,
        "operating_income": operating_income,
        "net_income": net_income,
        "operating_cash_flow": pd.NA,
        "ffo_proxy": ffo_proxy,
        "dividends": pd.NA,
        "estimated_holding_tax": pd.NA,
        "official_price_total": pd.NA,
        "source_type": "dart_optional_refresh",
        "last_updated": pd.Timestamp.today().strftime("%Y-%m-%d"),
    }


def main() -> int:
    api_key = os.getenv("DART_API_KEY", "").strip()
    if not api_key:
        print("DART 데이터 연결값이 없어 기존 snapshot을 유지합니다.")
        return 0
    if not MASTER_PATH.exists():
        print(f"마스터 파일이 없습니다: {MASTER_PATH}")
        return 1

    master = pd.read_csv(MASTER_PATH)
    existing = _load_existing_snapshot()
    refreshed_rows = []

    for _, row in master.iterrows():
        company_name = str(row.get("company_name", "")).strip()
        stock_code = str(row.get("stock_code", "")).strip().zfill(6)
        if not company_name or not stock_code:
            continue
        try:
            history, _, status = fetch_dart_annual_financial_history(
                api_key,
                stock_code=stock_code,
                corp_name_keyword=company_name,
                years_back=1,
            )
            if status != "connected" or history.empty:
                print(f"{company_name}: 갱신 건너뜀 - {sanitize_secret_text(status)}")
                continue
            row_out = _snapshot_row_from_dart(row, history)
            if row_out:
                refreshed_rows.append(row_out)
                print(f"{company_name}: DART snapshot 후보 생성")
        except Exception as exc:
            print(f"{company_name}: 갱신 실패 - {sanitize_secret_text(exc)}")

    if not refreshed_rows:
        print("갱신 가능한 행이 없어 기존 snapshot을 유지합니다.")
        return 0

    refreshed = pd.DataFrame(refreshed_rows)
    if existing.empty:
        output = refreshed
    else:
        preserved = existing[~existing["company_name"].isin(refreshed["company_name"])]
        output = pd.concat([preserved, refreshed], ignore_index=True)
    output.to_csv(SNAPSHOT_PATH, index=False, encoding="utf-8-sig")
    print(f"snapshot 저장 완료: {SNAPSHOT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
