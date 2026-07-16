# 변경 이력

## v15.1.0 - AX Workflow & Advisory Portfolio

- 일반 정보 화면 최상단에 고객 Pain Point와 AX Solution, 업무효과 추가
- 공시·세무검토의 As-Is·To-Be Workflow와 역할분담 명시
- 규칙엔진, AI 확장계층, Control Harness와 Human Review의 경계 명확화
- 구현 증빙, 미완료 대사와 전문가 확인 필요사항을 함께 표시
- AX Advisory Case Brief와 Requirements Definition 문서 추가
- Tax·Assurance 계산 로직과 네 가지 공개 모드는 변경하지 않음

## v15.0.1 - SK서린빌딩 핵심 자산 보유세 세무검토

- 「지방회계법」 제55조에 따른 10원 미만 끝수 미계산 기준 반영
- 세목별 끝수 처리 전 산출세액과 끝수 처리 후 재계산액 구분
- SK서린빌딩 보유세 재계산액 및 민감도 분석 갱신
- Tax 화면 사이드바 전체 노란색 배경 제거
- 사용자 화면의 한국어 세법 용어 정비
- 토지분 종합부동산세를 과세대상 제외로 명확화

## v15.0.0 - SK Seorin Golden Asset Tax Case Study

- 공개 Tax 화면의 분석 범위를 SK리츠·SK서린빌딩·2026년 Golden Asset Case Study로 고정
- 다른 리츠, 자산, 납세의무자와 보유구조 선택 UI를 공개 Tax 화면에서 제거
- 공식 입력자료 기반 산식 재계산액 `1,250,710,968.55472원`과 실제 고지세액 미확인 상태를 명확히 구분
- Golden Asset 계산 엔진과 Tax Rule Master를 재사용하는 Base, Moderate, Severe, Custom 민감도 Scenario 추가
- 우선순위와 검증 상태를 기준으로 한 Tax Issue Matrix 추가: P0 Open 3건, P1 Open 3건
- 각 Tax Issue를 Request List의 요청자료와 연결
- Scenario, Issue Matrix와 Request List를 Tax Review Memo, Markdown, HTML과 Excel Export에 반영
- 실제 고지서 확인 전 `verified_notice` 생성을 금지하고 장부가액·Peer fallback을 사용하지 않는 Fail-closed 통제 유지
- 범용 v15 백엔드 스키마와 파이프라인은 향후 공식자료 기반 확장을 위해 유지

## v14.1 - Metric Definition & Source Lineage Stabilization

- General·Assurance 재무지표 정의와 Source lineage 보강
- FFO proxy, 장부기준 NAV proxy, 총자산 기준 차입비율의 범위와 한계 명시
- DART 계정 매핑과 Power BI 검증 구조 안정화

## v14 - Tax Workflow Control & Validation

- 회사 단위 Tax Review Pack, 검증, 요청자료와 Memo 초안 도입
- v15에서 회사 전체 보유세 추정 경로를 공개 Tax 화면에서 대체

## v13 - Tax Review Pack Generator

- Tax Issue Matrix, Reconciliation, Request List와 Memo 생성 기반 도입

## v12 - Peer Benchmark & Red Flag Engine

- 상장리츠 Peer Benchmark와 Assurance Red Flag Engine 도입

## v11 - Tax & Assurance 중심 버전

- 공개 화면을 General, Assurance, Tax, Methodology 네 모드로 정리
- Deals와 KRX API를 공개 런타임에서 비활성화

## 버전 관리 원칙

중요 기능 추가는 `v16`, `v17`처럼 순차 버전으로 관리하고 안정화 변경은 `v15.1`처럼 소수점 버전을 사용합니다. `VERSION`, `config.py`, `CHANGELOG.md`와 공개 문서의 버전을 함께 갱신합니다.
