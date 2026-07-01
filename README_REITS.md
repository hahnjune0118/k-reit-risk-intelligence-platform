# K-REIT Risk Intelligence Platform v10.1

SK리츠 단일 케이스를 기준으로 공시자료, ECOS 거시경제 지표, DART 재무제표, KRX 시장가격, 자산별 임대·차입·보유세 데이터를 연결해 리츠 위험 전이 경로를 분석하는 Streamlit 앱입니다.

## 주요 변경사항

- General Info & Scenario와 Assurance / Tax / Deals 화면 분리
- Tax 모드에서 양도세 제거, 보유세 분석만 심화
- 보유세 산식 expander 추가: 과세표준, 별도합산 토지 세율, 건물분, 도시지역분, 지방교육세
- 한국부동산원/공시가격 계열 API endpoint와 파라미터 템플릿 입력 기능 추가
- 공시가격/기준시가 CSV 업로드 fallback 추가
- 최근 5년 공시지가/기준시가 변화에 따른 보유세 추이 분석 추가

## 실행

```powershell
py -m streamlit run app.py
```

## 개발 검증

```powershell
py -m pip install -r requirements.txt
py -m pip install -r requirements-dev.txt
py -m compileall -q .
py -m pytest -q
```

## 현재 파일 구조

```text
app.py                         # Streamlit orchestration layer
config.py                      # app title, data path, API endpoints
data_loader.py                 # CSV loading, schema validation, date-derived fields
data_validation.py             # required-column checks
formatting.py                  # display formatting helpers
api_ecos.py                    # ECOS macro indicators
api_dart.py                    # OpenDART financial statements and reports
api_krx.py                     # KRX API and KRX CSV fallback
api_real_estate_board.py       # official-price API/upload helpers
calculations_*.py              # scenario, risk, tax, assurance, deals calculations
ui_*.py                        # Streamlit layout and mode renderers
tests/                         # pytest smoke/regression tests
examples/                      # upload CSV templates
data/                          # bundled SK REIT source CSVs
```

## Tax CSV 권장 컬럼

- asset_name 또는 자산명
- year 또는 연도
- official_land_price_per_sqm_krw 또는 개별공시지가_원_m2
- building_standard_value_mn_krw 또는 건물기준시가_백만원
- land_area_sqm 또는 토지면적_sqm
- source 또는 출처

샘플 파일:

- `examples/holding_tax_sample.csv`
- `examples/krx_price_sample.csv`

## 주의사항

이 앱은 preliminary risk screening 및 포트폴리오 설명용 프로토타입입니다. 투자추천, 정식 가치평가, 감사의견, 세무 신고용 계산 결과를 제공하지 않습니다. DART 재무제표와 리츠 투자보고서 KPI는 basis가 다르므로, 공식 업무에 사용하기 전 원천 문서와 반드시 대사해야 합니다.
