# 3분 검토 가이드

현재 적용 버전: **v15.1.0 - AX Workflow & Advisory Portfolio**

## 1분: AX 적용 개요

일반 정보 및 시나리오 화면 최상단에서 다음 내용을 확인합니다.

- 분산된 공시·세법·공시가격·재무자료가 하나의 검토 Workflow로 연결되는 방식
- 고객 Pain Point, AX Solution과 업무효과
- 수작업 중심 As-Is와 통제된 To-Be Workflow
- Data, Automation, AI 지원영역, Control Harness, Human Review의 역할 경계
- 현재 구현 기능, 확장 설계와 전문가 확인 필요사항

공개 Runtime의 세액 계산은 규칙엔진으로 수행합니다. 생성형 AI는 비정형 문서 구조화와 검토문서 초안 지원을 위한 확장계층이며, 현재 앱에 직접 연결된 세법 판단 Runtime으로 설명하지 않습니다.

## 2분: 실제 화면

1. **일반 정보 및 시나리오**: 회사·시나리오 분석과 AX 적용 개요
2. **Tax: 보유세 분석**: SK서린빌딩 재계산, 민감도, 6개 주요 쟁점과 요청자료
3. **Assurance: 감사위험 분석**: RMM, KAM, 감사절차와 요청자료
4. **분석 방법론 및 데이터 출처**: 데이터 정의, Source Lineage와 한계

Tax Case Study의 핵심 증빙은 공식 과세근거자료 16건, 원시 재계산액 `1,250,710,968.55472원`, CSV·Excel·Markdown·HTML 출력입니다. 실제 고지세액은 확인되지 않아 대사 상태를 미완료로 유지합니다.

## 3분: 코드와 문서

1. [`ui_general.py`](../ui_general.py): AX 적용 개요와 기존 General 분석 화면
2. [`src/tax_v15/case_study.py`](../src/tax_v15/case_study.py): Tax Scenario와 Issue Matrix
3. [`src/tax_v15/calculators`](../src/tax_v15/calculators): Decimal 기반 세목별 규칙엔진
4. [`src/tax_v15/validation`](../src/tax_v15/validation): Source·Coverage·Fail-closed 통제
5. [AX Advisory Case Brief](AX_ADVISORY_CASE_BRIEF.md): 업무 문제와 To-Be 설계
6. [AX Requirements Definition](AX_REQUIREMENTS_DEFINITION.md): 기능·데이터·통제 요건
7. [`tests`](../tests): 버전, Tax, Assurance와 공개 UI 회귀검증

## 검토 시 유의점

이 프로젝트는 공개자료 기반 초기 검토를 지원하며 실제 신고세액, 법률해석, 감사의견 또는 과세관청 결정세액을 대체하지 않습니다. 공식자료가 부족한 항목은 추정으로 완료하지 않고 Fail-closed 상태와 추가 요청자료로 연결합니다.
