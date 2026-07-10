import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_public_modes_only_include_active_four_modes():
    tree = ast.parse(_read("ui_layout.py"))
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign) and node.targets[0].id == "PUBLIC_MODES")
    modes = [item.value for item in assignment.value.elts]

    assert modes == [
        "General Info & Scenario",
        "Tax",
        "Assurance",
        "Methodology & Data Sources",
    ]
    assert all("Deals" not in mode and "KRX" not in mode for mode in modes)


def test_public_streamlit_ui_has_no_unconditional_auth_value_inputs():
    sidebar = _read("ui_sidebar.py")
    tax_ui = _read("ui_tax.py")
    methodology = _read("ui_methodology.py")

    assert "SHOW_DEVELOPER_API_INPUTS" in sidebar
    assert "개발자 설정: 외부 데이터 인증값" in sidebar
    assert "st.text_input" not in tax_ui
    assert "st.text_input" not in methodology
    assert "API Key" not in tax_ui
    assert "API Key" not in methodology
    assert "secrets" not in tax_ui.lower()
    assert "secrets" not in methodology.lower()


def test_public_runtime_does_not_import_archived_deals_or_krx_ui():
    app = _read("app.py")
    professional = _read("ui_professional.py")
    layout = _read("ui_layout.py")
    active_text = "\n".join([app, professional, layout])

    assert "ui_deals" not in active_text
    assert "render_deals" not in active_text
    assert "api_krx" not in active_text
