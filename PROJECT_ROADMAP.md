# PROJECT ROADMAP

## 현재 릴리스

현재 공개 포트폴리오 버전은 **v15.0.1 - SK서린빌딩 핵심 자산 보유세 세무검토**입니다.

공개 Tax UI는 SK리츠의 SK서린빌딩 한 건을 대상으로 주소, PNU, 공식 시가표준액, 신탁구조와 납세의무자를 연결하여 보유세 표준 산식을 재계산합니다. 범용 Asset·Parcel·Building·Taxpayer 스키마는 유지하지만, 증빙 수준이 동일하지 않은 다른 리츠 결과는 공개 화면에 표시하지 않습니다.

## v15.0.0 완료 범위

- SK리츠·SK서린빌딩·2026년 Case Scope 고정
- 공식 입력자료 기반 보유세 산식 재계산
- Tax Rule Master 기반 토지·건축물·부가세목 계산
- Base, Moderate, Severe, Custom Tax Sensitivity Scenario
- P0/P1 우선순위 기반 Tax Issue Matrix
- Validation, Reconciliation과 Request List 연결
- 17단계 Tax Review 화면과 Markdown·HTML·Excel Export
- 실제 고지세액 미확인, 고지서 대사 미완료 상태의 Fail-closed 표시

General, Assurance와 Methodology 화면은 기존 다회사 기능을 유지합니다. Deals와 KRX API는 공개 런타임에서 계속 비활성화합니다.

## v15.x 안정화 후보

- 2026년 실제 재산세·지역자원시설세 고지서 확보 및 재계산액 대사
- 분리과세 코드가 표시된 과세내역서로 실제 과세구분 검증
- 과세기준일 현재 등기부등본·신탁원부로 납세의무자 판정 검증
- 토지대장·부속지번 자료로 5.3㎡ 면적 차이 해소
- 소방분 실제 위험유형 코드와 300% 배율 대사
- 법정 절사, 감면, 세부담상한과 지방자치단체 조정 반영 검토

## v16 확장 조건

다른 자산 또는 리츠로 확대하기 전 다음 조건을 충족해야 합니다.

1. 자산과 필지별 공식 주소·PNU 증빙 확보
2. 기준연도 개별공시지가와 건축물 시가표준액 확보
3. 법적 소유자, 신탁구조와 납세의무자 검증
4. 분리과세 등 법적 분류에 대한 검토 근거 확보
5. 실제 고지서 또는 과세내역서와의 Reconciliation 수행
6. Golden Asset과 동일한 자동 테스트와 Evidence Review 통과

## 버전 관리 원칙

- 현재 버전은 `VERSION`과 `config.py`에서 관리합니다.
- 기능, 데이터 계약과 공개 범위 변경은 `CHANGELOG.md`에 기록합니다.
- 증빙이 부족한 항목은 완료로 표시하지 않고 `docs/v15/COVERAGE_REPORT.md`에 제한사항을 남깁니다.
- main 병합과 운영 배포는 별도 Release 검토 후 수행합니다.
