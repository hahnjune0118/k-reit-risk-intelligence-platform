# Architecture

## 1. 전체 구조

K-REITs Risk Intelligence Platform은 Streamlit 앱을 중심으로 데이터 로딩, 계산, metric definition, source policy, UI 렌더링을 분리한 구조입니다.

```text
app.py
├─ config.py
├─ data_loader.py
├─ data_availability.py
├─ data_source_policy.py
├─ metric_definitions.py
├─ tax_data_loader.py
├─ calculations_holding_tax_bridge.py
├─ tax_validation.py
├─ tax_request_mapping.py
├─ calculations_tax_review_pack.py
├─ calculations_*.py
├─ red_flag_engine.py
├─ ui_*.py
└─ data/*.csv / data/*.json
```

`app.py`는 진입점과 orchestration 역할만 담당합니다. 화면 표시 문구와 table 렌더링은 `ui_*.py`에, 계산 로직은 `calculations_*.py`, `tax_*.py`, `red_flag_engine.py`에 둡니다.

## 2. 앱 진입점

```powershell
py -m streamlit run app.py
```

`app.py`의 주요 흐름:

1. 페이지 설정 및 모드 선택
2. 내부 CSV 데이터 로딩
3. Peer Snapshot 및 Red Flag Rule 로딩
4. 사이드바 분석 모드, 분석 대상회사, 시나리오, 데이터 연결 상태 구성
5. General/Tax/Assurance/Methodology 화면으로 context 전달

## 3. 활성 UI 모드

공개 v14.1에서 활성화된 화면은 네 가지입니다.

- 일반 정보 및 시나리오
- Tax: 보유세 분석
- Assurance: 감사위험 분석
- 분석 방법론 및 데이터 출처

Deals 모드와 KRX 기반 시장가치 분석은 공개 런타임에서 호출하지 않습니다.

## 4. v14.1 Tax 데이터 흐름

Tax 화면의 기본 흐름:

1. `tax_data_loader.py`가 선택 회사의 Tax Snapshot을 읽고, 부족하면 회사 전체 fallback 행을 생성
2. `data_source_policy.py`가 `source_type`별 한국어 라벨, 신뢰수준, 허용 산출물, UI/Memo 제한 문구를 제공
3. `calculations_holding_tax_bridge.py`가 공시가격 또는 장부가액에서 과세표준, 추정 보유세, FFO proxy 부담을 계산
4. `tax_validation.py`가 결측, fallback 사용, 0 denominator, 비정상 비율을 검증
5. `calculations_tax_review_pack.py`가 Issue Matrix, Reconciliation, FFO proxy Stress, Memo를 생성
6. `tax_request_mapping.py`가 Issue Matrix와 source 상태를 요청자료 리스트로 변환
7. `ui_tax.py`가 Memo, Issue Matrix, Reconciliation, Request List export를 제공

Fallback hierarchy:

1. 자산별 tax row
2. Peer Snapshot의 `estimated_holding_tax`
3. Peer Snapshot의 `official_price_total`
4. Peer Snapshot의 `investment_property`
5. `data_insufficient`

자산별 상세자료가 부족한 회사는 `asset_name = "회사 전체 추정"`, `region = "회사 전체"` 행으로 표시합니다.

## 5. 회사별 데이터 가용성

`data_availability.py`는 선택 회사별 상세 데이터 가용성을 한 곳에서 판정합니다. 현재 공개 sample에서 SK리츠 상세 자산 자료는 SK리츠 선택 시에만 사용합니다. 다른 상장리츠는 SK리츠 자산 목록, 임차인, Cap rate, 차입금 만기 자료를 재사용하지 않습니다.

## 6. 지표 정의와 source lineage

`metric_definitions.py`는 화면과 문서에서 공통으로 사용하는 핵심 지표 정의를 관리합니다.

- FFO proxy: 공식 공시 FFO와 다를 수 있는 비교 목적 proxy
- 장부기준 NAV proxy: 총자산 - 총부채. Snapshot에 총부채가 없으면 총자산 - 차입금으로 대체하지 않음
- 총자산 기준 차입비율: 이자부 차입부채 / 총자산. 담보가치 기준 LTV가 아니며 충당부채와 일반 영업채무는 분자에서 제외
- WALE 및 Cap rate proxy: 자산별 또는 계약별 상세자료가 있을 때만 사용

## 7. 공개 런타임 원칙

공개 앱은 시작 시 모든 상장리츠의 DART 자료를 일괄 호출하지 않습니다. 선택 회사에 대해 DART 연결이 가능하면 DART 재무제표를 우선 사용하고, 실시간 연결이 제한되거나 계정이 부족하면 Snapshot 또는 예시 데이터로 안정적으로 전환합니다.

외부 데이터 인증값은 서버 측 설정 또는 환경변수에서만 불러옵니다. 공개 UI에는 인증값 입력 필드를 표시하지 않습니다. 디버그 출력이나 API 응답을 화면에 표시할 경우 `sanitize_secret_text()`로 마스킹합니다.

## 8. 버전 관리

현재 버전은 `v14.1`입니다.

버전 관련 파일:

- `VERSION`
- `CHANGELOG.md`
- `config.py`

주요 기능 업데이트가 있을 때는 위 세 파일을 함께 갱신합니다.
