# K-REIT Risk Intelligence Platform

K-REIT Risk Intelligence Platform은 상장리츠의 공시자료, 거시경제 지표, 자산별 정보, 공시가격/기준시가 데이터, Peer Snapshot을 연결하여 감사위험과 보유세 부담을 분석하는 Streamlit 기반 공개 포트폴리오 애플리케이션입니다.

현재 안정 공개 버전: **v12 - Peer Benchmark & Red Flag Engine**

## 프로젝트 개요

이 프로젝트는 리츠 공시자료를 단순히 읽는 수준을 넘어, 재무·세무·감사 관점에서 함께 봐야 하는 항목을 한 화면에 연결하기 위해 만들었습니다. v12에서는 단일 회사 분석에 더해 상장리츠 Peer Benchmark와 Red Flag Engine을 추가했습니다.

대상 사용자는 리츠 업무를 처음 접하는 회계사, 감사·세무·자문 업무 담당자, 그리고 회계/컨설팅 업무의 디지털 전환 사례를 검토하는 사용자입니다. 기본 회계 지식은 있다고 가정하지만, REIT, API, Streamlit, 부동산 가치평가 모델에는 익숙하지 않을 수 있다는 점을 고려해 한국어 중심으로 설명했습니다.

이 앱은 예비 분석 및 업무 검토 지원 도구입니다. 감사의견, 세무신고서, 법률 자문, 투자추천, 신용등급, 정식 가치평가 의견을 제공하지 않습니다.

## v12 현재 범위

공개 UI의 활성 화면은 네 가지입니다.

1. 일반 정보 및 시나리오
2. Assurance: 감사위험 분석
3. Tax: 보유세 분석
4. 분석 방법론 및 데이터 출처

v12의 핵심 추가 기능은 다음과 같습니다.

1. 상장리츠 Peer Benchmark
2. Assurance Red Flag Engine
3. Tax 보유세 부담 Benchmark
4. 감사절차 및 요청자료 추천

## 주요 기능

### 상장리츠 Peer Benchmark

`data/reit_peer_snapshot.csv`에 포함된 상장리츠 snapshot 데이터를 기준으로 선택한 리츠의 자산규모, 차입부담, 이자비용 부담, 보유세 부담, 공시가격 대비 투자부동산 장부금액 비율을 peer group과 비교합니다.

### Assurance Red Flag Engine

투자부동산 집중도, 부채 부담, 단기 만기 집중, FFO 대비 이자비용, FFO 대비 배당, 영업현금흐름 배당 커버리지 등을 기준으로 감사계획 단계에서 참고할 수 있는 Red Flag를 표시합니다. 각 Red Flag에는 권장 감사절차와 요청 증거 목록이 연결됩니다.

### Tax 보유세 부담 Benchmark

보유세/FFO, 보유세/영업수익, 공시가격/투자부동산 비율을 peer group과 비교합니다. 이 분석은 신고 목적의 세액 산출이 아니라 보유자산별 세금 부담의 방향성과 민감도를 파악하기 위한 예비 분석입니다.

### 감사절차 및 요청자료 추천

Red Flag별로 실무자가 다음 단계에서 요청할 수 있는 문서와 검토 포인트를 제시합니다. 예를 들어 감정평가보고서, 차입금 약정서, 재산세 고지서, 개별공시지가 자료, 현금흐름 forecast 등이 포함됩니다.

## 데이터 구조

- **DART**: 개별 회사 재무제표와 최근 공시 목록 확인
- **ECOS**: 기준금리, 국고채, 회사채 등 거시경제 지표와 과거 금리 시계열
- **V-World / 공시가격 API**: 공시가격, 개별공시지가, 기준시가 등 Tax 화면 입력값
- **REIT Peer Snapshot**: v12 Peer Benchmark와 Red Flag Engine의 기본 입력값
- **Red Flag Rules**: Assurance 및 Tax 위험수준 판단 기준
- **내부 CSV 파일**: 공개 데모가 안정적으로 실행되도록 포함한 공시 기반 테이블

주요 v12 파일:

- `data/reit_master.csv`: 상장리츠 마스터 정보
- `data/reit_peer_snapshot.csv`: peer benchmark용 snapshot 데이터
- `data/red_flag_rules.json`: Red Flag 판단 규칙
- `calculations_peer.py`: peer metric 및 percentile 계산
- `red_flag_engine.py`: Red Flag 평가 로직
- `scripts/refresh_reit_peer_snapshot.py`: 선택적 DART snapshot 갱신 스크립트

`source_type = "sample_snapshot"`인 데이터는 공개 포트폴리오 검토용 예시 데이터입니다. 감사된 자료나 공식 확정 자료로 표시하지 않습니다.

## Snapshot 기반 설계 이유

공개 배포 버전은 앱 시작 시 모든 상장리츠의 DART API를 실시간 호출하지 않습니다. 전체 리츠 공시를 매번 호출하면 속도가 느려지고, API 제한이나 네트워크 상태에 따라 공개 링크의 안정성이 떨어질 수 있습니다.

따라서 v12는 빠른 실행과 안정적인 리뷰 경험을 위해 snapshot 데이터를 기본으로 사용합니다. 필요할 경우 별도 수집 스크립트로 snapshot을 갱신할 수 있으며, API 호출 실패 시 기존 snapshot은 삭제하지 않습니다.

## 데이터 연결 및 보안

공개 배포 버전은 서버 측 데이터 연결 설정 또는 환경변수를 통해 외부 데이터 인증값을 관리합니다. 사용자는 별도의 인증키를 발급하거나 입력할 필요가 없습니다.

보안 원칙:

- 인증값은 화면, GitHub 저장소, 로그, 디버그 출력에 표시하지 않습니다.
- 인증값은 Streamlit widget의 기본값으로 주입하지 않습니다.
- 디버그 문구, API 응답, 요청 파라미터를 화면에 표시해야 하는 경우에는 `api_manager.sanitize_secret_text()`로 마스킹합니다.
- KRX 데이터 연결은 v12 공개 UI와 앱 런타임에서 비활성화되어 있습니다.

서버 측 설정 이름:

```toml
ECOS_API_KEY = "..."
DART_API_KEY = "..."
REALTY_PRICE_API_KEY = "..."
```

## 실행 방법

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

개발 중 점검 명령:

```powershell
py -m pip install -r requirements-dev.txt
py -m compileall -q . -x "(\.git|\.venv|venv|__pycache__|\.cache|\.vscode)"
py -m pytest -q
```

선택적 snapshot 갱신:

```powershell
py scripts\refresh_reit_peer_snapshot.py
```

이 스크립트는 앱 시작 시 자동 실행되지 않습니다.

## 현재 제외된 기능

- Deals mode
- KRX market valuation
- 시장가격 기반 P/NAV, P/FFO 분석
- 거래 목적 가치평가

위 기능은 삭제한 것이 아니라 공개 v12 범위에서 비활성화한 상태입니다.

## 향후 로드맵

향후 v13 이후 버전에서는 다음 기능을 검토할 수 있습니다.

- 공시자료와 감사증거 문서 자동 추출
- Evidence request checklist 내보내기
- AI-assisted memo drafting
- 여러 REIT 간 다기간 trend 비교
- Snapshot 갱신 자동화 고도화

## 버전 관리

중요 기능이 추가되는 경우 버전을 순차적으로 올립니다: v13, v14 등. `VERSION`, `CHANGELOG.md`, `config.py`의 화면 표시 버전을 함께 맞춥니다.
