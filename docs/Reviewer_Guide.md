# 3분 리뷰 가이드

## 1분: 문제와 설계

[README](../README.md)의 해결하려는 문제와 v15 Tax 검토 구조를 확인합니다. 핵심은 회사 전체 추정치가 아니라 자산·납세의무자·필지·건축물 단위로 보유세 검토를 재설계했다는 점입니다.

## 2분: 실제 화면

Streamlit의 **Tax: 보유세 분석**에서 다음을 확인합니다.

- 14단계 Tax Review Document 구조
- 공식자료 계산·수동 검토·데이터 부족 Source Badge
- 토지·건축물·도시지역분·지방교육세·소방분·종부세의 분리된 계산표
- 검증 결과가 추가 요청자료로 이어지는 흐름
- CSV·Excel·Markdown·HTML 다운로드

현재 Snapshot에서 PNU와 시가표준액이 없는 것은 의도된 상태입니다. 앱은 이를 0이나 추정값으로 바꾸지 않습니다.

## 3분: 코드와 검증

1. [`src/tax_v15/calculators`](../src/tax_v15/calculators): Decimal 기반 세목별 계산
2. [`src/tax_v15/rules.py`](../src/tax_v15/rules.py): 공식 검증 Tax Rule Master 게이트
3. [`src/tax_v15/validation`](../src/tax_v15/validation): Source·Coverage·Fail-closed 통제
4. [`scripts/v15`](../scripts/v15): 수집부터 Memo까지 재현 가능한 파이프라인
5. [`tests/test_tax_v15.py`](../tests/test_tax_v15.py): 20개 필수 시나리오와 Golden Test
6. [Coverage Report](v15/COVERAGE_REPORT.md): 실제 확보 범위와 차단사유

## 평가 시 유의점

이 프로젝트는 전체 상장리츠의 확정 신고세액 데이터베이스라고 주장하지 않습니다. 현재 확보된 공식자료와 미확보 자료를 구분하고, 계산할 수 없는 항목을 명시적으로 차단하는 통제 설계가 주요 검토 대상입니다.
