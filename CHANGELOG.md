# 변경 이력

## v12 - Peer Benchmark & Red Flag Engine

- 상장리츠 Peer Benchmark 기능 추가
- Assurance Red Flag Engine 추가
- Tax 보유세 부담 Peer Benchmark 추가
- Red Flag별 감사절차 및 요청자료 추천 기능 추가
- DART 전체 실시간 호출 대신 Snapshot 기반 데이터 구조 도입
- Deals 및 KRX 비활성화 유지

## v11 - Tax & Assurance 중심 버전

- Deal 모드를 공개 버전에서 비활성화
- KRX API 의존성을 공개 UI에서 제거
- 화면 구성을 일반 정보 및 시나리오, Assurance: 감사위험 분석, Tax: 보유세 분석, 분석 방법론 및 데이터 출처로 재정리
- 특정 회계법인명 또는 채용 목적 문구를 공개 자료에서 제거
- 외부 데이터 인증값이 화면에 노출되지 않도록 보안 구조 개선
- 한국어 사용자를 기준으로 v11 UI와 GitHub 문서를 한국어 우선 문장으로 정리
- 향후 v12, v13 업데이트를 위한 단순 버전 관리 기준 추가

## 버전 관리 기준

중요 기능이 추가되는 경우 버전을 v12, v13처럼 순차적으로 올립니다. `VERSION`, `CHANGELOG.md`, `config.py`의 화면 표시 버전을 함께 맞춥니다.
