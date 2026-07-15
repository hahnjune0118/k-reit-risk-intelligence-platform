from __future__ import annotations

import re
import uuid
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = PROJECT_ROOT / "powerbi" / "exports"
MODEL_DIR = PROJECT_ROOT / "powerbi" / "K_REIT_Tax_Dashboard_v1.SemanticModel" / "definition"
TABLE_DIR = MODEL_DIR / "tables"


TABLE_FILES = {
    "dim_reit.csv": "DimREIT",
    "dim_source_policy.csv": "DimSource",
    "dim_period.csv": "DimPeriod",
    "fact_reit_kpi.csv": "FactKPI",
    "fact_tax_bridge.csv": "FactBridge",
    "fact_tax_issue.csv": "FactIssue",
    "fact_tax_request.csv": "FactRequest",
    "fact_tax_reconciliation.csv": "FactReconciliation",
    "fact_ffo_stress.csv": "FactStress",
    "fact_tax_validation.csv": "FactValidation",
    "fact_metric_lineage.csv": "FactLineage",
}


BOOLEAN_COLUMNS = {
    "annualized",
    "is_fallback",
    "fallback_used",
    "rate_reconciled",
    "period_aligned",
    "taxpayer_confirmed",
    "tax_components_complete",
    "is_current_snapshot",
}


INTEGER_COLUMNS = {
    "analysis_year",
    "financial_year",
    "year",
    "latest_year",
    "flow_months",
    "market_cap_rank",
    "reliability_sort",
    "stage_order",
    "risk_sort",
    "priority_sort",
    "scenario_sort",
}


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


DOUBLE_COLUMNS = {
    "market_cap",
    "annualization_factor",
    "value",
    "holding_tax_increase_pct",
    "ffo_stress_pct",
    *RATIO_COLUMNS,
}


def _existing_metadata(path: Path) -> tuple[str, dict[str, str]]:
    if not path.exists():
        return "", {}
    text = path.read_text(encoding="utf-8")
    table_tag_match = re.search(r"^\s*lineageTag:\s*([^\r\n]+)", text, flags=re.MULTILINE)
    table_tag = table_tag_match.group(1).strip() if table_tag_match else ""
    tags = {}
    for match in re.finditer(
        r"^\tcolumn\s+'?([^'\r\n]+?)'?\r?\n(?P<body>.*?)(?=^\tcolumn\s|^\tpartition\s)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    ):
        column = match.group(1).strip()
        tag_match = re.search(r"^\s*lineageTag:\s*([^\r\n]+)", match.group("body"), flags=re.MULTILINE)
        if tag_match:
            tags[column] = tag_match.group(1).strip()
    return table_tag, tags


def _tag(namespace: str, name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"k-reit-v14.1:{namespace}:{name}"))


def _column_type(column: str) -> str:
    if column in BOOLEAN_COLUMNS:
        return "boolean"
    if column in INTEGER_COLUMNS or column.endswith("_sort") or column.endswith("_order"):
        return "int64"
    if column in DOUBLE_COLUMNS or column.endswith("_eok") or column.endswith("_pct"):
        return "double"
    return "string"


def _format_string(column: str, data_type: str) -> str | None:
    if data_type == "int64":
        return "0"
    if data_type != "double":
        return None
    if column in RATIO_COLUMNS:
        return "0.0%"
    if column.endswith("_pct"):
        return "0.0"
    return "#,0.0"


def _summarize_by(column: str, data_type: str) -> str:
    if data_type != "double" or column in RATIO_COLUMNS or column.endswith("_pct"):
        return "none"
    return "sum"


def _m_type(column: str) -> str:
    data_type = _column_type(column)
    return {"string": "type text", "int64": "Int64.Type", "double": "type number", "boolean": "type logical"}[data_type]


def _render_table(csv_name: str, table_name: str) -> str:
    csv_path = EXPORT_DIR / csv_name
    columns = pd.read_csv(csv_path, nrows=0, encoding="utf-8-sig").columns.tolist()
    tmdl_path = TABLE_DIR / f"{table_name}.tmdl"
    existing_table_tag, existing_tags = _existing_metadata(tmdl_path)
    table_tag = existing_table_tag or f"auto-{table_name.lower()}"
    lines = [f"table {table_name}", f"\tlineageTag: {table_tag}", ""]
    for column in columns:
        data_type = _column_type(column)
        format_string = _format_string(column, data_type)
        lines.extend(
            [
                f"\tcolumn {column}",
                f"\t\tdataType: {data_type}",
            ]
        )
        if format_string:
            lines.append(f"\t\tformatString: {format_string}")
        lines.extend(
            [
                f"\t\tlineageTag: {existing_tags.get(column, _tag(table_name, column))}",
                f"\t\tsummarizeBy: {_summarize_by(column, data_type)}",
                f"\t\tsourceColumn: {column}",
                "",
                "\t\tannotation SummarizationSetBy = Automatic",
                "",
            ]
        )

    type_pairs = ", ".join(f'{{"{column}", {_m_type(column)}}}' for column in columns)
    lines.extend(
        [
            f"\tpartition {table_name} = m",
            "\t\tmode: import",
            "\t\tsource =",
            "\t\t\t\tlet",
            f'\t\t\t\t  Source = Csv.Document(File.Contents(pExportFolder & "\\{csv_name}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
            "\t\t\t\t  PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
            f'\t\t\t\t  ChangedType = Table.TransformColumnTypes(PromotedHeaders, {{{type_pairs}}}, "ko-KR")',
            "\t\t\t\tin",
            "\t\t\t\t  ChangedType",
            "",
            "\tannotation PBI_ResultType = Table",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _normalize_tmdl_tree() -> None:
    for path in MODEL_DIR.rglob("*.tmdl"):
        text = path.read_text(encoding="utf-8")
        normalized = "\n".join(line.rstrip() for line in text.splitlines()).rstrip() + "\n"
        if text != normalized:
            path.write_text(normalized, encoding="utf-8")


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    for csv_name, table_name in TABLE_FILES.items():
        (TABLE_DIR / f"{table_name}.tmdl").write_text(_render_table(csv_name, table_name), encoding="utf-8")
    (MODEL_DIR / "expressions.tmdl").write_text(
        'expression pExportFolder = "powerbi\\exports" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n',
        encoding="utf-8",
    )
    _normalize_tmdl_tree()


if __name__ == "__main__":
    main()
