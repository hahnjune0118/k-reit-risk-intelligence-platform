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
    peer_context=None,
):
    st.markdown("## 분석 방법론 및 데이터 출처")
    st.caption(f"현재 안정 공개 버전: {APP_VERSION_LABEL}")

    st.markdown("### v12 현재 범위")
    st.dataframe(
        pd.DataFrame([
            {"화면": "일반 정보 및 시나리오", "목적": "REIT 기본 위험 프로필, 거시경제 Scenario, Peer Benchmark 요약"},
            {"화면": "Assurance: 감사위험 분석", "목적": "감사계획, RMM(중요왜곡표시위험), KAM(핵심감사사항), Peer 기반 감사위험 Red Flag"},
            {"화면": "Tax: 보유세 분석", "목적": "공시가격/기준시가 기반 보유세 추정, Peer 기반 보유세 부담 Benchmark"},
            {"화면": "분석 방법론 및 데이터 출처", "목적": "자료 출처, Snapshot 구조, Red Flag 기준, 한계 및 보안 구조 설명"},
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
        {"자료": "REIT Peer Snapshot", "사용 목적": "v12 Peer Benchmark와 Red Flag Engine의 기본 입력값", "상태": "앱에 포함"},
        {"자료": "Red Flag Rules", "사용 목적": "Assurance 및 Tax 위험수준 판단 기준", "상태": "앱에 포함"},
        {"자료": "내부 CSV", "사용 목적": "공개 데모가 안정적으로 실행되도록 포함한 공시 기반 테이블", "상태": "앱에 포함"},
    ])
    st.dataframe(source_status, hide_index=True, width="stretch", height=230)

    st.markdown("### v12 Peer Benchmark 및 Red Flag 방법론")
    st.write(
        "Peer Benchmark는 `data/reit_peer_snapshot.csv`의 snapshot 데이터를 기준으로 선택 리츠와 상장리츠 peer group을 비교합니다. "
        "총자산, 투자부동산, 차입금, FFO(리츠의 반복적 영업현금흐름에 가까운 지표), 배당, 보유세, 공시가격 입력값을 이용해 "
        "감사위험과 보유세 부담 관련 비율을 계산합니다."
    )
    st.write(
        "Red Flag 판단은 `data/red_flag_rules.json`의 규칙을 사용합니다. 각 규칙은 절대 기준과 peer percentile을 함께 보며, "
        "정상·주의·높음·데이터 부족으로 표시합니다. 데이터가 없거나 0으로 나누는 계산은 강제로 추정하지 않고 데이터 부족으로 표시합니다."
    )
    st.info(
        "앱 실행 시 모든 상장리츠의 DART API를 실시간 호출하지 않습니다. 공개 배포 버전에서는 빠른 실행과 안정성을 위해 "
        "Snapshot 데이터를 기본으로 사용하고, 필요 시 별도 수집 스크립트로 갱신할 수 있도록 설계했습니다."
    )
    if peer_context:
        peer_metrics = peer_context.get("peer_metrics", pd.DataFrame())
        rules = peer_context.get("red_flag_rules", {})
        st.dataframe(
            pd.DataFrame([
                {"항목": "Peer 회사 수", "값": peer_metrics["company_name"].nunique() if not peer_metrics.empty and "company_name" in peer_metrics.columns else 0},
                {"항목": "Assurance 규칙 수", "값": len(rules.get("assurance", []))},
                {"항목": "Tax 규칙 수", "값": len(rules.get("tax", []))},
                {"항목": "자료 기준", "값": "Snapshot 기준 / sample_snapshot은 공식·감사 확정 데이터가 아닌 예시 데이터"},
            ]),
            hide_index=True,
            width="stretch",
            height=176,
        )

    st.markdown("### 계산 기준")
    st.write(
        "이 앱은 정식 의견서가 아니라 예비 분석 및 업무 검토 지원 도구입니다. 공시 재무제표, KPI, 자산별 정보, "
        "차입금 만기, 거시경제 지표, 공시가격 입력값을 연결해 Scenario 결과와 실무 체크리스트를 생성합니다."
    )
    st.write(
        "결과는 감사의견, 세무신고서, 법률 자문, 투자추천, 신용등급, 정식 가치평가 의견을 대체하지 않습니다. "
        "실무에 사용하려면 원천자료 대사와 전문가 검토가 필요합니다."
    )

    st.markdown("### 데이터 연결 및 보안")
    st.write(
        "외부 데이터 인증값은 서버 측 데이터 연결 설정 또는 환경변수에서만 불러옵니다. "
        "보안상 인증값은 화면에 표시하지 않으며, 디버그 문구와 API 응답도 표시 전 마스킹합니다."
    )
    st.info(
        "본 공개 버전은 서버 측 데이터 연결 설정을 사용하도록 설계되어 있습니다. 사용자는 별도의 인증키를 "
        "입력할 필요가 없으며, 실시간 데이터 연결이 제한될 경우 예시 데이터로 자동 전환됩니다."
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
        "v12는 감사위험, 보유세 분석, Peer Benchmark, Red Flag Engine에 집중한 공개 포트폴리오 버전입니다. "
        "향후 v13 이후에는 문서 추출, 요청자료 export, AI-assisted memo drafting, 다기간 peer trend 비교를 검토할 수 있습니다."
    )
