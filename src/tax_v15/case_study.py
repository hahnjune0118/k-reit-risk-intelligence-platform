from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pandas as pd

from .calculators.engine import calculate_holding_tax_detail
from .loaders import V15DataBundle
from .validation.controls import summarize_coverage


CORE_STOCK_CODE = "395400"
CORE_ASSET_ID = "SKR-SEOUL-SEORIN-001"
CORE_ASSET_TAXPAYER_ID = "SKR-TP-001"
CORE_TAX_YEAR = 2026
CORE_RECALCULATION_BEFORE_END_DIGIT_TREATMENT = Decimal("1250710968.55472")
CORE_RECALCULATION_AFTER_END_DIGIT_TREATMENT = Decimal("1250710930")

# Deprecated aliases retained for internal data-key compatibility.
GOLDEN_STOCK_CODE = CORE_STOCK_CODE
GOLDEN_ASSET_ID = CORE_ASSET_ID
GOLDEN_TAXPAYER_ID = CORE_ASSET_TAXPAYER_ID
GOLDEN_TAX_YEAR = CORE_TAX_YEAR
GOLDEN_RECALCULATION_RAW = CORE_RECALCULATION_BEFORE_END_DIGIT_TREATMENT

CALCULATED_STATUSES = {
    "verified_notice",
    "official_source_calculated",
    "not_applicable",
}

SCENARIO_SUMMARY_COLUMNS = [
    "민감도 분석",
    "토지 개별공시지가 변동률",
    "건축물 시가표준액 변동률",
    "끝수 처리 전 합계",
    "끝수 처리 후 합계",
    "기준 대비 증감액",
    "기준 대비 증감률",
]

ISSUE_MATRIX_COLUMNS = [
    "priority",
    "issue_code",
    "tax_issue",
    "current_status",
    "evidence_status",
    "potential_tax_effect",
    "quantitative_sensitivity",
    "required_document",
    "request_reason",
    "responsible_reviewer",
    "memo_included",
    "resolution_status",
]


@dataclass(frozen=True)
class CoreAssetTaxCaseData:
    reit_name: str
    stock_code: str
    tax_year: int
    assets: pd.DataFrame
    parcels: pd.DataFrame
    buildings: pd.DataFrame
    taxpayers: pd.DataFrame
    rules: pd.DataFrame
    calculations: pd.DataFrame
    validations: pd.DataFrame
    requests: pd.DataFrame
    reconciliation: pd.DataFrame


def select_core_asset_tax_case(bundle: V15DataBundle) -> CoreAssetTaxCaseData:
    assets = bundle.assets[
        bundle.assets["asset_id"].fillna("").astype(str).eq(CORE_ASSET_ID)
    ].copy()
    if len(assets) != 1:
        raise ValueError("SK서린빌딩 핵심 분석대상 자산을 하나로 식별할 수 없습니다.")

    reit_name = str(assets.iloc[0]["reit_name"])
    stock_code = str(assets.iloc[0]["stock_code"])
    if stock_code != CORE_STOCK_CODE:
        raise ValueError("핵심 분석대상 자산의 종목코드가 SK리츠와 일치하지 않습니다.")

    asset_ids = {CORE_ASSET_ID}
    parcels = bundle.parcels[
        bundle.parcels["asset_id"].fillna("").astype(str).isin(asset_ids)
    ].copy()
    buildings = bundle.buildings[
        bundle.buildings["asset_id"].fillna("").astype(str).isin(asset_ids)
    ].copy()
    taxpayers = bundle.taxpayers[
        bundle.taxpayers["asset_id"].fillna("").astype(str).isin(asset_ids)
    ].copy()
    calculations = bundle.calculations[
        (
            bundle.calculations["asset_id"]
            .fillna("")
            .astype(str)
            .eq(CORE_ASSET_ID)
        )
        | (
            bundle.calculations["taxpayer_id"]
            .fillna("")
            .astype(str)
            .eq(CORE_ASSET_TAXPAYER_ID)
        )
    ].copy()
    validations = bundle.validations[
        bundle.validations["reit_name"].fillna("").astype(str).eq(reit_name)
    ].copy()
    requests = bundle.requests[
        bundle.requests["reit_name"].fillna("").astype(str).eq(reit_name)
    ].copy()
    reconciliation = bundle.reconciliation[
        bundle.reconciliation["reit_name"].fillna("").astype(str).eq(reit_name)
        & pd.to_numeric(bundle.reconciliation["tax_year"], errors="coerce").eq(
            CORE_TAX_YEAR
        )
    ].copy()

    return CoreAssetTaxCaseData(
        reit_name=reit_name,
        stock_code=stock_code,
        tax_year=CORE_TAX_YEAR,
        assets=assets,
        parcels=parcels,
        buildings=buildings,
        taxpayers=taxpayers,
        rules=bundle.rules.copy(),
        calculations=calculations,
        validations=validations,
        requests=requests,
        reconciliation=reconciliation,
    )


# Deprecated API aliases retained for callers that still use the v15.0 names.
GoldenCaseData = CoreAssetTaxCaseData


def select_golden_case(bundle: V15DataBundle) -> CoreAssetTaxCaseData:
    return select_core_asset_tax_case(bundle)


def _decimal(value) -> Decimal:
    if value is None or pd.isna(value):
        return Decimal("0")
    return Decimal(str(value))


def _validate_scenario_change(value: int | float | Decimal, label: str) -> Decimal:
    change = Decimal(str(value))
    if change < Decimal("-10") or change > Decimal("20"):
        raise ValueError(f"{label}은 -10%부터 +20% 사이여야 합니다.")
    if change != change.to_integral_value():
        raise ValueError(f"{label}은 1% 단위 정수여야 합니다.")
    return change


def _scaled_inputs(
    case: CoreAssetTaxCaseData,
    land_change_pct: Decimal,
    building_change_pct: Decimal,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    parcels = case.parcels.copy()
    buildings = case.buildings.copy()
    land_factor = Decimal("1") + land_change_pct / Decimal("100")
    building_factor = Decimal("1") + building_change_pct / Decimal("100")

    parcels["individual_land_price_per_m2"] = parcels[
        "individual_land_price_per_m2"
    ].astype("object")
    for index, value in parcels["individual_land_price_per_m2"].items():
        parcels.at[index, "individual_land_price_per_m2"] = _decimal(value) * land_factor

    buildings["building_standard_value"] = buildings[
        "building_standard_value"
    ].astype("object")
    for index, value in buildings["building_standard_value"].items():
        buildings.at[index, "building_standard_value"] = (
            _decimal(value) * building_factor
        )
    return parcels, buildings


def _amount(frame: pd.DataFrame, mask: pd.Series, column: str) -> Decimal:
    rows = frame.loc[mask, column].dropna()
    return sum((_decimal(value) for value in rows), Decimal("0"))


def _detail_row(
    calculations: pd.DataFrame,
    scenario_name: str,
    display_name: str,
    mask: pd.Series,
) -> dict:
    rows = calculations.loc[mask].copy()
    before = _amount(
        calculations,
        mask,
        "calculated_tax_before_end_digit_treatment",
    )
    after = _amount(calculations, mask, "calculated_tax")
    statuses = sorted(set(rows["calculation_status"].dropna().astype(str)))
    articles = sorted(set(rows["article"].dropna().astype(str)))
    urls = sorted(set(rows["source_url"].dropna().astype(str)))
    return {
        "민감도 분석": scenario_name,
        "세목": display_name,
        "끝수 처리 전 산출세액": before,
        "끝수 처리 후 재계산액": after,
        "끝수 처리 차이": before - after,
        "계산상태": ", ".join(statuses) if statuses else "data_insufficient",
        "법적 근거": ", ".join(articles),
        "source_url": ", ".join(urls),
    }


def calculate_sensitivity_scenario(
    case: CoreAssetTaxCaseData,
    scenario_name: str,
    land_change_pct: int | float | Decimal,
    building_change_pct: int | float | Decimal,
) -> tuple[dict, pd.DataFrame]:
    land_change = _validate_scenario_change(
        land_change_pct, "토지 개별공시지가 변동률"
    )
    building_change = _validate_scenario_change(
        building_change_pct, "건축물 시가표준액 변동률"
    )
    parcels, buildings = _scaled_inputs(case, land_change, building_change)
    calculations = calculate_holding_tax_detail(
        case.reit_name,
        case.assets,
        parcels,
        buildings,
        case.taxpayers,
        case.rules,
        case.tax_year,
    )

    parcel_rows = calculations["parcel_id"].fillna("").astype(str).ne("")
    building_rows = calculations["building_id"].fillna("").astype(str).ne("")
    status_rows = calculations["calculation_status"].isin(CALCULATED_STATUSES)

    detail_specs = [
        ("토지 재산세", calculations["tax_name"].eq("토지 재산세")),
        (
            "토지 도시지역분",
            calculations["tax_name"].eq("재산세 도시지역분") & parcel_rows,
        ),
        (
            "토지 지방교육세",
            calculations["tax_name"].eq("지방교육세") & parcel_rows,
        ),
        ("건축물 재산세", calculations["tax_name"].eq("건축물 재산세")),
        (
            "건축물 도시지역분",
            calculations["tax_name"].eq("재산세 도시지역분") & building_rows,
        ),
        (
            "건축물 지방교육세",
            calculations["tax_name"].eq("지방교육세") & building_rows,
        ),
        (
            "소방분 지역자원시설세",
            calculations["tax_name"].eq("소방분 지역자원시설세"),
        ),
        (
            "종합부동산세",
            calculations["tax_name"].eq("토지분 종합부동산세"),
        ),
        (
            "농어촌특별세",
            calculations["tax_name"].eq("종합부동산세분 농어촌특별세"),
        ),
    ]
    details = pd.DataFrame(
        [
            _detail_row(
                calculations,
                scenario_name,
                display_name,
                mask & status_rows,
            )
            for display_name, mask in detail_specs
        ]
    )
    total_before = sum(details["끝수 처리 전 산출세액"], Decimal("0"))
    total_after = sum(details["끝수 처리 후 재계산액"], Decimal("0"))
    details = pd.concat(
        [
            details,
            pd.DataFrame(
                [
                    {
                        "민감도 분석": scenario_name,
                        "세목": "총계",
                        "끝수 처리 전 산출세액": total_before,
                        "끝수 처리 후 재계산액": total_after,
                        "끝수 처리 차이": total_before - total_after,
                        "계산상태": "official_source_calculated",
                        "법적 근거": "세목별 Tax Rule Master 산식 합계",
                        "source_url": "",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    summary = {
        "민감도 분석": scenario_name,
        "토지 개별공시지가 변동률": land_change,
        "건축물 시가표준액 변동률": building_change,
        "끝수 처리 전 합계": total_before,
        "끝수 처리 후 합계": total_after,
        "기준 대비 증감액": Decimal("0"),
        "기준 대비 증감률": Decimal("0"),
    }
    return summary, details


def build_sensitivity_scenarios(
    case: CoreAssetTaxCaseData,
    custom_land_change_pct: int = 0,
    custom_building_change_pct: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    definitions = [
        ("기준", 0, 0),
        ("공시가격·시가표준액 5% 상승", 5, 5),
        ("공시가격·시가표준액 10% 상승", 10, 10),
        ("사용자 설정", custom_land_change_pct, custom_building_change_pct),
    ]
    summaries: list[dict] = []
    details: list[pd.DataFrame] = []
    for name, land_change, building_change in definitions:
        summary, detail = calculate_sensitivity_scenario(
            case,
            name,
            land_change,
            building_change,
        )
        summaries.append(summary)
        details.append(detail)

    base_total = summaries[0]["끝수 처리 후 합계"]
    for summary in summaries:
        delta = summary["끝수 처리 후 합계"] - base_total
        summary["기준 대비 증감액"] = delta
        summary["기준 대비 증감률"] = (
            delta / base_total * Decimal("100")
            if base_total != 0
            else Decimal("0")
        )
    return (
        pd.DataFrame(summaries, columns=SCENARIO_SUMMARY_COLUMNS),
        pd.concat(details, ignore_index=True),
    )


def _reconciliation_row(case: CoreAssetTaxCaseData, metric: str) -> pd.Series | None:
    rows = case.reconciliation[
        case.reconciliation["metric"].fillna("").astype(str).eq(metric)
    ]
    return None if rows.empty else rows.iloc[0]


def build_tax_issue_matrix(case: CoreAssetTaxCaseData) -> pd.DataFrame:
    taxpayer = case.taxpayers.iloc[0]
    notice = _reconciliation_row(case, "holding_tax_notice_reconciliation")
    area = _reconciliation_row(case, "parcel_area_difference_tax_sensitivity")
    actual_notice_missing = str(
        taxpayer.get("actual_notice_classification", "unverified")
    ) == "unverified"
    notice_open = notice is None or pd.isna(notice.get("disclosed_or_verified_value"))
    ownership_open = str(
        taxpayer.get("assessment_date_ownership_verified", "")
    ).lower() not in {"true", "1", "verified", "yes"}
    fire_rows = case.calculations[
        case.calculations["tax_name"].eq("소방분 지역자원시설세")
    ]
    fire_amount = (
        _decimal(fire_rows.iloc[0]["calculated_tax"])
        if not fire_rows.empty
        else Decimal("0")
    )
    area_effect = _decimal(area.get("calculated_value")) if area is not None else Decimal("0")

    issues = [
        {
            "priority": "P0",
            "issue_code": "notice_classification_unverified",
            "tax_issue": "실제 재산세 고지 과세구분 미확인",
            "current_status": "Open" if actual_notice_missing else "Resolved",
            "evidence_status": str(
                taxpayer.get("actual_notice_classification", "unverified")
            ),
            "potential_tax_effect": "분리과세 실제 적용 및 종부세 제외 확인",
            "quantitative_sensitivity": "실제 과세구분 확인 전 정량화 불가",
            "required_document": "분리과세 코드가 표시된 과세내역서",
            "request_reason": "실제 고지 과세구분과 분리과세 코드 확인",
        },
        {
            "priority": "P0",
            "issue_code": "notice_amount_unreconciled",
            "tax_issue": "실제 고지세액 미대사",
            "current_status": "Open" if notice_open else "Resolved",
            "evidence_status": "not_reconciled" if notice_open else "reconciled",
            "potential_tax_effect": "모델 재계산액과 실제 세액 차이",
            "quantitative_sensitivity": (
                "끝수 처리 후 재계산액 "
                f"{CORE_RECALCULATION_AFTER_END_DIGIT_TREATMENT:,}원, "
                "실제 고지세액 미확인"
            ),
            "required_document": "2026 재산세·지역자원시설세 고지서",
            "request_reason": "세목별 산식 재계산액과 실제 고지세액 대사",
        },
        {
            "priority": "P0",
            "issue_code": "assessment_date_trust_status_unverified",
            "tax_issue": "6월 1일 현재 등기·신탁상태 미확인",
            "current_status": "Open" if ownership_open else "Resolved",
            "evidence_status": str(
                taxpayer.get("assessment_date_ownership_basis_status", "unverified")
            ),
            "potential_tax_effect": "재산세 납세의무자 판정",
            "quantitative_sensitivity": "소유·신탁 원문 대사 전 정량화 불가",
            "required_document": "2026년 6월 1일 현재 등기부등본·신탁원부",
            "request_reason": "수탁자·위탁자와 과세기준일 현재 소유관계 확인",
        },
        {
            "priority": "P1",
            "issue_code": "parcel_area_difference_5_3",
            "tax_issue": "토지면적 5.3㎡ 차이",
            "current_status": "Open",
            "evidence_status": "not_reconciled",
            "potential_tax_effect": "과세면적 차이에 따른 토지 관련 세액 차이",
            "quantitative_sensitivity": f"끝수 처리 적용 전 약 {area_effect:,}원",
            "required_document": "최신 토지대장·지적도 및 부속지번 자료",
            "request_reason": "서린동 91 포함 여부와 현행 과세면적 확인",
        },
        {
            "priority": "P1",
            "issue_code": "fire_notice_code_unreconciled",
            "tax_issue": "소방분 실제 위험유형 코드 미대사",
            "current_status": "Open",
            "evidence_status": "statutory_basis_verified_notice_code_open",
            "potential_tax_effect": "소방분 300% 배율의 실제 고지 적용 확인",
            "quantitative_sensitivity": f"300% 산식 재계산액 {fire_amount:,}원",
            "required_document": "실제 지역자원시설세 고지내역·과세코드",
            "request_reason": "과세관청의 실제 위험유형 코드와 배율 대사",
        },
        {
            "priority": "P1",
            "issue_code": "notice_adjustments_unmodeled",
            "tax_issue": "감면·세부담상한·지방자치단체 조정 미반영",
            "current_status": "Open" if notice_open else "Resolved",
            "evidence_status": "not_reflected",
            "potential_tax_effect": "실제 고지세액과 산식 재계산액의 차이",
            "quantitative_sensitivity": "실제 과세내역 확인 전 정량화 불가",
            "required_document": "과세내역서 및 감면·세부담상한 적용자료",
            "request_reason": "감면·세부담상한과 지방자치단체 조정 내역 확인",
        },
    ]
    for issue in issues:
        issue["responsible_reviewer"] = "Tax 검토자"
        issue["memo_included"] = True
        issue["resolution_status"] = issue["current_status"]
    return pd.DataFrame(issues, columns=ISSUE_MATRIX_COLUMNS)


def build_case_request_list(
    issue_matrix: pd.DataFrame,
    source_requests: pd.DataFrame,
) -> pd.DataFrame:
    source_aliases = {
        "notice_classification_unverified": {"tax_notice"},
        "notice_amount_unreconciled": {"tax_notice"},
        "assessment_date_trust_status_unverified": {
            "trust_registry_reconciliation",
            "taxpayer_verification",
        },
        "parcel_area_difference_5_3": {"parcel_area_reconciliation"},
        "fire_notice_code_unreconciled": {"tax_notice"},
        "notice_adjustments_unmodeled": {"tax_notice"},
    }
    rows: list[dict] = []
    for issue in issue_matrix.to_dict("records"):
        aliases = source_aliases[issue["issue_code"]]
        linked = source_requests[
            source_requests["issue_code"].fillna("").astype(str).isin(aliases)
        ]
        linked_ids = ", ".join(linked["request_id"].dropna().astype(str).unique())
        rows.append(
            {
                "priority": issue["priority"],
                "issue_code": issue["issue_code"],
                "tax_issue": issue["tax_issue"],
                "required_document": issue["required_document"],
                "request_reason": issue["request_reason"],
                "linked_request_id": linked_ids,
                "reviewer_status": "open"
                if issue["resolution_status"] == "Open"
                else "reviewed",
                "resolution_status": issue["resolution_status"],
            }
        )
    return pd.DataFrame(rows)


def build_case_kpis(
    case: CoreAssetTaxCaseData,
    issue_matrix: pd.DataFrame,
) -> dict[str, int | float | str]:
    coverage = summarize_coverage(
        case.assets,
        case.parcels,
        case.buildings,
        case.taxpayers,
        case.calculations,
    )
    evidence_checks = [
        coverage["verified_address_count"] > 0,
        coverage["verified_pnu_count"] > 0,
        coverage["verified_land_price_count"] > 0,
        coverage["verified_building_value_count"] > 0,
        coverage["verified_taxpayer_count"] > 0,
    ]
    open_rows = issue_matrix[issue_matrix["resolution_status"].eq("Open")]
    return {
        "p0_open": int(open_rows["priority"].eq("P0").sum()),
        "p1_open": int(open_rows["priority"].eq("P1").sum()),
        "completed_tax_items": int(coverage["completed_calculation_rows"]),
        "unreconciled_items": int(len(open_rows)),
        "notice_coverage": "0%",
        "evidence_coverage": f"{sum(evidence_checks)}/{len(evidence_checks)} ({sum(evidence_checks) / len(evidence_checks):.0%})",
    }
