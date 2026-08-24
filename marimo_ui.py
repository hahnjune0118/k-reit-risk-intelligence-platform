from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal
from html import escape
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
STYLE_PATH = PROJECT_ROOT / "marimo_styles.css"

# Inline styles are the rendering source of truth because Molab mirrors only the
# notebook file.  marimo_styles.css remains an optional local enhancement.
COLORS = {
    "title": "#0B2440",
    "value": "#082B52",
    "body": "#172033",
    "label": "#334155",
    "muted": "#475569",
    "meta": "#526274",
    "border": "#CBD5E1",
    "card": "#FFFFFF",
    "card_alt": "#F1F5F9",
    "blue_bg": "#E7F0F8",
    "navy": "#123B63",
    "teal": "#0B6267",
    "green": "#116149",
    "green_bg": "#E5F4EB",
    "green_border": "#9BC9AE",
    "amber": "#8A5200",
    "amber_bg": "#FFF0CC",
    "amber_border": "#D8B767",
    "red": "#9F2D35",
    "red_bg": "#FDE8E9",
    "red_border": "#DFA5A9",
}
FONT_FAMILY = (
    "Inter, Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif"
)
SHADOW = "0 4px 14px rgba(15, 39, 66, 0.08)"

STATUS_LABELS = {
    "confirmed": ("✓", "확인됨", "confirmed"),
    "verified_notice": ("✓", "고지서 확인", "confirmed"),
    "official_source_calculated": ("✓", "공식자료 재수행", "confirmed"),
    "official_verified": ("✓", "공식 근거 확인", "confirmed"),
    "estimated": ("△", "추정됨", "estimated"),
    "official_partial": ("△", "공식자료 일부", "estimated"),
    "manual_review_required": ("!", "추가 검토 필요", "estimated"),
    "public_disclosure_continuity_supported_registry_unverified": (
        "!",
        "공시 연속성 확인·등기 미확인",
        "estimated",
    ),
    "statutory_basis_verified_notice_code_open": (
        "!",
        "법령 근거 확인·고지 코드 미확인",
        "estimated",
    ),
    "unverified": ("?", "미확인", "unverified"),
    "not_reconciled": ("!", "미대사", "unverified"),
    "data_insufficient": ("!", "근거 부족", "unverified"),
    "open": ("!", "미해결", "unverified"),
    "not_reflected": ("!", "미반영", "unverified"),
    "not_applicable": ("—", "해당 없음", "neutral"),
}


def _style(**declarations: str) -> str:
    """Build deterministic inline CSS from trusted design tokens."""
    return "; ".join(
        f"{name.replace('_', '-')}: {value}" for name, value in declarations.items()
    )


def _base(**extra: str) -> str:
    declarations = {
        "box_sizing": "border-box",
        "color": COLORS["body"],
        "font_family": FONT_FAMILY,
        "line_height": "1.55",
    }
    declarations.update(extra)
    return _style(**declarations)


def _border(color: str) -> str:
    return f"1px solid {color}"


def _severity_palette(severity: str) -> tuple[str, str, str]:
    return {
        "ok": (COLORS["green"], COLORS["green_bg"], COLORS["green_border"]),
        "confirmed": (
            COLORS["green"],
            COLORS["green_bg"],
            COLORS["green_border"],
        ),
        "warning": (
            COLORS["amber"],
            COLORS["amber_bg"],
            COLORS["amber_border"],
        ),
        "estimated": (
            COLORS["amber"],
            COLORS["amber_bg"],
            COLORS["amber_border"],
        ),
        "critical": (COLORS["red"], COLORS["red_bg"], COLORS["red_border"]),
        "unverified": (
            COLORS["red"],
            COLORS["red_bg"],
            COLORS["red_border"],
        ),
    }.get(severity, (COLORS["title"], COLORS["blue_bg"], COLORS["border"]))


def load_css() -> str:
    """Return optional local CSS; helper rendering never requires this file."""
    try:
        return STYLE_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def safe_text(value, fallback: str = "—") -> str:
    if value is None or value is pd.NA:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text if text else fallback


def format_krw(value, decimals: int = 0) -> str:
    try:
        amount = Decimal(str(value))
    except (ArithmeticError, TypeError, ValueError):
        return "미확인"
    return f"{amount:,.{decimals}f}원"


def format_eok(value) -> str:
    try:
        amount = Decimal(str(value)) / Decimal(100000000)
    except (ArithmeticError, TypeError, ValueError):
        return "미확인"
    return f"약 {amount:,.2f}억원"


def format_percent(value, decimals: int = 1) -> str:
    try:
        number = Decimal(str(value))
    except (ArithmeticError, TypeError, ValueError):
        return "—"
    return f"{number:,.{decimals}f}%"


def status_badge(status: str, label: str | None = None) -> str:
    icon, default_label, semantic = STATUS_LABELS.get(
        str(status).strip().lower(), ("•", safe_text(status), "neutral")
    )
    color, background, border = _severity_palette(semantic)
    badge_style = _base(
        display="inline-flex",
        align_items="center",
        gap="5px",
        margin="2px 4px 2px 0",
        padding="5px 9px",
        border=_border(border),
        border_radius="999px",
        background=background,
        color=color,
        font_size="13px",
        font_weight="800",
        line_height="1.25",
        white_space="nowrap",
    )
    return (
        f'<span class="status-badge {semantic}" style="{badge_style}">'
        f'<span aria-hidden="true">{escape(icon)}</span>{escape(label or default_label)}</span>'
    )


def chip(label: str) -> str:
    style = _base(
        display="inline-flex",
        align_items="center",
        padding="5px 9px",
        border=_border(COLORS["border"]),
        border_radius="999px",
        background=COLORS["blue_bg"],
        color=COLORS["title"],
        font_size="13px",
        font_weight="800",
        line_height="1.25",
    )
    return f'<span class="chip" style="{style}">{escape(label)}</span>'


def hero(*, title: str, kicker: str, metadata: Iterable[str]) -> str:
    meta_style = _style(
        display="inline-flex",
        padding="6px 10px",
        border="1px solid rgba(255,255,255,0.45)",
        border_radius="999px",
        background="rgba(8,30,49,0.38)",
        color="#FFFFFF",
        font_size="14px",
        font_weight="700",
    )
    meta = "".join(
        f'<span style="{meta_style}">{escape(item)}</span>' for item in metadata
    )
    shell_style = _base(width="100%", min_width="0")
    hero_style = _base(
        position="relative",
        overflow="hidden",
        padding="28px",
        border="1px solid #255A72",
        border_radius="18px",
        background="linear-gradient(125deg, #0C263F 0%, #143E60 58%, #0E6268 100%)",
        box_shadow="0 10px 28px rgba(15,39,66,0.16)",
    )
    return (
        f'<div class="app-shell" style="{shell_style}">'
        f'<section class="assurance-hero" style="{hero_style}">'
        f'<p class="hero-kicker" style="{_style(margin="0 0 8px", color="#C7F0F1", font_size="15px", font_weight="800")}">{escape(kicker)}</p>'
        f'<h1 style="{_style(margin="0", color="#FFFFFF", font_size="clamp(27px, 3vw, 40px)", font_weight="800", line_height="1.25")}">{escape(title)}</h1>'
        f'<div class="hero-meta" style="{_style(display="flex", flex_wrap="wrap", gap="9px", margin_top="18px")}">{meta}</div>'
        "</section></div>"
    )


def compact_header(
    *,
    title: str,
    subtitle: str,
    metadata: Iterable[str],
    source_status: str,
    source_detail: str,
    retrieved_at: str,
) -> str:
    """Render the shared header with no external stylesheet dependency."""
    meta_style = _style(
        padding="5px 9px",
        border="1px solid rgba(255,255,255,0.46)",
        border_radius="999px",
        background="rgba(8,30,49,0.38)",
        color="#FFFFFF",
        font_size="13px",
        font_weight="750",
    )
    meta = "".join(
        f'<span style="{meta_style}">{escape(item)}</span>' for item in metadata
    )
    shell_style = _base(
        width="100%",
        min_width="0",
        margin="0 0 12px",
        border="1px solid #255A72",
        border_radius="14px",
        background="linear-gradient(120deg, #0C263F 0%, #143E60 62%, #0E6268 100%)",
        box_shadow="0 6px 18px rgba(15,39,66,0.14)",
        overflow="hidden",
    )
    title_row_style = _style(
        display="flex",
        flex_wrap="wrap",
        min_height="92px",
        align_items="center",
        justify_content="space-between",
        gap="16px",
        padding="14px 18px",
        border_top="5px solid #41A4A8",
    )
    workflow_style = _style(
        display="flex",
        align_items="center",
        flex_wrap="wrap",
        gap="8px",
        min_height="42px",
        padding="8px 16px",
        border_top=_border(COLORS["border"]),
        background=COLORS["card"],
        color=COLORS["title"],
    )
    source_style = _style(
        display="flex",
        align_items="center",
        flex_wrap="wrap",
        gap="8px",
        min_height="44px",
        padding="8px 16px",
        border_top=_border(COLORS["border"]),
        background=COLORS["blue_bg"],
        color=COLORS["muted"],
        font_size="14px",
    )
    item_style = _style(color=COLORS["title"], font_size="14px", font_weight="750")
    arrow = f'<b style="{_style(color=COLORS["teal"])}">→</b>'
    return (
        f'<div class="app-shell dense-header" style="{shell_style}">'
        f'<div class="dense-title-row" style="{title_row_style}">'
        f'<div style="{_style(flex="1 1 420px", min_width="0")}">'
        f'<h1 style="{_style(margin="0", color="#FFFFFF", font_size="clamp(27px, 2.3vw, 36px)", font_weight="800", line_height="1.25")}">{escape(title)}</h1>'
        f'<p style="{_style(margin="5px 0 0", color="#DCE7F0", font_size="15px", line_height="1.5")}">{escape(subtitle)}</p></div>'
        f'<div class="dense-meta" style="{_style(display="flex", flex="1 1 320px", flex_wrap="wrap", justify_content="flex-end", gap="6px")}">{meta}</div></div>'
        f'<div class="compact-workflow" aria-label="감사검토 절차" style="{workflow_style}">'
        f'<span style="{item_style}">위험 식별</span>{arrow}'
        f'<span style="{item_style}">감사증거 검증·독립적 재계산</span>{arrow}'
        f'<span style="{item_style}">고지서 대사·예외 후속조치</span>{arrow}'
        f'<span style="{item_style}">검토자 결론</span></div>'
        f'<div class="compact-source" style="{source_style}">{status_badge(source_status)}'
        f'<span style="{_style(color=COLORS["muted"], font_size="14px", line_height="1.5")}">{escape(source_detail)}</span>'
        f'<span class="compact-source-time" style="{_style(margin_left="auto", color=COLORS["meta"], font_size="14px", font_weight="750")}">자료 기준 {escape(retrieved_at)}</span>'
        "</div></div>"
    )


def dense_metric(
    label: str,
    value: str,
    *,
    baseline: str = "",
    delta: str = "",
    severity: str = "neutral",
) -> str:
    color, background, border = _severity_palette(severity)
    card_style = _base(
        display="flex",
        min_width="0",
        min_height="132px",
        flex_direction="column",
        padding="13px",
        border=_border(COLORS["border"]),
        border_top=f"4px solid {border}",
        border_radius="10px",
        background=background if severity != "neutral" else COLORS["card"],
    )
    return (
        f'<article class="dense-metric status-{escape(severity)}" style="{card_style}">'
        f'<span class="dense-metric-label" style="{_style(color=COLORS["label"], font_size="15px", font_weight="700", line_height="1.4")}">{escape(label)}</span>'
        f'<strong style="{_style(margin="6px 0", color=COLORS["value"], font_size="28px", font_weight="800", line_height="1.2", overflow_wrap="anywhere")}">{escape(value)}</strong>'
        f'<div class="dense-metric-meta" style="{_style(display="flex", flex_wrap="wrap", margin_top="auto", justify_content="space-between", gap="6px", color=COLORS["meta"], font_size="14px", line_height="1.45")}">'
        f'<span style="{_style(color=COLORS["meta"])}">{escape(baseline)}</span>'
        f'<span style="{_style(color=color, font_weight="700")}">{escape(delta)}</span>'
        "</div></article>"
    )


def dense_metric_grid(cards: Iterable[str]) -> str:
    style = _base(
        display="grid",
        grid_template_columns="repeat(auto-fit, minmax(210px, 1fr))",
        gap="9px",
        min_width="0",
        max_width="calc(100vw - 48px)",
    )
    return f'<div class="dense-metric-grid" style="{style}">{"".join(cards)}</div>'


def mini_stat(label: str, value: str, note: str = "", severity: str = "neutral") -> str:
    _color, background, border = _severity_palette(severity)
    stat_style = _base(
        display="flex",
        min_width="0",
        min_height="112px",
        flex_direction="column",
        padding="12px",
        border=_border(COLORS["border"]),
        border_left=f"4px solid {border}",
        border_radius="9px",
        background=background if severity != "neutral" else COLORS["card_alt"],
    )
    return (
        f'<div class="mini-stat status-{escape(severity)}" style="{stat_style}">'
        f'<span style="{_style(color=COLORS["label"], font_size="14px", font_weight="750")}">{escape(label)}</span>'
        f'<strong style="{_style(margin="3px 0", color=COLORS["value"], font_size="25px", font_weight="800", line_height="1.3", overflow_wrap="anywhere")}">{escape(value)}</strong>'
        f'<small style="{_style(margin_top="auto", color=COLORS["meta"], font_size="14px", line_height="1.45")}">{escape(note)}</small></div>'
    )


def mini_stat_grid(cards: Iterable[str]) -> str:
    style = _base(
        display="grid",
        grid_template_columns="repeat(auto-fit, minmax(190px, 1fr))",
        gap="8px",
        min_width="0",
        max_width="calc(100vw - 48px)",
    )
    return f'<div class="mini-stat-grid" style="{style}">{"".join(cards)}</div>'


def source_ribbon(*, status: str, detail: str, retrieved_at: str) -> str:
    ribbon_style = _base(
        display="flex",
        align_items="center",
        justify_content="space-between",
        flex_wrap="wrap",
        gap="14px",
        width="100%",
        margin="14px 0 16px",
        padding="14px 16px",
        border=_border(COLORS["border"]),
        border_radius="12px",
        background=COLORS["blue_bg"],
        box_shadow=SHADOW,
    )
    return (
        f'<section class="app-shell source-ribbon" aria-label="데이터 출처 및 계보" style="{ribbon_style}">'
        f'<div class="source-provenance" style="{_style(display="flex", min_width="0", align_items="center", flex_wrap="wrap", gap="8px")}">'
        f'<strong class="source-title" style="{_style(color=COLORS["title"], font_size="15px", font_weight="800")}">데이터 출처 및 계보</strong>'
        f'{status_badge(status)}<span class="source-detail" style="{_style(color=COLORS["muted"], font_size="15px", line_height="1.55")}">{escape(detail)}</span></div>'
        f'<div class="source-timestamp" style="{_style(display="flex", align_items="baseline", flex_wrap="wrap", gap="7px")}">'
        f'<strong class="source-time-label" style="{_style(color=COLORS["title"], font_size="14px", font_weight="800")}">자료 기준 일시</strong>'
        f'<span class="source-time-value" style="{_style(color=COLORS["meta"], font_size="14px", font_weight="650")}">{escape(retrieved_at)}</span></div></section>'
    )


def workflow(active_step: int) -> str:
    steps = [
        ("01", "위험 식별"),
        ("02", "감사증거 검증 및 독립적 재계산"),
        ("03", "고지서 대사 및 예외 후속조치"),
        ("04", "검토자 결론"),
    ]
    items: list[str] = []
    for number, label in steps:
        active = int(number) == active_step
        step_style = _base(
            display="flex",
            min_width="0",
            min_height="108px",
            flex_direction="column",
            align_items="flex-start",
            gap="9px",
            padding="15px",
            border=_border("#7FA6B7" if active else COLORS["border"]),
            border_left=f'5px solid {COLORS["teal"]}',
            border_radius="12px",
            background="#DCEAF0" if active else COLORS["card_alt"],
            box_shadow=SHADOW,
        )
        number_style = _style(
            display="inline-flex",
            padding="5px 8px",
            border_radius="999px",
            background=COLORS["teal"],
            color="#FFFFFF",
            font_size="13px",
            font_weight="800",
        )
        items.append(
            f'<div class="workflow-step{" is-active" if active else ""}" style="{step_style}">'
            f'<span class="step-no" style="{number_style}">{number}단계</span>'
            f'<strong style="{_style(color=COLORS["title"], font_size="16px", font_weight="800", line_height="1.45")}">{escape(label)}</strong></div>'
        )
    grid_style = _base(
        display="grid",
        grid_template_columns="repeat(auto-fit, minmax(220px, 1fr))",
        gap="12px",
        width="100%",
        margin="16px 0 20px",
    )
    return f'<div class="app-shell workflow" style="{grid_style}">{"".join(items)}</div>'


def metric_card(
    label: str,
    value: str,
    *,
    note: str = "",
    severity: str = "neutral",
) -> str:
    severity_labels = {
        "ok": "확인",
        "critical": "미확인",
        "warning": "주의",
        "neutral": "정보",
    }
    color, background, border = _severity_palette(severity)
    card_style = _base(
        display="flex",
        min_width="0",
        min_height="172px",
        flex_direction="column",
        padding="18px",
        border=_border(COLORS["border"]),
        border_top=f"5px solid {border}",
        border_radius="14px",
        background=background if severity != "neutral" else COLORS["card"],
        box_shadow=SHADOW,
    )
    status_style = _style(
        padding="4px 8px",
        border=_border(border),
        border_radius="999px",
        background=background,
        color=color,
        font_size="13px",
        font_weight="800",
    )
    return (
        f'<article class="metric-card status-{escape(severity)}" style="{card_style}">'
        f'<div class="metric-card-header" style="{_style(display="flex", align_items="flex-start", justify_content="space-between", gap="10px")}">'
        f'<div class="metric-label" style="{_style(color=COLORS["label"], font_size="15px", font_weight="700", line_height="1.45")}">{escape(label)}</div>'
        f'<span class="metric-status" style="{status_style}">{escape(severity_labels.get(severity, "정보"))}</span></div>'
        f'<div class="metric-value" style="{_style(margin="8px 0 6px", color=COLORS["value"], font_size="30px", font_weight="800", line_height="1.25", overflow_wrap="anywhere")}">{escape(value)}</div>'
        f'<div class="metric-note" style="{_style(margin_top="auto", color=COLORS["meta"], font_size="14px", line_height="1.55")}">{escape(note)}</div></article>'
    )


def metric_grid(cards: Iterable[str]) -> str:
    style = _base(
        display="grid",
        grid_template_columns="repeat(auto-fit, minmax(240px, 1fr))",
        gap="14px",
        width="100%",
        margin="18px 0 22px",
    )
    return f'<div class="app-shell metric-grid" style="{style}">{"".join(cards)}</div>'


def section_heading(
    title: str,
    *,
    kicker: str,
    description: str = "",
) -> str:
    return (
        f'<header class="app-shell section-heading" style="{_base(display="block", width="100%", margin="26px 0 14px")}">'
        f'<p class="section-kicker" style="{_style(margin="0 0 5px", color=COLORS["teal"], font_size="14px", font_weight="800")}">{escape(kicker)}</p>'
        f'<h2 style="{_style(margin="0", color=COLORS["title"], font_size="clamp(24px, 2.2vw, 28px)", font_weight="800", line_height="1.35")}">{escape(title)}</h2>'
        f'<p class="section-description" style="{_style(max_width="860px", margin="8px 0 0", padding_left="12px", border_left="3px solid #9AB1C3", color=COLORS["muted"], font_size="15px", line_height="1.6")}">{escape(description)}</p></header>'
    )


def callout(kind: str, title: str, body: str) -> str:
    semantic = kind if kind in {"warning", "critical", "ok"} else "neutral"
    color, background, border = _severity_palette(semantic)
    body_color = color if semantic != "neutral" else COLORS["body"]
    callout_style = _base(
        width="100%",
        min_width="0",
        margin="12px 0",
        padding="14px 16px",
        border=_border(COLORS["border"]),
        border_left=f"6px solid {border}",
        border_radius="12px",
        background=background,
        box_shadow="0 3px 10px rgba(15,39,66,0.05)",
    )
    return (
        f'<div class="app-shell callout {escape(semantic)}" style="{callout_style}">'
        f'<strong style="{_style(display="block", margin_bottom="5px", color=color, font_size="15px", font_weight="800")}">{escape(title)}</strong>'
        f'<p style="{_style(margin="0", color=body_color, font_size="15px", line_height="1.6")}">{escape(body)}</p></div>'
    )


def panel(title: str, body_html: str) -> str:
    """Compose trusted helper-generated HTML inside a self-styled panel."""
    panel_style = _base(
        min_width="0",
        max_width="calc(100vw - 48px)",
        padding="17px",
        border=_border(COLORS["border"]),
        border_radius="14px",
        background=COLORS["card"],
        box_shadow=SHADOW,
    )
    return (
        f'<section class="panel" style="{panel_style}">'
        f'<h3 style="{_style(margin="0 0 10px", color=COLORS["title"], font_size="17px", font_weight="800", line_height="1.45")}">{escape(title)}</h3>'
        f'<div style="{_style(color=COLORS["body"], font_size="15px", line_height="1.65")}">{body_html}</div></section>'
    )


def dense_panel(title: str, body_html: str, *, subtitle: str = "") -> str:
    """Dense dashboard panel with an inline-styled title and trusted body."""
    subtitle_html = (
        f'<span style="{_style(color=COLORS["meta"], font_size="14px")}">{escape(subtitle)}</span>'
        if subtitle
        else ""
    )
    panel_style = _base(
        min_width="0",
        max_width="calc(100vw - 48px)",
        padding="14px",
        border=_border(COLORS["border"]),
        border_radius="12px",
        background=COLORS["card"],
        box_shadow="0 3px 11px rgba(15,39,66,0.06)",
    )
    return (
        f'<section class="dense-panel" style="{panel_style}">'
        f'<div class="dense-panel-title" style="{_style(display="flex", align_items="baseline", justify_content="space-between", flex_wrap="wrap", gap="9px", margin_bottom="9px")}">'
        f'<h2 style="{_style(margin="0", color=COLORS["title"], font_size="18px", font_weight="800", line_height="1.35")}">{escape(title)}</h2>{subtitle_html}</div>{body_html}</section>'
    )


def columns(panels: Iterable[str], count: int = 2) -> str:
    """Lay out trusted panel HTML using an inline responsive grid."""
    minimum = "260px" if count == 3 else "320px"
    style = _base(
        display="grid",
        grid_template_columns=f"repeat(auto-fit, minmax(min(100%, {minimum}), 1fr))",
        gap="14px",
        width="100%",
        min_width="0",
        max_width="calc(100vw - 48px)",
        margin="14px 0",
    )
    css_class = "three-col" if count == 3 else "two-col"
    return f'<div class="app-shell {css_class}" style="{style}">{"".join(panels)}</div>'


def bullet_list(items: Iterable[str]) -> str:
    list_style = _style(
        margin="7px 0 0", padding_left="20px", color=COLORS["body"], font_size="15px"
    )
    item_style = _style(margin="4px 0", color=COLORS["body"], line_height="1.6")
    return (
        f'<ul style="{list_style}">'
        + "".join(f'<li style="{item_style}">{escape(item)}</li>' for item in items)
        + "</ul>"
    )


def formula_box(formula: str) -> str:
    style = _base(
        margin="10px 0",
        padding="15px",
        border=_border(COLORS["border"]),
        border_radius="10px",
        background=COLORS["card_alt"],
        color=COLORS["body"],
        font_family="'Cascadia Code', Consolas, monospace",
        font_size="14px",
        white_space="pre-wrap",
    )
    return f'<div class="formula-box" style="{style}">{escape(formula)}</div>'


def _format_cell(value, column: str, numeric_formats: Mapping[str, str]) -> str:
    if value is None or value is pd.NA:
        return "—"
    try:
        if pd.isna(value):
            return "—"
    except (TypeError, ValueError):
        pass
    pattern = numeric_formats.get(column)
    if pattern:
        try:
            return pattern.format(Decimal(str(value)))
        except (ArithmeticError, TypeError, ValueError):
            return safe_text(value)
    return safe_text(value)


def html_table(
    frame: pd.DataFrame,
    *,
    columns: Iterable[str] | None = None,
    labels: Mapping[str, str] | None = None,
    numeric_formats: Mapping[str, str] | None = None,
    status_columns: Iterable[str] = (),
    link_columns: Iterable[str] = (),
    max_rows: int = 100,
    empty_message: str = "표시할 검증 데이터가 없습니다.",
    caption: str = "감사 검토 데이터 표",
) -> str:
    if frame is None or frame.empty:
        return callout("neutral", "감사증거 없음", empty_message)
    selected = list(columns) if columns is not None else list(frame.columns)
    selected = [column for column in selected if column in frame.columns]
    visible = frame.loc[:, selected].head(max_rows)
    label_map = dict(labels or {})
    formats = dict(numeric_formats or {})
    status_set = set(status_columns)
    link_set = set(link_columns)
    header_style = _style(
        position="sticky",
        top="0",
        z_index="2",
        padding="11px 10px",
        border_bottom=_border(COLORS["border"]),
        background="#EAF0F5",
        color=COLORS["title"],
        font_size="14px",
        font_weight="800",
        line_height="1.45",
        text_align="left",
        white_space="nowrap",
    )
    headers = "".join(
        f'<th scope="col" style="{header_style + ("; left: 0; z-index: 4; background: #DFE8EF; min-width: 96px" if index == 0 else "")}">{escape(label_map.get(column, column))}</th>'
        for index, column in enumerate(selected)
    )
    rows: list[str] = []
    for row_index, (_, row) in enumerate(visible.iterrows()):
        cells: list[str] = []
        row_background = "#F7F9FB" if row_index % 2 else COLORS["card"]
        for column_index, column in enumerate(selected):
            text = _format_cell(row[column], column, formats)
            if column in status_set:
                rendered = status_badge(text)
            elif (
                column in link_set
                and text not in {"—", ""}
                and text.lower().startswith(("https://", "http://"))
            ):
                rendered = (
                    f'<a href="{escape(text, quote=True)}" target="_blank" '
                    'rel="noopener noreferrer" '
                    'style="color: #0B527D; font-weight: 800; text-decoration: underline" '
                    f'aria-label="{escape(label_map.get(column, column), quote=True)} '
                    f'원문 열기: {escape(text, quote=True)}">원문 ↗</a>'
                )
            else:
                rendered = escape(text)
            cell_style = _style(
                max_width="380px",
                padding="10px",
                border_bottom="1px solid #D7E0E8",
                background=row_background,
                color=COLORS["body"],
                font_size="14px",
                line_height="1.55",
                vertical_align="top",
                overflow_wrap="anywhere",
            )
            if column_index == 0:
                cell_style += (
                    "; position: sticky; left: 0; z-index: 3; min-width: 96px; "
                    f"box-shadow: 2px 0 0 #D7E0E8; background: {row_background}"
                )
            cells.append(f'<td style="{cell_style}">{rendered}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    note = ""
    if len(frame) > len(visible):
        note_style = _style(
            padding="8px 10px", color=COLORS["meta"], font_size="14px"
        )
        note = (
            f'<div class="metric-note" style="{note_style}">'
            f"상위 {len(visible):,}개 행 표시 · 전체 {len(frame):,}개 행</div>"
        )
    wrap_style = _base(
        max_width="calc(100vw - 48px)",
        min_width="0",
        width="100%",
        margin="10px 0 14px",
        overflow_x="auto",
        border=_border(COLORS["border"]),
        border_radius="12px",
        background=COLORS["card"],
        box_shadow=SHADOW,
        webkit_overflow_scrolling="touch",
    )
    table_style = _base(
        width="100%",
        min_width="720px",
        border_collapse="separate",
        border_spacing="0",
        background=COLORS["card"],
        color=COLORS["body"],
        font_size="14px",
    )
    caption_style = _style(
        position="absolute",
        width="1px",
        height="1px",
        padding="0",
        margin="-1px",
        overflow="hidden",
        clip="rect(0,0,0,0)",
        white_space="nowrap",
        border="0",
    )
    return (
        f'<div class="app-shell table-wrap" style="{wrap_style}" tabindex="0" role="region" aria-label="{escape(caption, quote=True)}">'
        f'<table class="audit-table" style="{table_style}">'
        f'<caption class="sr-only" style="{caption_style}">{escape(caption)}</caption>'
        f"<thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody>"
        f"</table>{note}</div>"
    )


def reconciliation_flow(model_amount: str) -> str:
    node_style = _base(
        display="flex",
        flex="1 1 190px",
        min_width="0",
        min_height="174px",
        flex_direction="column",
        gap="8px",
        padding="15px",
        border=_border(COLORS["border"]),
        border_radius="13px",
        background=COLORS["card"],
        box_shadow=SHADOW,
    )
    label_style = _style(
        color=COLORS["label"], font_size="15px", font_weight="800", line_height="1.45"
    )
    value_style = _style(
        color=COLORS["value"], font_size="25px", font_weight="800", line_height="1.3"
    )
    arrow_style = _style(
        align_self="center",
        flex="0 0 auto",
        color=COLORS["meta"],
        font_size="20px",
        font_weight="800",
        padding="4px",
    )
    flow_style = _base(
        display="flex",
        align_items="stretch",
        flex_wrap="wrap",
        gap="10px",
        width="100%",
        min_width="0",
        max_width="calc(100vw - 48px)",
        margin="14px 0",
    )
    return (
        f'<div class="app-shell recon-flow" style="{flow_style}">'
        f'<div class="recon-node recon-model" style="{node_style}"><span class="recon-label" style="{label_style}">모델 독립적 재계산</span>'
        f'<strong class="recon-value" style="{value_style}">{escape(model_amount)}</strong>{status_badge("official_source_calculated")}</div>'
        f'<div class="recon-arrow" aria-hidden="true" style="{arrow_style}">→</div>'
        f'<div class="recon-node recon-notice" style="{node_style}"><span class="recon-label" style="{label_style}">실제 고지세액</span>'
        f'<strong class="recon-value" style="{value_style}">미확인</strong>{status_badge("unverified")}</div>'
        f'<div class="recon-arrow" aria-hidden="true" style="{arrow_style}">→</div>'
        f'<div class="recon-node recon-conclusion" style="{node_style}"><span class="recon-label" style="{label_style}">차이 및 검토 결론</span>'
        f'<strong class="recon-value" style="{value_style}">계산 보류</strong>{status_badge("not_reconciled")}'
        f'<p class="recon-note" style="{_style(margin="auto 0 0", color=COLORS["meta"], font_size="14px", line_height="1.5")}">실제 고지서가 확보되지 않아 차이 분석 및 대사 결론을 보류했습니다.</p></div></div>'
    )
