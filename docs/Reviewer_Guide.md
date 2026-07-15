현재 적용 버전: v15.0.1 - SK서린빌딩 핵심 자산 보유세 세무검토

# 3분 리뷰 가이드

## 1분: 문제와 범위

[README](../README.md)에서 공개자료가 분산된 문제와 v15 Tax Case Study 범위를 확인합니다. 공개 Tax 화면은 여러 리츠의 미완성 추정치를 나열하지 않고, 공식 입력 Evidence를 연결할 수 있는 **SK리츠·SK서린빌딩·2026년** 한 건을 깊이 검토합니다.

핵심 구분은 다음과 같습니다.

- 공식 입력자료 기반 산식 재계산액: `1,250,710,968.55472원`
- 화면 표시: 약 `12.51억원`
- 실제 고지세액: 미확인
- 고지서 Reconciliation: 미완료

## 2분: 실제 화면

Streamlit의 **Tax: 보유세 분석**에서 다음을 확인합니다.

- 17단계 Golden Asset Tax Review 흐름
- 자산·필지·건축물·납세의무자 단위의 Source 연결
- 토지·건축물·도시지역분·지방교육세·소방분·종부세의 분리 계산
- Base, Moderate, Severe와 Custom Tax Sensitivity Scenario
- P0 Open 3건과 P1 Open 3건의 Tax Issue Matrix
- 각 Issue에서 Request List와 Tax Review Memo로 이어지는 추적성
- CSV·Excel·Markdown·HTML 다운로드

Tax 화면에는 다른 리츠, 자산 또는 납세의무자를 선택하는 UI가 없습니다. 일반 정보 및 시나리오 화면의 다회사 기능은 유지됩니다.

## 3분: 코드와 검증

1. [`src/tax_v15/case_study.py`](../src/tax_v15/case_study.py): Golden Case 선택, Scenario, Issue Matrix와 Request 연결
2. [`src/tax_v15/calculators`](../src/tax_v15/calculators): Decimal 기반 세목별 계산
3. [`src/tax_v15/rules.py`](../src/tax_v15/rules.py): 공식 검증 Tax Rule Master 게이트
4. [`src/tax_v15/validation`](../src/tax_v15/validation): Source·Coverage·Fail-closed 통제
5. [`ui_tax_case_study.py`](../ui_tax_case_study.py): 고정된 Case Study 공개 화면
6. [`tests/test_tax_v15_seorin_case_study.py`](../tests/test_tax_v15_seorin_case_study.py): Scope, Scenario, Issue, Memo와 Export 회귀 검증
7. [Golden Asset Review](v15/golden_asset/GOLDEN_ASSET_TAX_REVIEW.md): 공식 출처, 산식과 미해결 이슈

## 평가 시 유의점

이 프로젝트는 SK리츠 전체 자산 또는 전체 상장리츠의 확정 신고세액 데이터베이스라고 주장하지 않습니다. 현재 확보한 공식 입력과 미확보 증빙을 분리하고, 실제 고지서 확인 전에는 `verified_notice`를 생성하지 않는 통제 설계가 주요 검토 대상입니다.
