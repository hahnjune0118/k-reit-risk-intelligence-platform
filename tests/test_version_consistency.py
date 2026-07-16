from decimal import Decimal
from pathlib import Path

from src.tax_v15.case_study import (
    GOLDEN_RECALCULATION_RAW,
    build_sensitivity_scenarios,
    select_golden_case,
)
from src.tax_v15.loaders import load_v15_bundle


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_AX_FILES = (
    "ui_general.py",
    "README.md",
    "docs/Reviewer_Guide.md",
    "docs/AX_ADVISORY_CASE_BRIEF.md",
    "docs/AX_REQUIREMENTS_DEFINITION.md",
)


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def _public_ax_text() -> str:
    return "\n".join(_read(path) for path in PUBLIC_AX_FILES)


def test_general_ui_contains_ax_overview():
    ui = _read("ui_general.py")
    render_body = ui.split("def render_general_dashboard(", maxsplit=1)[1]

    assert "AX 적용 개요 — 공시·세무검토 Workflow 재설계" in ui
    assert render_body.index("_render_ax_advisory_overview()") < render_body.index(
        'st.markdown("## 1. 한눈에 보는 결론")'
    )


def test_general_ui_contains_pain_point_solution_and_effect():
    ui = _read("ui_general.py")

    assert "고객 Pain Point" in ui
    assert "AX Solution" in ui
    assert "업무효과" in ui


def test_general_ui_contains_as_is_and_to_be_workflow():
    ui = _read("ui_general.py")

    assert "As-Is·To-Be Workflow" in ui
    assert "공시 PDF 검색" in ui
    assert "공식자료 수집" in ui
    assert "전문가 승인" in ui


def test_general_ui_contains_ax_role_boundaries():
    ui = _read("ui_general.py")

    for role in (
        "Data",
        "Automation",
        "AI 지원영역",
        "Control Harness",
        "Human Review",
    ):
        assert role in ui


def test_general_ui_contains_control_harness_terms():
    ui = _read("ui_general.py")

    assert "Fail-closed" in ui
    assert "Source Grounding" in ui
    assert "회귀테스트" in ui


def test_public_copy_does_not_claim_active_generative_ai_runtime():
    public_text = _public_ax_text()

    assert "공개 Runtime의 세액 계산은 재현 가능한 규칙엔진" in public_text
    assert "생성형 AI Runtime 운영 중" not in public_text
    assert "LLM API 연결 완료" not in public_text
    assert "생성형 AI가 세법 판단을 자동 완료합니다" not in public_text


def test_public_copy_is_neutral_and_not_recruitment_targeted():
    public_text = _public_ax_text()

    for phrase in (
        "회계법인 지원",
        "채용전형",
        "지원자명",
        "면접관",
        "자기소개서",
    ):
        assert phrase not in public_text


def test_existing_tax_base_calculation_is_unchanged():
    case = select_golden_case(load_v15_bundle())
    scenarios, _ = build_sensitivity_scenarios(case)
    base_total = scenarios.loc[
        scenarios["Scenario"].eq("Base"), "총 보유세"
    ].iloc[0]

    assert GOLDEN_RECALCULATION_RAW == Decimal("1250710968.55472")
    assert base_total == GOLDEN_RECALCULATION_RAW


def test_existing_assurance_entrypoint_remains_active():
    assurance = _read("ui_assurance.py")
    app = _read("app.py")
    professional = _read("ui_professional.py")

    assert "def render_assurance_mode(" in assurance
    assert "render_professional_page(" in app
    assert "render_assurance_mode(" in professional
    assert "RMM" in assurance
    assert "KAM" in assurance


def test_v15_version_is_consistent_across_public_docs_and_config():
    version = "v15.1.0"
    title = "AX Workflow & Advisory Portfolio"
    release_label = f"{version} - {title}"

    assert _read("VERSION").strip() == version

    readme = _read("README.md")
    reviewer_guide = _read("docs/Reviewer_Guide.md")
    changelog = _read("CHANGELOG.md")
    roadmap = _read("PROJECT_ROADMAP.md")
    config = _read("config.py")

    assert version in readme
    assert title in readme
    assert release_label in reviewer_guide
    assert release_label in changelog
    assert release_label in roadmap
    assert f'APP_VERSION = "{version}"' in config
    assert f'APP_VERSION_NAME = "{title}"' in config


def test_public_modes_are_unchanged():
    config = _read("config.py")

    for mode in (
        "일반 정보 및 시나리오",
        "Assurance: 감사위험 분석",
        "Tax: 보유세 분석",
        "분석 방법론 및 데이터 출처",
    ):
        assert mode in config

    assert '"Deals":' not in config
