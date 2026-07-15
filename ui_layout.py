import streamlit as st

from config import APP_SUBTITLE, APP_TITLE, APP_VERSION_LABEL, PUBLIC_MODE_LABELS
from ui_common import render_user_mode_panel


PUBLIC_MODES = [
    "General Info & Scenario",
    "Tax",
    "Assurance",
    "Methodology & Data Sources",
]

SIDEBAR_SLOTS = {}


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
        section[data-testid="stSidebar"] div[data-baseweb="select"],
        section[data-testid="stSidebar"] div[data-baseweb="select"] *,
        div[data-baseweb="popover"] [role="listbox"],
        div[data-baseweb="popover"] [role="option"],
        div[data-baseweb="popover"] [role="option"] * {
            opacity: 1 !important;
            color: var(--text-color) !important;
            -webkit-text-fill-color: var(--text-color) !important;
        }
        div[data-baseweb="popover"] [role="option"][aria-selected="true"] {
            font-weight: 600 !important;
        }
        h2, h3 {margin-top: 0.35rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_mode_selector():
    st.sidebar.markdown(f"**{APP_TITLE}**")
    st.sidebar.caption(APP_VERSION_LABEL)
    st.sidebar.divider()
    SIDEBAR_SLOTS["mode"] = st.sidebar.container()
    SIDEBAR_SLOTS["company"] = st.sidebar.container()
    SIDEBAR_SLOTS["scenario"] = st.sidebar.container()
    SIDEBAR_SLOTS["assumptions"] = st.sidebar.container()
    SIDEBAR_SLOTS["data_status"] = st.sidebar.container()

    with SIDEBAR_SLOTS["mode"]:
        st.header("분석 모드")
        selected_user_mode = st.radio(
            "화면 선택",
            PUBLIC_MODES,
            index=0,
            format_func=lambda mode: PUBLIC_MODE_LABELS.get(mode, mode),
        )
        st.caption(
            "v15 Tax는 SK리츠의 SK서린빌딩을 대상으로 자산·필지·"
            "재산세 납세의무자 단위의 보유세 검토 흐름을 구현합니다."
        )
        st.divider()
    return selected_user_mode


def render_intro(selected_user_mode: str):
    st.title(APP_TITLE)
    st.caption(APP_VERSION_LABEL)

    if selected_user_mode != "General Info & Scenario":
        if selected_user_mode != "Tax":
            render_user_mode_panel(selected_user_mode)
        return

    st.info(APP_SUBTITLE)

    with st.expander("상장리츠 리스크 분석 개요", expanded=False):
        st.markdown(
            """
            **목적**
            상장리츠의 공시자료, 거시경제 지표, 자산별 정보, 공시가격 데이터를 연결하여
            감사위험과 보유세 부담을 한 화면에서 검토할 수 있도록 만든 분석 플랫폼입니다.

            **왜 만들었나요?**
            DART 공시나 리츠 투자보고서를 각각 읽는 것만으로는 금리, 차입금 만기, 자산 평가,
            임대 안정성, 보유세 부담이 서로 어떻게 연결되는지 빠르게 보기 어렵습니다. 이 앱은
            공시자료를 실무 검토 흐름에 맞게 재구성하여 먼저 볼 항목을 좁혀 줍니다.

            **누가 사용할 수 있나요?**
            리츠 업무를 처음 접하는 회계사와 감사·세무·자문 업무 담당자가 공개자료 기반으로
            먼저 확인할 위험 영역을 좁힐 수 있도록 설계했습니다.

            **v15 현재 범위**
            공개 버전은 일반 정보 및 시나리오, Tax: 보유세 분석, Assurance: 감사위험 분석,
            분석 방법론 및 데이터 출처에 집중합니다. v15 Tax는 SK리츠의 SK서린빌딩을
            핵심 분석대상 자산으로 선정하고, 자산대장, 필지·PNU, 재산세 납세의무자,
            공식 과세기초자료, 보유세 민감도, 주요 세무쟁점과 요청자료를 순서대로 연결합니다.
            """
        )

    with st.expander("필수 용어 및 분석 구조 보기", expanded=False):
        st.markdown(
            """
            - **REITs**: 다수 투자자로부터 자금을 모아 부동산에 투자하고 배당하는 부동산투자회사입니다.
            - **FFO proxy**: 공식 공시 FFO가 아니라, 확보 가능한 Snapshot `ffo_proxy` 또는 DART 영업활동현금흐름·영업이익·당기순이익을 사용한 비교 목적 proxy입니다.
            - **장부기준 NAV proxy**: 재무상태표상 총자산에서 총부채를 차감한 장부가액 기준 순자산입니다. 시가평가 NAV가 아닙니다.
            - **Cap rate proxy**: 자본환원율 proxy입니다. 자산별 평가액과 Cap rate가 있는 경우에만 사용하며 회사 전체 재무제표만으로 임의 산출하지 않습니다.
            - **WALE**: 가중평균 잔여 임대차기간입니다. 임차계약별 잔여기간과 가중치가 없으면 데이터 부족으로 봅니다.
            - **총자산 기준 차입비율**: 이자부 차입부채를 총자산으로 나눈 비율입니다. 담보가치 기준 LTV가 아니며 충당부채와 일반 영업채무는 분자에서 제외합니다.
            - **FFO 이자감당력 proxy**: FFO proxy를 이자비용으로 나눈 배율입니다. 이자비용이 결측이거나 0이면 데이터 부족으로 처리합니다.
            - **RMM**: 중요왜곡표시위험입니다. 감사계획에서 계정·공시별로 식별합니다.
            - **KAM**: 핵심감사사항입니다. 감사인이 특히 유의한 사항을 감사보고서에 설명할 때 사용합니다.
            """
        )

    with st.expander("시나리오 모델 설명", expanded=False):
        st.markdown(
            """
            이 시나리오 모델은 정식 가치평가 의견이 아니라 예비 검토용 분석입니다. 좌측 사이드바의
            예상 거시경제 상황에 따라 다음 항목을 함께 봅니다.

            - 금리 상승 또는 경기 둔화 시나리오에서 FFO proxy 하락 가정
            - Cap rate proxy 상승 가정에 따른 장부기준 NAV proxy 민감도
            - 차입 스프레드·리파이낸싱 금리 충격과 FFO 이자감당력 proxy
            - 자산 집중도, 주요 임차인, WALE 등 임대 안정성 지표
            """
        )

    render_user_mode_panel(selected_user_mode)
