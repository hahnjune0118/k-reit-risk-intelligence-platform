import pandas as pd
import streamlit as st

from api_manager import sanitize_secret_text
from config import APP_VERSION_LABEL
from data_source_policy import source_policy_table
from ui_common import render_selected_company_header


def _source_confidence_table(asset_risk, debt_schedule, financials, kpis) -> pd.DataFrame:
    frames = []
    for frame in [asset_risk, debt_schedule, financials, kpis]:
        if frame is not None and not frame.empty and {"source_document", "source_confidence"}.issubset(frame.columns):
            frames.append(frame[["source_document", "source_confidence"]])
    if not frames:
        return pd.DataFrame(columns=["자료 문서", "자료 신뢰도"])
    source_conf = pd.concat(frames, ignore_index=True).drop_duplicates()
    return source_conf.rename(columns={"source_document": "자료 문서", "source_confidence": "자료 신뢰도"})


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
    render_selected_company_header(peer_context)
    st.caption(f"현재 안정 공개 버전: {APP_VERSION_LABEL}")

    st.markdown("### v14 Tax Workflow Control 구조")
    st.dataframe(
        pd.DataFrame(
            [
                {"단계": "1. Source policy", "내용": "자료 출처를 공식 공시, Snapshot, Peer 추정, 데이터 부족으로 표준화"},
                {"단계": "2. Holding tax bridge", "내용": "공시가격 또는 장부가액에서 과세표준, 추정 보유세, FFO 부담으로 연결"},
                {"단계": "3. Validation", "내용": "결측, fallback 사용, 0 denominator, 비정상 비율을 별도 검증 패널로 표시"},
                {"단계": "4. Issue workflow", "내용": "Tax Issue Matrix를 요청자료 리스트와 Memo 초안으로 연결"},
                {"단계": "5. Export", "내용": "Memo, Issue Matrix, Reconciliation, Request List를 검토용 파일로 다운로드"},
            ]
        ),
        hide_index=True,
        width="stretch",
        height=210,
    )

    st.markdown("### 활성 공개 화면")
    st.dataframe(
        pd.DataFrame(
            [
                {"화면": "일반 정보 및 시나리오", "목적": "REIT 기본 위험 프로필, 거시경제 Scenario, Peer Benchmark 요약"},
                {"화면": "Tax: 보유세 분석", "목적": "Tax Summary, 보유세 브리지, Issue Matrix, Reconciliation, FFO Stress, Request List, Memo, Export, Validation"},
                {"화면": "Assurance: 감사위험 분석", "목적": "감사계획, RMM, KAM, Peer 기반 감사위험 Red Flag"},
                {"화면": "분석 방법론 및 데이터 출처", "목적": "자료 출처, Snapshot 구조, Red Flag 기준, 한계 및 공개 런타임 구조 설명"},
            ]
        ),
        hide_index=True,
        width="stretch",
        height=176,
    )

    st.markdown("### Source Type Taxonomy")
    st.caption("Tax 화면의 배너, source expander, 요청자료 리스트, Memo 제한 문구는 같은 source policy를 사용합니다.")
    st.dataframe(source_policy_table(), hide_index=True, width="stretch", height=260)

    st.markdown("### 데이터 사용 원칙")
    st.write(
        "공개 런타임은 앱 시작 시 모든 상장리츠의 DART 자료를 일괄 호출하지 않습니다. 선택 회사와 내장 Snapshot을 중심으로 "
        "빠르게 실행되며, 실시간 연결이 제한되면 예시 데이터로 안정적으로 전환합니다."
    )
    st.write(
        "SK리츠의 자산·임차인·차입금 상세 sample은 SK리츠 선택 시에만 사용합니다. 다른 회사는 회사 전체 Snapshot과 "
        "Peer 기반 추정 행으로 표시하며, SK리츠 자산 목록이나 상세 데이터를 재사용하지 않습니다."
    )
    st.info(
        "Tax 산출물은 신고 목적의 확정 세액, 법률의견, 투자 추천, 정식 가치평가 의견을 제공하지 않습니다. "
        "실무 사용 전에는 원자료 확인, 회사 확인, 세무 전문가 검토가 필요합니다."
    )

    st.markdown("### 사용 데이터")
    source_status = pd.DataFrame(
        [
            {"자료": "DART", "사용 목적": "재무제표와 최근 공시 목록 확인", "상태": _display_api_status(dart_status)},
            {"자료": "ECOS", "사용 목적": "거시경제 지표와 과거 금리 시계열 확인", "상태": _display_api_status(macro_history_status)},
            {"자료": "공시가격 계열 데이터", "사용 목적": "Tax 화면의 공시가격, 기준시가, 보유세 추정 입력값", "상태": "제한 시 예시 데이터 사용"},
            {"자료": "REIT Peer Snapshot", "사용 목적": "Peer Benchmark와 Red Flag Engine의 기본 입력값", "상태": "앱에 포함"},
            {"자료": "REIT Tax Snapshot", "사용 목적": "회사별 보유세 fallback 및 bridge 입력값", "상태": "앱에 포함"},
            {"자료": "Red Flag Rules", "사용 목적": "Assurance 및 Tax 위험수준 판단 기준", "상태": "앱에 포함"},
            {"자료": "내장 CSV", "사용 목적": "공개 데모가 안정적으로 실행되도록 포함한 공시 기반 테이블", "상태": "앱에 포함"},
        ]
    )
    st.dataframe(source_status, hide_index=True, width="stretch", height=230)

    st.markdown("### Peer Benchmark 및 Red Flag 방법론")
    st.write(
        "Peer Benchmark는 `data/reit_peer_snapshot.csv`의 Snapshot 데이터를 기준으로 선택 리츠와 상장리츠 peer group을 비교합니다. "
        "총자산, 투자부동산, 차입금, FFO, 배당, 보유세, 공시가격 입력값을 이용해 감사위험과 보유세 부담 관련 비율을 계산합니다."
    )
    st.write(
        "Red Flag 판단은 `data/red_flag_rules.json`의 규칙을 사용합니다. 각 규칙은 절대 기준과 peer percentile을 함께 보며, "
        "정상·주의·높음·데이터 부족으로 표시합니다. 데이터가 없거나 0으로 나누는 계산은 강제로 추정하지 않고 데이터 부족으로 표시합니다."
    )

    st.markdown("### Tax 계산 및 검증 기준")
    st.write(
        "Tax mode는 `build_company_tax_dataset`으로 선택 회사의 tax dataset을 만들고, `build_holding_tax_bridge`로 공시가격 또는 "
        "장부가액에서 과세표준과 추정 보유세를 연결합니다. `validate_tax_inputs`는 결측, fallback, denominator 안정성을 별도로 표시합니다."
    )
    st.caption(
        "회사별 상세 자료가 부족한 경우 `회사 전체 추정` 행과 `source_type = peer_snapshot_estimate`가 표시됩니다. "
        "이 값은 공식 고지세액이 아닌 공개자료 및 Snapshot 기반 예비 검토용 입력값입니다."
    )

    st.markdown("### 데이터 연결 및 공개 런타임")
    st.write(
        "외부 데이터 인증값은 서버 측 데이터 연결 설정 또는 환경변수에서만 불러옵니다. 인증값은 화면에 표시하지 않으며, "
        "디버그 문구와 API 응답도 표시 전 마스킹합니다."
    )
    st.info(
        "본 공개 버전은 서버 측 데이터 연결 설정을 사용하도록 설계되어 있습니다. 사용자는 별도의 인증값을 입력할 필요가 없으며, "
        "실시간 데이터 연결이 제한될 경우 예시 데이터로 자동 전환됩니다."
    )

    with st.expander("자료 신뢰도 요약", expanded=False):
        st.dataframe(_source_confidence_table(asset_risk, debt_schedule, financials, kpis), width="stretch", hide_index=True, height=220)

    with st.expander("데이터 사전", expanded=False):
        st.caption("원천 컬럼명은 재현성과 검증을 위해 일부 English identifier를 유지합니다.")
        st.dataframe(data_dictionary, width="stretch", hide_index=True, height=220)

    with st.expander("추가 자료 수집 계획", expanded=False):
        st.dataframe(source_plan, width="stretch", hide_index=True, height=220)
