from __future__ import annotations

import logging
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

for logger_name in (
    "streamlit",
    "streamlit.runtime.caching.cache_data_api",
    "streamlit.runtime.scriptrunner_utils.script_run_context",
):
    logging.getLogger(logger_name).setLevel(logging.ERROR)

from calculations_holding_tax_bridge import build_holding_tax_bridge
from calculations_peer import calculate_peer_metrics, load_peer_snapshot
from calculations_tax import summarize_holding_tax_history
from calculations_tax_review_pack import (
    build_ffo_cash_outflow_stress,
    build_holding_tax_reconciliation,
    build_tax_issue_matrix,
    build_tax_request_list,
    build_tax_review_memo,
)
from config import DEFAULT_TAX_ASSUMPTIONS_V14
from dart_financials import load_reit_master
from red_flag_engine import build_tax_red_flags, load_red_flag_rules
from scripts.export_powerbi_dataset import (
    DEFAULT_OUTPUT_DIR,
    _company_profile,
    _latest_kpi_from_peer,
    _peer_row,
    _uncached,
)
from tax_data_loader import (
    build_company_tax_dataset,
    build_tax_history_from_company_tax_data,
    get_tax_source_status,
    get_tax_source_summary,
    load_tax_snapshot,
)
from tax_validation import validate_tax_inputs


OUTPUT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "validation"
    / "v14_1_ground_truth"
    / "representative_company_acceptance.csv"
)

EXPECTED_STOCK_CODES = {
    "SK리츠": "395400",
    "롯데리츠": "330590",
    "ESR켄달스퀘어리츠": "365550",
    "제이알글로벌리츠": "348950",
}


def _number(value):
    result = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return result if pd.notna(result) else pd.NA


def _ratio(numerator, denominator):
    numerator = _number(numerator)
    denominator = _number(denominator)
    if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
        return pd.NA
    return numerator / denominator


def run_acceptance(write_output: bool = True) -> pd.DataFrame:
    master = _uncached(load_reit_master)()
    peer_snapshot = _uncached(load_peer_snapshot)()
    metrics = calculate_peer_metrics(peer_snapshot)
    tax_snapshot = _uncached(load_tax_snapshot)()
    rules = load_red_flag_rules()
    exported_kpi = pd.read_csv(
        DEFAULT_OUTPUT_DIR / "fact_reit_kpi.csv",
        dtype={"stock_code": str},
        encoding="utf-8-sig",
    )
    sk_asset_names = (
        pd.read_csv(PROJECT_ROOT / "data" / "sk_reit_asset_metrics.csv")["asset_name"]
        .dropna()
        .astype(str)
        .tolist()
    )

    rows: list[dict] = []
    for company_name, expected_stock_code in EXPECTED_STOCK_CODES.items():
        errors: list[str] = []
        master_match = master[master["company_name"].eq(company_name)]
        if master_match.empty:
            rows.append({"company_name": company_name, "status": "failed", "errors": "master row 누락"})
            continue

        profile = _company_profile(master_match.iloc[0])
        peer_row = _peer_row(metrics, company_name)
        latest_kpi = _latest_kpi_from_peer(peer_row)
        company_tax = build_company_tax_dataset(company_name, peer_snapshot, profile, tax_snapshot)
        source_summary = get_tax_source_summary(company_name, company_tax)
        tax_history = build_tax_history_from_company_tax_data(company_tax)
        annual_summary = summarize_holding_tax_history(tax_history)
        bridge = build_holding_tax_bridge(
            company_name,
            company_tax,
            peer_snapshot,
            DEFAULT_TAX_ASSUMPTIONS_V14,
        )
        validation = validate_tax_inputs(company_name, company_tax, peer_snapshot)
        reconciliation = build_holding_tax_reconciliation(tax_history, latest_kpi)
        stress = build_ffo_cash_outflow_stress(
            latest_kpi,
            annual_summary,
            DEFAULT_TAX_ASSUMPTIONS_V14["holding_tax_increase_pct"],
            DEFAULT_TAX_ASSUMPTIONS_V14["ffo_stress_pct"],
        )
        flags = build_tax_red_flags(company_name, metrics, rules)
        data_basis = get_tax_source_status(company_name, company_tax)
        issue_matrix = build_tax_issue_matrix(flags, reconciliation, stress, data_basis)
        request_list = build_tax_request_list(
            issue_matrix,
            source_summary.get("source_type", ""),
            validation,
        )
        memo = build_tax_review_memo(
            profile,
            data_basis,
            issue_matrix,
            reconciliation,
            request_list,
            stress,
            source_summary=source_summary,
            bridge=bridge,
            validation=validation,
        )

        stock_code = str(profile.get("stock_code", "")).zfill(6)
        if stock_code != expected_stock_code:
            errors.append(f"종목코드 불일치: {stock_code}")
        analysis_year = int(_number(source_summary.get("latest_year", peer_row.get("year", pd.NA))))
        if analysis_year != 2026:
            errors.append(f"분석연도 불일치: {analysis_year}")

        required_financials = [
            "total_assets",
            "borrowings_total",
            "investment_property",
            "ffo_proxy",
        ]
        if company_name != "제이알글로벌리츠":
            required_financials.extend(
                ["total_liabilities", "cash_and_cash_equivalents"]
            )
        missing_financials = [field for field in required_financials if pd.isna(_number(peer_row.get(field, pd.NA)))]
        if missing_financials:
            errors.append(f"필수 재무값 누락: {', '.join(missing_financials)}")

        estimated_tax = _number(peer_row.get("estimated_holding_tax", pd.NA))
        source_type = str(source_summary.get("source_type", ""))
        if company_name == "제이알글로벌리츠":
            if pd.notna(estimated_tax):
                errors.append("해외자산 회사에 국내 추정 보유세가 적용됨")
            if source_type != "data_insufficient":
                errors.append(f"해외자산 source_type 오류: {source_type}")
        elif pd.isna(estimated_tax):
            errors.append("추정 보유세 누락")

        if issue_matrix.empty:
            errors.append("Issue Matrix 누락")
        if request_list.empty:
            errors.append("Request List 누락")
        if request_list["요청자료"].duplicated().any():
            errors.append("Request List 중복")
        if not all(f"## {section}." in memo for section in range(1, 10)):
            errors.append("Memo 9개 섹션 누락")
        if not str(source_summary.get("source_note", "")).strip():
            errors.append("source_note 누락")

        export_match = exported_kpi[
            exported_kpi["stock_code"].astype(str).str.zfill(6).eq(expected_stock_code)
        ]
        if len(export_match) != 1:
            errors.append(f"Power BI KPI Export 행 수 오류: {len(export_match)}")

        if company_name != "SK리츠":
            rendered = company_tax.astype(str).to_csv(index=False)
            contaminated = [asset for asset in sk_asset_names if asset in rendered]
            if contaminated:
                errors.append(f"SK 자산 데이터 혼입: {', '.join(contaminated)}")

        calculated_tax_to_ffo = _ratio(estimated_tax, peer_row.get("ffo_proxy", pd.NA))
        stored_tax_to_ffo = _number(peer_row.get("holding_tax_to_ffo", pd.NA))
        if pd.notna(calculated_tax_to_ffo) and (
            pd.isna(stored_tax_to_ffo) or abs(calculated_tax_to_ffo - stored_tax_to_ffo) > 1e-9
        ):
            errors.append("보유세/FFO proxy 대사 불일치")

        debt_ratio = _ratio(peer_row.get("borrowings_total", pd.NA), peer_row.get("total_assets", pd.NA))
        interest_cover = _ratio(peer_row.get("ffo_proxy", pd.NA), peer_row.get("interest_expense", pd.NA))

        rows.append(
            {
                "company_name": company_name,
                "stock_code": stock_code,
                "analysis_year": analysis_year,
                "reporting_period": peer_row.get("reporting_period", ""),
                "financial_statement_scope": peer_row.get("financial_statement_scope", ""),
                "total_assets_mn_krw": _number(peer_row.get("total_assets", pd.NA)),
                "total_liabilities_mn_krw": _number(peer_row.get("total_liabilities", pd.NA)),
                "interest_bearing_debt_mn_krw": _number(peer_row.get("borrowings_total", pd.NA)),
                "investment_property_mn_krw": _number(peer_row.get("investment_property", pd.NA)),
                "cash_and_cash_equivalents_mn_krw": _number(peer_row.get("cash_and_cash_equivalents", pd.NA)),
                "provisions_mn_krw": _number(peer_row.get("provisions", pd.NA)),
                "ffo_proxy_mn_krw": _number(peer_row.get("ffo_proxy", pd.NA)),
                "estimated_holding_tax_mn_krw": estimated_tax,
                "holding_tax_to_ffo": stored_tax_to_ffo,
                "borrowings_to_total_assets": debt_ratio,
                "ffo_interest_coverage_proxy": interest_cover,
                "issue_count": len(issue_matrix),
                "request_count": len(request_list),
                "memo_sections": sum(f"## {section}." in memo for section in range(1, 10)),
                "source_type": source_type,
                "source_note": source_summary.get("source_note", ""),
                "is_fallback": source_summary.get("is_fallback", True),
                "non_sk_contamination": False if company_name != "SK리츠" and not any(asset in company_tax.astype(str).to_csv(index=False) for asset in sk_asset_names) else pd.NA,
                "export_rows": len(export_match),
                "status": "passed" if not errors else "failed",
                "errors": " / ".join(errors),
            }
        )

    result = pd.DataFrame(rows)
    if write_output:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    return result


def main() -> int:
    result = run_acceptance(write_output=True)
    print(result[["company_name", "stock_code", "status", "errors"]].to_string(index=False))
    return 0 if result["status"].eq("passed").all() else 1


if __name__ == "__main__":
    raise SystemExit(main())
