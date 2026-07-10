# v13 Tax Data Quality Report

> 참고: 현재 활성 버전은 v14 - Tax Workflow Control & Validation입니다. 이 문서는 v13 데이터 품질 점검 이력을 보존합니다.

## 분석 목적

v13 Tax Review Pack Generator가 SK리츠뿐 아니라 `reit_master.csv`에 포함된 전체 상장리츠 Snapshot universe에서 일관되게 작동하는지 점검했다. 분석 초점은 Tax mode의 데이터 커버리지, 결측, 단위와 비율의 안정성, Red Flag 기준, fallback 추정 로직이다.

본 보고서는 공개 포트폴리오용 데이터 품질 점검이며, 세무 신고 목적의 확정 세액 검토나 세무 자문이 아니다.

## 데이터 파일 현황

| file name | purpose | rows | cols | key columns | major issues |
|---|---:|---:|---:|---|---|
| `red_flag_rules.json` | Red Flag rule definition | 11 rules | 13 keys | assurance, tax | Tax rule 1개가 공시가격 상승률이 아니라 `holding_tax_to_ffo`를 재사용 |
| `reit_master.csv` | 회사 master / 분석 universe | 8 | 10 | company_name, stock_code, dart_corp_code, market_cap_rank | 8개 회사 Snapshot 기준. 공식 전체 universe로 과대 주장 금지 |
| `reit_peer_snapshot.csv` | Peer benchmark 및 red flag 입력 Snapshot | 8 | 18 | financials, FFO, holding tax, official price | 모든 회사 1개 기간 sample_snapshot. 5년 추세 아님 |
| `reit_tax_snapshot.csv` | v13 Tax Review Pack fallback 입력값 | 8 | 15 | company, asset_name, book_value, official_price, estimated_holding_tax | 모든 회사가 회사 전체 추정 1행. 자산별 tax grain 없음 |
| `reit_tax_snapshot_suggested.csv` | 개선 후보 Snapshot | 8 | 15 | production tax snapshot과 동일 | 생산 데이터 덮어쓰기 전 검토 필요 |
| `sk_reit_asset_metrics.csv` | SK리츠 자산상세 sample | 7 | 29 | asset_name, location, appraisal, lease data | 공식 자산별 세금자료는 아님. 다른 리츠에 재사용 금지 |
| `sk_reit_consolidated_financials.csv` | SK리츠 다기간 재무 sample | 6 | 35 | period_end, total_assets, revenue, debt | SK리츠 전용 |
| `sk_reit_latest_kpis.csv` | SK리츠 KPI sample | 2 | 22 | FFO, NAV, leverage, WALE | Peer Snapshot KPI와 기준 차이 가능 |
| `sk_reit_debt_schedule_20260331.csv` | SK리츠 차입금 상세 sample | 44 | 14 | debt_type, principal, rate, maturity | Tax mode 직접 입력값은 아님 |
| `sk_reit_debt_summary_20260331.csv` | SK리츠 차입금 요약 sample | 10 | 7 | maturity_year, principal, rate | Assurance/Scenario 중심 보조자료 |
| `sk_reit_parent_direct_assets_20260331.csv` | SK리츠 직접보유 자산 sample | 4 | 16 | asset_name, book_value, area | 공식 tax bill 또는 공시가격 원장 아님 |
| `sk_reit_additional_source_plan.csv` | 추가 수집 계획 | 9 | 7 | priority, fields_to_extract | 산출물보다는 데이터 roadmap 성격 |
| `sk_reit_data_dictionary.csv` | 데이터 정의 | 6 | 4 | table, field, definition | 일부 v13 신규 컬럼 정의 보강 필요 |

## 회사별 데이터 커버리지

| company_name | stock_code | rank | peer data | 5-year financial data | tax snapshot | asset-level tax data | asset-level real estate sample | source_type | coverage class | data quality status |
|---|---:|---:|---|---|---|---|---|---|---|---|
| SK리츠 | 395400 | 1 | yes | yes | yes | no | yes | peer_snapshot_estimate | Partial coverage | Tax Review Pack 생성 가능. SK 자산상세 sample은 있으나 공식 자산별 tax data는 없음 |
| ESR켄달스퀘어리츠 | 365550 | 2 | yes | no | yes | no | no | peer_snapshot_estimate | Partial coverage | 회사 전체 추정값 중심 |
| 롯데리츠 | 330590 | 3 | yes | no | yes | no | no | peer_snapshot_estimate | Partial coverage | 회사 전체 추정값 중심 |
| 제이알글로벌리츠 | 348950 | 4 | yes | no | yes | no | no | peer_snapshot_estimate | Partial coverage | 회사 전체 추정값 중심 |
| 신한알파리츠 | 293940 | 5 | yes | no | yes | no | no | peer_snapshot_estimate | Partial coverage | 회사 전체 추정값 중심 |
| 코람코라이프인프라리츠 | 357120 | 6 | yes | no | yes | no | no | peer_snapshot_estimate | Partial coverage | 회사 전체 추정값 중심 |
| NH올원리츠 | 400760 | 7 | yes | no | yes | no | no | peer_snapshot_estimate | Partial coverage | 회사 전체 추정값 중심 |
| 이지스밸류리츠 | 334890 | 8 | yes | no | yes | no | no | peer_snapshot_estimate | Partial coverage | 회사 전체 추정값 중심 |

요약:

| coverage class | company count |
|---|---:|
| Full coverage | 0 |
| Partial coverage | 8 |
| Peer-only coverage | 0 |
| Missing coverage | 0 |

모든 회사가 Peer Snapshot과 Tax Snapshot을 보유하므로 v13 Tax Review Pack의 기본 산출물은 생성 가능했다. 다만 당시 공식 자산별 tax dataset은 없고, SK리츠만 자산상세 sample을 별도로 보유했다. 따라서 모든 회사의 Tax 결과는 기본적으로 `회사 전체 추정` grain이라는 점을 화면과 memo에 계속 표시해야 했다.

## 주요 Tax 지표 결측률

| field | missing count | missing percentage | companies affected | fallback estimation possible |
|---|---:|---:|---|---|
| ffo_proxy | 0 | 0.0% | - | 제한적. peer snapshot 또는 DART 재무값 필요 |
| operating_revenue | 0 | 0.0% | - | 제한적. peer snapshot 또는 DART 재무값 필요 |
| investment_property | 0 | 0.0% | - | 가능 |
| official_price_total | 0 | 0.0% | - | 가능 |
| estimated_holding_tax | 0 | 0.0% | - | 가능 |
| holding_tax_to_ffo | 0 | 0.0% | - | 가능 |
| holding_tax_to_operating_revenue | 0 | 0.0% | - | 가능 |
| official_price_to_investment_property | 0 | 0.0% | - | 가능 |
| official_price_growth_5y | 0 | 0.0% | - | 가능. Tax Snapshot 기본 가정 또는 지역별 공시가격 추세 필요 |

결측률은 핵심 Snapshot 기준 0%다. 그러나 이는 모든 회사에 회사 전체 추정값을 채운 결과다. 결측이 없다는 사실이 공식 세액 또는 자산별 실자료가 충분하다는 의미는 아니다.

## Tax Metric Validation

### 주의가 필요한 row

| company_name | holding_tax_to_ffo | holding_tax_to_operating_revenue | official_price_to_investment_property | estimated_holding_tax / investment_property | official_price_growth_5y | flag |
|---|---:|---:|---:|---:|---:|---|
| 이지스밸류리츠 | 35.5% | 14.0% | 56.5% | 0.9% | 10.1% | holding_tax_to_ffo >= 35% |
| 제이알글로벌리츠 | 38.5% | 15.6% | 46.0% | 0.9% | 8.5% | holding_tax_to_ffo >= 35%; holding_tax_to_operating_revenue >= 15% |
| 코람코라이프인프라리츠 | 36.8% | 15.4% | 56.6% | 0.9% | 9.6% | holding_tax_to_ffo >= 35%; holding_tax_to_operating_revenue >= 15% |

검토 결과 division by zero, 음수 denominator, 즉시 계산 중단을 유발하는 값은 발견되지 않았다. 다만 `holding_tax_to_operating_revenue`가 모든 회사에서 11.6%~15.6% 수준으로 높아 현행 red 기준 15% 적용 시 여러 회사가 red가 된다. Sample 기반 추정치라는 점을 고려하면 threshold 과민 가능성이 있다.

### FFO 현금유출 스트레스

v13 기본 가정인 보유세 +10%, FFO -4%를 적용하면 아래와 같다.

| company_name | base FFO | base holding tax | stressed holding_tax_to_ffo | status |
|---|---:|---:|---:|---|
| ESR켄달스퀘어리츠 | 74,300 | 18,600 | 28.7% | 주의 |
| NH올원리츠 | 26,900 | 9,100 | 38.8% | 높음 |
| SK리츠 | 88,536 | 29,500 | 38.2% | 높음 |
| 롯데리츠 | 52,100 | 15,800 | 34.8% | 주의 |
| 신한알파리츠 | 48,700 | 12,100 | 28.5% | 주의 |
| 이지스밸류리츠 | 23,400 | 8,300 | 40.6% | 높음 |
| 제이알글로벌리츠 | 44,700 | 17,200 | 44.1% | 높음 |
| 코람코라이프인프라리츠 | 38,600 | 14,200 | 42.2% | 높음 |

이 결과는 보유세 자체가 과대라는 결론이 아니라, 현재 sample 추정치 기준으로 FFO 대비 현금유출 민감도가 크게 나타난다는 의미다.

## Peer Benchmark 분포

| metric | n | min | p25 | median | mean | p75 | p90 | max | recommended green | recommended yellow | recommended red |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| holding_tax_to_ffo | 8 | 24.8% | 29.0% | 33.6% | 32.3% | 35.8% | 37.3% | 38.5% | < 25% 또는 peer P70 미만 | 25%~35% | >= 35% |
| holding_tax_to_operating_revenue | 8 | 11.6% | 12.0% | 13.7% | 13.6% | 15.0% | 15.5% | 15.6% | < 12% | 12%~18% | >= 18% |
| official_price_to_investment_property | 8 | 46.0% | 51.8% | 55.1% | 53.5% | 56.5% | 56.7% | 57.0% | 35%~65% 범위 | 65% 이상 또는 35% 미만 | 75% 이상 또는 30% 미만 |
| estimated_holding_tax / investment_property | 8 | 0.6% | 0.7% | 0.8% | 0.8% | 0.9% | 0.9% | 0.9% | < 0.60% | 0.60%~0.75% | >= 0.75% |
| official_price_growth_5y | 8 | 7.8% | 9.3% | 10.4% | 10.6% | 11.4% | 12.8% | 14.5% | < 10% | 10%~15% | >= 15% |

주의: 표본은 8개 회사이며 대부분 sample/snapshot 추정이다. Percentile 기준은 보조 신호로만 사용하고, absolute threshold와 `source_type` 표시를 함께 써야 한다.

## Red Flag 기준 검토

| rule name | current metric | current threshold | observed distribution | recommended threshold | recommended basis | reason |
|---|---|---|---|---|---|---|
| holding_tax_to_ffo | holding_tax_to_ffo | yellow 0.25 / red 0.35 | median 33.6%, p75 35.8%, p90 37.3% | yellow 0.25 / red 0.35 | hybrid: absolute + percentile | 보수적이지만 실무 검토용으로 적절 |
| holding_tax_to_operating_revenue | holding_tax_to_operating_revenue | yellow 0.10 / red 0.15 | median 13.7%, p75 15.0%, p90 15.5% | yellow 0.12 / red 0.18 | hybrid: absolute + percentile | 현행 10%/15%는 sample-heavy 데이터에서 과잉 경보 가능 |
| official_price_to_investment_property | official_price_to_investment_property | yellow 0.55 / red 0.65 | median 55.1%, p75 56.5%, p90 56.7% | yellow 0.60 / red 0.70, lower-bound watch 추가 | absolute threshold with lower-bound watch | 지나치게 낮은 ratio도 데이터 품질 또는 누락 신호일 수 있음 |
| official_price_growth_placeholder | holding_tax_to_ffo | yellow 0.30 / red 0.40 | holding_tax_to_ffo 분포를 잘못 참조 | yellow 0.10 / red 0.15 on official_price_growth_5y | absolute threshold using official_price_growth_5y | 현재는 공시가격 상승률 rule로 작동하지 않음 |

핵심 이슈는 `official_price_growth_placeholder`였다. 이름과 설명상 공시가격 상승률 rule이지만 당시 metric이 `holding_tax_to_ffo`였다. v13 Tax Review Pack에서는 `official_price_growth_5y` 또는 별도 growth metric으로 분리하는 것이 안전했다.

## Fallback 추정 로직 제안

| 단계 | source_type | 사용 조건 | UI 문구 | 한계 |
|---:|---|---|---|---|
| 1 | `asset_level_tax_snapshot` | 회사별 자산별 공시가격/고지세액 Snapshot 존재 | 자산별 공시가격·보유세 Snapshot 기준입니다. | 공식 신고세액은 아니며 원자료 대사가 필요합니다. |
| 2 | `company_tax_snapshot` | 회사별 추정 보유세 직접 입력값 존재 | 회사 전체 보유세 Snapshot 기준입니다. | 자산별 이슈 식별력은 제한됩니다. |
| 3 | `peer_snapshot_estimate` | peer snapshot의 estimated_holding_tax 또는 official_price_total 존재 | 자산별 상세자료 부족으로 회사 전체 Snapshot 기반 추정값을 사용합니다. | 회사별 실제 고지세액과 차이가 클 수 있습니다. |
| 4 | `investment_property_estimate` | investment_property만 존재 | 투자부동산 장부금액 기반 보수적 추정값을 사용합니다. | 공시가격과 과세표준 구조를 반영하지 못합니다. |
| 5 | `data_missing` | 핵심 입력값 모두 부족 | 데이터 부족으로 해당 지표를 산출하지 않습니다. | Tax Review Pack 일부 산출물이 제한됩니다. |

Fallback 추정값은 어떤 단계에서도 공식 세액처럼 표현하면 안 된다. `source_note`에는 산식, 가정, 사용한 원천을 짧게 남기는 것이 좋다.

## Suggested Tax Snapshot

개선 후보 파일로 `data/reit_tax_snapshot_suggested.csv`를 생성했다. 기존 production 파일인 `data/reit_tax_snapshot.csv`는 덮어쓰지 않았다.

생성 기준:

- 모든 회사에 최소 1개 `회사 전체 추정` 행을 유지
- `source_type = peer_snapshot_estimate`
- `source_note = 자산별 상세자료 부족으로 회사 전체 Snapshot 기반 추정`
- 추정값은 공식 세액이 아니라 v13 Tax Review Pack 생성용 fallback 입력값

## Tax Review Pack 생성 가능성 평가

| company_name | Tax Issue Matrix | Holding Tax Reconciliation | Tax Request List | FFO cash outflow stress | Tax Review Memo Draft | source expander | why |
|---|---|---|---|---|---|---|---|
| SK리츠 | pass | pass | pass | pass | pass | pass | 생성 가능. 단, 공식 자산별 tax data는 아님 |
| ESR켄달스퀘어리츠 | pass | pass | pass | pass | pass | pass | 생성 가능. 회사 전체 추정값 기준 |
| 롯데리츠 | pass | pass | pass | pass | pass | pass | 생성 가능. 회사 전체 추정값 기준 |
| 제이알글로벌리츠 | pass | pass | pass | pass | pass | pass | 생성 가능. 회사 전체 추정값 기준 |
| 신한알파리츠 | pass | pass | pass | pass | pass | pass | 생성 가능. 회사 전체 추정값 기준 |
| 코람코라이프인프라리츠 | pass | pass | pass | pass | pass | pass | 생성 가능. 회사 전체 추정값 기준 |
| NH올원리츠 | pass | pass | pass | pass | pass | pass | 생성 가능. 회사 전체 추정값 기준 |
| 이지스밸류리츠 | pass | pass | pass | pass | pass | pass | 생성 가능. 회사 전체 추정값 기준 |

당시 상태에서는 모든 회사가 주요 v13 Tax Review Pack 산출물을 생성할 수 있었다. 실패 회사는 없었다. 다만 산출 가능성과 데이터 신뢰도는 달랐다. 대부분 회사는 asset-level 실자료가 아니라 회사 전체 Snapshot 기반이었다.

## 개선 우선순위

| priority | recommendation | impact |
|---:|---|---|
| 1 | `official_price_growth_placeholder`의 metric을 `holding_tax_to_ffo`에서 `official_price_growth_5y`로 분리 | 공시가격 상승 red flag가 실제 의도대로 작동 |
| 1 | `source_type = peer_snapshot_estimate`인 경우 모든 핵심 표와 Memo에 `회사 전체 추정` 표시 유지 | 비-SK 리츠 결과를 공식 세액으로 오해하는 위험 감소 |
| 2 | `reit_tax_snapshot.csv`를 자산별 행으로 확장하되, 최소한 산식과 원천을 `source_note`에 표준화 | Holding Tax Reconciliation 신뢰도 향상 |
| 3 | `holding_tax_to_operating_revenue` red 기준을 15%에서 18% 전후로 재검토하거나 percentile 병행 | sample-heavy 데이터에서 과잉 red 감소 |
| 4 | UI warning을 “예비 분석”과 “신고 목적 세액 아님” 중심으로 표준 문구화 | 리뷰어가 데이터 한계를 빠르게 이해 |

## UI 리스크 커뮤니케이션 권장 문구

- 자산별 상세 공시가격·고지세액 자료가 부족하여 회사 전체 Snapshot 기반 추정값을 사용합니다.
- 본 추정치는 신고 목적의 세액 산출이 아니라 보유세 부담의 방향성과 FFO 민감도를 파악하기 위한 예비 분석입니다.
- 공시가격 또는 고지세액 원자료가 부족한 항목은 데이터 부족으로 표시하며, 임의로 공식 세액처럼 표시하지 않습니다.
- `source_type = peer_snapshot_estimate`인 경우 자산별 비교보다 회사 전체 부담 수준과 요청자료 우선순위를 중심으로 해석해야 합니다.
- 최종 세무 판단에는 자산별 고지서, 토지대장, 건축물대장, 개별공시지가 조회자료 등 원자료 대사가 필요합니다.

## 한계 및 주의사항

- 현재 universe는 `reit_master.csv`의 8개 회사 Snapshot이다. 전체 상장리츠 공식 universe로 과대 해석하면 안 된다.
- `reit_peer_snapshot.csv`와 `reit_tax_snapshot.csv`는 공개 리뷰 안정성을 위한 Snapshot/sample 성격이다.
- SK리츠는 자산상세 CSV가 있으나 공식 자산별 tax dataset은 아직 없다. 다른 회사는 회사 전체 추정값 중심이다.
- Red Flag threshold는 표본 수가 작고 sample-heavy하므로 실제 API/공시 갱신 후 재보정이 필요하다.
- 이 보고서는 데이터 품질 개선을 위한 분석이며, 세무 자문·감사의견·투자판단을 제공하지 않는다.

## 다음 Codex 구현 작업 제안

```text
v13 Tax data reliability improvement task:
1. red_flag_rules.json에서 official_price_growth_placeholder의 metric을 official_price_growth_5y로 분리하고, red_flag_engine/calculations_peer가 해당 metric을 인식하도록 보완한다.
2. holding_tax_to_operating_revenue threshold를 sample distribution 기준으로 재검토하되, source_type이 peer_snapshot_estimate이면 경고 문구를 함께 표시한다.
3. reit_tax_snapshot_suggested.csv를 검토한 뒤 production reit_tax_snapshot.csv에 반영할지 결정한다.
4. Tax mode의 Memo와 표 하단에 source_type별 표준 disclaimer를 일관되게 표시한다.
5. 모든 회사에 대해 Tax Issue Matrix, Holding Tax Reconciliation, Request List, FFO stress, Memo 생성 regression test를 추가한다.
```
