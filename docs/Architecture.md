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
4. 사이드바 시나리오와 데이터 연결 상태 구성
5. Assurance/Tax/General/Methodology 화면으로 context 전달

## 3. 활성 UI 모드

공개 v12에서 활성화된 화면은 네 가지입니다.

- 일반 정보 및 시나리오
- Assurance: 감사위험 분석
- Tax: 보유세 분석
- 분석 방법론 및 데이터 출처

Deals 모드와 KRX 기반 시장가치 분석은 공개 런타임에서 호출하지 않습니다.

## 4. 데이터 흐름

주요 입력 데이터:

- `data/sk_reit_*.csv`: 기본 REIT 분석용 내부 CSV
- `data/reit_master.csv`: 상장리츠 마스터 정보
- `data/reit_peer_snapshot.csv`: Peer Benchmark Snapshot
- `data/red_flag_rules.json`: Assurance/Tax Red Flag 판단 규칙

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
