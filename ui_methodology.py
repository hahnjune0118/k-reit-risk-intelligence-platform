import pandas as pd
import streamlit as st

from api_manager import sanitize_secret_text
from config import APP_VERSION_LABEL
from data_source_policy import source_policy_table
from metric_definitions import metric_definition_table, metric_lineage_table
from src.tax_v15.constants import SOURCE_BADGES
from src.tax_v15.loaders import load_v15_bundle
from src.tax_v15.validation import summarize_coverage
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
    return "연결 준비 완료" if sanitized == "connected" else sanitized


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
    del macro_context
    st.markdown("## 분석 방법론 및 데이터 출처")
    render_selected_company_header(peer_context)
    st.caption(f"현재 공개 버전: {APP_VERSION_LABEL}")

    st.markdown("### v15 검토 범위")
    st.info(
        "v15는 회사 전체 장부가액이나 Peer 비율로 보유세를 추정하지 않습니다. 공식 출처가 연결된 자산·필지·건축물·"
        "납세의무자 자료만 세목별 계산에 사용하고, 필수 근거가 없으면 데이터 부족 또는 수동 검토로 차단합니다."
    )

    st.markdown("### 왜 상장리츠를 분석 대상으로 선택했나요?")
    st.write(
        "상장리츠는 다양한 업종 중에서도 수익 인식 구조가 비교적 단순한 편입니다. 주요 수익은 보유 부동산에서 발생하는 "
        "임대료이며, 기본적으로 월 임대료와 임대기간을 바탕으로 이해할 수 있습니다. 기업 내부 장부, 세부 임대차계약, "
        "감사조서 등 비공개 자료를 입수할 수 없는 환경에서도 사업보고서, 분기보고서, 공시자료와 공시가격 관련 자료를 통해 "
        "자산 구성, 임대수익, 차입금, 공정가치 평가, 배당 및 보유세 부담의 기초 정보를 구조화할 수 있습니다."
    )
    st.caption(
        "실제 감사조서나 회사 내부자료를 대체하지 않으며, 공개자료를 이용한 감사계획 단계의 위험평가와 Tax/Assurance "
        "검토 포인트를 초기 선별하는 것이 목적입니다."
    )

    st.markdown("### v15 Tax 데이터 흐름")
    st.dataframe(
        pd.DataFrame(
            [
                {"단계": "1. REIT Inventory", "검토 내용": "실행일 현재 공식 상장리츠 목록과 원천 URL 확인"},
                {"단계": "2. Asset Registry", "검토 내용": "직접·간접 보유자산, 주소, 법적 소유자와 지분 구조화"},
                {"단계": "3. Taxpayer", "검토 내용": "6월 1일 현재 소유자, 신탁 위탁자와 실제 납세의무자 판정"},
                {"단계": "4. Parcel / PNU", "검토 내용": "복수 필지, PNU, 면적, 소유지분과 기준연도 개별공시지가 연결"},
                {"단계": "5. Official Tax Base", "검토 내용": "토지·건축물 공식 입력값만 과세표준 계산에 사용"},
                {"단계": "6. Classification", "검토 내용": "분리·별도·종합합산, 도시지역분과 소방분 적용요건 검증"},
                {"단계": "7. Calculation", "검토 내용": "Tax Rule Master의 공식 검증 세율·구간·비율 적용"},
                {"단계": "8. Validation", "검토 내용": "출처·완전성·중복·납세의무자·고지서 대사 통제"},
                {"단계": "9. Review Output", "검토 내용": "요청자료와 Tax Review Memo·검토문서 생성"},
            ]
        ),
        hide_index=True,
        width="stretch",
        height=355,
    )

    st.markdown("### 계산 상태와 Source Badge")
    st.dataframe(
        pd.DataFrame(
            [
                {"상태": status, "화면 표시": label, "의미": meaning}
                for status, label, meaning in [
                    ("verified_notice", SOURCE_BADGES["verified_notice"], "실제 고지서 또는 과세내역서 확인"),
                    ("official_source_calculated", SOURCE_BADGES["official_source_calculated"], "공식 입력값과 검증된 규칙으로 계산"),
                    ("official_partial", SOURCE_BADGES["official_partial"], "공식 근거가 일부만 확보됨"),
                    ("manual_review_required", SOURCE_BADGES["manual_review_required"], "법적 분류나 핵심 입력값에 전문가 판단 필요"),
                    ("data_insufficient", SOURCE_BADGES["data_insufficient"], "필수 자료 부족으로 계산 불가"),
                    ("not_applicable", SOURCE_BADGES["not_applicable"], "검증된 법적 분류상 해당 세목 비적용"),
                ]
            ]
        ),
        hide_index=True,
        width="stretch",
        height=250,
    )
    st.warning(
        "상장 여부만으로 분리과세를 확정하지 않습니다. 법적 소유자, 과세기준일, 공모리츠 요건, 목적사업 사용, 신탁관계, "
        "자산 분류를 모두 확인하기 전에는 종합부동산세 비과세 결론도 자동 확정하지 않습니다."
    )

    bundle = load_v15_bundle()
    coverage = summarize_coverage(bundle.assets, bundle.parcels, bundle.buildings, bundle.taxpayers, bundle.calculations)
    st.markdown("### 현재 공개 Snapshot Coverage")
    st.write(
        f"공식 목록 {len(bundle.reits)}개 리츠 · 식별 자산 {coverage['asset_count']}건 · "
        f"주소 검증 {coverage['verified_address_count']}건 · PNU 검증 {coverage['verified_pnu_count']}건 · "
        f"개별공시지가 확인 {coverage['verified_land_price_count']}건 · "
        f"건축물 시가표준액 확인 {coverage['verified_building_value_count']}건"
    )
    st.caption(
        "Coverage가 0인 항목은 0원으로 가정한 것이 아니라 공식 근거가 확보되지 않아 계산에서 제외한 항목입니다. "
        "리츠별 차단사유와 다음 조치는 docs/v15/COVERAGE_REPORT.md에 기록합니다."
    )

    st.markdown("### Tax Rule Master와 법령 통제")
    st.write(
        "재산세, 도시지역분, 지방교육세, 소방분 지역자원시설세, 토지분 종합부동산세와 농어촌특별세 규칙은 "
        "`data/v15/tax_rule_master.csv`에서 과세연도·법령·조문·시행기간·공식 URL과 함께 관리합니다. "
        "`official_verified` 상태와 공식 URL이 모두 있는 규칙만 계산 엔진이 읽습니다."
    )
    st.caption(
        "실제 신고·납부 전에는 해당 과세연도의 개정 법령, 지방자치단체 조례, 감면, 세부담상한, 고지내역을 다시 확인해야 합니다."
    )

    st.markdown("### 사용 데이터와 연결 상태")
    st.dataframe(
        pd.DataFrame(
            [
                {"자료": "DART", "사용 목적": "재무제표·정기공시 확인", "상태": _display_api_status(dart_status)},
                {"자료": "ECOS", "사용 목적": "거시경제 지표·금리 시계열", "상태": _display_api_status(macro_history_status)},
                {"자료": "리츠정보시스템", "사용 목적": "상장리츠 공식 목록", "상태": f"Snapshot {len(bundle.reits)}개"},
                {"자료": "공식 리츠 홈페이지·IR", "사용 목적": "자산·주소·소유구조 근거", "상태": f"Manifest {len(bundle.documents)}건"},
                {"자료": "V-World 등 공시가격 데이터", "사용 목적": "PNU·개별공시지가 공식 조회", "상태": "공식 응답 Snapshot만 사용"},
                {"자료": "v15 내부 CSV", "사용 목적": "Source lineage와 검토 상태 보존", "상태": "앱에 포함"},
            ]
        ),
        hide_index=True,
        width="stretch",
        height=250,
    )
    st.info(
        "공개 버전은 서버 측 데이터 연결 설정을 사용합니다. 사용자가 인증값을 입력할 필요가 없으며, 실시간 연결이 제한되면 "
        "검증된 Snapshot을 사용하거나 해당 항목을 데이터 부족으로 표시합니다. 인증값은 화면·로그·다운로드에 표시하지 않습니다."
    )

    st.markdown("### General·Assurance 재무지표 방법론")
    st.caption("아래 지표는 General 및 Assurance 화면에 사용되며 v15 Tax 세액 계산의 대체 입력값으로 사용하지 않습니다.")
    st.dataframe(
        metric_definition_table(),
        hide_index=True,
        width="stretch",
        height=340,
        column_config={
            "구분": st.column_config.TextColumn("구분", width="small"),
            "지표": st.column_config.TextColumn("지표", width="medium"),
            "정의": st.column_config.TextColumn("정의", width="medium"),
            "계산식": st.column_config.TextColumn("계산식", width="large"),
            "사용 데이터": st.column_config.TextColumn("사용 데이터", width="large"),
            "제한사항": st.column_config.TextColumn("제한사항", width="large"),
        },
    )
    with st.expander("지표별 데이터 계보", expanded=False):
        st.dataframe(metric_lineage_table(), hide_index=True, width="stretch", height=230)
    with st.expander("General·Assurance Source Type 정책", expanded=False):
        st.dataframe(source_policy_table(), hide_index=True, width="stretch", height=260)
    with st.expander("자료 신뢰도 요약", expanded=False):
        st.dataframe(
            _source_confidence_table(asset_risk, debt_schedule, financials, kpis),
            width="stretch",
            hide_index=True,
            height=220,
        )
    with st.expander("데이터 사전", expanded=False):
        st.dataframe(data_dictionary, width="stretch", hide_index=True, height=220)
    with st.expander("추가 자료 수집 계획", expanded=False):
        st.dataframe(source_plan, width="stretch", hide_index=True, height=220)
