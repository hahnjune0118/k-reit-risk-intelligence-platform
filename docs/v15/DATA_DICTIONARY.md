# v15 데이터 사전

모든 CSV는 UTF-8 BOM 형식으로 저장하며, 빈 값은 0이 아니라 **미확인**을 의미합니다.

| 파일 | Grain | 주요 Key | 목적 |
|---|---|---|---|
| `reit_master.csv` | 상장리츠 1개 | `stock_code` | 법인명, 상장상태, 공식 홈페이지와 목록 출처 |
| `coverage_manifest.csv` | 상장리츠 1개 | `stock_code` | 수집·검증 Coverage와 차단사유 |
| `source_document_manifest.csv` | 원천문서 1개 | `reit_name + document_type + source_url` | URL, 캐시, 해시, 추출상태와 관련 페이지 |
| `asset_master.csv` | 부동산 자산 1개 | `asset_id` | 자산명, 유형, 보유구조, 소유자와 주소 |
| `parcel_master.csv` | 필지 1개 | `parcel_id` | PNU, 면적, 지분, 개별공시지가와 출처 |
| `building_master.csv` | 건축물 1개 | `building_id` | 연면적, 용도, 시가표준액과 소방분 분류 |
| `taxpayer_structure.csv` | 납세의무자-자산 관계 1개 | `taxpayer_id + asset_id` | 소유·신탁관계, 과세기준일과 분리과세 판정 |
| `tax_rule_master.csv` | 과세연도·규칙·구간 1개 | `tax_year + rule_code + bracket_start` | 세율, 공정시장가액비율, 누진구간과 법령 |
| `tax_calculation_detail.csv` | 자산·필지·건축물·세목 계산 1개 | 복합 Key | 입력값, 중간 과세표준, 세율과 결과 |
| `reconciliation.csv` | 리츠·납세의무자·연도·대사항목 1개 | 복합 Key | 계산값과 고지·검증값 대사 |
| `request_list.csv` | 이슈별 요청자료 1개 | `request_id` | 누락자료, 요청사유와 우선순위 |
| `validation_result.csv` | 검증 통제 결과 1개 | `validation_id` | 중요도, 상태, 메시지와 원천 URL |

## 공통 Source Lineage

Master 데이터에는 가능한 범위에서 다음 필드를 유지합니다.

- `source_type`, `source_url`
- `source_document_name`, `source_document_date`, `source_page`
- `source_quote_or_evidence`
- `retrieved_at`, `source_hash`
- `source_reliability`, `reviewer_status`

## 주요 관계

```text
reit_master 1 -> N asset_master
asset_master 1 -> N parcel_master
asset_master 1 -> N building_master
asset_master N <-> N taxpayer_structure
taxpayer_structure 1 -> N tax_calculation_detail
validation_result 1 -> N request_list
```

## 값 해석 원칙

- 금액 단위는 별도 표기가 없으면 원(KRW)입니다.
- 비율은 계산 엔진에서 `0.70`, `0.002`와 같은 Decimal 비율로 저장합니다.
- `ownership_share`는 0 초과 1 이하입니다.
- PNU는 선행 0을 보존하는 19자리 문자열입니다.
- `calculated_tax`는 세액만 저장합니다. 토지 시가표준액은 `official_value`에 저장합니다.
- `verified_tax`는 실제 고지서·과세내역서 확인 전 비워 둡니다.
