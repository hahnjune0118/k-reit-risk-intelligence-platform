from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd

from marimo_ui import (
    format_eok,
    format_krw,
    html_table,
    load_css,
    metric_card,
    reconciliation_flow,
    source_ribbon,
    status_badge,
    workflow,
)

ROOT = Path(__file__).resolve().parents[1]


def test_amount_formatting_preserves_raw_decimal_precision():
    amount = Decimal("1250710968.55472")

    assert format_krw(amount, 5) == "1,250,710,968.55472원"
    assert format_eok(amount) == "약 12.51억원"


def test_status_badges_include_text_and_icon_not_color_only():
    confirmed = status_badge("official_source_calculated")
    unresolved = status_badge("not_reconciled")

    assert "✓" in confirmed
    assert "공식자료 재수행" in confirmed
    assert "!" in unresolved
    assert "미대사" in unresolved


def test_html_table_escapes_cells_and_allows_only_http_links():
    frame = pd.DataFrame(
        [
            {
                "fact": "<script>alert(1)</script>",
                "source": "javascript:alert(1)",
            },
            {
                "fact": "공식 원문",
                "source": "https://example.com/evidence?a=1&b=2",
            },
        ]
    )

    rendered = html_table(frame, link_columns=["source"])

    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert 'href="javascript:' not in rendered
    assert 'href="https://example.com/evidence?a=1&amp;b=2"' in rendered
    assert '<th scope="col">' in rendered
    assert '<caption class="sr-only">' in rendered
    assert 'tabindex="0"' in rendered
    assert 'aria-label="source 원문 열기:' in rendered


def test_responsive_css_has_mobile_breakpoints_and_scrollable_tables():
    css = load_css()

    assert "@media (max-width: 760px)" in css
    assert "@media (max-width: 430px)" in css
    assert ".table-wrap" in css
    assert "overflow-x: auto" in css
    assert ".recon-flow" in css
    assert ".table-wrap:focus-visible" in css
    assert ".sr-only" in css
    assert "--audit-muted: #475569" in css
    assert "!important" not in css
    assert "-webkit-text-fill-color" not in css


def test_readability_components_have_explicit_semantic_hooks():
    source = source_ribbon(
        status="official_source_calculated",
        detail="저장 시점 자료 기반",
        retrieved_at="2026-07-15",
    )
    metric = metric_card("실제 고지세액", "미확인", note="고지서 미수령", severity="critical")
    flow = reconciliation_flow("1,250,710,968원")

    assert 'class="source-detail"' in source
    assert 'class="source-time-value"' in source
    assert 'class="metric-card-header"' in metric
    assert 'class="metric-status"' in metric
    assert "실제 고지서가 확보되지 않아" in flow
    assert 'class="workflow-step is-active"' in workflow(2)


def test_notebook_preserves_active_tab_and_wraps_mobile_hstacks():
    source = (ROOT / "k_reits_marimo.py").read_text(encoding="utf-8")

    assert 'mo.state("1. 종합 위험 및 시나리오")' in source
    assert "value=get_active_tab()" in source
    assert "on_change=set_active_tab" in source
    assert source.count("wrap=True") >= 3
    assert source.count("show_value=True") >= 8
    assert source.count("include_input=True") >= 8
    assert "2. 감사위험 및 보유세 재계산" in source
    assert "3. 감사증거·고지서 대사 및 결론" in source


def test_dense_dashboard_css_preserves_contrast_and_responsive_stack():
    css = load_css()

    assert len(css.encode("utf-8")) > 0
    assert ".app-shell" in css
    assert ".dense-header" in css
    assert "linear-gradient(120deg, #0c263f" in css
    assert ".dense-title-row h1" in css
    assert ".dense-panel" in css
    assert ".dense-metric" in css
    assert ".dense-metric-grid" in css
    assert ".dashboard-grid" in css
    assert ".audit-table" in css
    assert "grid-template-columns: repeat(3" in css
    assert "@media (max-width: 1250px)" in css
    assert "@media (max-width: 760px)" in css
