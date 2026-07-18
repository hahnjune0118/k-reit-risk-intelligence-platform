import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = (
    "README.md",
    "CHANGELOG.md",
    "PROJECT_ROADMAP.md",
    "config.py",
    "ui_tax_decision_first.py",
    "docs/Reviewer_Guide.md",
    "docs/BUSINESS_PROCESS_CASE_BRIEF.md",
    "docs/BUSINESS_REQUIREMENTS_DEFINITION.md",
)


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_v15_version_is_consistent_across_public_docs_and_config():
    version = "v15.1.0"
    title = "Decision-First Tax Review"
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


def test_business_documents_are_linked_and_complete():
    readme = _read("README.md")
    process_brief = _read("docs/BUSINESS_PROCESS_CASE_BRIEF.md")
    requirements = _read("docs/BUSINESS_REQUIREMENTS_DEFINITION.md")

    assert "docs/BUSINESS_PROCESS_CASE_BRIEF.md" in readme
    assert "docs/BUSINESS_REQUIREMENTS_DEFINITION.md" in readme
    for phrase in (
        "As-Is Workflow",
        "To-Be Workflow",
        "검증 통제와 예외처리",
        "전문가 검토 경계",
        "구현 범위",
        "한계와 향후 개선",
    ):
        assert phrase in process_brief
    for phrase in (
        "기능요건",
        "데이터요건",
        "검증 통제요건",
        "예외처리",
        "전문가 검토 경계",
        "제외범위",
    ):
        assert phrase in requirements


def test_public_files_use_firm_neutral_language():
    public_text = "\n".join(_read(path) for path in PUBLIC_FILES)
    forbidden_patterns = (
        r"\bAX\b",
        r"\bPwC\b",
        r"\bSamil\b",
        r"\bDeloitte\b",
        r"\bKPMG\b",
        r"\bEY\b",
        r"삼일",
        r"안진",
        r"삼정",
        r"한영",
        r"채용전형",
        r"지원자",
        r"면접관",
    )

    for pattern in forbidden_patterns:
        assert re.search(pattern, public_text, flags=re.IGNORECASE) is None
