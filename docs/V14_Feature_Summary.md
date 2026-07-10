# v14 Feature Summary

## v14 - Tax Workflow Control & Validation

v14는 Tax Review Pack을 생성하는 데서 한 단계 더 나아가, 자료 출처, 계산 경로, 요청자료, Memo 제한 문구, 검증 상태를 하나의 통제된 workflow로 연결합니다.

## 1. Source Reliability Framework

`data_source_policy.py`는 Tax 화면 전반에서 사용하는 source taxonomy를 제공합니다.

| source_type | 의미 |
| --- | --- |
| `official_disclosure` | 공식 공시/공식 원천자료 |
| `api_snapshot` | API 또는 Snapshot 자료 |
| `peer_snapshot` | Peer 비교용 Snapshot |
| `peer_snapshot_estimate` | Peer 기반 회사 전체 추정 |
| `sample_estimate` | 공개 데모 예시 추정 |
| `data_insufficient` | 핵심 입력값 부족 |

각 source type은 한국어 라벨, 신뢰수준, 허용 산출물, Memo 제한 문구, UI 경고 문구를 가집니다.

## 2. Holding Tax Bridge

`calculations_holding_tax_bridge.py`는 다음 순서로 보유세 추정 경로를 만듭니다.

1. 자산별 tax row
2. Peer Snapshot의 `estimated_holding_tax`
3. Peer Snapshot의 `official_price_total`
4. Peer Snapshot의 `investment_property`
5. `data_insufficient`

결과 표는 공시가격 또는 장부가액, 과세표준 추정, 적용 세율, 추정 보유세, FFO 대비, 영업수익 대비, Peer 대비 위치, source limitation을 함께 보여 줍니다.

## 3. Validation Panel

`tax_validation.py`는 다음 항목을 검증합니다.

- Tax Snapshot 결측
- 회사 전체 fallback 사용 여부
- FFO denominator 존재 여부
- 공시가격 또는 기준시가 입력값 존재 여부
- 보유세/FFO 및 공시가격/장부가액 비율의 비정상 구간

Tax 화면 하단의 `데이터 검증 및 한계` expander에서 결과를 확인할 수 있습니다.

## 4. Issue 기반 Request List

`tax_request_mapping.py`는 Tax Issue Matrix와 source 상태를 기반으로 요청자료를 생성합니다.

예시 요청자료:

- 재산세 고지서
- FFO 산정자료
- 배당가능이익 산정자료
- 자산별 장부가액 명세
- 토지대장
- 건축물대장
- 자산별 위치 및 면적 자료
- 자산별 세부 보유세 산출자료

## 5. Memo Draft

Tax Review Memo 초안은 6개 섹션으로 고정됩니다.

1. 검토 대상
2. 핵심 수치 요약
3. 주요 Tax 이슈
4. 요청자료
5. 실무적 시사점
6. 제한 및 유의사항

Memo는 항상 확정 세액, 법률의견, 투자 추천이 아니라는 제한 문구를 포함하고, source type에 따라 원자료 확인과 세무 전문가 검토 필요성을 표시합니다.

## 6. Export

Tax 화면은 다음 파일을 제공합니다.

- `tax_review_memo_{company_name}_v14.md`
- `tax_issue_matrix_{company_name}_v14.csv`
- `holding_tax_reconciliation_{company_name}_v14.csv`
- `tax_request_list_{company_name}_v14.csv`
- `tax_review_pack_{company_name}_v14.zip`

## 7. Non-SK 안정성

`reit_master.csv`의 모든 회사는 Tax Summary, bridge, issue matrix, reconciliation, FFO stress, request list, memo, banner, source expander를 생성할 수 있어야 합니다.

SK리츠 외 회사는 SK리츠의 상세 자산, 임차인, Cap rate, 차입금 만기 데이터를 재사용하지 않습니다. 상세자료가 부족하면 `회사 전체 추정` 행과 `회사 전체` region으로 표시합니다.
