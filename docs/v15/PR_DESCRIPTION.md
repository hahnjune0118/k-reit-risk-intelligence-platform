## Summary

v15 공개 Tax 기능을 여러 상장리츠의 미완성 범용 계산 화면이 아니라 **SK리츠·SK서린빌딩 2026년 Golden Asset Tax Case Study**로 최종 정리했습니다.

## Scope

- Tax UI 범위: SK리츠, SK서린빌딩, 2026년
- 자산 ID: `SKR-SEOUL-SEORIN-001`
- 납세의무자 ID: `SKR-TP-001`
- 공식 입력자료 기반 보유세 산식 재계산액: `1,250,710,968.55472원`
- 화면 표시: 약 `12.51억원`
- 실제 고지세액: 미확인
- 고지서 Reconciliation: 미완료

SK리츠 전체 자산의 총 보유세 또는 다른 리츠의 확정 계산 결과가 아닙니다. 범용 Backend와 CSV schema는 향후 확장을 위해 유지하되, 공개 Tax 화면에는 검증 가능한 Golden Asset만 표시합니다.

## Changes

- 다른 리츠·자산·납세의무자 선택 UI 제거
- 17단계 Golden Asset Tax Review 흐름 적용
- 기존 계산 엔진과 Tax Rule Master를 재사용하는 Tax Sensitivity Scenario 구현
- Base 0%, Moderate +5%, Severe +10%, Custom -10%부터 +20% 구현
- P0 Open 3건, P1 Open 3건의 Tax Issue Matrix 구현
- 각 Issue를 기존 Request List와 연결
- Scenario와 Issue Matrix를 Tax Review Memo, Markdown, HTML과 Excel Export에 반영
- 실제 고지서 확인 전 `verified_notice` 자동 생성 금지
- 장부가액 및 Peer fallback 미사용 통제 유지
- 공개 문서와 Coverage 설명을 Golden Asset Case Study 범위로 정리

## Scenario Results

| Scenario | 총 보유세 | Base 대비 증감액 |
|---|---:|---:|
| Base | 1,250,710,968.55472원 | 0원 |
| Moderate | 1,313,250,671.982456원 | 62,539,703.427736원 |
| Severe | 1,375,790,375.410192원 | 125,079,406.855472원 |

Scenario는 미래 세액 예측이 아니라 공시가격 및 시가표준액 변화에 대한 기계적 민감도 분석입니다.

## Open Tax Issues

- P0: 실제 고지 과세구분 미확인
- P0: 실제 고지세액 미대사
- P0: 과세기준일 현재 등기·신탁상태 미확인
- P1: 토지면적 5.3㎡ 차이
- P1: 소방분 실제 위험유형 코드 미대사
- P1: 법정 절사·감면·세부담상한 미반영

## Validation

- `py -m compileall -q .`: 통과
- `py -m pytest -q`: 127 passed
- `py -m ruff check .`: 통과
- Streamlit headless smoke test: 통과
- 로컬 Tax UI 검증: 요구 문구 표시, 다른 리츠 선택 UI 없음, visible combobox 0개

이 PR은 Draft 상태를 유지합니다. main 병합과 운영 Streamlit 배포는 수행하지 않았습니다.
