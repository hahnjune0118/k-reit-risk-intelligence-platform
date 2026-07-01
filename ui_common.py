import pandas as pd
import streamlit as st

from formatting import _is_na, format_pct_from_100, format_ratio


USER_MODE_CONFIG = {
    "General Info & Scenario": {
        "title": "General Info & Scenario / 공통 정보·시나리오 관점",
        "goal": "SK리츠의 현재 상태, 거시경제 시나리오, NAV/FFO/주가 전이, 자산·부채·임대 안정성을 한 번에 확인합니다.",
        "decision": "Assurance·Tax·Deals 세부 분석에 들어가기 전, 공통으로 필요한 리츠의 위험 전이 경로와 기초 지표를 점검합니다.",
        "questions": [
            "선택한 금리·Cap rate 시나리오에서 FFO와 NAV가 얼마나 훼손되는가?",
            "KRX 시장가격은 공시 NAV를 얼마나 할인하고 있는가?",
            "최근 5년간 금리, NAV/FFO, 시가총액은 어떤 방향으로 움직였는가?",
            "자산·임차인·차입금 중 어떤 부분이 공통 위험의 핵심 원인인가?",
        ],
    },
    "Assurance": {
        "title": "Assurance / 리츠 감사·내부회계 관점",
        "goal": "리츠회사 재무제표 감사와 내부회계관리제도 감사에서 중요왜곡표시위험(RMM)을 조기에 식별합니다.",
        "decision": "투자부동산 공정가치, 차입금 유동성, 계속기업, 핵심감사사항(KAM), 내부통제 설계·운영위험을 연결해서 봅니다.",
        "questions": [
            "어떤 부동산 자산이 공정가치 평가위험이 가장 큰가?",
            "금리·Cap rate 변화가 투자부동산 평가와 KAM 선정에 어떤 영향을 주는가?",
            "차입금 만기와 이자 감당력이 계속기업 관련 중요한 불확실성 검토 신호가 되는가?",
            "내부회계관리제도에서 어떤 통제가 핵심으로 설계·운영되어야 하는가?",
        ],
    },
    "Tax": {
        "title": "Tax / 공시가격·기준시가 기반 보유세 관점",
        "goal": "한국부동산원/공시가격 API 또는 업로드 자료의 공시지가·기준시가를 활용해 자산별 보유세 부담을 심도 있게 추정합니다.",
        "decision": "양도세는 배제하고, 과세표준·세율·도시지역분·지방교육세·지가 상승에 따른 최근 5년 보유세 증가를 비교합니다.",
        "questions": [
            "어떤 자산이 공시가격 또는 기준시가 기준 보유세 부담이 큰가?",
            "공시지가 상승으로 최근 5년간 보유세가 얼마나 증가했는가?",
            "토지분 별도합산, 건축물분, 도시지역분, 지방교육세 중 어떤 항목이 부담을 키우는가?",
            "공시가격 데이터가 실제 API값인지, 업로드값인지, proxy인지 구분되는가?",
        ],
    },
    "Deals": {
        "title": "Deals / Buy-side · Sell-side 가치평가 관점",
        "goal": "상장리츠의 현재가치와 미래가치를 NAV, FFO, 배당수익률, KRX 시장가격으로 추정하고 검증합니다.",
        "decision": "공시 NAV와 실제 시가총액의 차이가 단순 저평가인지, 금리·차환·배당·자산가치 위험을 반영한 것인지 해석합니다.",
        "questions": [
            "현재 시가총액은 NAV와 FFO 대비 저평가인가, 아니면 위험을 반영한 가격인가?",
            "금리와 Cap rate 시나리오 후 미래 시장가치는 어느 범위까지 변할 수 있는가?",
            "Buy-side는 어떤 가격과 리스크 보정이 필요한가?",
            "Sell-side는 어떤 리스크를 설명하고 방어해야 하는가?",
        ],
    },
}


def render_user_mode_panel(selected_mode: str):
    cfg = USER_MODE_CONFIG[selected_mode]
    st.markdown("## 0. 사용자별 의사결정 관점")
    st.caption("같은 리츠 데이터라도 사용자에 따라 봐야 할 질문이 다릅니다. 이 섹션은 현재 선택한 사용자에게 필요한 해석 프레임을 먼저 보여줍니다.")
    c1, c2 = st.columns([0.9, 1.25])
    with c1:
        st.metric("현재 사용자 모드", cfg["title"])
        st.write(f"**활용 목적**: {cfg['goal']}")
        st.write(f"**의사결정 방식**: {cfg['decision']}")
    with c2:
        st.write("**먼저 던져야 할 질문**")
        for q in cfg["questions"]:
            st.write(f"- {q}")


def mode_specific_action_items(selected_mode: str) -> pd.DataFrame:
    rows = {
        "General Info & Scenario": [
            ("공통요약", "현재 NAV, FFO, 이자감당력, P/NAV, 자산집중도, 부채만기 구조를 먼저 확인"),
            ("시나리오", "ECOS 기반 거시경제 시나리오별 금리·Cap rate 충격이 FFO와 NAV에 미치는 영향 확인"),
            ("시장가격", "KRX 시가총액과 공시 NAV의 괴리를 통해 시장이 반영한 위험 프리미엄 확인"),
            ("세부모드", "이후 Assurance, Tax, Deals 모드에서 각각 감사·보유세·가치평가 관점으로 상세 분석"),
        ],
        "Assurance": [
            ("RMM", "투자부동산 공정가치 평가위험이 큰 자산부터 외부평가보고서·Cap rate·NOI 가정을 검토"),
            ("KAM", "평가액 비중, 민감도, 시장금리 변화, 공시 복잡성을 기준으로 핵심감사사항 후보 판단"),
            ("계속기업", "1년 내 만기 차입금, 차환 가능성, 이자 감당력, 현금 보유액, 배당정책을 함께 확인"),
            ("내부회계", "공정가치 평가 검토, 차입금 만기 모니터링, 특수관계자 거래 식별 통제 설계·운영 확인"),
        ],
        "Tax": [
            ("공시가격", "한국부동산원/공시가격 API 또는 CSV 업로드로 개별공시지가·건물 기준시가를 확보"),
            ("보유세", "토지·건축물 과세표준, 별도합산 토지세율, 도시지역분, 지방교육세를 분리해 계산"),
            ("5년 추이", "공시지가 상승이 보유세 증가로 어떻게 전이되었는지 자산별·연도별로 확인"),
            ("주의", "본 화면은 신고 목적 계산기가 아니라 preliminary estimator이며 세무전문가 검토가 필요"),
        ],
        "Deals": [
            ("NAV 모델", "시나리오 후 NAV에 적용 P/NAV multiple을 곱해 equity value range 산출"),
            ("FFO 모델", "시나리오 후 FFO에 P/FFO multiple을 적용해 반복 현금흐름 기반 시장가치 추정"),
            ("Backtesting", "과거 NAV·FFO·시가총액을 비교해 모델이 실제 KRX 가격을 과대/과소평가했는지 검증"),
            ("자문 포인트", "Buy-side 가격 보정, Sell-side 리스크 방어 논리, refinancing/asset recycling 논리 연결"),
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
