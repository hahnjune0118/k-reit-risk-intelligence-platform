import pandas as pd
import streamlit as st

from calculations_assurance import (
    build_assurance_asset_priority,
    build_assurance_workpaper_index,
    build_audit_workflow_checklist,
    build_company_level_asset_tenant_proxy,
    build_company_level_refinancing_proxy,
    build_company_level_valuation_proxy,
    build_icfr_control_points,
    build_kam_candidate_table,
    build_rmm_assertion_checklist,
    build_rmm_mapping,
)
from ui_peer import (
    build_peer_metric_table,
    flags_to_assurance_review_table,
    render_overall_risk_message,
    style_risk_review_table,
)
from ui_common import render_data_scope_banner, render_selected_company_header


def _stage_rows(workflow: pd.DataFrame, stages: list[str]) -> pd.DataFrame:
    return workflow[workflow["감사단계"].isin(stages)].reset_index(drop=True)


def _render_checklist(df: pd.DataFrame, key: str, height: int = 360):
    display = df.copy()
    reference = pd.DataFrame()
    if "기준서 근거" in display.columns:
        reference_cols = [col for col in ["단계", "감사단계", "체크 항목", "기준서 근거"] if col in display.columns]
        reference = display[reference_cols].drop_duplicates().reset_index(drop=True)
        display = display.drop(columns=["기준서 근거"])
    if "감사단계" in display.columns:
        display = display.rename(columns={"감사단계": "단계"})
    preferred_order = [col for col in ["완료", "단계", "우선순위", "체크 항목", "리츠 감사 포인트", "수행 절차", "증거/문서화"] if col in display.columns]
    display = display[preferred_order + [col for col in display.columns if col not in preferred_order]]
    disabled_cols = [col for col in display.columns if col != "완료"]
    st.data_editor(
        display,
        width="stretch",
        hide_index=True,
        height=height,
        disabled=disabled_cols,
        key=key,
        column_config={
            "완료": st.column_config.CheckboxColumn("완료", width="small"),
            "단계": st.column_config.TextColumn("단계", width="small"),
            "우선순위": st.column_config.TextColumn("우선", width="small"),
            "체크 항목": st.column_config.TextColumn("체크 항목", width="medium"),
            "리츠 감사 포인트": st.column_config.TextColumn("리츠 감사 포인트", width="medium"),
            "수행 절차": st.column_config.TextColumn("수행 절차", width="large"),
            "증거/문서화": st.column_config.TextColumn("증거/문서화", width="medium"),
        },
    )
    if not reference.empty:
        with st.expander("기준서 근거 보기", expanded=False):
            if "감사단계" in reference.columns:
                reference = reference.rename(columns={"감사단계": "단계"})
            st.dataframe(
                reference,
                width="stretch",
                hide_index=True,
                height=160,
                column_config={
                    "단계": st.column_config.TextColumn("단계", width="small"),
                    "체크 항목": st.column_config.TextColumn("체크 항목", width="large"),
                    "기준서 근거": st.column_config.TextColumn("기준서 근거", width="small"),
                },
            )


def _render_compact_dataframe(df: pd.DataFrame, height: int = 260, column_config: dict | None = None):
    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        height=height,
        column_config=column_config,
    )


def _target_peer_row(peer_context: dict | None) -> pd.Series | None:
    if not peer_context:
        return None
    peer_metrics = peer_context.get("peer_metrics", pd.DataFrame())
    target_company = peer_context.get("target_company", "")
    if peer_metrics is None or peer_metrics.empty or "company_name" not in peer_metrics.columns:
        return None
    matched = peer_metrics[peer_metrics["company_name"].astype(str).str.strip() == str(target_company).strip()]
    if matched.empty:
        return None
    sort_cols = [col for col in ["year", "period"] if col in matched.columns]
    return matched.sort_values(sort_cols).iloc[-1] if sort_cols else matched.iloc[-1]


def _proxy_column_config() -> dict:
    return {
        "구분": st.column_config.TextColumn("구분", width="small"),
        "지표": st.column_config.TextColumn("지표", width="medium"),
        "값": st.column_config.TextColumn("값", width="small"),
        "위험수준": st.column_config.TextColumn("위험", width="small"),
        "주요 해석": st.column_config.TextColumn("주요 해석", width="large"),
        "데이터 기준": st.column_config.TextColumn("데이터 기준", width="medium"),
    }


def _render_company_level_proxy_tables(peer_context: dict | None):
    peer_row = _target_peer_row(peer_context)
    if peer_row is None:
        st.warning("회사 단위 proxy 분석에 필요한 Peer Snapshot 데이터가 부족합니다.")
        return

    data_availability = (peer_context or {}).get("data_availability", {}) or {}
    recent_5y = (peer_context or {}).get("recent_5y_financials", pd.DataFrame())
    data_basis = data_availability.get("scope_label") or (peer_context or {}).get("detail_data_basis", "회사 전체 Snapshot")

    st.write("**회사 단위 Assurance proxy 분석**")
    st.caption(
        "자산별 임차인, 차입금 만기 wall, Cap rate 상세자료가 부족한 경우에는 회사 전체 재무 Snapshot과 "
        "Peer Benchmark를 사용해 감사계획 단계의 위험 신호를 표시합니다."
    )
    st.info(
        "자산별 Cap rate proxy 데이터가 부족하면 NAV 민감도 카드를 계산하지 않고, 회사 전체 재무 Snapshot 기반 가치 민감도 proxy를 표시합니다."
    )

    with st.expander("자산·임차인 proxy", expanded=True):
        asset_proxy = build_company_level_asset_tenant_proxy(peer_row, recent_5y, data_basis)
        _render_compact_dataframe(asset_proxy, height=210, column_config=_proxy_column_config())

    with st.expander("차입금 만기·차환 proxy", expanded=True):
        debt_proxy = build_company_level_refinancing_proxy(peer_row, recent_5y, data_basis)
        _render_compact_dataframe(debt_proxy, height=240, column_config=_proxy_column_config())

    with st.expander("부동산 가치·장부NAV proxy", expanded=True):
        valuation_proxy = build_company_level_valuation_proxy(peer_row, data_availability, data_basis)
        _render_compact_dataframe(valuation_proxy, height=260, column_config=_proxy_column_config())


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
    render_overall_risk_message("Assurance 감사위험 요약", flags)

    metric_table = build_peer_metric_table(
        peer_metrics,
        target_company,
        {
            "investment_property_to_total_assets": "투자부동산/총자산",
            "debt_to_assets": "차입금/총자산",
            "current_debt_to_total_debt": "유동성 차입금/총차입금",
            "interest_expense_to_ffo": "이자비용/FFO proxy",
            "dividend_to_ffo": "배당/FFO proxy",
            "operating_cash_flow_to_dividends": "영업현금흐름/배당",
        },
    )

    review_table = flags_to_assurance_review_table(flags)
    if review_table.empty:
        st.info("표시할 Peer 기반 감사위험 Red Flag가 없습니다.")
    else:
        st.write("**감사절차 및 요청자료**")
        st.dataframe(
            style_risk_review_table(review_table),
            width="stretch",
            hide_index=True,
            height=330,
            column_config={
                "위험영역": st.column_config.TextColumn("위험영역", width="small"),
                "위험수준": st.column_config.TextColumn("위험수준", width="small"),
                "발생 근거": st.column_config.TextColumn("발생 근거", width="medium"),
                "권장 감사절차": st.column_config.TextColumn("권장 감사절차", width="large"),
                "요청자료": st.column_config.TextColumn("요청자료", width="medium"),
                "KAM 후보 검토": st.column_config.TextColumn("KAM 후보", width="small"),
            },
        )

    with st.expander("Peer 지표 비교표 보기", expanded=False):
        if metric_table.empty:
            st.info("Peer 지표 비교표를 만들 수 있는 데이터가 부족합니다.")
        else:
            st.dataframe(metric_table, width="stretch", hide_index=True, height=260)

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
    render_selected_company_header(peer_context)
    render_data_scope_banner(peer_context)
    st.caption(
        "이 화면은 리츠회사 감사계획 단계에서 어떤 자산과 계정을 중점적으로 봐야 하는지 판단하기 위한 참고 도구입니다. "
        "기업과 기업환경의 이해, 위험평가절차, 통제테스트, 실증절차 순서로 RMM(중요왜곡표시위험), "
        "KAM(핵심감사사항), 내부회계관리제도 핵심 통제 포인트를 정리합니다."
    )
    if peer_context and not peer_context.get("detail_data_available", True):
        st.info(
            "현재 선택 회사는 회사 전체 재무 Snapshot 및 Peer Benchmark를 기준으로 분석합니다. "
            "자산별 임차인·Cap rate·만기 wall 등 상세 데이터는 공개자료에서 충분히 구조화되지 않아, "
            "상세 표 대신 회사 전체 기준의 proxy 지표를 표시합니다."
        )
    run_id = (peer_context or {}).get("analysis_run_id", 0)

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
            f"assurance_planning_checklist_{run_id}",
            height=480,
        )

    with tab_rmm:
        st.write("**감사 중점 자산 우선순위**")
        st.caption("`시나리오가치변화_%`는 좌측 사이드바의 예상 거시경제 상황과 Cap rate(자본환원율) 충격 가정에 따라 즉시 달라집니다.")
        if assurance_assets.empty:
            st.info("자산별 상세자료가 부족하여 감사 중점 자산 우선순위 대신 회사 전체 proxy 지표를 표시합니다.")
            _render_company_level_proxy_tables(peer_context)
        else:
            _render_compact_dataframe(
                assurance_assets.head(8),
                height=260,
                column_config={
                    "자산": st.column_config.TextColumn("자산", width="medium"),
                    "평가액_백만원": st.column_config.NumberColumn("평가액", width="small"),
                    "평가액비중_%": st.column_config.NumberColumn("비중", width="small", format="%.1f%%"),
                    "Cap_rate_%": st.column_config.NumberColumn("Cap rate", width="small", format="%.1f%%"),
                    "남은임대기간_년": st.column_config.NumberColumn("WALE", width="small", format="%.1f"),
                    "주요임차인": st.column_config.TextColumn("임차인", width="small"),
                    "시나리오가치변화_%": st.column_config.NumberColumn("가치변화", width="small", format="%.1f%%"),
                    "감사중점점수": st.column_config.NumberColumn("점수", width="small", format="%.0f"),
                    "감사 우선순위": st.column_config.TextColumn("우선", width="small"),
                    "중점검토사유": st.column_config.TextColumn("중점검토사유", width="large"),
                    "가치변화 산정 메모": st.column_config.TextColumn("가치변화 메모", width="medium"),
                },
            )

        st.write("**RMM 요약 매핑**")
        st.caption("투자부동산 공정가치 RMM은 선택 Scenario와 Cap rate 충격을 함께 표시합니다.")
        _render_compact_dataframe(
            rmm,
            height=260,
            column_config={
                "감사영역": st.column_config.TextColumn("감사영역", width="small"),
                "RMM 신호": st.column_config.TextColumn("RMM 신호", width="large"),
                "왜 중요한가": st.column_config.TextColumn("중요성", width="medium"),
                "권장 감사절차": st.column_config.TextColumn("권장 감사절차", width="large"),
            },
        )

        st.write("**계정·공시 및 경영진 주장별 RMM 체크리스트**")
        _render_compact_dataframe(
            rmm_assertions,
            height=320,
            column_config={
                "계정/공시": st.column_config.TextColumn("계정/공시", width="small"),
                "경영진 주장": st.column_config.TextColumn("주장", width="small"),
                "RMM 판단": st.column_config.TextColumn("판단", width="small"),
                "위험 신호": st.column_config.TextColumn("위험 신호", width="medium"),
                "위험평가절차": st.column_config.TextColumn("위험평가절차", width="large"),
                "통제테스트 판단": st.column_config.TextColumn("통제테스트", width="medium"),
                "실증절차": st.column_config.TextColumn("실증절차", width="large"),
                "KAM 연계": st.column_config.TextColumn("KAM", width="small"),
            },
        )

    with tab_response:
        st.write("**통제테스트 및 실증절차 체크리스트**")
        _render_checklist(
            _stage_rows(workflow, ["통제테스트", "실증절차"]),
            f"assurance_response_checklist_{run_id}",
            height=500,
        )

        st.write("**내부회계관리제도 핵심 통제 포인트**")
        st.dataframe(icfr, width="stretch", hide_index=True, height=220)

    with tab_report:
        st.write("**KAM 후보와 감사보고서 고려사항**")
        _render_compact_dataframe(
            kam,
            height=230,
            column_config={
                "후보": st.column_config.TextColumn("후보", width="medium"),
                "선정 신호": st.column_config.TextColumn("신호", width="small"),
                "중점 고려사항": st.column_config.TextColumn("중점 고려사항", width="large"),
                "KAM/감사보고서 문구 방향": st.column_config.TextColumn("보고서 고려사항", width="large"),
            },
        )

        st.write("**보고·KAM·커뮤니케이션 체크리스트**")
        _render_checklist(
            _stage_rows(workflow, ["보고·KAM·커뮤니케이션"]),
            f"assurance_reporting_checklist_{run_id}",
            height=230,
        )

        st.write("**감사 작업문서 인덱스**")
        st.dataframe(workpaper_index, width="stretch", hide_index=True, height=300)

    _render_peer_assurance_section(peer_context)

    st.warning(
        "계속기업 관련 중요한 불확실성이 존재한다고 단정하지 않습니다. 다만 차입금 만기, FFO 이자감당력 proxy, 배당정책, "
        "리파이낸싱 계획, 후속사건은 감사계획 단계에서 추가 검토가 필요한 신호입니다."
    )
