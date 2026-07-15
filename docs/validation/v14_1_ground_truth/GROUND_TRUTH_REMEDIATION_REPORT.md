# v14.1 Ground Truth Remediation Report

## 1. 수정 개요

v14.1 Ground Truth Validation에서 확인된 30개 이슈를 계산 정확성, 데이터 계보, Tax Workflow, Power BI 계약 관점에서 재분류하고 수정했다. P0 4건은 모두 수정했으며, P1은 10건 수정, 3건 부분 수정, 2건 blocked로 처리했다. 고객 내부자료 또는 자산별 공식 원천이 필요한 항목은 수치를 임의 생성하지 않고 'data_insufficient' 및 요청자료로 연결했다.

- fixed: 18건
- partially_fixed: 5건
- blocked: 2건
- deferred_p2: 1건
- deferred_p3: 4건
- false_positive: 0건

## 2. 처리한 P0

| ID | 조치 | 결과 |
|---|---|---|
| P0-01 | 대표 3사의 유동성 차입금을 공식 계정별로 재매핑 | SK 1,243,689.893, 롯데 603,273.620, ESR 156,770.142백만원으로 교정 |
| P0-02 | Snapshot 세액 사용 시 implied effective rate를 표시하고 Bridge를 수학적으로 대사 | 과세표준×적용세율=추정 보유세 검증 통과 |
| P0-03 | 공시가격 상승 규칙을 official_price_growth_5y로 변경 | FFO 비율에 의한 오발생 제거 |
| P0-04 | 합성 5개년 보유세와 60/30/10 세목 배분 제거 | 실제 원자료가 없으면 단일 Snapshot·세목 결측으로 표시 |

## 3. 처리한 P1

- 회사별 실제 보고기간, 재무제표 범위, 연환산 여부와 배수를 저장했다.
- 단일 Snapshot으로 생성하던 가상 5개년 재무·보유세 이력을 제거했다.
- 대표 3사의 실제 DART corp code와 접수번호를 반영하고 예시 회사의 가상 식별자는 비워 두었다.
- FFO proxy를 연환산 영업활동현금흐름으로 단일화하고 영업이익·당기순이익 fallback을 제거했다.
- 차입 구성계정 완전성, 단기금융자산 사용가능성, NAV 총부채 요건을 보수적으로 적용했다.
- Tax model, 세목 범위, 납세의무자 확인 상태와 formula version을 데이터·Memo·Export에 연결했다.
- Tax validation에 세율 대사, 기간 정렬, 납세의무자, 세목 coverage 검사를 추가했다.
- Power BI Peer 중앙값에서 선택 회사 필터를 제거하고 공통 DimPeriod를 모든 Fact에 연결했다.
- Memo를 9개 표준 섹션으로 재구성하고 요청자료를 문서명 단위로 중복 제거했다.

FFO 정식 조정항목, restricted cash 사실관계, 법정 세목별 산식은 공개자료 범위에서 확정할 수 없어 부분 수정으로 분류했다.

## 4. blocked 항목

### P1-10 자산별 공시가격 Ground Truth

대표 회사별 PNU, 주소, 자산명, 연도, API 응답 hash 또는 실제 고지서가 없다. 회사 전체 effective-rate estimate만 예비 분석에 사용하며 자산별 공식 세액으로 표시하지 않는다.

### P1-11 소유·납세·부담 귀속

법적 소유자, 납세의무자, 실제 현금부담자, 임대차상 세부담 전가 여부는 내부 계약과 고지서가 필요하다. 상태 필드와 validation 경고, 요청자료는 구현했지만 사실관계는 'data_insufficient'로 유지한다.

## 5. false positive

없음. 모든 등록 이슈는 수정, 부분 수정, blocked 또는 후속 우선순위로 분류했다.

## 6. 변경한 계산식

| 지표 | 이전 | 변경 |
|---|---|---|
| 유동성 차입금 | 유동부채 또는 불완전 계정 합계 가능 | 단기차입금+유동성 장기차입금 등 검증된 이자부 구성계정 |
| FFO proxy | OCF·영업이익·당기순이익 fallback | 연환산 영업활동현금흐름만 사용 |
| 장부기준 NAV proxy | 총부채 결측 시 총자산-차입금 가능 | 총자산-총부채; 총부채 결측 시 미계산 |
| 순차입금 | 사용제한 미확인 단기금융자산 차감 | 현금만 차감; 명시적 unrestricted 확인 시에만 추가 차감 |
| 총자산 기준 차입비율 | Gross LTV 표시 | 이자부 차입부채/총자산, 담보 LTV가 아님을 명시 |
| Snapshot 보유세 Bridge | 표시 세율과 실제 세액 불일치 | 추정세액/추정 과세표준 implied rate로 대사 |
| Tax fallback | loader와 Bridge의 상이한 가정 | 기준가액×70%×1.1% 중앙 fallback, Snapshot 부재 시에만 적용 |

충당부채는 총부채와 NAV에는 포함하되 이자부 차입부채, 순차입금, 차입비율, 금리충격 분자에서는 제외한다.

## 7. 변경한 데이터 계보

- 핵심 지표별 metric_name, source_type, source_name, source_date, source_note, statement_scope, is_fallback, calculation_method, limitation을 fact_metric_lineage.csv로 제공한다.
- 공식 공시는 official_disclosure, 회사 전체 Tax 추정은 peer_snapshot_estimate, 예시는 sample_estimate, 산출 불가는 data_insufficient로 유지한다.
- sample_snapshot을 API 자료로 승격하지 않는다.
- 재무 기준연도와 공개 분석연도를 분리하고 보고기간·재무제표 범위를 함께 표시한다.
- Power BI 공개 시각화는 raw source_type 대신 한국어 source_label을 사용한다.

## 8. 변경한 UI와 Memo

- Streamlit Tax 화면에 계산 모델, 세율 기준, 세목 범위, 납세의무자·세목 coverage validation을 표시한다.
- 단일 Snapshot만 있을 때 5년 추이 차트를 표시하지 않고 데이터 부족을 안내한다.
- Gross LTV를 총자산 기준 차입비율로 교정했다.
- Memo는 검토 대상, 사실관계, 핵심 수치, 이슈, 세목 근거, 요청자료, 잠정분석, 시사점, 제한의 9개 섹션을 사용한다.
- 신고 목적 확정세액이 아니라 공개자료·Snapshot 기반 예비 추정이라는 제한 문구를 유지한다.

## 9. Power BI 수정

- 11개 UTF-8 BOM CSV, 14개 TMDL table, 51개 Measure를 연결했다.
- DimREIT와 DimPeriod를 중심으로 16개 단방향 관계를 구성했다. Fact-to-Fact와 양방향 관계는 없다.
- 회사·분석연도 Slicer를 세 페이지에 단일 선택으로 두고 각각 공통 sync group으로 연결했다.
- Peer 중앙값은 REMOVEFILTERS(DimREIT)를 적용한다.
- 요청자료 수는 DISTINCTCOUNT(request_item)으로 계산한다.
- Bridge는 숫자 원본과 통화·퍼센트 표시 문자열을 분리했다.
- 자동 제목 대신 분석 목적이 드러나는 명시적 제목을 적용했다.
- Streamlit URL 원문 대신 'Streamlit Tax Review Pack 열기' 동작을 표시한다.
- pExportFolder parameter를 사용하고 사용자 절대경로를 제거했다.
- 기존 3페이지, 회사·연도 Slicer, 선택 Measure, 페이지 제목, Source 시각화를 삭제하지 않고 재사용했다.
- diagramLayout.json과 바이너리 PBIX는 수정하지 않았다.

## 10. 추가·수정 테스트

추가 회귀 테스트는 다음 위험을 고정한다.

- 대표 3사 유동성 차입금과 공식 값 대사
- 합성 재무·세무 이력 금지
- FFO proxy의 OCF 전용 산식과 metadata
- 총부채·차입금·충당부채 분리 및 NAV 요건
- 단기금융자산의 무확인 차감 금지
- 해외자산 국내 보유세 적용 금지
- 공시가격 상승 Red Flag metric
- 요청자료 중복 제거와 9개 섹션 Memo
- CSV grain·단위·비밀정보·회사별 fallback 독립성
- Power BI CSV-TMDL schema, DAX, PBIR 필드, 관계, Slicer sync, 표시값, Page 1·2 base 대사
- 대표 4개 회사 Tax Review Pack acceptance

최종 실행 결과는 compileall 통과, pytest 72건 통과, Power BI export 11개 생성, PBIP 정적 검증 통과다. Streamlit은 8502 포트에서 실제 브라우저 렌더까지 확인했으며 예외가 없었다.

## 11. 대표 회사 Acceptance Test

| 회사 | 재무 범위 | 핵심 결과 | Tax 처리 | 상태 |
|---|---|---|---|---|
| SK리츠 | 2026-03-31 CFS, 3개월×4 | 총자산 5,408,832.249; 총부채 3,382,988.685; 차입금 3,103,854.821백만원 | 추정 보유세 29,500백만원, 보유세/FFO proxy 17.91% | 통과 |
| 롯데리츠 | 2025-12-31 OFS, 6개월×2 | 총자산 2,594,407.042; 총부채 1,454,908.461; 차입금 1,307,019.778백만원 | 추정 보유세 15,800백만원, 보유세/FFO proxy 12.34% | 통과 |
| ESR켄달스퀘어리츠 | 2025-11-30 CFS, 6개월×2 | 총자산 2,835,773.540; 총부채 1,670,571.944; 차입금 1,586,961.428백만원 | 추정 보유세 18,600백만원, 보유세/FFO proxy 105.25% | 통과 |
| 제이알글로벌리츠 | 2026 Sample estimate | 총부채·현금은 데이터 부족, 타 회사 값 미사용 | 해외자산에 국내 보유세 미적용, data_insufficient | 통과 |

회사명·종목코드·연도·재무지표·Issue Matrix·Request List·Memo·계보·Export와 비-SK 데이터 오사용 여부를 자동 검사했다.

## 12. 잔여 위험

- 공개자료만으로 정식 FFO 조정항목을 완성할 수 없다.
- 자산별 PNU, 법적 소유자, 납세의무자, 실제 고지세액과 세목 구성이 없다.
- Tax 계산은 statutory calculation이 아니라 회사 전체 effective-rate screening이다.
- Snapshot 회사 간 결산기와 재무제표 범위가 다르므로 단순 비교에 주의해야 한다.
- Power BI Desktop 실제 새로고침·렌더링은 로컬 Desktop에서 최종 확인하는 것이 바람직하다.
- pExportFolder는 실행 환경에 맞는 경로 parameter 설정이 필요하다.

## 13. 제출 가능성 평가

계산식, 추정·공시 구분, 회사별 fallback 독립성, Source lineage, 요청자료·Memo 연결은 공개 포트폴리오 검토에 사용할 수 있는 수준으로 안정화되었다. 다만 본 결과는 신고 목적 확정 세액, 법률의견 또는 감사조서를 대체하지 않으며 blocked 항목은 원자료 확보 전 수치 결론에 사용해서는 안 된다.

## 14. Git diff 요약

주요 변경 범위는 다음과 같다.

- 계산·데이터: DART mapping, FFO/NAV/debt, Tax loader·Bridge·validation, Red Flag, Request/Memo
- Snapshot: REIT master, Peer, Tax 데이터 및 재현 생성 스크립트
- Export: 11개 Power BI CSV와 metric lineage·period dimension
- Power BI: TMDL table·Measure·관계, PBIR 3페이지, 정적 validator·normalizer
- 테스트: Ground Truth, Export, Power BI contract, 대표회사 acceptance
- 문서: remediation register, 본 보고서, 방법론·README 명칭 정합화

원본 GROUND_TRUTH_VALIDATION_REPORT.md와 issue register는 삭제하지 않았다.
