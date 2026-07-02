import pandas as pd
import streamlit as st

from api_manager import sanitize_secret_text
from config import APP_VERSION_LABEL


def _source_confidence_table(asset_risk, debt_schedule, financials, kpis) -> pd.DataFrame:
    source_conf = pd.concat([
        asset_risk[["source_document", "source_confidence"]],
        debt_schedule[["source_document", "source_confidence"]],
        financials[["source_document", "source_confidence"]],
        kpis[["source_document", "source_confidence"]],
    ], ignore_index=True).drop_duplicates()
    return source_conf.rename(columns={
        "source_document": "자료 문서",
        "source_confidence": "자료 신뢰도",
    })


def _display_api_status(status: str) -> str:
    sanitized = sanitize_secret_text(status)
    return "API 연결 완료" if sanitized == "connected" else sanitized


def render_methodology_page(
    macro_context,
    macro_history_status,
    dart_status,
    financials,
    kpis,
    asset_risk,
    debt_schedule,
    source_plan,
    data_dictionary,
):
    st.markdown("## 분석 방법론 및 데이터 출처")
    st.caption(f"현재 안정 공개 버전: {APP_VERSION_LABEL}")

    st.markdown("### v11 현재 범위")
    st.dataframe(
        pd.DataFrame([
            {"화면": "일반 정보 및 시나리오", "목적": "REIT 기본 위험 프로필, 거시경제 Scenario 스트레스, 자산·부채 개요"},
            {"화면": "Assurance: 감사위험 분석", "목적": "감사계획, RMM(중요왜곡표시위험), KAM(핵심감사사항), 통제 대응 체크리스트"},
            {"화면": "Tax: 보유세 분석", "목적": "공시가격/기준시가 기반 보유세 추정, FFO 현금 유출 부담 분석"},
            {"화면": "분석 방법론 및 데이터 출처", "목적": "자료 출처, 추정 한계, API 보안 구조, 향후 개선 방향 설명"},
        ]),
        hide_index=True,
        width="stretch",
        height=176,
    )

    st.markdown("### 사용 데이터")
    source_status = pd.DataFrame([
        {"자료": "DART", "사용 목적": "재무제표와 최근 공시 목록 확인", "상태": _display_api_status(dart_status)},
        {"자료": "ECOS", "사용 목적": "거시경제 지표와 과거 금리 시계열 확인", "상태": _display_api_status(macro_history_status)},
        {"자료": "V-World / 공시가격 API", "사용 목적": "Tax 화면의 공시가격, 기준시가, 보유세 추정 입력값", "상태": "설정된 경우 사용 가능"},
        {"자료": "내부 CSV", "사용 목적": "공개 데모가 안정적으로 실행되도록 포함한 공시 기반 테이블", "상태": "앱에 포함"},
    ])
    st.dataframe(source_status, hide_index=True, width="stretch", height=190)

    st.markdown("### 계산 기준")
    st.write(
        "이 앱은 정식 의견서가 아니라 예비 분석 및 업무 검토 지원 도구입니다. 공시 재무제표, KPI, 자산별 정보, "
        "차입금 만기, 거시경제 지표, 공시가격 입력값을 연결해 Scenario 결과와 실무 체크리스트를 생성합니다."
    )
    st.write(
        "결과는 감사의견, 세무신고서, 법률 자문, 투자추천, 신용등급, 정식 가치평가 의견을 대체하지 않습니다. "
        "실무에 사용하려면 원천자료 대사와 전문가 검토가 필요합니다."
    )

    st.markdown("### API 연결 및 보안")
    st.write(
        "API Key는 Streamlit Secrets, 환경변수, 또는 개발자용 고급 설정의 세션 값에서만 불러옵니다. "
        "보안상 API Key는 화면에 표시하지 않으며, 디버그 문구와 API 응답도 표시 전 마스킹합니다."
    )
    st.info(
        "본 공개 버전은 서버에 저장된 API Key를 사용하도록 설계되어 있습니다. 사용자는 별도의 API Key를 "
        "발급하거나 입력할 필요가 없습니다. 보안상 API Key는 화면에 표시되지 않으며, 실시간 API 호출이 "
        "실패할 경우 내장 예시 데이터로 자동 전환됩니다."
    )

    with st.expander("자료 신뢰도 요약", expanded=False):
        st.dataframe(
            _source_confidence_table(asset_risk, debt_schedule, financials, kpis),
            width="stretch",
            hide_index=True,
            height=220,
        )

    with st.expander("데이터 사전", expanded=False):
        st.caption("원천 컬럼명은 재현성과 검증을 위해 일부 English identifier를 유지합니다.")
        st.dataframe(data_dictionary, width="stretch", hide_index=True, height=220)

    with st.expander("추가 자료 수집 계획", expanded=False):
        st.dataframe(source_plan, width="stretch", hide_index=True, height=220)

    st.markdown("### 한계 및 향후 개선 방향")
    st.write(
        "v11은 감사위험과 보유세 분석에 집중한 공개 포트폴리오 버전입니다. 향후 v12/v13에서는 데이터 연결이 더 안정화된 뒤 "
        "시장가격 기반 가치평가, 거래 분석, 다중 REIT 비교, 자료 대사 자동화 기능을 순차적으로 검토할 수 있습니다."
    )
