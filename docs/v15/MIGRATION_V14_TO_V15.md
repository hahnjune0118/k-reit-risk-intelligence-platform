# v14에서 v15로의 전환

## 변경 이유

v14의 Tax Review Pack은 공개 포트폴리오에서 Workflow와 요청자료를 보여주는 데 유용했지만, 회사 전체 공시가격·보유세 Snapshot 또는 장부가액 기반 추정이 실제 법정 세액 계산과 혼동될 위험이 있었습니다.

## 활성 경로에서 제거한 로직

- 투자부동산 장부가액 × 공시가격 비율
- 회사 전체 과세표준 × 실효 보유세율
- 다른 리츠 또는 Peer의 보유세율 재사용
- 상세자료가 없는 회사를 기존 자산 Sample로 대체
- 확인 불가능한 입력값을 0으로 간주

기존 v14 UI는 회귀 참조를 위해 `archive/v14/ui_tax_v14.py`에 보관하며 앱 시작 경로에서 호출하지 않습니다.

## 새 구조

| v14 | v15 |
|---|---|
| 회사 전체 Snapshot | 자산·납세의무자·필지·건축물 Registry |
| 단일 추정 보유세 | 세목별 중간 계산값과 상태 |
| Peer 기반 fallback | 공식 근거 미확보 시 Fail-closed |
| 회사 단위 Memo | 17개 섹션 Tax Review Document |
| 제한적 검증 | Source·Schema·법적 분류·고지서 대사 통제 |

## 호환성

General 및 Assurance 화면의 재무지표와 Peer Benchmark는 유지합니다. 단, 해당 재무·Peer 데이터는 v15 Tax 세액 계산의 대체 입력값으로 사용하지 않습니다.

## 전환 확인

```powershell
py -m pytest -q tests/test_tax_v15.py
py -m scripts.v15.run_pipeline --tax-year 2026 --all-reits --offline --no-resume
py -m streamlit run app.py
```
