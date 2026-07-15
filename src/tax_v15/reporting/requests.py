from __future__ import annotations

import hashlib

import pandas as pd

from ..schemas import CSV_SCHEMAS


REQUEST_MAP = {
    "asset_registry": [("자산 현황 및 편입·매각 내역", "공시 자산 수와 Asset Registry 완전성 확인")],
    "asset_source": [("최신 투자보고서·영업보고서·자산 목록", "자산 식별 근거 보완")],
    "taxpayer_cardinality": [
        ("자산별 등기부등본", "과세기준일 현재 법적 소유자 확인"),
        ("신탁원부·신탁계약서 및 지배구조도", "위탁자·수탁자와 실제 납세의무자 확인"),
    ],
    "taxpayer_verification": [
        ("자산별 등기부등본", "법적 소유자 확인"),
        ("신탁원부 및 신탁계약서", "신탁재산 납세의무자 확인"),
    ],
    "separation_tax_eligibility": [
        ("분리과세 코드가 표시된 재산세 과세내역서", "실제 과세구분 확인"),
        ("공모부동산투자회사 또는 법정 자회사 해당 근거", "법적 주체 요건 확인"),
        ("자산의 목적사업 사용 증빙", "분리과세 목적사업 사용 요건 확인"),
    ],
    "parcel_registry": [
        ("자산별 토지대장·지적도·PNU 목록", "필지 단위 과세표준 산출"),
        ("자산별 소유지분 자료", "필지별 과세면적 및 지분 확인"),
    ],
    "pnu_required": [("자산별 토지대장·지적도·PNU 목록", "필지 단위 과세표준 산출")],
    "duplicate_pnu": [("필지별 소유지분 및 자산-PNU 매핑표", "중복 필지 또는 공동소유 여부 확인")],
    "parcel_source": [("개별공시지가 확인서 및 토지대장", "필지별 공식 입력값 출처 확인")],
    "building_standard_value": [
        ("건축물 시가표준액 산출내역", "건축물 재산세 과세표준 확인"),
        ("건축물대장", "용도·구조·연면적 확인"),
    ],
    "urban_area_applicability": [("도시지역분 적용 내역 및 관련 조례", "도시지역분 적용 여부와 세율 확인")],
    "fire_risk_classification": [("소방분 용도·가중배율 판정자료", "100%·200%·300% 가중배율 확인")],
    "tax_notice": [
        ("자산별 재산세 납세고지서 및 과세내역서", "계산 결과와 실제 고지세액 대사"),
        ("종합부동산세 납부고지서 및 과세물건 명세", "전국 합산 과세표준과 공제액 확인"),
    ],
    "unverified_number_block": [("해당 계산의 공식 과세자료", "검증되지 않은 숫자 차단 해소")],
    "calculation_status_domain": [("계산 검토 로그", "비표준 상태 원인 확인")],
}


def build_request_list(validations: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    if validations is None or validations.empty:
        return pd.DataFrame(columns=CSV_SCHEMAS["request_list.csv"])
    for _, item in validations[validations["validation_status"].ne("passed")].iterrows():
        check = str(item.get("check_name", ""))
        mapped_requests = REQUEST_MAP.get(
            check,
            [("관련 공식 증빙자료", str(item.get("message", "추가 확인 필요")))],
        )
        for document, reason in mapped_requests:
            raw_id = "|".join([str(item.get("reit_name", "")), str(item.get("asset_id", "")), check, document])
            rows.append({
                "request_id": hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16],
                "reit_name": item.get("reit_name", ""),
                "taxpayer_id": item.get("taxpayer_id", ""),
                "asset_id": item.get("asset_id", ""),
                "issue_code": check,
                "issue": item.get("message", ""),
                "request_document": document,
                "request_reason": reason,
                "priority": "P0" if item.get("severity") in {"critical", "high"} else "P1",
                "calculation_status": "manual_review_required",
                "reviewer_status": "open",
            })
    return pd.DataFrame(rows, columns=CSV_SCHEMAS["request_list.csv"]).drop_duplicates("request_id")
