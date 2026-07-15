from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PAGES_DIR = (
    PROJECT_ROOT
    / "powerbi"
    / "K_REIT_Tax_Dashboard_v1.Report"
    / "definition"
    / "pages"
)

EXPLICIT_TITLES = {
    "0ce42fd0c46ff52e4212": "데이터 기준 및 출처",
    "p1_lineage_table": "핵심 지표 Source Lineage",
    "p1_tax_burden_bar": "Peer 보유세 / FFO proxy",
    "p1_tax_ltv_scatter": "보유세 부담과 총자산 기준 차입비율",
    "p2_base_stress_bar": "기준·스트레스 보유세",
    "p2_bridge": "Holding Tax Bridge",
    "p2_issue_matrix": "Tax Issue Matrix",
    "p3_reconciliation": "보유세 Reconciliation",
    "p3_request_list": "Tax 요청자료",
    "p3_validation": "Tax 입력값 Validation",
}

SYNC_GROUPS = {
    "4e96e31b2d192b4ac837": "K_REIT_Company",
    "p2_company_slicer": "K_REIT_Company",
    "p3_company_slicer": "K_REIT_Company",
    "157bf0fae63c68557422": "K_REIT_AnalysisYear",
    "p2_period_slicer": "K_REIT_AnalysisYear",
    "p3_period_slicer": "K_REIT_AnalysisYear",
}


def _literal(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def _title_object(show: bool, text: str = "") -> list[dict]:
    properties = {"show": _literal("true" if show else "false")}
    if show and text:
        properties["text"] = _literal(f"'{text}'")
    return [{"properties": properties}]


def main() -> None:
    for path in sorted(PAGES_DIR.rglob("visual.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        visual = document.setdefault("visual", {})
        visual_type = visual.get("visualType", "")
        visual_name = str(document.get("name", path.parent.name))
        container_objects = visual.setdefault("visualContainerObjects", {})

        explicit_title = EXPLICIT_TITLES.get(visual_name, "")
        if visual_type in {"tableEx", "clusteredBarChart", "scatterChart"} and explicit_title:
            container_objects["title"] = _title_object(True, explicit_title)
        else:
            container_objects["title"] = _title_object(False)

        if visual_name in SYNC_GROUPS:
            visual["syncGroup"] = {
                "groupName": SYNC_GROUPS[visual_name],
                "fieldChanges": True,
                "filterChanges": True,
            }

        if visual_name == "p3_streamlit_url":
            projection = visual["query"]["queryState"]["Data"]["projections"][0]
            projection["field"]["Measure"]["Property"] = "Tax Review Pack 열기"
            projection["queryRef"] = "_Measures.Tax Review Pack 열기"
            projection["nativeQueryRef"] = "Tax Review Pack 열기"
            container_objects["visualLink"] = [
                {
                    "properties": {
                        "show": _literal("true"),
                        "type": _literal("'WebUrl'"),
                        "webUrl": {
                            "expr": {
                                "Measure": {
                                    "Expression": {
                                        "SourceRef": {"Entity": "_Measures"}
                                    },
                                    "Property": "Detailed Tax Review Pack URL",
                                }
                            }
                        },
                        "enabledTooltip": _literal("'상세 Tax Review Pack 열기'"),
                    }
                }
            ]

        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
