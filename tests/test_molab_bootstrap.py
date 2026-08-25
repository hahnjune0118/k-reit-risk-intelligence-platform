from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "k_reits_marimo.py"
LOCAL_MODULE_ROOTS = {"marimo_assurance", "marimo_risk", "marimo_ui", "src"}


def _static_import_roots(source: str) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_notebook_hides_repository_modules_from_static_package_inference():
    source = NOTEBOOK.read_text(encoding="utf-8")

    assert _static_import_roots(source).isdisjoint(LOCAL_MODULE_ROOTS)
    assert 'importlib.import_module("marimo_assurance")' in source
    assert 'importlib.import_module("marimo_risk")' in source
    assert 'importlib.import_module("marimo_ui")' in source
    assert 'importlib.import_module("src.tax_v15.reporting")' in source
    assert 'css_file="marimo_styles.css"' not in source
    assert 'load_css = _ui_module.load_css' in source
    assert 'id="k-reits-inline-styles"' in source
    assert 'f\'<style id="k-reits-inline-styles">{_css_text}</style>\'' in source

    tree = ast.parse(source)
    app_call = next(
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "app" for target in node.targets)
    )
    assert all(keyword.arg != "css_file" for keyword in app_call.keywords)


def test_molab_archive_fallback_is_bounded_and_path_checked():
    source = NOTEBOOK.read_text(encoding="utf-8")

    assert "https://codeload.github.com/{_repository}/zip/{_ref}" in source
    assert "_maximum_archive_bytes = 50 * 1024 * 1024" in source
    assert "stat.S_ISLNK(_mode)" in source
    assert "_extract_root not in _destination.parents" in source
    assert '"main"' in source
    assert '"aed3f0f39bb68f1bd4e0eb2ea4f38884d82931b5"' in source
    assert 'Path("marimo_styles.css")' in source
    assert "_css_is_valid(_candidate)" in source


def test_notebook_loads_css_modules_and_snapshots_outside_repository_cwd(tmp_path):
    script = f"""
import runpy
import sys

namespace = runpy.run_path({str(NOTEBOOK)!r}, run_name="molab_smoke")
risk_snapshot = namespace["load_risk_snapshot"]()
assurance_snapshot = namespace["load_assurance_snapshot"]()
assurance_view = namespace["build_view_model_from_snapshot"](assurance_snapshot)
assert risk_snapshot.reit_master.shape[0] > 0
assert assurance_view.kpis["p0_open"] == 3
assert assurance_view.kpis["p1_open"] == 3
assert namespace["app"]._config.css_file is None
assert namespace["_ui_module"].load_css().strip()
assert "src.tax_v15.reporting" in sys.modules
print(assurance_view.base_total)
"""

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )

    assert completed.returncode == 0, completed.stderr
    assert "1250710968.55472" in completed.stdout


def test_exported_notebook_contains_verified_inline_styles(tmp_path):
    exported = tmp_path / "k_reits_rendered.html"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "marimo",
            "export",
            "html",
            str(NOTEBOOK),
            "-o",
            str(exported),
            "--no-include-code",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )

    assert completed.returncode == 0, completed.stderr
    rendered = exported.read_text(encoding="utf-8")
    assert 'id=\\"k-reits-inline-styles\\"' in rendered
    assert ".dense-header" in rendered
    assert "linear-gradient(120deg, #0c263f" in rendered


def test_missing_repository_files_raise_safe_diagnostic(tmp_path):
    isolated_notebook = tmp_path / NOTEBOOK.name
    shutil.copy2(NOTEBOOK, isolated_notebook)
    script = f"""
import runpy

try:
    runpy.run_path({str(isolated_notebook)!r}, run_name="molab_missing_repo")
except RuntimeError as error:
    print(str(error))
else:
    raise AssertionError("repository bootstrap unexpectedly succeeded")
"""

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert "저장소 root 발견 여부: 아니요" in completed.stdout
    assert "marimo_assurance.py" in completed.stdout
    assert "src/tax_v15" in completed.stdout
    assert "data/v15" in completed.stdout
    assert "marimo_styles.css" in completed.stdout
    assert "사용자 정의 CSS 발견·검증 여부: 아니요" in completed.stdout
    assert "GitHub mirror" in completed.stdout
    assert str(Path.home()) not in completed.stdout
