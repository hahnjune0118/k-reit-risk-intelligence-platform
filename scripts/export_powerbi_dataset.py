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
    from data_source_policy import SOURCE_POLICIES, dominant_source_type
    from metric_definitions import derive_book_nav_proxy, derive_net_debt
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
        "analysis_year",
        "year",
        "period",
        "period_end",
        "reporting_period",
        "flow_months",
        "annualized",
        "annualization_factor",
        "total_assets_eok",
        "total_liabilities_eok",
        "current_assets_eok",
        "current_liabilities_eok",
        "investment_property_eok",
        "borrowings_total_eok",
        "borrowings_current_eok",
        "short_term_borrowings_eok",
        "current_portion_long_term_debt_eok",
        "long_term_borrowings_eok",
        "bonds_eok",
        "lease_liabilities_eok",
        "short_term_financial_assets_eok",
        "interest_expense_eok",
        "operating_revenue_eok",
        "operating_income_eok",
        "net_income_eok",
        "operating_cash_flow_eok",
        "ffo_eok",
        "dividends_eok",
        "estimated_holding_tax_eok",
        "official_price_total_eok",
        "interest_bearing_debt_eok",
        "provisions_eok",
        "deferred_tax_liabilities_eok",
        "cash_and_cash_equivalents_eok",
        "net_debt_eok",
        "book_nav_proxy_eok",
        "ffo_proxy_eok",
        "holding_tax_to_ffo",
        "holding_tax_to_operating_revenue",
        "official_price_to_investment_property",
        "debt_to_assets",
        "current_debt_to_total_debt",
        "interest_expense_to_ffo",
        "dividend_to_ffo",
        "holding_tax_to_ffo_percentile",
        "source_type",
        "source_label",
        "source_name",
        "source_date",
        "source_note",
        "financial_statement_scope",
        "financial_source_type",
        "tax_source_type",
        "ffo_method",
        "ffo_limitation",
        "interest_bearing_debt_method",
        "interest_bearing_debt_completeness",
        "is_fallback",
        "calculation_method",
        "latest_year",
    ],
    "fact_tax_bridge.csv": [
        "stock_code",
        "company_name",
        "stage_order",
        "stage_label",
        "value",
        "display_value",
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
        "threshold",
        "review_direction",
        "evidence_request",
        "work_type",
        "data_basis",
        "source_limitation",
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
        "calculation_model",
        "tax_scope",
        "tax_component_status",
        "taxpayer_status",
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
        "rate_reconciled",
        "period_aligned",
        "taxpayer_confirmed",
        "tax_components_complete",
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
    "dim_period.csv": [
        "analysis_year",
        "period_label",
        "is_current_snapshot",
    ],
    "fact_metric_lineage.csv": [
        "stock_code",
        "company_name",
        "analysis_year",
        "financial_year",
        "reporting_period",
        "metric_name",
        "source_type",
        "source_name",
        "source_date",
        "source_note",
        "statement_scope",
        "is_fallback",
        "calculation_method",
        "limitation",
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


def build_dim_period(peer_snapshot: pd.DataFrame, tax_snapshot: pd.DataFrame) -> pd.DataFrame:
    years = set(pd.to_numeric(peer_snapshot.get("year", pd.Series(dtype="float64")), errors="coerce").dropna().astype(int))
    years.update(pd.to_numeric(tax_snapshot.get("latest_year", pd.Series(dtype="float64")), errors="coerce").dropna().astype(int))
    current_year = max(years) if years else pd.Timestamp.today().year
    return pd.DataFrame(
        [
            {
                "analysis_year": int(year),
                "period_label": f"{int(year)} 공개 분석 Snapshot",
                "is_current_snapshot": int(year) == int(current_year),
            }
            for year in sorted(years)
        ],
        columns=OUTPUT_COLUMNS["dim_period.csv"],
    )


def _fact_reit_kpi_row(profile: dict, peer_row: pd.Series, source_summary: dict) -> dict:
    latest_year = _latest_year(source_summary, peer_row)
    financial_source_type = peer_row.get("source_type", "data_insufficient")
    tax_source_type = source_summary.get("source_type", peer_row.get("tax_source_type", "data_insufficient"))
    source_type = dominant_source_type(f"{financial_source_type}, {tax_source_type}")
    source_policy = SOURCE_POLICIES.get(source_type, SOURCE_POLICIES["data_insufficient"])
    peer_note = str(source_summary.get("source_note") or "").strip()
    source_note = f"{peer_row.get('source_note', '')} Tax: {peer_note}".strip()
    book_nav, nav_method = derive_book_nav_proxy(
        peer_row.get("total_assets", pd.NA),
        peer_row.get("total_liabilities", pd.NA),
    )
    net_debt, net_debt_method = derive_net_debt(
        peer_row.get("borrowings_total", pd.NA),
        peer_row.get("cash_and_cash_equivalents", pd.NA),
        peer_row.get("short_term_financial_assets", pd.NA),
        short_term_financial_assets_unrestricted=bool(peer_row.get("short_term_financial_assets_unrestricted", False)),
    )
    return {
        "stock_code": profile["stock_code"],
        "company_name": profile["company_name"],
        "analysis_year": latest_year,
        "year": peer_row.get("year", latest_year),
        "period": peer_row.get("period", ""),
        "period_end": peer_row.get("period_end", ""),
        "reporting_period": peer_row.get("reporting_period", ""),
        "flow_months": peer_row.get("flow_months", pd.NA),
        "annualized": peer_row.get("annualized", False),
        "annualization_factor": peer_row.get("annualization_factor", pd.NA),
        "total_assets_eok": _mn_to_eok(peer_row.get("total_assets", pd.NA)),
        "total_liabilities_eok": _mn_to_eok(peer_row.get("total_liabilities", pd.NA)),
        "current_assets_eok": _mn_to_eok(peer_row.get("current_assets", pd.NA)),
        "current_liabilities_eok": _mn_to_eok(peer_row.get("current_liabilities", pd.NA)),
        "investment_property_eok": _mn_to_eok(peer_row.get("investment_property", pd.NA)),
        "borrowings_total_eok": _mn_to_eok(peer_row.get("borrowings_total", pd.NA)),
        "borrowings_current_eok": _mn_to_eok(peer_row.get("borrowings_current", pd.NA)),
        "short_term_borrowings_eok": _mn_to_eok(peer_row.get("short_term_borrowings", pd.NA)),
        "current_portion_long_term_debt_eok": _mn_to_eok(peer_row.get("current_portion_long_term_debt", pd.NA)),
        "long_term_borrowings_eok": _mn_to_eok(peer_row.get("long_term_borrowings", pd.NA)),
        "bonds_eok": _mn_to_eok(peer_row.get("bonds", pd.NA)),
        "lease_liabilities_eok": _mn_to_eok(peer_row.get("lease_liabilities", pd.NA)),
        "short_term_financial_assets_eok": _mn_to_eok(peer_row.get("short_term_financial_assets", pd.NA)),
        "interest_expense_eok": _mn_to_eok(peer_row.get("interest_expense", pd.NA)),
        "operating_revenue_eok": _mn_to_eok(peer_row.get("operating_revenue", pd.NA)),
        "operating_income_eok": _mn_to_eok(peer_row.get("operating_income", pd.NA)),
        "net_income_eok": _mn_to_eok(peer_row.get("net_income", pd.NA)),
        "operating_cash_flow_eok": _mn_to_eok(peer_row.get("operating_cash_flow", pd.NA)),
        "ffo_eok": _mn_to_eok(peer_row.get("ffo_proxy", pd.NA)),
        "dividends_eok": _mn_to_eok(peer_row.get("dividends", pd.NA)),
        "estimated_holding_tax_eok": _mn_to_eok(peer_row.get("estimated_holding_tax", pd.NA)),
        "official_price_total_eok": _mn_to_eok(peer_row.get("official_price_total", pd.NA)),
        "interest_bearing_debt_eok": _mn_to_eok(peer_row.get("borrowings_total", pd.NA)),
        "provisions_eok": _mn_to_eok(peer_row.get("provisions", pd.NA)),
        "deferred_tax_liabilities_eok": _mn_to_eok(peer_row.get("deferred_tax_liabilities", pd.NA)),
        "cash_and_cash_equivalents_eok": _mn_to_eok(peer_row.get("cash_and_cash_equivalents", pd.NA)),
        "net_debt_eok": _mn_to_eok(net_debt),
        "book_nav_proxy_eok": _mn_to_eok(book_nav),
        "ffo_proxy_eok": _mn_to_eok(peer_row.get("ffo_proxy", pd.NA)),
        "holding_tax_to_ffo": peer_row.get("holding_tax_to_ffo", pd.NA),
        "holding_tax_to_operating_revenue": peer_row.get("holding_tax_to_operating_revenue", pd.NA),
        "official_price_to_investment_property": peer_row.get("official_price_to_investment_property", pd.NA),
        "debt_to_assets": peer_row.get("debt_to_assets", pd.NA),
        "current_debt_to_total_debt": peer_row.get("current_debt_to_total_debt", pd.NA),
        "interest_expense_to_ffo": peer_row.get("interest_expense_to_ffo", pd.NA),
        "dividend_to_ffo": peer_row.get("dividend_to_ffo", pd.NA),
        "holding_tax_to_ffo_percentile": peer_row.get("holding_tax_to_ffo_percentile", pd.NA),
        "source_type": source_type,
        "source_label": source_policy.korean_label,
        "source_name": peer_row.get("source_name", "reit_peer_snapshot.csv"),
        "source_date": peer_row.get("source_date", peer_row.get("last_updated", pd.NA)),
        "source_note": source_note,
        "financial_statement_scope": peer_row.get("financial_statement_scope", "Snapshot 기준"),
        "financial_source_type": financial_source_type,
        "tax_source_type": tax_source_type,
        "ffo_method": peer_row.get("ffo_method", "operating_cash_flow_proxy"),
        "ffo_limitation": peer_row.get("ffo_limitation", "공식 FFO가 아닌 proxy"),
        "interest_bearing_debt_method": peer_row.get("interest_bearing_debt_method", ""),
        "interest_bearing_debt_completeness": peer_row.get("interest_bearing_debt_completeness", "data_insufficient"),
        "is_fallback": source_type != "official_disclosure",
        "calculation_method": (
            f"FFO proxy = {peer_row.get('ffo_method', 'operating_cash_flow_proxy')}. "
            f"Book NAV proxy = {nav_method}. Net debt = {net_debt_method}. "
            "Provisions are included in total liabilities but excluded from interest-bearing debt and the borrowings/total-assets numerator."
        ),
        "latest_year": latest_year,
    }


def _metric_lineage_rows(profile: dict, peer_row: pd.Series, source_summary: dict) -> list[dict]:
    analysis_year = _latest_year(source_summary, peer_row)
    financial_source = str(peer_row.get("source_type", "data_insufficient"))
    tax_source = str(source_summary.get("source_type", peer_row.get("tax_source_type", "data_insufficient")))
    financial_name = str(peer_row.get("source_name", "reit_peer_snapshot.csv"))
    financial_date = str(peer_row.get("source_date", peer_row.get("last_updated", "")))
    financial_note = str(peer_row.get("source_note", ""))
    tax_note = str(source_summary.get("source_note", ""))
    scope = str(peer_row.get("financial_statement_scope", "Snapshot 기준"))
    reporting_period = str(peer_row.get("reporting_period", peer_row.get("period", "")))

    specs = [
        ("총자산", financial_source, financial_name, financial_date, financial_note, "공시 또는 Snapshot 직접값", "재무제표 범위와 기준일을 함께 확인"),
        ("총부채", financial_source if pd.notna(_num(peer_row.get("total_liabilities", pd.NA))) else "data_insufficient", financial_name, financial_date, financial_note, "공시 직접값", "총부채 결측 시 장부기준 NAV proxy 미산정"),
        ("투자부동산", financial_source, financial_name, financial_date, financial_note, "공시 또는 Snapshot 직접값", "감정평가 최신성은 별도 확인"),
        ("이자부 차입부채", financial_source, financial_name, financial_date, financial_note, str(peer_row.get("interest_bearing_debt_method", "Snapshot borrowings_total")), str(peer_row.get("interest_bearing_debt_completeness", "data_insufficient"))),
        ("유동성 이자부 차입부채", financial_source, financial_name, financial_date, financial_note, "공식 유동 차입금·유동 사채 계정 합계 또는 Snapshot", "구성계정 완전성 확인 필요"),
        ("현금및현금성자산", financial_source if pd.notna(_num(peer_row.get("cash_and_cash_equivalents", pd.NA))) else "data_insufficient", financial_name, financial_date, financial_note, "공시 직접값", "단기금융자산은 사용제한 확인 전 순차입금에서 차감하지 않음"),
        ("충당부채", financial_source if pd.notna(_num(peer_row.get("provisions", pd.NA))) else "data_insufficient", financial_name, financial_date, financial_note, "공시 직접값", "차입부채·금리충격 분자에서는 제외; 총부채에는 포함"),
        ("장부기준 NAV proxy", financial_source if pd.notna(_num(peer_row.get("total_liabilities", pd.NA))) else "data_insufficient", financial_name, financial_date, financial_note, "총자산 - 총부채", "시가평가 NAV가 아니며 총부채 결측 시 미산정"),
        ("FFO proxy", financial_source, financial_name, financial_date, financial_note, str(peer_row.get("ffo_method", "operating_cash_flow_proxy")), str(peer_row.get("ffo_limitation", "공식 FFO가 아닌 proxy"))),
        ("추정 보유세", tax_source, "reit_tax_snapshot.csv", str(source_summary.get("latest_year", "")), tax_note, "effective-rate estimate 또는 data_insufficient", "자산별 고지서·세목 범위·납세의무자 확인 전 예비 추정"),
        ("보유세 / FFO proxy", dominant_source_type(f"{financial_source}, {tax_source}"), "재무 Snapshot + reit_tax_snapshot.csv", str(analysis_year), f"{financial_note} / {tax_note}", "추정 보유세 / FFO proxy", "서로 다른 source와 기간을 결합한 screening ratio"),
        ("총자산 기준 차입비율", financial_source, financial_name, financial_date, financial_note, "이자부 차입부채 / 총자산", "부동산 담보가치 기준 LTV가 아님"),
    ]
    return [
        {
            "stock_code": profile["stock_code"],
            "company_name": profile["company_name"],
            "analysis_year": analysis_year,
            "financial_year": peer_row.get("year", pd.NA),
            "reporting_period": reporting_period,
            "metric_name": metric_name,
            "source_type": source_type,
            "source_name": source_name,
            "source_date": source_date,
            "source_note": source_note,
            "statement_scope": scope,
            "is_fallback": source_type != "official_disclosure",
            "calculation_method": calculation_method,
            "limitation": limitation,
        }
        for metric_name, source_type, source_name, source_date, source_note, calculation_method, limitation in specs
    ]


def _append_bridge_rows(rows: list[dict], profile: dict, bridge: pd.DataFrame, source_summary: dict, latest_year):
    if bridge is None or bridge.empty:
        return
    for _, row in bridge.iterrows():
        source_type = row.get("source_type", source_summary.get("source_type", "data_insufficient"))
        source_note = row.get("source_note", source_summary.get("source_note", ""))
        interpretation_base = f"{row.get('데이터 기준', '')} / {row.get('source_label', '')} / {row.get('Peer 대비 위치', '')}".strip(" /")
        stage_specs = [
            (1, "공시가격 또는 장부가액", "공시가격 또는 장부가액(억원)", "억원", interpretation_base),
            (2, "과세표준 추정", "과세표준 추정(억원)", "억원", f"{row.get('계산 모델', '')} / 회사 전체 screening 과세표준"),
            (
                3,
                "추정 보유세",
                "추정 보유세(억원)",
                "억원",
                f"적용 실효세율 {_clean(row.get('적용 세율', ''))} / {row.get('세율 기준', '')} / {row.get('계산식', '')}",
            ),
            (4, "FFO proxy 대비", "FFO proxy 대비", "%", "FFO proxy 대비 보유세 부담"),
            (5, "영업수익 대비", "영업수익 대비", "%", "영업수익 대비 보유세 부담"),
        ]
        for stage_order, stage_label, value_col, unit, interpretation in stage_specs:
            value = row.get(value_col, pd.NA)
            if pd.isna(value):
                display_value = "데이터 부족"
            elif unit == "억원":
                display_value = f"{float(value):,.1f}억원"
            else:
                display_value = f"{float(value):.1%}"
            rows.append(
                {
                    "stock_code": profile["stock_code"],
                    "company_name": profile["company_name"],
                    "stage_order": stage_order,
                    "stage_label": stage_label,
                    "value": value,
                    "display_value": display_value,
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
                "threshold": row.get("임계값", ""),
                "review_direction": row.get("검토 방향", ""),
                "evidence_request": row.get("요청자료", ""),
                "work_type": row.get("업무유형", ""),
                "data_basis": row.get("데이터 기준", ""),
                "source_limitation": row.get("source limitation", ""),
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
                "calculation_model": row.get("계산 모델", "data_insufficient"),
                "tax_scope": row.get("tax_scope", "data_insufficient"),
                "tax_component_status": row.get("세목 범위", "data_insufficient"),
                "taxpayer_status": row.get("납세의무자 상태", "data_insufficient"),
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
            "rate_reconciled": bool(validation.get("rate_reconciled", False)),
            "period_aligned": bool(validation.get("period_aligned", False)),
            "taxpayer_confirmed": bool(validation.get("taxpayer_confirmed", False)),
            "tax_components_complete": bool(validation.get("tax_components_complete", False)),
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
        "dim_period.csv": build_dim_period(peer_snapshot, tax_snapshot),
        "fact_metric_lineage.csv": _empty_with_columns("fact_metric_lineage.csv"),
    }

    fact_reit_kpi = []
    fact_tax_bridge = []
    fact_tax_issue = []
    fact_tax_request = []
    fact_tax_reconciliation = []
    fact_ffo_stress = []
    fact_tax_validation = []
    fact_metric_lineage = []

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
        fact_metric_lineage.extend(_metric_lineage_rows(profile, peer_row, source_summary))
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
    tables["fact_metric_lineage.csv"] = pd.DataFrame(fact_metric_lineage, columns=OUTPUT_COLUMNS["fact_metric_lineage.csv"])
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
