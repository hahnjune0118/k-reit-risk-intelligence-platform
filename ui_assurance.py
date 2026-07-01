import pandas as pd
import streamlit as st

from calculations_assurance import (
    build_assurance_asset_priority,
    build_assurance_workpaper_index,
    build_audit_workflow_checklist,
    build_icfr_control_points,
    build_kam_candidate_table,
    build_rmm_assertion_checklist,
    build_rmm_mapping,
)


def _stage_rows(workflow: pd.DataFrame, stages: list[str]) -> pd.DataFrame:
    return workflow[workflow["감사단계"].isin(stages)].reset_index(drop=True)


def _render_checklist(df: pd.DataFrame, key: str, height: int = 360):
    disabled_cols = [col for col in df.columns if col != "완료"]
    st.data_editor(
        df,
        width="stretch",
        hide_index=True,
        height=height,
        disabled=disabled_cols,
        key=key,
    )


def render_assurance_mode(
    asset_risk: pd.DataFrame,
    debt_schedule: pd.DataFrame,
    latest_kpi: pd.Series,
    scenario: dict,
    materiality_pct: float,
):
    st.markdown("## A. Assurance 모드: 감사계획·RMM·KAM·내부회계 관점")
    st.caption(
        "목적: 리츠회사 감사인이 기업과 기업환경의 이해, 위험평가절차, 통제테스트, 실증절차 순서로 "
        "중요왜곡표시위험(RMM)과 KAM 후보, 내부회계관리제도 테스트 포인트를 문서화할 수 있게 합니다."
    )

    assurance_assets = build_assurance_asset_priority(asset_risk, scenario, materiality_pct)
    rmm = build_rmm_mapping(latest_kpi, debt_schedule, scenario, assurance_assets)
    kam = build_kam_candidate_table(scenario, assurance_assets, debt_schedule, latest_kpi)
    icfr = build_icfr_control_points()
    workflow = build_audit_workflow_checklist(latest_kpi, debt_schedule, scenario, assurance_assets)
    rmm_assertions = build_rmm_assertion_checklist(latest_kpi, debt_schedule, scenario, assurance_assets)
    workpaper_index = build_assurance_workpaper_index()

    tab_plan, tab_rmm, tab_response, tab_report = st.tabs(
        ["감사계획·위험평가", "RMM·자산 우선순위", "통제테스트·실증절차", "KAM·ICFR·보고"]
    )

    with tab_plan:
        st.write("**기업과 기업환경의 이해 및 위험평가절차 체크리스트**")
        _render_checklist(
            _stage_rows(workflow, ["기업과 기업환경 이해", "위험평가절차"]),
            "assurance_planning_checklist",
            height=480,
        )

    with tab_rmm:
        a1, a2 = st.columns([1.15, 1.0])
        with a1:
            st.write("**감사 중점 자산 우선순위**")
            st.caption("`시나리오가치변화_%`는 좌측 사이드바의 예상 거시경제 상황과 Cap rate 충격 가정에 따라 즉시 달라집니다.")
            st.dataframe(assurance_assets.head(8), width="stretch", hide_index=True, height=260)
        with a2:
            st.write("**RMM 요약 매핑**")
            st.caption("투자부동산 공정가치 RMM은 선택 시나리오명과 Cap rate 충격을 함께 표시합니다.")
            st.dataframe(rmm, width="stretch", hide_index=True, height=260)

        st.write("**계정·공시 및 경영진 주장별 RMM 체크리스트**")
        st.dataframe(rmm_assertions, width="stretch", hide_index=True, height=320)

    with tab_response:
        st.write("**통제테스트 및 실증절차 체크리스트**")
        _render_checklist(
            _stage_rows(workflow, ["통제테스트", "실증절차"]),
            "assurance_response_checklist",
            height=500,
        )

        st.write("**내부회계관리제도 핵심 통제 포인트**")
        st.dataframe(icfr, width="stretch", hide_index=True, height=220)

    with tab_report:
        b1, b2 = st.columns([1.0, 1.05])
        with b1:
            st.write("**KAM 후보와 감사보고서 고려사항**")
            st.dataframe(kam, width="stretch", hide_index=True, height=230)
        with b2:
            st.write("**보고·KAM·커뮤니케이션 체크리스트**")
            _render_checklist(
                _stage_rows(workflow, ["보고·KAM·커뮤니케이션"]),
                "assurance_reporting_checklist",
                height=230,
            )

        st.write("**감사 작업문서 인덱스**")
        st.dataframe(workpaper_index, width="stretch", hide_index=True, height=300)

    st.warning(
        "계속기업 관련 중요한 불확실성이 존재한다고 단정하지 않습니다. 다만 차입금 만기, 이자 감당력, 배당정책, "
        "리파이낸싱 계획, 후속사건은 감사계획 단계에서 추가 검토가 필요한 신호입니다."
    )
