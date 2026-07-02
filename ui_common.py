import pandas as pd
import streamlit as st

from config import PUBLIC_MODE_LABELS
from formatting import _is_na, format_pct_from_100, format_ratio


USER_MODE_CONFIG = {
    "General Info & Scenario": {
        "title": PUBLIC_MODE_LABELS["General Info & Scenario"],
        "goal": "REIT의 기본 재무상태, 거시경제 Scenario 민감도, 자산 집중도, 차입금 만기, NAV(순자산가치), FFO(반복적 영업현금흐름), 배당 여력을 함께 검토합니다.",
        "decision": "Assurance 또는 Tax 화면으로 이동하기 전에 공통 분석 기준을 잡는 화면입니다.",
        "questions": [
            "선택한 거시경제 Scenario에서 FFO, NAV, 이자 감당력, LTV가 얼마나 흔들리나요?",
            "어떤 자산, 임차인, 차입금 만기, 보유세 항목이 가장 먼저 확인해야 할 압박 요인인가요?",
            "어떤 공시자료 또는 원천문서를 먼저 대사해야 하나요?",
        ],
    },
    "Assurance": {
        "title": PUBLIC_MODE_LABELS["Assurance"],
        "goal": "리츠의 위험 지표를 감사계획, RMM(중요왜곡표시위험), KAM(핵심감사사항), 계속기업 검토, 내부회계관리제도 통제 포인트로 연결합니다.",
        "decision": "투자부동산 공정가치, 차입금 만기, 임대수익, 공시 통제 중 감사에서 우선 검토할 영역을 정합니다.",
        "questions": [
            "어떤 투자부동산이 공정가치 평가위험이 가장 높나요?",
            "Cap rate 상승과 차환 가정이 RMM 또는 KAM 후보에 어떤 영향을 주나요?",
            "평가 입력자료, 차입금 모니터링, 공시 작성 통제 중 어떤 통제를 테스트해야 하나요?",
        ],
    },
    "Tax": {
        "title": PUBLIC_MODE_LABELS["Tax"],
        "goal": "공시가격, 기준시가, CSV 업로드 또는 추정치(proxy) 가정을 사용해 리츠 보유자산의 보유세 부담과 FFO 현금 유출 영향을 추정합니다.",
        "decision": "자산별 재산세·도시지역분·지방교육세 부담, 자료 공백, 세무 자동화 가능 영역을 확인합니다.",
        "questions": [
            "어떤 자산이 가장 큰 보유세 부담을 만들고 있나요?",
            "공시가격 또는 지가 상승 시 추가 현금 유출이 FFO와 배당 여력을 얼마나 줄이나요?",
            "실무에 사용하기 전에 어떤 공시가격, 고지서, 면적 자료를 대사해야 하나요?",
        ],
    },
    "Methodology & Data Sources": {
        "title": PUBLIC_MODE_LABELS["Methodology & Data Sources"],
        "goal": "사용 데이터, 계산 방식, 가정, 한계, API Key 보안 구조, 버전 관리 기준을 설명합니다.",
        "decision": "분석 결과를 해석하기 전에 어떤 자료가 API, CSV, 사용자 업로드, 추정치에서 왔는지 확인합니다.",
        "questions": [
            "DART, ECOS, V-World, 내부 CSV 중 어떤 자료가 어느 표에 사용되나요?",
            "어떤 계산은 정식 의견이 아니라 예비 분석 또는 추정치인가요?",
            "v11 공개 버전에 포함된 범위와 향후 버전으로 미룬 범위는 무엇인가요?",
        ],
    },
}


def render_user_mode_panel(selected_mode: str):
    cfg = USER_MODE_CONFIG[selected_mode]
    st.markdown("## 0. 화면 이해하기")
    st.caption("같은 REIT 데이터를 감사, 세무, 방법론 관점에 맞게 다르게 읽을 수 있도록 구성했습니다.")
    c1, c2 = st.columns([0.9, 1.25])
    with c1:
        st.metric("현재 화면", cfg["title"])
        st.write(f"**목적**: {cfg['goal']}")
        st.write(f"**판단 관점**: {cfg['decision']}")
    with c2:
        st.write("**먼저 던질 질문**")
        for q in cfg["questions"]:
            st.write(f"- {q}")


def mode_specific_action_items(selected_mode: str) -> pd.DataFrame:
    rows = {
        "General Info & Scenario": [
            ("기준 상태", "NAV(순자산가치), FFO, 이자 감당력, LTV, 자산 집중도, 임차인 비중, 차입금 만기를 함께 확인합니다."),
            ("시나리오", "ECOS 기반 금리와 전망 입력값이 FFO, NAV, 이자 감당력, LTV 추정치에 미치는 영향을 확인합니다."),
            ("다음 업무", "감사위험 매핑은 Assurance 화면, 보유세 현금 유출 분석은 Tax 화면에서 이어서 검토합니다."),
        ],
        "Assurance": [
            ("RMM", "투자부동산 공정가치, 차환, 임대차 갱신, 공시 위험을 우선순위화합니다."),
            ("KAM", "평가 불확실성, Cap rate 민감도, 차입금 만기, 계속기업 검토 신호가 KAM 후보가 될 수 있는지 판단합니다."),
            ("내부통제", "평가 입력자료, 차입약정 모니터링, 공시 작성 프로세스에 대한 핵심 통제를 검토합니다."),
        ],
        "Tax": [
            ("공시가격 자료", "V-World/API, CSV 업로드, 또는 문서화된 추정치(proxy) 가정 중 어떤 자료를 사용했는지 확인합니다."),
            ("보유세", "토지분, 건물분, 도시지역분, 지방교육세 영향을 나누어 본 뒤 총 부담을 해석합니다."),
            ("현금흐름", "추가 보유세 현금 유출이 FFO와 배당 여력에 비해 어느 정도 부담인지 비교합니다."),
        ],
        "Methodology & Data Sources": [
            ("자료 기준", "DART, ECOS, V-World/API, 내부 CSV, 사용자 업로드 자료의 사용 위치를 확인합니다."),
            ("한계", "결과는 예비 검토용이며 감사의견, 세무신고, 정식 가치평가, 투자판단을 대체하지 않습니다."),
            ("버전 관리", "중요 기능이 추가되는 경우 v12, v13처럼 순차적으로 버전을 올립니다."),
        ],
    }
    return pd.DataFrame(rows[selected_mode], columns=["구분", "권장 확인사항"])


def compact_fig(fig, height=245):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=46, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def fmt_mn_to_bn(value):
    if _is_na(value):
        return "N/A"
    return f"{float(value)/1000:,.1f}십억원"


def fmt_metric_value(row, field):
    value = row[field]
    unit = row["unit"]
    if _is_na(value):
        return "N/A"
    if unit == "mn KRW":
        return fmt_mn_to_bn(value)
    if unit == "%":
        return format_pct_from_100(value)
    if unit == "x":
        return format_ratio(value)
    return str(value)
