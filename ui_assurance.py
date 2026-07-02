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
from ui_peer import build_peer_metric_table, flags_to_dataframe, render_overall_risk_message, render_red_flag_cards


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


def _render_peer_assurance_section(peer_context: dict | None):
    if not peer_context:
        return
    flags = peer_context.get("assurance_red_flags", [])
    peer_metrics = peer_context.get("peer_metrics", pd.DataFrame())
    target_company = peer_context.get("target_company", "선택 리츠")

    st.markdown("---")
    st.markdown("## Peer 기반 감사위험 Red Flag")
    st.caption(
        "감사계획 단계에서 참고할 수 있는 위험 스크리닝 결과입니다. "
        "최종 판단은 감사인과 전문가의 검토가 필요합니다."
    )
    render_overall_risk_message("Overall Assurance risk summary", flags)

    metric_table = build_peer_metric_table(
        peer_metrics,
        target_company,
        {
            "investment_property_to_total_assets": "투자부동산/총자산",
            "debt_to_assets": "차입금/총자산",
            "current_debt_to_total_debt": "유동성 차입금/총차입금",
            "interest_expense_to_ffo": "이자비용/FFO",
            "dividend_to_ffo": "배당/FFO",
            "operating_cash_flow_to_dividends": "영업현금흐름/배당",
        },
    )

    tab_flags, tab_metrics, tab_response = st.tabs(["Red Flag 카드", "Peer metric table", "감사절차와 요청자료"])
    with tab_flags:
        render_red_flag_cards(flags, "audit_response", "권장 감사절차", include_kam_indicator=True)

    with tab_metrics:
        if metric_table.empty:
            st.info("Peer metric table을 만들 수 있는 데이터가 부족합니다.")
        else:
            st.dataframe(metric_table, width="stretch", hide_index=True, height=260)

    with tab_response:
        table = flags_to_dataframe(flags, "audit_response")
        if table.empty:
            st.info("표시할 Red Flag가 없습니다.")
        else:
            st.dataframe(table, width="stretch", hide_index=True, height=300)
            procedures = sorted({item for flag in flags for item in flag.get("audit_response", [])})
            evidence = sorted({item for flag in flags for item in flag.get("evidence_request", [])})
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Recommended audit procedures**")
                for item in procedures or ["데이터 부족"]:
                    st.write(f"- {item}")
            with c2:
                st.write("**Evidence request checklist**")
                for item in evidence or ["데이터 부족"]:
                    st.write(f"- {item}")

    st.info(
        "이 결과는 감사계획 단계에서 참고할 수 있는 위험 스크리닝 결과입니다. "
        "앱이 실제 감사의견이나 KAM(핵심감사사항)을 확정하지 않습니다."
    )


def render_assurance_mode(
    asset_risk: pd.DataFrame,
    debt_schedule: pd.DataFrame,
    latest_kpi: pd.Series,
    scenario: dict,
    materiality_pct: float,
    peer_context: dict | None = None,
):
    st.markdown("## A. Assurance: 감사위험 분석")
    st.caption(
        "이 화면은 리츠회사 감사계획 단계에서 어떤 자산과 계정을 중점적으로 봐야 하는지 판단하기 위한 참고 도구입니다. "
        "기업과 기업환경의 이해, 위험평가절차, 통제테스트, 실증절차 순서로 RMM(중요왜곡표시위험), "
        "KAM(핵심감사사항), 내부회계관리제도 핵심 통제 포인트를 정리합니다."
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
            st.caption("`시나리오가치변화_%`는 좌측 사이드바의 예상 거시경제 상황과 Cap rate(자본환원율) 충격 가정에 따라 즉시 달라집니다.")
            st.dataframe(assurance_assets.head(8), width="stretch", hide_index=True, height=260)
        with a2:
            st.write("**RMM 요약 매핑**")
            st.caption("투자부동산 공정가치 RMM은 선택 Scenario와 Cap rate 충격을 함께 표시합니다.")
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

    _render_peer_assurance_section(peer_context)

    st.warning(
        "계속기업 관련 중요한 불확실성이 존재한다고 단정하지 않습니다. 다만 차입금 만기, 이자 감당력, 배당정책, "
        "리파이낸싱 계획, 후속사건은 감사계획 단계에서 추가 검토가 필요한 신호입니다."
    )
