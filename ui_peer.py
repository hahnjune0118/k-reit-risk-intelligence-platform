import pandas as pd
import streamlit as st

from calculations_peer import get_company_peer_profile
from red_flag_engine import risk_level_to_color_style, risk_level_to_icon, risk_level_to_korean_label
from ui_common import fmt_mn_to_bn


RATIO_METRICS = {
    "investment_property_to_total_assets",
    "debt_to_assets",
    "current_debt_to_total_debt",
    "interest_expense_to_ffo",
    "dividend_to_ffo",
    "holding_tax_to_ffo",
    "holding_tax_to_operating_revenue",
    "official_price_to_investment_property",
    "operating_cash_flow_to_dividends",
}


def format_peer_value(metric: str, value) -> str:
    if pd.isna(value):
        return "데이터 부족"
    if metric in RATIO_METRICS:
        return f"{float(value) * 100:.1f}%"
    if metric in {"total_assets", "investment_property", "borrowings_total", "estimated_holding_tax", "official_price_total"}:
        return fmt_mn_to_bn(float(value))
    return f"{float(value):,.1f}"


def format_peer_percentile(value) -> str:
    if pd.isna(value):
        return "데이터 부족"
    return f"{float(value) * 100:.0f}백분위"


def overall_flag_level(flags: list[dict]) -> str:
    levels = [flag.get("risk_level", "gray") for flag in flags]
    if not levels:
        return "gray"
    if "red" in levels:
        return "red"
    if "yellow" in levels:
        return "yellow"
    if all(level == "gray" for level in levels):
        return "gray"
    return "green"


def render_overall_risk_message(title: str, flags: list[dict], suffix: str = ""):
    level = overall_flag_level(flags)
    message = f"{title}: {risk_level_to_icon(level)} {risk_level_to_korean_label(level)}"
    if suffix:
        message = f"{message} - {suffix}"
    renderer = {
        "success": st.success,
        "warning": st.warning,
        "error": st.error,
        "info": st.info,
    }[risk_level_to_color_style(level)]
    renderer(message)


def flags_to_dataframe(flags: list[dict], response_field: str) -> pd.DataFrame:
    rows = []
    for flag in flags:
        rows.append({
            "위험명": flag.get("label", ""),
            "위험수준": f"{risk_level_to_icon(flag.get('risk_level'))} {risk_level_to_korean_label(flag.get('risk_level'))}",
            "지표값": format_peer_value(flag.get("metric", ""), flag.get("value")),
            "Peer 위치": format_peer_percentile(flag.get("percentile")),
            "발생 근거": flag.get("explanation_ko", ""),
            "권장 대응": " / ".join(flag.get(response_field, []) or []),
            "요청 증거": " / ".join(flag.get("evidence_request", []) or []),
        })
    return pd.DataFrame(rows)


def _join_list(value: list[str] | None) -> str:
    return "\n".join(value or ["데이터 부족"])


def _risk_review_label(level: str) -> str:
    return risk_level_to_korean_label(level)


def _risk_cell_style(value: str) -> str:
    if value == "높음":
        return "background-color: #fde2e2; color: #8a1f1f; font-weight: 600;"
    if value == "주의":
        return "background-color: #fff4ce; color: #6f4e00; font-weight: 600;"
    if value == "정상":
        return "background-color: #dff5e1; color: #145c2e; font-weight: 600;"
    return "background-color: #eeeeee; color: #555555; font-weight: 600;"


def style_risk_review_table(df: pd.DataFrame):
    if df.empty or "위험수준" not in df.columns:
        return df
    styler = df.style
    if hasattr(styler, "map"):
        return styler.map(_risk_cell_style, subset=["위험수준"])
    return styler.applymap(_risk_cell_style, subset=["위험수준"])


def flags_to_assurance_review_table(flags: list[dict]) -> pd.DataFrame:
    rows = []
    for flag in flags:
        level = flag.get("risk_level", "gray")
        kam_indicator = {
            "red": "검토 필요",
            "yellow": "검토 권장",
            "green": "낮음",
            "gray": "데이터 부족",
        }.get(level, "데이터 부족")
        rows.append({
            "위험영역": flag.get("label", ""),
            "위험수준": _risk_review_label(level),
            "발생 근거": flag.get("explanation_ko", "데이터 부족"),
            "권장 감사절차": _join_list(flag.get("audit_response", [])),
            "요청자료": _join_list(flag.get("evidence_request", [])),
            "KAM 후보 검토": kam_indicator,
        })
    return pd.DataFrame(rows)


def flags_to_tax_review_table(flags: list[dict]) -> pd.DataFrame:
    rows = []
    for flag in flags:
        level = flag.get("risk_level", "gray")
        rows.append({
            "세무 위험영역": flag.get("label", ""),
            "위험수준": _risk_review_label(level),
            "발생 근거": flag.get("explanation_ko", "데이터 부족"),
            "Tax 검토사항": _join_list(flag.get("tax_review_points", [])),
            "요청자료": _join_list(flag.get("evidence_request", [])),
            "관련 지표": format_peer_value(flag.get("metric", ""), flag.get("value")),
        })
    return pd.DataFrame(rows)


def render_red_flag_cards(flags: list[dict], response_field: str, response_label: str, include_kam_indicator: bool = False):
    if not flags:
        st.info("Peer Benchmark를 계산할 수 있는 데이터가 부족합니다.")
        return

    for flag in flags:
        level = flag.get("risk_level", "gray")
        title = f"{risk_level_to_icon(level)} {flag.get('label', 'Red Flag')} - {risk_level_to_korean_label(level)}"
        with st.expander(title, expanded=level in {"red", "yellow"}):
            c1, c2, c3 = st.columns(3)
            c1.metric("위험수준", risk_level_to_korean_label(level))
            c2.metric("지표값", format_peer_value(flag.get("metric", ""), flag.get("value")))
            c3.metric("Peer 위치", format_peer_percentile(flag.get("percentile")))
            st.write(f"**발생 근거**: {flag.get('explanation_ko', '데이터 부족')}")
            st.write(f"**{response_label}**")
            for item in flag.get(response_field, []) or ["데이터 부족"]:
                st.write(f"- {item}")
            st.write("**요청할 증거/자료**")
            for item in flag.get("evidence_request", []) or ["데이터 부족"]:
                st.write(f"- {item}")
            if include_kam_indicator:
                kam_indicator = {"red": "높음", "yellow": "중간", "green": "낮음", "gray": "데이터 부족"}.get(level, "데이터 부족")
                st.caption(f"KAM 후보 검토 필요성: {kam_indicator}")


def build_peer_metric_table(metrics_df: pd.DataFrame, company_name: str, metric_labels: dict[str, str]) -> pd.DataFrame:
    company_row = get_company_peer_profile(metrics_df, company_name)
    if isinstance(company_row, dict) and not company_row:
        return pd.DataFrame()

    rows = []
    for metric, label in metric_labels.items():
        if metric not in metrics_df.columns:
            continue
        peer_values = pd.to_numeric(metrics_df[metric], errors="coerce")
        rows.append({
            "지표": label,
            "선택 리츠": format_peer_value(metric, company_row.get(metric, pd.NA)),
            "Peer 중앙값": format_peer_value(metric, peer_values.median(skipna=True)),
            "Peer 평균": format_peer_value(metric, peer_values.mean(skipna=True)),
            "Peer 위치": format_peer_percentile(company_row.get(f"{metric}_percentile", pd.NA)),
        })
    return pd.DataFrame(rows)
