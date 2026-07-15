from __future__ import annotations

import pandas as pd
import streamlit as st

from src.tax_v15.constants import DISCLAIMER_KO, SOURCE_BADGES
from src.tax_v15.loaders import load_v15_bundle
from src.tax_v15.reporting import (
    build_tax_review_memo,
    dataframe_csv_bytes,
    review_document_html,
    review_pack_excel_bytes,
)
from src.tax_v15.validation import summarize_coverage


STATUS_ORDER = [
    "verified_notice",
    "official_source_calculated",
    "official_partial",
    "manual_review_required",
    "data_insufficient",
    "not_applicable",
]

GOLDEN_ASSET_ID = "SKR-SEOUL-SEORIN-001"


@st.cache_data(ttl=3600, show_spinner=False)
def _load_tax_v15_data():
    return load_v15_bundle()


def _safe_text(value, fallback: str = "데이터 부족") -> str:
    if value is None or value is pd.NA:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text or fallback


def _status_label(status: str) -> str:
    return f"[{SOURCE_BADGES.get(status, '데이터 부족')}]"


def _display_calculations(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "tax_name", "tax_classification", "official_value", "tax_base", "tax_rate", "multiplier",
        "calculated_tax", "calculation_status", "formula_text", "article", "source_url",
    ]
    if frame is None or frame.empty:
        return pd.DataFrame(columns=[
            "세목", "과세구분", "공식 입력값(원)", "과세표준(원)", "세율", "배율", "계산세액(원)",
            "근거 상태", "계산식", "법적 근거", "출처",
        ])
    result = frame[columns].copy()
    result["calculation_status"] = result["calculation_status"].map(
        lambda value: _status_label(str(value))
    )
    result = result.rename(columns={
        "tax_name": "세목",
        "tax_classification": "과세구분",
        "official_value": "공식 입력값(원)",
        "tax_base": "과세표준(원)",
        "tax_rate": "세율",
        "multiplier": "배율",
        "calculated_tax": "계산세액(원)",
        "calculation_status": "근거 상태",
        "formula_text": "계산식",
        "article": "법적 근거",
        "source_url": "출처",
    })
    return result


def _render_frame(frame: pd.DataFrame, *, height: int = 230) -> None:
    if frame is None or frame.empty:
        st.info("현재 공개자료에서 확인 가능한 행이 없습니다. 검증되지 않은 값은 계산하지 않습니다.")
        return
    config = {}
    for column in ["출처", "source_url", "공식 홈페이지"]:
        if column in frame.columns:
            config[column] = st.column_config.LinkColumn(column, display_text="원문")
    st.dataframe(frame, hide_index=True, width="stretch", height=height, column_config=config)


def _render_golden_asset_summary(
    assets: pd.DataFrame,
    parcels: pd.DataFrame,
    buildings: pd.DataFrame,
    taxpayers: pd.DataFrame,
    calculations: pd.DataFrame,
    reconciliation: pd.DataFrame,
) -> None:
    golden_assets = assets[assets["asset_id"].fillna("").astype(str).eq(GOLDEN_ASSET_ID)]
    if golden_assets.empty:
        return

    golden_parcels = parcels[
        parcels["asset_id"].fillna("").astype(str).eq(GOLDEN_ASSET_ID)
    ]
    golden_buildings = buildings[
        buildings["asset_id"].fillna("").astype(str).eq(GOLDEN_ASSET_ID)
    ]
    golden_taxpayers = taxpayers[
        taxpayers["asset_id"].fillna("").astype(str).eq(GOLDEN_ASSET_ID)
    ]
    golden_calculations = calculations[
        calculations["asset_id"].fillna("").astype(str).eq(GOLDEN_ASSET_ID)
        | calculations["taxpayer_id"].fillna("").astype(str).eq("SKR-TP-001")
    ].copy()
    blocked = golden_calculations["calculation_status"].isin(
        ["official_partial", "manual_review_required", "data_insufficient"]
    ).any()
    notice_rows = reconciliation[
        reconciliation["metric"].fillna("").astype(str).eq(
            "holding_tax_notice_reconciliation"
        )
    ]
    notice_complete = (
        not notice_rows.empty
        and pd.to_numeric(
            notice_rows["disclosed_or_verified_value"], errors="coerce"
        ).notna().any()
    )
    taxpayer_verified = (
        not golden_taxpayers.empty
        and golden_taxpayers["validation_status"]
        .fillna("")
        .astype(str)
        .isin(["verified_notice", "official_source_calculated"])
        .all()
    )
    separation_verified = (
        taxpayer_verified
        and golden_taxpayers["tax_classification"]
        .fillna("")
        .astype(str)
        .eq("separated_public_reit")
        .all()
    )
    status_rows = pd.DataFrame(
        [
            {
                "검증항목": "계산 완료 여부",
                "상태": "공식자료 계산 완료" if not blocked else "추가자료 필요",
                "확인 내용": "고지서 대사 전 계산값",
            },
            {
                "검증항목": "토지 Coverage",
                "상태": "공식자료 계산 완료" if len(golden_parcels) else "데이터 부족",
                "확인 내용": (
                    f"현행 PNU {len(golden_parcels)}건 / 개별공시지가 "
                    f"{pd.to_numeric(golden_parcels.get('individual_land_price_per_m2'), errors='coerce').notna().sum()}건"
                ),
            },
            {
                "검증항목": "건축물 Coverage",
                "상태": "공식자료 계산 완료" if len(golden_buildings) else "데이터 부족",
                "확인 내용": (
                    f"2026년 시가표준액 "
                    f"{pd.to_numeric(golden_buildings.get('building_standard_value'), errors='coerce').notna().sum()}건"
                ),
            },
            {
                "검증항목": "납세의무자 검증",
                "상태": "공식자료 판정" if taxpayer_verified else "수동 검토",
                "확인 내용": "신탁 위탁자 기준",
            },
            {
                "검증항목": "분리과세 검증",
                "상태": "공식자료 판정" if separation_verified else "수동 검토",
                "확인 내용": "공모리츠 목적사업용 토지",
            },
            {
                "검증항목": "실제 고지서 대사",
                "상태": "완료" if notice_complete else "미완료",
                "확인 내용": "2026년 고지서·과세내역서 필요",
            },
        ]
    )

    tax_rows = golden_calculations[
        golden_calculations["tax_name"].ne("토지 시가표준액")
    ].copy()
    tax_rows["구분"] = "납세의무자"
    tax_rows.loc[tax_rows["parcel_id"].fillna("").astype(str).ne(""), "구분"] = "토지"
    tax_rows.loc[tax_rows["building_id"].fillna("").astype(str).ne(""), "구분"] = "건축물"
    tax_rows["근거 상태"] = tax_rows["calculation_status"].map(
        lambda value: _status_label(str(value))
    )
    tax_rows["계산세액(원)"] = pd.to_numeric(
        tax_rows["calculated_tax"], errors="coerce"
    )
    tax_display = tax_rows[["구분", "tax_name", "계산세액(원)", "근거 상태"]].rename(
        columns={"tax_name": "세목"}
    )
    total = tax_rows.loc[
        tax_rows["calculation_status"].isin(
            ["verified_notice", "official_source_calculated", "not_applicable"]
        ),
        "계산세액(원)",
    ].sum(min_count=1)

    with st.container(border=True):
        st.markdown("### Golden Asset: SK서린빌딩")
        st.success(
            f"공식자료 계산 합계는 {total:,.0f}원입니다. "
            "토지·건물 공식 입력값을 사용했으며 실제 고지서 대사 전 수치입니다."
        )
        st.dataframe(status_rows, hide_index=True, width="stretch", height=250)
        st.markdown("**세목별 공식자료 계산 결과**")
        st.dataframe(
            tax_display,
            hide_index=True,
            width="stretch",
            height=330,
            column_config={
                "계산세액(원)": st.column_config.NumberColumn(format="%,.2f원"),
            },
        )
        st.caption(
            "건축물대장 부속지번 서린동 91과 현행 토지대장 간 5.3㎡ 차이는 "
            "대사 미결사항으로 유지했습니다. 최신 토지대장·지적도 및 과세내역서가 필요합니다."
        )


def _rule_rows(rules: pd.DataFrame, codes: list[str]) -> pd.DataFrame:
    if rules.empty:
        return pd.DataFrame()
    selected = rules[rules["rule_code"].isin(codes)].copy()
    columns = [
        "tax_name", "tax_classification", "bracket_start", "bracket_end", "marginal_rate",
        "fair_market_value_ratio", "law_name", "article", "exact_clause_summary", "source_url",
    ]
    selected = selected[columns].drop_duplicates()
    return selected.rename(columns={
        "tax_name": "세목", "tax_classification": "구분", "bracket_start": "구간 시작",
        "bracket_end": "구간 종료", "marginal_rate": "세율", "fair_market_value_ratio": "공정시장가액비율",
        "law_name": "법령", "article": "조문", "exact_clause_summary": "검증 요약", "source_url": "출처",
    })


def _render_stage(
    number: int,
    title: str,
    *,
    conclusion: str,
    legal_basis: pd.DataFrame | None = None,
    clause: str = "",
    requirements: list[str] | None = None,
    formula: str = "",
    calculation_rows: pd.DataFrame | None = None,
    source_rows: pd.DataFrame | None = None,
    limitation: str = "",
    expanded: bool = False,
) -> None:
    with st.expander(f"{number}. {title}", expanded=expanded):
        st.markdown("**A. 결론**")
        st.write(conclusion)
        if legal_basis is not None and not legal_basis.empty:
            st.markdown("**B. 적용 법규**")
            _render_frame(legal_basis, height=min(260, 72 + len(legal_basis) * 35))
        if clause:
            st.markdown("**C. 법규 핵심 문구**")
            st.write(clause)
        if requirements:
            st.markdown("**D. 적용 요건**")
            for item in requirements:
                st.write(f"- {item}")
        if formula:
            st.markdown("**E. 계산 공식**")
            st.code(formula, language="text")
        if calculation_rows is not None:
            st.markdown("**F-G. 실제 숫자 대입 및 계산 결과**")
            _render_frame(_display_calculations(calculation_rows), height=260)
        if source_rows is not None:
            st.markdown("**H. 출처**")
            _render_frame(source_rows, height=220)
        if limitation:
            st.markdown("**I. 한계 및 검토 필요사항**")
            st.warning(limitation)


def render_tax_mode(
    asset_risk: pd.DataFrame,
    scenario: dict,
    latest_kpi: pd.Series,
    assumptions: dict | None = None,
    peer_context: dict | None = None,
):
    del asset_risk, scenario, latest_kpi, assumptions
    bundle = _load_tax_v15_data()
    st.markdown("## Tax: 자산·납세의무자 단위 보유세 검토")
    st.caption("공식 출처가 연결된 자산·필지·납세의무자 입력만 계산하며, 불명확한 항목은 수동 검토 또는 데이터 부족으로 차단합니다.")

    if bundle.reits.empty:
        st.error("v15 상장리츠 목록이 없습니다. 데이터 파이프라인을 먼저 실행해야 합니다.")
        return

    profile_code = str((peer_context or {}).get("selected_company_profile", {}).get("stock_code", ""))
    reit_options = bundle.reits.sort_values(["reit_name", "stock_code"])[["stock_code", "reit_name"]].copy()
    option_labels = [f"{row.reit_name} ({row.stock_code})" for row in reit_options.itertuples()]
    default_index = next((idx for idx, row in enumerate(reit_options.itertuples()) if str(row.stock_code) == profile_code), 0)
    tax_years = sorted(pd.to_numeric(bundle.rules["tax_year"], errors="coerce").dropna().astype(int).unique(), reverse=True)

    f1, f2 = st.columns([1.35, 0.65])
    with f1:
        selected_label = st.selectbox("분석대상 리츠", option_labels, index=default_index, key="v15_tax_reit")
    with f2:
        tax_year = st.selectbox("기준연도", tax_years or [2026], key="v15_tax_year")
    stock_code = selected_label.rsplit("(", 1)[-1].rstrip(")")
    selected_reit = bundle.reits[bundle.reits["stock_code"].astype(str).eq(stock_code)].iloc[0]
    reit_name = str(selected_reit["reit_name"])

    assets = bundle.assets[bundle.assets["stock_code"].astype(str).eq(stock_code)].copy()
    asset_ids = set(assets["asset_id"].dropna().astype(str))
    parcels = bundle.parcels[bundle.parcels["asset_id"].astype(str).isin(asset_ids)].copy()
    buildings = bundle.buildings[bundle.buildings["asset_id"].astype(str).isin(asset_ids)].copy()
    taxpayers = bundle.taxpayers[bundle.taxpayers["asset_id"].astype(str).isin(asset_ids)].copy()
    calculations = bundle.calculations[
        bundle.calculations["reit_name"].astype(str).eq(reit_name)
        & pd.to_numeric(bundle.calculations["tax_year"], errors="coerce").eq(int(tax_year))
    ].copy()
    full_calculations = calculations.copy()
    validations = bundle.validations[bundle.validations["reit_name"].astype(str).eq(reit_name)].copy()
    requests = bundle.requests[bundle.requests["reit_name"].astype(str).eq(reit_name)].copy()
    reconciliation = bundle.reconciliation[
        bundle.reconciliation["reit_name"].astype(str).eq(reit_name)
    ].copy()

    a1, a2, a3 = st.columns(3)
    with a1:
        asset_options = ["전체 자산"] + sorted(assets["asset_name"].dropna().astype(str).unique().tolist())
        selected_asset = st.selectbox("자산", asset_options, key="v15_tax_asset")
    with a2:
        taxpayer_options = ["전체 납세의무자"] + sorted(taxpayers["taxpayer_id"].dropna().astype(str).unique().tolist())
        selected_taxpayer = st.selectbox("납세의무자", taxpayer_options, key="v15_tax_taxpayer")
    with a3:
        ownership_options = ["전체 보유구조"] + sorted(assets["direct_or_indirect"].dropna().astype(str).unique().tolist())
        selected_ownership = st.selectbox("직접·간접보유", ownership_options, key="v15_tax_ownership")
    status_options = [status for status in STATUS_ORDER if status in set(calculations["calculation_status"].astype(str))]
    selected_statuses = st.multiselect(
        "계산상태",
        status_options,
        default=status_options,
        format_func=lambda status: _status_label(status),
        key="v15_tax_status",
    )

    if selected_asset != "전체 자산":
        chosen_ids = set(assets.loc[assets["asset_name"].eq(selected_asset), "asset_id"].astype(str))
        assets = assets[assets["asset_id"].astype(str).isin(chosen_ids)]
        parcels = parcels[parcels["asset_id"].astype(str).isin(chosen_ids)]
        buildings = buildings[buildings["asset_id"].astype(str).isin(chosen_ids)]
        taxpayers = taxpayers[taxpayers["asset_id"].astype(str).isin(chosen_ids)]
        calculations = calculations[calculations["asset_id"].astype(str).isin(chosen_ids) | calculations["asset_id"].fillna("").eq("")]
    if selected_taxpayer != "전체 납세의무자":
        calculations = calculations[calculations["taxpayer_id"].astype(str).eq(selected_taxpayer)]
        taxpayers = taxpayers[taxpayers["taxpayer_id"].astype(str).eq(selected_taxpayer)]
    if selected_ownership != "전체 보유구조":
        ownership_ids = set(assets.loc[assets["direct_or_indirect"].eq(selected_ownership), "asset_id"].astype(str))
        assets = assets[assets["asset_id"].astype(str).isin(ownership_ids)]
        calculations = calculations[calculations["asset_id"].astype(str).isin(ownership_ids)]
    if selected_statuses:
        calculations = calculations[calculations["calculation_status"].isin(selected_statuses)]

    _render_golden_asset_summary(
        assets,
        parcels,
        buildings,
        taxpayers,
        full_calculations,
        reconciliation,
    )

    coverage = summarize_coverage(assets, parcels, buildings, taxpayers, calculations)
    verified_rows = calculations[
        calculations["calculation_status"].isin(["verified_notice", "official_source_calculated"])
        & calculations["tax_name"].ne("토지 시가표준액")
    ]
    verified_amounts = pd.to_numeric(verified_rows["calculated_tax"], errors="coerce").dropna()
    verified_total = verified_amounts.sum() if not verified_amounts.empty else None
    with st.container(border=True):
        st.markdown("### 결론")
        if verified_total is None:
            st.warning(
                f"{reit_name}은 현재 공개자료만으로 확정 표시할 수 있는 보유세 합계가 없습니다. "
                "검증되지 않은 주소·필지·납세의무자·시가표준액은 0이나 추정값으로 대체하지 않았습니다."
            )
        else:
            st.success(
                f"{reit_name}의 공식자료 계산 행 단순 합계는 {verified_total:,.0f}원입니다. "
                "고지서 대사·감면·세부담상한 검토 전 수치이며 신고 목적 확정세액이 아닙니다."
            )
        st.caption(
            f"검토 신뢰도: 자산 {coverage['asset_count']}건 · 주소 검증 {coverage['verified_address_count']}건 · "
            f"PNU 검증 {coverage['verified_pnu_count']}건 · 건축물 시가표준액 {coverage['verified_building_value_count']}건 · "
            f"최종 상태 {coverage['final_status']}"
        )

    legal_reit = _rule_rows(bundle.rules, ["public_reit_definition"])
    source_reit = pd.DataFrame([{
        "항목": "상장리츠 목록", "근거 상태": _status_label(str(selected_reit.get("verification_status", "data_insufficient"))),
        "공식 홈페이지": selected_reit.get("official_website", ""), "출처": selected_reit.get("source_url", ""),
    }])
    _render_stage(
        1, "분석대상 리츠와 기준연도",
        conclusion=f"{reit_name} ({stock_code}), {tax_year}년을 검토 대상으로 선택했습니다.",
        source_rows=source_reit,
        limitation="상장 사실은 공식 리츠정보시스템으로 확인했으나, 공모리츠 분리과세 요건은 별도 법적 판정 대상입니다.",
        expanded=True,
    )
    asset_display = assets[["asset_name", "asset_class", "direct_or_indirect", "legal_owner_name", "road_address", "verification_status", "source_url"]].rename(columns={
        "asset_name": "자산명", "asset_class": "자산유형", "direct_or_indirect": "보유구조", "legal_owner_name": "법적 소유자",
        "road_address": "주소", "verification_status": "검증상태", "source_url": "출처",
    }) if not assets.empty else pd.DataFrame()
    _render_stage(
        2, "자산 및 납세의무자 구조",
        conclusion=f"공식자료에서 식별된 자산 {len(assets)}건과 납세의무자 검토 행 {len(taxpayers)}건을 연결했습니다.",
        requirements=["직접·간접 보유구조", "법적 소유자", "신탁 위탁자·수탁자", "과세기준일 현재 소유지분"],
        source_rows=asset_display,
        limitation="법적 소유자 또는 신탁관계가 확인되지 않은 자산은 세액 계산에 사용하지 않습니다.",
    )
    _render_stage(
        3, "공모부동산투자회사 법적 요건",
        conclusion=_safe_text(selected_reit.get("public_reit_status"), "수동 검토 필요"),
        legal_basis=legal_reit,
        clause="부동산투자회사법 제49조의3의 공모부동산투자회사 해당 여부를 상장 여부와 별도로 확인합니다.",
        requirements=["법적 주체가 부동산투자회사인지", "공모부동산투자회사인지", "자회사 리츠 포함 요건에 해당하는지"],
        limitation="현재 Master의 public_reit_status가 수동 검토 상태이면 분리과세 결론을 자동 확정하지 않습니다.",
    )
    taxpayer_display = taxpayers[["taxpayer_id", "legal_owner", "tax_obligor", "public_reit_qualified", "purpose_business_use", "tax_classification", "validation_status", "source_url"]].rename(columns={
        "taxpayer_id": "납세의무자 ID", "legal_owner": "법적 소유자", "tax_obligor": "납세의무자", "public_reit_qualified": "공모리츠 요건",
        "purpose_business_use": "목적사업 사용", "tax_classification": "과세구분", "validation_status": "검증상태", "source_url": "출처",
    }) if not taxpayers.empty else pd.DataFrame()
    _render_stage(
        4, "분리과세 적용 요건",
        conclusion="모든 필수 법적 요건이 확인된 토지만 separated_public_reit로 판정합니다.",
        legal_basis=_rule_rows(bundle.rules, ["public_reit_land_separation"]),
        requirements=["공모리츠 또는 법정 자회사 리츠", "6월 1일 현재 소유", "목적사업 직접 사용", "주택이 아닌 토지", "제외·중과 규정 미적용"],
        source_rows=taxpayer_display,
        limitation="listed=true만으로 분리과세를 적용하지 않습니다.",
    )
    _render_stage(
        5, "과세기준일 및 납세의무자",
        conclusion=f"납세의무자 공식 검증 완료 행은 {coverage['verified_taxpayer_count']}건입니다.",
        legal_basis=_rule_rows(bundle.rules, ["property_tax_obligor"]),
        requirements=["매년 6월 1일 현재 사실상 소유자", "신탁재산의 위탁자 및 물적납세의무 검토", "공동소유 지분 확인"],
        source_rows=taxpayer_display,
        limitation="등기부등본·신탁원부·과세내역서가 없으면 납세의무자를 확정하지 않습니다.",
    )
    parcel_display = parcels[["parcel_id", "asset_id", "pnu", "road_address", "lot_address", "parcel_area_m2", "ownership_share", "validation_status", "source_url"]].rename(columns={
        "parcel_id": "필지 ID", "asset_id": "자산 ID", "pnu": "PNU", "road_address": "도로명주소", "lot_address": "지번주소",
        "parcel_area_m2": "필지면적(㎡)", "ownership_share": "소유지분", "validation_status": "검증상태", "source_url": "출처",
    }) if not parcels.empty else pd.DataFrame()
    _render_stage(
        6, "자산별 주소와 PNU",
        conclusion=f"주소 검증 {coverage['verified_address_count']}건, 19자리 PNU 검증 {coverage['verified_pnu_count']}건입니다.",
        source_rows=parcel_display,
        limitation="도로명주소 하나를 단일 필지로 간주하지 않습니다. 복수 필지는 PNU별로 확인해야 합니다.",
    )
    land_value_rows = calculations[calculations["tax_name"].eq("토지 시가표준액")]
    _render_stage(
        7, "토지 시가표준액 도출",
        conclusion=f"개별공시지가가 공식 확인된 필지는 {coverage['verified_land_price_count']}건입니다.",
        formula="필지별 토지 시가표준액 = 개별공시지가(원/㎡) × 과세면적(㎡) × 소유지분",
        calculation_rows=land_value_rows,
        limitation="PNU·과세면적·소유지분·기준연도 개별공시지가 중 하나라도 없으면 계산하지 않습니다.",
    )
    land_tax_rows = calculations[calculations["tax_name"].eq("토지 재산세")]
    _render_stage(
        8, "토지 재산세 계산",
        conclusion=f"토지 재산세 계산 또는 차단 행은 {len(land_tax_rows)}건입니다.",
        legal_basis=_rule_rows(bundle.rules, ["property_tax_land_separated", "property_tax_land_aggregate", "property_tax_land_separate_aggregate"]),
        formula="토지 재산세 과세표준 = 필지별 토지 시가표준액 × 해당 연도 공정시장가액비율\n토지 재산세 = 과세표준 × 검증된 과세구분별 세율",
        calculation_rows=land_tax_rows,
        limitation="분리·종합·별도합산 구분이 확정되지 않으면 세율을 적용하지 않습니다.",
    )
    building_display = buildings[["building_id", "building_name", "gross_floor_area_m2", "building_standard_value", "building_standard_value_year", "validation_status", "source_url"]].rename(columns={
        "building_id": "건축물 ID", "building_name": "건축물명", "gross_floor_area_m2": "연면적(㎡)", "building_standard_value": "건축물 시가표준액",
        "building_standard_value_year": "기준연도", "validation_status": "검증상태", "source_url": "출처",
    }) if not buildings.empty else pd.DataFrame()
    _render_stage(
        9, "건축물 시가표준액 도출",
        conclusion=f"공식 건축물 시가표준액 확인 건은 {coverage['verified_building_value_count']}건입니다.",
        source_rows=building_display,
        limitation="투자부동산 장부가액·감정가에 임의 비율을 곱해 건축물 시가표준액을 만들지 않습니다.",
    )
    building_tax_rows = calculations[calculations["tax_name"].eq("건축물 재산세")]
    _render_stage(
        10, "건축물 재산세 계산",
        conclusion=f"건축물 재산세 계산 또는 차단 행은 {len(building_tax_rows)}건입니다.",
        legal_basis=_rule_rows(bundle.rules, ["property_tax_building_general"]),
        formula="건축물 재산세 과세표준 = 공식 건축물 시가표준액 × 공정시장가액비율\n건축물 재산세 = 과세표준 × 검증된 용도별 세율",
        calculation_rows=building_tax_rows,
        limitation="건축물 용도별 중과 여부와 공식 시가표준액이 확인되어야 합니다.",
    )
    local_rows = calculations[calculations["tax_name"].isin(["재산세 도시지역분", "지방교육세"])]
    _render_stage(
        11, "도시지역분·지방교육세",
        conclusion=f"도시지역분·지방교육세 계산 또는 차단 행은 {len(local_rows)}건입니다.",
        legal_basis=_rule_rows(bundle.rules, ["urban_area_tax_standard", "local_education_tax"]),
        formula="도시지역분 = 검증된 과세표준 × 조례 적용 세율\n지방교육세 = 재산세 본세(도시지역분 제외) × 법정 세율",
        calculation_rows=local_rows,
        limitation="도시지역분 적용대상 고시와 지방자치단체 조례가 확인되지 않으면 자동 부과하지 않습니다.",
    )
    fire_rows = calculations[calculations["tax_name"].eq("소방분 지역자원시설세")]
    _render_stage(
        12, "소방분 지역자원시설세",
        conclusion=f"소방분 계산 또는 차단 행은 {len(fire_rows)}건입니다.",
        legal_basis=_rule_rows(bundle.rules, ["fire_resource_tax", "fire_multiplier_standard", "fire_multiplier_200", "fire_multiplier_300"]),
        formula="소방분 = 건축물 시가표준액 누진세액 × 검증된 위험유형 배율(100%·200%·300%)",
        calculation_rows=fire_rows,
        limitation="시가표준액 또는 화재위험 유형이 불명확하면 계산하지 않습니다.",
    )
    comp_rows = calculations[calculations["tax_name"].isin(["토지분 종합부동산세", "종합부동산세분 농어촌특별세"])]
    _render_stage(
        13, "종합부동산세·농어촌특별세",
        conclusion=f"종부세·농어촌특별세 계산 또는 차단 행은 {len(comp_rows)}건입니다.",
        legal_basis=_rule_rows(bundle.rules, [
            "comprehensive_land_aggregate_deduction", "comprehensive_land_aggregate",
            "comprehensive_land_separate_aggregate_deduction", "comprehensive_land_separate_aggregate", "rural_special_tax",
        ]),
        formula="종부세 = 납세의무자별 전국 합산 과세표준에 누진세율 적용 - 재산세 공제액\n농어촌특별세 = 검증된 종합부동산세액 × 법정 세율",
        calculation_rows=comp_rows,
        limitation="분리과세 토지는 해당 없음으로 표시합니다. 종합·별도합산은 전국 합산 공시가격과 재산세 공제액이 없으면 계산을 차단합니다.",
    )

    memo = build_tax_review_memo(
        reit_name, int(tax_year), assets, parcels, buildings, taxpayers, calculations, validations, requests
    )
    with st.expander("14. 총 보유세, 검증 결과 및 요청자료", expanded=True):
        st.markdown("**A. 결론**")
        st.write(
            f"공식자료 계산·고지서 확인 행 {coverage['completed_calculation_rows']}건, "
            f"수동 검토·데이터 부족 행 {coverage['blocked_calculation_rows']}건입니다."
        )
        st.markdown("**납세의무자별 공식자료 계산 세액**")
        taxpayer_totals = verified_rows.copy()
        taxpayer_totals["calculated_tax"] = pd.to_numeric(taxpayer_totals["calculated_tax"], errors="coerce")
        taxpayer_totals = (
            taxpayer_totals.dropna(subset=["calculated_tax"])
            .groupby("taxpayer_id", dropna=False, as_index=False)["calculated_tax"]
            .sum()
            .rename(columns={"taxpayer_id": "납세의무자 ID", "calculated_tax": "공식자료 계산 세액(원)"})
        )
        _render_frame(taxpayer_totals, height=180)
        st.markdown("**검증 결과**")
        _render_frame(validations[["check_name", "severity", "validation_status", "message", "source_url"]].rename(columns={
            "check_name": "검증항목", "severity": "중요도", "validation_status": "상태", "message": "결과", "source_url": "출처",
        }) if not validations.empty else validations, height=260)
        st.markdown("**추가 요청자료**")
        _render_frame(requests[["priority", "issue", "request_document", "request_reason", "reviewer_status"]].rename(columns={
            "priority": "우선순위", "issue": "이슈", "request_document": "요청자료", "request_reason": "요청사유", "reviewer_status": "검토상태",
        }) if not requests.empty else requests, height=280)
        st.markdown("**Tax Review Memo**")
        st.markdown(memo)

        st.markdown("**다운로드**")
        safe_code = stock_code.replace("/", "_")
        try:
            excel_bytes = review_pack_excel_bytes({
                "Assets": assets, "Parcels": parcels, "Buildings": buildings, "Taxpayers": taxpayers,
                "Calculations": calculations, "Validation": validations, "Requests": requests,
            })
            excel_available = True
        except (ImportError, ModuleNotFoundError):
            excel_bytes = b""
            excel_available = False
        d1, d2, d3, d4 = st.columns(4)
        d1.download_button(
            "계산내역 CSV", dataframe_csv_bytes(calculations),
            file_name=f"{safe_code}_{tax_year}_tax_calculation_detail.csv", mime="text/csv", width="stretch",
        )
        d2.download_button(
            "검토팩 Excel",
            excel_bytes,
            file_name=f"{safe_code}_{tax_year}_tax_review_pack.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            disabled=not excel_available,
            width="stretch",
        )
        d3.download_button(
            "Memo Markdown", memo.encode("utf-8-sig"),
            file_name=f"{safe_code}_{tax_year}_tax_review_memo.md", mime="text/markdown", width="stretch",
        )
        d4.download_button(
            "검토문서 HTML", review_document_html(f"{reit_name} Tax Review", memo),
            file_name=f"{safe_code}_{tax_year}_tax_review_document.html", mime="text/html", width="stretch",
        )
        if not excel_available:
            st.caption("Excel 내보내기 패키지를 설치하면 검토팩 Excel 다운로드가 활성화됩니다.")
        st.warning(DISCLAIMER_KO)
