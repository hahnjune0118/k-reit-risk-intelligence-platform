# K-REIT Risk Intelligence Platform

## 1. 프로젝트 개요

이 프로젝트는 상장 K-REIT의 Tax 업무 검토를 돕는 Streamlit 기반 워크플로 앱입니다. 공시자료, Peer Snapshot, 공시가격·보유세 추정 가정, 재무지표를 연결해 다음 산출물을 생성합니다.

- Tax Summary
- Holding Tax Bridge
- Tax Issue Matrix
- Holding Tax Reconciliation
- Tax Request List
- Tax Review Memo Draft
- Validation Panel
- CSV/Markdown/ZIP Export

현재 버전은 **v14 - Tax Workflow Control & Validation**입니다. 신고 목적의 확정 세액, 법률의견, 공식 세무자문, 투자 추천을 제공하지 않으며 공개자료와 Snapshot 기반의 예비 검토를 돕습니다.

## 2. 현재 활성 모드

활성 Streamlit 모드는 네 가지입니다.

1. 일반 정보 및 시나리오
2. Tax: 보유세 분석
3. Assurance: 감사위험 분석
4. 분석 방법론 및 데이터 출처

Deals 모드와 KRX 기반 시장가치 분석은 공개 런타임에서 비활성화되어 있으며 앱 시작 경로에서 호출하지 않습니다.

## 3. v14 핵심 기능

v14는 Tax Review Pack을 단순 생성하는 것을 넘어, 자료 출처와 계산 한계를 산출물 전체에 일관되게 연결합니다.

- `data_source_policy.py`: `official_disclosure`, `api_snapshot`, `peer_snapshot`, `peer_snapshot_estimate`, `sample_estimate`, `data_insufficient` source taxonomy
- `calculations_holding_tax_bridge.py`: 공시가격 또는 장부가액에서 과세표준, 추정 보유세, FFO 부담으로 이어지는 bridge
- `tax_validation.py`: 결측, 회사 전체 fallback, 0 denominator, 비정상 비율 검증
- `tax_request_mapping.py`: Issue Matrix 기반 요청자료 리스트 생성
- Tax Memo 6개 섹션: 검토 대상, 핵심 수치 요약, 주요 Tax 이슈, 요청자료, 실무적 시사점, 제한 및 유의사항
- Memo, Issue Matrix, Reconciliation, Request List 다운로드

## 4. 데이터 원칙

공개 앱은 시작 시 모든 상장리츠의 DART 자료를 실시간 호출하지 않습니다. 사용자가 사이드바에서 분석 대상회사를 선택하면 해당 회사의 Snapshot 기반 최근 5년 흐름을 우선 사용하고, Snapshot이 부족한 경우에만 선택 회사의 보조 자료를 사용할 수 있도록 설계했습니다.

회사별 상세 자산·보유세 데이터의 가용성은 서로 다를 수 있습니다. 상세 데이터가 부족한 회사는 다른 회사의 자산 샘플을 재사용하지 않고, `회사 전체 추정` 행과 `region = "회사 전체"` 기준으로 Tax Pack을 생성합니다. 이 값은 신고 목적 세액이 아니라 예비 검토용 입력값입니다.

## 5. 실행 방법

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

개발 점검:

```powershell
py -m pip install -r requirements-dev.txt
py -m compileall -q . -x "(\.git|\.venv|venv|__pycache__|\.cache|\.vscode)"
py -m pytest -q
```

선택적 Peer Snapshot 갱신:

```powershell
py scripts\refresh_reit_peer_snapshot.py
```

위 갱신 스크립트는 앱 시작 시 자동 실행되지 않습니다.

## 6. 리뷰 추천 파일

1. [docs/Reviewer_Guide.md](docs/Reviewer_Guide.md): 3분 리뷰 가이드
2. [docs/V14_Feature_Summary.md](docs/V14_Feature_Summary.md): v14 Tax Workflow Control 기능 요약
3. [docs/Architecture.md](docs/Architecture.md): 앱 구조와 데이터 흐름
4. [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md): 현재 범위와 향후 방향
5. [CHANGELOG.md](CHANGELOG.md): 버전별 변경 이력

핵심 코드 파일:

- `app.py`: Streamlit 진입점 및 화면 orchestration
- `config.py`: 버전, 화면 라벨, endpoint 상수
- `data_source_policy.py`: 자료 출처 taxonomy와 표준 제한 문구
- `calculations_holding_tax_bridge.py`: 보유세 추정 bridge
- `tax_validation.py`: Tax 입력 검증
- `tax_request_mapping.py`: Issue 기반 요청자료 매핑
- `calculations_tax_review_pack.py`: Issue Matrix, 요청자료, 검토 메모 생성
- `tax_data_loader.py`: Tax Snapshot 및 회사별 fallback 데이터 로딩
- `data_availability.py`: 회사별 상세 데이터 가용성 및 분석 범위 판정
- `ui_tax.py`: 보유세 분석 화면

## 7. 버전 관리

현재 버전은 `v14`입니다. 중요 기능이 추가되는 경우 `v15`, `v16`처럼 순차적으로 올립니다.

버전을 변경할 때는 다음 파일을 함께 맞춥니다.

- `VERSION`
- `CHANGELOG.md`
- `config.py`
