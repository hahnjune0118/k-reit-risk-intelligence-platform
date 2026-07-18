from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from src.tax_v15.case_study import (
    GOLDEN_ASSET_ID,
    GOLDEN_RECALCULATION_RAW,
    GOLDEN_STOCK_CODE,
    GOLDEN_TAXPAYER_ID,
    build_case_kpis,
    build_case_request_list,
    build_sensitivity_scenarios,
    build_tax_issue_matrix,
    calculate_sensitivity_scenario,
    select_golden_case,
)
from src.tax_v15.loaders import load_v15_bundle
from src.tax_v15.reporting import (
    build_tax_review_memo,
    review_document_html,
    review_pack_excel_bytes,
)


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ISSUES = {
    "notice_classification_unverified": "P0",
    "notice_amount_unreconciled": "P0",
    "assessment_date_trust_status_unverified": "P0",
    "parcel_area_difference_5_3": "P1",
    "fire_notice_code_unreconciled": "P1",
    "notice_adjustments_unmodeled": "P1",
}


@pytest.fixture(scope="module")
def case():
    return select_golden_case(load_v15_bundle())


@pytest.fixture(scope="module")
def scenario_frames(case):
    return build_sensitivity_scenarios(case, -10, 20)


@pytest.fixture(scope="module")
def issue_frames(case):
    issues = build_tax_issue_matrix(case)
    requests = build_case_request_list(issues, case.requests)
    return issues, requests


def _scenario_row(summary: pd.DataFrame, name: str) -> pd.Series:
    rows = summary[summary["Scenario"].eq(name)]
    assert len(rows) == 1
    return rows.iloc[0]


def test_tax_scope_is_only_sk_reit_and_sk_seorin(case):
    assert case.stock_code == GOLDEN_STOCK_CODE
    assert case.tax_year == 2026
    assert case.assets["asset_id"].tolist() == [GOLDEN_ASSET_ID]
    assert case.assets["asset_name"].tolist() == ["SK서린빌딩"]
    assert case.taxpayers["taxpayer_id"].tolist() == [GOLDEN_TAXPAYER_ID]
    assert case.assets["reit_name"].nunique() == 1


def test_tax_ui_has_no_cross_reit_or_asset_selectors():
    source = (ROOT / "ui_tax_decision_first.py").read_text(encoding="utf-8")
    wrapper = (ROOT / "ui_tax_v15.py").read_text(encoding="utf-8")

    assert "Tax: 의사결정 중심 보유세 검토" in source
    assert "ui_tax_decision_first" in wrapper
    assert "st.selectbox" not in source
    assert "분석대상 리츠" not in source
    assert '"전체 자산"' not in source
    assert '"전체 납세의무자"' not in source
    assert '"전체 보유구조"' not in source
    assert "ESR" not in source + wrapper
    assert "Peer Benchmark" not in source
    assert "Sample Estimate" not in source
    assert "FFO" not in source
    assert '**Raw statutory recalculation:** `{base_total:,}원`' in source


def test_tax_ui_uses_four_decision_first_tabs():
    source = (ROOT / "ui_tax_decision_first.py").read_text(encoding="utf-8")

    for tab_name in (
        "결론 및 시나리오",
        "주요 이슈 및 요청자료",
        "계산조서",
        "근거 및 다운로드",
    ):
        assert tab_name in source

    assert "공식 과세기초자료를 이용한 재계산 결과이며" in source
    assert "17. Downloads" not in source
    assert "_render_stage" not in source


def test_tax_ui_preserves_decision_metrics_and_downloads():
    source = (ROOT / "ui_tax_decision_first.py").read_text(encoding="utf-8")

    for label in (
        "2026 보유세 재계산액",
        "공식 입력근거 Coverage",
        "실제 고지서 대사 Coverage",
        "미해결 P0",
        "미해결 P1",
        "재계산 세목",
        "시나리오별 보유세 재계산액",
        "Base 대비 증감액 및 증감률",
        "Base 세목별 구성",
    ):
        assert label in source

    for download in (
        "계산내역 CSV",
        "시나리오 CSV",
        "이슈 목록 CSV",
        "요청자료 CSV",
        "검토팩 Excel",
        "검토메모 Markdown",
        "검토문서 HTML",
    ):
        assert download in source


def test_general_mode_keeps_multi_company_selector_and_tax_highlight():
    sidebar = (ROOT / "ui_sidebar.py").read_text(encoding="utf-8")
    layout = (ROOT / "ui_layout.py").read_text(encoding="utf-8")

    assert "selected_company_form" in sidebar
    assert 'st.selectbox(\n                "분석 대상회사"' in sidebar
    assert 'selected_user_mode == "Tax"' in layout
    assert "background:#fff9df" in layout
    assert "결론·시나리오·이슈·계산조서·근거를 네 탭에서 확인하세요." in sidebar


def test_base_scenario_matches_golden_raw_total(scenario_frames):
    summary, breakdown = scenario_frames
    base = _scenario_row(summary, "Base")
    base_details = breakdown[breakdown["Scenario"].eq("Base")]

    assert base["총 보유세"] == GOLDEN_RECALCULATION_RAW
    assert base_details.loc[base_details["세목"].eq("총계"), "계산세액"].iloc[0] == (
        GOLDEN_RECALCULATION_RAW
    )
    assert all(isinstance(value, Decimal) for value in base_details["계산세액"])


def test_moderate_and_severe_scenarios_are_exact(scenario_frames):
    summary, _ = scenario_frames
    moderate = _scenario_row(summary, "Moderate")
    severe = _scenario_row(summary, "Severe")

    assert moderate["토지 시가표준액"] == Decimal("387676091250.0000")
    assert moderate["건축물 시가표준액"] == Decimal("42232839709.200")
    assert moderate["총 보유세"] == Decimal("1313250671.982456")
    assert severe["토지 시가표준액"] == Decimal("406136857500.000")
    assert severe["건축물 시가표준액"] == Decimal("44243927314.40")
    assert severe["총 보유세"] == Decimal("1375790375.410192")


def test_custom_scenario_accepts_bounds_and_rejects_invalid_steps(case):
    lower, _ = calculate_sensitivity_scenario(case, "Custom", -10, -10)
    upper, _ = calculate_sensitivity_scenario(case, "Custom", 20, 20)

    assert lower["총 보유세"] < GOLDEN_RECALCULATION_RAW
    assert upper["총 보유세"] > GOLDEN_RECALCULATION_RAW
    with pytest.raises(ValueError, match=r"-10%부터 \+20%"):
        calculate_sensitivity_scenario(case, "Custom", -11, 0)
    with pytest.raises(ValueError, match="1% 단위"):
        calculate_sensitivity_scenario(case, "Custom", 1.5, 0)


def test_scenario_reuses_tax_rule_master(case):
    rules = case.rules.copy()
    mask = rules["rule_code"].eq("property_tax_land_separated")
    original_rate = Decimal(str(rules.loc[mask, "marginal_rate"].iloc[0]))
    rules.loc[mask, "marginal_rate"] = float(original_rate * Decimal("2"))
    changed_case = replace(case, rules=rules)
    changed, detail = calculate_sensitivity_scenario(changed_case, "Base", 0, 0)

    assert changed["총 보유세"] > GOLDEN_RECALCULATION_RAW
    land_tax = detail[detail["세목"].eq("토지 재산세")].iloc[0]
    assert land_tax["계산세액"] == Decimal("1033802910.0")
    assert "제111조" in land_tax["법적 근거"]


def test_scenario_keeps_classification_and_is_not_notice(case, scenario_frames):
    _, breakdown = scenario_frames
    assert case.taxpayers["tax_classification"].eq("separated_public_reit").all()
    assert case.taxpayers["actual_notice_classification"].eq("unverified").all()
    assert not breakdown["계산상태"].str.contains("verified_notice").any()
    ui_source = (ROOT / "ui_tax_decision_first.py").read_text(encoding="utf-8")
    assert "과세관청의 결정세액을 예측하지 않습니다." in ui_source


def test_each_scenario_total_equals_breakdown_sum(scenario_frames):
    summary, breakdown = scenario_frames
    for scenario_name in summary["Scenario"]:
        detail = breakdown[
            breakdown["Scenario"].eq(scenario_name)
            & breakdown["세목"].ne("총계")
        ]
        expected = sum(detail["계산세액"], Decimal("0"))
        actual = _scenario_row(summary, scenario_name)["총 보유세"]
        assert actual == expected


def test_issue_matrix_contains_required_open_p0_and_p1(issue_frames):
    issues, _ = issue_frames
    actual = dict(zip(issues["issue_code"], issues["priority"], strict=True))

    assert actual == EXPECTED_ISSUES
    assert issues["current_status"].eq("Open").all()
    assert issues["resolution_status"].eq("Open").all()
    assert issues["memo_included"].eq(True).all()  # noqa: E712
    area = issues[issues["issue_code"].eq("parcel_area_difference_5_3")].iloc[0]
    assert "901,567.1원" in area["quantitative_sensitivity"]


def test_issue_matrix_kpis_and_request_links(case, issue_frames):
    issues, requests = issue_frames
    kpis = build_case_kpis(case, issues)

    assert kpis == {
        "p0_open": 3,
        "p1_open": 3,
        "completed_tax_items": 9,
        "unreconciled_items": 6,
        "notice_coverage": "0%",
        "evidence_coverage": "5/5 (100%)",
    }
    assert len(requests) == 6
    assert requests["linked_request_id"].str.strip().ne("").all()
    assert set(requests["issue_code"]) == set(EXPECTED_ISSUES)


def test_memo_and_exports_include_scenario_issue_and_requests(
    case,
    scenario_frames,
    issue_frames,
):
    summary, breakdown = scenario_frames
    issues, requests = issue_frames
    memo = build_tax_review_memo(
        case.reit_name,
        case.tax_year,
        case.assets,
        case.parcels,
        case.buildings,
        case.taxpayers,
        case.calculations,
        case.validations,
        requests,
        summary,
        issues,
    )
    html = review_document_html("SK Seorin Tax Review", memo).decode("utf-8")
    workbook = review_pack_excel_bytes(
        {
            "ScenarioSummary": summary,
            "ScenarioBreakdown": breakdown,
            "TaxIssueMatrix": issues,
            "RequestList": requests,
        }
    )
    sheet_names = pd.ExcelFile(BytesIO(workbook)).sheet_names

    for section in [
        "Executive Conclusion",
        "Ownership and Taxpayer Structure",
        "Public REIT Separate-Tax Eligibility",
        "Tax Sensitivity Scenario",
        "Tax Issue Matrix",
        "Request List",
        "Reconciliation",
        "Reviewer Sign-off",
    ]:
        assert section in memo
        assert section in html
    assert f"{GOLDEN_RECALCULATION_RAW:,}원" in memo
    assert "실제 고지세액: 미확인" in memo
    assert "notice_classification_unverified" in memo
    assert set(sheet_names) == {
        "ScenarioSummary",
        "ScenarioBreakdown",
        "TaxIssueMatrix",
        "RequestList",
    }


def test_no_notice_or_fallback_claim_is_reintroduced(case):
    source = (ROOT / "src" / "tax_v15" / "case_study.py").read_text(
        encoding="utf-8"
    )
    ui_source = (ROOT / "ui_tax_decision_first.py").read_text(encoding="utf-8")

    assert case.taxpayers["actual_notice_classification"].eq("unverified").all()
    assert case.taxpayers["notice_reconciliation_status"].eq("not_reconciled").all()
    assert "book_value" not in source
    assert "peer_snapshot" not in source
    assert "장부가액" not in ui_source
    assert "Peer" not in ui_source
    assert "실제 고지서와의 " in ui_source
    assert "대사는 완료되지 않았습니다." in ui_source


def test_tax_ui_keeps_expert_review_and_private_evidence_boundary():
    source = (ROOT / "ui_tax_decision_first.py").read_text(encoding="utf-8")

    assert "공동담보목록" in source
    assert "공식가액이나 실제 세금 고지서를 대체하지 않습니다." in source
    assert "비공개 등기·신탁 원문은 공개 앱에 노출하지 않으며" in source
    assert "Fail-closed" in source
