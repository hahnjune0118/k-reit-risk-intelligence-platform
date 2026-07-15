from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
V15_DATA_DIR = PROJECT_ROOT / "data" / "v15"

RESULT_STATUSES = {
    "verified_notice",
    "official_source_calculated",
    "official_partial",
    "manual_review_required",
    "data_insufficient",
    "not_applicable",
}

CALCULABLE_SOURCE_STATUSES = {
    "verified_notice",
    "official_source_calculated",
}

SOURCE_BADGES = {
    "verified_notice": "고지서 확인",
    "official_source_calculated": "공식자료 계산",
    "official_partial": "공식자료 일부",
    "manual_review_required": "수동 검토",
    "data_insufficient": "데이터 부족",
    "not_applicable": "해당 없음",
}

LAND_CLASSIFICATIONS = {
    "separated_public_reit",
    "separated_other",
    "separate_aggregate",
    "aggregate",
    "housing",
    "exempt",
    "undetermined",
}

DISCLAIMER_KO = (
    "본 검토는 공개된 자료 및 확인 가능한 공식 데이터를 바탕으로 한 초기 Tax Screening 결과이다. "
    "실제 세액은 개별 자산의 과세내역서, 시가표준액, 신탁·소유구조, 지방자치단체 조례, "
    "분리과세 판정, 합산배제 및 세부담상한 등에 따라 달라질 수 있다. 검증되지 않은 항목은 "
    "공식 신고·납부 또는 투자 의사결정의 확정 근거로 사용할 수 없다."
)
