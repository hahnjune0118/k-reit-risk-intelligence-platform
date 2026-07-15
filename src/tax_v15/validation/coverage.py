from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from ..loaders import V15DataBundle
from ..schemas import CSV_SCHEMAS


VERIFIED_STATUSES = {"verified_notice", "official_source_calculated"}


def _percent(numerator: int, denominator: int) -> str:
    return f"{(numerator / denominator * 100):.1f}%" if denominator else "0.0%"


def _has_text(value) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return bool(str(value).strip())


def build_coverage_manifest(bundle: V15DataBundle) -> pd.DataFrame:
    rows: list[dict] = []
    for _, reit in bundle.reits.iterrows():
        reit_name = str(reit.get("reit_name", ""))
        stock_code = str(reit.get("stock_code", ""))
        assets = bundle.assets[bundle.assets["stock_code"].fillna("").astype(str).eq(stock_code)]
        asset_ids = set(assets["asset_id"].dropna().astype(str))
        parcels = bundle.parcels[bundle.parcels["asset_id"].fillna("").astype(str).isin(asset_ids)]
        buildings = bundle.buildings[bundle.buildings["asset_id"].fillna("").astype(str).isin(asset_ids)]
        taxpayers = bundle.taxpayers[bundle.taxpayers["asset_id"].fillna("").astype(str).isin(asset_ids)]
        calculations = bundle.calculations[
            bundle.calculations["reit_name"].fillna("").astype(str).eq(reit_name)
        ]
        documents = bundle.documents[bundle.documents["reit_name"].fillna("").astype(str).eq(reit_name)]

        address_count = int(assets["address_confidence"].fillna("").astype(str).isin(["verified", "high"]).sum())
        pnu_count = int(parcels["pnu"].fillna("").astype(str).str.fullmatch(r"\d{19}").sum())
        land_price_count = int(pd.to_numeric(parcels["individual_land_price_per_m2"], errors="coerce").notna().sum())
        building_value_count = int(pd.to_numeric(buildings["building_standard_value"], errors="coerce").notna().sum())
        taxpayer_count = int(taxpayers["validation_status"].fillna("").astype(str).isin(VERIFIED_STATUSES).sum())
        numeric_tax = pd.to_numeric(calculations["calculated_tax"], errors="coerce")
        completed_count = int(
            (
                calculations["calculation_status"].fillna("").astype(str).isin(VERIFIED_STATUSES)
                & numeric_tax.notna()
                & calculations["tax_name"].ne("토지 시가표준액")
            ).sum()
        )

        blockers: list[str] = []
        actions: list[str] = []
        if assets.empty:
            blockers.append("공식자료 기반 Asset Registry 미구축")
            actions.append("공식 홈페이지·DART 투자보고서에서 자산 목록 확인")
        if len(assets) and pnu_count == 0:
            blockers.append("PNU·필지 목록 미확인")
            actions.append("토지대장·지적도·PNU 매핑 확보")
        if len(parcels) and land_price_count < len(parcels):
            blockers.append("일부 개별공시지가 미확인")
            actions.append("기준연도 개별공시지가 공식 조회")
        if len(buildings) and building_value_count < len(buildings):
            blockers.append("건축물 시가표준액 미확인")
            actions.append("건축물 시가표준액 산출내역 확보")
        if len(assets) and taxpayer_count < len(assets):
            blockers.append("법적 납세의무자·분리과세 요건 미검증")
            actions.append("등기·신탁·목적사업 사용·과세내역서 확인")
        if completed_count:
            calculation_status = "official_source_calculated"
        elif len(assets):
            calculation_status = "official_partial"
        else:
            calculation_status = "data_insufficient"

        pdf_checked = documents[
            documents["document_type"].eq("official_pdf")
            & documents["extraction_status"].isin(
                ["extracted_text", "extracted_with_ocr", "extracted_no_keyword_hit"]
            )
        ]
        dart_checked = documents[
            documents["document_type"].eq("dart_filings")
            & documents["extraction_status"].ne("manual_review_required")
        ]
        rows.append({
            "reit_name": reit_name,
            "stock_code": stock_code,
            "official_website_found": _has_text(reit.get("official_website", "")),
            "ir_documents_checked": not pdf_checked.empty,
            "dart_documents_checked": not dart_checked.empty,
            "asset_count_identified": len(assets),
            "address_count_verified": address_count,
            "parcel_count_verified": pnu_count,
            "land_price_coverage": _percent(land_price_count, len(parcels)),
            "building_value_coverage": _percent(building_value_count, len(buildings)),
            "taxpayer_coverage": _percent(taxpayer_count, len(assets)),
            "tax_calculation_status": calculation_status,
            "blocking_reason": "; ".join(dict.fromkeys(blockers)) or "추가 차단사항 없음",
            "next_action": "; ".join(dict.fromkeys(actions)) or "고지서 대사 및 reviewer sign-off",
        })
    return pd.DataFrame(rows, columns=CSV_SCHEMAS["coverage_manifest.csv"])


def _duplicate_count(frame: pd.DataFrame, keys: list[str]) -> int:
    if frame.empty or any(key not in frame.columns for key in keys):
        return 0
    usable = frame[keys].fillna("").astype(str)
    return int(usable.duplicated(keys, keep=False).sum())


def _markdown_table(frame: pd.DataFrame) -> list[str]:
    if frame.empty:
        return ["데이터 없음"]
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for _, row in frame.iterrows():
        values = [str(row.get(column, "")).replace("|", "\\|").replace("\n", " ") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def build_coverage_report(bundle: V15DataBundle, coverage: pd.DataFrame) -> str:
    calculations = bundle.calculations
    status_counts = calculations["calculation_status"].fillna("미입력").value_counts().to_dict()
    data_sets = [
        ("reit_master.csv", bundle.reits, ["stock_code"], ["stock_code"]),
        ("asset_master.csv", bundle.assets, ["asset_id"], ["asset_id"]),
        ("parcel_master.csv", bundle.parcels, ["parcel_id"], ["parcel_id"]),
        ("building_master.csv", bundle.buildings, ["building_id"], ["building_id"]),
        (
            "taxpayer_structure.csv",
            bundle.taxpayers,
            ["taxpayer_id", "asset_id"],
            ["taxpayer_id", "asset_id"],
        ),
        (
            "tax_calculation_detail.csv",
            bundle.calculations,
            ["tax_year", "reit_name", "tax_name"],
            ["tax_year", "reit_name", "taxpayer_id", "asset_id", "parcel_id", "building_id", "tax_name"],
        ),
    ]
    quality_rows = []
    for name, frame, required_keys, unique_keys in data_sets:
        missing_keys = 0
        if not frame.empty:
            required = frame[required_keys]
            missing_keys = int(
                (required.isna() | required.fillna("").astype(str).apply(lambda column: column.str.strip().eq("")))
                .any(axis=1)
                .sum()
            )
        quality_rows.append(
            (name, len(frame), ", ".join(unique_keys), missing_keys, _duplicate_count(frame, unique_keys))
        )

    pnu_count = int(bundle.parcels["pnu"].fillna("").astype(str).str.fullmatch(r"\d{19}").sum())
    land_price_count = int(
        pd.to_numeric(bundle.parcels["individual_land_price_per_m2"], errors="coerce").notna().sum()
    )
    building_value_count = int(
        pd.to_numeric(bundle.buildings["building_standard_value"], errors="coerce").notna().sum()
    )
    lines = [
        "# v15 Coverage Report",
        "",
        f"생성시각(UTC): {datetime.now(timezone.utc).isoformat()}",
        "",
        "## 전체 요약",
        "",
        f"- 공식 상장리츠 목록: {len(bundle.reits)}개",
        f"- 공식자료에서 식별한 자산: {len(bundle.assets)}건",
        f"- 19자리 PNU 검증: {pnu_count}건",
        f"- 공식 개별공시지가 확인: {land_price_count}건",
        f"- 공식 건축물 시가표준액 확인: {building_value_count}건",
        f"- 계산상태 분포: {status_counts}",
        "",
        "> 현재 Coverage는 전체 상장리츠의 자산·필지·세액 검증 완료를 의미하지 않습니다. 공식 근거가 없는 값은 계산에서 차단됩니다.",
        "",
        "## 리츠별 Coverage",
        "",
        *_markdown_table(coverage),
        "",
        "## 데이터 품질 점검",
        "",
        "| 파일 | 행 수 | 기대 Grain Key | Key 누락 행 | 중복 Key 행 |",
        "|---|---:|---|---:|---:|",
    ]
    lines.extend(
        f"| {name} | {row_count} | {keys} | {missing} | {duplicates} |"
        for name, row_count, keys, missing, duplicates in quality_rows
    )
    lines.extend([
        "",
        "## 주요 차단사항",
        "",
        "- 법적 소유자·신탁관계와 과세기준일 현재 납세의무자 확인",
        "- 자산별 전체 PNU·필지면적·소유지분 확인",
        "- 기준연도 개별공시지가와 건축물 시가표준액 확인",
        "- 도시지역분 조례, 소방분 위험유형 및 가중배율 확인",
        "- 납세의무자별 전국 합산 종부세 과세자료와 재산세 공제액 확인",
        "- 실제 고지서·과세내역서 대사",
        "",
    ])
    return "\n".join(lines)
