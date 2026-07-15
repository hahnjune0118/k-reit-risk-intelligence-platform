from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_v15_version_is_consistent_across_public_docs_and_config():
    assert _read("VERSION").strip() == "v15.0.0"

    readme = _read("README.md")
    reviewer_guide = _read("docs/Reviewer_Guide.md")
    changelog = _read("CHANGELOG.md")
    roadmap = _read("PROJECT_ROADMAP.md")
    config = _read("config.py")

    assert "v15.0.0" in readme
    assert "Asset & Taxpayer-Level Holding Tax" in readme
    assert "v15" in reviewer_guide
    assert "v15.0.0 - Asset & Taxpayer-Level Holding Tax" in changelog
    assert "v15.0.0 - Asset & Taxpayer-Level Holding Tax" in roadmap
    assert 'APP_VERSION = "v15.0.0"' in config
    assert "Asset & Taxpayer-Level Holding Tax" in config
