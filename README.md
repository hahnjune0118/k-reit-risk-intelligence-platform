# K-REIT Risk Intelligence Platform


**현재 버전: v15.1.0 - Decision-First Tax Review**

상장리츠의 공시자료, 거시경제 지표, 자산별 정보와 공시가격 데이터를 연결하여 Assurance 및 Tax 관점의 초기 위험 검토를 지원하는 공개 포트폴리오 프로젝트입니다. 기존 Streamlit 앱과 Golden Asset 감사 검토에 집중한 Marimo Assurance 앱을 병행합니다.

분산된 공시와 보유세 검토자료를 Data·Automation 기반의 검증 가능한 업무 흐름으로 연결하고, 결론·미해결 이슈·계산조서·근거자료를 의사결정 순서에 맞게 제공합니다.

## 프로젝트 개요

DART, ECOS, 리츠 공시와 공시가격 자료는 유용하지만 서로 분리되어 있습니다. 이 프로젝트는 공개자료 수집, 지표 비교, 위험 신호 식별과 검토자료 요청안 작성처럼 반복되는 업무를 구조화합니다.

기존 Streamlit 공개 화면은 다음 네 가지 모드를 제공합니다.

1. **일반 정보 및 시나리오**: 여러 상장리츠의 재무·자산 정보와 거시경제 시나리오 요약
2. **Assurance: 감사위험 분석**: 자산 우선순위, RMM(중요왜곡표시위험), KAM(핵심감사사항)과 감사절차 검토
3. **Tax: 보유세 분석**: 결론, 시나리오, 주요 이슈, 계산조서와 근거자료 중심 보유세 검토
4. **분석 방법론 및 데이터 출처**: 지표 정의, Source lineage, 보안, 한계와 면책사항

Deals 모드와 KRX 기반 시장가치 분석은 현재 공개 버전에서 비활성화되어 있습니다.

## 앱 구성: Streamlit와 Marimo

두 앱은 대체 관계가 아니라 목적이 다른 병행 진입점입니다. 기존 계산 모듈과 검증된 `data/v15` Snapshot을 공유하므로 UI가 달라도 Golden Asset의 산식과 회귀 기준값은 같아야 합니다.

| 앱 | 진입 파일 | 역할 |
|---|---|---|
| Streamlit | `app.py` | 기존 네 가지 모드, 다중 리츠 탐색과 공개 앱 호환성 유지 |
| Marimo Assurance | `k_reits_marimo.py` | SK리츠·SK서린빌딩 2026년 Case를 감사 증거, 재수행, 대사와 검토자 결론 순서로 제시 |

기존 Streamlit 공개 앱: [K-REIT Risk Intelligence Platform](https://hahnjune0118-k-reit-risk-intelligence-platform-app.streamlit.app/)

Marimo Assurance 앱은 다음 세 페이지로 구성합니다.

1. **Executive Review**: Audit Question, Related Accounts, Relevant Assertions, RMM, 재수행액 약 12.51억원, Evidence Coverage, 고지서 대사 Coverage, P0/P1 이슈와 현재 결론
2. **Evidence Testing & Reperformance**: IPE 완전성·정확성, Source lineage, 자산–필지–납세의무자–세목 연결, 계산조서, Tax Rule Master, Base/Moderate/Severe/Custom Scenario와 Fail-closed 상태
3. **Reconciliation & Reviewer Conclusion**: 모델과 실제 고지세액의 대사 구조, Issue Matrix, 요청자료와 Exception Follow-up, Reviewer Conclusion, 미해결 Evidence Gap과 export

Streamlit의 `session_state`와 전역 rerun을 복제하지 않습니다. Marimo widget 값과 계산 셀 사이의 reactive dependency를 사용하며, Custom Scenario 입력이 바뀌면 Snapshot 로드 셀은 유지되고 view model과 이에 의존하는 표·차트·페이지 출력이 갱신됩니다. 상세 설계와 상태관리 매핑은 [Marimo Migration Guide](docs/MARIMO_MIGRATION.md)를 참고하십시오.

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
- `data/v15/*.csv`와 `data/v15/golden_asset/*.json`의 정규화 Snapshot, Source lineage와 검증 상태

공시자료, API 수집자료, Snapshot, 추정값과 미검증 항목을 구분합니다. 모든 값이 감사받은 수치 또는 실제 고지세액이라고 주장하지 않습니다.

## API Key 및 보안

공개 배포 버전은 Streamlit Secrets 또는 환경변수로 서버 측 인증정보를 관리합니다. API Key는 GitHub, 화면, 로그, 디버그 출력과 다운로드 파일에 표시하지 않습니다. 공개 사용자는 별도 인증키를 입력할 필요가 없습니다.

기존 Streamlit 연결은 `ECOS_API_KEY`, `DART_API_KEY`, `KRX_API_KEY`, `REALTY_PRICE_API_KEY`를 사용할 수 있습니다. Marimo Golden Asset 경로는 현재 실시간 API를 호출하지 않고 저장소의 `data/v15` Snapshot을 기본 데이터이자 fallback으로 사용하므로 API 키 없이 실행됩니다.

실시간 데이터 연결이 제한되면 검증된 Snapshot을 사용합니다. 다만 공식 입력 근거가 없는 Tax 항목은 예시값, 장부가액, Peer 비율 또는 0으로 채우지 않고 `data_insufficient` 또는 `manual_review_required` 상태로 계산을 중단합니다. 향후 Marimo에 live refresh를 연결하더라도 키는 배포 secret 또는 서버 환경변수로만 주입해야 합니다.

Marimo Snapshot 로더는 핵심 v15 파일의 정규화 bundle digest, Golden Asset JSON↔CSV 사실, 저장 계산조서↔Tax 엔진 재수행 결과를 대사합니다. `data/v15`를 갱신할 때는 근거와 회귀값을 검토한 후에만 trust anchor를 함께 갱신하십시오. 자세한 절차는 [Marimo Migration Guide](docs/MARIMO_MIGRATION.md)를 따릅니다.

## 실행 방법

저장소 루트에서 공통 의존성을 설치합니다.

```powershell
py -m pip install -r requirements.txt
```

Streamlit 앱:

```powershell
py -m streamlit run app.py
```

Marimo Assurance 앱은 별도 API 키나 Snapshot flag 없이 커밋된 `data/v15`를 사용합니다.

```powershell
py -m marimo run k_reits_marimo.py
```

개발용 편집 UI:

```powershell
py -m marimo edit k_reits_marimo.py
```

Windows의 `py` launcher를 사용하지 않는 환경에서는 같은 명령의 `py`를 `python`으로 바꾸면 됩니다. 로컬 모듈, CSS와 Snapshot 상대경로를 찾을 수 있도록 저장소 루트에서 실행하십시오.

## 검증 명령

```powershell
py -m compileall -q .
py -m pytest -q
py -m ruff check k_reits_marimo.py marimo_assurance.py marimo_ui.py tests/test_marimo_assurance.py tests/test_marimo_ui.py
py -m marimo check --strict k_reits_marimo.py
py -m pytest -q tests/test_marimo_assurance.py
```

마지막 smoke test로 `py -m marimo run k_reits_marimo.py`와 `py -m streamlit run app.py`를 각각 실행하여 Marimo 세 페이지, Custom Scenario 반응과 기존 Streamlit 시작을 확인합니다.

## Marimo 알려진 한계

- Marimo 공개 범위는 SK리츠·SK서린빌딩·2026년 Golden Asset 한 건이며 Streamlit의 General 및 전체 리츠 비교 기능을 복제하지 않습니다.
- 공식 입력 Evidence 5/5는 실제 고지서 대사 또는 법적 결론의 완결성을 뜻하지 않습니다. 실제 고지세액과 분리과세 코드가 없어 상태는 `Not reconciled`입니다.
- 법정 절사, 감면, 세부담상한, 지방자치단체 조정과 실제 소방분 과세코드는 아직 반영·대사하지 않았습니다.
- Marimo 앱의 live API refresh는 현재 구현 범위가 아니며 데이터 최신성은 커밋된 Snapshot에 좌우됩니다.
- 넓은 감사 표는 작은 화면에서 가로 스크롤을 사용합니다. 브라우저 전용 WASM 배포는 로컬 모듈, Snapshot과 Excel export 호환성을 별도로 검증해야 합니다.
- Molab 세션은 최대 12시간이며 90분 유휴 시 종료될 수 있으므로 장기 실행 서비스나 영구 저장소를 대신하지 않습니다.

## Molab 배포 준비

Molab 배포에는 notebook 진입 파일뿐 아니라 다음 저장소 상대경로가 함께 필요합니다.

- `k_reits_marimo.py`, `marimo_assurance.py`, `marimo_ui.py`, `marimo_styles.css`
- `src/__init__.py`, `src/tax_v15/**`
- `data/v15/*.csv`, `data/v15/golden_asset/*.json`

Python 3.10 이상이 필요합니다. 패키지는 `marimo==0.24.0`, `pandas>=2.3`, `plotly>=6.0`, `openpyxl>=3.1`이며 모두 `requirements.txt`와 `k_reits_marimo.py`의 PEP 723 inline metadata에 기록되어 있습니다. 의존성을 변경할 때는 두 목록을 함께 갱신하거나 `marimo edit --sandbox k_reits_marimo.py`로 metadata를 관리하십시오.

GitHub notebook URL은 `https://molab.marimo.io/github/hahnjune0118/k-reit-risk-intelligence-platform/blob/<branch>/k_reits_marimo.py` 형식으로 열 수 있습니다. 공식 Molab 문서에 따르면 GitHub에서 notebook을 열 때 같은 저장소의 파일이 notebook에 제공되므로 helper, CSS, `src/tax_v15`와 `data/v15`를 동일 branch와 위 상대경로로 커밋해야 합니다. 다만 이 앱의 package 설치, CSS·Snapshot 경로, Excel export에 대한 Molab/WASM 실제 실행은 별도로 smoke test해야 합니다. 현재 상태는 Molab-ready 배포본이 아니라 배포 준비본입니다. Molab notebook은 공개될 수 있으므로 API 키나 `.streamlit/secrets.toml`을 업로드하지 마십시오.

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
- [Streamlit → Marimo 전환 가이드](docs/MARIMO_MIGRATION.md)

## 다음 단계

우선순위는 2026년 실제 재산세·지역자원시설세 고지서, 분리과세 코드가 표시된 과세내역서, 등기부등본과 신탁원부를 확보하여 Golden Asset 재계산액을 대사하는 것입니다. 다른 리츠로의 범위 확대는 동일 수준의 공식 입력자료와 검증 증빙을 확보한 뒤 진행합니다.

본 프로젝트는 공개자료 기반의 초기 Tax Screening 및 Assurance 위험평가 도구이며, 신고세액 산출, 법률해석 또는 과세관청의 결정세액을 대체하지 않습니다.
