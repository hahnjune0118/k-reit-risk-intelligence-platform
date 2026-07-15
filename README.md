# K-REITs Risk Intelligence Platform

상장리츠의 공시자료, 거시경제 지표, 자산별 정보와 공시가격 데이터를 연결해 Assurance 및 Tax 관점의 초기 위험평가를 지원하는 Streamlit 기반 공개 포트폴리오 프로젝트입니다.

**현재 버전: v15.0.0 - Asset & Taxpayer-Level Holding Tax**

## 1. 해결하려는 문제

DART, ECOS, 리츠정보시스템, 각 리츠 홈페이지와 공시가격 자료는 유용하지만 서로 분리되어 있습니다. 실무 검토자는 자산 목록, 소유구조, 필지, 과세구분과 법정 세율을 반복해서 연결해야 하며, 공개자료만으로 확인되지 않는 항목도 많습니다.

v15는 보유세 검토의 Grain을 회사 전체 추정치에서 **자산·납세의무자·필지·건축물** 단위로 전환했습니다. 공식 근거가 없는 값은 장부가액, Peer 비율 또는 0으로 대체하지 않고 검토 필요 상태로 차단합니다.

## 2. 활성 화면

1. **일반 정보 및 시나리오**: 재무·자산 정보, 거시경제 Scenario와 위험 요약
2. **Assurance: 감사위험 분석**: 자산 우선순위, RMM, KAM, 통제 및 감사절차
3. **Tax: 보유세 분석**: 자산·납세의무자 단위 세목별 계산, 검증, 요청자료와 Memo
4. **분석 방법론 및 데이터 출처**: 지표 정의, Source lineage, v15 Fail-closed 정책과 한계

Deals 모드와 KRX 기반 시장가치 분석은 공개 런타임에서 비활성화되어 있습니다.

## 3. v15 Tax 검토 구조

```text
REIT Inventory
  -> Asset Registry
  -> Legal Owner / Taxpayer
  -> Parcel / PNU and Building
  -> Official Tax Base
  -> Tax Classification
  -> Tax Calculation Detail
  -> Validation / Reconciliation
  -> Request List
  -> Tax Review Memo
```

주요 구현 범위:

- 공식 리츠정보시스템 기반 상장리츠 목록과 Coverage Manifest
- 자산·필지·건축물·납세의무자 데이터 스키마
- 과세연도·법령·조문·시행기간·공식 URL을 보존하는 Tax Rule Master
- 토지·건축물 재산세, 도시지역분, 지방교육세, 소방분 지역자원시설세 계산
- 분리과세 토지의 종합부동산세 제외 및 종합·별도합산 토지의 전국 합산 검증 통제
- 농어촌특별세 계산, 고지서 대사 구조, 누락자료별 Request List
- CSV, Excel, Markdown Memo와 HTML 검토문서 다운로드

## 4. Fail-closed 정책

계산 결과는 다음 상태 중 하나로 관리합니다.

| 상태 | 화면 표시 | 의미 |
|---|---|---|
| `verified_notice` | 고지서 확인 | 실제 고지서·과세내역서 확인 |
| `official_source_calculated` | 공식자료 계산 | 공식 입력값과 검증된 규칙으로 계산 |
| `official_partial` | 공식자료 일부 | 일부 핵심 근거만 확보 |
| `manual_review_required` | 수동 검토 | 법적 분류 또는 핵심 판단 필요 |
| `data_insufficient` | 데이터 부족 | 계산 필수자료 부족 |
| `not_applicable` | 해당 없음 | 검증된 분류상 해당 세목 비적용 |

분리과세, 납세의무자, PNU, 개별공시지가, 건축물 시가표준액, 도시지역분과 소방분 요건이 불명확하면 세액을 표시하지 않습니다.

## 5. 현재 데이터 Coverage

2026-07-15 실행 Snapshot 기준으로 공식 상장리츠 목록 23개를 수집했습니다. 공식 홈페이지에서 실제 자산 주소를 식별한 범위는 ESR켄달스퀘어리츠 21개 물류자산입니다.

PNU, 개별공시지가, 건축물 시가표준액, 법적 납세의무자와 분리과세 판정은 아직 공식 증빙이 확보되지 않아 계산에서 차단했습니다. 상세 현황은 [Coverage Report](docs/v15/COVERAGE_REPORT.md)에서 확인할 수 있습니다.

## 6. 데이터 출처

- 리츠정보시스템: 상장리츠 공식 목록
- 각 리츠 공식 홈페이지·IR·PDF: 자산, 주소와 소유구조 근거
- DART: 재무제표와 공시문서
- ECOS: 거시경제 지표와 금리 시계열
- V-World 등 공식 공시가격 데이터: PNU와 개별공시지가
- 국가법령정보센터: 지방세법, 종합부동산세법과 관련 시행령
- `data/v15/*.csv`: 정규화된 Snapshot, Source lineage와 검토 상태

공시자료, API 수집자료, 계산값과 미검증 항목을 구분하며 모든 값이 감사받은 수치라고 주장하지 않습니다.

## 7. API Key 및 보안

공개 배포 버전은 Streamlit Secrets 또는 환경변수로 서버 측 인증값을 관리합니다. 인증값은 GitHub, 화면, 로그, 디버그 출력과 다운로드 파일에 표시하지 않습니다. 공개 리뷰어는 별도 인증값을 입력할 필요가 없습니다.

실시간 호출이 제한되면 검증된 Snapshot을 사용하며, 공식 입력값이 없는 v15 Tax 항목은 예시값으로 대체하지 않고 `data_insufficient`로 표시합니다.

## 8. 실행 방법

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

v15 전체 파이프라인:

```powershell
py -m scripts.v15.run_pipeline --tax-year 2026 --all-reits --no-resume
```

오프라인 Snapshot 재검증:

```powershell
py -m scripts.v15.run_pipeline --tax-year 2026 --all-reits --offline
```

특정 리츠 재실행:

```powershell
py -m scripts.v15.run_pipeline --tax-year 2026 --reit-code 365550 --refresh-sources
```

품질 확인:

```powershell
py -m pytest -q
py -m ruff check .
py -m compileall -q . -x "(\.git|\.venv|venv|__pycache__|\.cache|\.vscode)"
```

## 9. 검토 시작점

- [v15 사용자 가이드](docs/v15/USER_GUIDE.md)
- [Tax 계산 로직](docs/v15/TAX_LOGIC.md)
- [법령 근거](docs/v15/LEGAL_BASIS.md)
- [데이터 사전](docs/v15/DATA_DICTIONARY.md)
- [Source 정책](docs/v15/SOURCE_POLICY.md)
- [검증 정책](docs/v15/VALIDATION_POLICY.md)
- [v14에서 v15로의 전환](docs/v15/MIGRATION_V14_TO_V15.md)
- [Architecture](docs/Architecture.md)

## 10. 한계와 다음 단계

현재 공개 Snapshot은 전체 상장리츠의 자산·필지·고지세액 검증을 완료한 데이터베이스가 아닙니다. 다음 단계는 각 리츠의 최신 투자보고서와 DART 문서 수집, 자산별 등기·신탁자료, 전체 PNU, 기준연도 개별공시지가, 건축물 시가표준액과 실제 고지서 확보입니다.

본 프로젝트는 공개자료 기반 초기 Tax Screening 및 Assurance 위험평가 도구이며 공식 신고세액, 법률의견 또는 투자 판단의 확정 근거가 아닙니다.
