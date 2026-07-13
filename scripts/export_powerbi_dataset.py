from __future__ import annotations

import argparse
import contextlib
import io
import logging
import os
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("STREAMLIT_LOG_LEVEL", "error")
for _logger_name in (
    "streamlit",
    "streamlit.runtime.caching.cache_data_api",
    "streamlit.runtime.scriptrunner_utils.script_run_context",
):
    logging.getLogger(_logger_name).setLevel(logging.ERROR)

# Streamlit-decorated loaders emit bare-mode cache warnings at import time.
with contextlib.redirect_stderr(io.StringIO()):
    from calculations_holding_tax_bridge import build_holding_tax_bridge
    from calculations_peer import calculate_peer_metrics, get_company_peer_profile, load_peer_snapshot
    from calculations_tax import summarize_holding_tax_history
    from calculations_tax_review_pack import (
        build_ffo_cash_outflow_stress,
        build_holding_tax_reconciliation,
        build_tax_issue_matrix,
        build_tax_request_list,
    )
    from config import DEFAULT_TAX_ASSUMPTIONS_V14
    from dart_financials import load_reit_master
    from data_source_policy import SOURCE_POLICIES
    from red_flag_engine import build_tax_red_flags, load_red_flag_rules
    from tax_data_loader import (
        build_company_tax_dataset,
        build_tax_history_from_company_tax_data,
        get_tax_source_status,
        get_tax_source_summary,
        load_tax_snapshot,
    )
    from tax_validation import validate_tax_inputs


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "powerbi" / "exports"

OUTPUT_COLUMNS = {
    "dim_reit.csv": [
        "stock_code",
        "company_name",
        "dart_corp_code",
        "market_cap_rank",
        "market_cap",
        "market",
        "reit_type",
        "main_asset_type",
        "main_region",
        "note",
    ],
    "fact_reit_kpi.csv": [
        "stock_code",
        "company_name",
        "year",
        "total_assets_eok",
        "investment_property_eok",
        "borrowings_total_eok",
        "borrowings_current_eok",
        "interest_expense_eok",
        "operating_revenue_eok",
        "operating_income_eok",
        "net_income_eok",
        "operating_cash_flow_eok",
        "ffo_eok",
        "dividends_eok",
        "estimated_holding_tax_eok",
        "official_price_total_eok",
        "holding_tax_to_ffo",
        "holding_tax_to_operating_revenue",
        "official_price_to_investment_property",
        "debt_to_assets",
        "current_debt_to_total_debt",
        "interest_expense_to_ffo",
        "dividend_to_ffo",
        "holding_tax_to_ffo_percentile",
        "source_type",
        "source_note",
        "latest_year",
    ],
    "fact_tax_bridge.csv": [
        "stock_code",
        "company_name",
        "stage_order",
        "stage_label",
        "value",
        "unit",
        "interpretation",
        "source_type",
        "source_note",
        "latest_year",
    ],
    "fact_tax_issue.csv": [
        "stock_code",
        "company_name",
        "tax_issue",
        "risk_level",
        "risk_sort",
        "occurrence_basis",
        "affected_metric",
        "review_direction",
        "evidence_request",
        "work_type",
        "data_basis",
        "source_type",
        "latest_year",
    ],
    "fact_tax_request.csv": [
        "stock_code",
        "company_name",
        "request_item",
        "request_purpose",
        "related_issue",
        "priority",
        "priority_sort",
        "review_area",
        "source_trigger",
        "note",
        "source_type",
        "latest_year",
    ],
    "fact_tax_reconciliation.csv": [
        "stock_code",
        "company_name",
        "asset_name",
        "region",
        "book_value_eok",
        "official_price_eok",
        "official_price_to_book",
        "estimated_tax_base_eok",
        "estimated_holding_tax_eok",
        "holding_tax_to_ffo",
        "official_price_growth_5y",
        "review_required",
        "source_type",
        "source_note",
        "latest_year",
    ],
    "fact_ffo_stress.csv": [
        "stock_code",
        "company_name",
        "scenario",
        "scenario_sort",
        "amount_eok",
        "ffo_ratio",
        "interpretation",
        "holding_tax_increase_pct",
        "ffo_stress_pct",
        "source_type",
        "latest_year",
    ],
    "fact_tax_validation.csv": [
        "stock_code",
        "company_name",
        "validation_status",
        "missing_fields",
        "fallback_used",
        "calculation_limitations",
        "source_type",
        "source_note",
        "latest_year",
    ],
    "dim_source_policy.csv": [
        "source_type",
        "korean_label",
        "reliability_level",
        "reliability_sort",
        "allowed_outputs",
        "memo_limitation_text",
        "ui_warning_text",
    ],
}

RISK_SORT = {"높음": 1, "주의": 2, "데이터 부족": 3, "정상": 4}
PRIORITY_SORT = {"높음": 1, "중간": 2, "낮음": 3}
RELIABILITY_SORT = {"높음": 1, "중간": 2, "중간-제한": 3, "추정": 4, "예시": 5, "부족": 6}


def _stock_code(value) -> str:
    text = "" if pd.isna(value) else str(value).strip()
    return text.zfill(6) if text and text.lower() != "nan" else ""


def _num(value):
    return pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]


def _mn_to_eok(value):
    number = _num(value)
    return number / 100 if pd.notna(number) else pd.NA


def _clean(value):
    if isinstance(value, (list, tuple, set)):
        return " / ".join(str(item) for item in value if str(item).strip())
    if isinstance(value, dict):
        return " / ".join(f"{key}: {val}" for key, val in value.items())
    if pd.isna(value):
        return ""
    return str(value)


def _latest_year(source_summary: dict, peer_row) -> object:
    if source_summary.get("latest_year") is not None:
        return source_summary["latest_year"]
    if isinstance(peer_row, pd.Series):
        return peer_row.get("year", pd.NA)
    return pd.NA


def _company_profile(row: pd.Series) -> dict:
    return {
        "company_name": row.get("company_name", ""),
        "stock_code": _stock_code(row.get("stock_code", "")),
        "dart_corp_code": row.get("dart_corp_code", ""),
        "market_cap_rank": row.get("market_cap_rank", pd.NA),
        "market_cap": row.get("market_cap", pd.NA),
        "market": row.get("market", ""),
        "reit_type": row.get("reit_type", ""),
        "main_asset_type": row.get("main_asset_type", ""),
        "main_region": row.get("main_region", ""),
        "note": row.get("note", ""),
    }


def _peer_row(metrics: pd.DataFrame, company_name: str) -> pd.Series:
    row = get_company_peer_profile(metrics, company_name)
    if isinstance(row, dict) and not row:
        return pd.Series(dtype="object")
    return row


def _latest_kpi_from_peer(row: pd.Series) -> pd.Series:
    return pd.Series(
        {
            "ffo_mn_krw": row.get("ffo_proxy", pd.NA),
            "common_dividend_total_mn_krw": row.get("dividends", pd.NA),
            "revenue_mn_krw": row.get("operating_revenue", pd.NA),
            "net_income_mn_krw": row.get("net_income", pd.NA),
        }
    )


def _empty_with_columns(filename: str) -> pd.DataFrame:
    return pd.DataFrame(columns=OUTPUT_COLUMNS[filename])


def _uncached(function):
    return getattr(function, "__wrapped__", function)


def build_dim_reit(master: pd.DataFrame) -> pd.DataFrame:
    out = master.copy()
    out["stock_code"] = out["stock_code"].apply(_stock_code)
    for col in OUTPUT_COLUMNS["dim_reit.csv"]:
        if col not in out.columns:
            out[col] = ""
    return out[OUTPUT_COLUMNS["dim_reit.csv"]]


def build_dim_source_policy() -> pd.DataFrame:
    rows = []
    for source_type, policy in SOURCE_POLICIES.items():
        rows.append(
            {
                "source_type": source_type,
                "korean_label": policy.korean_label,
                "reliability_level": policy.reliability_level,
                "reliability_sort": RELIABILITY_SORT.get(policy.reliability_level, 99),
                "allowed_outputs": " / ".join(policy.allowed_outputs),
                "memo_limitation_text": policy.memo_limitation_text,
                "ui_warning_text": policy.ui_warning_text,
            }
        )
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS["dim_source_policy.csv"])


def _fact_reit_kpi_row(profile: dict, peer_row: pd.Series, source_summary: dict) -> dict:
    latest_year = _latest_year(source_summary, peer_row)
    return {
        "stock_code": profile["stock_code"],
        "company_name": profile["company_name"],
        "year": peer_row.get("year", latest_year),
        "total_assets_eok": _mn_to_eok(peer_row.get("total_assets", pd.NA)),
        "investment_property_eok": _mn_to_eok(peer_row.get("investment_property", pd.NA)),
        "borrowings_total_eok": _mn_to_eok(peer_row.get("borrowings_total", pd.NA)),
        "borrowings_current_eok": _mn_to_eok(peer_row.get("borrowings_current", pd.NA)),
        "interest_expense_eok": _mn_to_eok(peer_row.get("interest_expense", pd.NA)),
        "operating_revenue_eok": _mn_to_eok(peer_row.get("operating_revenue", pd.NA)),
        "operating_income_eok": _mn_to_eok(peer_row.get("operating_income", pd.NA)),
        "net_income_eok": _mn_to_eok(peer_row.get("net_income", pd.NA)),
        "operating_cash_flow_eok": _mn_to_eok(peer_row.get("operating_cash_flow", pd.NA)),
        "ffo_eok": _mn_to_eok(peer_row.get("ffo_proxy", pd.NA)),
        "dividends_eok": _mn_to_eok(peer_row.get("dividends", pd.NA)),
        "estimated_holding_tax_eok": _mn_to_eok(peer_row.get("estimated_holding_tax", pd.NA)),
        "official_price_total_eok": _mn_to_eok(peer_row.get("official_price_total", pd.NA)),
        "holding_tax_to_ffo": peer_row.get("holding_tax_to_ffo", pd.NA),
        "holding_tax_to_operating_revenue": peer_row.get("holding_tax_to_operating_revenue", pd.NA),
        "official_price_to_investment_property": peer_row.get("official_price_to_investment_property", pd.NA),
        "debt_to_assets": peer_row.get("debt_to_assets", pd.NA),
        "current_debt_to_total_debt": peer_row.get("current_debt_to_total_debt", pd.NA),
        "interest_expense_to_ffo": peer_row.get("interest_expense_to_ffo", pd.NA),
        "dividend_to_ffo": peer_row.get("dividend_to_ffo", pd.NA),
        "holding_tax_to_ffo_percentile": peer_row.get("holding_tax_to_ffo_percentile", pd.NA),
        "source_type": source_summary.get("source_type") or peer_row.get("source_type", "data_insufficient"),
        "source_note": source_summary.get("source_note", ""),
        "latest_year": latest_year,
    }


def _append_bridge_rows(rows: list[dict], profile: dict, bridge: pd.DataFrame, source_summary: dict, latest_year):
    if bridge is None or bridge.empty:
        return
    for _, row in bridge.iterrows():
        source_type = row.get("source_type", source_summary.get("source_type", "data_insufficient"))
        source_note = row.get("source_note", source_summary.get("source_note", ""))
        interpretation_base = f"{row.get('데이터 기준', '')} / {row.get('source_label', '')} / {row.get('Peer 대비 위치', '')}".strip(" /")
        stage_specs = [
            (1, "공시가격 또는 장부가액", "공시가격 또는 장부가액(억원)", "억원", interpretation_base),
            (2, "과세표준 추정", "과세표준 추정(억원)", "억원", f"공정시장가액비율 {DEFAULT_TAX_ASSUMPTIONS_V14['fair_market_value_ratio']:.1f}% 기준"),
            (3, "추정 보유세", "추정 보유세(억원)", "억원", f"실효 보유세율 {DEFAULT_TAX_ASSUMPTIONS_V14['effective_holding_tax_rate']:.1f}% 또는 Snapshot 추정값"),
            (4, "FFO proxy 대비", "FFO proxy 대비", "decimal", "FFO proxy 대비 보유세 부담"),
            (5, "영업수익 대비", "영업수익 대비", "decimal", "영업수익 대비 보유세 부담"),
        ]
        for stage_order, stage_label, value_col, unit, interpretation in stage_specs:
            rows.append(
                {
                    "stock_code": profile["stock_code"],
                    "company_name": profile["company_name"],
                    "stage_order": stage_order,
                    "stage_label": stage_label,
                    "value": row.get(value_col, pd.NA),
                    "unit": unit,
                    "interpretation": interpretation,
                    "source_type": source_type,
                    "source_note": source_note,
                    "latest_year": latest_year,
                }
            )


def _append_issue_rows(rows: list[dict], profile: dict, issue_matrix: pd.DataFrame, source_type: str, latest_year):
    if issue_matrix is None or issue_matrix.empty:
        return
    for _, row in issue_matrix.iterrows():
        risk_level = row.get("위험수준", "")
        rows.append(
            {
                "stock_code": profile["stock_code"],
                "company_name": profile["company_name"],
                "tax_issue": row.get("세무 이슈", ""),
                "risk_level": risk_level,
                "risk_sort": RISK_SORT.get(risk_level, 99),
                "occurrence_basis": row.get("발생 근거", ""),
                "affected_metric": row.get("영향받는 지표", ""),
                "review_direction": row.get("검토 방향", ""),
                "evidence_request": row.get("요청자료", ""),
                "work_type": row.get("업무유형", ""),
                "data_basis": row.get("데이터 기준", ""),
                "source_type": source_type,
                "latest_year": latest_year,
            }
        )


def _append_request_rows(rows: list[dict], profile: dict, request_list: pd.DataFrame, source_type: str, latest_year):
    if request_list is None or request_list.empty:
        return
    for _, row in request_list.iterrows():
        priority = row.get("우선순위", "")
        rows.append(
            {
                "stock_code": profile["stock_code"],
                "company_name": profile["company_name"],
                "request_item": row.get("요청자료", ""),
                "request_purpose": row.get("요청 목적", ""),
                "related_issue": row.get("관련 이슈", ""),
                "priority": priority,
                "priority_sort": PRIORITY_SORT.get(priority, 99),
                "review_area": row.get("해당 검토영역", ""),
                "source_trigger": row.get("source trigger", ""),
                "note": row.get("비고", ""),
                "source_type": source_type,
                "latest_year": latest_year,
            }
        )


def _append_reconciliation_rows(rows: list[dict], profile: dict, reconciliation: pd.DataFrame, source_summary: dict, latest_year):
    if reconciliation is None or reconciliation.empty:
        return
    for _, row in reconciliation.iterrows():
        rows.append(
            {
                "stock_code": profile["stock_code"],
                "company_name": profile["company_name"],
                "asset_name": row.get("자산명", ""),
                "region": row.get("지역", ""),
                "book_value_eok": row.get("장부가액(억원)", pd.NA),
                "official_price_eok": row.get("공시가격(억원)", pd.NA),
                "official_price_to_book": row.get("공시가격 / 장부가액", pd.NA),
                "estimated_tax_base_eok": row.get("추정 과세표준(억원)", pd.NA),
                "estimated_holding_tax_eok": row.get("추정 보유세(억원)", pd.NA),
                "holding_tax_to_ffo": row.get("보유세 / FFO proxy", row.get("보유세 / FFO", pd.NA)),
                "official_price_growth_5y": row.get("최근 5년 공시가격 증가율", pd.NA),
                "review_required": row.get("검토 필요 여부", ""),
                "source_type": row.get("source_type", source_summary.get("source_type", "")),
                "source_note": row.get("source_note", source_summary.get("source_note", "")),
                "latest_year": latest_year,
            }
        )


def _append_ffo_stress_rows(rows: list[dict], profile: dict, ffo_stress: pd.DataFrame, source_type: str, latest_year):
    if ffo_stress is None or ffo_stress.empty:
        return
    for idx, row in ffo_stress.reset_index(drop=True).iterrows():
        rows.append(
            {
                "stock_code": profile["stock_code"],
                "company_name": profile["company_name"],
                "scenario": row.get("항목", ""),
                "scenario_sort": idx + 1,
                "amount_eok": row.get("금액(억원)", pd.NA),
                "ffo_ratio": row.get("FFO proxy 대비", row.get("FFO 대비", pd.NA)),
                "interpretation": row.get("주요 해석", ""),
                "holding_tax_increase_pct": DEFAULT_TAX_ASSUMPTIONS_V14["holding_tax_increase_pct"],
                "ffo_stress_pct": DEFAULT_TAX_ASSUMPTIONS_V14["ffo_stress_pct"],
                "source_type": source_type,
                "latest_year": latest_year,
            }
        )


def _append_validation_row(rows: list[dict], profile: dict, validation: dict, source_summary: dict, latest_year):
    rows.append(
        {
            "stock_code": profile["stock_code"],
            "company_name": profile["company_name"],
            "validation_status": validation.get("validation_status", ""),
            "missing_fields": _clean(validation.get("missing_fields", [])),
            "fallback_used": bool(validation.get("fallback_used", False)),
            "calculation_limitations": _clean(validation.get("calculation_limitations", [])),
            "source_type": source_summary.get("source_type", ""),
            "source_note": source_summary.get("source_note", ""),
            "latest_year": latest_year,
        }
    )


def build_powerbi_tables() -> dict[str, pd.DataFrame]:
    master = load_reit_master()
    peer_snapshot = load_peer_snapshot()
    metrics = calculate_peer_metrics(peer_snapshot)
    rules = load_red_flag_rules()
    tax_snapshot = _uncached(load_tax_snapshot)()

    tables: dict[str, pd.DataFrame] = {
        "dim_reit.csv": build_dim_reit(master),
        "fact_reit_kpi.csv": _empty_with_columns("fact_reit_kpi.csv"),
        "fact_tax_bridge.csv": _empty_with_columns("fact_tax_bridge.csv"),
        "fact_tax_issue.csv": _empty_with_columns("fact_tax_issue.csv"),
        "fact_tax_request.csv": _empty_with_columns("fact_tax_request.csv"),
        "fact_tax_reconciliation.csv": _empty_with_columns("fact_tax_reconciliation.csv"),
        "fact_ffo_stress.csv": _empty_with_columns("fact_ffo_stress.csv"),
        "fact_tax_validation.csv": _empty_with_columns("fact_tax_validation.csv"),
        "dim_source_policy.csv": build_dim_source_policy(),
    }

    fact_reit_kpi = []
    fact_tax_bridge = []
    fact_tax_issue = []
    fact_tax_request = []
    fact_tax_reconciliation = []
    fact_ffo_stress = []
    fact_tax_validation = []

    for _, master_row in master.iterrows():
        profile = _company_profile(master_row)
        company_name = profile["company_name"]
        peer_row = _peer_row(metrics, company_name)
        latest_kpi = _latest_kpi_from_peer(peer_row)
        company_tax = build_company_tax_dataset(company_name, peer_snapshot, profile, tax_snapshot)
        source_summary = get_tax_source_summary(company_name, company_tax)
        latest_year = _latest_year(source_summary, peer_row)

        tax_history = build_tax_history_from_company_tax_data(company_tax)
        annual_summary = summarize_holding_tax_history(tax_history)
        tax_bridge = build_holding_tax_bridge(company_name, company_tax, peer_snapshot, DEFAULT_TAX_ASSUMPTIONS_V14)
        validation = validate_tax_inputs(company_name, company_tax, peer_snapshot)
        reconciliation = build_holding_tax_reconciliation(tax_history, latest_kpi)
        ffo_stress = build_ffo_cash_outflow_stress(
            latest_kpi,
            annual_summary,
            DEFAULT_TAX_ASSUMPTIONS_V14["holding_tax_increase_pct"],
            DEFAULT_TAX_ASSUMPTIONS_V14["ffo_stress_pct"],
        )
        flags = build_tax_red_flags(company_name, metrics, rules)
        data_basis = get_tax_source_status(company_name, company_tax)
        issue_matrix = build_tax_issue_matrix(flags, reconciliation, ffo_stress, data_basis)
        request_list = build_tax_request_list(issue_matrix, source_summary.get("source_type", ""), validation)

        fact_reit_kpi.append(_fact_reit_kpi_row(profile, peer_row, source_summary))
        _append_bridge_rows(fact_tax_bridge, profile, tax_bridge, source_summary, latest_year)
        _append_issue_rows(fact_tax_issue, profile, issue_matrix, source_summary.get("source_type", ""), latest_year)
        _append_request_rows(fact_tax_request, profile, request_list, source_summary.get("source_type", ""), latest_year)
        _append_reconciliation_rows(fact_tax_reconciliation, profile, reconciliation, source_summary, latest_year)
        _append_ffo_stress_rows(fact_ffo_stress, profile, ffo_stress, source_summary.get("source_type", ""), latest_year)
        _append_validation_row(fact_tax_validation, profile, validation, source_summary, latest_year)

    tables["fact_reit_kpi.csv"] = pd.DataFrame(fact_reit_kpi, columns=OUTPUT_COLUMNS["fact_reit_kpi.csv"])
    tables["fact_tax_bridge.csv"] = pd.DataFrame(fact_tax_bridge, columns=OUTPUT_COLUMNS["fact_tax_bridge.csv"])
    tables["fact_tax_issue.csv"] = pd.DataFrame(fact_tax_issue, columns=OUTPUT_COLUMNS["fact_tax_issue.csv"])
    tables["fact_tax_request.csv"] = pd.DataFrame(fact_tax_request, columns=OUTPUT_COLUMNS["fact_tax_request.csv"])
    tables["fact_tax_reconciliation.csv"] = pd.DataFrame(fact_tax_reconciliation, columns=OUTPUT_COLUMNS["fact_tax_reconciliation.csv"])
    tables["fact_ffo_stress.csv"] = pd.DataFrame(fact_ffo_stress, columns=OUTPUT_COLUMNS["fact_ffo_stress.csv"])
    tables["fact_tax_validation.csv"] = pd.DataFrame(fact_tax_validation, columns=OUTPUT_COLUMNS["fact_tax_validation.csv"])
    return tables


def write_powerbi_tables(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, int]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    tables = build_powerbi_tables()
    row_counts = {}
    for filename, df in tables.items():
        df = df.copy()
        if "stock_code" in df.columns:
            df["stock_code"] = df["stock_code"].apply(_stock_code)
        df.to_csv(output_path / filename, index=False, encoding="utf-8-sig")
        row_counts[filename] = len(df)
    return row_counts


def main(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, int]:
    return write_powerbi_tables(output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export v14.1 K-REITs Tax workflow tables for Power BI.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for generated CSV files.")
    args = parser.parse_args()
    counts = main(args.output_dir)
    for filename, count in counts.items():
        print(f"{filename}: {count} rows")
