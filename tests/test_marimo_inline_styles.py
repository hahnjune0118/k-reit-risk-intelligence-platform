from __future__ import annotations

import ast
import re
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

import marimo_ui
from marimo_ui import (
    callout,
    chip,
    columns,
    compact_header,
    dense_metric,
    dense_metric_grid,
    html_table,
    mini_stat,
    panel,
    reconciliation_flow,
    section_heading,
    source_ribbon,
    status_badge,
    workflow,
)

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "k_reits_marimo.py"


class _StyleCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.styles: list[str] = []
        self.malformed_attributes: list[str] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.malformed_attributes.extend(name for name, value in attrs if value is None)
        style = dict(attrs).get("style")
        if style:
            self.styles.append(style.replace(" ", "").lower())


def _all_components() -> dict[str, str]:
    table = pd.DataFrame([{"항목": "공식자료", "상태": "confirmed"}])
    return {
        "compact_header": compact_header(
            title="종합 위험 및 시나리오",
            subtitle="재무·자산 위험을 비교합니다.",
            metadata=["SK리츠", "2026 과세연도"],
            source_status="official_source_calculated",
            source_detail="검증 저장 시점 자료",
            retrieved_at="2026-07-15",
        ),
        "dense_metric": dense_metric("종합 위험도", "56.5 · Medium"),
        "dense_metric_grid": dense_metric_grid([dense_metric("FFO", "123억원")]),
        "mini_stat": mini_stat("고지서 대사율", "0%", "미대사", "critical"),
        "status_badge": status_badge("not_reconciled"),
        "chip": chip("과세연도 2026년"),
        "panel": panel("판단 근거", "<p>공식자료를 재수행했습니다.</p>"),
        "columns": columns([panel("A", "본문"), panel("B", "본문")]),
        "callout": callout("warning", "주의", "추가 감사증거가 필요합니다."),
        "html_table": html_table(table, status_columns=["상태"]),
        "reconciliation_flow": reconciliation_flow("1,250,710,968원"),
        "workflow": workflow(2),
        "source_ribbon": source_ribbon(
            status="official_source_calculated",
            detail="검증 저장 시점 자료",
            retrieved_at="2026-07-15",
        ),
        "section_heading": section_heading(
            "핵심 검토 결과", kicker="01 · 위험 식별", description="감사검토 결과"
        ),
    }


def test_marimo_app_has_no_css_file_argument():
    source = NOTEBOOK.read_text(encoding="utf-8")
    tree = ast.parse(source)
    app_call = next(
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "app"
            for target in node.targets
        )
    )

    assert all(keyword.arg != "css_file" for keyword in app_call.keywords)
    assert "<style>" not in source


def test_helpers_render_without_optional_stylesheet(tmp_path, monkeypatch):
    monkeypatch.setattr(marimo_ui, "STYLE_PATH", tmp_path / "missing.css")

    assert marimo_ui.load_css() == ""
    for name, rendered in _all_components().items():
        assert rendered.strip(), name
        assert 'style="' in rendered, name


def test_key_helpers_emit_inline_visual_hierarchy():
    for name, rendered in _all_components().items():
        normalized = rendered.lower().replace(" ", "")
        assert "color:" in normalized, name
        assert "font-size:" in normalized, name
        assert any(
            property_name in normalized
            for property_name in ("background:", "border:", "display:")
        ), name

    grid = dense_metric_grid([dense_metric("검토", "정상")]).replace(" ", "")
    assert "display:grid" in grid
    assert "repeat(auto-fit,minmax(" in grid

    table = html_table(pd.DataFrame([{"항목": "값"}])).replace(" ", "")
    assert "overflow-x:auto" in table
    assert "min-width:720px" in table


def test_helper_inputs_remain_html_escaped():
    payload = '<script>alert("x")</script>'

    rendered = "".join(
        [
            chip(payload),
            dense_metric(payload, payload, baseline=payload, delta=payload),
            mini_stat(payload, payload, payload),
            callout("neutral", payload, payload),
            section_heading(payload, kicker=payload, description=payload),
        ]
    )

    assert "<script>" not in rendered
    assert rendered.count("&lt;script&gt;") >= 5


def test_white_cards_never_set_white_text_on_same_element():
    parser = _StyleCollector()
    parser.feed("".join(_all_components().values()))

    assert parser.malformed_attributes == []
    for style in parser.styles:
        has_white_background = bool(
            re.search(r"background(?:-color)?:#(?:fff|ffffff)(?:;|$)", style)
        )
        has_white_text = bool(re.search(r"color:#(?:fff|ffffff)(?:;|$)", style))
        assert not (has_white_background and has_white_text), style
