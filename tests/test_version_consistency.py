from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_v14_version_is_consistent_across_public_docs_and_config():
    assert _read("VERSION").strip() == "v14"

    readme = _read("README.md")
    reviewer_guide = _read("docs/Reviewer_Guide.md")
    changelog = _read("CHANGELOG.md")
    roadmap = _read("PROJECT_ROADMAP.md")
    config = _read("config.py")

    assert "v14" in readme
    assert "Tax Workflow Control & Validation" in readme
    assert "v14" in reviewer_guide
    assert "v14 - Tax Workflow Control & Validation" in changelog
    assert "현재" in changelog.splitlines()[2]
    assert "v14 - Tax Workflow Control & Validation" in roadmap
    assert 'APP_VERSION = "v14"' in config
    assert "Tax Workflow Control & Validation" in config
