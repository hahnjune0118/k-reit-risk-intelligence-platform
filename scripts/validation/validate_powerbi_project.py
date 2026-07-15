from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
POWERBI_DIR = PROJECT_ROOT / "powerbi"
REPORT_DEFINITION = POWERBI_DIR / "K_REIT_Tax_Dashboard_v1.Report" / "definition"
MODEL_DEFINITION = POWERBI_DIR / "K_REIT_Tax_Dashboard_v1.SemanticModel" / "definition"
TABLE_DIR = MODEL_DEFINITION / "tables"
EXPORT_DIR = POWERBI_DIR / "exports"
OUTPUT_REPORT = PROJECT_ROOT / "docs" / "validation" / "v14_1_ground_truth" / "powerbi_static_validation.json"

EXPORT_TABLES = {
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

ABSOLUTE_PATH_PATTERN = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/)")
TABLE_PATTERN = re.compile(r"^table\s+(.+?)\s*$")
COLUMN_PATTERN = re.compile(r"^\tcolumn\s+(.+?)\s*$")
MEASURE_PATTERN = re.compile(r"^\tmeasure\s+(.+?)\s*=")
RELATIONSHIP_PATTERN = re.compile(r"^relationship\s+(.+?)\s*$")
DAX_COLUMN_PATTERN = re.compile(r"(?<![\w'])('?[_A-Za-z][_A-Za-z0-9 ]*'?)\[([^\]]+)\]")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def _read_table_schema(path: Path) -> tuple[str, set[str], set[str]]:
    table_name = ""
    columns: set[str] = set()
    measures: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not table_name:
            match = TABLE_PATTERN.match(line)
            if match:
                table_name = _unquote(match.group(1))
                continue
        match = COLUMN_PATTERN.match(line)
        if match:
            columns.add(_unquote(match.group(1)))
            continue
        match = MEASURE_PATTERN.match(line)
        if match:
            measures.add(_unquote(match.group(1)))
    return table_name, columns, measures


def _walk_json(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _visual_references(document: dict[str, Any]) -> set[tuple[str, str, str]]:
    references: set[tuple[str, str, str]] = set()
    for node in _walk_json(document):
        for field_type in ("Column", "Measure"):
            field = node.get(field_type)
            if not isinstance(field, dict):
                continue
            expression = field.get("Expression")
            if not isinstance(expression, dict):
                continue
            source_ref = expression.get("SourceRef")
            if not isinstance(source_ref, dict) or "Entity" not in source_ref:
                continue
            property_name = field.get("Property")
            if property_name:
                references.add((str(source_ref["Entity"]), str(property_name), field_type))
    return references


def _parse_relationships(path: Path) -> list[dict[str, str]]:
    relationships: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        match = RELATIONSHIP_PATTERN.match(raw_line)
        if match:
            if current:
                relationships.append(current)
            current = {"name": _unquote(match.group(1))}
            continue
        if current and raw_line.startswith("\t") and ":" in raw_line:
            key, value = raw_line.strip().split(":", 1)
            current[key] = value.strip()
    if current:
        relationships.append(current)
    return relationships


def _split_column_ref(value: str) -> tuple[str, str]:
    table, separator, column = value.rpartition(".")
    if not separator:
        return "", ""
    return _unquote(table), _unquote(column)


def validate() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    required_paths = [
        POWERBI_DIR / "K_REIT_Tax_Dashboard_v1.pbip",
        REPORT_DEFINITION.parent / "definition.pbir",
        MODEL_DEFINITION / "model.tmdl",
        MODEL_DEFINITION / "relationships.tmdl",
        MODEL_DEFINITION / "expressions.tmdl",
    ]
    missing_paths = [str(path.relative_to(PROJECT_ROOT)) for path in required_paths if not path.exists()]
    if missing_paths:
        errors.extend(f"필수 파일 누락: {path}" for path in missing_paths)
    checks["required_files"] = {"passed": not missing_paths, "missing": missing_paths}

    schemas: dict[str, dict[str, set[str]]] = {}
    measure_names: list[str] = []
    table_files = sorted(TABLE_DIR.glob("*.tmdl"))
    for table_file in table_files:
        table_name, columns, measures = _read_table_schema(table_file)
        if not table_name:
            errors.append(f"TMDL table 선언을 찾을 수 없음: {table_file.name}")
            continue
        if table_name in schemas:
            errors.append(f"중복 table 선언: {table_name}")
        schemas[table_name] = {"columns": columns, "measures": measures}
        measure_names.extend(measures)
    duplicate_measures = sorted(name for name, count in Counter(measure_names).items() if count > 1)
    if duplicate_measures:
        errors.extend(f"중복 Measure: {name}" for name in duplicate_measures)
    checks["semantic_objects"] = {
        "passed": bool(schemas) and not duplicate_measures,
        "table_count": len(schemas),
        "measure_count": len(measure_names),
        "duplicate_measures": duplicate_measures,
    }

    model_text = (MODEL_DEFINITION / "model.tmdl").read_text(encoding="utf-8") if (MODEL_DEFINITION / "model.tmdl").exists() else ""
    model_refs = {_unquote(match.group(1)) for match in re.finditer(r"^ref table\s+(.+?)\s*$", model_text, flags=re.MULTILINE)}
    missing_refs = sorted(set(schemas) - model_refs)
    if missing_refs:
        errors.extend(f"model.tmdl table ref 누락: {name}" for name in missing_refs)
    if "ref expression pExportFolder" not in model_text:
        errors.append("model.tmdl에서 pExportFolder expression ref가 누락됨")
    checks["model_references"] = {"passed": not missing_refs and "ref expression pExportFolder" in model_text, "missing": missing_refs}

    schema_mismatches: list[str] = []
    for csv_name, table_name in EXPORT_TABLES.items():
        csv_path = EXPORT_DIR / csv_name
        if not csv_path.exists():
            schema_mismatches.append(f"{csv_name}: CSV 누락")
            continue
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            csv_columns = next(csv.reader(handle), [])
        tmdl_columns = schemas.get(table_name, {}).get("columns", set())
        if set(csv_columns) != tmdl_columns:
            missing_in_tmdl = sorted(set(csv_columns) - tmdl_columns)
            extra_in_tmdl = sorted(tmdl_columns - set(csv_columns))
            schema_mismatches.append(
                f"{table_name}: TMDL 누락={missing_in_tmdl}, TMDL 초과={extra_in_tmdl}"
            )
    if schema_mismatches:
        errors.extend(f"CSV-TMDL 스키마 불일치: {item}" for item in schema_mismatches)
    checks["csv_tmdl_schema"] = {"passed": not schema_mismatches, "issues": schema_mismatches}

    relationships_path = MODEL_DEFINITION / "relationships.tmdl"
    relationships = _parse_relationships(relationships_path) if relationships_path.exists() else []
    relationship_names = [item.get("name", "") for item in relationships]
    duplicate_relationships = sorted(name for name, count in Counter(relationship_names).items() if count > 1)
    relationship_edges: list[tuple[str, str]] = []
    relationship_issues: list[str] = []
    for relationship in relationships:
        from_table, from_column = _split_column_ref(relationship.get("fromColumn", ""))
        to_table, to_column = _split_column_ref(relationship.get("toColumn", ""))
        if not from_table or not to_table:
            relationship_issues.append(f"{relationship.get('name')}: from/to column 형식 오류")
            continue
        if from_column not in schemas.get(from_table, {}).get("columns", set()):
            relationship_issues.append(f"{relationship.get('name')}: 존재하지 않는 from column {from_table}.{from_column}")
        if to_column not in schemas.get(to_table, {}).get("columns", set()):
            relationship_issues.append(f"{relationship.get('name')}: 존재하지 않는 to column {to_table}.{to_column}")
        if from_table.startswith("Fact") and to_table.startswith("Fact"):
            relationship_issues.append(f"{relationship.get('name')}: Fact-to-Fact 관계 금지")
        if relationship.get("crossFilteringBehavior", "").lower() == "both":
            relationship_issues.append(f"{relationship.get('name')}: 양방향 필터 금지")
        relationship_edges.append((relationship.get("fromColumn", ""), relationship.get("toColumn", "")))
    duplicate_edges = sorted(edge for edge, count in Counter(relationship_edges).items() if count > 1)
    if duplicate_relationships:
        relationship_issues.extend(f"중복 relationship 이름: {name}" for name in duplicate_relationships)
    if duplicate_edges:
        relationship_issues.extend(f"중복 relationship edge: {edge[0]} -> {edge[1]}" for edge in duplicate_edges)
    if relationship_issues:
        errors.extend(relationship_issues)
    checks["relationships"] = {
        "passed": not relationship_issues,
        "count": len(relationships),
        "issues": relationship_issues,
    }

    dax_issues: list[str] = []
    measures_path = TABLE_DIR / "_Measures.tmdl"
    if measures_path.exists():
        measure_text = measures_path.read_text(encoding="utf-8")
        for table_name, column_name in DAX_COLUMN_PATTERN.findall(measure_text):
            table_name = _unquote(table_name)
            if table_name not in schemas:
                dax_issues.append(f"Measure가 존재하지 않는 table 참조: {table_name}[{column_name}]")
            elif column_name not in schemas[table_name]["columns"]:
                dax_issues.append(f"Measure가 존재하지 않는 column 참조: {table_name}[{column_name}]")
    if dax_issues:
        errors.extend(dax_issues)
    checks["dax_column_references"] = {"passed": not dax_issues, "issues": sorted(set(dax_issues))}

    json_errors: list[str] = []
    broken_visual_refs: list[str] = []
    title_issues: list[str] = []
    raw_source_visuals: list[str] = []
    visual_count = 0
    for json_path in sorted(REPORT_DEFINITION.rglob("*.json")):
        try:
            document = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            json_errors.append(f"{json_path.relative_to(PROJECT_ROOT)}: {exc}")
            continue
        if json_path.name != "visual.json":
            continue
        visual_count += 1
        visual = document.get("visual", {})
        title_objects = visual.get("visualContainerObjects", {}).get("title", [])
        if not title_objects:
            title_issues.append(f"{json_path.relative_to(PROJECT_ROOT)}: title 설정 누락")
        elif visual.get("visualType") in {"tableEx", "clusteredBarChart", "scatterChart"}:
            properties = title_objects[0].get("properties", {})
            if properties.get("show", {}).get("expr", {}).get("Literal", {}).get("Value") != "true":
                title_issues.append(f"{json_path.relative_to(PROJECT_ROOT)}: 분석 시각화 제목 비활성")
            if "text" not in properties:
                title_issues.append(f"{json_path.relative_to(PROJECT_ROOT)}: 명시적 제목 문구 누락")
        for table_name, property_name, field_type in _visual_references(document):
            if table_name == "FactKPI" and property_name == "source_type":
                raw_source_visuals.append(str(json_path.relative_to(PROJECT_ROOT)))
            if table_name not in schemas:
                broken_visual_refs.append(
                    f"{json_path.relative_to(PROJECT_ROOT)}: 존재하지 않는 table {table_name}"
                )
                continue
            collection = "measures" if field_type == "Measure" else "columns"
            if property_name not in schemas[table_name][collection]:
                broken_visual_refs.append(
                    f"{json_path.relative_to(PROJECT_ROOT)}: 존재하지 않는 {field_type} {table_name}.{property_name}"
                )
    if json_errors:
        errors.extend(f"PBIR JSON 오류: {item}" for item in json_errors)
    if broken_visual_refs:
        errors.extend(f"PBIR 필드 참조 오류: {item}" for item in broken_visual_refs)
    if title_issues:
        errors.extend(f"PBIR 제목 설정 오류: {item}" for item in title_issues)
    if raw_source_visuals:
        errors.extend(f"PBIR 원시 source_type 노출: {item}" for item in sorted(set(raw_source_visuals)))
    checks["report_definition"] = {
        "passed": not json_errors and not broken_visual_refs and not title_issues and not raw_source_visuals,
        "visual_count": visual_count,
        "json_errors": json_errors,
        "broken_references": broken_visual_refs,
        "title_issues": title_issues,
        "raw_source_visuals": sorted(set(raw_source_visuals)),
    }

    text_files = [
        *MODEL_DEFINITION.rglob("*.tmdl"),
        *REPORT_DEFINITION.rglob("*.json"),
        POWERBI_DIR / "K_REIT_Tax_Dashboard_v1.pbip",
    ]
    absolute_path_hits: list[str] = []
    for path in text_files:
        if path.exists() and ABSOLUTE_PATH_PATTERN.search(path.read_text(encoding="utf-8")):
            absolute_path_hits.append(str(path.relative_to(PROJECT_ROOT)))
    if absolute_path_hits:
        errors.extend(f"절대 경로 발견: {path}" for path in absolute_path_hits)
    checks["portable_paths"] = {"passed": not absolute_path_hits, "hits": absolute_path_hits}

    required_slicers = {
        "page1_company": REPORT_DEFINITION / "pages" / "4d3c0a10fecce17f65e3" / "visuals" / "4e96e31b2d192b4ac837" / "visual.json",
        "page1_period": REPORT_DEFINITION / "pages" / "4d3c0a10fecce17f65e3" / "visuals" / "157bf0fae63c68557422" / "visual.json",
        "page2_company": REPORT_DEFINITION / "pages" / "taxIssueSensitivity" / "visuals" / "p2_company_slicer" / "visual.json",
        "page2_period": REPORT_DEFINITION / "pages" / "taxIssueSensitivity" / "visuals" / "p2_period_slicer" / "visual.json",
        "page3_company": REPORT_DEFINITION / "pages" / "requestReviewWorkflow" / "visuals" / "p3_company_slicer" / "visual.json",
        "page3_period": REPORT_DEFINITION / "pages" / "requestReviewWorkflow" / "visuals" / "p3_period_slicer" / "visual.json",
    }
    missing_slicers = [name for name, path in required_slicers.items() if not path.exists()]
    sync_issues: list[str] = []
    for name, path in required_slicers.items():
        if not path.exists():
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        expected_group = "K_REIT_Company" if name.endswith("company") else "K_REIT_AnalysisYear"
        sync_group = document.get("visual", {}).get("syncGroup", {})
        if sync_group.get("groupName") != expected_group:
            sync_issues.append(f"{name}: sync group이 {expected_group}이 아님")
        if sync_group.get("filterChanges") is not True:
            sync_issues.append(f"{name}: filterChanges가 true가 아님")
    if missing_slicers:
        errors.extend(f"필수 Slicer 누락: {name}" for name in missing_slicers)
    if sync_issues:
        errors.extend(sync_issues)
    checks["company_period_slicers"] = {
        "passed": not missing_slicers and not sync_issues,
        "missing": missing_slicers,
        "sync_issues": sync_issues,
    }

    return {
        "status": "passed" if not errors else "failed",
        "validated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def main() -> int:
    result = validate()
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
