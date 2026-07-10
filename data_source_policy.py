from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SourcePolicy:
    source_type: str
    korean_label: str
    reliability_level: str
    allowed_outputs: tuple[str, ...]
    memo_limitation_text: str
    ui_warning_text: str


SOURCE_POLICIES: dict[str, SourcePolicy] = {
    "official_disclosure": SourcePolicy(
        source_type="official_disclosure",
        korean_label="공식 공시/공식 원천자료",
        reliability_level="높음",
        allowed_outputs=("Tax Summary", "보유세 브리지", "Issue Matrix", "Request List", "Memo Draft"),
        memo_limitation_text="공식 공시자료를 사용하더라도 원자료 대사와 회사 확인 없이는 확정 세액이나 법률의견으로 사용할 수 없습니다.",
        ui_warning_text="공식 공시자료 기준입니다. 최종 판단 전 원자료 대사와 회사 확인이 필요합니다.",
    ),
    "api_snapshot": SourcePolicy(
        source_type="api_snapshot",
        korean_label="API/Snapshot 자료",
        reliability_level="중간",
        allowed_outputs=("Tax Summary", "보유세 브리지", "Issue Matrix", "Request List", "Memo Draft"),
        memo_limitation_text="API 또는 Snapshot 자료는 기준일과 수집 방식의 차이가 있을 수 있으므로 원자료 확인이 필요합니다.",
        ui_warning_text="API/Snapshot 기준입니다. 기준일과 원천자료 차이를 확인해야 합니다.",
    ),
    "peer_snapshot": SourcePolicy(
        source_type="peer_snapshot",
        korean_label="Peer Snapshot",
        reliability_level="중간-제한",
        allowed_outputs=("Peer 비교", "Issue Matrix", "Request List", "Memo Draft"),
        memo_limitation_text="Peer Snapshot은 비교와 초기 선별 목적의 자료이며 회사별 자산 원장이나 고지세액을 대체하지 않습니다.",
        ui_warning_text="Peer Snapshot 기준입니다. 회사별 상세 원자료가 확보된 범위 안에서 해석해야 합니다.",
    ),
    "peer_snapshot_estimate": SourcePolicy(
        source_type="peer_snapshot_estimate",
        korean_label="Peer 기반 회사 전체 추정",
        reliability_level="추정",
        allowed_outputs=("Tax Summary", "보유세 브리지", "Issue Matrix", "Request List", "Memo Draft"),
        memo_limitation_text="회사 전체 Snapshot 기반 추정값입니다. 자산별 고지세액, 과세표준, 장부가액 명세로 반드시 보완해야 합니다.",
        ui_warning_text="회사 전체 Snapshot 기반 추정입니다. 자산별 상세자료가 부족한 상태의 예비 분석입니다.",
    ),
    "sample_estimate": SourcePolicy(
        source_type="sample_estimate",
        korean_label="공개 데모 예시 추정",
        reliability_level="예시",
        allowed_outputs=("Tax Summary", "보유세 브리지", "Issue Matrix", "Request List", "Memo Draft"),
        memo_limitation_text="공개 데모 예시 데이터가 포함되어 있습니다. 실제 업무 사용 전 회사 원자료와 공식 조회자료로 교체해야 합니다.",
        ui_warning_text="공개 데모 예시 데이터가 포함되어 있습니다. 실제 업무용 원자료가 아닙니다.",
    ),
    "data_insufficient": SourcePolicy(
        source_type="data_insufficient",
        korean_label="데이터 부족",
        reliability_level="부족",
        allowed_outputs=("Request List", "Memo Limitation"),
        memo_limitation_text="핵심 입력값이 부족하여 수치 산출이 제한됩니다. 원자료 확보 전에는 수치 결론을 제시하지 않습니다.",
        ui_warning_text="핵심 입력값이 부족합니다. 요청자료 확보 후 재계산해야 합니다.",
    ),
}

SOURCE_TYPE_ALIASES = {
    "": "data_insufficient",
    "unknown": "data_insufficient",
    "data_missing": "data_insufficient",
    "missing": "data_insufficient",
    "sample_snapshot": "api_snapshot",
    "dart_optional_refresh": "api_snapshot",
    "dart_api_selected_company": "official_disclosure",
    "high_disclosed_kpi": "official_disclosure",
    "high_disclosed_summary": "official_disclosure",
    "high_disclosed_table": "official_disclosure",
    "official_price_estimate": "peer_snapshot_estimate",
    "investment_property_estimate": "peer_snapshot_estimate",
}

SOURCE_STRENGTH_ORDER = {
    "official_disclosure": 0,
    "api_snapshot": 1,
    "peer_snapshot": 2,
    "sample_estimate": 3,
    "peer_snapshot_estimate": 4,
    "data_insufficient": 5,
}


def _split_source_types(source_type: str | None) -> list[str]:
    if source_type is None:
        return []
    text = str(source_type).strip()
    if not text:
        return []
    for sep in [";", "/", "|"]:
        text = text.replace(sep, ",")
    return [part.strip() for part in text.split(",") if part.strip()]


def normalize_source_type(source_type: str | None) -> str:
    text = str(source_type or "").strip()
    canonical = SOURCE_TYPE_ALIASES.get(text, text)
    if canonical in SOURCE_POLICIES:
        return canonical
    if "estimate" in text or "proxy" in text or "추정" in text:
        return "peer_snapshot_estimate"
    if "sample" in text:
        return "sample_estimate"
    if "snapshot" in text:
        return "api_snapshot"
    return "data_insufficient"


def dominant_source_type(source_type_text: str | None) -> str:
    parts = _split_source_types(source_type_text)
    if not parts:
        return "data_insufficient"
    canonical = [normalize_source_type(part) for part in parts]
    return max(canonical, key=lambda source_type: SOURCE_STRENGTH_ORDER.get(source_type, 99))


def get_source_policy(source_type: str | None) -> SourcePolicy:
    return SOURCE_POLICIES[dominant_source_type(source_type)]


def source_type_label(source_type: str | None) -> str:
    return get_source_policy(source_type).korean_label


def source_reliability_level(source_type: str | None) -> str:
    return get_source_policy(source_type).reliability_level


def contains_estimate_source(source_type_text: str | None) -> bool:
    source_type = dominant_source_type(source_type_text)
    return source_type in {"peer_snapshot_estimate", "sample_estimate", "data_insufficient"} or any(
        keyword in str(source_type_text or "")
        for keyword in ["estimate", "proxy", "추정", "sample", "data_missing"]
    )


def source_policy_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "source_type": policy.source_type,
                "한국어 라벨": policy.korean_label,
                "신뢰수준": policy.reliability_level,
                "허용 산출물": ", ".join(policy.allowed_outputs),
                "Memo 한계 문구": policy.memo_limitation_text,
                "UI 경고 문구": policy.ui_warning_text,
            }
            for policy in SOURCE_POLICIES.values()
        ]
    )
