import pandas as pd

from calculations_tax import summarize_holding_tax_history
from calculations_tax_review_pack import build_ffo_cash_outflow_stress, build_holding_tax_reconciliation
from tax_data_loader import build_company_tax_dataset, build_tax_history_from_company_tax_data


def test_holding_tax_ratios_do_not_raise_when_ffo_is_zero():
    peer_snapshot = pd.DataFrame(
        [
            {
                "company_name": "제로FFO리츠",
                "year": 2026,
                "investment_property": 100000,
                "official_price_total": 55000,
                "estimated_holding_tax": 600,
                "ffo_proxy": 0,
                "source_type": "sample_snapshot",
            }
        ]
    )
    profile = {
        "company_name": "제로FFO리츠",
        "stock_code": "000000",
        "dart_corp_code": "sample_zero",
        "main_asset_type": "Office",
        "main_region": "Seoul",
    }

    company_tax = build_company_tax_dataset("제로FFO리츠", peer_snapshot, profile, tax_snapshot=pd.DataFrame(columns=["company_name"]))
    tax_history = build_tax_history_from_company_tax_data(company_tax)
    annual_summary = summarize_holding_tax_history(tax_history)
    latest_kpi = pd.Series({"ffo_mn_krw": 0})

    reconciliation = build_holding_tax_reconciliation(tax_history, latest_kpi)
    ffo_stress = build_ffo_cash_outflow_stress(latest_kpi, annual_summary, 10.0, 5.0)

    assert pd.isna(company_tax["holding_tax_to_ffo"].iloc[0])
    assert pd.isna(reconciliation["보유세 / FFO"].iloc[0])
    assert ffo_stress["FFO 대비"].isna().all()


def test_holding_tax_ratios_do_not_raise_when_ffo_is_missing():
    company_tax = pd.DataFrame(
        [
            {
                "company_name": "결측FFO리츠",
                "stock_code": "000001",
                "dart_corp_code": "sample_na",
                "asset_name": "회사 전체 추정",
                "region": "회사 전체",
                "asset_type": "Office",
                "book_value": 100000,
                "official_price": 55000,
                "estimated_tax_base": 38500,
                "estimated_holding_tax": 600,
                "official_price_growth_5y": 10.0,
                "holding_tax_to_ffo": pd.NA,
                "source_type": "peer_snapshot_estimate",
                "source_note": "자산별 상세자료 부족으로 회사 전체 Snapshot 기반 추정",
                "latest_year": 2026,
            }
        ]
    )
    tax_history = build_tax_history_from_company_tax_data(company_tax)
    annual_summary = summarize_holding_tax_history(tax_history)

    reconciliation = build_holding_tax_reconciliation(tax_history, pd.Series(dtype="object"))
    ffo_stress = build_ffo_cash_outflow_stress(pd.Series(dtype="object"), annual_summary, 10.0, 5.0)

    assert pd.isna(reconciliation["보유세 / FFO"].iloc[0])
    assert ffo_stress["FFO 대비"].isna().all()
