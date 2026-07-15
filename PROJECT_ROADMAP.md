# PROJECT ROADMAP

## 현재 위치

현재 활성 개발 및 공개 포트폴리오 버전은 **v15.0.0 - Asset & Taxpayer-Level Holding Tax**입니다.

v15는 보유세 검토를 회사 전체 추정치에서 자산·납세의무자·필지·건축물 단위로 전환하고, 공식 근거가 없는 숫자를 차단하는 Tax Technology 통제 구조를 구현합니다.

## 현재 범위

- 공식 상장리츠 목록과 리츠별 Coverage Manifest
- 공식 홈페이지·IR·PDF Source Manifest
- Asset, Parcel, Building, Taxpayer Registry
- 공식 법령 기반 Tax Rule Master
- 토지·건축물 재산세와 부가세목 계산
- 분리과세 토지의 종부세 제외 및 전국 합산 검증 통제
- Validation, Reconciliation, Request List와 Tax Review Memo
- 14단계 문서형 Streamlit Tax UI와 검토팩 다운로드

General, Assurance와 Methodology 화면은 유지합니다. Deals와 KRX API는 공개 런타임에서 비활성화되어 있습니다.

## 다음 후보

### v15.x 안정화

- 전체 상장리츠 DART 고유번호와 최신 투자보고서 수집 Coverage 확대
- 자산별 법적 소유자·신탁관계·PNU 검증
- 기준연도 개별공시지가와 건축물 시가표준액 Snapshot 확대
- 실제 고지서 기반 Golden Dataset과 Reconciliation
- OCR 런타임과 PDF 표 추출 정확도 개선

### v16 후보

- 검토자 승인 Workflow와 변경 이력
- 과세연도별 법령 Diff와 Rule Master 승인 절차
- 자산 매입·매각에 따른 기간별 보유세 Bridge
- Power BI용 v15 Asset/Taxpayer 모델 Export

## 버전 관리 원칙

- 현재 버전은 `VERSION`과 `config.py`에서 관리합니다.
- 기능과 데이터 계약 변경은 `CHANGELOG.md`에 기록합니다.
- Coverage가 부족한 항목은 완료로 표시하지 않고 `docs/v15/COVERAGE_REPORT.md`에 차단사유를 남깁니다.
