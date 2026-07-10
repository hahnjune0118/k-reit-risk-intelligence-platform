from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_v13_version_is_consistent_across_public_docs_and_config():
    assert _read("VERSION").strip() == "v13"

    readme = _read("README.md")
    reviewer_guide = _read("docs/Reviewer_Guide.md")
    changelog = _read("CHANGELOG.md")
    roadmap = _read("PROJECT_ROADMAP.md")
    config = _read("config.py")

    assert "v13" in readme
    assert "Tax Review Pack" in readme
    assert "v13" in reviewer_guide
    assert "v13 - Tax Review Pack Generator" in changelog
    assert "현재" in changelog.splitlines()[2]
    assert "v13 - Tax Review Pack Generator" in roadmap
    assert 'APP_VERSION = "v13"' in config
    assert "Tax Review Pack" in config
