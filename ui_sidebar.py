import os

import pandas as pd
import streamlit as st

from api_dart import (
    fetch_dart_annual_financial_history,
    fetch_dart_corp_code_table,
    fetch_dart_recent_report_list,
    fetch_dart_single_year_financials,
)
from api_ecos import build_macro_context, fetch_ecos_key_indicators
from api_manager import get_api_key, sanitize_secret_text
from calculations_scenario import DEFAULT_MACRO_FORECAST, FORECAST_WEIGHTED_SCENARIO_NAME, macro_scenario_parameters
from dart_financials import (
    company_options,
    get_recent_5y_financials,
    get_selected_company_profile,
    load_reit_master,
)
from ui_layout import SIDEBAR_SLOTS


SHOW_DEVELOPER_API_INPUTS = os.getenv("SHOW_DEVELOPER_API_INPUTS", "false").lower() == "true"


def _ensure_sidebar_session_defaults():
    defaults = {
        "analysis_run_id": 0,
        "selected_company_assets": pd.DataFrame(),
        "selected_company_tax_data": pd.DataFrame(),
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def _latest_period_context(kpis: pd.DataFrame, financials: pd.DataFrame) -> tuple[str, pd.Series, pd.Series]:
    selected_period = kpis.sort_values("period_end", ascending=False)["period_end"].dt.strftime("%Y-%m-%d").iloc[0]
    latest_kpi = kpis[kpis["period_end"].dt.strftime("%Y-%m-%d") == selected_period].iloc[0]
    latest_fin_candidates = financials[financials["period_end"].dt.strftime("%Y-%m-%d") == selected_period]
    latest_fin = latest_fin_candidates.iloc[0] if not latest_fin_candidates.empty else financials.sort_values("period_end").iloc[-1]
    return selected_period, latest_kpi, latest_fin


def _render_developer_api_inputs() -> tuple[str, str, str]:
    if not SHOW_DEVELOPER_API_INPUTS:
        return "", "", ""

    for session_key in ["ecos_api_key", "dart_api_key", "realty_price_api_key"]:
        if session_key not in st.session_state:
            st.session_state[session_key] = ""

    st.sidebar.divider()
    with st.sidebar.expander("개발자 설정: 외부 데이터 인증값", expanded=False):
        with st.form("manual_api_key_form", clear_on_submit=True):
            ecos_api_key_input = st.text_input("ECOS 인증값", value="", type="password", placeholder="로컬 테스트용 임시 값")
            dart_api_key_input = st.text_input("DART 인증값", value="", type="password", placeholder="로컬 테스트용 임시 값")
            realty_price_api_key_input = st.text_input("공시가격 데이터 인증값", value="", type="password", placeholder="로컬 테스트용 임시 값")
            apply_manual_keys = st.form_submit_button("임시 인증값 적용", width="stretch")
            clear_manual_keys = st.form_submit_button("임시 인증값 초기화", width="stretch")

        if apply_manual_keys:
            manual_updates = {
                "ecos_api_key": ecos_api_key_input.strip(),
                "dart_api_key": dart_api_key_input.strip(),
                "realty_price_api_key": realty_price_api_key_input.strip(),
            }
            for session_key, manual_value in manual_updates.items():
                if manual_value:
                    st.session_state[session_key] = manual_value
            fetch_ecos_key_indicators.clear()
            fetch_dart_corp_code_table.clear()
            fetch_dart_single_year_financials.clear()
            fetch_dart_annual_financial_history.clear()
            fetch_dart_recent_report_list.clear()

        if clear_manual_keys:
            for session_key in ["ecos_api_key", "dart_api_key", "realty_price_api_key"]:
                st.session_state[session_key] = ""
            fetch_ecos_key_indicators.clear()
            fetch_dart_corp_code_table.clear()
            fetch_dart_single_year_financials.clear()
            fetch_dart_annual_financial_history.clear()
            fetch_dart_recent_report_list.clear()

    return (
        st.session_state.get("ecos_api_key", ""),
        st.session_state.get("dart_api_key", ""),
        st.session_state.get("realty_price_api_key", ""),
    )


def _status_text(is_ready: bool, fallback: str = "실시간 데이터 연결이 제한되어 예시 데이터를 사용합니다.") -> str:
    return "준비 완료" if is_ready else fallback


def _sidebar_slot(name: str):
    return SIDEBAR_SLOTS.get(name, st.sidebar)


def _render_data_status(macro_context: dict, dart_status: str, ecos_conn, dart_conn, realty_conn):
    macro_ready = bool(ecos_conn.configured and macro_context.get("source") == "한국은행 ECOS API")
    dart_ready = bool(dart_status == "connected" or str(dart_status).startswith("Snapshot 기준"))
    realty_ready = bool(realty_conn.configured)
    data_connection_status = {
        "macro_ready": macro_ready,
        "dart_ready": dart_ready,
        "realty_ready": realty_ready,
    }

    st.divider()
    st.write("**데이터 연결 상태**")
    st.caption("실시간 연결이 제한될 경우 Snapshot 또는 예시 데이터를 사용합니다.")
    status_rows = pd.DataFrame([
        {"데이터": "거시경제 데이터", "상태": _status_text(macro_ready)},
        {"데이터": "공시 데이터", "상태": _status_text(dart_ready)},
        {"데이터": "공시가격 데이터", "상태": _status_text(realty_ready, "공시가격 실시간 조회가 제한되어 예시 데이터를 사용합니다.")},
    ])
    st.dataframe(status_rows, hide_index=True, width="stretch", height=142)

    with st.expander("데이터 연결 상세", expanded=False):
        macro_display = pd.DataFrame([
            {"지표": "한국은행 기준금리", "값": f"{macro_context['base_rate_pct']:.2f}%"},
            {"지표": "국고채 3년", "값": f"{macro_context['gov3y_pct']:.2f}%"},
            {"지표": "회사채 AA- 3년", "값": f"{macro_context['corp_aa_3y_pct']:.2f}%"},
            {"지표": "회사채-국고채 차이", "값": f"{macro_context['credit_spread_pct']:.2f}%p"},
        ])
        st.dataframe(macro_display, hide_index=True, width="stretch", height=150)
        if macro_context.get("status") != "connected":
            st.caption(f"거시경제 데이터: {sanitize_secret_text(macro_context.get('status', '예시 데이터 사용'))}")
        if dart_status != "connected":
            st.caption(f"공시 데이터: {sanitize_secret_text(dart_status)}")
    return data_connection_status


def render_data_sidebar(
    kpis: pd.DataFrame,
    financials: pd.DataFrame,
    selected_user_mode: str,
    peer_metrics: pd.DataFrame | None = None,
    peer_snapshot: pd.DataFrame | None = None,
) -> dict:
    _ensure_sidebar_session_defaults()
    selected_period, latest_kpi, latest_fin = _latest_period_context(kpis, financials)

    manual_ecos_value, manual_dart_value, manual_realty_value = _render_developer_api_inputs()
    ecos_conn = get_api_key("ECOS", manual_ecos_value)
    dart_conn = get_api_key("DART", manual_dart_value)
    realty_conn = get_api_key("V-World", manual_realty_value)
    macro_context = build_macro_context(ecos_conn.key)

    with _sidebar_slot("scenario"):
        st.write("**시나리오 선택**")
        selected_macro_scenario = st.selectbox(
            "예상 거시경제 상황",
            [
                FORECAST_WEIGHTED_SCENARIO_NAME,
                "중립: 현재와 유사한 금융환경",
                "호황: 금리 높지만 임대수익 방어",
                "불황: 금리 인하에도 신용위험 확대",
            ],
        )
        macro_forecast = DEFAULT_MACRO_FORECAST.copy()
        with st.expander("전망 기반 시나리오 가정", expanded=selected_macro_scenario == FORECAST_WEIGHTED_SCENARIO_NAME):
            st.caption("기본값은 2026년 주요 전망치 수준을 반영한 시작점입니다. 내부 전망치가 있으면 이 값만 조정하세요.")
            macro_forecast["gdp_growth_2026_pct"] = st.slider(
                "2026 GDP 성장률 전망",
                min_value=0.0,
                max_value=5.0,
                value=float(DEFAULT_MACRO_FORECAST["gdp_growth_2026_pct"]),
                step=0.1,
            )
            macro_forecast["cpi_2026_pct"] = st.slider(
                "2026 소비자물가 상승률 전망",
                min_value=0.0,
                max_value=5.0,
                value=float(DEFAULT_MACRO_FORECAST["cpi_2026_pct"]),
                step=0.1,
            )
            macro_forecast["policy_rate_12m_pct"] = st.slider(
                "12개월 후 기준금리 전망",
                min_value=0.5,
                max_value=5.0,
                value=float(DEFAULT_MACRO_FORECAST["policy_rate_12m_pct"]),
                step=0.25,
            )
            macro_forecast["credit_spread_change_bp"] = st.slider(
                "신용스프레드 변화 전망",
                min_value=-100,
                max_value=200,
                value=int(DEFAULT_MACRO_FORECAST["credit_spread_change_bp"]),
                step=25,
            )
    macro_scenario = macro_scenario_parameters(macro_context, selected_macro_scenario, macro_forecast)

    rate_shock_bp = macro_scenario["rate_shock_bp"]
    refinancing_share_pct = macro_scenario["refinancing_share_pct"]
    ffo_haircut_pct = macro_scenario["ffo_haircut_pct"]
    cap_rate_shock_bp = macro_scenario["cap_rate_shock_bp"]

    with _sidebar_slot("scenario"):
        st.info(macro_scenario["scenario_explain"])
        if macro_scenario.get("scenario_probabilities"):
            probs = macro_scenario["scenario_probabilities"]
            st.caption(f"확률가중: 호황 {probs['호황']:.0%} · 중립 {probs['중립']:.0%} · 불황 {probs['불황']:.0%}")
        st.caption(
            f"스트레스 값: 차입금리 +{rate_shock_bp}bp · 차환 대상 {refinancing_share_pct}% · "
            f"현금흐름 하락 {ffo_haircut_pct}% · Cap rate +{cap_rate_shock_bp}bp"
        )
        st.divider()

    with _sidebar_slot("company"):
        st.write("**분석 대상회사**")
        st.caption("시가총액 순위 Snapshot 기준 정렬")
        reit_master = load_reit_master()
        options = company_options(reit_master)
        if "selected_company_option" not in st.session_state:
            st.session_state["selected_company_option"] = options[0]
        with st.form("selected_company_form", clear_on_submit=False):
            selected_company_option = st.selectbox(
                "분석 대상회사",
                options,
                index=options.index(st.session_state["selected_company_option"]) if st.session_state["selected_company_option"] in options else 0,
                help="시가총액 순위 Snapshot을 기준으로 정렬한 상장리츠 목록입니다.",
            )
            run_analysis = st.form_submit_button("분석 실행", width="stretch")
        previous_company_option = st.session_state.get("selected_company_option")
        if run_analysis:
            if selected_company_option != previous_company_option:
                for stale_key in [
                    "realty_price_api_history",
                    "realty_price_api_status",
                    "selected_company_assets",
                    "selected_company_tax_data",
                ]:
                    st.session_state.pop(stale_key, None)
            st.session_state["selected_company_option"] = selected_company_option
            st.session_state["analysis_run_id"] = int(st.session_state.get("analysis_run_id", 0)) + 1
        elif st.session_state.get("selected_company_option") not in options:
            st.session_state["selected_company_option"] = selected_company_option
        target_company_option = st.session_state.get("selected_company_option", selected_company_option)
        company_profile = get_selected_company_profile(target_company_option, reit_master, peer_snapshot)
        target_company = company_profile["company_name"]
        peer_group = "전체 상장리츠"
        recent_5y_financials, recent_5y_status = get_recent_5y_financials(company_profile, peer_snapshot, dart_conn.key)
        st.session_state["selected_company"] = target_company
        st.session_state["selected_stock_code"] = company_profile.get("stock_code", "")
        st.session_state["selected_dart_corp_code"] = company_profile.get("dart_corp_code", "")
        st.session_state["selected_company_profile"] = company_profile
        st.session_state["recent_5y_financials"] = recent_5y_financials
        rank = company_profile.get("market_cap_rank", pd.NA)
        rank_text = f"{int(rank)}위" if pd.notna(rank) else "순위 정보 없음"
        st.caption(f"{company_profile.get('stock_code', '')} / {rank_text} / {company_profile.get('main_asset_type', '')}")
        if run_analysis:
            st.success(f"분석 대상이 {target_company}(으)로 업데이트되었습니다.")
        st.divider()

    with _sidebar_slot("assumptions"):
        st.write("**분석 가정**")
        professional_assumptions = {"realty_conn": realty_conn}
        if selected_user_mode == "Assurance":
            professional_assumptions["assurance_materiality_pct"] = st.slider(
                "감사 중점 자산 기준: 평가액 비중",
                min_value=5.0,
                max_value=25.0,
                value=10.0,
                step=2.5,
                help="평가액 비중이 이 기준 이상인 자산은 공정가치 평가위험 검토 우선순위가 올라갑니다.",
            )
        elif selected_user_mode == "Tax":
            st.caption("Tax 모드는 양도세를 제외하고 보유세만 분석합니다.")
            professional_assumptions["land_fmv_ratio_pct"] = st.slider("토지 공정시장가액비율", 40.0, 100.0, 70.0, 5.0)
            professional_assumptions["building_fmv_ratio_pct"] = st.slider("건축물 공정시장가액비율", 40.0, 100.0, 70.0, 5.0)
            professional_assumptions["building_tax_rate_pct"] = st.slider(
                "일반 건축물 재산세율 추정치(proxy)",
                min_value=0.05,
                max_value=1.00,
                value=0.25,
                step=0.05,
                help="상업용 일반 건축물에 대한 단순 추정치(proxy)입니다. 실제 용도별 세율 검토가 필요합니다.",
            )
            professional_assumptions["include_urban_area_tax"] = st.checkbox("도시지역분 포함", value=True)
            professional_assumptions["include_local_education_tax"] = st.checkbox("지방교육세 포함", value=True)
            professional_assumptions["apply_tax_burden_cap"] = st.checkbox("세부담상한 단순 적용", value=False)
            professional_assumptions["tax_burden_cap_pct"] = st.slider("세부담상한 추정치(proxy)", 110.0, 200.0, 150.0, 10.0)
            with st.expander("공시가격 실시간 조회 제한 시 추정치(proxy) 가정", expanded=False):
                professional_assumptions["proxy_land_growth_pct"] = st.slider("연간 공시지가 상승률 추정치(proxy)", 0.0, 15.0, 3.0, 0.5)
                professional_assumptions["official_to_appraisal_ratio_pct"] = st.slider("토지 공시가격/감정가 추정치(proxy)", 10.0, 90.0, 55.0, 5.0)
                professional_assumptions["building_standard_ratio_pct"] = st.slider("건물 기준시가/감정가 추정치(proxy)", 0.0, 60.0, 20.0, 5.0)

    dart_history = recent_5y_financials
    dart_reports = pd.DataFrame()
    dart_status = "connected" if str(recent_5y_status).startswith("DART 선택 회사") else recent_5y_status

    market_history = pd.DataFrame()
    market_status = "시장가격 데이터 모듈은 향후 버전을 위해 비활성화되어 있습니다."

    with _sidebar_slot("data_status"):
        data_connection_status = _render_data_status(macro_context, dart_status, ecos_conn, dart_conn, realty_conn)
        st.caption(
            "ECOS는 현재·과거 지표를 제공합니다. 전망 기반 확률가중 모드는 별도 전망 입력값을 사용해 "
            "호황·중립·불황 확률을 산정한 뒤 리츠 스트레스 값으로 변환합니다."
        )

    return {
        "mode": selected_user_mode,
        "selected_mode": selected_user_mode,
        "selected_period": selected_period,
        "latest_kpi": latest_kpi,
        "latest_fin": latest_fin,
        "selected_company": target_company,
        "target_company": target_company,
        "selected_stock_code": company_profile.get("stock_code", ""),
        "selected_dart_corp_code": company_profile.get("dart_corp_code", ""),
        "peer_group": peer_group,
        "selected_company_profile": company_profile,
        "recent_5y_financials": recent_5y_financials,
        "recent_5y_status": recent_5y_status,
        "selected_company_assets": st.session_state.get("selected_company_assets", pd.DataFrame()),
        "selected_company_tax_data": st.session_state.get("selected_company_tax_data", pd.DataFrame()),
        "selected_scenario": macro_scenario.get("selected_scenario", selected_macro_scenario),
        "scenario": macro_scenario,
        "analysis_run_id": st.session_state.get("analysis_run_id", 0),
        "data_connection_status": data_connection_status,
        "ecos_conn": ecos_conn,
        "dart_conn": dart_conn,
        "realty_conn": realty_conn,
        "ecos_api_key": ecos_conn.key,
        "dart_api_key": dart_conn.key,
        "realty_api_key": realty_conn.key,
        "realty_price_api_key": realty_conn.key,
        "macro_context": macro_context,
        "dart_history": dart_history,
        "dart_reports": dart_reports,
        "dart_status": dart_status,
        "market_history": market_history,
        "market_status": market_status,
        "macro_scenario": macro_scenario,
        "rate_shock_bp": rate_shock_bp,
        "refinancing_share_pct": refinancing_share_pct,
        "ffo_haircut_pct": ffo_haircut_pct,
        "cap_rate_shock_bp": cap_rate_shock_bp,
        "professional_assumptions": professional_assumptions,
    }
