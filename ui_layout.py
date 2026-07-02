import streamlit as st

from config import APP_SUBTITLE, APP_TITLE, APP_VERSION_LABEL, PUBLIC_MODE_LABELS
from ui_common import render_user_mode_panel


PUBLIC_MODES = [
    "General Info & Scenario",
    "Assurance",
    "Tax",
    "Methodology & Data Sources",
]


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
    st.sidebar.header("분석 모드")
    selected_user_mode = st.sidebar.radio(
        "화면 선택",
        PUBLIC_MODES,
        index=0,
        format_func=lambda mode: PUBLIC_MODE_LABELS.get(mode, mode),
    )
    st.sidebar.caption("v11은 일반 정보, 감사위험 분석, 보유세 분석, 분석 방법론 화면에 집중합니다.")
    st.sidebar.divider()
    return selected_user_mode


def render_intro(selected_user_mode: str):
    st.title(APP_TITLE)
    st.caption(APP_VERSION_LABEL)
    st.info(APP_SUBTITLE)

    if selected_user_mode != "General Info & Scenario":
        render_user_mode_panel(selected_user_mode)
        return

    with st.expander("이 도구는 무엇을 하나요?", expanded=True):
        st.markdown(
            """
            **목적**
            이 도구는 상장리츠의 공시자료와 거시경제 지표, 자산별 정보, 공시가격 데이터를 연결하여
            리츠의 재무·세무·감사 리스크를 한 화면에서 검토할 수 있도록 만든 분석 플랫폼입니다.

            **왜 만들었나요?**
            DART 공시나 리츠 투자보고서를 각각 읽는 것만으로는 금리, 차입금 만기, 자산 평가,
            임대 안정성, 보유세 부담이 서로 어떻게 연결되는지 빠르게 보기 어렵습니다. 이 앱은
            공시자료를 실무 검토 흐름에 맞게 재구성하여 먼저 볼 항목을 좁혀 줍니다.

            **누가 사용할 수 있나요?**
            리츠 업무를 처음 접하는 회계사, 감사·세무·자문 업무 담당자, 그리고 회계/컨설팅
            디지털 전환 포트폴리오를 검토하는 사용자를 기준으로 설계했습니다.

            **v11 현재 범위**
            공개 버전은 일반 정보 및 시나리오, Assurance: 감사위험 분석, Tax: 보유세 분석,
            분석 방법론 및 데이터 출처에 집중합니다. 시장가격 기반 가치평가와 거래 분석은
            향후 버전에서 별도 모듈로 재검토할 예정입니다.
            """
        )

    with st.expander("필수 용어", expanded=False):
        st.markdown(
            """
            - **REIT**: 다수 투자자로부터 자금을 모아 부동산에 투자하고 배당하는 부동산투자회사입니다.
            - **FFO**: 리츠의 반복적 영업현금흐름에 가까운 지표로, 배당 여력과 현금 유출 부담을 볼 때 사용합니다.
            - **NAV**: 순자산가치입니다. 자산 평가액에서 부채를 차감한 지분가치의 proxy로 사용합니다.
            - **Cap rate**: 자본환원율입니다. 같은 임대수익이라도 Cap rate가 상승하면 부동산 평가가치는 하락합니다.
            - **WALE**: 가중평균 잔여 임대차기간입니다. 짧을수록 임대차 갱신 리스크가 커질 수 있습니다.
            - **LTV**: 담보가치 또는 자산가치 대비 부채 비율입니다.
            - **RMM**: 중요왜곡표시위험입니다. 감사계획에서 계정·공시별로 식별합니다.
            - **KAM**: 핵심감사사항입니다. 감사인이 특히 유의한 사항을 감사보고서에 설명할 때 사용합니다.
            """
        )

    with st.expander("시나리오 모델을 어떻게 읽나요?", expanded=True):
        st.markdown(
            """
            이 시나리오 모델은 정식 가치평가 의견이 아니라 예비 검토용 분석입니다. 좌측 사이드바의
            예상 거시경제 상황에 따라 다음 항목을 함께 봅니다.

            - 금리 상승 또는 경기 둔화 시나리오에서 FFO 하락 가정
            - Cap rate 상승 가정에 따른 NAV 민감도
            - 차입금 만기 부담과 이자 감당력
            - 자산 집중도, 주요 임차인, WALE 등 임대 안정성 지표
            """
        )

    render_user_mode_panel(selected_user_mode)
