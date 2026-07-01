import xml.etree.ElementTree as ET

import pandas as pd
import requests
import streamlit as st

from formatting import _safe_float


def parse_official_price_upload(uploaded_file) -> tuple[pd.DataFrame, str]:
    """Parse user-uploaded official-price CSV.

    Expected flexible columns:
    - asset_name / 자산 / asset
    - year / 연도
    - official_land_price_per_sqm_krw / 개별공시지가_원_m2 / 공시지가
    - land_area_sqm / 토지면적
    - building_standard_value_mn_krw / 건물기준시가_백만원 / 건물시가표준액_백만원
    """
    if uploaded_file is None:
        return pd.DataFrame(), "업로드 파일 없음"
    last_error = None
    for enc in ["utf-8-sig", "cp949", "euc-kr", "utf-8"]:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding=enc)
            break
        except Exception as exc:
            df = None
            last_error = exc
    if df is None:
        return pd.DataFrame(), f"CSV 읽기 실패: {last_error}"

    rename_map = {}
    for col in df.columns:
        c = str(col).strip()
        lc = c.lower()
        if lc in ["asset", "asset_name", "자산", "자산명"]:
            rename_map[col] = "asset_name"
        elif lc in ["year", "연도", "yyyy"]:
            rename_map[col] = "year"
        elif lc in ["official_land_price_per_sqm_krw", "land_price_per_sqm", "개별공시지가", "개별공시지가_원_m2", "공시지가", "공시지가_원_m2"]:
            rename_map[col] = "official_land_price_per_sqm_krw"
        elif lc in ["land_area_sqm", "토지면적", "토지면적_sqm", "토지면적_m2"]:
            rename_map[col] = "land_area_sqm"
        elif lc in ["building_standard_value_mn_krw", "건물기준시가_백만원", "건물시가표준액_백만원", "building_tax_base_mn_krw"]:
            rename_map[col] = "building_standard_value_mn_krw"
        elif lc in ["source", "출처"]:
            rename_map[col] = "official_price_source"
    df = df.rename(columns=rename_map)
    required = {"asset_name", "year"}
    if not required.issubset(set(df.columns)):
        return pd.DataFrame(), "CSV에는 최소한 asset_name/자산명, year/연도 컬럼이 필요합니다."
    for c in ["year", "official_land_price_per_sqm_krw", "land_area_sqm", "building_standard_value_mn_krw"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "official_price_source" not in df.columns:
        df["official_price_source"] = "uploaded_official_price_csv"
    return df, "uploaded"


def _extract_rows_from_json_or_xml_payload(payload_text: str):
    """Best-effort parser for heterogeneous public API payloads."""
    import json
    rows = []
    try:
        payload = json.loads(payload_text)
        def walk(obj):
            if isinstance(obj, list):
                for item in obj:
                    walk(item)
            elif isinstance(obj, dict):
                # common OpenAPI shapes: response.body.items.item, body.items, row, data
                if any(k in obj for k in ["year", "stdrYear", "pblntfDe", "pblntfPclnd", "공시지가", "공시가격"]):
                    rows.append(obj)
                for v in obj.values():
                    if isinstance(v, (list, dict)):
                        walk(v)
        walk(payload)
        return rows
    except Exception:
        pass
    try:
        root = ET.fromstring(payload_text)
        for elem in root.iter():
            if len(list(elem)) > 0:
                d = {child.tag: child.text for child in list(elem)}
                if d:
                    rows.append(d)
    except Exception:
        pass
    return rows


def _pick_first_numeric(row: dict, candidates: list[str]):
    lowered = {str(k).lower(): v for k, v in row.items()}
    for key in candidates:
        if key in row:
            return _safe_float(row.get(key))
        if key.lower() in lowered:
            return _safe_float(lowered.get(key.lower()))
    return pd.NA


@st.cache_data(ttl=60 * 60)
def fetch_official_price_history_generic(api_key: str, endpoint: str, param_template: str, asset_name: str, address: str, pnu_or_code: str, start_year: int, end_year: int) -> tuple[pd.DataFrame, str]:
    """Fetch official price history using a user-configurable API endpoint and parameter template.

    This intentionally avoids hard-coding one endpoint because Korean official-price APIs differ by
    service approval and data type. The parameter template supports placeholders:
    {year}, {asset_name}, {address}, {pnu}, {service_key}.
    """
    if not api_key or not endpoint:
        return pd.DataFrame(), "API key 또는 endpoint가 입력되지 않았습니다."
    import json
    collected = []
    try:
        template = json.loads(param_template) if param_template else {}
    except Exception as exc:
        return pd.DataFrame(), f"파라미터 템플릿 JSON 오류: {exc}"
    for year in range(int(start_year), int(end_year) + 1):
        params = {}
        for k, v in template.items():
            if isinstance(v, str):
                params[k] = v.format(year=year, asset_name=asset_name, address=address, pnu=pnu_or_code, service_key=api_key)
            else:
                params[k] = v
        # Common service-key conventions. If user already specified serviceKey in template, this is harmlessly skipped.
        if "serviceKey" not in params and "service_key" not in params and "ServiceKey" not in params:
            params["serviceKey"] = api_key
        try:
            response = requests.get(endpoint, params=params, timeout=12)
            response.raise_for_status()
            rows = _extract_rows_from_json_or_xml_payload(response.text)
            for row in rows:
                land_price = _pick_first_numeric(row, [
                    "official_land_price_per_sqm_krw", "pblntfPclnd", "pblntf_pclnd", "공시지가", "개별공시지가",
                    "landPrice", "land_price", "price", "공시가격", "stdLandPrice"
                ])
                building_value = _pick_first_numeric(row, [
                    "building_standard_value_mn_krw", "건물기준시가_백만원", "건물시가표준액_백만원", "buildingValueMnKrw", "building_tax_base_mn_krw"
                ])
                if pd.notna(land_price) or pd.notna(building_value):
                    collected.append({
                        "asset_name": asset_name,
                        "year": year,
                        "official_land_price_per_sqm_krw": land_price,
                        "building_standard_value_mn_krw": building_value,
                        "official_price_source": "official_price_api",
                    })
        except Exception as exc:
            collected.append({
                "asset_name": asset_name,
                "year": year,
                "official_land_price_per_sqm_krw": pd.NA,
                "building_standard_value_mn_krw": pd.NA,
                "official_price_source": f"api_error: {exc}",
            })
    df = pd.DataFrame(collected)
    if df.empty:
        return df, "API 응답에서 공시가격/공시지가 필드를 찾지 못했습니다. endpoint·파라미터·응답 컬럼을 확인하세요."
    return df, "connected_or_partial"
