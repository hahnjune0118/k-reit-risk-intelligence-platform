from __future__ import annotations

import json
from pathlib import Path

from scripts.validation.validate_powerbi_project import validate


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = PROJECT_ROOT / "powerbi" / "K_REIT_Tax_Dashboard_v1.SemanticModel" / "definition"
REPORT_DIR = PROJECT_ROOT / "powerbi" / "K_REIT_Tax_Dashboard_v1.Report" / "definition"


def test_powerbi_project_has_no_broken_static_contracts():
    result = validate()
    assert result["status"] == "passed", result["errors"]


def test_peer_median_ignores_selected_company_filter_and_requests_are_distinct():
    measures = (MODEL_DIR / "tables" / "_Measures.tmdl").read_text(encoding="utf-8")

    assert "REMOVEFILTERS(DimREIT)" in measures
    assert "ALLSELECTED(DimREIT[company_name])" not in measures
    assert "DISTINCTCOUNT(FactRequest[request_item])" in measures
    assert "총자산 기준 Gross LTV" not in measures
    assert "measure '총자산 기준 차입비율'" in measures


def test_all_report_pages_use_company_and_analysis_period_slicers():
    slicers = [
        REPORT_DIR / "pages" / "4d3c0a10fecce17f65e3" / "visuals" / "157bf0fae63c68557422" / "visual.json",
        REPORT_DIR / "pages" / "taxIssueSensitivity" / "visuals" / "p2_period_slicer" / "visual.json",
        REPORT_DIR / "pages" / "requestReviewWorkflow" / "visuals" / "p3_period_slicer" / "visual.json",
    ]
    for slicer_path in slicers:
        document = json.loads(slicer_path.read_text(encoding="utf-8"))
        projection = document["visual"]["query"]["queryState"]["Values"]["projections"][0]
        column = projection["field"]["Column"]
        assert column["Expression"]["SourceRef"]["Entity"] == "DimPeriod"
        assert column["Property"] == "analysis_year"
        assert document["visual"]["syncGroup"]["groupName"] == "K_REIT_AnalysisYear"
        assert document["visual"]["syncGroup"]["filterChanges"] is True


def test_powerbi_tmdl_uses_portable_export_parameter():
    expression = (MODEL_DIR / "expressions.tmdl").read_text(encoding="utf-8")
    model = (MODEL_DIR / "model.tmdl").read_text(encoding="utf-8")

    assert "expression pExportFolder" in expression
    assert "ref expression pExportFolder" in model
    assert "C:\\Users\\" not in expression


def test_streamlit_entry_visual_shows_label_and_keeps_url_as_action_only():
    path = (
        REPORT_DIR
        / "pages"
        / "requestReviewWorkflow"
        / "visuals"
        / "p3_streamlit_url"
        / "visual.json"
    )
    document = json.loads(path.read_text(encoding="utf-8"))
    projection = document["visual"]["query"]["queryState"]["Data"]["projections"][0]
    assert projection["field"]["Measure"]["Property"] == "Tax Review Pack 열기"
    link = document["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]
    assert link["show"]["expr"]["Literal"]["Value"] == "true"
    assert link["webUrl"]["expr"]["Measure"]["Property"] == "Detailed Tax Review Pack URL"
