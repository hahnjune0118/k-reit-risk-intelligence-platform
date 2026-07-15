from pathlib import Path

import pandas as pd
import streamlit as st

from calculations_holding_tax_bridge import calculate_estimated_holding_tax, calculate_estimated_tax_base
from config import DATA_DIR
from data_source_policy import contains_estimate_source, get_source_policy, normalize_source_type


TAX_SNAPSHOT_PATH = DATA_DIR / "reit_tax_snapshot.csv"
COMPANY_LEVEL_FALLBACK_ASSET_NAME = "회사 전체 추정"
COMPANY_LEVEL_FALLBACK_REGION = "회사 전체"
COMPANY_LEVEL_FALLBACK_NOTE = "자산별 상세자료 부족으로 회사 전체 Snapshot 기반 추정"
DATA_MISSING_NOTE = "Peer Snapshot 데이터가 부족하여 보유세 추정이 제한됨"
NUMERIC_TAX_COLUMNS = [
    "book_value",
    "official_price",
    "estimated_tax_base",
    "estimated_holding_tax",
    "official_price_growth_5y",
    "holding_tax_to_ffo",
    "fair_market_value_ratio",
    "effective_holding_tax_rate",
    "latest_year",
]


def _read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data
def load_tax_snapshot(path: str | Path = TAX_SNAPSHOT_PATH) -> pd.DataFrame:
    df = _read_csv_if_exists(Path(path))
    if df.empty:
        return df
    for col in NUMERIC_TAX_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in [
        "company_name", "stock_code", "dart_corp_code", "asset_name", "region", "asset_type",
        "calculation_model", "formula_version", "tax_scope", "tax_component_status",
        "legal_owner_status", "taxpayer_status", "tax_pass_through_status", "pnu",
        "source_type", "source_name", "source_date", "source_note",
    ]:
        if col not in df.columns:
            df[col] = ""
    return df


def get_company_tax_data(company_name: str, tax_snapshot: pd.DataFrame | None = None) -> pd.DataFrame:
    snapshot = tax_snapshot if tax_snapshot is not None else load_tax_snapshot()
    if snapshot is None or snapshot.empty:
        return pd.DataFrame()
    return snapshot[snapshot["company_name"].astype(str).str.strip() == str(company_name).strip()].copy()


def _peer_row(company_name: str, peer_snapshot: pd.DataFrame | None) -> pd.Series | None:
    if peer_snapshot is None or peer_snapshot.empty or "company_name" not in peer_snapshot.columns:
        return None
    matches = peer_snapshot[peer_snapshot["company_name"].astype(str).str.strip() == str(company_name).strip()]
    if matches.empty:
        return None
    sort_cols = [col for col in ["year", "period"] if col in matches.columns]
    return matches.sort_values(sort_cols).iloc[-1] if sort_cols else matches.iloc[-1]


def _num(value):
    return pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]


def estimate_company_holding_tax_from_peer_snapshot(
    company_name: str,
    peer_snapshot: pd.DataFrame | None,
    company_profile: dict | None = None,
) -> pd.DataFrame:
    profile = company_profile or {}
    row = _peer_row(company_name, peer_snapshot)
    if row is None:
        return pd.DataFrame(
            [
                {
                    "company_name": company_name,
                    "stock_code": profile.get("stock_code", ""),
                    "dart_corp_code": profile.get("dart_corp_code", ""),
                    "asset_name": COMPANY_LEVEL_FALLBACK_ASSET_NAME,
                    "region": COMPANY_LEVEL_FALLBACK_REGION,
                    "asset_type": profile.get("main_asset_type", ""),
                    "book_value": pd.NA,
                    "official_price": pd.NA,
                    "estimated_tax_base": pd.NA,
                    "estimated_holding_tax": pd.NA,
                    "official_price_growth_5y": pd.NA,
                    "holding_tax_to_ffo": pd.NA,
                    "calculation_model": "data_insufficient",
                    "formula_version": "holding_tax_screening_v14_1",
                    "tax_scope": "data_insufficient",
                    "tax_component_status": "data_insufficient",
                    "legal_owner_status": "data_insufficient",
                    "taxpayer_status": "data_insufficient",
                    "tax_pass_through_status": "data_insufficient",
                    "source_type": "data_insufficient",
                    "source_note": DATA_MISSING_NOTE,
                    "latest_year": pd.NA,
                }
            ]
        )

    investment_property = _num(row.get("investment_property", pd.NA))
    official_price = _num(row.get("official_price_total", pd.NA))
    estimated_tax = _num(row.get("estimated_holding_tax", pd.NA))
    source_type = "peer_snapshot_estimate"
    source_note = COMPANY_LEVEL_FALLBACK_NOTE

    if str(profile.get("main_region", "")).strip().lower() == "overseas":
        return pd.DataFrame(
            [
                {
                    "company_name": company_name,
                    "stock_code": str(profile.get("stock_code", "")),
                    "dart_corp_code": profile.get("dart_corp_code", ""),
                    "asset_name": COMPANY_LEVEL_FALLBACK_ASSET_NAME,
                    "region": "Overseas",
                    "asset_type": profile.get("main_asset_type", ""),
                    "book_value": investment_property,
                    "official_price": pd.NA,
                    "estimated_tax_base": pd.NA,
                    "estimated_holding_tax": pd.NA,
                    "official_price_growth_5y": pd.NA,
                    "holding_tax_to_ffo": pd.NA,
                    "calculation_model": "data_insufficient",
                    "formula_version": "holding_tax_screening_v14_1",
                    "tax_scope": "overseas_asset_not_modeled",
                    "tax_component_status": "data_insufficient",
                    "legal_owner_status": "data_insufficient",
                    "taxpayer_status": "data_insufficient",
                    "tax_pass_through_status": "data_insufficient",
                    "source_type": "data_insufficient",
                    "source_note": "해외자산 중심 회사에는 국내 공시가격·보유세 산식을 적용하지 않습니다.",
                    "latest_year": row.get("year", pd.NA),
                }
            ]
        )

    if pd.isna(estimated_tax) and pd.notna(official_price):
        tax_base = calculate_estimated_tax_base(official_price, 0.70)
        estimated_tax = calculate_estimated_holding_tax(tax_base, 0.011)
        source_type = "official_price_estimate"
        source_note = "보유세 직접 추정값이 부족하여 공시가격×70%×1.1% screening proxy 적용"
    if pd.isna(official_price) and pd.notna(investment_property):
        official_price = investment_property * 0.55
        if pd.isna(estimated_tax):
            tax_base = calculate_estimated_tax_base(official_price, 0.70)
            estimated_tax = calculate_estimated_holding_tax(tax_base, 0.011)
        source_type = "investment_property_estimate"
        source_note = "공시가격과 자산별 상세자료가 부족하여 투자부동산 장부금액 기반 proxy 적용"

    ffo = _num(row.get("ffo_proxy", pd.NA))
    tax_base = calculate_estimated_tax_base(official_price, 0.70)
    effective_rate = estimated_tax / tax_base if pd.notna(estimated_tax) and pd.notna(tax_base) and tax_base else pd.NA
    return pd.DataFrame(
        [
            {
                "company_name": company_name,
                "stock_code": str(profile.get("stock_code", "")),
                "dart_corp_code": profile.get("dart_corp_code", ""),
                "asset_name": COMPANY_LEVEL_FALLBACK_ASSET_NAME,
                "region": COMPANY_LEVEL_FALLBACK_REGION,
                "asset_type": profile.get("main_asset_type", ""),
                "book_value": investment_property,
                "official_price": official_price,
                "estimated_tax_base": tax_base,
                "estimated_holding_tax": estimated_tax,
                "official_price_growth_5y": pd.NA,
                "holding_tax_to_ffo": estimated_tax / ffo if pd.notna(estimated_tax) and pd.notna(ffo) and ffo else pd.NA,
                "calculation_model": "effective-rate estimate" if pd.notna(estimated_tax) else "data_insufficient",
                "fair_market_value_ratio": 0.70,
                "effective_holding_tax_rate": effective_rate,
                "formula_version": "holding_tax_screening_v14_1",
                "tax_scope": "company_level_screening_total",
                "tax_component_status": "data_insufficient",
                "legal_owner_status": "data_insufficient",
                "taxpayer_status": "data_insufficient",
                "tax_pass_through_status": "data_insufficient",
                "source_type": source_type,
                "source_note": source_note,
                "latest_year": row.get("year", pd.NA),
            }
        ]
    )


def build_company_tax_dataset(
    company_name: str,
    peer_snapshot: pd.DataFrame | None = None,
    company_profile: dict | None = None,
    tax_snapshot: pd.DataFrame | None = None,
) -> pd.DataFrame:
    company_tax = get_company_tax_data(company_name, tax_snapshot)
    if company_tax.empty:
        company_tax = estimate_company_holding_tax_from_peer_snapshot(company_name, peer_snapshot, company_profile)
    if company_tax.empty:
        return company_tax

    company_tax = company_tax.copy()
    company_tax["company_name"] = company_name
    defaults = {
        "source_type": "data_insufficient",
        "source_name": "",
        "source_date": "",
        "source_note": "",
        "asset_name": COMPANY_LEVEL_FALLBACK_ASSET_NAME,
        "region": COMPANY_LEVEL_FALLBACK_REGION,
        "calculation_model": "data_insufficient",
        "formula_version": "holding_tax_screening_v14_1",
        "tax_scope": "data_insufficient",
        "tax_component_status": "data_insufficient",
        "legal_owner_status": "data_insufficient",
        "taxpayer_status": "data_insufficient",
        "tax_pass_through_status": "data_insufficient",
        "pnu": "",
    }
    for col, default in defaults.items():
        if col not in company_tax.columns:
            company_tax[col] = default
    fallback_mask = company_tax["asset_name"].astype(str).str.strip().eq(COMPANY_LEVEL_FALLBACK_ASSET_NAME)
    company_tax.loc[fallback_mask, "region"] = COMPANY_LEVEL_FALLBACK_REGION
    company_tax.loc[fallback_mask & company_tax["source_type"].astype(str).str.strip().eq(""), "source_type"] = "peer_snapshot_estimate"
    company_tax.loc[fallback_mask & company_tax["source_note"].astype(str).str.strip().eq(""), "source_note"] = COMPANY_LEVEL_FALLBACK_NOTE
    company_tax["source_type"] = company_tax["source_type"].apply(lambda value: normalize_source_type(value) if value == "data_missing" else value)
    for col in NUMERIC_TAX_COLUMNS:
        if col in company_tax.columns:
            company_tax[col] = pd.to_numeric(company_tax[col], errors="coerce")
    return company_tax


def get_tax_source_summary(company_name: str, company_tax_data: pd.DataFrame) -> dict:
    if company_tax_data is None or company_tax_data.empty:
        policy = get_source_policy("data_insufficient")
        return {
            "company_name": company_name,
            "latest_year": None,
            "source_type": "data_insufficient",
            "source_note": DATA_MISSING_NOTE,
            "scope_label": "데이터 부족",
            "is_estimated": False,
            "korean_label": policy.korean_label,
            "reliability_level": policy.reliability_level,
            "memo_limitation_text": policy.memo_limitation_text,
            "ui_warning_text": policy.ui_warning_text,
            "allowed_outputs": policy.allowed_outputs,
        }

    source_types = sorted(company_tax_data.get("source_type", pd.Series(dtype="object")).dropna().astype(str).unique())
    source_notes = sorted(company_tax_data.get("source_note", pd.Series(dtype="object")).dropna().astype(str).unique())
    latest_year = pd.NA
    if "latest_year" in company_tax_data.columns:
        years = pd.to_numeric(company_tax_data["latest_year"], errors="coerce").dropna()
        latest_year = years.max() if not years.empty else pd.NA

    asset_names = company_tax_data.get("asset_name", pd.Series(dtype="object")).astype(str).str.strip()
    fallback_assets = asset_names.eq(COMPANY_LEVEL_FALLBACK_ASSET_NAME)
    source_type_text = ", ".join(source_types) or "data_insufficient"
    policy = get_source_policy(source_type_text)
    is_estimated = fallback_assets.any() or contains_estimate_source(source_type_text)
    if policy.source_type == "data_insufficient":
        scope_label = "데이터 부족"
    elif fallback_assets.any():
        scope_label = "회사 전체 Snapshot 기반 추정"
    elif is_estimated:
        scope_label = "예비 추정"
    else:
        scope_label = "자산별 상세"

    return {
        "company_name": company_name,
        "latest_year": int(latest_year) if pd.notna(latest_year) else None,
        "source_type": source_type_text,
        "source_note": " / ".join(source_notes) or DATA_MISSING_NOTE,
        "scope_label": scope_label,
        "is_estimated": bool(is_estimated),
        "korean_label": policy.korean_label,
        "reliability_level": policy.reliability_level,
        "memo_limitation_text": policy.memo_limitation_text,
        "ui_warning_text": policy.ui_warning_text,
        "allowed_outputs": policy.allowed_outputs,
    }


def get_tax_source_status(company_name: str, company_tax_data: pd.DataFrame) -> str:
    summary = get_tax_source_summary(company_name, company_tax_data)
    year_text = f"{summary['latest_year']}년" if summary["latest_year"] else "연도 미확인"
    return (
        f"{company_name}: {year_text} / {summary['source_type']} / {summary['scope_label']} / "
        f"{summary['korean_label']} / {summary['source_note']}"
    )


def build_tax_history_from_company_tax_data(
    company_tax_data: pd.DataFrame,
    years_back: int = 5,
    default_latest_year: int = 2026,
) -> pd.DataFrame:
    if company_tax_data is None or company_tax_data.empty:
        return pd.DataFrame()

    rows = []
    for _, row in company_tax_data.iterrows():
        latest_year = int(row.get("latest_year", default_latest_year)) if pd.notna(row.get("latest_year", pd.NA)) else default_latest_year
        latest_official = row.get("official_price", pd.NA)
        latest_tax_base = row.get("estimated_tax_base", pd.NA)
        latest_tax = row.get("estimated_holding_tax", pd.NA)
        rows.append(
            {
                "asset_name": row.get("asset_name", COMPANY_LEVEL_FALLBACK_ASSET_NAME),
                "year": latest_year,
                "location": row.get("region", ""),
                "asset_type": row.get("asset_type", ""),
                "official_land_price_per_sqm_krw": pd.NA,
                "토지_시가표준액_백만원": latest_official,
                "건물_시가표준액_백만원": pd.NA,
                "토지_과세표준_백만원": latest_tax_base,
                "건물_과세표준_백만원": pd.NA,
                "재산세본세_백만원": pd.NA,
                "도시지역분_백만원": pd.NA,
                "지방교육세_백만원": pd.NA,
                "보유세_추정_백만원": latest_tax,
                "공시지가_전년대비_%": pd.NA,
                "보유세_전년대비_%": pd.NA,
                "보유세_5년누적증가_%": pd.NA,
                "official_price_growth_5y": row.get("official_price_growth_5y", pd.NA),
                "history_kind": "snapshot_single_period",
                "calculation_model": row.get("calculation_model", "data_insufficient"),
                "formula_version": row.get("formula_version", "holding_tax_screening_v14_1"),
                "tax_scope": row.get("tax_scope", "data_insufficient"),
                "tax_component_status": row.get("tax_component_status", "data_insufficient"),
                "legal_owner_status": row.get("legal_owner_status", "data_insufficient"),
                "taxpayer_status": row.get("taxpayer_status", "data_insufficient"),
                "tax_pass_through_status": row.get("tax_pass_through_status", "data_insufficient"),
                "official_price_source": row.get("source_type", ""),
                "source_type": row.get("source_type", ""),
                "source_name": row.get("source_name", ""),
                "source_date": row.get("source_date", ""),
                "source_note": row.get("source_note", ""),
                "book_value_mn_krw": row.get("book_value", pd.NA),
                "official_price_mn_krw": latest_official,
                "tax_base_mn_krw": latest_tax_base,
            }
        )
    history = pd.DataFrame(rows)
    if history.empty:
        return history
    history = history.sort_values(["asset_name", "year"])
    return history
