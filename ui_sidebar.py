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


def render_data_sidebar(kpis: pd.DataFrame, financials: pd.DataFrame, selected_user_mode: str) -> dict:
    st.sidebar.header("데이터 연결과 시나리오")
    st.sidebar.caption("사용자가 금리를 임의로 넣는 대신, ECOS에서 불러온 금리 지표를 기준으로 시나리오를 선택합니다.")

    selected_period = st.sidebar.selectbox(
        "공시 기준일",
        kpis.sort_values("period_end", ascending=False)["period_end"].dt.strftime("%Y-%m-%d").tolist(),
    )
    latest_kpi = kpis[kpis["period_end"].dt.strftime("%Y-%m-%d") == selected_period].iloc[0]
    latest_fin_candidates = financials[financials["period_end"].dt.strftime("%Y-%m-%d") == selected_period]
    latest_fin = latest_fin_candidates.iloc[0] if not latest_fin_candidates.empty else financials.sort_values("period_end").iloc[-1]

    for session_key in ["ecos_api_key", "dart_api_key", "realty_price_api_key"]:
        if session_key not in st.session_state:
            st.session_state[session_key] = ""

    st.sidebar.divider()
    with st.sidebar.expander("고급 설정: 수동 API Key 입력", expanded=False):
        with st.form("manual_api_key_form", clear_on_submit=True):
            ecos_api_key_input = st.text_input(
                "ECOS API Key",
                value="",
                type="password",
                placeholder="Secrets에 있으면 입력하지 않아도 됩니다.",
            )
            dart_api_key_input = st.text_input(
                "DART API Key",
                value="",
                type="password",
                placeholder="Secrets에 있으면 입력하지 않아도 됩니다.",
            )
            realty_price_api_key_input = st.text_input(
                "V-World / Realty Price API Key",
                value="",
                type="password",
                placeholder="Secrets에 있으면 입력하지 않아도 됩니다.",
            )
            apply_manual_keys = st.form_submit_button("수동 API Key 적용", width="stretch")
            clear_manual_keys = st.form_submit_button("수동 API Key 초기화", width="stretch")

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

    ecos_conn = get_api_key("ECOS", st.session_state.get("ecos_api_key", ""))
    dart_conn = get_api_key("DART", st.session_state.get("dart_api_key", ""))
    realty_conn = get_api_key("V-World", st.session_state.get("realty_price_api_key", ""))
    api_status_rows = [
        {"상태": "ECOS: API key loaded" if ecos_conn.configured else "ECOS: not configured"},
        {"상태": "DART: API key loaded" if dart_conn.configured else "DART: not configured"},
        {"상태": "V-World: API key loaded" if realty_conn.configured else "V-World: not configured"},
    ]

    st.sidebar.write("**API 연결 상태**")
    st.sidebar.dataframe(
        pd.DataFrame(api_status_rows),
        hide_index=True,
        width="stretch",
        height=176,
    )

    st.sidebar.divider()
    st.sidebar.write("**한국은행 ECOS 연결**")
    st.sidebar.caption("ECOS API key는 Streamlit Secrets, 환경변수 또는 고급 설정의 수동 입력에서 불러옵니다.")

    macro_context = build_macro_context(ecos_conn.key)

    if macro_context["status"] == "connected":
        if macro_context["source"] == "한국은행 ECOS API":
            st.sidebar.success("ECOS API 연결 완료")
        else:
            st.sidebar.warning("ECOS 연결은 되었지만 일부 지표명이 매칭되지 않아 예시값을 일부 사용합니다.")
    else:
        st.sidebar.warning("ECOS 미연결: 예시값으로 실행 중")
        with st.sidebar.expander("ECOS 연결 상태 보기", expanded=False):
            st.write(sanitize_secret_text(macro_context.get("status", "unknown")))

    macro_display = pd.DataFrame([
        {"지표": "한국은행 기준금리", "값": f"{macro_context['base_rate_pct']:.2f}%"},
        {"지표": "국고채 3년", "값": f"{macro_context['gov3y_pct']:.2f}%"},
        {"지표": "회사채 AA- 3년", "값": f"{macro_context['corp_aa_3y_pct']:.2f}%"},
        {"지표": "회사채-국고채 차이", "값": f"{macro_context['credit_spread_pct']:.2f}%p"},
    ])
    st.sidebar.dataframe(macro_display, hide_index=True, width="stretch", height=150)

    st.sidebar.divider()
    st.sidebar.write("**금융감독원 DART 연결**")
    st.sidebar.caption("DART 인증키를 입력하면 SK리츠의 최근 5개 사업연도 재무제표를 자동으로 불러와 시계열 분석에 사용합니다.")

    if "dart_stock_code" not in st.session_state:
        st.session_state["dart_stock_code"] = "395400"
    if "dart_company_keyword" not in st.session_state:
        st.session_state["dart_company_keyword"] = "SK리츠"

    with st.sidebar.form("dart_config_form", clear_on_submit=False):
        dart_stock_code_input = st.text_input("종목코드", value=st.session_state.get("dart_stock_code", "395400"))
        dart_company_keyword_input = st.text_input("회사명 검색어", value=st.session_state.get("dart_company_keyword", "SK리츠"))
        submitted_dart_key = st.form_submit_button("DART 최근 5년 재무제표 불러오기", width="stretch")

    if submitted_dart_key:
        st.session_state["dart_stock_code"] = dart_stock_code_input.strip()
        st.session_state["dart_company_keyword"] = dart_company_keyword_input.strip()
        fetch_dart_corp_code_table.clear()
        fetch_dart_single_year_financials.clear()
        fetch_dart_annual_financial_history.clear()
        fetch_dart_recent_report_list.clear()

    dart_stock_code = st.session_state.get("dart_stock_code", "395400")
    dart_company_keyword = st.session_state.get("dart_company_keyword", "SK리츠")

    dart_history, dart_reports, dart_status = fetch_dart_annual_financial_history(
        dart_conn.key,
        dart_stock_code,
        dart_company_keyword,
        years_back=5,
    ) if dart_conn.key else (pd.DataFrame(), pd.DataFrame(), "DART 미연결: 로컬 CSV 기준으로 실행")

    if dart_status == "connected":
        st.sidebar.success("DART API 연결 완료")
    else:
        st.sidebar.warning("DART 미연결 또는 일부 자료 수집 실패")
        with st.sidebar.expander("DART 연결 상태 보기", expanded=False):
            st.write(sanitize_secret_text(dart_status))

    market_history = pd.DataFrame()
    market_status = "Market data module archived for future version"

    st.sidebar.divider()
    st.sidebar.write("**시나리오 선택**")
    selected_macro_scenario = st.sidebar.selectbox(
        "예상 거시경제 상황",
        [
            FORECAST_WEIGHTED_SCENARIO_NAME,
            "중립: 현재와 유사한 금융환경",
            "호황: 금리 높지만 임대수익 방어",
            "불황: 금리 인하에도 신용위험 확대",
        ],
    )
    macro_forecast = DEFAULT_MACRO_FORECAST.copy()
    with st.sidebar.expander("전망 기반 시나리오 가정", expanded=selected_macro_scenario == FORECAST_WEIGHTED_SCENARIO_NAME):
        st.caption("기본값은 2026년 주요 전망치 수준을 반영한 시작점입니다. 실제 house view가 있으면 이 값만 조정하세요.")
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

    st.sidebar.info(macro_scenario["scenario_explain"])
    if macro_scenario.get("scenario_probabilities"):
        probs = macro_scenario["scenario_probabilities"]
        st.sidebar.caption(
            f"확률가중: 호황 {probs['호황']:.0%} · 중립 {probs['중립']:.0%} · 불황 {probs['불황']:.0%}"
        )
    st.sidebar.write("**자동 적용되는 스트레스 값**")
    st.sidebar.caption(
        f"차입금리 충격: +{rate_shock_bp}bp · 차환 대상 부채: {refinancing_share_pct}% · "
        f"현금흐름 하락: {ffo_haircut_pct}% · Cap rate 상승: +{cap_rate_shock_bp}bp"
    )

    st.sidebar.divider()
    st.sidebar.write("**모드별 가정값**")
    professional_assumptions = {"realty_conn": realty_conn}
    if selected_user_mode == "Assurance":
        professional_assumptions["assurance_materiality_pct"] = st.sidebar.slider(
            "감사 중점 자산 기준: 평가액 비중",
            min_value=5.0,
            max_value=25.0,
            value=10.0,
            step=2.5,
            help="평가액 비중이 이 기준 이상인 자산은 공정가치 평가위험 검토 우선순위가 올라갑니다.",
        )
    elif selected_user_mode == "Tax":
        st.sidebar.caption("Tax 모드는 양도세를 제외하고 보유세만 분석합니다.")
        professional_assumptions["land_fmv_ratio_pct"] = st.sidebar.slider(
            "토지 공정시장가액비율", min_value=40.0, max_value=100.0, value=70.0, step=5.0,
            help="토지 시가표준액에 곱해 재산세 과세표준을 계산하는 비율입니다."
        )
        professional_assumptions["building_fmv_ratio_pct"] = st.sidebar.slider(
            "건축물 공정시장가액비율", min_value=40.0, max_value=100.0, value=70.0, step=5.0,
        )
        professional_assumptions["building_tax_rate_pct"] = st.sidebar.slider(
            "일반 건축물 재산세율 proxy", min_value=0.05, max_value=1.00, value=0.25, step=0.05,
            help="상업용 일반 건축물 proxy입니다. 실제 용도별 세율 검토가 필요합니다."
        )
        professional_assumptions["include_urban_area_tax"] = st.sidebar.checkbox("도시지역분 포함", value=True)
        professional_assumptions["include_local_education_tax"] = st.sidebar.checkbox("지방교육세 포함", value=True)
        professional_assumptions["apply_tax_burden_cap"] = st.sidebar.checkbox("세부담상한 단순 적용", value=False)
        professional_assumptions["tax_burden_cap_pct"] = st.sidebar.slider("세부담상한 proxy", min_value=110.0, max_value=200.0, value=150.0, step=10.0)
        with st.sidebar.expander("API 미연결시 proxy 가정", expanded=False):
            professional_assumptions["proxy_land_growth_pct"] = st.slider("연간 공시지가 상승률 proxy", 0.0, 15.0, 3.0, 0.5)
            professional_assumptions["official_to_appraisal_ratio_pct"] = st.slider("토지 공시가격/감정가 proxy", 10.0, 90.0, 55.0, 5.0)
            professional_assumptions["building_standard_ratio_pct"] = st.slider("건물 기준시가/감정가 proxy", 0.0, 60.0, 20.0, 5.0)


    st.sidebar.divider()
    status_rows = [
        {
            "소스": "ECOS",
            "상태": "API" if macro_context.get("source") == "한국은행 ECOS API" else "Fallback",
        },
        {
            "소스": "DART",
            "상태": "API" if dart_status == "connected" else "Local CSV",
        },
    ]
    st.sidebar.write("**데이터 소스 상태**")
    st.sidebar.dataframe(pd.DataFrame(status_rows), hide_index=True, width="stretch", height=140)
    st.sidebar.divider()
    st.sidebar.caption(
        "ECOS는 현재·과거 지표를 제공합니다. 전망 기반 확률가중 모드는 별도 전망 입력값을 사용해 "
        "호황·중립·불황 확률을 산정한 뒤 리츠 스트레스 값으로 변환합니다."
    )

    return {
        "selected_period": selected_period,
        "latest_kpi": latest_kpi,
        "latest_fin": latest_fin,
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
