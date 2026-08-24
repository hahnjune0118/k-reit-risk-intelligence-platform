# Streamlit–Marimo 기능 대조표

이 문서는 `app.py`의 Streamlit 경로와 `k_reits_marimo.py`의 Marimo 경로를 같은 계산 계약으로 대조한다. 화면 문구나 카드가 아니라 실제 데이터 원천과 계산 함수의 존재를 기준으로 분류한다.

| 영역 | 기존 Streamlit 계산 경로 | 작업 전 Marimo 상태 | 구현 우선순위 | 목표 상태 |
|---|---|---|---|---|
| 분석대상 리츠 선택 | `reit_master.csv` + `reit_peer_snapshot.csv` | 계산과 UI 모두 추가 작업 필요 | P0 | 복원 완료 |
| Peer Group / Benchmark | `calculate_peer_metrics`, `summarize_peer_position` | 계산 모듈은 있으나 화면에서 누락됨 | P0 | 복원 완료 |
| 거시경제 입력·확률가중 | `macro_scenario_parameters`, `build_forecast_scenario_probabilities` | 계산 모듈은 있으나 화면에서 누락됨 | P0 | 복원 완료 |
| 금리·차환·FFO·Cap rate 충격 | `build_interactive_scenario_outputs` | 계산 모듈은 있으나 화면에서 누락됨 | P0 | 복원 완료 |
| 위험점수·FFO·ICR·NAV·LTV·배당여력 | `calculate_reit_level_risk`, `build_interactive_scenario_outputs`, `scenario_verdict` | 계산 모듈은 있으나 화면에서 누락됨 | P0 | 복원 완료 |
| 자산·임차인 집중도 | `build_asset_concentration_table`, `build_tenant_exposure_table` | 계산 모듈은 있으나 화면에서 누락됨 | P0 | 복원 완료 |
| 차입금 만기·차환 부담 | `build_debt_stress_table`, 공시 차입금 스케줄 | 계산 모듈은 있으나 화면에서 누락됨 | P0 | 복원 완료 |
| 최근 5년 흐름·위험전이 | `build_historical_panel`, `build_macro_transmission_table` | 계산 모듈은 있으나 화면에서 누락됨 | P1 | Snapshot 범위 내 복원 |
| Peer Red Flag | `build_assurance_red_flags` | 계산 모듈은 있으나 화면에서 누락됨 | P1 | 복원 완료 |
| 감사계획·RMM·대응절차 | `build_rmm_mapping` 및 감사절차 표 | 일부 보유세 RMM만 이식됨 | P0 | 재무위험과 보유세 RMM을 통합 |
| 자산별 감사 우선순위 | `build_assurance_asset_priority` | 계산 모듈은 있으나 화면에서 누락됨 | P1 | 복원 완료 |
| KAM 후보·내부회계 핵심통제 | `build_kam_candidate_table`, `build_icfr_control_points` | 계산 모듈은 있으나 화면에서 누락됨 | P1 | 모의 감사검토 표현으로 복원 |
| 보유세 기준·중간·심각·사용자 시나리오 | `calculate_sensitivity_scenario` + v15 Tax 엔진 | 이미 이식됨 | P0 | 유지·고밀도 재배치 |
| 세목별 독립 재계산 | `build_view_model_from_snapshot` + Tax Rule Master | 이미 이식됨 | P0 | 유지·compact 조서로 재배치 |
| Evidence Matrix / Source Lineage / Fail-closed | v15 검증 Snapshot과 `marimo_assurance.py` | 이미 이식됨 | P0 | 유지·증거 페이지로 재배치 |
| P0/P1·요청자료·고지서 대사 | `issue_matrix`, `request_list`, `reconciliation` | 이미 이식됨 | P0 | 유지·결론과 연결 |
| CSV·Excel·Markdown·HTML 내보내기 | `src.tax_v15.reporting` | 이미 이식됨 | P0 | 로컬 Python 유지, WASM 제한 표기 |

## 데이터 및 계산 계약

- 상세 자산·차입금 계산은 현재 공식 상세 CSV가 있는 SK리츠에서만 수행한다. 다른 리츠 선택 시 Peer Snapshot 기반 지표만 표시하고 상세 자산 수치를 임의로 보간하지 않는다.
- 거시 입력은 기존 시나리오 규칙을 사용한다. 사용자 설정은 동일한 `build_interactive_scenario_outputs` 계산 경로를 호출한다.
- 보유세는 `data/v15/`의 검증 Snapshot과 세법 규칙 기준표를 사용한다. 공식 근거가 없으면 0으로 대체하지 않고 미확인·미대사로 남긴다.
- 기준 재계산액 `1,250,710,968.55472원`, P0 3건, P1 3건은 회귀 기준값이다.
- Streamlit UI 함수는 Marimo에서 호출하지 않는다. `data_loader.py`의 Streamlit 캐시 결합은 Marimo 전용 순수 Python 로더로 분리한다.

## 의도적으로 제외하거나 축약하는 항목

- 기준서 원문 전체, 데이터 사전 전체, 모든 중간 계산표는 첫 화면의 판단 밀도를 해치므로 접기 또는 기존 Streamlit에 남긴다.
- API 키가 필요한 실시간 ECOS/DART 호출은 Marimo 공개 화면에서 자동 실행하지 않는다. 키가 없는 경우 명시적인 Snapshot 기준 상태를 유지한다.
- 타 리츠의 자산별 임차인·만기 스케줄은 회사별 공식 상세 원천이 없으므로 Peer Snapshot proxy로만 표시한다.
