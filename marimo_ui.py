from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal
from html import escape
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
STYLE_PATH = PROJECT_ROOT / "marimo_styles.css"


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


def load_css() -> str:
    return STYLE_PATH.read_text(encoding="utf-8")


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
    icon, default_label, css_class = STATUS_LABELS.get(
        str(status).strip().lower(), ("•", safe_text(status), "neutral")
    )
    visible = label or default_label
    return (
        f'<span class="status-badge {css_class}">'
        f'<span aria-hidden="true">{escape(icon)}</span>{escape(visible)}</span>'
    )


def chip(label: str) -> str:
    return f'<span class="chip">{escape(label)}</span>'


def hero(*, title: str, kicker: str, metadata: Iterable[str]) -> str:
    meta = "".join(f"<span>{escape(item)}</span>" for item in metadata)
    return (
        '<div class="app-shell"><section class="assurance-hero">'
        f'<p class="hero-kicker">{escape(kicker)}</p>'
        f"<h1>{escape(title)}</h1>"
        f'<div class="hero-meta">{meta}</div>'
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
    """Render the shared dense header used by all three analysis pages."""
    meta = "".join(f"<span>{escape(item)}</span>" for item in metadata)
    return (
        '<div class="app-shell dense-header">'
        '<div class="dense-title-row"><div>'
        f'<h1>{escape(title)}</h1><p>{escape(subtitle)}</p>'
        f'</div><div class="dense-meta">{meta}</div></div>'
        '<div class="compact-workflow" aria-label="감사검토 절차">'
        '<span>위험 식별</span><b>→</b><span>감사증거 검증·독립적 재계산</span>'
        '<b>→</b><span>고지서 대사·예외 후속조치</span><b>→</b><span>검토자 결론</span>'
        '</div><div class="compact-source">'
        f'{status_badge(source_status)}<span>{escape(source_detail)}</span>'
        f'<span class="compact-source-time">자료 기준 {escape(retrieved_at)}</span>'
        '</div></div>'
    )


def dense_metric(
    label: str,
    value: str,
    *,
    baseline: str = "",
    delta: str = "",
    severity: str = "neutral",
) -> str:
    return (
        f'<article class="dense-metric status-{escape(severity)}">'
        f'<span class="dense-metric-label">{escape(label)}</span>'
        f'<strong>{escape(value)}</strong>'
        '<div class="dense-metric-meta">'
        f'<span>{escape(baseline)}</span><span>{escape(delta)}</span></div></article>'
    )


def dense_metric_grid(cards: Iterable[str]) -> str:
    return f'<div class="dense-metric-grid">{"".join(cards)}</div>'


def mini_stat(label: str, value: str, note: str = "", severity: str = "neutral") -> str:
    return (
        f'<div class="mini-stat status-{escape(severity)}">'
        f'<span>{escape(label)}</span><strong>{escape(value)}</strong>'
        f'<small>{escape(note)}</small></div>'
    )


def source_ribbon(*, status: str, detail: str, retrieved_at: str) -> str:
    return (
        '<section class="app-shell source-ribbon" aria-label="데이터 출처 및 계보">'
        '<div class="source-provenance">'
        '<strong class="source-title">데이터 출처 및 계보</strong>'
        f'{status_badge(status)}<span class="source-detail">{escape(detail)}</span>'
        "</div>"
        '<div class="source-timestamp">'
        '<strong class="source-time-label">자료 기준 일시</strong>'
        f'<span class="source-time-value">{escape(retrieved_at)}</span></div>'
        "</section>"
    )


def workflow(active_step: int) -> str:
    steps = [
        ("01", "위험 식별"),
        ("02", "감사증거 검증 및 독립적 재계산"),
        ("03", "고지서 대사 및 예외 후속조치"),
        ("04", "검토자 결론"),
    ]
    items = "".join(
        f'<div class="workflow-step{" is-active" if int(number) == active_step else ""}">'
        f'<span class="step-no">{number}단계</span><strong>{escape(label)}</strong>'
        "</div>"
        for number, label in steps
    )
    return f'<div class="app-shell workflow">{items}</div>'


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
    severity_label = severity_labels.get(severity, "정보")
    return (
        f'<article class="metric-card status-{escape(severity)}">'
        '<div class="metric-card-header">'
        f'<div class="metric-label">{escape(label)}</div>'
        f'<span class="metric-status">{escape(severity_label)}</span></div>'
        f'<div class="metric-value">{escape(value)}</div>'
        f'<div class="metric-note">{escape(note)}</div>'
        "</article>"
    )


def metric_grid(cards: Iterable[str]) -> str:
    return f'<div class="app-shell metric-grid">{"".join(cards)}</div>'


def section_heading(
    title: str,
    *,
    kicker: str,
    description: str = "",
) -> str:
    return (
        '<header class="app-shell section-heading">'
        f'<p class="section-kicker">{escape(kicker)}</p>'
        f"<h2>{escape(title)}</h2>"
        f'<p class="section-description">{escape(description)}</p>'
        "</header>"
    )


def callout(kind: str, title: str, body: str) -> str:
    css_kind = kind if kind in {"warning", "critical", "ok", "neutral"} else ""
    return (
        f'<div class="app-shell callout {css_kind}">'
        f"<strong>{escape(title)}</strong><p>{escape(body)}</p></div>"
    )


def panel(title: str, body_html: str) -> str:
    """Compose trusted helper-generated HTML inside a titled panel."""
    return (
        f'<section class="panel"><h3>{escape(title)}</h3>{body_html}</section>'
    )


def columns(panels: Iterable[str], count: int = 2) -> str:
    """Lay out trusted panel HTML; callers must escape untrusted values first."""
    css_class = "three-col" if count == 3 else "two-col"
    return f'<div class="app-shell {css_class}">{"".join(panels)}</div>'


def bullet_list(items: Iterable[str]) -> str:
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def formula_box(formula: str) -> str:
    return f'<div class="formula-box">{escape(formula)}</div>'


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
    headers = "".join(
        f'<th scope="col">{escape(label_map.get(c, c))}</th>' for c in selected
    )
    rows: list[str] = []
    for _, row in visible.iterrows():
        cells: list[str] = []
        for column in selected:
            raw = row[column]
            text = _format_cell(raw, column, formats)
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
                    f'aria-label="{escape(label_map.get(column, column), quote=True)} '
                    f'원문 열기: {escape(text, quote=True)}">원문 ↗</a>'
                )
            else:
                rendered = escape(text)
            cells.append(f"<td>{rendered}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    note = ""
    if len(frame) > len(visible):
        note = f'<div class="metric-note">상위 {len(visible):,}개 행 표시 · 전체 {len(frame):,}개 행</div>'
    return (
        '<div class="app-shell table-wrap" tabindex="0" role="region" '
        f'aria-label="{escape(caption, quote=True)}">'
        '<table class="audit-table">'
        f'<caption class="sr-only">{escape(caption)}</caption>'
        f"<thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody>"
        f"</table>{note}</div>"
    )


def reconciliation_flow(model_amount: str) -> str:
    return (
        '<div class="app-shell recon-flow">'
        '<div class="recon-node recon-model"><span class="recon-label">모델 독립적 재계산</span>'
        f'<strong class="recon-value">{escape(model_amount)}</strong>'
        f"{status_badge('official_source_calculated')}</div>"
        '<div class="recon-arrow" aria-hidden="true">→</div>'
        '<div class="recon-node recon-notice"><span class="recon-label">실제 고지세액</span>'
        f'<strong class="recon-value">미확인</strong>{status_badge("unverified")}</div>'
        '<div class="recon-arrow" aria-hidden="true">→</div>'
        '<div class="recon-node recon-conclusion"><span class="recon-label">차이 및 검토 결론</span>'
        f'<strong class="recon-value">계산 보류</strong>{status_badge("not_reconciled")}'
        '<p class="recon-note">실제 고지서가 확보되지 않아 차이 분석 및 대사 결론을 보류했습니다.</p></div>'
        "</div>"
    )
