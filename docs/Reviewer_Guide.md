# 3분 검토 가이드

현재 적용 버전: **v15.1.0 - Decision-First Tax Review**

## 1분: 문제와 결론

[README](../README.md)에서 프로젝트 범위와 데이터 한계를 확인한 뒤 Streamlit의 **Tax: 보유세 분석**으로 이동합니다. 첫 탭에서 다음 핵심 상태를 바로 확인할 수 있습니다.

- 2026년 보유세 재계산액: 약 12.51억원
- 공식 입력근거 Coverage: 5/5
- 실제 고지서 대사 Coverage: 0%
- 미해결 이슈: P0 3건, P1 3건
- 계산 완료 세목: 9개

재계산액은 공식 과세기초자료와 Tax Rule Master를 이용한 결과이며 실제 고지세액이 아닙니다.

## 2분: 네 개의 Tax 탭

1. **결론 및 시나리오**: Base, +5%, +10%, 사용자 설정 시나리오와 세목별 구성
2. **주요 이슈 및 요청자료**: 우선순위, 필요 증빙, 예상 영향과 다음 조치
3. **계산조서**: 세목별 입력값, 적용률·세율, 재계산액, 근거상태와 고지서 대사상태
4. **근거 및 다운로드**: Reconciliation, Source Lineage, Evidence Matrix, 검토메모와 출력파일

등기·신탁·담보 자료는 소유·권리관계 분석을 지원하지만 공식가액과 실제 세금 고지서를 대체하지 않는다는 경계를 함께 확인합니다.

## 3분: 코드와 업무문서

1. [`ui_tax_decision_first.py`](../ui_tax_decision_first.py): 네 탭 Tax 화면과 기존 엔진 출력의 시각화
2. [`src/tax_v15/case_study.py`](../src/tax_v15/case_study.py): 기준 사례, 시나리오, 이슈와 요청자료 연결
3. [`src/tax_v15/calculators`](../src/tax_v15/calculators): Decimal 기반 세목별 계산
4. [`src/tax_v15/validation`](../src/tax_v15/validation): Source·Coverage·Fail-closed 통제
5. [Business Process Case Brief](BUSINESS_PROCESS_CASE_BRIEF.md): As-Is·To-Be 업무 재설계
6. [Business Requirements Definition](BUSINESS_REQUIREMENTS_DEFINITION.md): 기능·데이터·검증·예외처리 요건
7. [`tests`](../tests): 계산 불변값, 공개 UI와 버전 일관성 검증

## 검토 시 유의점

이 프로젝트는 공개자료 기반 초기 Tax Screening과 의사결정 지원을 목적으로 합니다. 실제 과세내역서, 과세기준일 소유·신탁관계, 감면, 세부담상한과 고지세액은 전문가 검토와 추가 증빙이 필요합니다.
