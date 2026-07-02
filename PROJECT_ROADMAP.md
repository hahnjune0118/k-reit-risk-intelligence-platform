# PROJECT ROADMAP

## 현재 위치

현재 활성 개발 및 공개 포트폴리오 버전은 **v12 - Peer Benchmark & Red Flag Engine**입니다.

v12는 상장리츠의 공시자료, 거시경제 지표, 자산별 정보, 공시가격 데이터, Peer Snapshot을 연결하여 Assurance와 Tax 업무에서 반복적으로 수행되는 위험 검토를 자동화하는 버전입니다.

## v12 현재 범위

활성 Streamlit 모드는 네 가지입니다.

1. 일반 정보 및 시나리오
2. Assurance: 감사위험 분석
3. Tax: 보유세 분석
4. 분석 방법론 및 데이터 출처

v12의 중심 기능:

- 상장리츠 Peer Benchmark
- Assurance Red Flag Engine
- Tax 보유세 부담 Benchmark
- Red Flag별 감사절차 및 요청자료 추천
- Snapshot 기반 공개 리뷰 경험
- API Key 비노출 보안 구조

## 공개 버전에서 제외된 범위

다음 기능은 현재 공개 런타임에서 비활성화되어 있습니다.

- Deals mode
- KRX API 기반 시장가격 수집
- KRX 기반 market-implied valuation
- 거래 목적 가치평가

위 기능은 삭제 대상이 아니라 향후 별도 모듈 후보입니다. 다만 공개 포트폴리오 버전에서는 Assurance와 Tax workflow의 완성도와 안정성을 우선합니다.

## v13 후보

v13에서는 다음 항목을 검토할 수 있습니다.

- Peer Benchmark Snapshot 갱신 프로세스 고도화
- 여러 회계연도 trend 기반 Red Flag
- Evidence request checklist 내보내기
- 감사계획 메모 초안 자동화
- 보유세 민감도 분석의 자산별 상세화

## v14 이후 후보

v14 이후에는 다음 확장을 별도 모듈로 검토할 수 있습니다.

- 안정화된 KRX 기반 시장가치 비교
- Deals 분석 모드 재도입
- 공시자료와 외부 증빙 문서 간 자동 cross-check
- 내부 검토 메모 및 working paper 자동 생성

## 버전 관리 원칙

- 현재 버전은 `VERSION` 파일에 기록합니다.
- 화면 표시 버전은 `config.py`에서 관리합니다.
- 주요 기능 추가 시 `CHANGELOG.md`를 업데이트합니다.
- 공개 UI에서 비활성화된 기능은 앱 시작 경로에 의존하지 않도록 유지합니다.
