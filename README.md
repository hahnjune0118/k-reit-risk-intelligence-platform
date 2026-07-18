# K-REIT Risk Intelligence Platform


**현재 버전: v15.1.0 - Decision-First Tax Review**

상장리츠의 공시자료, 거시경제 지표, 자산별 정보와 공시가격 데이터를 연결하여 Assurance 및 Tax 관점의 초기 위험 검토를 지원하는 Streamlit 기반 공개 포트폴리오 프로젝트입니다.

분산된 공시와 보유세 검토자료를 Data·Automation 기반의 검증 가능한 업무 흐름으로 연결하고, 결론·미해결 이슈·계산조서·근거자료를 의사결정 순서에 맞게 제공합니다.

## 프로젝트 개요

DART, ECOS, 리츠 공시와 공시가격 자료는 유용하지만 서로 분리되어 있습니다. 이 프로젝트는 공개자료 수집, 지표 비교, 위험 신호 식별과 검토자료 요청안 작성처럼 반복되는 업무를 구조화합니다.

현재 공개 화면은 다음 네 가지 모드를 제공합니다.

1. **일반 정보 및 시나리오**: 여러 상장리츠의 재무·자산 정보와 거시경제 시나리오 요약
2. **Assurance: 감사위험 분석**: 자산 우선순위, RMM(중요왜곡표시위험), KAM(핵심감사사항)과 감사절차 검토
3. **Tax: 보유세 분석**: 결론, 시나리오, 주요 이슈, 계산조서와 근거자료 중심 보유세 검토
4. **분석 방법론 및 데이터 출처**: 지표 정의, Source lineage, 보안, 한계와 면책사항

Deals 모드와 KRX 기반 시장가치 분석은 현재 공개 버전에서 비활성화되어 있습니다.

## v15.1.0 Decision-First Tax Review

Tax 모듈은 SK리츠의 대표 자산인 SK서린빌딩을 기준 사례로 선정하여 공모리츠 보유세 검토를 자산·필지·납세의무자 단위로 구현했습니다. 공개 화면은 다음 네 탭으로 구성합니다.

1. **결론 및 시나리오**: 재계산액, Evidence Coverage, 고지서 대사 Coverage, P0/P1 이슈와 민감도
2. **주요 이슈 및 요청자료**: 이슈, 필요 증빙, 예상 영향과 다음 조치 통합
3. **계산조서**: 세목별 입력값·세율·재계산액·근거상태·고지서 대사상태
4. **근거 및 다운로드**: Evidence Matrix, Source Lineage, Fail-closed 통제와 결과 내려받기

| 구분 | 공개 범위 |
|---|---|
| 분석대상 리츠 | SK리츠, 종목코드 395400 |
| 분석대상 자산 | SK서린빌딩, `SKR-SEOUL-SEORIN-001` |
| 납세의무자 단위 | `SKR-TP-001` |
| 기준연도 | 2026년 |
| 공식 입력자료 기반 산식 재계산액 | `1,250,710,968.55472원` |
| 화면 표시금액 | 약 12.51억원 |
| 실제 고지세액 | 미확인 |
| 고지서 대사 | 미완료 |

이 결과는 다음과 같이 제한됩니다.

- SK리츠 전체 자산의 총 보유세가 아닙니다.
- 다른 상장리츠에 자동 적용한 확정 계산 결과가 아닙니다.
- 실제 과세관청의 고지세액이 아닙니다.
- 확인된 공식 입력자료와 Tax Rule Master의 표준 산식에 따른 재계산입니다.
- 실제 과세내역서상 분리과세 코드, 법정 절사, 감면, 세부담상한과 지방자치단체 조정은 아직 대사하지 않았습니다.

범용 자산·필지·납세의무자 데이터 스키마와 계산 파이프라인은 향후 확장을 위해 유지하되, 공개 Tax UI는 검증 가능한 SK서린빌딩 사례만 표시합니다.

## Tax Sensitivity Scenario

시나리오는 미래 세액 예측이 아니라 공시가격 및 시가표준액 변동에 대한 기계적 민감도 분석입니다. 토지 개별공시지가와 건축물 시가표준액만 조정하고, 법적 분류, 세율, 공정시장가액비율, 소유지분과 필지면적은 Base와 동일하게 고정합니다. 계산은 Golden Asset 계산 엔진과 Tax Rule Master를 그대로 재사용합니다.

| Scenario | 토지 변동 | 건축물 변동 | 총 보유세 | Base 대비 증감액 |
|---|---:|---:|---:|---:|
| Base | 0% | 0% | 1,250,710,968.55472원 | 0원 |
| Moderate | +5% | +5% | 1,313,250,671.982456원 | 62,539,703.427736원 |
| Severe | +10% | +10% | 1,375,790,375.410192원 | 125,079,406.855472원 |

Custom Scenario는 토지와 건축물 각각 `-10%`부터 `+20%`까지 1% 단위로 검토할 수 있습니다. 소방분 지역자원시설세의 누진구조 때문에 총세액 증감률은 입력 변동률과 정확히 일치하지 않을 수 있습니다.

## Tax Issue Matrix

Tax Issue Matrix는 계산 결과만으로 위험을 확정하지 않고, 검증 상태와 필요한 증빙을 함께 보여주는 초기 Tax Review 도구입니다.

- **P0 Open 3건**: 실제 고지 과세구분, 실제 고지세액, 과세기준일 현재 등기·신탁상태
- **P1 Open 3건**: 토지면적 5.3㎡ 차이, 소방분 위험유형 코드, 법정 절사·감면·세부담상한
- 모든 이슈는 Request List의 기존 요청자료와 연결됩니다.
- Scenario, Issue Matrix와 Request List는 Markdown Memo, HTML과 Excel Export에 함께 포함됩니다.

## 계산 및 통제 구조

```text
Official Input Evidence
  -> Asset / Parcel / Building / Taxpayer Registry
  -> Tax Classification
  -> Tax Rule Master
  -> Statutory Recalculation Detail
  -> Validation / Reconciliation
  -> Tax Sensitivity Scenario
  -> Tax Issue Matrix / Request List
  -> Tax Review Memo and Exports
```

공식 근거가 부족한 값은 장부가액, Peer 비율이나 0으로 대체하지 않습니다. 계산 상태를 `official_source_calculated`, `official_partial`, `manual_review_required`, `data_insufficient` 등으로 구분하고, 실제 고지서 확인 전에는 `verified_notice`로 처리하지 않습니다.

## 데이터 출처

- 리츠정보시스템과 리츠 공식 홈페이지·IR·PDF
- DART 공시문서와 재무자료
- ECOS 거시경제 지표
- V-World 등 공시가격 관련 공식자료
- 국가법령정보센터의 지방세 및 종합부동산세 관련 법령
- `data/v15/*.csv`의 정규화 Snapshot, Source lineage와 검증 상태

공시자료, API 수집자료, Snapshot, 추정값과 미검증 항목을 구분합니다. 모든 값이 감사받은 수치 또는 실제 고지세액이라고 주장하지 않습니다.

## API Key 및 보안

공개 배포 버전은 Streamlit Secrets 또는 환경변수로 서버 측 인증정보를 관리합니다. API Key는 GitHub, 화면, 로그, 디버그 출력과 다운로드 파일에 표시하지 않습니다. 공개 사용자는 별도 인증키를 입력할 필요가 없습니다.

실시간 데이터 연결이 제한되면 검증된 Snapshot을 사용합니다. 다만 공식 입력 근거가 없는 Tax 항목은 예시값으로 채우지 않고 계산을 중단합니다.

## 실행 방법

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

검증 명령:

```powershell
py -m compileall -q .
py -m pytest -q
py -m ruff check .
```

## 검토 문서

- [Business Process Case Brief](docs/BUSINESS_PROCESS_CASE_BRIEF.md)
- [Business Requirements Definition](docs/BUSINESS_REQUIREMENTS_DEFINITION.md)
- [v15 Case Study 사용 가이드](docs/v15/USER_GUIDE.md)
- [Tax 계산 및 시나리오 로직](docs/v15/TAX_LOGIC.md)
- [Golden Asset Evidence Review](docs/v15/golden_asset/GOLDEN_ASSET_TAX_REVIEW.md)
- [Case Study Coverage Report](docs/v15/COVERAGE_REPORT.md)
- [법령 근거](docs/v15/LEGAL_BASIS.md)
- [데이터 사전](docs/v15/DATA_DICTIONARY.md)
- [Source 정책](docs/v15/SOURCE_POLICY.md)
- [검증 정책](docs/v15/VALIDATION_POLICY.md)

## 다음 단계

우선순위는 2026년 실제 재산세·지역자원시설세 고지서, 분리과세 코드가 표시된 과세내역서, 등기부등본과 신탁원부를 확보하여 Golden Asset 재계산액을 대사하는 것입니다. 다른 리츠로의 범위 확대는 동일 수준의 공식 입력자료와 검증 증빙을 확보한 뒤 진행합니다.

본 프로젝트는 공개자료 기반의 초기 Tax Screening 및 Assurance 위험평가 도구이며, 신고세액 산출, 법률해석 또는 과세관청의 결정세액을 대체하지 않습니다.
