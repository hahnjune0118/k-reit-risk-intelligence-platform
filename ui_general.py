import pandas as pd
import plotly.express as px
import streamlit as st

from calculations_scenario import korean_metric_label, korean_risk_label
from data_source_policy import source_type_label
from formatting import format_pct_from_100, format_ratio, format_score, format_trn_krw_from_mn
from api_manager import sanitize_secret_text
from ui_common import compact_fig, fmt_metric_value, fmt_mn_to_bn, mode_specific_action_items, render_selected_company_header
from ui_peer import build_peer_metric_table, format_peer_percentile, format_peer_value, render_overall_risk_message


AX_RUNTIME_SCOPE_NOTE = (
    "공개 Runtime의 세액 계산은 재현 가능한 규칙엔진을 사용합니다. "
    "생성형 AI는 비정형 문서 구조화와 검토문서 작성 지원을 위한 확장계층으로 "
    "설계하며, 확정적인 세법 판단과 신고·납부 의사결정은 전문가 검토 대상으로 "
    "유지합니다."
)


def _render_ax_advisory_overview():
    st.markdown("## AX 적용 개요 — 공시·세무검토 Workflow 재설계")
    st.write(
        "분산된 리츠 공시, 세법, 공시가격 및 재무자료를 연결하여 검토대상 식별, "
        "법정산식 계산, 과세근거 추적, 주요 세무쟁점 도출, 추가 요청자료 및 "
        "검토메모 생성을 하나의 통제된 업무 프로세스로 구조화했습니다."
    )

    pain_point, solution, effect = st.columns(3)
    with pain_point:
        st.markdown("#### 고객 Pain Point")
        st.markdown(
            "- 공시·IR·세법·공시가격 자료의 분산\n"
            "- 주소·소유구조·과세정보의 반복 확인\n"
            "- Excel 계산과 근거자료의 분리\n"
            "- 담당자별 검토절차와 문서 양식의 차이\n"
            "- 공식자료가 부족한 경우 추정값 사용 위험"
        )
    with solution:
        st.markdown("#### AX Solution")
        st.markdown(
            "- 자산·필지·납세의무자 단위 데이터 표준화\n"
            "- 법정 산식 기반 규칙엔진\n"
            "- Source Lineage와 과세근거 연결\n"
            "- 주요 세무쟁점과 추가 요청자료 자동 연결\n"
            "- Fail-closed 및 Human-in-the-loop 통제"
        )
    with effect:
        st.markdown("#### 업무효과")
        st.markdown(
            "- 검토 순서의 표준화\n"
            "- 계산 재현성\n"
            "- 근거 추적성\n"
            "- 누락·중복 통제\n"
            "- Review-ready 산출물 생성"
        )

    st.markdown("### As-Is·To-Be Workflow")
    workflow = pd.DataFrame(
        [
            {
                "구분": "As-Is",
                "업무 프로세스": (
                    "공시 PDF 검색 → 주소·소유관계 수작업 확인 → 공시가격 별도 조회 "
                    "→ Excel 세액 계산 → 근거 재확인 → 쟁점·요청자료·메모 수작업 작성"
                ),
            },
            {
                "구분": "To-Be",
                "업무 프로세스": (
                    "공식자료 수집 → 자산·필지·납세의무자 구조화 → 과세기초자료 검증 "
                    "→ 법정 산식 계산 → 검증통제 → 주요 세무쟁점 → 추가 요청자료 "
                    "→ 검토메모 → 전문가 승인"
                ),
            },
        ]
    )
    st.dataframe(
        workflow,
        width="stretch",
        hide_index=True,
        column_config={
            "구분": st.column_config.TextColumn(width="small"),
            "업무 프로세스": st.column_config.TextColumn(width="large"),
        },
    )

    st.markdown("### AI·Data·Automation·Human Review 역할")
    roles = pd.DataFrame(
        [
            {
                "역할": "Data",
                "적용 내용": "공시·주소·PNU·시가표준액·납세의무자 구조화",
            },
            {
                "역할": "Automation",
                "적용 내용": "세액 계산, 끝수 처리, 검증, 민감도 분석, 문서 출력",
            },
            {
                "역할": "AI 지원영역",
                "적용 내용": (
                    "비정형 문서 구조화, 주요 쟁점 요약, 추가 요청자료 및 "
                    "검토메모 초안 지원"
                ),
            },
            {
                "역할": "Control Harness",
                "적용 내용": (
                    "Source Grounding, Schema 검증, Fail-closed, 회귀테스트, "
                    "검증상태 관리"
                ),
            },
            {
                "역할": "Human Review",
                "적용 내용": "법적 판단, 실제 고지서 대사, 최종 승인",
            },
        ]
    )
    st.dataframe(
        roles,
        width="stretch",
        hide_index=True,
        column_config={
            "역할": st.column_config.TextColumn(width="medium"),
            "적용 내용": st.column_config.TextColumn(width="large"),
        },
    )
    st.info(AX_RUNTIME_SCOPE_NOTE)

    st.markdown("### 구현범위와 한계")
    implementation_scope = pd.DataFrame(
        [
            {
                "상태": "구현",
                "범위": (
                    "공식자료 기반 데이터 구조화, 법정 산식 계산, 민감도 분석, "
                    "Source Lineage, 주요 세무쟁점, 추가 요청자료, 검토메모, "
                    "CSV·Excel·Markdown·HTML 출력"
                ),
            },
            {
                "상태": "설계·확장영역",
                "범위": "AI 기반 비정형 문서 추출, 쟁점 요약 및 문서 초안 지원",
            },
            {
                "상태": "전문가 확인 필요",
                "범위": (
                    "실제 과세내역서, 과세기준일 소유·신탁관계, 감면·세부담상한, "
                    "실제 고지세액, 최종 세법 판단"
                ),
            },
        ]
    )
    st.dataframe(
        implementation_scope,
        width="stretch",
        hide_index=True,
        column_config={
            "상태": st.column_config.TextColumn(width="medium"),
            "범위": st.column_config.TextColumn(width="large"),
        },
    )

    st.markdown("### 구현 증빙")
    # v15 공개 검증 Snapshot과 Tax Case Study의 확정된 범위만 표시합니다.
    evidence = pd.DataFrame(
        [
            {"항목": "핵심 분석대상 자산", "확인 결과": "SK서린빌딩"},
            {"항목": "공식 과세근거자료", "확인 결과": "16건"},
            {"항목": "주요 세무쟁점", "확인 결과": "6건"},
            {
                "항목": "출력형식",
                "확인 결과": "CSV·Excel·Markdown·HTML",
            },
            {"항목": "검증 방식", "확인 결과": "Fail-closed"},
            {"항목": "실제 고지세액 대사", "확인 결과": "미완료"},
        ]
    )
    st.dataframe(evidence, width="stretch", hide_index=True)

    with st.expander("3분 권장 열람 순서", expanded=False):
        st.markdown(
            "1. AX 적용 개요와 As-Is·To-Be Workflow\n"
            "2. 일반 정보 및 시나리오의 데이터 분석\n"
            "3. SK서린빌딩 보유세 재계산과 민감도 분석\n"
            "4. 주요 세무쟁점·추가 요청자료·과세근거자료"
        )

    st.markdown("---")


def _display_api_status(status: str) -> str:
    sanitized = sanitize_secret_text(status)
    return "API 연결 완료" if sanitized == "connected" else sanitized


def _fmt_pct(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.2f}%"


def _fmt_100mn_from_mn(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value) / 100:,.0f}"


def _numeric_series(df: pd.DataFrame, *candidates: str) -> pd.Series:
    for col in candidates:
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(pd.NA, index=df.index, dtype="Float64")


def _trend_interpretation(row: pd.Series) -> str:
    rate = pd.to_numeric(row.get("기준금리(%)"), errors="coerce")
    ffo = pd.to_numeric(row.get("FFO(억원)"), errors="coerce")
    debt = pd.to_numeric(row.get("차입금(억원)"), errors="coerce")
    if pd.notna(rate) and rate >= 3.0 and pd.notna(debt) and debt > 0:
        return "금리 부담과 차입금 구조를 함께 확인"
    if pd.notna(ffo) and ffo <= 0:
        return "FFO proxy 또는 이익 지표 보완 필요"
    return "특이 신호 제한적"


def build_five_year_trend_display(historical_panel: pd.DataFrame) -> pd.DataFrame:
    if historical_panel is None or historical_panel.empty:
        return pd.DataFrame()
    df = historical_panel.sort_values("year").tail(5).copy()
    out = pd.DataFrame()
    out["연도"] = df["year"].astype("Int64").astype(str)
    out["기준금리(%)"] = _numeric_series(df, "기준금리")
    out["국고채 3년(%)"] = _numeric_series(df, "국고채 3년")
    out["회사채 AA- 3년(%)"] = _numeric_series(df, "회사채 AA- 3년")
    out["장부NAV proxy(억원)"] = _numeric_series(df, "순자산가치_또는_자본", "nav_mn_krw", "book_nav_proxy", "nav") / 100
    out["FFO proxy(억원)"] = _numeric_series(df, "현금흐름_또는_이익", "ffo_mn_krw", "ffo_proxy") / 100
    out["총자산(억원)"] = _numeric_series(df, "total_assets_mn_krw", "total_assets") / 100
    out["차입금(억원)"] = _numeric_series(df, "interest_bearing_debt_mn_krw", "borrowings_total") / 100
    out["이자비용(억원)"] = _numeric_series(df, "interest_expense", "interest_expense_mn_krw") / 100
    out["주요 해석"] = out.apply(_trend_interpretation, axis=1)

    display = out.copy()
    for col in ["기준금리(%)", "국고채 3년(%)", "회사채 AA- 3년(%)"]:
        display[col] = display[col].map(_fmt_pct)
    for col in ["장부NAV proxy(억원)", "FFO proxy(억원)", "총자산(억원)", "차입금(억원)", "이자비용(억원)"]:
        display[col] = display[col].map(lambda value: f"{value:,.0f}" if pd.notna(value) else "N/A")
    return display


def _render_peer_benchmark_overview(peer_context: dict | None):
    if not peer_context:
        return
    peer_metrics = peer_context.get("peer_metrics", pd.DataFrame())
    peer_summary = peer_context.get("peer_summary", {})
    target_company = peer_context.get("target_company", "선택 리츠")
    if not peer_summary.get("available"):
        st.info("Peer Benchmark를 계산할 수 있는 snapshot 데이터가 부족합니다.")
        return

    st.markdown("### Peer Benchmark 및 Red Flag 요약")
    st.caption(
        "선택한 리츠 회사를 상장 REITs Peer Group과 비교하여 감사위험, 보유세 부담, "
        "FFO proxy 현금유출 부담이 상대적으로 높은 영역을 자동으로 스크리닝합니다."
    )
    st.caption(
        f"대상 리츠: {target_company} / Peer Group: {peer_context.get('peer_group', '전체 상장리츠')} / "
        f"Snapshot 기준: data/reit_peer_snapshot.csv / 데이터 출처: "
        f"{source_type_label(peer_summary.get('source_type'))} / "
        "실시간 API 호출 실패 시 예시 데이터 사용"
    )

    metrics = peer_summary.get("metrics", {})
    asset_size = metrics.get("total_assets", {})
    debt_burden = metrics.get("debt_to_assets", {})
    interest_burden = metrics.get("interest_expense_to_ffo", {})
    holding_tax_burden = metrics.get("holding_tax_to_ffo", {})
    official_price_ratio = metrics.get("official_price_to_investment_property", {})

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("자산규모", format_peer_value("total_assets", asset_size.get("value")), format_peer_percentile(asset_size.get("percentile")))
    c2.metric("차입부담", format_peer_value("debt_to_assets", debt_burden.get("value")), format_peer_percentile(debt_burden.get("percentile")))
    c3.metric("이자비용/FFO proxy", format_peer_value("interest_expense_to_ffo", interest_burden.get("value")), format_peer_percentile(interest_burden.get("percentile")))
    c4.metric("보유세/FFO proxy", format_peer_value("holding_tax_to_ffo", holding_tax_burden.get("value")), format_peer_percentile(holding_tax_burden.get("percentile")))
    c5.metric("공시가격/투자부동산", format_peer_value("official_price_to_investment_property", official_price_ratio.get("value")), format_peer_percentile(official_price_ratio.get("percentile")))

    a_flags = peer_context.get("assurance_red_flags", [])
    t_flags = peer_context.get("tax_red_flags", [])
    c_left, c_right = st.columns(2)
    with c_left:
        render_overall_risk_message("Assurance Red Flag", a_flags, "감사계획 단계의 참고용 스크리닝 결과입니다.")
    with c_right:
        render_overall_risk_message("Tax Red Flag", t_flags, "신고 목적 세액 산출이 아닌 예비 검토 신호입니다.")

    metric_table = build_peer_metric_table(
        peer_metrics,
        target_company,
        {
            "total_assets": "자산규모",
            "debt_to_assets": "차입부담",
            "interest_expense_to_ffo": "이자비용/FFO proxy",
            "holding_tax_to_ffo": "보유세/FFO proxy",
            "holding_tax_to_operating_revenue": "보유세/영업수익",
            "official_price_to_investment_property": "공시가격/투자부동산",
        },
    )
    if not metric_table.empty:
        st.dataframe(metric_table, width="stretch", hide_index=True, height=220)


def render_general_dashboard(
    verdict_level,
    verdict_text,
    verdict_reason,
    macro_scenario,
    macro_context,
    risk_level,
    total_risk,
    scenario,
    market_snapshot,
    market_gap,
    market_gap_narrative,
    historical_panel,
    transmission_narrative,
    transmission_table,
    transmission_corr,
    selected_user_mode,
    risk_scores,
    watchlist,
    risk_decomposition,
    asset_risk,
    concentration_table,
    tenant_exposure,
    debt_schedule,
    debt_summary,
    cap_rate_shock_bp,
    source_plan,
    data_dictionary,
    financials,
    kpis,
    macro_history_status,
    dart_status,
    dart_reports,
    peer_context=None,
):
    _render_ax_advisory_overview()
    company_profile = (peer_context or {}).get("selected_company_profile", {})
    recent_5y_status = (peer_context or {}).get("recent_5y_status", "")
    st.markdown("## 1. 한눈에 보는 결론")
    render_selected_company_header(peer_context)

    if company_profile:
        rank = company_profile.get("market_cap_rank", pd.NA)
        rank_text = f"{int(rank)}위" if pd.notna(rank) else "N/A"
        summary = pd.DataFrame([
            {"항목": "회사명", "내용": company_profile.get("company_name", "")},
            {"항목": "종목코드", "내용": company_profile.get("stock_code", "")},
            {"항목": "DART corp_code", "내용": company_profile.get("dart_corp_code", "")},
            {"항목": "시가총액 순위", "내용": rank_text},
            {"항목": "데이터 기준", "내용": recent_5y_status or company_profile.get("data_basis", "")},
        ])
        st.write("**선택 회사 요약**")
        st.dataframe(summary, width="stretch", hide_index=True, height=190)
        st.caption("선택 회사의 최근 가용 공시자료 및 Snapshot 데이터를 기준으로 분석합니다. FFO와 NAV는 공식값이 아니라 proxy 기준으로 표시될 수 있습니다.")

    if verdict_level == "High":
        st.error(f"{verdict_text} — {verdict_reason}")
    elif verdict_level == "Medium":
        st.warning(f"{verdict_text} — {verdict_reason}")
    else:
        st.success(f"{verdict_text} — {verdict_reason}")

    st.caption(
        f"선택 시나리오: {macro_scenario['selected_scenario']} | "
        f"{macro_scenario.get('scenario_base_rate_label', '시나리오 기준금리')} "
        f"{macro_scenario['base_rate_pct']:.2f}% → {macro_scenario['scenario_base_rate_pct']:.2f}% | "
        f"차입 스프레드·리파이낸싱 금리 충격 +{macro_scenario['rate_shock_bp']}bp | "
        f"Cap rate +{macro_scenario['cap_rate_shock_bp']}bp | "
        f"자료 기준: {macro_context['source']}"
    )
    st.caption(macro_scenario.get("scenario_base_rate_note", ""))

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("종합 위험도", {"High":"높음", "Medium":"보통", "Low":"낮음"}.get(risk_level, risk_level), format_score(total_risk))
    k2.metric("시나리오 후 FFO proxy", fmt_mn_to_bn(scenario["stressed_ffo"]), f"{scenario['ffo_decline_pct']:.1f}%" if pd.notna(scenario["ffo_decline_pct"]) else "N/A")
    k3.metric("FFO 이자감당력 proxy", format_ratio(scenario["stressed_icr"]), f"현재 {format_ratio(scenario['reported_icr'])}")
    k4.metric("장부NAV proxy 영향", format_pct_from_100(scenario["nav_change_pct"]), fmt_mn_to_bn(scenario["total_value_change"]))
    k5.metric(
        "투자부동산 가치 기준 차입비율 proxy",
        format_pct_from_100(scenario["stressed_ltv_proxy"]),
        f"현재 {format_pct_from_100(scenario['base_ltv_proxy'])}",
    )

    _render_peer_benchmark_overview(peer_context)

    st.markdown("---")
    st.markdown("## 2. 현재 상태와 선택한 시나리오 비교")
    st.caption("좌측 사이드바에서 거시경제 시나리오를 바꾸면 FFO proxy, FFO 이자감당력 proxy, 배당 여력, 장부기준 NAV proxy가 즉시 바뀝니다.")

    left, right = st.columns([1.05, 1.0])

    with left:
        fig_ffo = px.bar(
            scenario["ffo_bridge"].sort_values("display_order"),
            x="step",
            y="mn_krw",
            title="FFO proxy 변화: 현재 → 시나리오 후",
            text="mn_krw",
        )
        fig_ffo.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
        st.plotly_chart(compact_fig(fig_ffo, 255), width="stretch")

    with right:
        kpi_display = scenario["kpi_summary"].copy()
        kpi_display["지표"] = kpi_display["metric"].apply(korean_metric_label)
        kpi_display["현재"] = kpi_display.apply(lambda r: fmt_metric_value(r, "baseline"), axis=1)
        kpi_display["시나리오 후"] = kpi_display.apply(lambda r: fmt_metric_value(r, "stressed"), axis=1)
        kpi_display = kpi_display[["지표", "현재", "시나리오 후"]]
        st.dataframe(kpi_display, width="stretch", hide_index=True, height=245)

    st.markdown("---")
    st.markdown("## 3. 최근 5년 흐름: 금리와 REITs 주요 지표")
    st.caption(
        "선택 회사의 최근 5년 재무 흐름은 서버 측 DART 연결이 가능하면 DART 자료를 우선 사용하고, 연결이 제한되거나 계정이 부족하면 Snapshot fallback을 사용합니다. "
        "거시경제 시계열은 ECOS 연결 또는 내장 예시 데이터를 통해 함께 표시합니다."
    )
    st.caption(
        "금리 지표와 리츠 재무지표는 단위와 해석 기준이 다르기 때문에 하나의 축으로 지수화하여 비교하면 오해가 발생할 수 있습니다. "
        "따라서 본 화면에서는 기준금리·국고채·회사채 금리는 실제 이자율(%)로, 장부NAV proxy·FFO proxy·총자산·차입금 등은 실제 금액(억원)으로 구분하여 표시합니다."
    )

    trend_display = build_five_year_trend_display(historical_panel)
    if trend_display.empty:
        st.info("최근 5년 흐름 표를 만들 수 있는 데이터가 아직 부족합니다.")
    else:
        st.write("**최근 5년 흐름: 금리와 리츠 주요 지표**")
        st.dataframe(trend_display, width="stretch", hide_index=True, height=250)

    if all(c in historical_panel.columns for c in ["기준금리_변화_bp", "순자산가치_변화율", "현금흐름_변화율"]):
        reaction = historical_panel[["year", "기준금리_변화_bp", "순자산가치_변화율", "현금흐름_변화율"]].dropna().copy()
        if not reaction.empty:
            reaction = reaction.rename(columns={
                "year": "연도",
                "기준금리_변화_bp": "기준금리 변화폭(bp)",
                "순자산가치_변화율": "장부NAV proxy/자본 변화율(%)",
                "현금흐름_변화율": "FFO proxy/이익 변화율(%)",
            })
            st.write("**기준금리 변화와 리츠 지표 변화**")
            st.dataframe(reaction, width="stretch", hide_index=True, height=160)
            st.caption(
                "주의: 이 표는 인과관계를 확정하지 않습니다. REITs의 장부NAV proxy·FFO proxy는 금리 외에도 자산 편입, 유상증자, 임대차 계약, 회계 기준, 평가가정에 영향을 받습니다."
            )

    if all(c in historical_panel.columns for c in ["기준금리_변화_bp", "시장가치_변화율", "P_NAV_변화"]):
        market_reaction = historical_panel[["year", "기준금리_변화_bp", "시장가치_변화율", "P_NAV_변화"]].dropna().copy()
        if not market_reaction.empty:
            market_reaction = market_reaction.rename(columns={
                "year": "연도",
                "기준금리_변화_bp": "기준금리 변화폭(bp)",
                "시장가치_변화율": "시가총액 변화율(%)",
                "P_NAV_변화": "P/NAV 변화",
            })
            st.write("**기준금리 변화와 시장가격 반응**")
            st.dataframe(market_reaction, width="stretch", hide_index=True, height=150)
            st.caption(
                "P/NAV 하락은 시장이 장부기준 NAV proxy보다 더 큰 할인율을 적용하기 시작했다는 신호일 수 있습니다. "
                "단, 주가는 시장 전체 리스크 선호, 유상증자, 배당정책, 거래량에도 영향을 받습니다."
            )

    st.markdown("### 3-1. 위험 전이 진단: 금리 → FFO proxy/장부NAV proxy → 시장가격")
    st.caption(
        "이 섹션은 금리가 바뀐 해에 REITs의 FFO proxy와 장부기준 NAV proxy가 어떻게 움직였는지 요약합니다. "
        "인과관계 확정이 아니라, Assurance와 Tax 초기검토에서 어디를 더 봐야 하는지 알려주는 신호입니다."
    )
    st.info(transmission_narrative)

    t_left, t_right = st.columns([1.15, 0.85])
    with t_left:
        if transmission_table is not None and not transmission_table.empty:
            st.write("**연도별 전이 신호**")
            st.dataframe(transmission_table.tail(5), width="stretch", hide_index=True, height=220)
        else:
            st.caption("금리·재무·시장가격 시계열이 충분히 연결되면 연도별 전이 신호가 표시됩니다.")

    with t_right:
        if transmission_corr is not None and not transmission_corr.empty:
            st.write("**단순 민감도 참고표**")
            corr_display = transmission_corr.copy()
            corr_display["상관계수"] = corr_display["상관계수"].map(lambda x: f"{x:.2f}")
            st.dataframe(corr_display, width="stretch", hide_index=True, height=220)
        else:
            st.caption("상관계수는 최소 3개 이상의 연도별 관측치가 있을 때 표시됩니다.")

    if transmission_table is not None and not transmission_table.empty and {"기준금리 변화폭(bp)", "시가총액 변화율(%)"}.issubset(transmission_table.columns):
        scatter_data = transmission_table[["연도", "기준금리 변화폭(bp)", "시가총액 변화율(%)", "해석 신호"]].dropna().copy()
        if not scatter_data.empty:
            fig_trans = px.scatter(
                scatter_data,
                x="기준금리 변화폭(bp)",
                y="시가총액 변화율(%)",
                color="해석 신호",
                text="연도",
                title="금리 변화와 시가총액 반응",
            )
            fig_trans.update_traces(textposition="top center")
            st.plotly_chart(compact_fig(fig_trans, 250), width="stretch")

    st.write("**현재 사용자 모드의 권장 확인사항**")
    st.dataframe(mode_specific_action_items(selected_user_mode), width="stretch", hide_index=True, height=140)

    st.markdown("---")
    st.info("Assurance와 Tax 상세 분석은 좌측 사용자 모드에서 해당 모드를 선택하면 별도 화면으로 표시됩니다.")

    st.markdown("---")
    st.markdown("## 4. 위험 점수와 우선 확인 항목")

    r1, r2 = st.columns([0.9, 1.25])

    with r1:
        risk_chart = pd.DataFrame({
            "위험 유형": [korean_risk_label(k) for k in risk_scores.keys()],
            "점수": list(risk_scores.values()),
        })
        fig_risk = px.bar(
            risk_chart,
            x="점수",
            y="위험 유형",
            orientation="h",
            title="위험 유형별 점수",
            range_x=[0, 100],
            text="점수",
        )
        fig_risk.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
        st.plotly_chart(compact_fig(fig_risk, 255), width="stretch")

    with r2:
        wl_cols = ["watch_item", "category", "priority_score", "why_it_matters"]
        watch_display = watchlist[wl_cols].head(6).rename(columns={
            "watch_item": "확인 항목",
            "category": "구분",
            "priority_score": "우선순위 점수",
            "why_it_matters": "왜 중요한가",
        })
        st.write("**먼저 확인할 항목**")
        st.dataframe(watch_display, width="stretch", hide_index=True, height=245)

    triggered_decomp = risk_decomposition[risk_decomposition["triggered"]].copy()
    if not triggered_decomp.empty:
        st.write("**점수를 높인 주요 원인**")
        decomp_display = triggered_decomp[["risk_category", "driver", "score_delta", "weighted_score_delta", "interpretation"]].head(8).copy()
        decomp_display["risk_category"] = decomp_display["risk_category"].apply(korean_risk_label)
        decomp_display = decomp_display.rename(columns={
            "risk_category": "위험 유형",
            "driver": "원인",
            "score_delta": "점수 영향",
            "weighted_score_delta": "가중 영향",
            "interpretation": "해석",
        })
        st.dataframe(
            decomp_display,
            width="stretch",
            hide_index=True,
            height=190,
        )

    st.markdown("---")
    st.markdown("## 5. 자산·임차인·임대 안정성")

    if asset_risk.empty or concentration_table.empty:
        st.warning(
            "선택 회사의 자산별 상세 데이터가 부족하여 자산·임차인 상세 섹션은 표시하지 않습니다. "
            "회사 전체 Peer Benchmark와 재무 Snapshot을 기준으로 해석하세요."
        )
    else:
        total_appraised = asset_risk["appraised_value_mn_krw_20251231"].sum()
        top_asset = concentration_table.sort_values("appraised_value_mn_krw_20251231", ascending=False).iloc[0]
        top3_share = concentration_table.head(3)["portfolio_value_share_pct"].sum()
        hhi = concentration_table["hhi_component"].sum()

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("부동산 평가액", format_trn_krw_from_mn(total_appraised))
        p2.metric("상위 3개 자산 비중", format_pct_from_100(top3_share))
        p3.metric("최대 자산 비중", format_pct_from_100(top_asset["portfolio_value_share_pct"]))
        p4.metric("자산 집중도", f"{hhi:.3f}")

        c_left, c_mid, c_right = st.columns([1.0, 1.0, 1.0])

        with c_left:
            top_assets = concentration_table[[
                "asset_name",
                "appraised_value_mn_krw_20251231",
                "portfolio_value_share_pct",
                "major_tenant",
                "wale_yrs",
                "cap_rate_pct_20251231",
                "asset_risk_score",
            ]].head(7).copy()
            top_assets = top_assets.rename(columns={
                "asset_name": "자산",
                "appraised_value_mn_krw_20251231": "평가액_백만원",
                "portfolio_value_share_pct": "포트폴리오_비중_%",
                "major_tenant": "주요_임차인",
                "wale_yrs": "남은_임대기간_년",
                "cap_rate_pct_20251231": "Cap_rate_%",
                "asset_risk_score": "위험점수",
            })
            st.write("**핵심 자산**")
            st.dataframe(top_assets, width="stretch", hide_index=True, height=245)

        with c_mid:
            tenant_simple = tenant_exposure[["major_tenant", "tenant_credit", "portfolio_value_share_pct"]].head(7).copy()
            tenant_simple = tenant_simple.rename(columns={
                "major_tenant": "임차인",
                "tenant_credit": "신용도",
                "portfolio_value_share_pct": "포트폴리오_비중_%",
            })
            st.write("**주요 임차인 비중**")
            st.dataframe(tenant_simple, width="stretch", hide_index=True, height=245)

        with c_right:
            fig_wale = px.bar(
                asset_risk.sort_values("wale_yrs", ascending=True).dropna(subset=["wale_yrs"]),
                x="wale_yrs",
                y="asset_name",
                orientation="h",
                title="자산별 남은 임대기간",
                text="wale_yrs",
            )
            fig_wale.update_traces(texttemplate="%{text:.1f}y", textposition="outside", cliponaxis=False)
            st.plotly_chart(compact_fig(fig_wale, 245), width="stretch")

    st.markdown("---")
    st.markdown("## 6. 부채 만기와 차환 부담")

    if debt_schedule.empty or debt_summary.empty:
        st.warning("선택 회사의 차입금 만기 상세 데이터가 부족하여 만기 wall 상세표를 표시하지 않습니다.")
    else:
        total_principal = debt_schedule["principal_mn_krw"].sum()
        fixed_principal = debt_schedule[debt_schedule["rate_type"] == "고정"]["principal_mn_krw"].sum()
        floating_principal = debt_schedule[debt_schedule["rate_type"] == "변동"]["principal_mn_krw"].sum()
        near_1y = debt_schedule[debt_schedule["days_to_maturity"].between(0, 365, inclusive="both")]["principal_mn_krw"].sum()

        b1, b2, b3, b4 = st.columns(4)
        b1.metric("공시 차입금", format_trn_krw_from_mn(total_principal))
        b2.metric("고정금리 비중", format_pct_from_100(fixed_principal / total_principal * 100 if total_principal else pd.NA))
        b3.metric("변동금리 비중", format_pct_from_100(floating_principal / total_principal * 100 if total_principal else pd.NA))
        b4.metric("1년 내 만기", format_pct_from_100(near_1y / total_principal * 100 if total_principal else pd.NA))

        d_left, d_right = st.columns([1.15, 0.85])

        with d_left:
            debt_by_year = debt_summary.groupby("maturity_year", as_index=False).agg(
                principal_mn_krw=("principal_mn_krw", "sum"),
                weighted_avg_all_in_rate_pct=("weighted_avg_all_in_rate_pct", "mean"),
                number_of_facilities=("number_of_facilities", "sum"),
            )
            fig_wall = px.bar(
                debt_by_year.sort_values("maturity_year"),
                x="maturity_year",
                y="principal_mn_krw",
                title="연도별 부채 만기",
                text="principal_mn_krw",
            )
            fig_wall.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
            st.plotly_chart(compact_fig(fig_wall, 250), width="stretch")

        with d_right:
            debt_simple = debt_by_year.rename(columns={
                "maturity_year": "만기연도",
                "principal_mn_krw": "원금_백만원",
                "weighted_avg_all_in_rate_pct": "평균금리_%",
                "number_of_facilities": "건수",
            })
            st.write("**만기 요약**")
            st.dataframe(debt_simple, width="stretch", hide_index=True, height=250)

    st.markdown("---")
    st.markdown("## 7. 부동산 가치와 장부기준 NAV proxy 변화")
    st.caption("Cap rate proxy는 부동산 수익률 proxy입니다. 이 수치가 오르면 같은 NOI proxy를 가진 부동산의 평가가치는 내려갑니다.")

    v1, v2, v3, v4 = st.columns(4)
    v1.metric("현재 장부NAV proxy", format_trn_krw_from_mn(scenario["base_nav"]))
    v2.metric("시나리오 후 장부NAV proxy", format_trn_krw_from_mn(scenario["stressed_nav"]))
    v3.metric("장부NAV proxy 변화", format_pct_from_100(scenario["nav_change_pct"]))
    v4.metric("배당 후 남는 여력", fmt_mn_to_bn(scenario["dividend_cushion"]))

    asset_sens = scenario["asset_sensitivity"].copy().sort_values("value_change_pct")
    if asset_sens.empty:
        st.info("선택 회사의 자산별 Cap rate 및 평가액 데이터가 부족하여 자산가치 변화 표를 표시하지 않습니다.")
    else:
        val_left, val_right = st.columns([1.15, 0.85])

        with val_left:
            fig_nav = px.bar(
                asset_sens,
                x="value_change_pct",
                y="asset_name",
                orientation="h",
                title=f"자산별 가치 변화: Cap rate +{cap_rate_shock_bp}bp",
                text="value_change_pct",
            )
            fig_nav.update_traces(texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
            st.plotly_chart(compact_fig(fig_nav, 270), width="stretch")

        with val_right:
            sens_simple = asset_sens[[
                "asset_name",
                "cap_rate_pct_20251231",
                "appraised_value_mn_krw_20251231",
                "value_under_cap_rate_shock_mn_krw",
                "value_change_pct",
            ]].copy()
            sens_simple = sens_simple.rename(columns={
                "asset_name": "자산",
                "cap_rate_pct_20251231": "현재_Cap_rate_%",
                "appraised_value_mn_krw_20251231": "현재가치_백만원",
                "value_under_cap_rate_shock_mn_krw": "시나리오후_가치_백만원",
                "value_change_pct": "가치변화_%",
            })
            st.write("**자산가치 변화 표**")
            st.dataframe(sens_simple, width="stretch", hide_index=True, height=270)

    st.markdown("---")
    st.markdown("## 8. 자료 출처와 계산 기준")
    st.caption("공시자료와 API 자료의 출처는 하단에서 필요한 경우만 확인합니다.")

    with st.expander("자료 출처, 데이터 사전, 추가 확인 자료 보기", expanded=False):
        s1, s2 = st.columns(2)
        with s1:
            st.write("**자료 신뢰도 요약**")
            source_conf = pd.concat([
                asset_risk[["source_document", "source_confidence"]],
                debt_schedule[["source_document", "source_confidence"]],
                financials[["source_document", "source_confidence"]],
                kpis[["source_document", "source_confidence"]],
            ], ignore_index=True).drop_duplicates()
            source_conf = source_conf.rename(columns={
                "source_document": "자료 문서",
                "source_confidence": "자료 신뢰도",
            })
            st.dataframe(source_conf, width="stretch", hide_index=True, height=170)
            st.caption(
                "거시경제 지표: "
                f"{sanitize_secret_text(macro_context['source'])} / "
                f"과거 금리: {_display_api_status(macro_history_status)} / "
                f"DART: {_display_api_status(dart_status)}"
            )
        with s2:
            st.write("**추가 수집 자료 계획**")
            st.dataframe(source_plan, width="stretch", hide_index=True, height=170)

        if dart_reports is not None and not dart_reports.empty:
            st.write("**DART에서 확인한 최근 사업보고서**")
            report_cols = [c for c in ["rcept_dt", "report_nm", "rcept_no"] if c in dart_reports.columns]
            st.dataframe(dart_reports[report_cols].head(10), width="stretch", hide_index=True, height=150)

        st.write("**데이터 사전**")
        st.dataframe(data_dictionary, width="stretch", hide_index=True, height=160)

        st.write("**불러온 CSV 표**")
        loaded = pd.DataFrame({
            "table": [
                "sk_reit_consolidated_financials.csv",
                "sk_reit_latest_kpis.csv",
                "sk_reit_asset_metrics.csv",
                "sk_reit_parent_direct_assets_20260331.csv",
                "sk_reit_debt_schedule_20260331.csv",
                "sk_reit_debt_summary_20260331.csv",
                "sk_reit_additional_source_plan.csv",
                "sk_reit_data_dictionary.csv",
                "reit_master.csv",
                "reit_peer_snapshot.csv",
                "red_flag_rules.json",
            ],
            "purpose": [
                "재무 추이와 K-IFRS 기준 부채비율 분석",
                "장부NAV proxy, FFO proxy, 배당, 차입, FFO 이자감당력 proxy KPI",
                "자산 평가액, 임대차, 주요 임차인 정보",
                "투자보고서 기준 직접 보유자산 세부정보",
                "차입 약정별 만기와 금리 분석",
                "연도별 차환 부담 요약",
                "추가 수집이 필요한 자료 계획",
                "컬럼 정의와 산식 기준 메모",
                "상장리츠 peer master 정보",
                "Peer Benchmark와 Red Flag Engine snapshot",
                "Assurance 및 Tax Red Flag 판단 규칙",
            ],
        })
        st.dataframe(loaded.rename(columns={"table": "파일명", "purpose": "사용 목적"}), width="stretch", hide_index=True, height=170)

    st.divider()
    st.caption(
        "주의: 이 Streamlit 프로토타입은 리츠 위험을 빠르게 확인하기 위한 예비 분석 도구입니다. "
        "DART·ECOS API 결과는 각 기관의 제공 범위와 승인 상태에 따라 달라질 수 있으며, "
        "투자추천, 정식 가치평가, 감사의견, 신용등급, 법률·세무 자문을 제공하지 않습니다."
    )
