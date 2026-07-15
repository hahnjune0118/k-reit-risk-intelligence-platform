from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


PEER_FIELDS = [
    "company_name",
    "stock_code",
    "dart_corp_code",
    "year",
    "period",
    "period_start",
    "period_end",
    "reporting_period",
    "flow_months",
    "annualized",
    "annualization_factor",
    "financial_statement_scope",
    "total_assets",
    "total_liabilities",
    "current_assets",
    "cash_and_cash_equivalents",
    "short_term_financial_assets",
    "short_term_financial_assets_unrestricted",
    "investment_property",
    "current_liabilities",
    "borrowings_total",
    "borrowings_current",
    "short_term_borrowings",
    "current_portion_long_term_debt",
    "long_term_borrowings",
    "bonds",
    "lease_liabilities",
    "provisions",
    "deferred_tax_liabilities",
    "interest_expense",
    "operating_revenue",
    "operating_income",
    "net_income",
    "operating_cash_flow",
    "ffo_proxy",
    "dividends",
    "reported_interest_expense",
    "reported_operating_revenue",
    "reported_operating_income",
    "reported_net_income",
    "reported_operating_cash_flow",
    "reported_dividends",
    "estimated_holding_tax",
    "official_price_total",
    "official_price_growth_5y",
    "source_type",
    "tax_source_type",
    "source_name",
    "source_date",
    "source_note",
    "ffo_method",
    "ffo_limitation",
    "interest_bearing_debt_method",
    "interest_bearing_debt_completeness",
    "last_updated",
]


MASTER_FIELDS = [
    "company_name",
    "stock_code",
    "dart_corp_code",
    "market_cap_rank",
    "market_cap",
    "market",
    "reit_type",
    "main_asset_type",
    "main_region",
    "note",
]


TAX_FIELDS = [
    "company_name",
    "stock_code",
    "dart_corp_code",
    "asset_name",
    "region",
    "asset_type",
    "book_value",
    "official_price",
    "estimated_tax_base",
    "estimated_holding_tax",
    "official_price_growth_5y",
    "holding_tax_to_ffo",
    "calculation_model",
    "fair_market_value_ratio",
    "effective_holding_tax_rate",
    "formula_version",
    "tax_scope",
    "tax_component_status",
    "legal_owner_status",
    "taxpayer_status",
    "tax_pass_through_status",
    "pnu",
    "source_type",
    "source_name",
    "source_date",
    "source_note",
    "latest_year",
]


def _write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fields} for row in rows])


def _annualized_financial_row(
    *,
    company_name: str,
    stock_code: str,
    dart_corp_code: str,
    year: int,
    period: str,
    period_start: str,
    period_end: str,
    flow_months: int,
    scope: str,
    total_assets: float,
    total_liabilities: float,
    current_assets: float,
    cash: float,
    short_financial_assets: float | str,
    investment_property: float,
    current_liabilities: float,
    debt_total: float,
    debt_current: float,
    short_borrowings: float | str,
    current_long_debt: float | str,
    long_borrowings: float | str,
    bonds: float | str,
    interest_expense: float,
    revenue: float,
    operating_income: float,
    net_income: float,
    operating_cash_flow: float,
    dividends: float,
    estimated_tax: float,
    official_price: float,
    source_name: str,
    debt_method: str,
) -> dict:
    factor = 12 / flow_months
    return {
        "company_name": company_name,
        "stock_code": stock_code,
        "dart_corp_code": dart_corp_code,
        "year": year,
        "period": period,
        "period_start": period_start,
        "period_end": period_end,
        "reporting_period": f"{period_start}~{period_end}",
        "flow_months": flow_months,
        "annualized": True,
        "annualization_factor": factor,
        "financial_statement_scope": scope,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "current_assets": current_assets,
        "cash_and_cash_equivalents": cash,
        "short_term_financial_assets": short_financial_assets,
        "short_term_financial_assets_unrestricted": False,
        "investment_property": investment_property,
        "current_liabilities": current_liabilities,
        "borrowings_total": debt_total,
        "borrowings_current": debt_current,
        "short_term_borrowings": short_borrowings,
        "current_portion_long_term_debt": current_long_debt,
        "long_term_borrowings": long_borrowings,
        "bonds": bonds,
        "interest_expense": interest_expense * factor,
        "operating_revenue": revenue * factor,
        "operating_income": operating_income * factor,
        "net_income": net_income * factor,
        "operating_cash_flow": operating_cash_flow * factor,
        "ffo_proxy": operating_cash_flow * factor,
        "dividends": dividends * factor,
        "reported_interest_expense": interest_expense,
        "reported_operating_revenue": revenue,
        "reported_operating_income": operating_income,
        "reported_net_income": net_income,
        "reported_operating_cash_flow": operating_cash_flow,
        "reported_dividends": dividends,
        "estimated_holding_tax": estimated_tax,
        "official_price_total": official_price,
        "source_type": "official_disclosure",
        "tax_source_type": "peer_snapshot_estimate",
        "source_name": source_name,
        "source_date": period_end,
        "source_note": (
            f"재무상태표는 {period_end} {scope} 기준이며 손익·현금흐름은 "
            f"{flow_months}개월 공시값을 {factor:g}배 연환산했습니다. "
            "보유세와 공시가격은 회사 전체 Snapshot 기반 추정입니다."
        ),
        "ffo_method": "annualized_operating_cash_flow_proxy",
        "ffo_limitation": "공식 FFO가 아니며 공시 영업활동현금흐름의 단순 연환산 proxy",
        "interest_bearing_debt_method": debt_method,
        "interest_bearing_debt_completeness": "official_total_reconciled",
        "last_updated": "2026-07-15",
    }


def _sample_financial_row(
    company_name: str,
    stock_code: str,
    total_assets: float,
    investment_property: float,
    borrowings_total: float,
    borrowings_current: float,
    interest_expense: float,
    revenue: float,
    operating_income: float,
    net_income: float,
    operating_cash_flow: float,
    dividends: float,
    estimated_tax: float | str,
    official_price: float | str,
    note: str = "회사 전체 예시 Snapshot입니다.",
) -> dict:
    return {
        "company_name": company_name,
        "stock_code": stock_code,
        "year": 2026,
        "period": "2026Q1",
        "reporting_period": "2026 Sample Snapshot",
        "annualized": True,
        "annualization_factor": 1,
        "financial_statement_scope": "Sample estimate",
        "total_assets": total_assets,
        "investment_property": investment_property,
        "borrowings_total": borrowings_total,
        "borrowings_current": borrowings_current,
        "interest_expense": interest_expense,
        "operating_revenue": revenue,
        "operating_income": operating_income,
        "net_income": net_income,
        "operating_cash_flow": operating_cash_flow,
        "ffo_proxy": operating_cash_flow,
        "dividends": dividends,
        "estimated_holding_tax": estimated_tax,
        "official_price_total": official_price,
        "source_type": "sample_estimate",
        "tax_source_type": "data_insufficient" if estimated_tax == "" else "peer_snapshot_estimate",
        "source_name": "Bundled peer sample",
        "source_date": "2026-07-02",
        "source_note": note,
        "ffo_method": "operating_cash_flow_proxy",
        "ffo_limitation": "공식 FFO가 아닌 예시 영업활동현금흐름 proxy",
        "interest_bearing_debt_method": "Sample borrowings_total",
        "interest_bearing_debt_completeness": "unverified_sample",
        "last_updated": "2026-07-15",
    }


def build_peer_rows() -> list[dict]:
    rows = [
        _annualized_financial_row(
            company_name="SK리츠",
            stock_code="395400",
            dart_corp_code="01535150",
            year=2026,
            period="2026Q1",
            period_start="2026-01-01",
            period_end="2026-03-31",
            flow_months=3,
            scope="연결재무제표(CFS)",
            total_assets=5_408_832.248718,
            total_liabilities=3_382_988.684641,
            current_assets=168_971.880637,
            cash=73_378.212337,
            short_financial_assets=11_446.465160,
            investment_property=5_232_672.201430,
            current_liabilities=1_318_000.437012,
            debt_total=3_103_854.820967,
            debt_current=1_243_689.893284,
            short_borrowings=669_076.449351,
            current_long_debt=574_613.443933,
            long_borrowings=1_451_238.083598,
            bonds=408_926.844085,
            interest_expense=33_926.344403,
            revenue=63_369.239197,
            operating_income=53_853.739755,
            net_income=20_539.220221,
            operating_cash_flow=41_169.870700,
            dividends=20_986.921349,
            estimated_tax=29_500,
            official_price=2_877_970,
            source_name="DART 2026Q1 보고서 (rcp_no 20260610000569)",
            debt_method="공식 XBRL 유동·비유동 이자부 차입계정 합계",
        ),
        _annualized_financial_row(
            company_name="롯데리츠",
            stock_code="330590",
            dart_corp_code="01363818",
            year=2025,
            period="2025H2",
            period_start="2025-07-01",
            period_end="2025-12-31",
            flow_months=6,
            scope="별도재무제표(OFS)",
            total_assets=2_594_407.041849,
            total_liabilities=1_454_908.461475,
            current_assets=58_448.614109,
            cash=12_577.978163,
            short_financial_assets="",
            investment_property=2_527_222.594740,
            current_liabilities=621_336.979126,
            debt_total=1_307_019.777689,
            debt_current=603_273.619875,
            short_borrowings="",
            current_long_debt=603_273.619875,
            long_borrowings=703_746.157814,
            bonds=525_000,
            interest_expense=27_353.183265,
            revenue=70_879.702538,
            operating_income=46_254.900872,
            net_income=19_627.460882,
            operating_cash_flow=64_017.736779,
            dividends=33_809.359428,
            estimated_tax=15_800,
            official_price=1_320_000,
            source_name="DART 사업보고서 (rcp_no 20260310002810)",
            debt_method="공식 XBRL 유동·비유동 이자부 차입계정 합계",
        ),
        _annualized_financial_row(
            company_name="ESR켄달스퀘어리츠",
            stock_code="365550",
            dart_corp_code="01437186",
            year=2025,
            period="2025H2",
            period_start="2025-06-01",
            period_end="2025-11-30",
            flow_months=6,
            scope="연결재무제표(CFS)",
            total_assets=2_835_773.540304,
            total_liabilities=1_670_571.944339,
            current_assets=206_705.351492,
            cash=171_445.697130,
            short_financial_assets=4_258.324920,
            investment_property=2_433_793.981472,
            current_liabilities=186_471.185667,
            debt_total=1_586_961.428286,
            debt_current=156_770.141523,
            short_borrowings=26_499.399652,
            current_long_debt=130_270.741871,
            long_borrowings=1_430_191.286763,
            bonds="",
            interest_expense=27_995.840506,
            revenue=59_557.601618,
            operating_income=25_859.163408,
            net_income=-3_436.388048,
            operating_cash_flow=8_836.054309,
            dividends=29_193.193000,
            estimated_tax=18_600,
            official_price=1_487_000,
            source_name="DART 사업보고서 (rcp_no 20260213002140)",
            debt_method="공식 XBRL 단기차입금·유동성장기차입금·장기차입금 합계",
        ),
        _sample_financial_row(
            "제이알글로벌리츠",
            "348950",
            2_050_000,
            1_968_000,
            1_260_000,
            578_000,
            53_200,
            110_500,
            78_200,
            31_800,
            38_900,
            50_100,
            "",
            "",
            "해외자산 중심 회사의 국내 보유세 입력은 데이터 부족으로 처리합니다.",
        ),
        _sample_financial_row("신한알파리츠", "293940", 1_840_000, 1_736_000, 875_000, 102_000, 31_200, 101_400, 82_900, 35_600, 46_200, 41_400, 12_100, 914_000),
        _sample_financial_row("코람코라이프인프라리츠", "357120", 1_630_000, 1_510_000, 820_000, 154_000, 29_600, 92_000, 74_800, 29_100, 35_200, 36_100, 14_200, 855_000),
        _sample_financial_row("이지스밸류리츠", "334890", 980_000, 910_000, 546_000, 210_000, 20_500, 59_400, 45_600, 16_800, 20_200, 23_200, 8_300, 514_000),
        _sample_financial_row("NH올원리츠", "400760", 1_120_000, 1_045_000, 585_000, 89_000, 18_800, 61_200, 49_300, 19_600, 24_100, 23_900, 9_100, 576_000),
    ]
    growth_by_company = {
        "SK리츠": 12.0,
        "롯데리츠": 10.8,
        "ESR켄달스퀘어리츠": 14.5,
        "제이알글로벌리츠": "",
        "신한알파리츠": 11.2,
        "코람코라이프인프라리츠": 9.6,
        "NH올원리츠": 7.8,
        "이지스밸류리츠": 10.1,
    }
    for row in rows:
        row["official_price_growth_5y"] = growth_by_company[row["company_name"]]
    return rows


def build_master_rows() -> list[dict]:
    rows = [
        ("SK리츠", "395400", "01535150", 1, 980_000, "Office", "Seoul", "DART corp code 검증 완료; 시가총액 순위는 예시 Snapshot"),
        ("ESR켄달스퀘어리츠", "365550", "01437186", 2, 950_000, "Logistics", "Greater Seoul", "DART corp code 검증 완료; 시가총액 순위는 예시 Snapshot"),
        ("롯데리츠", "330590", "01363818", 3, 780_000, "Retail", "Nationwide", "DART corp code 검증 완료; 시가총액 순위는 예시 Snapshot"),
        ("제이알글로벌리츠", "348950", "", 4, 640_000, "Office", "Overseas", "DART corp code 미검증; 시가총액 순위는 예시 Snapshot"),
        ("신한알파리츠", "293940", "", 5, 590_000, "Office", "Seoul", "DART corp code 미검증; 시가총액 순위는 예시 Snapshot"),
        ("코람코라이프인프라리츠", "357120", "", 6, 470_000, "Retail / Infra", "Nationwide", "DART corp code 미검증; 시가총액 순위는 예시 Snapshot"),
        ("NH올원리츠", "400760", "", 7, 320_000, "Diversified", "Nationwide", "DART corp code 미검증; 시가총액 순위는 예시 Snapshot"),
        ("이지스밸류리츠", "334890", "", 8, 300_000, "Office", "Seoul", "DART corp code 미검증; 시가총액 순위는 예시 Snapshot"),
    ]
    return [
        {
            "company_name": company,
            "stock_code": stock_code,
            "dart_corp_code": corp_code,
            "market_cap_rank": rank,
            "market_cap": market_cap,
            "market": "KOSPI",
            "reit_type": "위탁관리리츠",
            "main_asset_type": asset_type,
            "main_region": region,
            "note": note,
        }
        for company, stock_code, corp_code, rank, market_cap, asset_type, region, note in rows
    ]


def build_tax_rows(peer_rows: list[dict], master_rows: list[dict]) -> list[dict]:
    peer_by_company = {row["company_name"]: row for row in peer_rows}
    master_by_company = {row["company_name"]: row for row in master_rows}
    base = [
        ("SK리츠", "Seoul", "Office", 5_232_672, 2_877_970, 29_500, 12.0, "공개 검증자료에 자산별 PNU·고지서가 없어 회사 전체 Snapshot 기반 effective-rate estimate로 사용"),
        ("ESR켄달스퀘어리츠", "Greater Seoul", "Logistics", 2_433_793.981472, 1_487_000, 18_600, 14.5, "자산별 PNU·고지서가 없어 회사 전체 Snapshot 기반 effective-rate estimate로 사용"),
        ("롯데리츠", "Nationwide", "Retail", 2_527_222.594740, 1_320_000, 15_800, 10.8, "자산별 PNU·고지서 및 임대차별 세부담 귀속 확인 전 회사 전체 Snapshot 기반 estimate"),
        ("제이알글로벌리츠", "Overseas", "Office", 1_968_000, "", "", "", "해외자산 중심 회사이므로 국내 공시가격·보유세 산식을 적용하지 않고 데이터 부족으로 처리"),
        ("신한알파리츠", "Seoul", "Office", 1_736_000, 914_000, 12_100, 11.2, "회사 전체 예시 Snapshot 기반 effective-rate estimate"),
        ("코람코라이프인프라리츠", "Nationwide", "Retail / Infra", 1_510_000, 855_000, 14_200, 9.6, "회사 전체 예시 Snapshot 기반 effective-rate estimate"),
        ("NH올원리츠", "Nationwide", "Diversified", 1_045_000, 576_000, 9_100, 7.8, "회사 전체 예시 Snapshot 기반 effective-rate estimate"),
        ("이지스밸류리츠", "Seoul", "Office", 910_000, 514_000, 8_300, 10.1, "회사 전체 예시 Snapshot 기반 effective-rate estimate"),
    ]
    rows = []
    for company, region, asset_type, book_value, official_price, tax, growth, note in base:
        peer = peer_by_company[company]
        master = master_by_company[company]
        ffo = peer.get("ffo_proxy", "")
        has_tax = tax != "" and official_price != ""
        tax_base = float(official_price) * 0.70 if has_tax else ""
        effective_rate = float(tax) / tax_base if has_tax and tax_base else ""
        source_type = "data_insufficient" if not has_tax else "peer_snapshot_estimate"
        rows.append(
            {
                "company_name": company,
                "stock_code": master["stock_code"],
                "dart_corp_code": master["dart_corp_code"],
                "asset_name": "회사 전체 추정",
                "region": region,
                "asset_type": asset_type,
                "book_value": book_value,
                "official_price": official_price,
                "estimated_tax_base": tax_base,
                "estimated_holding_tax": tax,
                "official_price_growth_5y": growth,
                "holding_tax_to_ffo": float(tax) / float(ffo) if has_tax and ffo else "",
                "calculation_model": "effective-rate estimate" if has_tax else "data_insufficient",
                "fair_market_value_ratio": 0.70 if has_tax else "",
                "effective_holding_tax_rate": effective_rate,
                "formula_version": "holding_tax_screening_v14_1",
                "tax_scope": "company_level_screening_total" if has_tax else "data_insufficient",
                "tax_component_status": "data_insufficient",
                "legal_owner_status": "data_insufficient",
                "taxpayer_status": "data_insufficient",
                "tax_pass_through_status": "disclosure_indicates_some_tenant_pass_through" if company == "롯데리츠" else "data_insufficient",
                "pnu": "",
                "source_type": source_type,
                "source_name": "Bundled company-level tax snapshot",
                "source_date": "2026-07-02",
                "source_note": note,
                "latest_year": 2026,
            }
        )
    return rows


def main() -> None:
    peer_rows = build_peer_rows()
    master_rows = build_master_rows()
    tax_rows = build_tax_rows(peer_rows, master_rows)
    _write_csv(DATA_DIR / "reit_peer_snapshot.csv", PEER_FIELDS, peer_rows)
    _write_csv(DATA_DIR / "reit_master.csv", MASTER_FIELDS, master_rows)
    _write_csv(DATA_DIR / "reit_tax_snapshot.csv", TAX_FIELDS, tax_rows)


if __name__ == "__main__":
    main()
