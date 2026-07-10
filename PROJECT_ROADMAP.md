# PROJECT ROADMAP

## 현재 위치

현재 활성 개발 및 공개 포트폴리오 버전은 **v14 - Tax Workflow Control & Validation**입니다.

v14는 상장리츠의 공시자료, 거시경제 지표, Peer Snapshot, Tax Snapshot을 연결하여 Tax 업무에서 반복적으로 수행되는 보유세 검토, 요청자료 정리, Memo 초안 작성, 데이터 검증을 하나의 workflow로 안정화한 버전입니다.

## v14 현재 범위

활성 Streamlit 모드는 네 가지입니다.

1. 일반 정보 및 시나리오
2. Tax: 보유세 분석
3. Assurance: 감사위험 분석
4. 분석 방법론 및 데이터 출처

v14의 중심 기능:

- 상장리츠 Peer Benchmark
- Tax 보유세 부담 Benchmark
- Source reliability framework
- Holding Tax Bridge
- Tax Issue Matrix
- Holding Tax Reconciliation
- Issue 기반 Tax Request List
- Tax Review Memo 초안
- Tax 입력 검증 패널
- CSV/Markdown/ZIP export
- Assurance Red Flag Engine 유지
- Snapshot 기반 공개 리뷰 경험

## 공개 버전에서 제외된 범위

다음 기능은 현재 공개 런타임에서 비활성화되어 있습니다.

- Deals mode
- KRX API 기반 시장가격 수집
- KRX 기반 market-implied valuation
- 거래 목적 가치평가

위 기능은 공개 포트폴리오 버전의 시작 경로에서 제외되어 있으며, v14는 Tax workflow의 통제, 검증, source transparency를 우선합니다.

## 다음 후보

향후 버전에서는 다음 항목을 검토할 수 있습니다.

- Tax Snapshot 갱신 프로세스 고도화
- 여러 회계연도 trend 기반 Tax Red Flag
- 공시가격·고지세액 대사 자동화
- 보유세 민감도 분석의 자산별 상세화
- source_type별 데이터 품질 리포트 자동 생성

## 버전 관리 원칙

- 현재 버전은 `VERSION` 파일에 기록합니다.
- 화면 표시 버전은 `config.py`에서 관리합니다.
- 주요 기능 추가 시 `CHANGELOG.md`를 업데이트합니다.
- 공개 UI에서 비활성화된 기능은 앱 시작 경로에 의존하지 않도록 유지합니다.
