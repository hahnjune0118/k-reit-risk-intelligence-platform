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
        required = ["company_name", "asset_name", "source_type", "source_note", "official_price", "estimated_holding_tax"]
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
    }
