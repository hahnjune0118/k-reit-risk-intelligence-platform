# v15 Tax Case Study 사용자 가이드

## 시작

Streamlit에서 **Tax: 보유세 분석**을 선택하면 SK리츠의 SK서린빌딩 2026년 Golden Asset Case Study가 바로 열립니다. 공개 Tax 화면에는 회사, 자산, 납세의무자 또는 보유구조 선택 기능이 없습니다.

일반 정보 및 시나리오 화면은 기존처럼 여러 상장리츠를 비교할 수 있지만, Tax 계산 결과는 SK서린빌딩 한 건으로만 제한됩니다.

## 결과를 읽는 순서

1. Executive Conclusion
2. SK리츠·SK서린빌딩 Case Scope
3. Ownership & Taxpayer Structure
4. Public REIT Separate-Tax Eligibility
5. Address·PNU·Official Values
6. Land Property Tax
7. Building Property Tax
8. Urban Area·Local Education Tax
9. Fire Resource Facility Tax
10. Comprehensive Real Estate Holding Tax
11. Total Statutory Recalculation
12. Tax Sensitivity Scenario
13. Tax Issue Matrix
14. Request List
15. Tax Review Memo
16. Evidence & Limitations
17. Downloads

화면 상단의 raw 산식 재계산액 `1,250,710,968.55472원`과 요약 표시 약 `12.51억원`은 같은 결과입니다. 실제 고지세액은 미확인이며 고지서 대사는 미완료입니다.

## Tax Sensitivity Scenario

Base, Moderate, Severe는 각각 토지 개별공시지가와 건축물 시가표준액을 `0%`, `+5%`, `+10%` 조정합니다. Custom은 각 입력을 `-10%`부터 `+20%`까지 1% 단위로 변경합니다.

시나리오에서 다음 항목은 고정됩니다.

- 공모리츠 분리과세 법적 판단
- 공정시장가액비율과 각 세율
- 소방분 누진구조와 300% 배율
- 소유지분과 필지면적

시나리오는 가격 입력 변화에 대한 기계적 민감도입니다. 미래 세액, 실제 고지세액 또는 과세관청의 결정세액이 아닙니다.

## Tax Issue Matrix

Matrix는 `priority`와 `current_status`를 기준으로 표시합니다. 숫자의 크기만으로 위험도를 자동 확정하지 않습니다.

- **P0 Open**: 실제 고지 과세구분, 실제 고지세액, 과세기준일 등기·신탁상태
- **P1 Open**: 토지면적 5.3㎡ 차이, 소방분 실제 위험유형 코드, 법정 절사·감면·세부담상한

각 행의 필요자료와 요청사유는 Request List에 연결되며 Memo와 Export에도 포함됩니다.

## 계산 상태 해석

- **고지서 확인**: 실제 과세자료와 대사된 상태
- **공식자료 계산**: 공식 입력값과 검증된 규칙으로 계산한 상태
- **공식자료 일부**: 일부 근거만 확보된 상태
- **수동 검토**: 법적 판단 또는 전문 검토가 필요한 상태
- **데이터 부족**: 필수자료 부족으로 계산하지 않은 상태
- **해당 없음**: 검증된 분류상 세목이 적용되지 않는 상태

`데이터 부족`은 0원을 의미하지 않습니다. 실제 고지서 확인 전에는 결과를 `verified_notice`로 표시하지 않습니다.

## 다운로드

- Case Scope와 계산내역 CSV
- Scenario Summary와 세목별 Breakdown CSV
- Issue Matrix와 Request List CSV
- 입력, 계산, 검증, Evidence를 포함한 Excel 검토팩
- Scenario, Issue Matrix와 Request List를 포함한 Markdown Tax Review Memo
- 브라우저에서 열 수 있는 HTML 검토문서

## 실행 및 검증

```powershell
py -m streamlit run app.py
py -m pytest -q
py -m ruff check .
py -m compileall -q .
```

## 주의

본 화면은 공개자료 기반의 초기 Tax Review Case Study입니다. SK리츠 전체 자산의 총 보유세, 다른 상장리츠의 세액 또는 실제 신고·납부세액을 산출하지 않습니다. 실제 업무 적용에는 과세내역서, 고지서, 등기·신탁원부, 감면, 세부담상한과 지방자치단체 조정 검토가 추가로 필요합니다.
