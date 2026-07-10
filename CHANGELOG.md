# 변경 이력

## v14 - Tax Workflow Control & Validation (현재)

- source reliability framework 추가: `data_source_policy.py`
- Holding Tax Bridge 추가: 공시가격/장부가액, 과세표준, 추정 보유세, FFO 부담 연결
- Tax 입력 검증 패널 추가: 결측, fallback, 0 denominator, 비정상 비율 확인
- Issue 기반 Tax Request List 매핑 추가
- Tax Review Memo를 6개 섹션 구조로 확장하고 source-specific limitation 문구 반영
- Tax 화면 순서를 source banner, assumptions, Tax Summary, bridge, Issue Matrix, Reconciliation, FFO stress, Request List, Memo, Export, Validation, source/raw expanders로 정리
- Memo Markdown, Issue Matrix CSV, Reconciliation CSV, Request List CSV, ZIP export 추가
- Methodology 페이지에 v14 Tax Workflow Control 구조와 source_type taxonomy 표 추가
- 비-SK 리츠가 SK리츠 상세 자산 데이터를 재사용하지 않는 fallback 구조 유지 및 테스트 보강
- GitHub Actions CI workflow 추가

## v13 - Tax Review Pack Generator

- Tax Issue Matrix 추가
- Holding Tax Reconciliation 추가
- Tax 요청자료 리스트 자동 생성 기능 추가
- Tax Review Memo 초안 생성 기능 추가
- Tax mode 중심 UI 재정렬
- SK리츠 외 상장리츠도 Tax 기능이 작동하도록 Snapshot/API fallback 구조 보완
- 회사별 상세 데이터 가용성을 `data_availability.py`에서 판정하도록 정리
- 비-SK 리츠에 SK리츠 자산 상세자료가 재사용되지 않도록 회사 전체 Snapshot 기반 fallback 명시
- Assurance 화면에 자산·임차인, 차입금 만기·차환, 가치·NAV 회사 단위 proxy 표 추가
- 일반모드 설명 섹션 기본 접힘 처리
- Tax 분석 가정 패널 접근성 개선

## v12 - Peer Benchmark & Red Flag Engine

- 상장리츠 Peer Benchmark 기능 추가
- Assurance Red Flag Engine 추가
- Tax 보유세 부담 Peer Benchmark 추가
- Red Flag별 감사절차, Tax 검토사항, 요청자료 추천 기능 추가
- DART 전체 실시간 호출 대신 Snapshot 기반 데이터 구조 도입
- 공개 리뷰 환경에서 실시간 API 연결이 제한될 경우 예시 데이터로 전환되도록 설계
- 상장리츠를 분석 대상으로 선택한 방법론적 이유를 UI와 문서에 추가
- 사이드바에서 공시 기준일 선택기를 제거하고 시나리오 선택을 우선 배치
- 분석 대상회사 변경 시 Assurance, Tax, Peer Benchmark가 같은 선택 회사 상태로 갱신되도록 개선
- 회사별 상세 자산·보유세 데이터가 부족한 경우 SK리츠 샘플 데이터를 재사용하지 않고 데이터 부족 및 Peer Snapshot 중심 화면으로 표시
- 저장소 문서를 README, Roadmap, Architecture, Reviewer Guide, v12 Feature Summary 중심으로 재구성

## v11 - Tax & Assurance 중심 버전

- Deals 모드를 공개 버전에서 비활성화
- KRX API 의존성을 공개 UI에서 제거
- 화면 구성을 일반 정보 및 시나리오, Assurance: 감사위험 분석, Tax: 보유세 분석, 분석 방법론 및 데이터 출처로 재정리
- 외부 데이터 인증값이 화면에 노출되지 않도록 구조 개선
- 한국어 사용자를 기준으로 UI와 GitHub 문서를 한국어 우선 문장으로 정리
- 향후 버전 업데이트를 위한 단순 버전 관리 기준 추가

## 버전 관리 기준

중요 기능이 추가되는 경우 버전을 v14, v15처럼 순차적으로 올립니다. `VERSION`, `CHANGELOG.md`, `config.py`의 화면 표시 버전을 함께 맞춥니다.
