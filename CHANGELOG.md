# 변경 이력

## v15.0.0 - Asset & Taxpayer-Level Holding Tax

- Tax 계산 Grain을 회사 전체 추정에서 자산·납세의무자·필지·건축물 단위로 전환
- 장부가액 기반 공시가격 추정과 Peer 실효세율 기반 보유세 fallback을 v15 활성 경로에서 제거
- 공식 출처가 없는 값의 계산을 차단하는 Fail-closed 상태 체계 도입
- 상장리츠 Master, Coverage Manifest, Source Document Manifest와 Asset Registry 도입
- Tax Rule Master 기반 토지·건축물 재산세와 부가세목 계산 엔진 구현
- 공모리츠 분리과세 요건, 신탁 납세의무자와 납세의무자별 전국 합산 검증 구조 도입
- 14단계 문서형 Tax UI, Source Badge, Request List와 17개 섹션 Tax Review Memo 구현
- CSV·Excel·Markdown·HTML 다운로드와 재현 가능한 v15 파이프라인 추가
- 20개 필수 계산·통제 시나리오 및 Golden Test 추가

## v14.1 - Metric Definition & Source Lineage Stabilization

- General·Assurance 재무지표의 정의와 Source lineage 보강
- FFO proxy, 장부기준 NAV proxy, 총자산 기준 차입비율의 범위와 한계 명시
- DART 계정 매핑과 Power BI 검증 구조 안정화

## v14 - Tax Workflow Control & Validation

- 회사 단위 Tax Review Pack, 검증, 요청자료와 Memo 초안 도입
- v15에서 회사 전체 보유세 추정 경로는 활성 Tax 런타임에서 대체됨

## v13 - Tax Review Pack Generator

- Tax Issue Matrix, Reconciliation, Request List와 Memo 생성 기능 도입

## v12 - Peer Benchmark & Red Flag Engine

- 상장리츠 Peer Benchmark와 Assurance Red Flag Engine 도입

## v11 - Tax & Assurance 중심 버전

- 공개 화면을 General, Assurance, Tax, Methodology 네 모드로 정리
- Deals와 KRX API를 공개 런타임에서 비활성화

## 버전 관리 원칙

중요 기능 추가는 `v16`, `v17`처럼 순차 버전으로 관리하고, 안정화 변경은 `v15.1`처럼 소수점 버전을 사용합니다. `VERSION`, `config.py`, `CHANGELOG.md`와 공개 문서의 버전을 함께 갱신합니다.
