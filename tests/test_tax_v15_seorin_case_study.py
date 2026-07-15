from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from src.tax_v15.case_study import (
    CORE_ASSET_ID,
    CORE_ASSET_TAXPAYER_ID,
    CORE_RECALCULATION_AFTER_END_DIGIT_TREATMENT,
    CORE_RECALCULATION_BEFORE_END_DIGIT_TREATMENT,
    CORE_STOCK_CODE,
    GOLDEN_ASSET_ID,
    build_case_kpis,
    build_case_request_list,
    build_sensitivity_scenarios,
    build_tax_issue_matrix,
    calculate_sensitivity_scenario,
    select_core_asset_tax_case,
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
    return select_core_asset_tax_case(load_v15_bundle())


@pytest.fixture(scope="module")
def scenario_frames(case):
    return build_sensitivity_scenarios(case, -10, 20)


@pytest.fixture(scope="module")
def issue_frames(case):
    issues = build_tax_issue_matrix(case)
    requests = build_case_request_list(issues, case.requests)
    return issues, requests


def _scenario_row(summary: pd.DataFrame, name: str) -> pd.Series:
    rows = summary[summary["민감도 분석"].eq(name)]
    assert len(rows) == 1
    return rows.iloc[0]


def test_tax_scope_is_only_sk_reit_and_sk_seorin(case):
    assert case.stock_code == CORE_STOCK_CODE
    assert case.tax_year == 2026
    assert case.assets["asset_id"].tolist() == [CORE_ASSET_ID]
    assert case.assets["asset_name"].tolist() == ["SK서린빌딩"]
    assert case.taxpayers["taxpayer_id"].tolist() == [CORE_ASSET_TAXPAYER_ID]
    assert case.assets["reit_name"].nunique() == 1


def test_deprecated_selector_and_ids_remain_compatible(case):
    legacy = select_golden_case(load_v15_bundle())

    assert GOLDEN_ASSET_ID == CORE_ASSET_ID
    assert legacy.assets.equals(case.assets)


def test_tax_ui_is_fixed_to_one_asset_and_uses_korean_public_copy():
    source = (ROOT / "ui_tax_case_study.py").read_text(encoding="utf-8")
    wrapper = (ROOT / "ui_tax_v15.py").read_text(encoding="utf-8")

    assert "SK리츠 핵심 자산 보유세 세무검토" in source
    assert "### SK서린빌딩" in source
    assert "st.selectbox" not in source
    assert "Peer Benchmark" not in source
    assert "FFO" not in source
    assert "끝수 처리 후 보유세 재계산액" in source
    assert "끝수 처리 전 산식상 산출세액" in source
    assert not any(
        term in source + wrapper
        for term in [
            "Golden Asset",
            "Golden Case",
            "Raw statutory recalculation",
            "Actual assessed amount",
            "Notice reconciliation",
        ]
    )


def test_sidebar_keeps_default_background_and_korean_tax_caption():
    sidebar = (ROOT / "ui_sidebar.py").read_text(encoding="utf-8")
    layout = (ROOT / "ui_layout.py").read_text(encoding="utf-8")

    assert "selected_company_form" in sidebar
    assert 'st.selectbox(\n                "분석 대상회사"' in sidebar
    assert "background:#fff9df" not in layout
    assert "border-right:3px solid" not in layout
    assert "SK서린빌딩 보유세 세무검토의 주요 단계와 민감도 분석을 " in sidebar
    assert "아래에서 확인할 수 있습니다." in sidebar


def test_base_scenario_matches_before_and_after_totals(scenario_frames):
    summary, breakdown = scenario_frames
    base = _scenario_row(summary, "기준")
    base_details = breakdown[breakdown["민감도 분석"].eq("기준")]
    total = base_details[base_details["세목"].eq("총계")].iloc[0]

    assert base["끝수 처리 전 합계"] == CORE_RECALCULATION_BEFORE_END_DIGIT_TREATMENT
    assert base["끝수 처리 후 합계"] == CORE_RECALCULATION_AFTER_END_DIGIT_TREATMENT
    assert total["끝수 처리 전 산출세액"] == CORE_RECALCULATION_BEFORE_END_DIGIT_TREATMENT
    assert total["끝수 처리 후 재계산액"] == CORE_RECALCULATION_AFTER_END_DIGIT_TREATMENT
    assert all(
        isinstance(value, Decimal)
        for value in base_details["끝수 처리 후 재계산액"]
    )


def test_five_and_ten_percent_scenarios_are_exact(scenario_frames):
    summary, _ = scenario_frames
    five = _scenario_row(summary, "공시가격·시가표준액 5% 상승")
    ten = _scenario_row(summary, "공시가격·시가표준액 10% 상승")

    assert five["끝수 처리 전 합계"] == Decimal("1313250671.982456000")
    assert five["끝수 처리 후 합계"] == Decimal("1313250630")
    assert ten["끝수 처리 전 합계"] == Decimal("1375790375.41019200")
    assert ten["끝수 처리 후 합계"] == Decimal("1375790350")


def test_custom_scenario_accepts_bounds_and_rejects_invalid_steps(case):
    lower, _ = calculate_sensitivity_scenario(case, "사용자 설정", -10, -10)
    upper, _ = calculate_sensitivity_scenario(case, "사용자 설정", 20, 20)

    assert lower["끝수 처리 후 합계"] < CORE_RECALCULATION_AFTER_END_DIGIT_TREATMENT
    assert upper["끝수 처리 후 합계"] > CORE_RECALCULATION_AFTER_END_DIGIT_TREATMENT
    with pytest.raises(ValueError, match=r"-10%부터 \+20%"):
        calculate_sensitivity_scenario(case, "사용자 설정", -11, 0)
    with pytest.raises(ValueError, match="1% 단위"):
        calculate_sensitivity_scenario(case, "사용자 설정", Decimal("1.5"), 0)


def test_scenario_reuses_tax_rule_master_without_float(case):
    rules = case.rules.copy()
    mask = rules["rule_code"].eq("property_tax_land_separated")
    original_rate = Decimal(str(rules.loc[mask, "marginal_rate"].iloc[0]))
    rules["marginal_rate"] = rules["marginal_rate"].astype(object)
    rules.loc[mask, "marginal_rate"] = original_rate * Decimal("2")
    changed_case = replace(case, rules=rules)
    changed, detail = calculate_sensitivity_scenario(changed_case, "기준", 0, 0)

    assert changed["끝수 처리 후 합계"] > CORE_RECALCULATION_AFTER_END_DIGIT_TREATMENT
    land_tax = detail[detail["세목"].eq("토지 재산세")].iloc[0]
    assert land_tax["끝수 처리 전 산출세액"] == Decimal("1033802910.0")
    assert land_tax["끝수 처리 후 재계산액"] == Decimal("1033802910")
    assert "제111조" in land_tax["법적 근거"]


def test_scenario_keeps_classification_and_is_not_notice(case, scenario_frames):
    _, breakdown = scenario_frames
    assert case.taxpayers["tax_classification"].eq("separated_public_reit").all()
    assert case.taxpayers["actual_notice_classification"].eq("unverified").all()
    assert not breakdown["계산상태"].str.contains("verified_notice").any()
    ui_source = (ROOT / "ui_tax_case_study.py").read_text(encoding="utf-8")
    assert "미래 결정세액 또는 과세관청의 고지세액을 예측한" in ui_source


def test_each_scenario_total_equals_per_line_after_sum(scenario_frames):
    summary, breakdown = scenario_frames
    for scenario_name in summary["민감도 분석"]:
        detail = breakdown[
            breakdown["민감도 분석"].eq(scenario_name)
            & breakdown["세목"].ne("총계")
        ]
        expected = sum(detail["끝수 처리 후 재계산액"], Decimal("0"))
        actual = _scenario_row(summary, scenario_name)["끝수 처리 후 합계"]
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


def test_memo_and_exports_use_korean_sections_and_amounts(case, scenario_frames, issue_frames):
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
    html = review_document_html("SK리츠 SK서린빌딩 보유세 세무검토", memo).decode("utf-8")
    workbook = review_pack_excel_bytes(
        {
            "민감도분석": summary,
            "세목별민감도": breakdown,
            "주요세무쟁점": issues,
            "추가요청자료": requests,
        }
    )
    sheet_names = pd.ExcelFile(BytesIO(workbook)).sheet_names

    for section in [
        "검토 결론",
        "소유·신탁 구조 및 재산세 납세의무자",
        "목적사업용 토지의 분리과세 적용요건",
        "세목별 끝수 처리",
        "보유세 민감도 분석",
        "주요 세무쟁점",
        "추가 요청자료 목록",
        "고지세액 대사",
    ]:
        assert section in memo
        assert section in html
    assert f"{CORE_RECALCULATION_AFTER_END_DIGIT_TREATMENT:,}원" in memo
    assert f"{CORE_RECALCULATION_BEFORE_END_DIGIT_TREATMENT:,}원" in memo
    assert "실제 고지세액: 과세내역서 미확보" in memo
    assert set(sheet_names) == {"민감도분석", "세목별민감도", "주요세무쟁점", "추가요청자료"}


def test_no_notice_or_fallback_claim_is_reintroduced(case):
    source = (ROOT / "src" / "tax_v15" / "case_study.py").read_text(encoding="utf-8")
    ui_source = (ROOT / "ui_tax_case_study.py").read_text(encoding="utf-8")

    assert case.taxpayers["actual_notice_classification"].eq("unverified").all()
    assert case.taxpayers["notice_reconciliation_status"].eq("not_reconciled").all()
    assert "book_value" not in source
    assert "peer_snapshot" not in source
    assert "장부가액" not in ui_source
    assert "Peer" not in ui_source
    assert "실제 고지세액이 아니며" in ui_source
