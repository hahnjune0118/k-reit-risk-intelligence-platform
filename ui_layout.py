import streamlit as st

from config import APP_TITLE
from ui_common import render_user_mode_panel


def apply_page_config():
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.3rem; padding-bottom: 2rem; max-width: 1380px;}
        div[data-testid="stMetric"] {background: rgba(128,128,128,0.06); border: 1px solid rgba(128,128,128,0.18); border-radius: 12px; padding: 0.65rem 0.75rem;}
        div[data-testid="stMetricLabel"] {font-size: 0.78rem;}
        div[data-testid="stMetricValue"] {font-size: 1.25rem;}
        div[data-testid="stDataFrame"] {font-size: 0.82rem;}
        h2, h3 {margin-top: 0.35rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_mode_selector():
    st.sidebar.header("사용자 모드")
    selected_user_mode = st.sidebar.radio(
        "어떤 화면을 볼까요?",
        ["General Info & Scenario", "Assurance", "Tax", "Deals"],
        index=0,
    )
    st.sidebar.caption("공통 정보·시나리오와 Assurance·Tax·Deals 전문 분석을 분리해 표시합니다.")
    st.sidebar.divider()
    return selected_user_mode


def render_intro(selected_user_mode: str):
    st.title(APP_TITLE)
    st.caption(
        "Phase 1 — SK리츠 고도화 · General Info & Scenario / Assurance / Tax / Deals 분리형 분석"
    )

    st.info(
        "이 도구는 리츠정보시스템·DART·ECOS·KRX처럼 원천 데이터를 조회하는 포털을 대체하지 않습니다. "
        "대신 SK리츠 사례를 기준으로 공시자료, 거시경제 지표, 주가·시가총액 데이터를 연결해 "
        "General Info & Scenario는 공통 리츠 정보와 거시경제 시나리오를, Assurance는 RMM/KAM/계속기업/내부회계 위험을, Tax는 공시가격·기준시가 기반 보유세를, Deals는 NAV/FFO 기반 시장가치와 KRX 검증을 분리해서 해석합니다."
    )

    if selected_user_mode != "General Info & Scenario":
        render_user_mode_panel(selected_user_mode)
        return

    with st.expander("이 도구는 무엇을 하고, 왜 유용한가요?", expanded=True):
        st.markdown(
            """
            **무엇을 하나요?**  
            공시자료에 흩어진 리츠의 자산, 임차인, 차입금, 배당, 순자산 정보를 모아
            선택한 거시경제 시나리오에서 재무지표가 얼마나 악화되는지 보여줍니다.

            **왜 만들었나요?**  
            리츠는 배당률만 보고 판단하기 쉽지만, 실제 위험은 금리 상승, 차환 부담,
            부동산 가치 하락, 임차인 집중도에서 발생합니다. 이 도구는 그 위험을 초보자도 볼 수 있게
            숫자와 그래프로 단순화합니다.

            **누구에게 유용한가요?**  
            리츠회사 재무제표·내부회계관리제도 감사를 수행하는 Assurance 팀,
            공시가격·기준시가 기반 보유세 부담을 검토하는 Tax 팀,
            그리고 buy-side/sell-side 가치평가와 리파이낸싱 자문을 수행하는 Deals 팀에게 유용합니다.
            """
        )

    with st.expander("필수 용어 간단 설명", expanded=False):
        st.markdown(
            """
            - **현금흐름(FFO)**: 리츠가 임대수익 등으로 벌어들인 현금창출력을 보는 지표입니다. 배당 여력을 볼 때 중요합니다.
            - **순자산가치(NAV)**: 리츠가 보유한 부동산 가치에서 부채를 뺀 순자산입니다.
            - **Cap rate(자본환원율)**: 부동산 임대수익을 부동산 가치로 나눈 비율입니다. 이 비율이 올라가면 같은 임대수익의 부동산 가치는 내려갑니다.
            - **이자 감당력**: 벌어들인 현금흐름이 이자비용을 몇 배나 감당하는지 보는 지표입니다.
            - **LTV(부채비율)**: 부동산 가치 대비 부채가 얼마나 큰지 보는 지표입니다. 값이 높을수록 차환과 담보 여력이 약해질 수 있습니다.
            - **차환**: 만기가 온 빚을 새 대출이나 회사채로 다시 빌려 갚는 것입니다.
            """
        )


    with st.expander("핵심 가치평가 모형: 지표가 NAV에 영향을 주는 경로", expanded=True):
        st.markdown(
            """
            이 앱의 계산은 정식 감정평가가 아니라, 리츠를 빠르게 이해하기 위한 **스크리닝 모형**입니다.
            핵심 관계는 아래와 같습니다.

            **1) 순자산가치(NAV)**  
            `NAV ≈ 보유 부동산 가치 + 기타자산 - 부채`  
            부동산 가치가 내려가거나 부채 부담이 커지면 NAV가 감소합니다.

            **2) 부동산 가치와 Cap rate**  
            `부동산 가치 ≈ 임대순수익(NOI) / Cap rate`  
            같은 임대수익이라도 Cap rate가 올라가면 부동산 가치는 하락합니다. 그래서 Cap rate 상승은 NAV 하락 요인입니다.

            **3) 금리와 현금흐름(FFO)**  
            `시나리오 후 FFO ≈ 현재 FFO - 영업 하락분 - 추가 이자비용`  
            금리가 오르거나 차환금리가 높아지면 이자비용이 늘고, 배당 재원이 되는 FFO가 줄어듭니다.

            **4) 이자 감당력**  
            `이자 감당력 ≈ FFO / 이자비용`  
            이 값이 낮아질수록 배당 유지와 차환 안정성이 약해질 수 있습니다.

            **5) 부채비율 추정치(LTV)**  
            `LTV ≈ 이자부채 / 부동산 가치`  
            Cap rate 상승으로 부동산 가치가 하락하면 같은 부채라도 LTV가 올라가 담보 여력이 약해질 수 있습니다.

            **6) 시장이 반영한 위험(P/NAV)**  
            `P/NAV = 시가총액 / 순자산가치`  
            P/NAV가 1보다 낮으면 시장이 공시 순자산가치보다 낮은 가격으로 리츠를 평가한다는 뜻입니다.
            이 할인은 단순 저평가일 수도 있지만, 차환위험·배당위험·평가가정 불신을 반영한 것일 수도 있습니다.
            """
        )

    render_user_mode_panel(selected_user_mode)
