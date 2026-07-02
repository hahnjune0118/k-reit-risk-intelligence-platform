# Codex Handoff - K-REIT Risk Intelligence Platform

현재 안정 공개 버전: **v12 - Peer Benchmark & Red Flag Engine**

## 현재 범위

v12는 한국어 사용자를 기준으로 정리한 상장리츠 리스크 분석 공개 포트폴리오 버전입니다. 활성 Streamlit 화면은 다음 네 가지입니다.

1. 일반 정보 및 시나리오
2. Assurance: 감사위험 분석
3. Tax: 보유세 분석
4. 분석 방법론 및 데이터 출처

v12의 핵심 추가 기능은 상장리츠 Peer Benchmark, Assurance Red Flag Engine, Tax 보유세 부담 Benchmark, Red Flag별 감사절차 및 요청자료 추천입니다. Deals 모드와 KRX 기반 시장가격 분석은 공개 UI와 앱 런타임에서 계속 비활성화합니다.

## 실행 진입점

Streamlit 진입점은 `app.py`입니다.

```powershell
py -m streamlit run app.py
```

## 주요 파일

- `config.py`: 앱 버전, 제목, 표시 라벨, endpoint 상수
- `api_manager.py`: 안전한 외부 데이터 인증값 로딩과 마스킹
- `calculations_peer.py`: Peer Snapshot 로딩, metric, percentile 계산
- `red_flag_engine.py`: Assurance 및 Tax Red Flag 평가
- `data/reit_master.csv`: 상장리츠 마스터 정보
- `data/reit_peer_snapshot.csv`: Peer Benchmark용 snapshot
- `data/red_flag_rules.json`: Red Flag 판단 규칙
- `ui_layout.py`: 공개 모드 선택과 첫 화면 설명
- `ui_sidebar.py`: 공통 시나리오, 데이터 연결 상태, Peer 대상 선택
- `ui_general.py`: 일반 정보, Scenario, Peer Benchmark 요약
- `ui_assurance.py`: 감사위험 분석 workflow와 Peer 기반 Red Flag
- `ui_tax.py`: 보유세 분석 workflow와 Peer 기반 보유세 부담 분석
- `ui_methodology.py`: 분석 방법론 및 데이터 출처

## 보안

외부 데이터 인증값을 Streamlit widget의 `value=`에 넣거나 화면에 표시하면 안 됩니다. 인증값은 `api_manager.get_api_key()`로 로드하고, 화면에 표시될 수 있는 API 응답이나 상태 문구는 `api_manager.sanitize_secret_text()`로 마스킹합니다.

공개 UI에서는 사용자가 인증키를 입력하도록 요구하지 않습니다. 서버 측 설정 또는 환경변수에서 값을 읽고, 실시간 데이터 연결이 제한될 경우 snapshot 또는 예시 데이터로 전환합니다.

## 버전 관리

중요 기능이 추가되는 경우 v13, v14처럼 순차적으로 버전을 올립니다. `VERSION`, `CHANGELOG.md`, `config.py`의 표시 버전을 함께 맞춥니다.
