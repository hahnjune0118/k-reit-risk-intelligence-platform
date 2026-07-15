from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from dart_financials import load_reit_master
from scripts.export_powerbi_dataset import OUTPUT_COLUMNS, main as export_powerbi_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COMPANY_FACTS = [
    "fact_reit_kpi.csv",
    "fact_tax_bridge.csv",
    "fact_tax_issue.csv",
    "fact_tax_request.csv",
    "fact_tax_reconciliation.csv",
    "fact_ffo_stress.csv",
    "fact_tax_validation.csv",
    "fact_metric_lineage.csv",
]
RATIO_COLUMNS = {
    "holding_tax_to_ffo",
    "holding_tax_to_operating_revenue",
    "official_price_to_investment_property",
    "debt_to_assets",
    "current_debt_to_total_debt",
    "interest_expense_to_ffo",
    "dividend_to_ffo",
    "holding_tax_to_ffo_percentile",
    "official_price_to_book",
    "official_price_growth_5y",
    "ffo_ratio",
}
SECRET_PATTERN = re.compile(
    r"(ECOS_API_KEY|DART_API_KEY|REALTY_PRICE_API_KEY|KRX_API_KEY|api[_ -]?key|serviceKey|access_token|token\s*[:=])",
    re.IGNORECASE,
)


@pytest.fixture(scope="module")
def powerbi_export(tmp_path_factory):
    output_dir = tmp_path_factory.mktemp("powerbi_exports")
    row_counts = export_powerbi_dataset(output_dir)
    return output_dir, row_counts


def _read_csv(output_dir: Path, filename: str) -> pd.DataFrame:
    path = output_dir / filename
    header = pd.read_csv(path, nrows=0, encoding="utf-8-sig")
    dtype = {"stock_code": str} if "stock_code" in header.columns else None
    return pd.read_csv(path, dtype=dtype, encoding="utf-8-sig")


def _master_stock_codes() -> set[str]:
    master = load_reit_master()
    return set(master["stock_code"].astype(str).str.zfill(6))


def _non_empty_values(series: pd.Series) -> pd.Series:
    values = series.dropna()
    return values[values.astype(str).str.strip().ne("")]


def test_powerbi_export_writes_required_bom_csv_files(powerbi_export):
    output_dir, row_counts = powerbi_export

    assert set(row_counts) == set(OUTPUT_COLUMNS)
    for filename, columns in OUTPUT_COLUMNS.items():
        path = output_dir / filename
        assert path.exists()
        assert path.read_bytes().startswith(b"\xef\xbb\xbf")

        df = _read_csv(output_dir, filename)
        assert list(df.columns) == columns
        assert len(df) == row_counts[filename]
        assert not df.empty


def test_powerbi_export_covers_all_master_companies(powerbi_export):
    output_dir, _ = powerbi_export
    master_codes = _master_stock_codes()

    dim_reit = _read_csv(output_dir, "dim_reit.csv")
    assert master_codes.issubset(set(dim_reit["stock_code"].astype(str).str.zfill(6)))

    for filename in REQUIRED_COMPANY_FACTS:
        df = _read_csv(output_dir, filename)
        codes = df["stock_code"].astype(str).str.zfill(6)
        assert master_codes.issubset(set(codes)), filename
        assert codes.isna().sum() == 0


def test_powerbi_export_keeps_source_policy_and_sort_contracts(powerbi_export):
    output_dir, _ = powerbi_export

    for filename in OUTPUT_COLUMNS:
        df = _read_csv(output_dir, filename)
        if "source_type" in df.columns:
            source_type = df["source_type"].astype(str).str.strip()
            assert source_type.ne("").all(), filename
            assert source_type.ne("nan").all(), filename

    issue = _read_csv(output_dir, "fact_tax_issue.csv")
    assert set(issue["risk_level"]).issubset({"높음", "주의", "데이터 부족", "정상"})
    assert issue.set_index("risk_level")["risk_sort"].to_dict()["높음"] == 1
    assert issue.set_index("risk_level")["risk_sort"].to_dict()["주의"] == 2

    requests = _read_csv(output_dir, "fact_tax_request.csv")
    assert set(requests["priority"]).issubset({"높음", "중간", "낮음"})
    priority_map = requests.set_index("priority")["priority_sort"].to_dict()
    assert priority_map["높음"] == 1
    assert priority_map["중간"] == 2

    source_policy = _read_csv(output_dir, "dim_source_policy.csv")
    assert source_policy["source_type"].is_unique
    assert source_policy["reliability_sort"].notna().all()


def test_powerbi_export_numeric_units_and_ratio_fields_are_powerbi_ready(powerbi_export):
    output_dir, _ = powerbi_export

    for filename in OUTPUT_COLUMNS:
        df = _read_csv(output_dir, filename)
        numeric_columns = [
            col
            for col in df.columns
            if col.endswith("_eok")
            or col.endswith("_sort")
            or col.endswith("_pct")
            or col in RATIO_COLUMNS
            or col in {
                "analysis_year", "financial_year", "year", "latest_year", "flow_months",
                "annualization_factor", "stage_order", "scenario_sort", "value",
            }
        ]
        for col in numeric_columns:
            values = _non_empty_values(df[col])
            if values.empty:
                continue
            assert pd.to_numeric(values, errors="coerce").notna().all(), f"{filename}:{col}"

        for col in RATIO_COLUMNS.intersection(df.columns):
            values = _non_empty_values(df[col]).astype(str)
            assert not values.str.contains("%", regex=False).any(), f"{filename}:{col}"


def test_powerbi_export_does_not_leak_secrets_or_python_literals(powerbi_export):
    output_dir, _ = powerbi_export
    python_literal_tokens = ("['", '["', "{'", '{"')

    for filename in OUTPUT_COLUMNS:
        text = (output_dir / filename).read_text(encoding="utf-8-sig")
        assert not SECRET_PATTERN.search(text), filename
        assert not any(token in text for token in python_literal_tokens), filename


def test_powerbi_export_never_reuses_sk_asset_data_for_other_companies(powerbi_export):
    output_dir, _ = powerbi_export
    asset_path = PROJECT_ROOT / "data" / "sk_reit_asset_metrics.csv"
    sk_assets = (
        pd.read_csv(asset_path)["asset_name"].dropna().astype(str).tolist()
        if asset_path.exists()
        else []
    )
    assert sk_assets

    for filename in OUTPUT_COLUMNS:
        df = _read_csv(output_dir, filename)
        if "stock_code" not in df.columns:
            continue
        non_sk = df[df["stock_code"].astype(str).str.zfill(6).ne("395400")]
        rendered = non_sk.astype(str).to_csv(index=False)
        assert "SK리츠" not in non_sk.get("company_name", pd.Series(dtype="object")).astype(str).tolist()
        for asset_name in sk_assets:
            assert asset_name not in rendered, f"{filename}:{asset_name}"


def test_powerbi_export_ground_truth_schema_and_grain(powerbi_export):
    output_dir, _ = powerbi_export
    kpi = _read_csv(output_dir, "fact_reit_kpi.csv")
    lineage = _read_csv(output_dir, "fact_metric_lineage.csv")
    requests = _read_csv(output_dir, "fact_tax_request.csv")

    assert not kpi.duplicated(["stock_code", "analysis_year", "period"]).any()
    assert {"analysis_year", "period", "reporting_period", "financial_statement_scope"}.issubset(kpi.columns)
    assert {"total_liabilities_eok", "book_nav_proxy_eok", "ffo_method", "financial_source_type", "tax_source_type"}.issubset(kpi.columns)
    assert requests.duplicated(["stock_code", "latest_year", "request_item"]).sum() == 0
    assert not lineage.duplicated(["stock_code", "analysis_year", "metric_name"]).any()
    assert {
        "metric_name", "source_type", "source_name", "source_date", "source_note",
        "statement_scope", "is_fallback", "calculation_method", "limitation",
    }.issubset(lineage.columns)


def test_powerbi_export_matches_validated_representative_values(powerbi_export):
    output_dir, _ = powerbi_export
    kpi = _read_csv(output_dir, "fact_reit_kpi.csv").set_index("company_name")

    assert kpi.loc["SK리츠", "borrowings_current_eok"] == pytest.approx(12_436.89893284)
    assert kpi.loc["롯데리츠", "borrowings_current_eok"] == pytest.approx(6_032.73619875)
    assert kpi.loc["ESR켄달스퀘어리츠", "borrowings_current_eok"] == pytest.approx(1_567.70141523)
    assert kpi.loc["SK리츠", "book_nav_proxy_eok"] == pytest.approx((5_408_832.248718 - 3_382_988.684641) / 100)
    assert pd.isna(kpi.loc["제이알글로벌리츠", "estimated_holding_tax_eok"])


def test_powerbi_bridge_exports_display_ready_money_and_percent_values(powerbi_export):
    output_dir, _ = powerbi_export
    bridge = _read_csv(output_dir, "fact_tax_bridge.csv")

    money_rows = bridge[bridge["unit"].eq("억원")]
    ratio_rows = bridge[bridge["unit"].eq("%")]
    assert not money_rows.empty
    assert not ratio_rows.empty
    assert money_rows["display_value"].astype(str).map(
        lambda value: value.endswith("억원") or value == "데이터 부족"
    ).all()
    assert ratio_rows["display_value"].astype(str).map(
        lambda value: value.endswith("%") or value == "데이터 부족"
    ).all()


def test_powerbi_page1_and_page2_base_holding_tax_values_reconcile(powerbi_export):
    output_dir, _ = powerbi_export
    kpi = _read_csv(output_dir, "fact_reit_kpi.csv").set_index("stock_code")
    stress = _read_csv(output_dir, "fact_ffo_stress.csv")
    base = stress[stress["scenario"].eq("기준 보유세")].set_index("stock_code")

    for stock_code, kpi_row in kpi.iterrows():
        if pd.isna(kpi_row["estimated_holding_tax_eok"]):
            assert pd.isna(base.loc[stock_code, "amount_eok"])
        else:
            assert base.loc[stock_code, "amount_eok"] == pytest.approx(
                kpi_row["estimated_holding_tax_eok"]
            )
