from pathlib import Path


APP_VERSION = "v12"
APP_VERSION_NAME = "Peer Benchmark & Red Flag Engine"
APP_VERSION_LABEL = f"{APP_VERSION} - Peer Benchmark 및 Red Flag 자동화 버전"
APP_TITLE = "K-REIT Risk Intelligence Platform"
APP_SUBTITLE = (
    "상장리츠의 공시자료, 거시경제 지표, 자산별 정보, 공시가격 데이터를 연결하여 "
    "감사위험, 보유세 부담, Peer Benchmark 기반 Red Flag를 분석하는 Streamlit 기반 리스크 분석 도구"
)
PUBLIC_MODE_LABELS = {
    "General Info & Scenario": "일반 정보 및 시나리오",
    "Assurance": "Assurance: 감사위험 분석",
    "Tax": "Tax: 보유세 분석",
    "Methodology & Data Sources": "분석 방법론 및 데이터 출처",
}
DATA_DIR = Path(__file__).resolve().parent / "data"


ECOS_KEY_INDICATOR_ENDPOINT = "https://ecos.bok.or.kr/api/KeyStatisticList/{api_key}/json/kr/1/100"
ECOS_STAT_SEARCH_ENDPOINT = "https://ecos.bok.or.kr/api/StatisticSearch/{api_key}/json/kr/1/{count}/{stat_code}/{cycle}/{start_date}/{end_date}/{item_code}"

DART_CORP_CODE_ENDPOINT = "https://opendart.fss.or.kr/api/corpCode.xml"
DART_SINGLE_FS_ENDPOINT = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
DART_LIST_ENDPOINT = "https://opendart.fss.or.kr/api/list.json"

# Archived for future KRX-based Deals valuation module.
KRX_KOSPI_DAILY_TRADE_ENDPOINT = "https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd"

# 공시가격 계열 API는 승인 서비스별 조회 방식이 다를 수 있어 공개 UI에서는 예시 데이터 fallback을 기본으로 둡니다.
REALTY_PRICE_API_ENDPOINT_DEFAULT = ""


# ECOS item codes are kept as constants so they can be adjusted if ECOS code mappings change.
ECOS_RATE_SERIES = {
    "기준금리": {"stat_code": "722Y001", "cycle": "D", "item_code": "0101000"},
    "국고채 3년": {"stat_code": "817Y002", "cycle": "D", "item_code": "010200000"},
    "국고채 5년": {"stat_code": "817Y002", "cycle": "D", "item_code": "010200001"},
    "회사채 AA- 3년": {"stat_code": "817Y002", "cycle": "D", "item_code": "010300000"},
}

FALLBACK_MACRO = {
    "한국은행 기준금리": 2.50,
    "국고채수익률(3년)": 3.73,
    "국고채수익률(5년)": 3.78,
    "회사채수익률(3년, AA-)": 4.40,
}
