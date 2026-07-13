from __future__ import annotations

import pandas as pd

from data_source_policy import get_source_policy, normalize_source_type


COMPANY_LEVEL_ASSET_NAME = "회사 전체 추정"
COMPANY_LEVEL_REGION = "회사 전체"


def _to_number(value):
    return pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]


def safe_ratio(numerator, denominator):
    numerator = _to_number(numerator)
    denominator = _to_number(denominator)
    if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
        return pd.NA
    return numerator / denominator


def _ratio_to_fraction(value, default: float) -> float:
    ratio = _to_number(value)
    if pd.isna(ratio):
        ratio = default
    ratio = float(ratio)
    return ratio / 100 if ratio > 1 else ratio


def calculate_estimated_tax_base(official_price, fair_market_value_ratio):
    official_price = _to_number(official_price)
    if pd.isna(official_price) or official_price < 0:
        return pd.NA
    return official_price * _ratio_to_fraction(fair_market_value_ratio, 0.70)


def calculate_estimated_holding_tax(tax_base, effective_holding_tax_rate):
    tax_base = _to_number(tax_base)
    if pd.isna(tax_base) or tax_base < 0:
        return pd.NA
    return tax_base * _ratio_to_fraction(effective_holding_tax_rate, 0.011)


def classify_holding_tax_burden(metric, peer_distribution, source_type: str | None = None) -> str:
    value = _to_number(metric)
    if pd.isna(value):
        return "데이터 부족"
    canonical = normalize_source_type(source_type)
    if canonical == "data_insufficient":
        return "데이터 부족"

    distribution = pd.to_numeric(pd.Series(peer_distribution), errors="coerce").dropna()
    if distribution.empty:
        if value >= 0.35:
            return "높음"
        if value >= 0.20:
            return "주의"
        return "검토 필요" if canonical in {"peer_snapshot_estimate", "sample_estimate"} else "정상"

    q75 = distribution.quantile(0.75)
    q50 = distribution.quantile(0.50)
    if pd.notna(q75) and value >= q75:
        return "높음"
    if pd.notna(q50) and value >= q50:
        return "주의"
    return "검토 필요" if canonical in {"peer_snapshot_estimate", "sample_estimate"} else "정상"


def _latest_peer_row(company_name: str, peer_snapshot: pd.DataFrame | None) -> pd.Series:
    if peer_snapshot is None or peer_snapshot.empty or "company_name" not in peer_snapshot.columns:
        return pd.Series(dtype="object")
    rows = peer_snapshot[peer_snapshot["company_name"].astype(str).str.strip() == str(company_name).strip()]
    if rows.empty:
        return pd.Series(dtype="object")
    sort_cols = [col for col in ["year", "period"] if col in rows.columns]
    return rows.sort_values(sort_cols).iloc[-1] if sort_cols else rows.iloc[-1]


def _peer_distribution(peer_snapshot: pd.DataFrame | None) -> pd.Series:
    if peer_snapshot is None or peer_snapshot.empty:
        return pd.Series(dtype="float64")
    holding_tax = pd.to_numeric(peer_snapshot.get("estimated_holding_tax", pd.Series(dtype="float64")), errors="coerce")
    ffo = pd.to_numeric(peer_snapshot.get("ffo_proxy", pd.Series(dtype="float64")), errors="coerce")
    return holding_tax / ffo.where(ffo.ne(0))


def _fallback_dataset_from_peer(company_name: str, peer_row: pd.Series) -> pd.DataFrame:
    if peer_row.empty:
        return pd.DataFrame(
            [
                {
                    "company_name": company_name,
                    "asset_name": COMPANY_LEVEL_ASSET_NAME,
                    "region": COMPANY_LEVEL_REGION,
                    "book_value": pd.NA,
                    "official_price": pd.NA,
                    "estimated_tax_base": pd.NA,
                    "estimated_holding_tax": pd.NA,
                    "source_type": "data_insufficient",
                    "source_note": "Peer Snapshot과 Tax Snapshot이 부족하여 보유세 추정이 제한됩니다.",
                    "latest_year": pd.NA,
                }
            ]
        )
    official_price = peer_row.get("official_price_total", pd.NA)
    tax_base = calculate_estimated_tax_base(official_price, 70.0)
    estimated_tax = peer_row.get("estimated_holding_tax", pd.NA)
    if pd.isna(_to_number(estimated_tax)):
        estimated_tax = calculate_estimated_holding_tax(tax_base, 1.1)
    return pd.DataFrame(
        [
            {
                "company_name": company_name,
                "asset_name": COMPANY_LEVEL_ASSET_NAME,
                "region": COMPANY_LEVEL_REGION,
                "book_value": peer_row.get("investment_property", pd.NA),
                "official_price": official_price,
                "estimated_tax_base": tax_base,
                "estimated_holding_tax": estimated_tax,
                "source_type": "peer_snapshot_estimate",
                "source_note": "자산별 상세자료 부족으로 회사 전체 Snapshot 기반 추정",
                "latest_year": peer_row.get("year", pd.NA),
            }
        ]
    )


def _basis_label(row: pd.Series, official_price, estimated_tax, peer_row: pd.Series) -> str:
    source_type = normalize_source_type(row.get("source_type", ""))
    asset_name = str(row.get("asset_name", ""))
    if source_type == "data_insufficient":
        return "data_insufficient"
    if asset_name and asset_name != COMPANY_LEVEL_ASSET_NAME and pd.notna(_to_number(estimated_tax)):
        return "asset-level"
    if pd.notna(_to_number(row.get("estimated_holding_tax", pd.NA))):
        return "peer estimated_holding_tax"
    if pd.notna(_to_number(official_price)) or pd.notna(_to_number(peer_row.get("official_price_total", pd.NA))):
        return "official_price_total"
    if pd.notna(_to_number(row.get("book_value", pd.NA))) or pd.notna(_to_number(peer_row.get("investment_property", pd.NA))):
        return "investment_property"
    return "data_insufficient"


def build_holding_tax_bridge(
    company_name: str,
    tax_dataset: pd.DataFrame | None,
    peer_snapshot: pd.DataFrame | None,
    assumptions: dict | None = None,
) -> pd.DataFrame:
    assumptions = assumptions or {}
    peer_row = _latest_peer_row(company_name, peer_snapshot)
    data = tax_dataset.copy() if tax_dataset is not None and not tax_dataset.empty else _fallback_dataset_from_peer(company_name, peer_row)
    if data.empty:
        return pd.DataFrame()

    fair_market_value_ratio = assumptions.get("fair_market_value_ratio", assumptions.get("land_fmv_ratio_pct", 70.0))
    effective_tax_rate = assumptions.get("effective_holding_tax_rate", 1.1)
    peer_tax_to_ffo = _peer_distribution(peer_snapshot)
    rows = []

    for _, row in data.iterrows():
        source_type = row.get("source_type", "data_insufficient")
        policy = get_source_policy(source_type)
        official_price = _to_number(row.get("official_price", pd.NA))
        book_value = _to_number(row.get("book_value", pd.NA))
        if pd.isna(official_price) and pd.notna(_to_number(peer_row.get("official_price_total", pd.NA))):
            official_price = _to_number(peer_row.get("official_price_total", pd.NA))
        if pd.isna(book_value) and pd.notna(_to_number(peer_row.get("investment_property", pd.NA))):
            book_value = _to_number(peer_row.get("investment_property", pd.NA))

        tax_base = _to_number(row.get("estimated_tax_base", pd.NA))
        if pd.isna(tax_base):
            tax_base = calculate_estimated_tax_base(official_price, fair_market_value_ratio)

        estimated_tax = _to_number(row.get("estimated_holding_tax", pd.NA))
        if pd.isna(estimated_tax):
            estimated_tax = calculate_estimated_holding_tax(tax_base, effective_tax_rate)

        ffo = _to_number(peer_row.get("ffo_proxy", pd.NA))
        operating_revenue = _to_number(peer_row.get("operating_revenue", pd.NA))
        tax_to_ffo = safe_ratio(estimated_tax, ffo)
        tax_to_revenue = safe_ratio(estimated_tax, operating_revenue)
        peer_position = classify_holding_tax_burden(tax_to_ffo, peer_tax_to_ffo, source_type)
        basis = _basis_label(row, official_price, estimated_tax, peer_row)

        rows.append(
            {
                "회사명": company_name,
                "자산명": row.get("asset_name", COMPANY_LEVEL_ASSET_NAME),
                "지역": row.get("region", COMPANY_LEVEL_REGION),
                "source_type": source_type,
                "source_label": policy.korean_label,
                "신뢰수준": policy.reliability_level,
                "source_note": row.get("source_note", ""),
                "데이터 기준": basis,
                "공시가격 또는 장부가액(억원)": official_price / 100 if pd.notna(official_price) else book_value / 100 if pd.notna(book_value) else pd.NA,
                "과세표준 추정(억원)": tax_base / 100 if pd.notna(tax_base) else pd.NA,
                "적용 세율": _ratio_to_fraction(effective_tax_rate, 0.011),
                "추정 보유세(억원)": estimated_tax / 100 if pd.notna(estimated_tax) else pd.NA,
                "FFO proxy 대비": tax_to_ffo,
                "영업수익 대비": tax_to_revenue,
                "Peer 대비 위치": peer_position,
                "검토 필요 여부": "필요" if peer_position in {"높음", "주의", "검토 필요", "데이터 부족"} else "낮음",
                "한계": policy.memo_limitation_text,
            }
        )

    return pd.DataFrame(rows)
