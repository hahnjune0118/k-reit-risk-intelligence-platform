# Architecture

## 1. 전체 구조

K-REIT Risk Intelligence Platform은 Streamlit 앱을 중심으로 데이터 로딩, 계산, API 연결, UI 렌더링을 분리한 구조입니다.

```text
app.py
├─ config.py
├─ data_loader.py
├─ api_manager.py
├─ api_ecos.py / api_dart.py / api_real_estate_board.py
├─ calculations_*.py
├─ red_flag_engine.py
├─ ui_*.py
└─ data/*.csv / data/*.json
```

`app.py`는 진입점과 orchestration 역할만 담당합니다. 각 화면의 표시 문구와 table 렌더링은 `ui_*.py`에, 계산 로직은 `calculations_*.py`와 `red_flag_engine.py`에 둡니다.

## 2. 앱 진입점

Streamlit 진입점은 `app.py`입니다.

```powershell
py -m streamlit run app.py
```

`app.py`의 주요 흐름:

1. 페이지 설정 및 모드 선택
2. 내부 CSV 데이터 로딩
3. Peer Snapshot 및 Red Flag Rule 로딩
4. 사이드바 분석 모드, 분석 대상회사, 시나리오, 데이터 연결 상태 구성
5. Assurance/Tax/General/Methodology 화면으로 context 전달

## 3. 활성 UI 모드

공개 v12에서 활성화된 화면은 네 가지입니다.

- 일반 정보 및 시나리오
- Assurance: 감사위험 분석
- Tax: 보유세 분석
- 분석 방법론 및 데이터 출처

Deals 모드와 KRX 기반 시장가치 분석은 공개 런타임에서 호출하지 않습니다.

사이드바는 `분석 모드 → 분석 대상회사 → 시나리오 → 데이터 연결 상태` 순서로 구성합니다. 분석 대상회사는 `data/reit_master.csv`의 시가총액 순위 Snapshot을 기준으로 정렬하고, 선택된 회사의 종목코드와 DART corp_code를 공통 상태로 전달합니다. 공개 UI에서는 인증값 입력 필드를 표시하지 않습니다.

## 4. 데이터 흐름

주요 입력 데이터:

- `data/sk_reit_*.csv`: 기본 REIT 분석용 내부 CSV
- `data/reit_master.csv`: 상장리츠 마스터 정보
- `data/reit_peer_snapshot.csv`: Peer Benchmark Snapshot
- `data/red_flag_rules.json`: Assurance/Tax Red Flag 판단 규칙

선택 회사 workflow:

1. 사이드바에서 시가총액 순위 Snapshot 기준으로 정렬된 상장리츠를 선택
2. `dart_financials.py`가 회사명, 종목코드, DART corp_code, market cap rank를 해석
3. 최근 5년 재무 흐름은 `data/reit_peer_snapshot.csv`의 Snapshot을 우선 사용
4. Snapshot이 부족하고 서버 측 DART 연결이 가능한 경우에만 선택 회사 DART 자료를 보조 조회
5. General, Assurance, Tax 화면은 같은 선택 회사 context를 사용
6. 분석 실행 시 `analysis_run_id`를 갱신하고 회사별 상세 자산·보유세 관련 session state를 초기화하여 이전 회사의 세부 데이터가 남지 않도록 처리

회사별 상세 자산·차입금·보유세 데이터가 없는 경우에는 빈 DataFrame과 `detail_data_available = False` 상태를 전달합니다. 이때 Assurance와 Tax 화면은 SK리츠 등 다른 회사의 샘플 데이터를 재사용하지 않고, 데이터 부족 안내와 Peer Benchmark/재무 Snapshot 중심의 결과를 표시합니다.

v12 Peer Benchmark 흐름:

1. `calculations_peer.load_peer_snapshot()`으로 snapshot 로딩
2. `calculate_peer_metrics()`로 주요 지표 계산
3. `calculate_percentile_ranks()`로 Peer 내 상대 위치 계산
4. `red_flag_engine.build_assurance_red_flags()`와 `build_tax_red_flags()`로 Red Flag 평가
5. `ui_peer.py`, `ui_assurance.py`, `ui_tax.py`에서 결과 표시

## 5. API 연결 구조

API 연결은 공개 UI의 필수 조건이 아닙니다. 서버 측 설정 또는 환경변수로 인증값을 사용할 수 있고, 실시간 연결이 제한되면 Snapshot 또는 예시 데이터로 전환합니다.

활성 API 성격:

- ECOS: 거시경제 지표
- DART: 공시 및 재무제표 보조 데이터
- V-World / official land price related data: 보유세 분석 관련 공시가격 데이터

KRX API는 현재 공개 런타임에서 비활성화되어 있습니다.

공시가격 데이터는 공개 리뷰 환경에서 실시간 조회가 제한될 수 있으므로, Tax 화면은 예시 데이터와 선택적 CSV 업로드를 통해 계속 사용할 수 있게 설계했습니다.

최근 5년 흐름 화면은 금리와 리츠 재무지표를 하나의 축으로 지수화하지 않습니다. 기준금리, 국고채, 회사채 금리는 실제 이자율(%)로 표시하고, NAV, FFO, 총자산, 차입금, 이자비용은 실제 금액(억원) 표로 구분합니다.

## 6. 보안 설계

`api_manager.py`는 외부 데이터 인증값 로딩과 마스킹을 담당합니다.

보안 원칙:

- API Key를 GitHub에 저장하지 않음
- API Key를 Streamlit UI에 표시하지 않음
- API Key를 widget 기본값으로 전달하지 않음
- 디버그 출력이나 API 응답을 화면에 표시할 경우 `sanitize_secret_text()`로 마스킹
- 공개 사용자가 별도 인증키를 입력하지 않아도 앱을 검토할 수 있도록 Snapshot 기반 fallback 유지

## 7. 버전 관리

현재 버전은 `v12`입니다.

버전 관련 파일:

- `VERSION`
- `CHANGELOG.md`
- `config.py`

주요 기능 업데이트가 있을 때는 위 세 파일을 함께 갱신합니다.
