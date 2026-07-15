# 3분 리뷰 가이드

## 1분: 문제와 범위

[README](../README.md)에서 분산된 공개자료를 하나의 검토 흐름으로 연결하는 문제와 v15 범위를 확인합니다. 공개 Tax 화면은 공식 과세기초자료를 연결할 수 있는 **SK리츠·SK서린빌딩·2026년** 한 건을 깊이 검토합니다.

- 끝수 처리 전 산식상 산출세액: `1,250,710,968.55472원`
- 끝수 처리 후 보유세 재계산액: `1,250,710,930원`
- 실제 고지세액: 과세내역서 미확보
- 고지세액 대사 상태: 미대사

## 2분: 실제 화면

Streamlit의 **Tax: 보유세 분석**에서 다음을 확인합니다.

- 법률판정을 먼저 제시하는 20단계 보유세 세무검토 흐름
- 자산·필지·건축물·납세의무자 단위의 공식자료 연결
- 토지 분리과세와 건축물·도시지역분·지방교육세·소방분의 별도 계산
- 세목별 10원 미만 끝수 처리와 처리 전·후 감사추적
- 기준·5%·10%·사용자 설정 보유세 민감도 분석
- P0 3건과 P1 3건의 주요 세무쟁점, 추가 요청자료와 메모 연결
- CSV·Excel·Markdown·HTML 내려받기

Tax 화면에는 다른 리츠, 자산 또는 납세의무자를 선택하는 UI가 없습니다. 일반 정보 및 시나리오 화면의 다회사 기능은 유지됩니다.

## 3분: 코드와 검증

1. [`src/tax_v15/case_study.py`](../src/tax_v15/case_study.py): 분석대상 선택, 민감도, 세무쟁점과 요청자료 연결
2. [`src/tax_v15/calculators`](../src/tax_v15/calculators): Decimal 기반 세목별 계산과 끝수 처리
3. [`src/tax_v15/rules.py`](../src/tax_v15/rules.py): 공식 검증 세법 규칙표 게이트
4. [`src/tax_v15/validation`](../src/tax_v15/validation): 자료·확인범위·Fail-closed 통제
5. [`ui_tax_case_study.py`](../ui_tax_case_study.py): 단일 자산 공개 화면
6. [`tests/test_tax_v15_end_digit_treatment.py`](../tests/test_tax_v15_end_digit_treatment.py): 끝수 처리와 공개 UI 회귀 검증
7. [SK서린빌딩 과세근거 검토](v15/golden_asset/GOLDEN_ASSET_TAX_REVIEW.md): 공식 출처, 산식과 미해결 이슈

## 평가 시 유의점

이 프로젝트는 SK리츠 전체 자산의 확정 신고세액 데이터베이스라고 주장하지 않습니다. 확보한 공식 과세기초자료와 미확보 증빙을 분리하고, 실제 고지서 확인 전에는 `verified_notice`를 생성하지 않는 통제 설계가 주요 검토 대상입니다.
