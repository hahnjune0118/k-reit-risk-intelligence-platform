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
            or col in {"year", "latest_year", "stage_order", "scenario_sort", "value"}
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
