import pandas as pd

from calculations_peer import load_peer_snapshot
from tax_data_loader import load_tax_snapshot


DETAILED_SAMPLE_STOCK_CODE = "395400"
DETAILED_SAMPLE_COMPANY = "SK리츠"


def _stock_code(company_profile: dict | None) -> str:
    if not company_profile:
        return ""
    return str(company_profile.get("stock_code", "")).zfill(6)


def _is_detailed_sample_company(company_name: str, company_profile: dict | None = None) -> bool:
    return (
        str(company_name).strip() == DETAILED_SAMPLE_COMPANY
        or _stock_code(company_profile) == DETAILED_SAMPLE_STOCK_CODE
    )


def _latest_peer_row(company_name: str, peer_snapshot: pd.DataFrame | None = None) -> pd.Series | None:
    peer = peer_snapshot if peer_snapshot is not None else load_peer_snapshot()
    if peer is None or peer.empty or "company_name" not in peer.columns:
        return None
    rows = peer[peer["company_name"].astype(str).str.strip() == str(company_name).strip()]
    if rows.empty:
        return None
    sort_cols = [col for col in ["year", "period"] if col in rows.columns]
    return rows.sort_values(sort_cols).iloc[-1] if sort_cols else rows.iloc[-1]


def _company_tax_rows(company_name: str, tax_snapshot: pd.DataFrame | None = None) -> pd.DataFrame:
    tax = tax_snapshot if tax_snapshot is not None else load_tax_snapshot()
    if tax is None or tax.empty or "company_name" not in tax.columns:
        return pd.DataFrame()
    return tax[tax["company_name"].astype(str).str.strip() == str(company_name).strip()].copy()


def has_asset_level_data(company_name: str, company_profile: dict | None = None) -> bool:
    return _is_detailed_sample_company(company_name, company_profile)


def has_tax_asset_data(company_name: str, company_profile: dict | None = None) -> bool:
    # Current public dataset has SK asset detail that can drive a tax proxy.
    # It is still not an official asset-by-asset tax bill.
    return _is_detailed_sample_company(company_name, company_profile)


def has_debt_maturity_data(company_name: str, company_profile: dict | None = None) -> bool:
    return _is_detailed_sample_company(company_name, company_profile)


def has_cap_rate_data(company_name: str, company_profile: dict | None = None) -> bool:
    return _is_detailed_sample_company(company_name, company_profile)


def has_tenant_data(company_name: str, company_profile: dict | None = None) -> bool:
    return _is_detailed_sample_company(company_name, company_profile)


def get_company_data_availability(
    company_name: str,
    company_profile: dict | None = None,
    peer_snapshot: pd.DataFrame | None = None,
    tax_snapshot: pd.DataFrame | None = None,
) -> dict:
    peer_row = _latest_peer_row(company_name, peer_snapshot)
    tax_rows = _company_tax_rows(company_name, tax_snapshot)
    peer_available = peer_row is not None
    tax_available = not tax_rows.empty
    detail_available = has_asset_level_data(company_name, company_profile)
    tax_asset_available = has_tax_asset_data(company_name, company_profile)

    source_types = []
    if tax_available and "source_type" in tax_rows.columns:
        source_types.extend(tax_rows["source_type"].dropna().astype(str).unique().tolist())
    if peer_available:
        source_types.append(str(peer_row.get("source_type", "sample_snapshot")))
    source_type = ", ".join(sorted(set(filter(None, source_types)))) or "data_missing"

    latest_year = pd.NA
    if tax_available and "latest_year" in tax_rows.columns:
        latest_year = pd.to_numeric(tax_rows["latest_year"], errors="coerce").dropna().max()
    if pd.isna(latest_year) and peer_available:
        latest_year = pd.to_numeric(pd.Series([peer_row.get("year", pd.NA)]), errors="coerce").iloc[0]

    if detail_available:
        scope_label = "자산별 상세 Snapshot + 회사 전체 Peer Snapshot"
        source_note = (
            "선택 회사의 자산·임차인·차입금 상세 sample을 사용할 수 있습니다. "
            "보유세는 공식 고지세액이 아니라 공시가격/기준시가 proxy 또는 Snapshot 기반 예비 분석입니다."
        )
    elif tax_available or peer_available:
        scope_label = "회사 전체 Snapshot / Peer 기반 예비 추정"
        source_note = (
            "자산별 상세자료가 부족하여 회사 전체 Snapshot 기반 추정값을 사용합니다. "
            "다른 회사의 자산 상세자료는 재사용하지 않습니다."
        )
    else:
        scope_label = "데이터 부족"
        source_note = "회사별 Peer Snapshot과 Tax Snapshot이 부족하여 일부 지표 산출이 제한됩니다."

    return {
        "company_name": company_name,
        "stock_code": _stock_code(company_profile),
        "company_level_financials_available": bool(peer_available),
        "peer_snapshot_available": bool(peer_available),
        "tax_snapshot_available": bool(tax_available),
        "asset_level_tax_available": bool(tax_asset_available),
        "tenant_detail_available": bool(has_tenant_data(company_name, company_profile)),
        "debt_maturity_detail_available": bool(has_debt_maturity_data(company_name, company_profile)),
        "cap_rate_detail_available": bool(has_cap_rate_data(company_name, company_profile)),
        "nav_detail_available": bool(peer_available),
        "asset_level_real_estate_available": bool(detail_available),
        "latest_year": int(latest_year) if pd.notna(latest_year) else None,
        "source_type": source_type,
        "source_note": source_note,
        "scope_label": scope_label,
    }


def get_data_scope_label(company_name: str, company_profile: dict | None = None) -> str:
    return get_company_data_availability(company_name, company_profile).get("scope_label", "데이터 부족")
