from __future__ import annotations

import pandas as pd

from tax_data_loader import COMPANY_LEVEL_FALLBACK_ASSET_NAME


def _num(value):
    return pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]


def _latest_peer_row(company_name: str, peer_snapshot: pd.DataFrame | None) -> pd.Series:
    if peer_snapshot is None or peer_snapshot.empty or "company_name" not in peer_snapshot.columns:
        return pd.Series(dtype="object")
    rows = peer_snapshot[peer_snapshot["company_name"].astype(str).str.strip() == str(company_name).strip()]
    if rows.empty:
        return pd.Series(dtype="object")
    sort_cols = [col for col in ["year", "period"] if col in rows.columns]
    return rows.sort_values(sort_cols).iloc[-1] if sort_cols else rows.iloc[-1]


def validate_tax_inputs(
    company_name: str,
    tax_dataset: pd.DataFrame | None,
    peer_snapshot: pd.DataFrame | None,
) -> dict:
    warnings: list[str] = []
    missing_fields: list[str] = []
    limitations: list[str] = []

    data = tax_dataset.copy() if tax_dataset is not None else pd.DataFrame()
    peer_row = _latest_peer_row(company_name, peer_snapshot)
    if data.empty:
        missing_fields.extend(["tax_snapshot", "estimated_holding_tax", "official_price"])
        limitations.append("Tax Snapshot 행이 없어 Peer Snapshot 또는 요청자료 확보가 필요합니다.")
    else:
        required = [
            "company_name", "asset_name", "source_type", "source_note", "calculation_model",
            "tax_scope", "official_price", "estimated_tax_base", "estimated_holding_tax",
        ]
        for col in required:
            if col not in data.columns or data[col].isna().all() or data[col].astype(str).str.strip().eq("").all():
                missing_fields.append(col)

    asset_level_tax_data_exists = bool(
        not data.empty
        and "asset_name" in data.columns
        and not data["asset_name"].astype(str).str.strip().eq(COMPANY_LEVEL_FALLBACK_ASSET_NAME).all()
    )
    fallback_used = bool(
        data.empty
        or (
            "asset_name" in data.columns
            and data["asset_name"].astype(str).str.strip().eq(COMPANY_LEVEL_FALLBACK_ASSET_NAME).any()
        )
    )

    ffo = _num(peer_row.get("ffo_proxy", pd.NA))
    official_price_total = _num(peer_row.get("official_price_total", pd.NA))
    investment_property = _num(peer_row.get("investment_property", pd.NA))
    estimated_tax = _num(peer_row.get("estimated_holding_tax", pd.NA))
    peer_year = _num(peer_row.get("year", pd.NA))

    ffo_exists = pd.notna(ffo) and ffo != 0
    official_price_exists = bool(
        (not data.empty and "official_price" in data.columns and pd.to_numeric(data["official_price"], errors="coerce").notna().any())
        or pd.notna(official_price_total)
    )

    if not ffo_exists:
        warnings.append("FFO가 없거나 0이어서 보유세/FFO 비율 산출이 제한됩니다.")
        limitations.append("FFO denominator가 부족하여 현금유출 부담 비율은 요청자료 확보 후 재계산해야 합니다.")
    if not official_price_exists:
        warnings.append("공시가격 또는 기준시가 입력값이 부족합니다.")
        limitations.append("공시가격 조회자료 또는 자산별 과세표준 자료가 필요합니다.")
    if fallback_used:
        warnings.append("자산별 상세자료 대신 회사 전체 추정 행을 사용했습니다.")
        limitations.append("회사 전체 Snapshot 기반 추정값은 자산별 고지세액 대사 전까지 예비 분석으로만 사용합니다.")

    rate_reconciled = True
    if not data.empty:
        for _, row in data.iterrows():
            tax_base = _num(row.get("estimated_tax_base", pd.NA))
            row_tax = _num(row.get("estimated_holding_tax", pd.NA))
            effective_rate = _num(row.get("effective_holding_tax_rate", pd.NA))
            if pd.notna(tax_base) and pd.notna(row_tax) and pd.notna(effective_rate):
                expected_tax = tax_base * (effective_rate / 100 if effective_rate > 1 else effective_rate)
                if abs(float(expected_tax) - float(row_tax)) > max(0.01, abs(float(row_tax)) * 1e-6):
                    rate_reconciled = False
                    warnings.append("추정 과세표준×실효세율과 추정 보유세가 일치하지 않습니다.")
                    limitations.append("세액·과세표준·실효세율의 수학적 reconciliation이 필요합니다.")
                    break

    latest_years = pd.to_numeric(data.get("latest_year", pd.Series(dtype="float64")), errors="coerce").dropna()
    period_aligned = bool(latest_years.empty or pd.isna(peer_year) or int(latest_years.max()) == int(peer_year))
    if not period_aligned:
        warnings.append("보유세 Snapshot 연도와 최신 재무제표 기준연도가 다릅니다.")
        limitations.append("보유세/FFO proxy 비율은 서로 다른 기준기간을 연결한 screening 비율입니다.")

    taxpayer_status = set(data.get("taxpayer_status", pd.Series(dtype="object")).fillna("").astype(str).str.strip())
    taxpayer_confirmed = bool(taxpayer_status and taxpayer_status.isdisjoint({"", "data_insufficient"}))
    if not taxpayer_confirmed:
        warnings.append("법적 소유자·납세의무자·실제 현금부담자가 확인되지 않았습니다.")
        limitations.append("등기·신탁·SPC 구조와 임대차상 세금 전가 조항을 확인해야 합니다.")

    component_status = set(data.get("tax_component_status", pd.Series(dtype="object")).fillna("").astype(str).str.strip())
    tax_components_complete = bool(component_status and component_status.isdisjoint({"", "data_insufficient"}))
    if not tax_components_complete:
        warnings.append("추정 보유세에 포함된 세목 범위가 확인되지 않았습니다.")
        limitations.append("재산세 외 종합부동산세·농어촌특별세·지역자원시설세 및 감면 적용 여부를 확인해야 합니다.")

    if pd.notna(estimated_tax) and ffo_exists and estimated_tax / ffo > 1:
        warnings.append("보유세/FFO 비율이 100%를 초과합니다. 단위와 연환산 기준을 확인해야 합니다.")
    if pd.notna(official_price_total) and pd.notna(investment_property) and investment_property:
        ratio = official_price_total / investment_property
        if ratio > 1.2 or ratio < 0.25:
            warnings.append("공시가격/투자부동산 장부금액 비율이 일반 범위를 벗어납니다. 단위와 원천자료를 확인해야 합니다.")

    validation_status = "검토 필요" if warnings or missing_fields else "정상"
    if len(missing_fields) >= 3 or not official_price_exists:
        validation_status = "자료 부족"

    return {
        "company_name": company_name,
        "validation_status": validation_status,
        "warnings": warnings,
        "missing_fields": sorted(set(missing_fields)),
        "fallback_used": fallback_used,
        "calculation_limitations": limitations,
        "asset_level_tax_data_exists": asset_level_tax_data_exists,
        "ffo_exists": bool(ffo_exists),
        "official_price_exists": bool(official_price_exists),
        "rate_reconciled": bool(rate_reconciled),
        "period_aligned": bool(period_aligned),
        "taxpayer_confirmed": bool(taxpayer_confirmed),
        "tax_components_complete": bool(tax_components_complete),
    }
