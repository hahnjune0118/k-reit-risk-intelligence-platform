# K-REITs Risk Intelligence Platform v14.1 Ground Truth Validation

> 검증 기준일: 2026-07-14
> 검증 방식: read-only 독립 검증. 애플리케이션·계산 로직·기존 데이터는 수정하지 않음.
> 단위: 별도 표시가 없으면 백만원.
> 결론 성격: 공개자료 기반 예비 검증이며 세무신고, 법률의견, 감사증거 또는 투자판단을 대체하지 않음.

## 1. Executive Summary

### 결론

v14.1은 **Tax screening workflow, source limitation 표시, 비SK 상세데이터 차단, Streamlit-Power BI export 구조**는 유용한 프로토타입 수준입니다. 그러나 현재 정량 결과를 외부 제출용 Ground Truth 또는 신고·감사 결론으로 제시하기에는 **P0 4건, P1 15건**이 남아 있습니다.

가장 중요한 결론은 다음과 같습니다.

1. `borrowings_current`는 대표 3사의 공식 유동성 이자부 차입부채와 일치하지 않으며, SK리츠에서는 공식 **유동부채**와 동일해 mapping 오류 가능성이 높습니다.
2. 보유세 브리지는 적용세율 1.1%를 보여 주지만 Snapshot 세액이 있으면 그 세액을 그대로 사용합니다. 세 회사의 implied rate는 1.4643%~1.7869%입니다.
3. 공시가격 상승률 Red Flag가 실제로는 `holding_tax_to_ffo`를 사용합니다.
4. 최근 5년 재산세·도시지역분·지방교육세는 고지서가 아니라 최신 추정세액을 60%/30%/10%로 임의 배분한 합성 시계열입니다.
5. 롯데리츠와 ESR켄달스퀘어리츠의 재무 Snapshot은 공식 최신 사업보고서와 직접 조정되지 않으며, SK리츠는 연결/별도와 분기 연환산 값이 혼합되어 있습니다.

엄격 일치율은 **프로젝트에 값이 있고 공식 동기간·동범위 값도 확인되는 항목**을 분모로 하며 `match`와 `rounding_difference`만 일치로 보았습니다. 기간·범위 차이는 불일치로 포함했습니다.

| 회사 | 종목코드 | DART corp code | 공식 보고서 | 공식 기간 | 범위 | 엄격 일치율 |
|---|---|---|---|---|---|---|
| SK리츠 | 395400 | 01535150 | 사업보고서 / 2026-06-10 | 재무상태 2026-03-31; 손익·현금흐름 2026-01-01~2026-03-31 | 연결(CFS) | 3/11 (27.3%) |
| 롯데리츠 | 330590 | 01363818 | 사업보고서 / 2026-03-10 | 재무상태 2025-12-31; 손익·현금흐름 2025-07-01~2025-12-31 | 별도(OFS) | 0/10 (0.0%) |
| ESR켄달스퀘어리츠 | 365550 | 01437186 | 사업보고서 / 2026-02-13 | 재무상태 2025-11-30; 손익·현금흐름 2025-06-01~2025-11-30 | 연결(CFS) | 0/10 (0.0%) |

SK리츠의 직접 비교 가능한 재무상태 핵심 4개 항목(총자산, 투자부동산, 이자부 차입부채, 유동성 이자부 차입부채)만 보면 3/4(75.0%)가 일치합니다. 전체 엄격 일치율이 27.3%인 이유는 Snapshot 손익·현금흐름이 연환산 또는 다른 범위를 사용하기 때문입니다.

### 이슈 요약

| 등급 | 건수 | 의미 |
|---|---|---|
| P0 | 4 | 수치·mapping·세목 표시의 즉시 수정 필요 오류 |
| P1 | 15 | Tax/Assurance 결론과 제출 신뢰성에 중대한 영향 |
| P2 | 7 | 설명 가능성·확장성·Power BI UX 위험 |
| P3 | 4 | 차기 자동화·운영 고도화 |

### 제출 가능성

- **정량 보유세 산출물 또는 공식 Ground Truth 제출:** 현재 불가.
- **Tax/Assurance workflow 자동화 프로토타입 시연:** P0를 수정하고 모든 수치를 Snapshot/estimate로 명확히 제한하면 조건부 가능.
- **Power BI 포트폴리오 시연:** 현재 export 수치 자체는 Streamlit 입력과 일치하지만 Peer median과 연도 filter를 수정한 뒤 권장.

## 2. 검증 범위와 한계

### 검증 범위

- 코드: `app.py`, `config.py`, `dart_financials.py`, `api_manager.py`, `data_source_policy.py`, `data_availability.py`, `tax_data_loader.py`, `calculations_peer.py`, `calculations_holding_tax_bridge.py`, `calculations_tax_review_pack.py`, `red_flag_engine.py`, `tax_request_mapping.py`, `tax_validation.py`, `ui_tax.py`, `ui_methodology.py`, `scripts/export_powerbi_dataset.py`.
- 데이터: `data/reit_master.csv`, `data/reit_peer_snapshot.csv`, `data/reit_tax_snapshot.csv`, `data/red_flag_rules.json`, SK 상세 CSV.
- 출력: `powerbi/exports/*.csv`, TMDL table/measure/relationship 정의.
- 대표회사: SK리츠, 롯데리츠, ESR켄달스퀘어리츠.
- 공식 원천: DART/OpenDART XBRL 및 국가법령정보센터.

### 검증 한계

- 서버 API Key는 로컬에서 설정되지 않아 DART/ECOS/V-World live 호출 대신 공식 DART 원문과 다운로드 XBRL을 독립 조회했습니다.
- 자산별 재산세 고지서, 과세대장, PNU별 공시지가·건축물 시가표준액, 감면 결정, 종합부동산세 고지서는 공개 공시에서 확보하지 못했습니다.
- 롯데리츠·ESR켄달스퀘어리츠의 공식 FFO bridge는 최신 XBRL에서 확인하지 못했습니다.
- SK Cap rate/WALE CSV가 참조하는 Annual Report/투자보고서 원문 파일은 저장소에 없으므로 source metadata와 DART 공시 일부만 대조했습니다.

## 3. 저장소 및 데이터 흐름

### 기준 상태

- 버전: `v14.1`, `APP_VERSION_NAME = Metric Definition & Source Lineage Stabilization`.
- 기준 커밋: `bcd934e Finalize v14.1 Tax metrics, source lineage, and API fallback controls`.
- 작업 시작 전 기존 변경: `.gitignore`, Power BI PBIX/export, `scripts/export_powerbi_dataset.py`, PBIP/PBIR/TMDL 및 자동화 파일. 기존 변경은 초기화하지 않았습니다.
- 초기 테스트: `47 passed`.

### 데이터 흐름

`DART/API 또는 bundled CSV` → `loading/normalization` → `metric calculation` → `Streamlit UI` → `Tax Review Pack` → `powerbi/exports` → `TMDL measures`

상세 계보는 [source_lineage.csv](source_lineage.csv)에 대표 3사×24개 지표군, 총 72개 회사-지표 행으로 기록했습니다.

주요 취약점은 회사 행 단위 `source_type` 하나가 여러 지표의 서로 다른 원천·기간·범위를 대표한다는 점입니다. SK Snapshot 한 행 안에서도 연결 재무상태, 연결 분기 연환산 손익, 별도 투자보고서 연환산 FFO가 섞여 있습니다.

## 4. 대표회사 Ground Truth 결과

### 공식 보고서

1. [SK리츠 사업보고서 2026-06-10](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260610000569), DART corp code `01535150`, 연결 기준.
2. [롯데리츠 사업보고서 2026-03-10](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260310002810), DART corp code `01363818`, 별도 기준.
3. [ESR켄달스퀘어리츠 사업보고서 2026-02-13](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260213002140), DART corp code `01437186`, 연결 기준.

### 핵심 차이

- **SK리츠:** 총자산 5,408,832, 투자부동산 5,232,672, 이자부 차입부채 3,103,855는 공식 공시와 반올림 수준에서 일치합니다. 그러나 `borrowings_current` 1,318,000은 공식 유동성 이자부 차입부채 1,243,689.893이 아니라 공식 유동부채 1,318,000.437과 일치합니다.
- **롯데리츠:** 프로젝트 총자산 2,460,000 vs 공식 2,594,407.042(-5.18%), 투자부동산 2,315,000 vs 공식 2,527,222.595(-8.40%), 총 이자부 차입부채 1,298,000 vs 공식 1,307,019.778(-0.69%). 차입부채 차이는 작지만 반올림이 아닌 90억원 규모이며 lineage가 없습니다.
- **ESR켄달스퀘어리츠:** 프로젝트 총자산 3,135,000 vs 공식 2,835,773.540(+10.55%), 투자부동산 3,010,000 vs 공식 2,433,793.981(+23.68%), 차입부채 1,645,000 vs 공식 1,586,961.428(+3.66%). 프로젝트 순이익 +52,900과 공식 최신 연결 반기 순손실 -3,436.388은 부호도 다릅니다.

전체 계정별 결과는 [financial_reconciliation.csv](financial_reconciliation.csv)에 72행으로 제공했습니다.

## 5. 보유세 계산 검증

### 법령 기준일과 확인한 기본식

법령 검토 기준일은 **2026-07-14**입니다.

- 지방세법은 2026-07-01 시행 법률, 지방세법 시행령은 2026-06-01 시행 대통령령을 기준으로 확인했습니다.
- 지방세법 제111조: 별도합산 토지는 2억원 이하 0.2%, 2억원 초과 10억원 이하 0.3% 누진, 10억원 초과 0.4% 누진. 일반 건축물 0.25%.
- 지방세법 제112조: 도시지역분 표준세율 0.14%, 조례로 0.23% 이하 조정 가능.
- 지방세법 제151조: 도시지역분을 제외한 재산세액의 20%를 지방교육세로 계산.
- 지방세법 시행령 제109조: 토지·건축물 공정시장가액비율 70%.
- 종합부동산세법은 2026-01-01 시행 법령이 존재하나 현재 모델은 이를 계산하지 않습니다.

공식 근거:

- [지방세법 제111조](https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0111&lsiSeq=282559&urlMode=lsScJoRltInfoR)
- [지방세법 제112조](https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0112&lsiSeq=282559&urlMode=lsScJoRltInfoR)
- [지방세법 제151조](https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0151&lsiSeq=282559&urlMode=lsScJoRltInfoR)
- [지방세법 시행령 제109조](https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0109&lsiSeq=286395&urlMode=lsScJoRltInfoR)
- [종합부동산세법](https://law.go.kr/LSW/lsInfoP.do?lsiSeq=280417)

### 실제 구현 경로

1. 상세 estimator `calculations_tax.py`는 기본 재산세·도시지역분·지방교육세 산식의 주요 표준세율과 일치합니다.
2. 그러나 주 Tax UI 경로는 자산별 상세 estimator가 아니라 `reit_tax_snapshot.csv`의 회사 전체 추정세액을 우선 사용합니다.
3. `tax_data_loader.py` fallback은 `official_price × 1.1%`, 브리지는 `official_price × 70% × 1.1%`이므로 경로가 다릅니다.
4. Snapshot 세액이 있으면 브리지에서 사용자가 보는 적용세율을 무시하고 저장 세액을 유지합니다.

| 회사 | 추정 과세표준 | Snapshot 세액 | Implied rate | 1.1% 계산 세액 | 차이 |
|---|---|---|---|---|---|
| SK리츠 | 2,014,579.0 | 29,500.0 | 1.4643% | 22,160.4 | 7,339.6 |
| 롯데리츠 | 924,000.0 | 15,800.0 | 1.7100% | 10,164.0 | 5,636.0 |
| ESR켄달스퀘어리츠 | 1,040,900.0 | 18,600.0 | 1.7869% | 11,449.9 | 7,150.1 |

### 세목 coverage

| 세목 | 상세 estimator | 회사 전체 Snapshot 경로 | 판단 |
|---|---|---|---|
| 재산세 본세 | 기본 토지·건축물 식 일부 | Snapshot 총액에 내재한다고 가정 | 부분 검증 |
| 도시지역분 | 0.14% | Snapshot 총액에 내재한다고 가정 | 부분 검증 |
| 지방교육세 | 재산세 본세의 20% | Snapshot 총액에 내재한다고 가정 | 부분 검증 |
| 지역자원시설세 | 제외 | 제외 | 추가 자료 필요 |
| 종합부동산세 | 제외 | 제외 | 추가 자료 필요 |
| 농어촌특별세 | 제외 | 제외 | 추가 자료 필요 |
| 해외 부동산 현지 보유세 | 제외 | 제외 | 추가 자료 필요 |
| 감면·합산·분리과세·세부담상한 | 단순 option 일부 | 미반영 | 추가 자료 필요 |

### 공시 비용과의 대사

세 회사 모두 프로젝트 추정세액과 공시된 세금/관련 비용은 **비교 불가**입니다. 공시 계정은 기간·세목·연결범위가 다르고, 롯데리츠는 직접운영비용에 감가상각·수수료·보험료·세금이 함께 포함됩니다. 상세 결과는 [holding_tax_reconciliation.csv](holding_tax_reconciliation.csv)입니다.

## 6. FFO proxy 검증

### 구현식

현재 구현은 다음과 같습니다.

`FFO proxy = Snapshot ffo_proxy 우선; 없으면 영업활동현금흐름; 없으면 영업이익; 없으면 당기순이익`

따라서 정식 FFO처럼 `순이익 + 감가상각 - 부동산 처분이익 - 공정가치평가이익 ± 비경상 조정` bridge를 수행하지 않습니다.

| 회사 | 시작 항목 | 가산 | 차감 | 기타 조정 | 프로젝트 FFO | 공시/참조 FFO | 차이 | 판정 |
|---|---|---|---|---|---|---|---|---|
| SK리츠 | 별도 투자보고서 공시 FFO 22,134 | 원문 조정 bridge 미보관 | 원문 조정 bridge 미보관 | 4배 연환산 | 88,536.0 | 22,134.0 | 66,402.0 | period_difference |
| 롯데리츠 | Snapshot ffo_proxy 직접값 | 미제공 | 미제공 | 공식 FFO 및 조정내역 미확인 | 52,100.0 | - | - | unverifiable |
| ESR켄달스퀘어리츠 | Snapshot ffo_proxy 직접값 | 미제공 | 미제공 | 공식 FFO 및 조정내역 미확인 | 74,300.0 | - | - | unverifiable |

SK리츠 FFO 22,134는 `data/sk_reit_latest_kpis.csv`의 별도 투자보고서 source metadata를 근거로 했으며, 프로젝트 88,536은 정확히 4배입니다. 해당 원문이 저장소에 없고 주 Snapshot은 연결 재무상태 수치와 혼합되므로 `period_difference`로 판정했습니다. 롯데·ESR은 공식 FFO 조정표를 확인하지 못해 `unverifiable`입니다.

### Tax screening KPI 적합성

| KPI | 장점 | 한계 | 데이터 확보 | 판단 |
|---|---|---|---|---|
| 보유세 / FFO proxy | 배당·반복 현금창출력과 연결 | 회사별 proxy 정의 불일치 | 현재 있음 | 보조지표 |
| 보유세 / CFO | 현금흐름표 공시와 직접 대사 가능 | 운전자본·일회성 변동 큼 | DART 가능 | 검증용 보조지표 |
| 보유세 / 영업수익 | 회사 간 단순 비교 | 수익성·임대차 비용전가 반영 못함 | 현재 있음 | 보조지표 |
| 보유세 / NOI | 자산 세부담과 가장 직접적 | 자산별 정상화 NOI 확보 어려움 | 현재 부족 | 권장 핵심지표 |
| 보유세 / 배당가능이익 | 실제 배당제약과 연결 | 법정 계산·별도재무제표 자료 필요 | 현재 부족 | 실무 검토지표 |

## 7. 총부채·차입금·충당부채 검증

### 구분

- 총부채: 재무상태표의 모든 부채. 차입금, 사채, 리스부채, 매입채무, 미지급비용, 충당부채, 이연법인세부채 등을 포함합니다.
- 이자부 차입부채: 단기차입금 + 유동성장기차입금 + 장기차입금 + 사채 + 정책상 포함한 리스부채.
- 비이자성 부채: 매입채무, 미지급비용, 충당부채, 이연법인세부채 등.

### 검증 결과

- 장부기준 NAV proxy는 총자산-총부채로 정의되어 충당부채도 총부채를 통해 포함합니다. 정의는 적정합니다.
- Gross debt/LTV는 이자부 차입부채를 사용하고 충당부채를 제외합니다. 정의는 적정합니다.
- 현재 Power BI export의 `total_liabilities_eok`, `provisions_eok`, `cash_and_cash_equivalents_eok`, `book_nav_proxy_eok`는 Snapshot schema 한계로 공란입니다.
- 가장 큰 오류는 `borrowings_current`입니다. 이 값은 Assurance에서 유동성 차입금 비율로 사용되지만 공식 XBRL 계정과 조정되지 않습니다.
- `derive_interest_bearing_debt`는 하나의 구성계정만 확보되어도 부분합을 전체 차입부채로 반환합니다. 구성 completeness 검사가 필요합니다.

## 8. NAV·LTV·이자감당력 검증

상세 정의와 판단은 [metric_definition_matrix.csv](metric_definition_matrix.csv)에 17개 지표로 정리했습니다.

- `장부기준 NAV proxy = 총자산 - 총부채`: 시장가치 NAV와 구분되어 있어 명칭은 적정합니다.
- `총자산 기준 Gross LTV = 이자부 차입부채 / 총자산`: 담보 LTV가 아니라 총자산 차입비율입니다. 현재 명칭은 구분을 제공합니다.
- `Property LTV = 이자부 차입부채 / 투자부동산 장부금액`: 담보별 debt/value가 아니라 회사 전체 부채와 장부가를 사용합니다.
- `FFO 이자감당력 proxy = FFO proxy / 이자비용`: 분자·분모의 기간·연결범위가 동일해야 하나 Snapshot metadata가 이를 보장하지 않습니다.
- `유효차입금리 proxy = 이자비용 / 평균 이자부 차입부채`: 평균잔액이 없으면 기말잔액 proxy를 쓰므로 반드시 proxy 표기가 필요합니다.

## 9. Source Reliability 검증

| source_type | 현재 해석 | 검증 판단 |
|---|---|---|
| official_disclosure | DART/API 공식 공시 | 적정하나 field-level period/scope 필요 |
| api_snapshot | API/Snapshot | sample_snapshot alias 때문에 현재 과대표시 가능 |
| peer_snapshot | Peer 비교 Snapshot | 기준일·범위·원문 reference 필수 |
| peer_snapshot_estimate | Peer 기반 추정 | 대표 Tax 데이터의 실제 상태와 부합 |
| sample_estimate | 예시·추정 | SK 상세 sample에 적합 |
| data_insufficient | 데이터 부족 | 비SK 상세 차단에 적합 |

가장 중요한 source 이슈는 `data_source_policy.py:74`의 `sample_snapshot -> api_snapshot` alias입니다. 현재 `reit_peer_snapshot.csv`는 명시적으로 `sample_snapshot`인데 UI·export 정책에서는 API/Snapshot으로 승격될 수 있습니다. 또한 `reit_master.csv`의 대표회사 DART corp code가 실제 `01535150`, `01363818`, `01437186`가 아니라 `sample_001` 등입니다.

권장 최소 source grain은 다음입니다.

`company + metric + reporting_period + statement_scope + source_document + account_id + transformation + annualized_flag + source_type`

## 10. 비SK 데이터 재사용 검증

| 회사 | SK 자산명 | SK 임차인 | SK Cap rate/WALE | 판정 |
|---|---|---|---|---|
| 롯데리츠 | 미검출 | 미검출 | data_insufficient | 검증 완료 |
| ESR켄달스퀘어리츠 | 미검출 | 미검출 | data_insufficient | 검증 완료 |
| 제이알글로벌리츠 | 미검출 | 미검출 | data_insufficient | 검증 완료 |
| 신한알파리츠 | 미검출 | 미검출 | data_insufficient | 검증 완료 |

`data_availability.py`는 SK리츠/395400만 상세 sample 회사로 인정하고 비SK 회사의 asset, tax asset, debt maturity, Cap rate, tenant detail을 차단합니다. `tests/test_no_sk_data_reuse.py`와 `tests/test_non_sk_tax_pack.py`도 이를 검증합니다. 따라서 **직접적인 SK 자산·임차인·Cap rate·WALE 재사용은 발견하지 못했습니다.**

다만 모든 회사가 동일한 합성 Peer/Tax Snapshot 구조와 generic Request List를 쓰는 것은 별도 문제이며, 이는 데이터 재사용이 아니라 source 품질·회사별 relevance 문제로 P1/P2에 기록했습니다.

## 11. Streamlit·Power BI Reconciliation

| 회사 | 추정 보유세 | FFO proxy | 보유세/FFO | Gross LTV | CSV/Measure |
|---|---|---|---|---|---|
| SK리츠 | 29,500.0 | 88,536.0 | 33.3% | 57.4% | CSV와 Measure 산식 일치 |
| 롯데리츠 | 15,800.0 | 52,100.0 | 30.3% | 52.8% | CSV와 Measure 산식 일치 |
| ESR켄달스퀘어리츠 | 18,600.0 | 74,300.0 | 25.0% | 52.5% | CSV와 Measure 산식 일치 |

| 회사 | Issue 행 | Request 행 | Validation 행 |
|---|---|---|---|
| SK리츠 | 6 | 11 | 1 |
| 롯데리츠 | 6 | 11 | 1 |
| ESR켄달스퀘어리츠 | 6 | 11 | 1 |

검증 결과:

- Power BI ratio는 ratio column의 합계가 아니라 `DIVIDE(SUM numerator, SUM denominator)`로 재계산합니다. 이 부분은 적정합니다.
- 대표 3사의 `estimated_holding_tax`, `ffo_proxy`, `holding_tax_to_ffo`, `debt_to_assets`는 Streamlit 입력 Snapshot과 Power BI export에서 일치합니다.
- 현재 export key 중 대표 사실표에서 회사·연도 중복은 발견되지 않았습니다.
- Peer median은 `ALLSELECTED(DimREIT[company_name])`를 사용해 단일 회사 slicer에서 target value로 축소될 수 있습니다.
- 모든 Fact 관계가 `stock_code`에만 연결되어 공통 연도 slicer가 Issue/Request/Stress 전체를 일관되게 필터링하지 않습니다.
- TMDL Power Query는 로컬 절대경로를 사용해 다른 검토자 환경에서 refresh가 실패할 수 있습니다.
- 대표 3사 모두 Request 11행 중 고유 요청자료명은 10개입니다. `자산별 장부가액 명세`가 서로 다른 목적·이슈로 2회 생성되며 현재 Request count는 행 수를 세므로 1건 과대 표시됩니다.

## 12. Red Flag·Request Mapping 검증

### Red Flag

| rule id | metric | threshold | 비교·발생 조건 | 데이터 가용성 | Tax 의미 | Request/Memo 연결 | 오류 여부 |
|---|---|---|---|---|---|---|---|
| `holding_tax_to_ffo` | `holding_tax_to_ffo` | 주의 25%, 높음 35% 또는 Peer percentile | 높을수록 위험 | 값은 있으나 분자·분모 모두 추정 | 현금창출력 대비 세부담 | issue→재산세 고지서·FFO 자료→Memo | 산식 연결은 맞으나 threshold 근거 미검증 |
| `holding_tax_to_operating_revenue` | `holding_tax_to_operating_revenue` | 주의 10%, 높음 15% 또는 Peer percentile | 높을수록 위험 | 값은 있으나 기간 불일치 가능 | 매출 대비 세부담·전가 구조 | 임대차계약·관리비 정산→Memo | 기간·scope 보정 필요 |
| `official_price_to_investment_property` | `official_price_to_investment_property` | 주의 55%, 높음 65% 또는 Peer percentile | 높을수록 위험 | 회사 전체 추정 공시가격 | 장부가 대비 과세기준 proxy | 공시가격·감정평가·면적자료→Memo | 공식 자산별 공시가격 부재 |
| `official_price_growth_placeholder` | `holding_tax_to_ffo` | 주의 30%, 높음 40% 또는 Peer percentile | FFO 비율로 발생 | 실제 공시가격 성장률 없음 | 의도는 가격상승 위험 | 최근 5년 가격·고지서→Memo | **P0: metric 오연결** |

P0 확인:

```text
rule id: official_price_growth_placeholder
label: 공시가격 상승률 추가 검토
metric: holding_tax_to_ffo
```

이 규칙은 공시가격 성장률을 측정하지 않습니다. 대표회사 issue export에서 SK·롯데는 FFO 비율 때문에 공시가격 상승률 주의로 표시되고 ESR은 정상으로 표시됩니다.

### Request List

대표 3사는 각각 11개 요청자료를 생성하며 재산세 고지서, 개별공시지가, FFO proxy 산정자료, 배당가능이익, 자산별 장부가액, 토지대장, 건축물대장을 포함합니다. 기본 구조는 실무적으로 유용합니다.

누락 또는 보완 필요 자료:

- 종합부동산세 고지서와 농어촌특별세 내역.
- 자산별 법적 소유자·수익증권/SPC/신탁 구조 및 납세의무자 확인 자료.
- 책임임대차상 세금 pass-through 조항.
- 해외자산 현지 보유세 고지서.
- 감면·합산배제·세부담상한 적용 근거.

## 13. Tax Review Memo 검증

현재 Memo는 다음 6개 섹션입니다: 검토 대상, 핵심 수치 요약, 주요 Tax 이슈, 요청자료, 실무적 시사점, 제한 및 유의사항.

장점:

- `source_type`, `source_note`, 신뢰수준, estimate limitation을 표시합니다.
- 공식 FFO가 아니라 `FFO proxy`, 확정세액이 아니라 `추정 보유세`로 표시합니다.
- data_insufficient 상태에서 확정적 결론을 피하는 제한문구가 있습니다.

보완 필요:

- 요구되는 9개 구조 중 사실관계, 관련 법적 근거, 잠정 분석이 분리되지 않습니다.
- `reconciliation.iloc[0]`, `bridge.iloc[0]`만 사용해 다자산 합계를 누락할 수 있습니다.
- 세법 조문과 적용/미적용 세목이 Memo에 직접 연결되지 않습니다.
- Request List와 Red Flag는 연결되지만 P0 placeholder rule 때문에 잘못 연결될 수 있습니다.

## 14. 테스트 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| `py -m compileall -q . -x ...` | 통과 | 검증 스크립트 포함 syntax check |
| `py -m pytest -q` | 47 passed | 기존 로직 테스트 |
| `py .\scripts\export_powerbi_dataset.py` | 통과 | 9개 CSV 재생성/검증 |
| 비SK SK-data 재사용 | 통과 | 기존 전용 테스트 및 경로 검토 |
| divide-by-zero | 통과 | 기존 테스트 |
| Source metadata 존재 | 통과 | 기존 구조 테스트 |
| 공식 공시 Ground Truth 회귀 | 미구현 | 본 보고서에서 수동 독립 대조 |
| 보유세 세율-세액 조정 | 실패 | P0-02 |
| Power BI slicer context | 정적 위험 확인 | P1-13, P1-14 |

테스트가 통과해도 P0가 남는 이유는 현재 테스트 fixture가 Snapshot 자체의 내부 재현성을 검증할 뿐, 공식 공시·법정 산식과의 외부 조정을 검증하지 않기 때문입니다.

## 15. P0~P3 개선사항

| 등급 | 건수 | 의미 |
|---|---|---|
| P0 | 4 | 수치·mapping·세목 표시의 즉시 수정 필요 오류 |
| P1 | 15 | Tax/Assurance 결론과 제출 신뢰성에 중대한 영향 |
| P2 | 7 | 설명 가능성·확장성·Power BI UX 위험 |
| P3 | 4 | 차기 자동화·운영 고도화 |

### P0 상세

| ID | 오류 | 핵심 증거 | 영향 |
|---|---|---|---|
| P0-01 | borrowings_current가 유동성 이자부 차입부채와 일치하지 않음 | SK 1,318,000은 공식 유동부채 1,318,000.437과 일치하나 공식 유동성 이자부 차입부채는 1,243,689.893. 롯데·ESR도 각각 -52.6%, +26.3% 차이. | 유동성 차입금 비율과 차환 Red Flag가 잘못 산출됨 |
| P0-02 | 보유세 브리지의 표시 세율이 Snapshot 세액에 적용되지 않음 | 표시 1.1% 대비 Snapshot implied rate는 SK 1.4643%, 롯데 1.7100%, ESR 1.7869%. Snapshot 세액이 있으면 rate slider를 우회. | 동일 화면의 세율·과세표준·세액이 수학적으로 조정되지 않음 |
| P0-03 | 공시가격 상승률 규칙이 holding_tax_to_ffo를 참조 | rule id official_price_growth_placeholder의 metric이 holding_tax_to_ffo로 설정됨 | 공시가격 상승 위험이 FFO 비율로 발생하고 Request/Memo까지 잘못 전파됨 |
| P0-04 | 5년 보유세 세목을 60%/30%/10%로 임의 배분 | 최신 추정세액을 역산한 뒤 재산세 60%, 도시지역분 30%, 지방교육세 10%로 고정 배분 | 법정 산식과 무관한 세목별 금액이 실제 추이처럼 표시됨 |

전체 이슈와 재현 경로는 [p0_p3_issue_register.csv](p0_p3_issue_register.csv)에 30건으로 기록했습니다.

## 16. 최종 제출 가능성

### 현재 가능한 제출

- 아키텍처, 보안, source limitation, 비SK isolation, Tax Review Pack workflow를 설명하는 **프로토타입 포트폴리오**.
- 모든 정량값을 `Snapshot/estimate/proxy`로 명확히 제한한 화면 시연.

### 현재 불가능한 제출

- 회사별 확정 보유세 또는 신고세액 산출.
- PNU/고지서 없이 공시가격·과세표준·보유세를 공식값으로 주장.
- FFO proxy를 공식 FFO로 주장.
- 현재 `borrowings_current` 기반 차환위험을 공시 Ground Truth로 주장.
- 현재 공시가격 상승률 Red Flag를 회사별 사실로 주장.

## 17. 검증하지 못한 항목

1. 대표 3사의 자산별 최신 PNU, 토지 개별공시지가, 건축물 시가표준액.
2. 자산별 재산세·도시지역분·지방교육세·지역자원시설세 고지서.
3. 종합부동산세·농어촌특별세와 합산배제·감면 내역.
4. 연결 자산별 법적 소유자와 실제 납세의무자, 임차인 세금 부담 조항 전체.
5. 롯데리츠·ESR켄달스퀘어리츠의 공식 FFO bridge.
6. SK 상세 Cap rate/WALE source 문서의 페이지별 원문 재수행.
7. 해외부동산 현지 보유세와 환율 기준.
8. Power BI Desktop에서의 실제 slicer interaction. TMDL 정적 검토만 수행했습니다.

각 항목의 상태는 `원자료 추가 필요` 또는 `부분 검증`이며, 0 또는 Peer 평균으로 대체하지 않았습니다.

## 18. 다음 수정 권고

수정은 별도 승인 후 다음 순서로 진행하는 것이 안전합니다.

1. `borrowings_current`를 공식 유동성 이자부 차입계정으로 재구축하고 대표회사 fixture를 추가합니다.
2. 보유세 브리지에서 Snapshot 세액과 가정 세율 중 하나만 authoritative input으로 선택하고 수학적 조정을 강제합니다.
3. `official_price_growth_placeholder`를 비활성화하거나 실제 성장률 metric으로 교체합니다.
4. 합성 5개년 세목 배분을 제거하고 총액 Scenario 또는 `data_insufficient`로 대체합니다.
5. 회사·지표·기간·연결범위·연환산·account_id 단위 source lineage를 도입합니다.
6. 자산별 PNU·고지서·법적 소유자/납세의무자 정보를 확보한 뒤 보유세 산식을 확장합니다.
7. 공식 FFO bridge를 확보하지 못한 회사는 CFO/영업이익 proxy를 별도 유형으로 분리합니다.
8. Power BI Peer median과 공통 기간 dimension을 수정하고 filter-context 회귀 테스트를 추가합니다.
9. Memo를 9개 표준 섹션으로 확장하고 법령 근거·사실·추정·잠정 결론을 분리합니다.

---

검증 산출물은 애플리케이션 코드를 수정하지 않고 생성했습니다. commit과 push는 수행하지 않았습니다.
