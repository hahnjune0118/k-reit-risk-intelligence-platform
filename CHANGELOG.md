# 변경 이력

## v12 - Peer Benchmark & Red Flag Engine

- v12를 현재 활성 개발 및 공개 포트폴리오 버전으로 정리
- 상장리츠 Peer Benchmark 기능 추가
- Assurance Red Flag Engine 추가
- Tax 보유세 부담 Peer Benchmark 추가
- Red Flag별 감사절차, Tax 검토사항, 요청자료 추천 기능 추가
- DART 전체 실시간 호출 대신 Snapshot 기반 데이터 구조 도입
- 공개 리뷰 환경에서 실시간 API 연결이 제한될 경우 예시 데이터로 전환되도록 설계
- 상장리츠를 분석 대상으로 선택한 방법론적 이유를 UI와 문서에 추가
- 사이드바에서 공시 기준일 선택기를 제거하고 시나리오 선택을 우선 배치
- 사이드바 workflow를 분석 모드, 분석 대상회사, 시나리오, 데이터 연결 상태 순서로 정리
- 분석 대상회사를 시가총액 순위 Snapshot 기준으로 정렬하고 종목코드/DART corp_code를 자동 연결
- 최근 5년 흐름을 금리와 재무지표의 실제값 표로 표시하도록 개선
- Assurance와 Tax Red Flag 표시를 단일 실무형 요청자료 표로 통합
- Deals 및 KRX 기반 시장가치 분석 비활성화 유지
- 저장소 문서를 README, Roadmap, Architecture, Reviewer Guide, v12 Feature Summary 중심으로 재구성

## v11 - Tax & Assurance 중심 버전

- Deals 모드를 공개 버전에서 비활성화
- KRX API 의존성을 공개 UI에서 제거
- 화면 구성을 일반 정보 및 시나리오, Assurance: 감사위험 분석, Tax: 보유세 분석, 분석 방법론 및 데이터 출처로 재정리
- 특정 회사명 또는 채용 목적 문구를 공개 자료에서 제거
- 외부 데이터 인증값이 화면에 노출되지 않도록 보안 구조 개선
- 한국어 사용자를 기준으로 UI와 GitHub 문서를 한국어 우선 문장으로 정리
- 향후 버전 업데이트를 위한 단순 버전 관리 기준 추가

## 버전 관리 기준

중요 기능이 추가되는 경우 버전을 v13, v14처럼 순차적으로 올립니다. `VERSION`, `CHANGELOG.md`, `config.py`의 화면 표시 버전을 함께 맞춥니다.
