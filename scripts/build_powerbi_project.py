from __future__ import annotations

import json
import runpy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POWERBI_DIR = PROJECT_ROOT / "powerbi"
SEMANTIC_DIR = POWERBI_DIR / "K_REIT_Tax_Dashboard_v1.SemanticModel" / "definition"
TABLE_DIR = SEMANTIC_DIR / "tables"
REPORT_PAGES_DIR = POWERBI_DIR / "K_REIT_Tax_Dashboard_v1.Report" / "definition" / "pages"


def measure_block(name: str, expression: str, folder: str, fmt: str | None = None, lineage: str | None = None) -> str:
    lines = [f"\tmeasure '{name}' =", ""]
    lines.extend("\t\t\t" + line for line in expression.strip("\n").splitlines())
    if fmt:
        lines.append(f"\t\tformatString: {fmt}")
    lines.append(f"\t\tdisplayFolder: {folder}")
    if lineage:
        lines.append(f"\t\tlineageTag: {lineage}")
    lines.append("")
    return "\n".join(lines)


def write_measures() -> None:
    existing_lineages = {
        "선택 회사": "c91b12d5-0908-4809-89a8-4d1339630bb3",
        "선택 기준연도 표시": "922902fd-7601-4da5-8dc1-a20dc08abd08",
        "선택 기준연도": "4a87bd52-6400-4170-b3a2-a9bf8b2d4926",
        "페이지 제목": "d95c0410-8e02-4627-9ab0-3cd6b9c06811",
        "분석 Source Type": "4be71f5f-2398-4ecc-ab80-da241d055209",
        "Source Note": "635d8745-3480-4d8d-b84e-fe634efde747",
    }
    measures = [
        ("선택 회사", 'SELECTEDVALUE(DimREIT[company_name], "전체 REITs")', "01 Selection", None),
        ("선택 기준연도", "SELECTEDVALUE(DimPeriod[analysis_year], MAX(DimPeriod[analysis_year]))", "01 Selection", "0"),
        ("선택 기준연도 표시", 'FORMAT([선택 기준연도], "0")', "01 Selection", None),
        ("페이지 제목", '[선택 회사] & " | " & [선택 기준연도 표시] & " Tax Executive Summary"', "01 Selection", None),
        ("분석 Source Type", 'SELECTEDVALUE(FactKPI[source_type], "복수 또는 확인 필요")', "02 Source Lineage", None),
        (
            "분석 Source Type 표시",
            """SWITCH(
    [분석 Source Type],
    "official_api", "공식 API",
    "official_disclosure", "공식 공시자료",
    "api_snapshot", "API/Snapshot 자료",
    "peer_snapshot", "Peer Snapshot",
    "peer_snapshot_estimate", "Peer Snapshot estimate",
    "sample_estimate", "Sample estimate",
    "data_insufficient", "데이터 부족",
    [분석 Source Type]
)""",
            "02 Source Lineage",
            None,
        ),
        ("Source Note", 'SELECTEDVALUE(FactKPI[source_note], "세부 데이터 출처를 확인하세요.")', "02 Source Lineage", None),
        ("재무제표 범위", 'SELECTEDVALUE(FactKPI[financial_statement_scope], "Snapshot 또는 확인 필요")', "02 Source Lineage", None),
        ("Fallback 상태", 'IF(SELECTEDVALUE(FactKPI[is_fallback], TRUE()), "Snapshot/Fallback 사용", "공식 API 또는 직접 원천")', "02 Source Lineage", None),
        ("Source Name", 'SELECTEDVALUE(FactKPI[source_name], "")', "02 Source Lineage", None),
        ("Source Date", 'SELECTEDVALUE(FactKPI[source_date], "")', "02 Source Lineage", None),
        ("Calculation Method", 'SELECTEDVALUE(FactKPI[calculation_method], "계산 경로 확인 필요")', "02 Source Lineage", None),
        ("총자산(억원)", "SUM(FactKPI[total_assets_eok])", "03 Financial Position", "#,0.0"),
        ("총부채(억원)", "SUM(FactKPI[total_liabilities_eok])", "03 Financial Position", "#,0.0"),
        ("이자부 차입부채(억원)", "SUM(FactKPI[interest_bearing_debt_eok])", "03 Financial Position", "#,0.0"),
        ("충당부채(억원)", "SUM(FactKPI[provisions_eok])", "03 Financial Position", "#,0.0"),
        ("현금및현금성자산(억원)", "SUM(FactKPI[cash_and_cash_equivalents_eok])", "03 Financial Position", "#,0.0"),
        (
            "순차입금(억원)",
            "IF(ISBLANK([이자부 차입부채(억원)]) || ISBLANK([현금및현금성자산(억원)]), BLANK(), [이자부 차입부채(억원)] - [현금및현금성자산(억원)])",
            "03 Financial Position",
            "#,0.0",
        ),
        ("투자부동산(억원)", "SUM(FactKPI[investment_property_eok])", "03 Financial Position", "#,0.0"),
        ("Book NAV proxy(억원)", "SUM(FactKPI[book_nav_proxy_eok])", "03 Financial Position", "#,0.0"),
        ("FFO proxy(억원)", "SUM(FactKPI[ffo_proxy_eok])", "04 Cash Flow & Tax", "#,0.0"),
        ("영업활동현금흐름(억원)", "SUM(FactKPI[operating_cash_flow_eok])", "04 Cash Flow & Tax", "#,0.0"),
        ("영업수익(억원)", "SUM(FactKPI[operating_revenue_eok])", "04 Cash Flow & Tax", "#,0.0"),
        ("영업이익(억원)", "SUM(FactKPI[operating_income_eok])", "04 Cash Flow & Tax", "#,0.0"),
        ("이자비용(억원)", "SUM(FactKPI[interest_expense_eok])", "04 Cash Flow & Tax", "#,0.0"),
        ("추정 보유세(억원)", "SUM(FactKPI[estimated_holding_tax_eok])", "04 Cash Flow & Tax", "#,0.0"),
        ("보유세 / FFO proxy", "DIVIDE([추정 보유세(억원)], [FFO proxy(억원)])", "05 Ratios", "0.0%"),
        ("보유세 / 영업수익", "DIVIDE([추정 보유세(억원)], [영업수익(억원)])", "05 Ratios", "0.0%"),
        ("총자산 기준 차입비율", "DIVIDE([이자부 차입부채(억원)], [총자산(억원)])", "05 Ratios", "0.0%"),
        ("투자부동산 기준 Property LTV", "DIVIDE([이자부 차입부채(억원)], [투자부동산(억원)])", "05 Ratios", "0.0%"),
        ("FFO 이자감당배율 proxy", "DIVIDE([FFO proxy(억원)], [이자비용(억원)])", "05 Ratios", "0.00배"),
        ("영업현금흐름 이자감당배율 proxy", "DIVIDE([영업활동현금흐름(억원)], [이자비용(억원)])", "05 Ratios", "0.00배"),
        ("공시가격 / 투자부동산", "DIVIDE(SUM(FactKPI[official_price_total_eok]), [투자부동산(억원)])", "05 Ratios", "0.0%"),
        ("배당 / FFO proxy", "DIVIDE(SUM(FactKPI[dividends_eok]), [FFO proxy(억원)])", "05 Ratios", "0.0%"),
        (
            "Peer 보유세 / FFO 중앙값",
            "CALCULATE(MEDIANX(VALUES(DimREIT[company_name]), [보유세 / FFO proxy]), REMOVEFILTERS(DimREIT))",
            "05 Ratios",
            "0.0%",
        ),
        ("Peer 대비 차이", "[보유세 / FFO proxy] - [Peer 보유세 / FFO 중앙값]", "05 Ratios", "0.0%"),
        ("고위험 이슈 수", 'CALCULATE(COUNTROWS(FactIssue), FactIssue[risk_level] = "높음")', "06 Issues & Validation", "0"),
        ("주의 이슈 수", 'CALCULATE(COUNTROWS(FactIssue), FactIssue[risk_level] = "주의")', "06 Issues & Validation", "0"),
        ("요청자료 수", "DISTINCTCOUNT(FactRequest[request_item])", "06 Issues & Validation", "0"),
        ("검토 필요 항목 수", "[고위험 이슈 수] + [주의 이슈 수]", "06 Issues & Validation", "0"),
        ("Validation 이슈 수", 'CALCULATE(COUNTROWS(FactValidation), FactValidation[validation_status] <> "정상")', "06 Issues & Validation", "0"),
        ("Validation 종합 상태", 'IF([Validation 이슈 수] > 0, "검토 필요", "정상")', "06 Issues & Validation", None),
        ("pHoldingTaxIncrease Value", "SELECTEDVALUE(pHoldingTaxIncrease[pHoldingTaxIncrease], 10)", "07 Stress Scenario", "0"),
        ("pFFODecline Value", "SELECTEDVALUE(pFFODecline[pFFODecline], 4)", "07 Stress Scenario", "0"),
        ("스트레스 보유세(억원)", "[추정 보유세(억원)] * (1 + DIVIDE([pHoldingTaxIncrease Value], 100))", "07 Stress Scenario", "#,0.0"),
        ("스트레스 FFO proxy(억원)", "[FFO proxy(억원)] * (1 - DIVIDE([pFFODecline Value], 100))", "07 Stress Scenario", "#,0.0"),
        ("스트레스 보유세 / FFO proxy", "DIVIDE([스트레스 보유세(억원)], [스트레스 FFO proxy(억원)])", "07 Stress Scenario", "0.0%"),
        ("추가 현금유출(억원)", "[스트레스 보유세(억원)] - [추정 보유세(억원)]", "07 Stress Scenario", "#,0.0"),
        (
            "스트레스 위험수준",
            'SWITCH(TRUE(), ISBLANK([스트레스 보유세 / FFO proxy]), "데이터 부족", [스트레스 보유세 / FFO proxy] >= 0.35, "높음", [스트레스 보유세 / FFO proxy] >= 0.25, "주의", "정상")',
            "07 Stress Scenario",
            None,
        ),
        ("Detailed Tax Review Pack URL", '"https://hahnjune0118-k-reit-risk-intelligence-platform-app.streamlit.app/"', "06 Issues & Validation", None),
        ("Tax Review Pack 열기", '"Streamlit Tax Review Pack 열기"', "06 Issues & Validation", None),
    ]

    lines = ["table _Measures", "\tisHidden", "\tlineageTag: e42962c0-dc6e-4198-ab60-fe4a06f30995", ""]
    for name, expr, folder, fmt in measures:
        lines.append(measure_block(name, expr, folder, fmt, existing_lineages.get(name)))
    lines.extend(
        [
            "\tcolumn 'Measure Holder'",
            "\t\tisHidden",
            "\t\tlineageTag: 138f0677-84d3-46c4-abdd-efb0bb783e7a",
            "\t\tsummarizeBy: none",
            "\t\tisNameInferred",
            "\t\tsourceColumn: [Measure Holder]",
            "",
            "\t\tannotation SummarizationSetBy = Automatic",
            "",
            "\tpartition _Measures = calculated",
            "\t\tmode: import",
            "\t\tsource =",
            '\t\t\t\tDATATABLE("Measure Holder", STRING, {{"Measures"}})',
            "",
            "\tannotation PBI_Id = 08ecacedd89e410cbf0f9c682ebca5f7",
            "",
        ]
    )
    (TABLE_DIR / "_Measures.tmdl").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def measure_field(name: str) -> dict:
    return {
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Measures"}}, "Property": name}},
        "queryRef": f"_Measures.{name}",
        "nativeQueryRef": name,
    }


def column_field(table: str, col: str) -> dict:
    return {
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": col}},
        "queryRef": f"{table}.{col}",
        "nativeQueryRef": col,
    }


def agg_field(table: str, col: str, label: str | None = None) -> dict:
    return {
        "field": {
            "Aggregation": {
                "Expression": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": col}},
                "Function": 0,
            }
        },
        "queryRef": f"Sum({table}.{col})",
        "nativeQueryRef": label or col,
    }


def visual(name: str, visual_type: str, x: float, y: float, w: float, h: float, z: int, query_state: dict, objects: dict | None = None) -> dict:
    item = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z},
        "visual": {"visualType": visual_type, "query": {"queryState": query_state}, "drillFilterOtherVisuals": True},
    }
    if objects:
        item["visual"]["objects"] = objects
    return item


def card(name: str, measure: str, x: float, y: float, w: float = 170, h: float = 90, z: int = 1000) -> dict:
    return visual(name, "cardVisual", x, y, w, h, z, {"Data": {"projections": [measure_field(measure)]}})


def slicer(
    name: str,
    table: str,
    col: str,
    x: float,
    y: float,
    w: float = 220,
    h: float = 110,
    z: int = 1000,
    default_value: str | int | None = None,
) -> dict:
    item = visual(
        name,
        "slicer",
        x,
        y,
        w,
        h,
        z,
        {"Values": {"projections": [column_field(table, col)]}},
        {
            "data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Basic'"}}}}}],
            "selection": [
                {
                    "properties": {
                        "singleSelect": {"expr": {"Literal": {"Value": "true"}}},
                        "strictSingleSelect": {"expr": {"Literal": {"Value": "true"}}},
                        "selectAllCheckboxEnabled": {"expr": {"Literal": {"Value": "false"}}},
                    }
                }
            ],
        },
    )
    if table == "DimREIT":
        item["visual"]["syncGroup"] = {
            "groupName": "K_REIT_Company",
            "fieldChanges": True,
            "filterChanges": True,
        }
    elif table == "DimPeriod":
        item["visual"]["syncGroup"] = {
            "groupName": "K_REIT_AnalysisYear",
            "fieldChanges": True,
            "filterChanges": True,
        }
    if default_value is not None:
        literal = f"{default_value}L" if isinstance(default_value, int) else f"'{default_value}'"
        item["visual"]["objects"]["general"] = [
            {
                "properties": {
                    "filter": {
                        "filter": {
                            "Version": 2,
                            "From": [{"Name": "s", "Entity": table, "Type": 0}],
                            "Where": [
                                {
                                    "Condition": {
                                        "In": {
                                            "Expressions": [
                                                {
                                                    "Column": {
                                                        "Expression": {"SourceRef": {"Source": "s"}},
                                                        "Property": col,
                                                    }
                                                }
                                            ],
                                            "Values": [[{"Literal": {"Value": literal}}]],
                                        }
                                    }
                                }
                            ],
                        }
                    }
                }
            }
        ]
    return item


def table(name: str, fields: list[dict], x: float, y: float, w: float, h: float, z: int = 1000) -> dict:
    return visual(name, "tableEx", x, y, w, h, z, {"Values": {"projections": fields}})


def bar(name: str, category: dict, value: dict, x: float, y: float, w: float, h: float, z: int = 1000) -> dict:
    return visual(name, "clusteredBarChart", x, y, w, h, z, {"Category": {"projections": [category]}, "Y": {"projections": [value]}})


def scatter(name: str, details: dict, x_measure: dict, y_measure: dict, x: float, y: float, w: float, h: float, z: int = 1000) -> dict:
    return visual(
        name,
        "scatterChart",
        x,
        y,
        w,
        h,
        z,
        {"Details": {"projections": [details]}, "X": {"projections": [x_measure]}, "Y": {"projections": [y_measure]}},
    )


def write_visual(page_dir: Path, data: dict) -> None:
    vdir = page_dir / "visuals" / data["name"]
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / "visual.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report_pages() -> None:
    page1_id = "4d3c0a10fecce17f65e3"
    page1 = REPORT_PAGES_DIR / page1_id
    page1_json = json.loads((page1 / "page.json").read_text(encoding="utf-8"))
    page1_json["displayName"] = "01 Tax Executive Summary"
    page1_json["displayOption"] = "FitToPage"
    (page1 / "page.json").write_text(json.dumps(page1_json, ensure_ascii=False, indent=2), encoding="utf-8")

    positions = {
        "4e96e31b2d192b4ac837": (20, 20, 220, 90, 100),
        "157bf0fae63c68557422": (250, 20, 180, 90, 110),
        "776fa67dfd83ca2b06fd": (440, 20, 210, 90, 120),
        "96e12a045696332e2651": (660, 20, 160, 90, 130),
        "680c0ae3edab07209f19": (830, 20, 420, 90, 140),
        "3c927abc1968e6543878": (20, 600, 220, 90, 900),
        "c9c59eb01c3122ad6a42": (250, 600, 470, 90, 910),
        "0ce42fd0c46ff52e4212": (730, 600, 520, 90, 920),
    }
    for visual_id, (x, y, w, h, z) in positions.items():
        path = page1 / "visuals" / visual_id / "visual.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            data["position"].update({"x": x, "y": y, "width": w, "height": h, "z": z, "tabOrder": z})
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    for item in [
        card("p1_estimated_tax", "추정 보유세(억원)", 20, 130, 170, 85, 200),
        card("p1_tax_to_ffo", "보유세 / FFO proxy", 200, 130, 170, 85, 210),
        card("p1_ffo_proxy", "FFO proxy(억원)", 380, 130, 170, 85, 220),
        card("p1_book_nav", "Book NAV proxy(억원)", 560, 130, 170, 85, 230),
        card("p1_gross_ltv", "총자산 기준 차입비율", 740, 130, 170, 85, 240),
        card("p1_interest_cover", "FFO 이자감당배율 proxy", 920, 130, 170, 85, 250),
        card("p1_high_issue_count", "고위험 이슈 수", 1100, 130, 150, 85, 260),
        bar("p1_tax_burden_bar", column_field("DimREIT", "company_name"), measure_field("보유세 / FFO proxy"), 20, 235, 560, 340, 300),
        scatter(
            "p1_tax_ltv_scatter",
            column_field("DimREIT", "company_name"),
            measure_field("총자산 기준 차입비율"),
            measure_field("보유세 / FFO proxy"),
            600,
            235,
            310,
            340,
            310,
        ),
        table(
            "p1_lineage_table",
            [
                column_field("DimREIT", "company_name"),
                column_field("FactKPI", "source_label"),
                column_field("FactKPI", "source_name"),
                column_field("FactKPI", "source_date"),
                column_field("FactKPI", "financial_statement_scope"),
                column_field("FactKPI", "calculation_method"),
            ],
            930,
            235,
            320,
            340,
            320,
        ),
    ]:
        write_visual(page1, item)

    for page_id, display_name in [
        ("taxIssueSensitivity", "02 Tax Issue & Sensitivity"),
        ("requestReviewWorkflow", "03 Request & Review Workflow"),
    ]:
        page_dir = REPORT_PAGES_DIR / page_id
        (page_dir / "visuals").mkdir(parents=True, exist_ok=True)
        (page_dir / "page.json").write_text(
            json.dumps(
                {
                    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
                    "name": page_id,
                    "displayName": display_name,
                    "displayOption": "FitToPage",
                    "height": 720,
                    "width": 1280,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    page2 = REPORT_PAGES_DIR / "taxIssueSensitivity"
    for item in [
        slicer("p2_company_slicer", "DimREIT", "company_name", 20, 20, 220, 90, 100, "SK리츠"),
        slicer("p2_tax_increase_slicer", "pHoldingTaxIncrease", "pHoldingTaxIncrease", 250, 20, 180, 90, 110),
        slicer("p2_ffo_decline_slicer", "pFFODecline", "pFFODecline", 440, 20, 180, 90, 120),
        slicer("p2_period_slicer", "DimPeriod", "analysis_year", 630, 20, 170, 90, 130, 2026),
        card("p2_stress_tax", "스트레스 보유세(억원)", 20, 130, 180, 85, 200),
        card("p2_stress_ffo", "스트레스 FFO proxy(억원)", 210, 130, 180, 85, 210),
        card("p2_stress_ratio", "스트레스 보유세 / FFO proxy", 400, 130, 180, 85, 220),
        card("p2_extra_cash", "추가 현금유출(억원)", 590, 130, 180, 85, 230),
        card("p2_stress_level", "스트레스 위험수준", 780, 130, 180, 85, 240),
        table(
            "p2_issue_matrix",
            [
                column_field("FactIssue", "tax_issue"),
                column_field("FactIssue", "risk_level"),
                column_field("FactIssue", "occurrence_basis"),
                column_field("FactIssue", "review_direction"),
                column_field("FactIssue", "evidence_request"),
                column_field("FactIssue", "source_type"),
            ],
            20,
            240,
            760,
            430,
            300,
        ),
        table(
            "p2_bridge",
            [
                column_field("FactBridge", "stage_order"),
                column_field("FactBridge", "stage_label"),
                column_field("FactBridge", "display_value"),
                column_field("FactBridge", "interpretation"),
            ],
            800,
            240,
            430,
            200,
            310,
        ),
        bar("p2_base_stress_bar", column_field("FactStress", "scenario"), agg_field("FactStress", "amount_eok", "금액(억원)"), 800, 460, 430, 210, 320),
    ]:
        write_visual(page2, item)

    page3 = REPORT_PAGES_DIR / "requestReviewWorkflow"
    for item in [
        slicer("p3_company_slicer", "DimREIT", "company_name", 20, 20, 220, 90, 100, "SK리츠"),
        card("p3_request_count", "요청자료 수", 250, 20, 170, 85, 110),
        card("p3_review_count", "검토 필요 항목 수", 430, 20, 170, 85, 120),
        card("p3_validation_count", "Validation 이슈 수", 610, 20, 170, 85, 130),
        card("p3_validation_status", "Validation 종합 상태", 790, 20, 190, 85, 140),
        card("p3_fallback_status", "Fallback 상태", 990, 20, 220, 85, 150),
        table(
            "p3_request_list",
            [
                column_field("FactRequest", "priority"),
                column_field("FactRequest", "request_item"),
                column_field("FactRequest", "request_purpose"),
                column_field("FactRequest", "related_issue"),
                column_field("FactRequest", "review_area"),
                column_field("FactRequest", "note"),
            ],
            20,
            130,
            590,
            390,
            300,
        ),
        table(
            "p3_reconciliation",
            [
                column_field("FactReconciliation", "asset_name"),
                column_field("FactReconciliation", "book_value_eok"),
                column_field("FactReconciliation", "official_price_eok"),
                column_field("FactReconciliation", "estimated_holding_tax_eok"),
                column_field("FactReconciliation", "holding_tax_to_ffo"),
                column_field("FactReconciliation", "review_required"),
            ],
            630,
            130,
            590,
            210,
            310,
        ),
        table(
            "p3_validation",
            [
                column_field("FactValidation", "validation_status"),
                column_field("FactValidation", "missing_fields"),
                column_field("FactValidation", "fallback_used"),
                column_field("FactValidation", "calculation_limitations"),
                column_field("FactValidation", "source_note"),
            ],
            630,
            360,
            590,
            160,
            320,
        ),
        card("p3_streamlit_url", "Tax Review Pack 열기", 20, 545, 590, 90, 330),
        slicer("p3_period_slicer", "DimPeriod", "analysis_year", 630, 545, 170, 90, 920, 2026),
    ]:
        write_visual(page3, item)

    (REPORT_PAGES_DIR / "pages.json").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
                "pageOrder": ["4d3c0a10fecce17f65e3", "taxIssueSensitivity", "requestReviewWorkflow"],
                "activePageName": "4d3c0a10fecce17f65e3",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    write_measures()
    write_report_pages()
    runpy.run_path(
        str(PROJECT_ROOT / "scripts" / "validation" / "normalize_powerbi_report.py"),
        run_name="__main__",
    )
    print("Power BI TMDL measures and PBIR pages updated.")


if __name__ == "__main__":
    main()
