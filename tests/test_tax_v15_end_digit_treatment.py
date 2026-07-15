from __future__ import annotations

import inspect
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from src.tax_v15.calculators.common import truncate_to_ten_won
from src.tax_v15.case_study import (
    CORE_RECALCULATION_AFTER_END_DIGIT_TREATMENT,
    CORE_RECALCULATION_BEFORE_END_DIGIT_TREATMENT,
    build_sensitivity_scenarios,
    select_core_asset_tax_case,
)
from src.tax_v15.loaders import load_v15_bundle
from src.tax_v15.schemas import CSV_SCHEMAS


ROOT = Path(__file__).resolve().parents[1]
AUDIT_COLUMNS = [
    "calculated_tax_before_end_digit_treatment",
    "end_digit_treatment_unit",
    "end_digit_treatment_method",
    "end_digit_treatment_legal_basis",
    "calculated_tax_after_end_digit_treatment",
    "end_digit_treatment_difference",
]
EXPECTED_AFTER = [
    Decimal("516901450"),
    Decimal("361831010"),
    Decimal("103380290"),
    Decimal("70388060"),
    Decimal("39417310"),
    Decimal("14077610"),
    Decimal("144715200"),
]


@pytest.fixture(scope="module")
def case():
    return select_core_asset_tax_case(load_v15_bundle())


def _tax_rows(case) -> pd.DataFrame:
    return case.calculations[
        case.calculations["end_digit_treatment_method"]
        .fillna("")
        .astype(str)
        .ne("")
    ].copy()


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("516901455.0", "516901450"),
        ("361831018.50000", "361831010"),
        ("103380291.00", "103380290"),
        ("70388066.18200", "70388060"),
        ("39417317.061920", "39417310"),
        ("14077613.236400", "14077610"),
        ("144715207.574400", "144715200"),
    ],
)
def test_truncate_to_ten_won_matches_each_tax_line(amount: str, expected: str):
    assert truncate_to_ten_won(Decimal(amount)) == Decimal(expected)


@pytest.mark.parametrize(
    ("amount", "expected"),
    [("0", "0"), ("9.999", "0"), ("10", "10"), ("1250710930", "1250710930")],
)
def test_truncate_to_ten_won_boundaries(amount: str, expected: str):
    assert truncate_to_ten_won(Decimal(amount)) == Decimal(expected)


def test_truncate_to_ten_won_rejects_negative_amount():
    with pytest.raises(ValueError, match="음수"):
        truncate_to_ten_won(Decimal("-0.01"))


@pytest.mark.parametrize("amount", [1.5, 10, "10"])
def test_truncate_to_ten_won_rejects_non_decimal(amount):
    with pytest.raises(TypeError, match="Decimal"):
        truncate_to_ten_won(amount)


def test_truncation_implementation_uses_no_round_or_float():
    source = inspect.getsource(truncate_to_ten_won)

    assert "round(" not in source
    assert "float(" not in source


def test_calculation_schema_contains_end_digit_audit_columns():
    schema = CSV_SCHEMAS["tax_calculation_detail.csv"]

    assert all(column in schema for column in AUDIT_COLUMNS)
    assert schema.index("calculated_tax_after_end_digit_treatment") < schema.index(
        "calculated_tax"
    )


def test_each_calculated_line_preserves_before_and_after(case):
    rows = _tax_rows(case)

    assert len(rows) == 7
    assert [Decimal(str(value)) for value in rows["calculated_tax"]] == EXPECTED_AFTER
    assert rows["end_digit_treatment_unit"].map(Decimal).eq(Decimal("10")).all()
    assert rows["end_digit_treatment_method"].eq("10원 미만 끝수 미계산").all()
    assert rows["end_digit_treatment_legal_basis"].str.contains("지방회계법 제55조").all()


def test_before_after_totals_and_difference_are_exact(case):
    rows = _tax_rows(case)
    before = sum(
        (Decimal(str(value)) for value in rows["calculated_tax_before_end_digit_treatment"]),
        Decimal("0"),
    )
    after = sum((Decimal(str(value)) for value in rows["calculated_tax"]), Decimal("0"))
    difference = sum(
        (Decimal(str(value)) for value in rows["end_digit_treatment_difference"]),
        Decimal("0"),
    )

    assert before == CORE_RECALCULATION_BEFORE_END_DIGIT_TREATMENT
    assert after == CORE_RECALCULATION_AFTER_END_DIGIT_TREATMENT
    assert difference == Decimal("38.55472")
    assert before - after == difference


def test_calculated_tax_is_the_after_amount(case):
    rows = _tax_rows(case)

    assert all(
        Decimal(str(calculated)) == Decimal(str(after))
        for calculated, after in zip(
            rows["calculated_tax"],
            rows["calculated_tax_after_end_digit_treatment"],
            strict=True,
        )
    )


def test_total_only_truncation_is_not_used(case):
    rows = _tax_rows(case)
    total_only = truncate_to_ten_won(CORE_RECALCULATION_BEFORE_END_DIGIT_TREATMENT)
    per_line_total = sum(
        (Decimal(str(value)) for value in rows["calculated_tax"]),
        Decimal("0"),
    )

    assert total_only == Decimal("1250710960")
    assert per_line_total == Decimal("1250710930")
    assert total_only != per_line_total


def test_non_applicable_and_value_rows_have_no_end_digit_audit_values(case):
    excluded = case.calculations[
        case.calculations["calculation_status"].eq("not_applicable")
        | case.calculations["tax_name"].eq("토지 시가표준액")
    ]

    assert not excluded.empty
    assert excluded[AUDIT_COLUMNS].isna().all().all()


def test_sensitivity_scenarios_use_the_same_per_line_engine(case):
    summary, _ = build_sensitivity_scenarios(case)
    actual = dict(zip(summary["민감도 분석"], summary["끝수 처리 후 합계"], strict=True))

    assert actual["기준"] == Decimal("1250710930")
    assert actual["공시가격·시가표준액 5% 상승"] == Decimal("1313250630")
    assert actual["공시가격·시가표준액 10% 상승"] == Decimal("1375790350")


def test_public_tax_ui_has_exact_twenty_stage_order():
    source = (ROOT / "ui_tax_case_study.py").read_text(encoding="utf-8")
    titles = [
        "검토 결론",
        "검토대상 및 범위",
        "공모부동산투자회사 법적 지위",
        "소유·신탁 구조 및 재산세 납세의무자",
        "공모부동산투자회사 목적사업용 토지의 분리과세 적용요건",
        "법정 요건과 SK서린빌딩 사실관계 대조",
        "자산 소재지·필지고유번호(PNU) 및 공식 과세기초자료",
        "토지 시가표준액 및 토지분 재산세",
        "건축물 시가표준액 및 건축물분 재산세",
        "재산세 도시지역분 및 지방교육세",
        "소방분 지역자원시설세",
        "토지분 종합부동산세 및 농어촌특별세",
        "세목별 끝수 처리",
        "법정 산식에 따른 보유세 재계산",
        "보유세 민감도 분석",
        "주요 세무쟁점 및 추가 확인사항",
        "추가 요청자료 목록",
        "보유세 세무검토 메모",
        "과세근거자료 및 검토 한계",
        "검토자료 내려받기",
    ]
    render_source = source[source.index("def render_tax_mode") :]
    positions = [render_source.index(title) for title in titles]

    assert positions == sorted(positions)


def test_public_tax_download_names_are_korean():
    source = (ROOT / "ui_tax_case_study.py").read_text(encoding="utf-8")
    expected_suffixes = [
        "보유세계산내역.csv",
        "보유세민감도분석.csv",
        "주요세무쟁점.csv",
        "추가요청자료.csv",
        "세무검토팩.xlsx",
        "보유세세무검토.md",
        "보유세세무검토.html",
    ]

    assert 'safe_prefix = "395400_SK서린빌딩_2026"' in source
    assert all(suffix in source for suffix in expected_suffixes)


def test_primary_after_amount_has_no_decimal_suffix():
    from ui_tax_case_study import _format_decimal

    assert _format_decimal(Decimal("1250710930.000000")) == "1,250,710,930"
