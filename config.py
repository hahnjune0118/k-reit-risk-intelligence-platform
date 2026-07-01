from pathlib import Path


APP_TITLE = "K-REIT Risk Intelligence Platform | v10.1 General Scenario · Assurance · Holding Tax · Deals"
DATA_DIR = Path(__file__).resolve().parent / "data"


ECOS_KEY_INDICATOR_ENDPOINT = "https://ecos.bok.or.kr/api/KeyStatisticList/{api_key}/json/kr/1/100"
ECOS_STAT_SEARCH_ENDPOINT = "https://ecos.bok.or.kr/api/StatisticSearch/{api_key}/json/kr/1/{count}/{stat_code}/{cycle}/{start_date}/{end_date}/{item_code}"

DART_CORP_CODE_ENDPOINT = "https://opendart.fss.or.kr/api/corpCode.xml"
DART_SINGLE_FS_ENDPOINT = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
DART_LIST_ENDPOINT = "https://opendart.fss.or.kr/api/list.json"

# KRX Data Marketplace Open API.
# 사용자의 KRX Open API 사용신청/승인 상태에 따라 호출 가능 여부가 달라질 수 있습니다.
KRX_KOSPI_DAILY_TRADE_ENDPOINT = "https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd"

# 한국부동산원 부동산공시가격 계열 API는 사용신청 서비스별 endpoint/파라미터가 다를 수 있어
# 사용자가 실제 승인받은 endpoint와 파라미터 템플릿을 입력할 수 있도록 설계합니다.
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
