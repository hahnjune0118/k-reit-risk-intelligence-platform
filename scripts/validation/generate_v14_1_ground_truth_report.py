from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "docs" / "validation" / "v14_1_ground_truth"
AS_OF_DATE = "2026-07-14"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        result = float(text)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _csv_number(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _fmt_number(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "-"
    return f"{value:,.{decimals}f}"


def _fmt_pct(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.{decimals}f}%"


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    def clean(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", "<br>")

    output = [
        "| " + " | ".join(clean(header) for header in headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    output.extend("| " + " | ".join(clean(value) for value in row) + " |" for row in rows)
    return "\n".join(output)


PROJECT_COLUMN_BY_METRIC = {
    "total_assets": "total_assets",
    "total_liabilities": None,
    "current_assets": None,
    "cash_and_cash_equivalents": None,
    "short_term_financial_assets": None,
    "investment_property": "investment_property",
    "current_liabilities": None,
    "short_term_borrowings": None,
    "current_portion_long_term_debt": None,
    "long_term_borrowings": None,
    "bonds": None,
    "lease_liabilities": None,
    "provisions": None,
    "deferred_tax_liabilities": None,
    "interest_bearing_debt": "borrowings_total",
    "current_interest_bearing_debt": "borrowings_current",
    "operating_revenue": "operating_revenue",
    "operating_income": "operating_income",
    "net_income": "net_income",
    "interest_expense": "interest_expense",
    "operating_cash_flow": "operating_cash_flow",
    "dividends_paid": "dividends",
    "issued_shares": None,
    "ffo_proxy": "ffo_proxy",
}


METRIC_NAMES = {
    "total_assets": "총자산",
    "total_liabilities": "총부채",
    "current_assets": "유동자산",
    "cash_and_cash_equivalents": "현금및현금성자산",
    "short_term_financial_assets": "단기금융자산",
    "investment_property": "투자부동산",
    "current_liabilities": "유동부채",
    "short_term_borrowings": "단기차입금",
    "current_portion_long_term_debt": "유동성장기차입금 또는 유동성 차입부채",
    "long_term_borrowings": "장기차입금",
    "bonds": "사채",
    "lease_liabilities": "리스부채",
    "provisions": "충당부채",
    "deferred_tax_liabilities": "이연법인세부채",
    "interest_bearing_debt": "이자부 차입부채",
    "current_interest_bearing_debt": "유동성 이자부 차입부채",
    "operating_revenue": "영업수익",
    "operating_income": "영업이익",
    "net_income": "당기순이익",
    "interest_expense": "이자비용(금융원가)",
    "operating_cash_flow": "영업활동현금흐름",
    "dividends_paid": "배당금 지급",
    "issued_shares": "발행주식수",
    "ffo_proxy": "FFO proxy",
}


OFFICIAL_COMPANIES: dict[str, dict[str, Any]] = {
    "SK리츠": {
        "stock_code": "395400",
        "dart_corp_code": "01535150",
        "report_name": "사업보고서",
        "report_date": "2026-06-10",
        "reporting_period": "재무상태 2026-03-31; 손익·현금흐름 2026-01-01~2026-03-31",
        "statement_scope": "연결(CFS)",
        "source_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260610000569",
        "facts": {
            "total_assets": (5408832.248718, "ifrs-full:Assets", "자산총계"),
            "total_liabilities": (3382988.684641, "ifrs-full:Liabilities", "부채총계"),
            "current_assets": (168971.880637, "ifrs-full:CurrentAssets", "유동자산"),
            "cash_and_cash_equivalents": (73378.212337, "ifrs-full:CashAndCashEquivalents", "현금및현금성자산"),
            "short_term_financial_assets": (
                11446.465160,
                "ifrs-full:ShorttermDepositsNotClassifiedAsCashEquivalents",
                "현금성자산으로 분류되지 않은 단기예치금",
            ),
            "investment_property": (5232672.201430, "ifrs-full:InvestmentProperty", "투자부동산"),
            "current_liabilities": (1318000.437012, "ifrs-full:CurrentLiabilities", "유동부채"),
            "short_term_borrowings": (None, "", "별도 분리 불가"),
            "current_portion_long_term_debt": (
                669076.449351,
                "ifrs-full:OtherCurrentBorrowingsAndCurrentPortionOfOtherNoncurrentBorrowings",
                "기타유동차입금 및 기타비유동차입금 유동분",
            ),
            "long_term_borrowings": (
                1451238.083598,
                "ifrs-full:NoncurrentPortionOfOtherNoncurrentBorrowings",
                "기타비유동차입금 비유동분",
            ),
            "bonds": (
                983540.288018,
                "derived:CurrentBondsIssuedAndCurrentPortionOfNoncurrentBondsIssued + NoncurrentPortionOfNoncurrentBondsIssued",
                "유동·비유동 사채 장부금액 합계",
            ),
            "lease_liabilities": (None, "", "주요 재무제표 계정에서 별도 검증 불가"),
            "provisions": (None, "", "주요 재무제표 계정에서 별도 검증 불가"),
            "deferred_tax_liabilities": (None, "", "주요 재무제표 계정에서 별도 검증 불가"),
            "interest_bearing_debt": (
                3103854.820967,
                "derived:669076.449351 + 574613.443933 + 1451238.083598 + 408926.844085",
                "유동·비유동 차입금 및 사채 장부금액 합계",
            ),
            "current_interest_bearing_debt": (
                1243689.893284,
                "derived:669076.449351 + 574613.443933",
                "유동성 차입금 및 유동성 사채 합계",
            ),
            "operating_revenue": (63369.239197, "ifrs-full:Revenue", "영업수익"),
            "operating_income": (53853.739755, "dart:OperatingIncomeLoss", "영업이익"),
            "net_income": (20539.220221, "ifrs-full:ProfitLoss", "당기순이익"),
            "interest_expense": (33926.344403, "ifrs-full:FinanceCosts", "금융원가"),
            "operating_cash_flow": (
                41169.870700,
                "ifrs-full:CashFlowsFromUsedInOperatingActivities",
                "영업활동현금흐름",
            ),
            "dividends_paid": (
                20986.921349,
                "ifrs-full:DividendsPaidClassifiedAsFinancingActivities",
                "배당금의 지급",
            ),
            "issued_shares": (301017620.0, "ifrs-full:NumberOfSharesIssued", "발행주식수"),
            "ffo_proxy": (
                22134.0,
                "SK리츠 투자보고서:FFO",
                "제20기 별도 투자보고서 FFO; 프로젝트 내 source metadata 기준",
            ),
        },
    },
    "롯데리츠": {
        "stock_code": "330590",
        "dart_corp_code": "01363818",
        "report_name": "사업보고서",
        "report_date": "2026-03-10",
        "reporting_period": "재무상태 2025-12-31; 손익·현금흐름 2025-07-01~2025-12-31",
        "statement_scope": "별도(OFS)",
        "source_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260310002810",
        "facts": {
            "total_assets": (2594407.041849, "ifrs-full:Assets", "자산총계"),
            "total_liabilities": (1454908.461475, "ifrs-full:Liabilities", "부채총계"),
            "current_assets": (58448.614109, "ifrs-full:CurrentAssets", "유동자산"),
            "cash_and_cash_equivalents": (12577.978163, "ifrs-full:CashAndCashEquivalents", "현금및현금성자산"),
            "short_term_financial_assets": (None, "", "주요 재무제표 계정에서 별도 검증 불가"),
            "investment_property": (2527222.594740, "ifrs-full:InvestmentProperty", "투자부동산"),
            "current_liabilities": (621336.979126, "ifrs-full:CurrentLiabilities", "유동부채"),
            "short_term_borrowings": (None, "", "유동성 차입부채 계정에서 별도 분리 불가"),
            "current_portion_long_term_debt": (
                603273.619875,
                "ifrs-full:CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings",
                "유동차입금 및 비유동차입금 유동분",
            ),
            "long_term_borrowings": (703746.157814, "ifrs-full:LongtermBorrowings", "장기차입금"),
            "bonds": (525000.0, "ifrs-full:BondsIssuedNominalValue", "사채 명목금액; 차입금 계정 포함 여부 주의"),
            "lease_liabilities": (None, "", "주요 재무제표 계정에서 별도 검증 불가"),
            "provisions": (None, "", "주요 재무제표 계정에서 별도 검증 불가"),
            "deferred_tax_liabilities": (None, "", "주요 재무제표 계정에서 별도 검증 불가"),
            "interest_bearing_debt": (
                1307019.777689,
                "derived:CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings + LongtermBorrowings",
                "유동·비유동 차입부채 장부금액 합계",
            ),
            "current_interest_bearing_debt": (
                603273.619875,
                "ifrs-full:CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings",
                "유동성 이자부 차입부채",
            ),
            "operating_revenue": (70879.702538, "ifrs-full:Revenue", "영업수익"),
            "operating_income": (46254.900872, "dart:OperatingIncomeLoss", "영업이익"),
            "net_income": (19627.460882, "ifrs-full:ProfitLoss", "당기순이익"),
            "interest_expense": (27353.183265, "ifrs-full:FinanceCosts", "금융원가"),
            "operating_cash_flow": (
                64017.736779,
                "ifrs-full:CashFlowsFromUsedInOperatingActivities",
                "영업활동현금흐름",
            ),
            "dividends_paid": (
                33809.359428,
                "ifrs-full:DividendsPaidClassifiedAsFinancingActivities",
                "배당금의 지급",
            ),
            "issued_shares": (288968884.0, "ifrs-full:NumberOfSharesIssued", "발행주식수"),
            "ffo_proxy": (None, "", "공식 XBRL에서 독립된 FFO 계정 미확인"),
        },
    },
    "ESR켄달스퀘어리츠": {
        "stock_code": "365550",
        "dart_corp_code": "01437186",
        "report_name": "사업보고서",
        "report_date": "2026-02-13",
        "reporting_period": "재무상태 2025-11-30; 손익·현금흐름 2025-06-01~2025-11-30",
        "statement_scope": "연결(CFS)",
        "source_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260213002140",
        "facts": {
            "total_assets": (2835773.540304, "ifrs-full:Assets", "자산총계"),
            "total_liabilities": (1670571.944339, "ifrs-full:Liabilities", "부채총계"),
            "current_assets": (206705.351492, "ifrs-full:CurrentAssets", "유동자산"),
            "cash_and_cash_equivalents": (171445.697130, "ifrs-full:CashAndCashEquivalents", "현금및현금성자산"),
            "short_term_financial_assets": (
                4258.324920,
                "ifrs-full:ShorttermDepositsNotClassifiedAsCashEquivalents",
                "현금성자산으로 분류되지 않은 단기예치금",
            ),
            "investment_property": (2433793.981472, "ifrs-full:InvestmentProperty", "투자부동산"),
            "current_liabilities": (186471.185667, "ifrs-full:CurrentLiabilities", "유동부채"),
            "short_term_borrowings": (26499.399652, "ifrs-full:ShorttermBorrowings", "단기차입금"),
            "current_portion_long_term_debt": (
                130270.741871,
                "ifrs-full:CurrentPortionOfLongtermBorrowings",
                "유동성장기차입금",
            ),
            "long_term_borrowings": (1430191.286763, "ifrs-full:LongtermBorrowings", "장기차입금"),
            "bonds": (None, "", "주요 재무제표 계정에서 별도 검증 불가"),
            "lease_liabilities": (None, "", "주요 재무제표 계정에서 별도 검증 불가"),
            "provisions": (None, "", "주요 재무제표 계정에서 별도 검증 불가"),
            "deferred_tax_liabilities": (None, "", "주요 재무제표 계정에서 별도 검증 불가"),
            "interest_bearing_debt": (
                1586961.428286,
                "derived:ShorttermBorrowings + CurrentPortionOfLongtermBorrowings + LongtermBorrowings",
                "단기·유동성장기·장기차입금 합계",
            ),
            "current_interest_bearing_debt": (
                156770.141523,
                "derived:ShorttermBorrowings + CurrentPortionOfLongtermBorrowings",
                "단기차입금 및 유동성장기차입금 합계",
            ),
            "operating_revenue": (59557.601618, "ifrs-full:Revenue", "영업수익"),
            "operating_income": (25859.163408, "dart:OperatingIncomeLoss", "영업이익"),
            "net_income": (-3436.388048, "ifrs-full:ProfitLoss", "당기순손실"),
            "interest_expense": (27995.840506, "ifrs-full:FinanceCosts", "금융원가"),
            "operating_cash_flow": (
                8836.054309,
                "ifrs-full:CashFlowsFromUsedInOperatingActivities",
                "영업활동현금흐름",
            ),
            "dividends_paid": (
                29193.193000,
                "ifrs-full:DividendsPaidClassifiedAsFinancingActivities",
                "배당금의 지급",
            ),
            "issued_shares": (246089000.0, "ifrs-full:NumberOfSharesIssued", "발행주식수"),
            "ffo_proxy": (None, "", "공식 XBRL에서 독립된 FFO 계정 미확인"),
        },
    },
}


VERDICT_OVERRIDES = {
    ("SK리츠", "total_assets"): "rounding_difference",
    ("SK리츠", "investment_property"): "rounding_difference",
    ("SK리츠", "interest_bearing_debt"): "rounding_difference",
    ("SK리츠", "current_interest_bearing_debt"): "mapping_difference",
    ("SK리츠", "operating_revenue"): "period_difference",
    ("SK리츠", "operating_income"): "period_difference",
    ("SK리츠", "net_income"): "period_difference",
    ("SK리츠", "interest_expense"): "estimate",
    ("SK리츠", "operating_cash_flow"): "estimate",
    ("SK리츠", "dividends_paid"): "period_difference",
    ("SK리츠", "ffo_proxy"): "period_difference",
    ("롯데리츠", "total_assets"): "mapping_difference",
    ("롯데리츠", "investment_property"): "mapping_difference",
    ("롯데리츠", "interest_bearing_debt"): "mapping_difference",
    ("롯데리츠", "current_interest_bearing_debt"): "mapping_difference",
    ("롯데리츠", "operating_revenue"): "period_difference",
    ("롯데리츠", "operating_income"): "period_difference",
    ("롯데리츠", "net_income"): "period_difference",
    ("롯데리츠", "interest_expense"): "period_difference",
    ("롯데리츠", "operating_cash_flow"): "period_difference",
    ("롯데리츠", "dividends_paid"): "period_difference",
    ("ESR켄달스퀘어리츠", "total_assets"): "mapping_difference",
    ("ESR켄달스퀘어리츠", "investment_property"): "mapping_difference",
    ("ESR켄달스퀘어리츠", "interest_bearing_debt"): "mapping_difference",
    ("ESR켄달스퀘어리츠", "current_interest_bearing_debt"): "mapping_difference",
    ("ESR켄달스퀘어리츠", "operating_revenue"): "period_difference",
    ("ESR켄달스퀘어리츠", "operating_income"): "period_difference",
    ("ESR켄달스퀘어리츠", "net_income"): "likely_error",
    ("ESR켄달스퀘어리츠", "interest_expense"): "period_difference",
    ("ESR켄달스퀘어리츠", "operating_cash_flow"): "period_difference",
    ("ESR켄달스퀘어리츠", "dividends_paid"): "period_difference",
}


EXPLANATIONS = {
    ("SK리츠", "total_assets"): "Snapshot은 공식 연결 재무상태표 금액을 백만원 단위로 반올림했습니다.",
    ("SK리츠", "investment_property"): "Snapshot은 공식 연결 투자부동산 금액을 백만원 단위로 반올림했습니다.",
    ("SK리츠", "interest_bearing_debt"): "Snapshot은 유동·비유동 차입금 및 사채 합계와 반올림 수준에서 일치합니다.",
    ("SK리츠", "current_interest_bearing_debt"): "프로젝트 1,318,000은 공식 유동부채 1,318,000.437과 일치하지만 공식 유동성 이자부 차입부채 1,243,689.893과 다릅니다.",
    ("SK리츠", "operating_revenue"): "프로젝트 값은 공식 1분기 연결 영업수익을 정확히 4배 연환산한 값이지만 annualized/scope metadata가 없습니다.",
    ("SK리츠", "operating_income"): "프로젝트 값은 공식 1분기 연결 영업이익을 4배 연환산한 값입니다.",
    ("SK리츠", "net_income"): "프로젝트 값은 공식 1분기 연결 당기순이익을 4배 연환산한 값입니다.",
    ("SK리츠", "ffo_proxy"): "프로젝트 88,536은 로컬 source metadata의 별도 투자보고서 FFO 22,134를 4배 연환산한 값입니다. 연결 재무제표와 범위가 다릅니다.",
    ("롯데리츠", "current_interest_bearing_debt"): "프로젝트 286,000은 공식 유동성 차입부채 603,273.620과 52.6% 차이가 납니다.",
    ("ESR켄달스퀘어리츠", "current_interest_bearing_debt"): "프로젝트 198,000은 공식 단기차입금+유동성장기차입금 156,770.142보다 26.3% 큽니다.",
    ("ESR켄달스퀘어리츠", "net_income"): "프로젝트는 +52,900이나 공식 최신 연결 반기 당기순손실은 -3,436.388입니다. 기간 차이만으로 부호 역전을 설명할 lineage가 없습니다.",
}


def build_financial_reconciliation() -> list[dict[str, Any]]:
    snapshot_rows = _read_csv(ROOT / "data" / "reit_peer_snapshot.csv")
    snapshots = {row["company_name"].strip(): row for row in snapshot_rows}
    rows: list[dict[str, Any]] = []

    for company_name, official in OFFICIAL_COMPANIES.items():
        snapshot = snapshots[company_name]
        for metric_key in PROJECT_COLUMN_BY_METRIC:
            project_column = PROJECT_COLUMN_BY_METRIC[metric_key]
            project_value = _number(snapshot.get(project_column)) if project_column else None
            official_value, account_id, account_name = official["facts"][metric_key]
            difference = None
            difference_pct = None
            if project_value is not None and official_value is not None:
                difference = project_value - official_value
                if official_value != 0:
                    difference_pct = difference / abs(official_value)

            override = VERDICT_OVERRIDES.get((company_name, metric_key))
            if override:
                verdict = override
            elif project_value is None or official_value is None:
                verdict = "unverifiable" if project_value is None else "estimate"
            elif abs(difference_pct or 0) <= 0.001:
                verdict = "rounding_difference"
            else:
                verdict = "mapping_difference"

            explanation = EXPLANATIONS.get((company_name, metric_key))
            if not explanation:
                if project_value is None and official_value is not None:
                    explanation = "공식 공시값은 확인했으나 현재 Snapshot/Power BI export에는 해당 프로젝트 값이 없습니다."
                elif project_value is not None and official_value is None:
                    explanation = "프로젝트 값은 존재하지만 공식 공시에서 동기간·동범위의 독립 계정을 확인하지 못했습니다."
                elif verdict == "period_difference":
                    explanation = "프로젝트와 공식 공시의 기간 또는 연환산 기준이 일치하지 않습니다."
                elif verdict in {"mapping_difference", "likely_error"}:
                    explanation = "Snapshot 값과 공식 최신 공시값 사이의 차이를 설명하는 field-level lineage가 없습니다."
                else:
                    explanation = "공식 공시와 반올림 수준에서 일치합니다."

            unit = "주" if metric_key == "issued_shares" else "백만원"
            source_document = f"{company_name} {official['report_name']} ({official['report_date']})"
            source_reference = official["source_url"]
            if company_name == "SK리츠" and metric_key == "ffo_proxy":
                source_document = "SK리츠 투자보고서 2026-06-30 (프로젝트 source metadata; 원문 파일 미보관)"
                source_reference = "data/sk_reit_latest_kpis.csv"
            rows.append(
                {
                    "company_name": company_name,
                    "metric": METRIC_NAMES[metric_key],
                    "project_value": _csv_number(project_value),
                    "official_value": _csv_number(official_value),
                    "difference": _csv_number(difference),
                    "difference_pct": _csv_number(difference_pct),
                    "project_unit": unit,
                    "official_unit": unit,
                    "reporting_period": official["reporting_period"],
                    "statement_scope": official["statement_scope"],
                    "source_document": source_document,
                    "source_reference": source_reference,
                    "account_id": account_id,
                    "account_name": account_name,
                    "verdict": verdict,
                    "explanation": explanation,
                }
            )
    return rows


def build_holding_tax_reconciliation() -> list[dict[str, Any]]:
    return [
        {
            "company_name": "SK리츠",
            "asset_or_scope": "회사 전체 Snapshot 추정 대 연결 세금과공과",
            "project_estimated_tax": "29500",
            "disclosed_tax_or_related_expense": "3.36",
            "comparable": "False",
            "difference": "",
            "source": "SK리츠 사업보고서 2026-06-10; dart:TaxesDues; https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260610000569",
            "ownership_structure": "연결실체 기준이며 자산별 법적 소유자·신탁·종속리츠별 납세의무자를 확인하지 못함",
            "tax_scope": "프로젝트는 재산세·도시지역분·지방교육세 screening 추정; 공시는 법인세 이외 세금 중 세금과공과 계정",
            "limitation": "공시 세금과공과는 보유세 전용 계정이 아니고 3개월 수치이며, 프로젝트 세액은 연간 회사 전체 추정값입니다.",
            "verdict": "unverifiable",
        },
        {
            "company_name": "롯데리츠",
            "asset_or_scope": "회사 전체 Snapshot 추정 대 투자부동산 직접운영비용",
            "project_estimated_tax": "15800",
            "disclosed_tax_or_related_expense": "23536.456",
            "comparable": "False",
            "difference": "",
            "source": "롯데리츠 사업보고서 2026-03-10; ifrs-full:DirectOperatingExpenseFromInvestmentProperty; https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260310002810",
            "ownership_structure": "별도재무제표 기준; 일부 책임임대차계약은 관리비·보험료·제세공과금을 임차인이 부담한다고 공시",
            "tax_scope": "직접운영비용에는 감가상각비·수수료·보험료·세금과공과 등이 포함되어 세금만 분리 불가",
            "limitation": "보유세 현금부담 주체와 세금 전용 공시금액을 확인할 수 없어 프로젝트 추정세액과 비교할 수 없습니다.",
            "verdict": "unverifiable",
        },
        {
            "company_name": "ESR켄달스퀘어리츠",
            "asset_or_scope": "회사 전체 Snapshot 추정 대 연결 법인세 이외의 세금",
            "project_estimated_tax": "18600",
            "disclosed_tax_or_related_expense": "3806.976",
            "comparable": "False",
            "difference": "",
            "source": "ESR켄달스퀘어리츠 사업보고서 2026-02-13; ifrs-full:TaxExpenseOtherThanIncomeTaxExpense; https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260213002140",
            "ownership_structure": "연결실체 기준이며 자산별 소유 SPC·종속회사와 법적 납세의무자를 분리 검증하지 못함",
            "tax_scope": "공시는 모든 법인세 이외 세금이며 재산세·종합부동산세·기타 공과를 분리하지 않음",
            "limitation": "6개월 연결 비용과 연간 회사 전체 추정세액의 기간·세목·법인 범위가 다릅니다.",
            "verdict": "unverifiable",
        },
    ]


def build_source_lineage() -> list[dict[str, Any]]:
    base_rows = [
        {
            "metric": "총자산",
            "raw_source": "DART/OpenDART XBRL 또는 data/reit_peer_snapshot.csv",
            "loading_function": "dart_financials.load_recent_5y_financials / calculations_peer.load_peer_snapshot",
            "normalized_column": "total_assets",
            "calculation_function": "직접 매핑",
            "ui_location": "일반 정보·Assurance·Peer 비교",
            "tax_review_pack": "Peer 요약 및 LTV 분모",
            "power_bi_column_or_measure": "FactKPI[total_assets_eok] / [총자산(억원)]",
            "source_type": "DART이면 official_disclosure; 현재 bundled row는 sample_snapshot→api_snapshot",
            "limitation": "현재 대표 3사 공개 export는 공시 field-level source가 아닌 회사 단위 Snapshot source를 사용합니다.",
        },
        {
            "metric": "총부채",
            "raw_source": "DART/OpenDART XBRL",
            "loading_function": "api_dart.fetch_dart_financial_history",
            "normalized_column": "total_liabilities",
            "calculation_function": "직접 매핑",
            "ui_location": "장부기준 NAV proxy",
            "tax_review_pack": "직접 사용하지 않음",
            "power_bi_column_or_measure": "FactKPI[total_liabilities_eok] / 현재 export는 공란",
            "source_type": "official_disclosure 또는 data_insufficient",
            "limitation": "현재 peer snapshot schema에 총부채가 없어 Snapshot fallback에서는 NAV proxy를 산출할 수 없습니다.",
        },
        {
            "metric": "투자부동산",
            "raw_source": "DART XBRL 또는 peer Snapshot",
            "loading_function": "api_dart / calculations_peer.load_peer_snapshot",
            "normalized_column": "investment_property",
            "calculation_function": "직접 매핑",
            "ui_location": "Assurance·Tax·Peer 비교",
            "tax_review_pack": "공시가격/투자부동산 장부금액",
            "power_bi_column_or_measure": "FactKPI[investment_property_eok] / [투자부동산(억원)]",
            "source_type": "현재 대표 3사는 sample_snapshot",
            "limitation": "롯데·ESR Snapshot이 공식 최신 공시와 각각 약 -8.4%, +23.7% 차이가 납니다.",
        },
        {
            "metric": "유동부채",
            "raw_source": "DART XBRL",
            "loading_function": "api_dart.fetch_dart_financial_history",
            "normalized_column": "current_liabilities",
            "calculation_function": "직접 매핑",
            "ui_location": "직접 표시 없음",
            "tax_review_pack": "직접 사용하지 않음",
            "power_bi_column_or_measure": "없음",
            "source_type": "official_disclosure",
            "limitation": "peer Snapshot에는 없으나 SK borrowings_current가 공식 유동부채와 동일해 차입금 mapping 오류가 의심됩니다.",
        },
        {
            "metric": "이자부 차입부채",
            "raw_source": "DART 차입금·사채·리스부채 계정 또는 peer borrowings_total",
            "loading_function": "api_dart / calculations_peer.load_peer_snapshot",
            "normalized_column": "interest_bearing_debt 또는 borrowings_total",
            "calculation_function": "metric_definitions.derive_interest_bearing_debt",
            "ui_location": "Assurance·Peer 비교",
            "tax_review_pack": "FFO 이자감당력 및 LTV",
            "power_bi_column_or_measure": "FactKPI[interest_bearing_debt_eok] / [이자부 차입부채(억원)]",
            "source_type": "official_disclosure 또는 Snapshot",
            "limitation": "일부 구성계정만 존재해도 합계를 확정값처럼 반환하며 누락 리스부채 여부를 검증하지 않습니다.",
        },
        {
            "metric": "유동성 이자부 차입부채",
            "raw_source": "peer Snapshot borrowings_current",
            "loading_function": "calculations_peer.build_peer_metrics",
            "normalized_column": "borrowings_current",
            "calculation_function": "borrowings_current / borrowings_total",
            "ui_location": "Assurance 유동성 차입금/총차입금",
            "tax_review_pack": "간접 사용",
            "power_bi_column_or_measure": "FactKPI[borrowings_current_eok] / current_debt_to_total_debt",
            "source_type": "sample_snapshot",
            "limitation": "대표 3사 모두 공식 유동성 이자부 차입부채와 불일치하며 SK는 유동부채를 잘못 매핑한 정황이 있습니다.",
        },
        {
            "metric": "현금및현금성자산·단기금융자산",
            "raw_source": "DART XBRL",
            "loading_function": "api_dart.fetch_dart_financial_history",
            "normalized_column": "cash_and_cash_equivalents / short_term_financial_assets",
            "calculation_function": "metric_definitions.derive_net_debt",
            "ui_location": "순차입금 proxy",
            "tax_review_pack": "직접 사용하지 않음",
            "power_bi_column_or_measure": "FactKPI[cash_and_cash_equivalents_eok]; 현재 export 공란",
            "source_type": "official_disclosure 또는 data_insufficient",
            "limitation": "단기금융자산의 사용제한 여부를 fact metadata로 확인하지 않고 자동 차감할 수 있습니다.",
        },
        {
            "metric": "충당부채",
            "raw_source": "DART XBRL",
            "loading_function": "api_dart",
            "normalized_column": "provisions",
            "calculation_function": "NAV에는 총부채를 통해 포함; 이자부 차입부채에서는 제외",
            "ui_location": "방법론",
            "tax_review_pack": "직접 사용하지 않음",
            "power_bi_column_or_measure": "FactKPI[provisions_eok]; 현재 export 공란",
            "source_type": "data_insufficient",
            "limitation": "대표 3사 프로젝트 Snapshot에는 별도 값이 없습니다.",
        },
        {
            "metric": "영업수익·영업이익·당기순이익",
            "raw_source": "DART XBRL 또는 peer Snapshot",
            "loading_function": "dart_financials / calculations_peer",
            "normalized_column": "operating_revenue / operating_income / net_income",
            "calculation_function": "직접 매핑 또는 Snapshot",
            "ui_location": "일반 정보·Assurance·Peer 비교",
            "tax_review_pack": "보유세/영업수익, FFO fallback",
            "power_bi_column_or_measure": "FactKPI 관련 *_eok measures",
            "source_type": "현재 대표 3사는 sample_snapshot",
            "limitation": "SK는 분기 연결값 4배 연환산, 롯데·ESR은 공식 최신 반기값과 연결되지 않는 Snapshot이며 기간 metadata가 부족합니다.",
        },
        {
            "metric": "이자비용",
            "raw_source": "DART FinanceCosts 또는 peer Snapshot",
            "loading_function": "api_dart / calculations_peer",
            "normalized_column": "interest_expense",
            "calculation_function": "직접 매핑",
            "ui_location": "Assurance·Peer 비교",
            "tax_review_pack": "FFO 이자감당력",
            "power_bi_column_or_measure": "FactKPI[interest_expense_eok] / [이자비용(억원)]",
            "source_type": "Snapshot",
            "limitation": "Snapshot의 기간·연환산 근거가 field-level로 남아 있지 않습니다.",
        },
        {
            "metric": "영업활동현금흐름",
            "raw_source": "DART 현금흐름표 또는 peer Snapshot",
            "loading_function": "api_dart / dart_financials",
            "normalized_column": "operating_cash_flow",
            "calculation_function": "FFO proxy fallback 1순위",
            "ui_location": "일반 정보·방법론",
            "tax_review_pack": "현금유출 보조 KPI",
            "power_bi_column_or_measure": "FactKPI[operating_cash_flow_eok]",
            "source_type": "Snapshot",
            "limitation": "SK Snapshot 97,200은 공식 1분기 CFO 41,169.871의 단순 연환산과도 일치하지 않습니다.",
        },
        {
            "metric": "FFO proxy",
            "raw_source": "peer Snapshot ffo_proxy 또는 DART CFO/영업이익/순이익 fallback",
            "loading_function": "dart_financials._normalize_dart_history",
            "normalized_column": "ffo_proxy",
            "calculation_function": "metric_definitions.derive_ffo_proxy",
            "ui_location": "Assurance·Tax·Peer 비교",
            "tax_review_pack": "보유세/FFO 및 stress",
            "power_bi_column_or_measure": "FactKPI[ffo_proxy_eok] / [FFO proxy(억원)]",
            "source_type": "Snapshot 우선",
            "limitation": "감가상각·처분손익·공정가치·일회성 항목 조정 bridge가 없어 공식 FFO가 아닙니다.",
        },
        {
            "metric": "공시가격",
            "raw_source": "data/reit_tax_snapshot.csv 또는 peer official_price_total",
            "loading_function": "tax_data_loader.load_tax_snapshot",
            "normalized_column": "official_price / official_price_total",
            "calculation_function": "회사 전체 합계",
            "ui_location": "Tax Summary·보유세 브리지",
            "tax_review_pack": "공시가격/장부가액 및 요청자료",
            "power_bi_column_or_measure": "FactKPI[official_price_total_eok]; FactBridge[amount_eok]",
            "source_type": "peer_snapshot_estimate",
            "limitation": "대표 3사 모두 PNU·자산·연도별 공식 조회 응답 또는 고지서 lineage가 없습니다.",
        },
        {
            "metric": "추정 과세표준",
            "raw_source": "회사 전체 공시가격 추정",
            "loading_function": "tax_data_loader",
            "normalized_column": "estimated_tax_base",
            "calculation_function": "calculations_holding_tax_bridge.calculate_estimated_tax_base",
            "ui_location": "Tax 보유세 산출 브리지",
            "tax_review_pack": "reconciliation·memo",
            "power_bi_column_or_measure": "FactReconciliation[estimated_tax_base_eok]",
            "source_type": "peer_snapshot_estimate",
            "limitation": "현재 기본식은 회사 전체 공시가격×70%이며 토지·건축물·주택 유형과 합산구분을 반영하지 않습니다.",
        },
        {
            "metric": "추정 보유세",
            "raw_source": "reit_tax_snapshot estimated_holding_tax 또는 fallback",
            "loading_function": "tax_data_loader.estimate_company_holding_tax_from_peer_snapshot",
            "normalized_column": "estimated_holding_tax",
            "calculation_function": "Snapshot 값 우선; 결측 시 공식가격×1.1% 또는 과세표준×1.1%",
            "ui_location": "Tax Summary·브리지·trend",
            "tax_review_pack": "issue·request·memo·stress",
            "power_bi_column_or_measure": "FactKPI[estimated_holding_tax_eok] / [추정 보유세(억원)]",
            "source_type": "peer_snapshot_estimate",
            "limitation": "동일 화면의 적용세율과 저장 세액이 조정되지 않고 법정 세목 전체를 포함하지 않습니다.",
        },
        {
            "metric": "보유세 / FFO proxy",
            "raw_source": "추정 보유세와 FFO proxy",
            "loading_function": "calculations_peer / calculations_tax_review_pack",
            "normalized_column": "holding_tax_to_ffo",
            "calculation_function": "safe_divide(estimated_holding_tax, ffo_proxy)",
            "ui_location": "Tax Red Flag·Peer·stress",
            "tax_review_pack": "핵심 KPI",
            "power_bi_column_or_measure": "DIVIDE([추정 보유세(억원)], [FFO proxy(억원)])",
            "source_type": "분자·분모의 낮은 신뢰도를 승계",
            "limitation": "공식세액과 공식 FFO가 아닌 두 추정치를 나눈 비율입니다.",
        },
        {
            "metric": "보유세 / 영업수익",
            "raw_source": "추정 보유세와 Snapshot 영업수익",
            "loading_function": "calculations_peer",
            "normalized_column": "holding_tax_to_operating_revenue",
            "calculation_function": "estimated_holding_tax / operating_revenue",
            "ui_location": "Tax Peer·Red Flag",
            "tax_review_pack": "보조 KPI",
            "power_bi_column_or_measure": "DIVIDE([추정 보유세(억원)], [영업수익(억원)])",
            "source_type": "Snapshot estimate",
            "limitation": "영업수익의 기간과 추정 보유세의 연간 기준이 일치한다는 보장이 없습니다.",
        },
        {
            "metric": "Gross LTV",
            "raw_source": "이자부 차입부채와 총자산",
            "loading_function": "calculations_peer",
            "normalized_column": "debt_to_assets",
            "calculation_function": "interest_bearing_debt / total_assets",
            "ui_location": "Assurance·Peer",
            "tax_review_pack": "보조 리스크",
            "power_bi_column_or_measure": "[총자산 기준 Gross LTV]",
            "source_type": "Snapshot",
            "limitation": "부동산 담보 LTV가 아니라 총자산 기준 차입비율입니다.",
        },
        {
            "metric": "Property LTV",
            "raw_source": "이자부 차입부채와 투자부동산",
            "loading_function": "metric_definitions",
            "normalized_column": "property_ltv",
            "calculation_function": "interest_bearing_debt / investment_property",
            "ui_location": "방법론·Power BI",
            "tax_review_pack": "보조 리스크",
            "power_bi_column_or_measure": "[투자부동산 기준 Property LTV]",
            "source_type": "Snapshot",
            "limitation": "담보부채만을 분자로 쓰지 않고 회사 전체 이자부 차입부채를 사용합니다.",
        },
        {
            "metric": "장부기준 NAV proxy",
            "raw_source": "총자산·총부채 또는 자본총계",
            "loading_function": "api_dart / dart_financials",
            "normalized_column": "book_nav_proxy",
            "calculation_function": "metric_definitions.derive_book_nav_proxy",
            "ui_location": "일반 정보·방법론",
            "tax_review_pack": "직접 사용하지 않음",
            "power_bi_column_or_measure": "FactKPI[book_nav_proxy_eok]; 현재 export 공란",
            "source_type": "official_disclosure 또는 data_insufficient",
            "limitation": "시장가치 NAV가 아니며 현재 peer Snapshot에는 총부채가 없어 산출되지 않습니다.",
        },
        {
            "metric": "순차입금",
            "raw_source": "이자부 차입부채·현금·단기금융자산",
            "loading_function": "api_dart",
            "normalized_column": "net_debt",
            "calculation_function": "metric_definitions.derive_net_debt",
            "ui_location": "방법론",
            "tax_review_pack": "직접 사용하지 않음",
            "power_bi_column_or_measure": "현재 없음",
            "source_type": "official_disclosure",
            "limitation": "담보·질권·사용제한 여부를 구조화하지 않아 차감 가능 유동성을 과대평가할 수 있습니다.",
        },
        {
            "metric": "유효차입금리 proxy",
            "raw_source": "이자비용·평균 또는 기말 이자부 차입부채",
            "loading_function": "metric_definitions",
            "normalized_column": "effective_borrowing_rate_proxy",
            "calculation_function": "이자비용/평균 차입부채; 평균 결측 시 기말 차입부채",
            "ui_location": "Assurance·방법론",
            "tax_review_pack": "간접 사용",
            "power_bi_column_or_measure": "직접 measure 없음",
            "source_type": "proxy",
            "limitation": "기간 수치가 연환산되지 않거나 평균잔액이 없으면 경제적 금리와 다릅니다.",
        },
        {
            "metric": "Cap rate proxy",
            "raw_source": "data/sk_reit_asset_metrics.csv",
            "loading_function": "data_loader.load_local_data",
            "normalized_column": "cap_rate_pct_20251231",
            "calculation_function": "표시 Cap rate 또는 Cap rate×취득가액으로 NOI proxy 역산",
            "ui_location": "SK리츠 상세·Assurance",
            "tax_review_pack": "직접 사용하지 않음",
            "power_bi_column_or_measure": "현재 export 없음",
            "source_type": "sample_estimate",
            "limitation": "SK 상세 sample만 존재하고 일부 연간임대료는 Cap rate×취득가액으로 역산됩니다. 비SK에는 data_insufficient가 정상입니다.",
        },
        {
            "metric": "WALE",
            "raw_source": "data/sk_reit_asset_metrics.csv / sk_reit_latest_kpis.csv",
            "loading_function": "data_loader.load_local_data",
            "normalized_column": "wale_yrs",
            "calculation_function": "공시 KPI 직접 사용; 계약별 가중 재계산은 미구현",
            "ui_location": "SK리츠 상세·Assurance",
            "tax_review_pack": "직접 사용하지 않음",
            "power_bi_column_or_measure": "현재 export 없음",
            "source_type": "sample_estimate 또는 official metadata",
            "limitation": "면적·임대료 가중 방식과 계약별 만기 입력을 재수행하지 않았고 비SK에는 값이 없습니다.",
        },
    ]

    project_period = "2026Q1"
    expanded: list[dict[str, Any]] = []
    tax_columns = {
        "official_price / official_price_total",
        "estimated_tax_base",
        "estimated_holding_tax",
        "holding_tax_to_ffo",
        "holding_tax_to_operating_revenue",
    }
    for company_name, official in OFFICIAL_COMPANIES.items():
        for base_row in base_rows:
            row = dict(base_row)
            normalized_column = row["normalized_column"]
            if normalized_column in tax_columns:
                raw_source_type = "peer_snapshot_estimate"
            elif normalized_column in {"cap_rate_pct_20251231", "wale_yrs"}:
                raw_source_type = "sample_estimate" if company_name == "SK리츠" else "data_insufficient"
            else:
                raw_source_type = "sample_snapshot"

            if company_name == "SK리츠":
                project_scope = "혼합: 연결 재무상태·손익 + 별도 투자보고서 FFO"
            else:
                project_scope = f"Snapshot 범위 미문서화; 공식 비교는 {official['statement_scope']}"

            row.update(
                {
                    "company_name": company_name,
                    "stock_code": official["stock_code"],
                    "project_period": project_period,
                    "official_reporting_period": official["reporting_period"],
                    "project_statement_scope": project_scope,
                    "raw_source_type": raw_source_type,
                }
            )
            expanded.append(row)
    return expanded


def build_metric_definition_matrix() -> list[dict[str, Any]]:
    return [
        {
            "metric": "장부기준 NAV proxy",
            "ui_label": "장부기준 NAV proxy",
            "implemented_formula": "총자산 - 총부채; 둘 중 하나 결측 시 자본총계 fallback",
            "source_columns": "total_assets, total_liabilities, total_equity",
            "included": "모든 인식 부채(차입금·사채·리스부채·충당부채·이연법인세부채 포함)",
            "excluded": "미인식 시장가치 조정, 매각비용, 잠재세금",
            "financial_meaning": "장부상 순자산/자본 proxy",
            "label_accuracy": "적정: proxy 명시",
            "validation_status": "부분 검증",
            "primary_risk": "현재 Snapshot 총부채 결측으로 대표회사 export에서는 공란",
            "code_reference": "metric_definitions.py:36-44",
        },
        {
            "metric": "이자부 차입부채",
            "ui_label": "이자부 차입부채",
            "implemented_formula": "가용한 단기차입금+유동성장기차입금+장기차입금+사채+리스부채; 모두 결측 시 borrowings_total",
            "source_columns": "short_term_borrowings, current_portion_long_term_debt, long_term_borrowings, bonds, lease_liabilities, borrowings_total",
            "included": "입력된 이자부 구성계정",
            "excluded": "매입채무·충당부채·이연법인세 등 비이자성 부채",
            "financial_meaning": "총부채가 아닌 이자부 금융부채 proxy",
            "label_accuracy": "조건부 적정",
            "validation_status": "오류 가능성 높음",
            "primary_risk": "일부 구성계정만 있어도 부분합을 전체로 확정",
            "code_reference": "metric_definitions.py:47-68",
        },
        {
            "metric": "유동성 차입금 비율",
            "ui_label": "유동성 차입금/총차입금",
            "implemented_formula": "borrowings_current / borrowings_total",
            "source_columns": "reit_peer_snapshot.borrowings_current, borrowings_total",
            "included": "Snapshot이 current debt라고 주장하는 값",
            "excluded": "계정별 검증",
            "financial_meaning": "단기 차환부담 proxy",
            "label_accuracy": "부적정",
            "validation_status": "P0",
            "primary_risk": "SK 값이 유동부채와 일치하고 공식 유동성 이자부 차입부채와 불일치",
            "code_reference": "calculations_peer.py:79; data/reit_peer_snapshot.csv",
        },
        {
            "metric": "순차입금",
            "ui_label": "순차입금",
            "implemented_formula": "이자부 차입부채 - 현금및현금성자산 - 단기금융자산",
            "source_columns": "interest_bearing_debt, cash_and_cash_equivalents, short_term_financial_assets",
            "included": "현금과 입력된 단기금융자산",
            "excluded": "사용제한 판별 로직",
            "financial_meaning": "가용 유동성을 차감한 순부채 proxy",
            "label_accuracy": "조건부 적정",
            "validation_status": "P1",
            "primary_risk": "질권·제한예금까지 차감할 수 있음",
            "code_reference": "metric_definitions.py:71-82",
        },
        {
            "metric": "Gross LTV",
            "ui_label": "총자산 기준 Gross LTV",
            "implemented_formula": "이자부 차입부채 / 총자산",
            "source_columns": "interest_bearing_debt, total_assets",
            "included": "회사 전체 이자부 차입부채와 총자산",
            "excluded": "담보별 debt/value 대응",
            "financial_meaning": "총자산 대비 이자부 부채 비율",
            "label_accuracy": "적정: 총자산 기준 명시",
            "validation_status": "부분 검증",
            "primary_risk": "일반적인 담보 LTV와 혼동 가능",
            "code_reference": "metric_definitions.py; _Measures.tmdl:200-205",
        },
        {
            "metric": "Property LTV",
            "ui_label": "투자부동산 기준 Property LTV",
            "implemented_formula": "회사 전체 이자부 차입부채 / 투자부동산 장부금액",
            "source_columns": "interest_bearing_debt, investment_property",
            "included": "회사 전체 이자부 부채",
            "excluded": "담보부채 식별, 공정가치/감정가액",
            "financial_meaning": "투자부동산 장부금액 대비 차입부담 proxy",
            "label_accuracy": "조건부 적정",
            "validation_status": "부분 검증",
            "primary_risk": "담보 LTV로 해석하면 안 됨",
            "code_reference": "_Measures.tmdl:207-212",
        },
        {
            "metric": "유효차입금리 proxy",
            "ui_label": "유효차입금리 proxy",
            "implemented_formula": "이자비용 / 평균 이자부 차입부채; 평균 결측 시 기말 이자부 차입부채",
            "source_columns": "interest_expense, average_interest_bearing_debt 또는 ending debt",
            "included": "금융원가 계정과 차입부채",
            "excluded": "연환산·평균잔액 조정이 결측일 수 있음",
            "financial_meaning": "회계상 이자부담률 proxy",
            "label_accuracy": "적정: proxy 명시",
            "validation_status": "P2",
            "primary_risk": "기간과 잔액 기준 불일치",
            "code_reference": "metric_definitions.py",
        },
        {
            "metric": "FFO proxy",
            "ui_label": "FFO proxy",
            "implemented_formula": "Snapshot ffo_proxy 우선; 결측 시 CFO→영업이익→순이익",
            "source_columns": "ffo_proxy, operating_cash_flow, operating_income, net_income",
            "included": "선택된 단일 proxy 계정",
            "excluded": "감가상각 가산, 처분손익·평가손익·비경상 항목 조정 bridge",
            "financial_meaning": "반복 영업현금창출력의 간이 대용치",
            "label_accuracy": "적정: proxy 명시",
            "validation_status": "P1",
            "primary_risk": "회사별 proxy 정의와 기간·범위가 다름",
            "code_reference": "metric_definitions.py:85-100; dart_financials.py:148-209",
        },
        {
            "metric": "FFO 이자감당력 proxy",
            "ui_label": "FFO 이자감당력 proxy",
            "implemented_formula": "FFO proxy / 이자비용",
            "source_columns": "ffo_proxy, interest_expense",
            "included": "Snapshot FFO proxy와 금융원가",
            "excluded": "동일 기간·범위 보정",
            "financial_meaning": "이자부담 감내 여력의 간이 배수",
            "label_accuracy": "조건부 적정",
            "validation_status": "P1",
            "primary_risk": "분자·분모 기간 불일치",
            "code_reference": "metric_definitions.py; _Measures.tmdl:214-224",
        },
        {
            "metric": "회사 전체 보유세 브리지",
            "ui_label": "추정 보유세 / 적용 세율",
            "implemented_formula": "공시가격×70%로 과세표준 산출 후 Snapshot estimated_holding_tax가 있으면 그대로 사용, 없을 때만 과세표준×1.1%",
            "source_columns": "official_price, estimated_tax_base, estimated_holding_tax, fair_market_value_ratio, effective_holding_tax_rate",
            "included": "회사 전체 추정값",
            "excluded": "자산유형·과세구분·세목별 실제 계산",
            "financial_meaning": "Tax screening bridge",
            "label_accuracy": "부적정",
            "validation_status": "P0",
            "primary_risk": "화면 세율이 세액 계산에 반영되지 않는 경우가 있음",
            "code_reference": "calculations_holding_tax_bridge.py:146-203",
        },
        {
            "metric": "상세 재산세 estimator",
            "ui_label": "상세 보유세 estimator(주 경로 아님)",
            "implemented_formula": "별도합산 토지 누진세율 + 일반건축물 0.25% + 도시지역분 0.14% + 재산세 본세의 지방교육세 20%",
            "source_columns": "land/building official price and FMV ratios",
            "included": "재산세 본세·도시지역분·지방교육세",
            "excluded": "지역자원시설세·종합부동산세·농어촌특별세·해외세·감면/합산/소유구조",
            "financial_meaning": "기본 재산세 screening",
            "label_accuracy": "조건부 적정",
            "validation_status": "부분 검증",
            "primary_risk": "현재 주 Tax 화면의 회사 전체 Snapshot 경로에서는 사용되지 않음",
            "code_reference": "calculations_tax.py:38-100",
        },
        {
            "metric": "보유세 / FFO proxy",
            "ui_label": "보유세 / FFO proxy",
            "implemented_formula": "추정 보유세 / FFO proxy",
            "source_columns": "estimated_holding_tax, ffo_proxy",
            "included": "회사 전체 추정치",
            "excluded": "공식세액·공식 FFO 조정",
            "financial_meaning": "추정 세부담의 현금창출력 대비 비율",
            "label_accuracy": "적정: 분자·분모 proxy 표기 필요",
            "validation_status": "P1",
            "primary_risk": "두 추정치의 기간·범위 불일치",
            "code_reference": "metric_definitions.py; _Measures.tmdl:186-191",
        },
        {
            "metric": "보유세 / 영업수익",
            "ui_label": "보유세 / 영업수익",
            "implemented_formula": "추정 보유세 / 영업수익",
            "source_columns": "estimated_holding_tax, operating_revenue",
            "included": "회사 전체 수익",
            "excluded": "NOI·자산별 수익",
            "financial_meaning": "매출 대비 추정 세부담",
            "label_accuracy": "조건부 적정",
            "validation_status": "P1",
            "primary_risk": "연간 세액과 비연간 수익의 기간 불일치",
            "code_reference": "_Measures.tmdl:193-198",
        },
        {
            "metric": "공시가격 / 투자부동산",
            "ui_label": "공시가격 / 투자부동산 장부금액",
            "implemented_formula": "회사 전체 공시가격 추정 / 투자부동산 장부금액",
            "source_columns": "official_price_total, investment_property",
            "included": "회사 전체 추정 공시가격",
            "excluded": "자산별 대사·소유비율·토지/건물 구분",
            "financial_meaning": "과세 기준 proxy와 장부가의 상대규모",
            "label_accuracy": "조건부 적정",
            "validation_status": "P1",
            "primary_risk": "분자가 공식 공시가격 합계로 검증되지 않음",
            "code_reference": "_Measures.tmdl:228-233",
        },
        {
            "metric": "Cap rate proxy",
            "ui_label": "Cap rate proxy",
            "implemented_formula": "공식 NOI/자산가치 또는 표시 Cap rate; 일부 NOI는 Cap rate×취득가액 역산",
            "source_columns": "cap_rate_pct_20251231, acquisition_price, appraised_value",
            "included": "SK sample 자산",
            "excluded": "비SK와 계약별 정상화 NOI",
            "financial_meaning": "자산 수익률 가정 proxy",
            "label_accuracy": "적정: proxy 명시",
            "validation_status": "P2",
            "primary_risk": "원자료 미보관 및 자산가치 기준 혼재",
            "code_reference": "metric_definitions.py; data/sk_reit_asset_metrics.csv",
        },
        {
            "metric": "WALE",
            "ui_label": "WALE",
            "implemented_formula": "공시된 회사/자산 KPI 직접 사용; 계약별 Σ(가중치×잔여기간)/Σ가중치 재계산 미구현",
            "source_columns": "wale_yrs, lease_end_or_wale",
            "included": "SK sample 공시 KPI",
            "excluded": "가중치 정의 및 계약별 재계산",
            "financial_meaning": "가중평균 잔여 임대기간",
            "label_accuracy": "조건부 적정",
            "validation_status": "P2",
            "primary_risk": "임대료/면적 가중 기준 확인 불가",
            "code_reference": "metric_definitions.py; data/sk_reit_asset_metrics.csv",
        },
        {
            "metric": "최근 5년 보유세 추이",
            "ui_label": "재산세·도시지역분·지방교육세 추이",
            "implemented_formula": "최신 추정세액을 성장률로 역산하고 각 연도 총세액을 60%/30%/10%로 배분",
            "source_columns": "estimated_holding_tax, official_price_growth_5y",
            "included": "생성된 세 항목",
            "excluded": "법정 세율·실제 고지서·세부담상한·감면",
            "financial_meaning": "합성 시계열",
            "label_accuracy": "부적정",
            "validation_status": "P0",
            "primary_risk": "법정 산식이 아닌 임의 비율을 실제 세목처럼 표시",
            "code_reference": "tax_data_loader.py:228-272",
        },
    ]


def build_issue_register() -> list[dict[str, Any]]:
    issues = [
        (
            "P0-01",
            "P0",
            "재무 mapping",
            "borrowings_current가 유동성 이자부 차입부채와 일치하지 않음",
            "data/reit_peer_snapshot.csv; calculations_peer.py:79; ui_assurance.py:163",
            "SK 1,318,000은 공식 유동부채 1,318,000.437과 일치하나 공식 유동성 이자부 차입부채는 1,243,689.893. 롯데·ESR도 각각 -52.6%, +26.3% 차이.",
            "유동성 차입금 비율과 차환 Red Flag가 잘못 산출됨",
            "공식 XBRL 계정별 유동 차입금+유동 사채로 재매핑하고 provenance를 보존",
            "오류 가능성 높음",
        ),
        (
            "P0-02",
            "P0",
            "보유세 계산",
            "보유세 브리지의 표시 세율이 Snapshot 세액에 적용되지 않음",
            "calculations_holding_tax_bridge.py:159,173-200; data/reit_tax_snapshot.csv",
            "표시 1.1% 대비 Snapshot implied rate는 SK 1.4643%, 롯데 1.7100%, ESR 1.7869%. Snapshot 세액이 있으면 rate slider를 우회.",
            "동일 화면의 세율·과세표준·세액이 수학적으로 조정되지 않음",
            "Snapshot 세액 사용 시 적용세율을 implied rate로 표시하거나, 사용자 가정으로 세액을 일관되게 재계산",
            "검증 완료",
        ),
        (
            "P0-03",
            "P0",
            "Red Flag",
            "공시가격 상승률 규칙이 holding_tax_to_ffo를 참조",
            "data/red_flag_rules.json:216-225",
            "rule id official_price_growth_placeholder의 metric이 holding_tax_to_ffo로 설정됨",
            "공시가격 상승 위험이 FFO 비율로 발생하고 Request/Memo까지 잘못 전파됨",
            "공식가격 성장률 전용 metric으로 교체하거나 데이터 확보 전 규칙 비활성화",
            "검증 완료",
        ),
        (
            "P0-04",
            "P0",
            "보유세 시계열",
            "5년 보유세 세목을 60%/30%/10%로 임의 배분",
            "tax_data_loader.py:228-272",
            "최신 추정세액을 역산한 뒤 재산세 60%, 도시지역분 30%, 지방교육세 10%로 고정 배분",
            "법정 산식과 무관한 세목별 금액이 실제 추이처럼 표시됨",
            "고지서 원자료가 없으면 총액 Scenario로만 표시하고 세목 분해를 금지",
            "검증 완료",
        ),
        (
            "P1-01",
            "P1",
            "기간 정합성",
            "모든 Peer Snapshot을 2026Q1로 표시하나 공식 최신 결산기가 다름",
            "data/reit_peer_snapshot.csv",
            "롯데 공식 기준일 2025-12-31, ESR 2025-11-30인데 Snapshot period는 모두 2026Q1",
            "회사·기간 비교가 동질적이라는 오해와 연환산 오류 가능",
            "metric-level reporting_period, annualized flag, statement_scope를 필수화",
            "검증 완료",
        ),
        (
            "P1-02",
            "P1",
            "범위 정합성",
            "SK Snapshot이 연결 재무제표와 별도 투자보고서 연환산 값을 혼합",
            "data/reit_peer_snapshot.csv; data/sk_reit_latest_kpis.csv",
            "자산·부채는 연결, FFO와 배당은 별도 투자보고서×4, 일부 손익은 연결 분기×4",
            "분자·분모 범위가 달라 Tax/Assurance 비율 해석이 약화",
            "각 field에 scope와 annualization_method를 저장하고 혼합 비율 차단",
            "부분 검증",
        ),
        (
            "P1-03",
            "P1",
            "역사 데이터",
            "단일 Snapshot으로 5개년 재무실적을 합성",
            "dart_financials.py:95-140",
            "최신 연도에 0.82/0.88/0.93/0.97/1.00 등의 계수를 적용",
            "실제 역사 추이와 변동성·Red Flag가 왜곡될 수 있음",
            "공식 DART 연도별 fact만 사용하고 결측은 data_insufficient로 유지",
            "검증 완료",
        ),
        (
            "P1-04",
            "P1",
            "Source lineage",
            "sample_snapshot을 api_snapshot으로 정규화하고 corp code도 sample 값",
            "data_source_policy.py:69-82; data/reit_master.csv",
            "sample_snapshot→api_snapshot alias, 대표회사 dart_corp_code가 sample_001 등",
            "사용자가 API/공식값으로 오인하고 자동 DART 추적이 불안정",
            "sample_snapshot을 sample_estimate로 유지하고 실제 DART corp code 저장; field-level lineage 추가",
            "검증 완료",
        ),
        (
            "P1-05",
            "P1",
            "FFO",
            "FFO proxy가 정식 FFO bridge가 아님",
            "metric_definitions.py:85-100; dart_financials.py:148-209",
            "Snapshot 우선, 결측 시 CFO→영업이익→순이익; 감가상각·처분손익·평가손익 조정 없음",
            "회사 간 FFO 비교와 보유세/FFO Red Flag의 경제적 의미가 일관되지 않음",
            "FFO bridge를 회사·기간별로 저장하고 fallback proxy type을 별도 라벨링",
            "검증 완료",
        ),
        (
            "P1-06",
            "P1",
            "부채",
            "일부 차입 구성계정만 있어도 전체 이자부 차입부채로 확정",
            "metric_definitions.py:47-68; api_dart.py",
            "available component가 하나라도 있으면 합계를 반환하고 fallback/fullness 검사를 하지 않음",
            "사채·리스부채 누락으로 LTV와 이자감당력 왜곡 가능",
            "필수 구성계정 completeness flag와 residual reconciliation을 추가",
            "검증 완료",
        ),
        (
            "P1-07",
            "P1",
            "순차입금",
            "단기금융자산 사용제한 여부를 구조화하지 않음",
            "metric_definitions.py:71-82; api_dart.py",
            "코드는 모든 matched short-term financial assets를 차감할 수 있으나 UI 설명은 즉시 사용 가능 자산만 차감한다고 기재",
            "담보·질권 예금을 차감해 순차입금을 과소평가할 수 있음",
            "restricted_cash flag가 확인된 금액만 제외하고 불명확하면 차감 금지",
            "부분 검증",
        ),
        (
            "P1-08",
            "P1",
            "세법 범위",
            "현재 보유세 모델이 전체 보유세를 포괄하지 않음",
            "calculations_tax.py:38-100; ui_tax.py",
            "재산세·도시지역분·지방교육세 기본식만 있고 지역자원시설세·종합부동산세·농특세·감면·합산·세부담상한·해외세 제외",
            "추정 보유세 총액을 신고 수준으로 해석할 수 없음",
            "세목 coverage matrix를 UI에 고정하고 screening total 명칭으로 제한",
            "검증 완료",
        ),
        (
            "P1-09",
            "P1",
            "보유세 fallback",
            "fallback 세액 산식이 브리지와 다름",
            "tax_data_loader.py:99-127; calculations_holding_tax_bridge.py:32-43",
            "loader는 official_price×1.1%, bridge는 official_price×70%×1.1%",
            "동일 입력에서 경로에 따라 세액이 42.9% 차이",
            "단일 tax calculation service로 통합하고 formula_version 저장",
            "검증 완료",
        ),
        (
            "P1-10",
            "P1",
            "공시가격",
            "대표 3사 공시가격·과세표준·세액의 자산별 공식 원천 부재",
            "data/reit_tax_snapshot.csv; tax_data_loader.py",
            "모든 행이 회사 전체 추정이며 PNU·연도·V-World 응답·고지서 id가 없음",
            "Ground Truth 조정과 자산별 Request 우선순위의 신뢰도가 낮음",
            "PNU/주소/자산명/연도/응답 hash를 포함한 자산별 source table 구축",
            "검증 완료",
        ),
        (
            "P1-11",
            "P1",
            "납세의무자",
            "소유구조·책임임대차의 세부담 귀속을 모델링하지 않음",
            "tax_data_loader.py; data/reit_tax_snapshot.csv",
            "연결실체와 법적 소유자가 다를 수 있고 롯데 일부 임대차는 제세공과금을 임차인이 부담한다고 공시",
            "REIT 현금유출과 법정 고지세액을 동일시할 수 있음",
            "asset-owner-taxpayer-payer 구조와 lease tax pass-through를 별도 필드로 관리",
            "부분 검증",
        ),
        (
            "P1-12",
            "P1",
            "Validation",
            "Tax validation이 세율·기간·소유구조·세목 coverage를 점검하지 않음",
            "tax_validation.py:22-97; tests",
            "결측/0/비율 범위는 검사하지만 세액=과세표준×세율, period/scope, legal owner, 세목 누락은 검사하지 않음",
            "현재 P0 계산 불일치가 테스트를 통과",
            "법정 산식 reconciliation과 official ground-truth fixture 테스트 추가",
            "검증 완료",
        ),
        (
            "P1-13",
            "P1",
            "Power BI",
            "Peer median이 단일 회사 slicer에서 선택 회사 값으로 축소 가능",
            "powerbi/K_REIT_Tax_Dashboard_v1.SemanticModel/definition/tables/_Measures.tmdl:242-251",
            "MEDIANX(ALLSELECTED(DimREIT[company_name]), ...) 사용",
            "회사 선택 시 Peer 대비 차이가 0으로 보일 수 있음",
            "peer universe filter를 선택 회사 filter와 분리하고 REMOVEFILTERS/보존 조건 명시",
            "정적 검증 완료",
        ),
        (
            "P1-14",
            "P1",
            "Power BI",
            "공유 연도 차원이 없어 연도 slicer가 모든 Fact를 일관되게 필터링하지 못함",
            "powerbi/K_REIT_Tax_Dashboard_v1.SemanticModel/definition/relationships.tmdl:1-27",
            "모든 관계는 stock_code만 연결; Issue·Request·Stress 등은 공통 year dimension이 없음",
            "다년 데이터가 추가되면 페이지 간 회사·연도 수치가 불일치할 수 있음",
            "DimPeriod를 추가하고 stock_code+period grain uniqueness를 검증",
            "정적 검증 완료",
        ),
        (
            "P1-15",
            "P1",
            "Memo·Request",
            "Memo가 사실관계·법적근거·잠정분석을 분리하지 않고 첫 행만 사용",
            "calculations_tax_review_pack.py:266-340; tax_request_mapping.py",
            "6개 섹션만 생성하고 reconciliation.iloc[0]/bridge.iloc[0] 사용; 종부세 고지서·법적 소유자 확인 자료도 기본 요청에서 누락",
            "자산 다건 시 금액 누락 및 Tax 검토문서의 감사추적성 부족",
            "회사 총계 aggregation 후 9개 표준 섹션과 법령·요청자료 연결 추가",
            "검증 완료",
        ),
        (
            "P2-01",
            "P2",
            "Cap rate·WALE",
            "Cap rate와 WALE 상세가 SK sample에만 존재",
            "data_availability.py:43-62; data/sk_reit_asset_metrics.csv",
            "비SK는 data_insufficient로 차단되지만 원공시 문서는 저장소에 없고 계약별 WALE 재계산도 없음",
            "Peer 화면의 비교 가능성이 제한됨",
            "원문 reference/hash와 가중기준을 저장",
            "검증 완료",
        ),
        (
            "P2-02",
            "P2",
            "Power BI portability",
            "TMDL Power Query가 사용자 절대경로를 참조",
            "powerbi/K_REIT_Tax_Dashboard_v1.SemanticModel/definition/tables/*.tmdl",
            "<PROJECT_ROOT>\\powerbi\\exports 경로 하드코딩",
            "다른 검토자 환경에서 refresh 실패",
            "PBIP 상대경로 parameter 또는 배포용 data source parameter 사용",
            "정적 검증 완료",
        ),
        (
            "P2-03",
            "P2",
            "Power BI grain",
            "Fact 관계가 stock_code만 사용",
            "relationships.tmdl:1-27",
            "현재는 1회사 1최신연도라 중복이 없지만 다년/다자산 확장 시 many-to-many 위험",
            "향후 집계·filter ambiguity",
            "회사·기간·자산 grain별 dimension과 composite surrogate key 설계",
            "검증 완료",
        ),
        (
            "P2-04",
            "P2",
            "Source UX",
            "sample_snapshot이 API/Snapshot으로 표시될 수 있음",
            "data_source_policy.py:74; ui_methodology.py",
            "실제 bundled sample임에도 canonical api_snapshot label 승계",
            "사용자 오해 가능",
            "sample/estimate 라벨을 유지하고 source note에 raw type 표시",
            "검증 완료",
        ),
        (
            "P2-05",
            "P2",
            "요청자료",
            "대표 회사별 요청자료가 대부분 동일한 generic list",
            "tax_request_mapping.py; powerbi/exports/fact_tax_request.csv",
            "대표 3사 각각 11개이며 회사별 법적 소유·해외자산·임대차 tax pass-through 특성이 충분히 반영되지 않음",
            "실무 relevance와 우선순위 차별화 부족",
            "asset type·ownership·red flag rule별 request template 분기",
            "검증 완료",
        ),
        (
            "P2-06",
            "P2",
            "테스트 coverage",
            "Power BI measure와 Streamlit 수치 일치가 일부 대표 ratio에 한정",
            "tests/test_powerbi_export.py",
            "ratio SUM 오류는 방지하지만 slicer context·peer median·다년 filter는 자동 검증하지 않음",
            "보고서 interaction 회귀 가능",
            "TMDL 정적 lint와 representative filter-context 테스트 추가",
            "검증 완료",
        ),
        (
            "P2-07",
            "P2",
            "Power BI 요청자료",
            "동일 회사·연도에서 요청자료명이 중복되어 Request 건수가 과대 표시됨",
            "tax_request_mapping.py; powerbi/exports/fact_tax_request.csv; _Measures.tmdl",
            "대표 3사 모두 '자산별 장부가액 명세'가 서로 다른 목적·이슈로 2회 생성되어 11행이지만 고유 요청자료명은 10개",
            "Power BI Request count가 실제 발송 문서 종류보다 1건 많게 보임",
            "요청자료명 단위로 목적·관련 이슈를 합치거나 measure를 DISTINCTCOUNT(request_item)로 변경",
            "검증 완료",
        ),
        (
            "P3-01",
            "P3",
            "자동화",
            "공식 XBRL 원문 hash와 재현 가능한 fact snapshot 부재",
            "repository-wide",
            "검증은 외부 원문과 수동 대조에 의존",
            "향후 재검증 비용 증가",
            "official source manifest와 checksum 기반 snapshot pipeline 구축",
            "개선 제안",
        ),
        (
            "P3-02",
            "P3",
            "Tax rule engine",
            "법령 시행일·지자체 조례·세목별 rule version 관리 부재",
            "calculations_tax.py",
            "현재 상수식 중심",
            "법령 변경 추적 어려움",
            "effective_date가 있는 rule table과 법적 근거 URL 관리",
            "개선 제안",
        ),
        (
            "P3-03",
            "P3",
            "자산 그래프",
            "자산-법적소유자-납세의무자-현금부담자 관계 모델 부재",
            "tax_data_loader.py",
            "회사 전체 한 행 중심",
            "SPC/신탁/해외자산 분석 확장 제한",
            "property ownership graph와 tax incidence table 구축",
            "개선 제안",
        ),
        (
            "P3-04",
            "P3",
            "회귀 검증",
            "공시 대 Streamlit 대 Power BI end-to-end 자동 reconciliation 미구현",
            "scripts/export_powerbi_dataset.py; tests",
            "현재 로컬 export 일치만 검사",
            "신규 Snapshot 적재 시 오류 조기 탐지 제한",
            "대표회사 official fixture와 golden-output regression 구축",
            "개선 제안",
        ),
    ]
    return [
        {
            "issue_id": issue_id,
            "severity": severity,
            "category": category,
            "title": title,
            "affected_files": affected_files,
            "evidence": evidence,
            "impact": impact,
            "recommended_action": recommended_action,
            "validation_status": validation_status,
        }
        for (
            issue_id,
            severity,
            category,
            title,
            affected_files,
            evidence,
            impact,
            recommended_action,
            validation_status,
        ) in issues
    ]


def _strict_match_stats(financial_rows: list[dict[str, Any]]) -> dict[str, dict[str, int | float]]:
    result: dict[str, dict[str, int | float]] = {}
    for company_name in OFFICIAL_COMPANIES:
        candidates = [
            row
            for row in financial_rows
            if row["company_name"] == company_name
            and row["project_value"] != ""
            and row["official_value"] != ""
        ]
        matched = [row for row in candidates if row["verdict"] in {"match", "rounding_difference"}]
        result[company_name] = {
            "matched": len(matched),
            "compared": len(candidates),
            "rate": len(matched) / len(candidates) if candidates else 0.0,
        }
    return result


def _build_report(
    financial_rows: list[dict[str, Any]],
    holding_tax_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    metric_rows: list[dict[str, Any]],
    issue_rows: list[dict[str, Any]],
) -> str:
    match_stats = _strict_match_stats(financial_rows)
    severity_counts = Counter(row["severity"] for row in issue_rows)

    project_snapshot = {
        row["company_name"]: row for row in _read_csv(ROOT / "data" / "reit_peer_snapshot.csv")
    }
    tax_snapshot = {
        row["company_name"]: row for row in _read_csv(ROOT / "data" / "reit_tax_snapshot.csv")
    }

    bridge_rows = []
    for company_name in OFFICIAL_COMPANIES:
        tax_row = tax_snapshot[company_name]
        tax_base = _number(tax_row["estimated_tax_base"])
        tax = _number(tax_row["estimated_holding_tax"])
        expected = tax_base * 0.011 if tax_base is not None else None
        implied = tax / tax_base if tax_base and tax is not None else None
        bridge_rows.append(
            [
                company_name,
                _fmt_number(tax_base, 1),
                _fmt_number(tax, 1),
                _fmt_pct(implied, 4),
                _fmt_number(expected, 1),
                _fmt_number((tax or 0) - (expected or 0), 1),
            ]
        )

    company_rows = []
    for company_name, official in OFFICIAL_COMPANIES.items():
        stat = match_stats[company_name]
        company_rows.append(
            [
                company_name,
                official["stock_code"],
                official["dart_corp_code"],
                f"{official['report_name']} / {official['report_date']}",
                official["reporting_period"],
                official["statement_scope"],
                f"{stat['matched']}/{stat['compared']} ({stat['rate'] * 100:.1f}%)",
            ]
        )

    ffo_rows = []
    for company_name, official in OFFICIAL_COMPANIES.items():
        snapshot = project_snapshot[company_name]
        official_ffo = official["facts"]["ffo_proxy"][0]
        project_ffo = _number(snapshot["ffo_proxy"])
        if company_name == "SK리츠":
            starting_item = "별도 투자보고서 공시 FFO 22,134"
            additions = "원문 조정 bridge 미보관"
            deductions = "원문 조정 bridge 미보관"
            other_adjustments = "4배 연환산"
        else:
            starting_item = "Snapshot ffo_proxy 직접값"
            additions = "미제공"
            deductions = "미제공"
            other_adjustments = "공식 FFO 및 조정내역 미확인"
        difference = project_ffo - official_ffo if project_ffo is not None and official_ffo is not None else None
        ffo_rows.append(
            [
                company_name,
                starting_item,
                additions,
                deductions,
                other_adjustments,
                _fmt_number(project_ffo, 1),
                _fmt_number(official_ffo, 1),
                _fmt_number(difference, 1),
                "period_difference" if company_name == "SK리츠" else "unverifiable",
            ]
        )

    powerbi_rows = []
    for company_name in OFFICIAL_COMPANIES:
        snapshot = project_snapshot[company_name]
        tax = _number(snapshot["estimated_holding_tax"])
        ffo = _number(snapshot["ffo_proxy"])
        assets = _number(snapshot["total_assets"])
        debt = _number(snapshot["borrowings_total"])
        powerbi_rows.append(
            [
                company_name,
                _fmt_number(tax, 1),
                _fmt_number(ffo, 1),
                _fmt_pct(tax / ffo if tax is not None and ffo else None),
                _fmt_pct(debt / assets if debt is not None and assets else None),
                "CSV와 Measure 산식 일치",
            ]
        )

    powerbi_issue_rows = _read_csv(ROOT / "powerbi" / "exports" / "fact_tax_issue.csv")
    powerbi_request_rows = _read_csv(ROOT / "powerbi" / "exports" / "fact_tax_request.csv")
    powerbi_validation_rows = _read_csv(ROOT / "powerbi" / "exports" / "fact_tax_validation.csv")
    powerbi_control_rows = []
    for company_name in OFFICIAL_COMPANIES:
        issue_count = sum(row.get("company_name") == company_name for row in powerbi_issue_rows)
        request_count = sum(row.get("company_name") == company_name for row in powerbi_request_rows)
        validation_count = sum(row.get("company_name") == company_name for row in powerbi_validation_rows)
        powerbi_control_rows.append([company_name, issue_count, request_count, validation_count])

    issue_summary = _markdown_table(
        ["등급", "건수", "의미"],
        [
            ["P0", severity_counts["P0"], "수치·mapping·세목 표시의 즉시 수정 필요 오류"],
            ["P1", severity_counts["P1"], "Tax/Assurance 결론과 제출 신뢰성에 중대한 영향"],
            ["P2", severity_counts["P2"], "설명 가능성·확장성·Power BI UX 위험"],
            ["P3", severity_counts["P3"], "차기 자동화·운영 고도화"],
        ],
    )

    p0_table = _markdown_table(
        ["ID", "오류", "핵심 증거", "영향"],
        [
            [row["issue_id"], row["title"], row["evidence"], row["impact"]]
            for row in issue_rows
            if row["severity"] == "P0"
        ],
    )

    source_table = _markdown_table(
        ["source_type", "현재 해석", "검증 판단"],
        [
            ["official_disclosure", "DART/API 공식 공시", "적정하나 field-level period/scope 필요"],
            ["api_snapshot", "API/Snapshot", "sample_snapshot alias 때문에 현재 과대표시 가능"],
            ["peer_snapshot", "Peer 비교 Snapshot", "기준일·범위·원문 reference 필수"],
            ["peer_snapshot_estimate", "Peer 기반 추정", "대표 Tax 데이터의 실제 상태와 부합"],
            ["sample_estimate", "예시·추정", "SK 상세 sample에 적합"],
            ["data_insufficient", "데이터 부족", "비SK 상세 차단에 적합"],
        ],
    )

    non_sk_table = _markdown_table(
        ["회사", "SK 자산명", "SK 임차인", "SK Cap rate/WALE", "판정"],
        [
            ["롯데리츠", "미검출", "미검출", "data_insufficient", "검증 완료"],
            ["ESR켄달스퀘어리츠", "미검출", "미검출", "data_insufficient", "검증 완료"],
            ["제이알글로벌리츠", "미검출", "미검출", "data_insufficient", "검증 완료"],
            ["신한알파리츠", "미검출", "미검출", "data_insufficient", "검증 완료"],
        ],
    )

    report = f"""# K-REITs Risk Intelligence Platform v14.1 Ground Truth Validation

> 검증 기준일: {AS_OF_DATE}
> 검증 방식: read-only 독립 검증. 애플리케이션·계산 로직·기존 데이터는 수정하지 않음.
> 단위: 별도 표시가 없으면 백만원.
> 결론 성격: 공개자료 기반 예비 검증이며 세무신고, 법률의견, 감사증거 또는 투자판단을 대체하지 않음.

## 1. Executive Summary

### 결론

v14.1은 **Tax screening workflow, source limitation 표시, 비SK 상세데이터 차단, Streamlit-Power BI export 구조**는 유용한 프로토타입 수준입니다. 그러나 현재 정량 결과를 외부 제출용 Ground Truth 또는 신고·감사 결론으로 제시하기에는 **P0 {severity_counts['P0']}건, P1 {severity_counts['P1']}건**이 남아 있습니다.

가장 중요한 결론은 다음과 같습니다.

1. `borrowings_current`는 대표 3사의 공식 유동성 이자부 차입부채와 일치하지 않으며, SK리츠에서는 공식 **유동부채**와 동일해 mapping 오류 가능성이 높습니다.
2. 보유세 브리지는 적용세율 1.1%를 보여 주지만 Snapshot 세액이 있으면 그 세액을 그대로 사용합니다. 세 회사의 implied rate는 1.4643%~1.7869%입니다.
3. 공시가격 상승률 Red Flag가 실제로는 `holding_tax_to_ffo`를 사용합니다.
4. 최근 5년 재산세·도시지역분·지방교육세는 고지서가 아니라 최신 추정세액을 60%/30%/10%로 임의 배분한 합성 시계열입니다.
5. 롯데리츠와 ESR켄달스퀘어리츠의 재무 Snapshot은 공식 최신 사업보고서와 직접 조정되지 않으며, SK리츠는 연결/별도와 분기 연환산 값이 혼합되어 있습니다.

엄격 일치율은 **프로젝트에 값이 있고 공식 동기간·동범위 값도 확인되는 항목**을 분모로 하며 `match`와 `rounding_difference`만 일치로 보았습니다. 기간·범위 차이는 불일치로 포함했습니다.

{_markdown_table(['회사', '종목코드', 'DART corp code', '공식 보고서', '공식 기간', '범위', '엄격 일치율'], company_rows)}

SK리츠의 직접 비교 가능한 재무상태 핵심 4개 항목(총자산, 투자부동산, 이자부 차입부채, 유동성 이자부 차입부채)만 보면 3/4(75.0%)가 일치합니다. 전체 엄격 일치율이 27.3%인 이유는 Snapshot 손익·현금흐름이 연환산 또는 다른 범위를 사용하기 때문입니다.

### 이슈 요약

{issue_summary}

### 제출 가능성

- **정량 보유세 산출물 또는 공식 Ground Truth 제출:** 현재 불가.
- **Tax/Assurance workflow 자동화 프로토타입 시연:** P0를 수정하고 모든 수치를 Snapshot/estimate로 명확히 제한하면 조건부 가능.
- **Power BI 포트폴리오 시연:** 현재 export 수치 자체는 Streamlit 입력과 일치하지만 Peer median과 연도 filter를 수정한 뒤 권장.

## 2. 검증 범위와 한계

### 검증 범위

- 코드: `app.py`, `config.py`, `dart_financials.py`, `api_manager.py`, `data_source_policy.py`, `data_availability.py`, `tax_data_loader.py`, `calculations_peer.py`, `calculations_holding_tax_bridge.py`, `calculations_tax_review_pack.py`, `red_flag_engine.py`, `tax_request_mapping.py`, `tax_validation.py`, `ui_tax.py`, `ui_methodology.py`, `scripts/export_powerbi_dataset.py`.
- 데이터: `data/reit_master.csv`, `data/reit_peer_snapshot.csv`, `data/reit_tax_snapshot.csv`, `data/red_flag_rules.json`, SK 상세 CSV.
- 출력: `powerbi/exports/*.csv`, TMDL table/measure/relationship 정의.
- 대표회사: SK리츠, 롯데리츠, ESR켄달스퀘어리츠.
- 공식 원천: DART/OpenDART XBRL 및 국가법령정보센터.

### 검증 한계

- 서버 API Key는 로컬에서 설정되지 않아 DART/ECOS/V-World live 호출 대신 공식 DART 원문과 다운로드 XBRL을 독립 조회했습니다.
- 자산별 재산세 고지서, 과세대장, PNU별 공시지가·건축물 시가표준액, 감면 결정, 종합부동산세 고지서는 공개 공시에서 확보하지 못했습니다.
- 롯데리츠·ESR켄달스퀘어리츠의 공식 FFO bridge는 최신 XBRL에서 확인하지 못했습니다.
- SK Cap rate/WALE CSV가 참조하는 Annual Report/투자보고서 원문 파일은 저장소에 없으므로 source metadata와 DART 공시 일부만 대조했습니다.

## 3. 저장소 및 데이터 흐름

### 기준 상태

- 버전: `v14.1`, `APP_VERSION_NAME = Metric Definition & Source Lineage Stabilization`.
- 기준 커밋: `bcd934e Finalize v14.1 Tax metrics, source lineage, and API fallback controls`.
- 작업 시작 전 기존 변경: `.gitignore`, Power BI PBIX/export, `scripts/export_powerbi_dataset.py`, PBIP/PBIR/TMDL 및 자동화 파일. 기존 변경은 초기화하지 않았습니다.
- 초기 테스트: `47 passed`.

### 데이터 흐름

`DART/API 또는 bundled CSV` → `loading/normalization` → `metric calculation` → `Streamlit UI` → `Tax Review Pack` → `powerbi/exports` → `TMDL measures`

상세 계보는 [source_lineage.csv](source_lineage.csv)에 대표 3사×24개 지표군, 총 {len(source_rows)}개 회사-지표 행으로 기록했습니다.

주요 취약점은 회사 행 단위 `source_type` 하나가 여러 지표의 서로 다른 원천·기간·범위를 대표한다는 점입니다. SK Snapshot 한 행 안에서도 연결 재무상태, 연결 분기 연환산 손익, 별도 투자보고서 연환산 FFO가 섞여 있습니다.

## 4. 대표회사 Ground Truth 결과

### 공식 보고서

1. [SK리츠 사업보고서 2026-06-10](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260610000569), DART corp code `01535150`, 연결 기준.
2. [롯데리츠 사업보고서 2026-03-10](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260310002810), DART corp code `01363818`, 별도 기준.
3. [ESR켄달스퀘어리츠 사업보고서 2026-02-13](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260213002140), DART corp code `01437186`, 연결 기준.

### 핵심 차이

- **SK리츠:** 총자산 5,408,832, 투자부동산 5,232,672, 이자부 차입부채 3,103,855는 공식 공시와 반올림 수준에서 일치합니다. 그러나 `borrowings_current` 1,318,000은 공식 유동성 이자부 차입부채 1,243,689.893이 아니라 공식 유동부채 1,318,000.437과 일치합니다.
- **롯데리츠:** 프로젝트 총자산 2,460,000 vs 공식 2,594,407.042(-5.18%), 투자부동산 2,315,000 vs 공식 2,527,222.595(-8.40%), 총 이자부 차입부채 1,298,000 vs 공식 1,307,019.778(-0.69%). 차입부채 차이는 작지만 반올림이 아닌 90억원 규모이며 lineage가 없습니다.
- **ESR켄달스퀘어리츠:** 프로젝트 총자산 3,135,000 vs 공식 2,835,773.540(+10.55%), 투자부동산 3,010,000 vs 공식 2,433,793.981(+23.68%), 차입부채 1,645,000 vs 공식 1,586,961.428(+3.66%). 프로젝트 순이익 +52,900과 공식 최신 연결 반기 순손실 -3,436.388은 부호도 다릅니다.

전체 계정별 결과는 [financial_reconciliation.csv](financial_reconciliation.csv)에 {len(financial_rows)}행으로 제공했습니다.

## 5. 보유세 계산 검증

### 법령 기준일과 확인한 기본식

법령 검토 기준일은 **{AS_OF_DATE}**입니다.

- 지방세법은 2026-07-01 시행 법률, 지방세법 시행령은 2026-06-01 시행 대통령령을 기준으로 확인했습니다.
- 지방세법 제111조: 별도합산 토지는 2억원 이하 0.2%, 2억원 초과 10억원 이하 0.3% 누진, 10억원 초과 0.4% 누진. 일반 건축물 0.25%.
- 지방세법 제112조: 도시지역분 표준세율 0.14%, 조례로 0.23% 이하 조정 가능.
- 지방세법 제151조: 도시지역분을 제외한 재산세액의 20%를 지방교육세로 계산.
- 지방세법 시행령 제109조: 토지·건축물 공정시장가액비율 70%.
- 종합부동산세법은 2026-01-01 시행 법령이 존재하나 현재 모델은 이를 계산하지 않습니다.

공식 근거:

- [지방세법 제111조](https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0111&lsiSeq=282559&urlMode=lsScJoRltInfoR)
- [지방세법 제112조](https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0112&lsiSeq=282559&urlMode=lsScJoRltInfoR)
- [지방세법 제151조](https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0151&lsiSeq=282559&urlMode=lsScJoRltInfoR)
- [지방세법 시행령 제109조](https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0109&lsiSeq=286395&urlMode=lsScJoRltInfoR)
- [종합부동산세법](https://law.go.kr/LSW/lsInfoP.do?lsiSeq=280417)

### 실제 구현 경로

1. 상세 estimator `calculations_tax.py`는 기본 재산세·도시지역분·지방교육세 산식의 주요 표준세율과 일치합니다.
2. 그러나 주 Tax UI 경로는 자산별 상세 estimator가 아니라 `reit_tax_snapshot.csv`의 회사 전체 추정세액을 우선 사용합니다.
3. `tax_data_loader.py` fallback은 `official_price × 1.1%`, 브리지는 `official_price × 70% × 1.1%`이므로 경로가 다릅니다.
4. Snapshot 세액이 있으면 브리지에서 사용자가 보는 적용세율을 무시하고 저장 세액을 유지합니다.

{_markdown_table(['회사', '추정 과세표준', 'Snapshot 세액', 'Implied rate', '1.1% 계산 세액', '차이'], bridge_rows)}

### 세목 coverage

| 세목 | 상세 estimator | 회사 전체 Snapshot 경로 | 판단 |
|---|---|---|---|
| 재산세 본세 | 기본 토지·건축물 식 일부 | Snapshot 총액에 내재한다고 가정 | 부분 검증 |
| 도시지역분 | 0.14% | Snapshot 총액에 내재한다고 가정 | 부분 검증 |
| 지방교육세 | 재산세 본세의 20% | Snapshot 총액에 내재한다고 가정 | 부분 검증 |
| 지역자원시설세 | 제외 | 제외 | 추가 자료 필요 |
| 종합부동산세 | 제외 | 제외 | 추가 자료 필요 |
| 농어촌특별세 | 제외 | 제외 | 추가 자료 필요 |
| 해외 부동산 현지 보유세 | 제외 | 제외 | 추가 자료 필요 |
| 감면·합산·분리과세·세부담상한 | 단순 option 일부 | 미반영 | 추가 자료 필요 |

### 공시 비용과의 대사

세 회사 모두 프로젝트 추정세액과 공시된 세금/관련 비용은 **비교 불가**입니다. 공시 계정은 기간·세목·연결범위가 다르고, 롯데리츠는 직접운영비용에 감가상각·수수료·보험료·세금이 함께 포함됩니다. 상세 결과는 [holding_tax_reconciliation.csv](holding_tax_reconciliation.csv)입니다.

## 6. FFO proxy 검증

### 구현식

현재 구현은 다음과 같습니다.

`FFO proxy = Snapshot ffo_proxy 우선; 없으면 영업활동현금흐름; 없으면 영업이익; 없으면 당기순이익`

따라서 정식 FFO처럼 `순이익 + 감가상각 - 부동산 처분이익 - 공정가치평가이익 ± 비경상 조정` bridge를 수행하지 않습니다.

{_markdown_table(['회사', '시작 항목', '가산', '차감', '기타 조정', '프로젝트 FFO', '공시/참조 FFO', '차이', '판정'], ffo_rows)}

SK리츠 FFO 22,134는 `data/sk_reit_latest_kpis.csv`의 별도 투자보고서 source metadata를 근거로 했으며, 프로젝트 88,536은 정확히 4배입니다. 해당 원문이 저장소에 없고 주 Snapshot은 연결 재무상태 수치와 혼합되므로 `period_difference`로 판정했습니다. 롯데·ESR은 공식 FFO 조정표를 확인하지 못해 `unverifiable`입니다.

### Tax screening KPI 적합성

| KPI | 장점 | 한계 | 데이터 확보 | 판단 |
|---|---|---|---|---|
| 보유세 / FFO proxy | 배당·반복 현금창출력과 연결 | 회사별 proxy 정의 불일치 | 현재 있음 | 보조지표 |
| 보유세 / CFO | 현금흐름표 공시와 직접 대사 가능 | 운전자본·일회성 변동 큼 | DART 가능 | 검증용 보조지표 |
| 보유세 / 영업수익 | 회사 간 단순 비교 | 수익성·임대차 비용전가 반영 못함 | 현재 있음 | 보조지표 |
| 보유세 / NOI | 자산 세부담과 가장 직접적 | 자산별 정상화 NOI 확보 어려움 | 현재 부족 | 권장 핵심지표 |
| 보유세 / 배당가능이익 | 실제 배당제약과 연결 | 법정 계산·별도재무제표 자료 필요 | 현재 부족 | 실무 검토지표 |

## 7. 총부채·차입금·충당부채 검증

### 구분

- 총부채: 재무상태표의 모든 부채. 차입금, 사채, 리스부채, 매입채무, 미지급비용, 충당부채, 이연법인세부채 등을 포함합니다.
- 이자부 차입부채: 단기차입금 + 유동성장기차입금 + 장기차입금 + 사채 + 정책상 포함한 리스부채.
- 비이자성 부채: 매입채무, 미지급비용, 충당부채, 이연법인세부채 등.

### 검증 결과

- 장부기준 NAV proxy는 총자산-총부채로 정의되어 충당부채도 총부채를 통해 포함합니다. 정의는 적정합니다.
- Gross debt/LTV는 이자부 차입부채를 사용하고 충당부채를 제외합니다. 정의는 적정합니다.
- 현재 Power BI export의 `total_liabilities_eok`, `provisions_eok`, `cash_and_cash_equivalents_eok`, `book_nav_proxy_eok`는 Snapshot schema 한계로 공란입니다.
- 가장 큰 오류는 `borrowings_current`입니다. 이 값은 Assurance에서 유동성 차입금 비율로 사용되지만 공식 XBRL 계정과 조정되지 않습니다.
- `derive_interest_bearing_debt`는 하나의 구성계정만 확보되어도 부분합을 전체 차입부채로 반환합니다. 구성 completeness 검사가 필요합니다.

## 8. NAV·LTV·이자감당력 검증

상세 정의와 판단은 [metric_definition_matrix.csv](metric_definition_matrix.csv)에 {len(metric_rows)}개 지표로 정리했습니다.

- `장부기준 NAV proxy = 총자산 - 총부채`: 시장가치 NAV와 구분되어 있어 명칭은 적정합니다.
- `총자산 기준 Gross LTV = 이자부 차입부채 / 총자산`: 담보 LTV가 아니라 총자산 차입비율입니다. 현재 명칭은 구분을 제공합니다.
- `Property LTV = 이자부 차입부채 / 투자부동산 장부금액`: 담보별 debt/value가 아니라 회사 전체 부채와 장부가를 사용합니다.
- `FFO 이자감당력 proxy = FFO proxy / 이자비용`: 분자·분모의 기간·연결범위가 동일해야 하나 Snapshot metadata가 이를 보장하지 않습니다.
- `유효차입금리 proxy = 이자비용 / 평균 이자부 차입부채`: 평균잔액이 없으면 기말잔액 proxy를 쓰므로 반드시 proxy 표기가 필요합니다.

## 9. Source Reliability 검증

{source_table}

가장 중요한 source 이슈는 `data_source_policy.py:74`의 `sample_snapshot -> api_snapshot` alias입니다. 현재 `reit_peer_snapshot.csv`는 명시적으로 `sample_snapshot`인데 UI·export 정책에서는 API/Snapshot으로 승격될 수 있습니다. 또한 `reit_master.csv`의 대표회사 DART corp code가 실제 `01535150`, `01363818`, `01437186`가 아니라 `sample_001` 등입니다.

권장 최소 source grain은 다음입니다.

`company + metric + reporting_period + statement_scope + source_document + account_id + transformation + annualized_flag + source_type`

## 10. 비SK 데이터 재사용 검증

{non_sk_table}

`data_availability.py`는 SK리츠/395400만 상세 sample 회사로 인정하고 비SK 회사의 asset, tax asset, debt maturity, Cap rate, tenant detail을 차단합니다. `tests/test_no_sk_data_reuse.py`와 `tests/test_non_sk_tax_pack.py`도 이를 검증합니다. 따라서 **직접적인 SK 자산·임차인·Cap rate·WALE 재사용은 발견하지 못했습니다.**

다만 모든 회사가 동일한 합성 Peer/Tax Snapshot 구조와 generic Request List를 쓰는 것은 별도 문제이며, 이는 데이터 재사용이 아니라 source 품질·회사별 relevance 문제로 P1/P2에 기록했습니다.

## 11. Streamlit·Power BI Reconciliation

{_markdown_table(['회사', '추정 보유세', 'FFO proxy', '보유세/FFO', 'Gross LTV', 'CSV/Measure'], powerbi_rows)}

{_markdown_table(['회사', 'Issue 행', 'Request 행', 'Validation 행'], powerbi_control_rows)}

검증 결과:

- Power BI ratio는 ratio column의 합계가 아니라 `DIVIDE(SUM numerator, SUM denominator)`로 재계산합니다. 이 부분은 적정합니다.
- 대표 3사의 `estimated_holding_tax`, `ffo_proxy`, `holding_tax_to_ffo`, `debt_to_assets`는 Streamlit 입력 Snapshot과 Power BI export에서 일치합니다.
- 현재 export key 중 대표 사실표에서 회사·연도 중복은 발견되지 않았습니다.
- Peer median은 `ALLSELECTED(DimREIT[company_name])`를 사용해 단일 회사 slicer에서 target value로 축소될 수 있습니다.
- 모든 Fact 관계가 `stock_code`에만 연결되어 공통 연도 slicer가 Issue/Request/Stress 전체를 일관되게 필터링하지 않습니다.
- TMDL Power Query는 로컬 절대경로를 사용해 다른 검토자 환경에서 refresh가 실패할 수 있습니다.
- 대표 3사 모두 Request 11행 중 고유 요청자료명은 10개입니다. `자산별 장부가액 명세`가 서로 다른 목적·이슈로 2회 생성되며 현재 Request count는 행 수를 세므로 1건 과대 표시됩니다.

## 12. Red Flag·Request Mapping 검증

### Red Flag

| rule id | metric | threshold | 비교·발생 조건 | 데이터 가용성 | Tax 의미 | Request/Memo 연결 | 오류 여부 |
|---|---|---|---|---|---|---|---|
| `holding_tax_to_ffo` | `holding_tax_to_ffo` | 주의 25%, 높음 35% 또는 Peer percentile | 높을수록 위험 | 값은 있으나 분자·분모 모두 추정 | 현금창출력 대비 세부담 | issue→재산세 고지서·FFO 자료→Memo | 산식 연결은 맞으나 threshold 근거 미검증 |
| `holding_tax_to_operating_revenue` | `holding_tax_to_operating_revenue` | 주의 10%, 높음 15% 또는 Peer percentile | 높을수록 위험 | 값은 있으나 기간 불일치 가능 | 매출 대비 세부담·전가 구조 | 임대차계약·관리비 정산→Memo | 기간·scope 보정 필요 |
| `official_price_to_investment_property` | `official_price_to_investment_property` | 주의 55%, 높음 65% 또는 Peer percentile | 높을수록 위험 | 회사 전체 추정 공시가격 | 장부가 대비 과세기준 proxy | 공시가격·감정평가·면적자료→Memo | 공식 자산별 공시가격 부재 |
| `official_price_growth_placeholder` | `holding_tax_to_ffo` | 주의 30%, 높음 40% 또는 Peer percentile | FFO 비율로 발생 | 실제 공시가격 성장률 없음 | 의도는 가격상승 위험 | 최근 5년 가격·고지서→Memo | **P0: metric 오연결** |

P0 확인:

```text
rule id: official_price_growth_placeholder
label: 공시가격 상승률 추가 검토
metric: holding_tax_to_ffo
```

이 규칙은 공시가격 성장률을 측정하지 않습니다. 대표회사 issue export에서 SK·롯데는 FFO 비율 때문에 공시가격 상승률 주의로 표시되고 ESR은 정상으로 표시됩니다.

### Request List

대표 3사는 각각 11개 요청자료를 생성하며 재산세 고지서, 개별공시지가, FFO proxy 산정자료, 배당가능이익, 자산별 장부가액, 토지대장, 건축물대장을 포함합니다. 기본 구조는 실무적으로 유용합니다.

누락 또는 보완 필요 자료:

- 종합부동산세 고지서와 농어촌특별세 내역.
- 자산별 법적 소유자·수익증권/SPC/신탁 구조 및 납세의무자 확인 자료.
- 책임임대차상 세금 pass-through 조항.
- 해외자산 현지 보유세 고지서.
- 감면·합산배제·세부담상한 적용 근거.

## 13. Tax Review Memo 검증

현재 Memo는 다음 6개 섹션입니다: 검토 대상, 핵심 수치 요약, 주요 Tax 이슈, 요청자료, 실무적 시사점, 제한 및 유의사항.

장점:

- `source_type`, `source_note`, 신뢰수준, estimate limitation을 표시합니다.
- 공식 FFO가 아니라 `FFO proxy`, 확정세액이 아니라 `추정 보유세`로 표시합니다.
- data_insufficient 상태에서 확정적 결론을 피하는 제한문구가 있습니다.

보완 필요:

- 요구되는 9개 구조 중 사실관계, 관련 법적 근거, 잠정 분석이 분리되지 않습니다.
- `reconciliation.iloc[0]`, `bridge.iloc[0]`만 사용해 다자산 합계를 누락할 수 있습니다.
- 세법 조문과 적용/미적용 세목이 Memo에 직접 연결되지 않습니다.
- Request List와 Red Flag는 연결되지만 P0 placeholder rule 때문에 잘못 연결될 수 있습니다.

## 14. 테스트 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| `py -m compileall -q . -x ...` | 통과 | 검증 스크립트 포함 syntax check |
| `py -m pytest -q` | 47 passed | 기존 로직 테스트 |
| `py .\\scripts\\export_powerbi_dataset.py` | 통과 | 9개 CSV 재생성/검증 |
| 비SK SK-data 재사용 | 통과 | 기존 전용 테스트 및 경로 검토 |
| divide-by-zero | 통과 | 기존 테스트 |
| Source metadata 존재 | 통과 | 기존 구조 테스트 |
| 공식 공시 Ground Truth 회귀 | 미구현 | 본 보고서에서 수동 독립 대조 |
| 보유세 세율-세액 조정 | 실패 | P0-02 |
| Power BI slicer context | 정적 위험 확인 | P1-13, P1-14 |

테스트가 통과해도 P0가 남는 이유는 현재 테스트 fixture가 Snapshot 자체의 내부 재현성을 검증할 뿐, 공식 공시·법정 산식과의 외부 조정을 검증하지 않기 때문입니다.

## 15. P0~P3 개선사항

{issue_summary}

### P0 상세

{p0_table}

전체 이슈와 재현 경로는 [p0_p3_issue_register.csv](p0_p3_issue_register.csv)에 {len(issue_rows)}건으로 기록했습니다.

## 16. 최종 제출 가능성

### 현재 가능한 제출

- 아키텍처, 보안, source limitation, 비SK isolation, Tax Review Pack workflow를 설명하는 **프로토타입 포트폴리오**.
- 모든 정량값을 `Snapshot/estimate/proxy`로 명확히 제한한 화면 시연.

### 현재 불가능한 제출

- 회사별 확정 보유세 또는 신고세액 산출.
- PNU/고지서 없이 공시가격·과세표준·보유세를 공식값으로 주장.
- FFO proxy를 공식 FFO로 주장.
- 현재 `borrowings_current` 기반 차환위험을 공시 Ground Truth로 주장.
- 현재 공시가격 상승률 Red Flag를 회사별 사실로 주장.

## 17. 검증하지 못한 항목

1. 대표 3사의 자산별 최신 PNU, 토지 개별공시지가, 건축물 시가표준액.
2. 자산별 재산세·도시지역분·지방교육세·지역자원시설세 고지서.
3. 종합부동산세·농어촌특별세와 합산배제·감면 내역.
4. 연결 자산별 법적 소유자와 실제 납세의무자, 임차인 세금 부담 조항 전체.
5. 롯데리츠·ESR켄달스퀘어리츠의 공식 FFO bridge.
6. SK 상세 Cap rate/WALE source 문서의 페이지별 원문 재수행.
7. 해외부동산 현지 보유세와 환율 기준.
8. Power BI Desktop에서의 실제 slicer interaction. TMDL 정적 검토만 수행했습니다.

각 항목의 상태는 `원자료 추가 필요` 또는 `부분 검증`이며, 0 또는 Peer 평균으로 대체하지 않았습니다.

## 18. 다음 수정 권고

수정은 별도 승인 후 다음 순서로 진행하는 것이 안전합니다.

1. `borrowings_current`를 공식 유동성 이자부 차입계정으로 재구축하고 대표회사 fixture를 추가합니다.
2. 보유세 브리지에서 Snapshot 세액과 가정 세율 중 하나만 authoritative input으로 선택하고 수학적 조정을 강제합니다.
3. `official_price_growth_placeholder`를 비활성화하거나 실제 성장률 metric으로 교체합니다.
4. 합성 5개년 세목 배분을 제거하고 총액 Scenario 또는 `data_insufficient`로 대체합니다.
5. 회사·지표·기간·연결범위·연환산·account_id 단위 source lineage를 도입합니다.
6. 자산별 PNU·고지서·법적 소유자/납세의무자 정보를 확보한 뒤 보유세 산식을 확장합니다.
7. 공식 FFO bridge를 확보하지 못한 회사는 CFO/영업이익 proxy를 별도 유형으로 분리합니다.
8. Power BI Peer median과 공통 기간 dimension을 수정하고 filter-context 회귀 테스트를 추가합니다.
9. Memo를 9개 표준 섹션으로 확장하고 법령 근거·사실·추정·잠정 결론을 분리합니다.

---

검증 산출물은 애플리케이션 코드를 수정하지 않고 생성했습니다. commit과 push는 수행하지 않았습니다.
"""
    return report


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    financial_rows = build_financial_reconciliation()
    holding_tax_rows = build_holding_tax_reconciliation()
    source_rows = build_source_lineage()
    metric_rows = build_metric_definition_matrix()
    issue_rows = build_issue_register()

    _write_csv(
        OUTPUT_DIR / "financial_reconciliation.csv",
        financial_rows,
        [
            "company_name",
            "metric",
            "project_value",
            "official_value",
            "difference",
            "difference_pct",
            "project_unit",
            "official_unit",
            "reporting_period",
            "statement_scope",
            "source_document",
            "source_reference",
            "account_id",
            "account_name",
            "verdict",
            "explanation",
        ],
    )
    _write_csv(
        OUTPUT_DIR / "holding_tax_reconciliation.csv",
        holding_tax_rows,
        [
            "company_name",
            "asset_or_scope",
            "project_estimated_tax",
            "disclosed_tax_or_related_expense",
            "comparable",
            "difference",
            "source",
            "ownership_structure",
            "tax_scope",
            "limitation",
            "verdict",
        ],
    )
    _write_csv(
        OUTPUT_DIR / "source_lineage.csv",
        source_rows,
        [
            "company_name",
            "stock_code",
            "metric",
            "project_period",
            "official_reporting_period",
            "project_statement_scope",
            "raw_source_type",
            "raw_source",
            "loading_function",
            "normalized_column",
            "calculation_function",
            "ui_location",
            "tax_review_pack",
            "power_bi_column_or_measure",
            "source_type",
            "limitation",
        ],
    )
    _write_csv(
        OUTPUT_DIR / "metric_definition_matrix.csv",
        metric_rows,
        [
            "metric",
            "ui_label",
            "implemented_formula",
            "source_columns",
            "included",
            "excluded",
            "financial_meaning",
            "label_accuracy",
            "validation_status",
            "primary_risk",
            "code_reference",
        ],
    )
    _write_csv(
        OUTPUT_DIR / "p0_p3_issue_register.csv",
        issue_rows,
        [
            "issue_id",
            "severity",
            "category",
            "title",
            "affected_files",
            "evidence",
            "impact",
            "recommended_action",
            "validation_status",
        ],
    )

    report = _build_report(financial_rows, holding_tax_rows, source_rows, metric_rows, issue_rows)
    (OUTPUT_DIR / "GROUND_TRUTH_VALIDATION_REPORT.md").write_text(report.rstrip() + "\n", encoding="utf-8")

    match_stats = _strict_match_stats(financial_rows)
    severity_counts = Counter(row["severity"] for row in issue_rows)
    print(f"Generated validation outputs in: {OUTPUT_DIR}")
    for company_name, stats in match_stats.items():
        print(
            f"- {company_name}: {stats['matched']}/{stats['compared']} "
            f"({stats['rate'] * 100:.1f}%) strict match"
        )
    print(f"- P0: {severity_counts['P0']}")
    print(f"- P1: {severity_counts['P1']}")


if __name__ == "__main__":
    main()
