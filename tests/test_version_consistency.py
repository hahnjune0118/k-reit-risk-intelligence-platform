from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_v15_version_is_consistent_across_public_docs_and_config():
    version = "v15.0.1"
    title = "SK서린빌딩 핵심 자산 보유세 세무검토"
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
