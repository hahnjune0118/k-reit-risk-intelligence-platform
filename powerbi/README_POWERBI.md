# Power BI Export Layer

이 폴더는 v14.1 기준 K-REITs Risk Intelligence Platform의 Tax workflow 검토용 CSV export를 보관합니다. Streamlit 앱의 계산 모듈과 동일한 source policy를 사용하며, Power BI 또는 Excel에서 보유세 부담, FFO proxy 스트레스, 요청자료, 데이터 한계를 검토할 수 있도록 설계했습니다.

## 생성 방법

저장소 루트에서 실행합니다.

```powershell
py scripts\export_powerbi_dataset.py
```

다른 폴더로 내보내려면 다음처럼 실행합니다.

```powershell
py scripts\export_powerbi_dataset.py --output-dir C:\path\to\exports
```

스크립트는 한국어 라벨이 Power BI와 Excel에서 안정적으로 열리도록 UTF-8-BOM CSV를 `powerbi/exports/`에 생성합니다.

## 테이블

- `dim_reit.csv`: REITs 회사 마스터 차원입니다. `stock_code`는 텍스트로 불러옵니다.
- `fact_reit_kpi.csv`: 회사별 최신 KPI와 peer benchmark 지표입니다.
- `fact_tax_bridge.csv`: 회사별 Holding Tax Bridge 단계입니다.
- `fact_tax_issue.csv`: Tax Issue Matrix와 위험수준 정렬 키입니다.
- `fact_tax_request.csv`: 요청자료 목록과 우선순위 정렬 키입니다.
- `fact_tax_reconciliation.csv`: 자산별 또는 회사 단위 보유세 reconciliation입니다.
- `fact_ffo_stress.csv`: FFO proxy 현금유출 stress scenario입니다.
- `fact_tax_validation.csv`: 입력값 검증, fallback 상태, 계산 한계입니다.
- `dim_source_policy.csv`: source_type별 신뢰도, 사용 조건, 제한사항입니다.

## 모델링 권장사항

- `dim_reit[stock_code]` 1:* 각 fact table의 `stock_code`
- `dim_source_policy[source_type]` 1:* `source_type`을 포함한 fact table

정렬 컬럼:

- Risk: `risk_sort` (`높음`=1, `주의`=2, `데이터 부족`=3, `정상`=4)
- Priority: `priority_sort` (`높음`=1, `중간`=2, `낮음`=3)
- Source reliability: `reliability_sort`

## 단위

- `_eok`으로 끝나는 컬럼은 억원 단위입니다.
- 비율 필드는 표시용 문자열이 아니라 decimal ratio입니다.
- `stock_code`는 앞자리 0 손실을 방지하기 위해 텍스트로 가져옵니다.

## Source Policy

추정값은 `source_type`과 `source_note`를 유지합니다. 이를 통해 공식 공시자료, API 수집자료, Snapshot 데이터, Peer Snapshot estimate, Sample estimate, Data insufficient 상태를 시각화에서 구분할 수 있습니다.

본 export는 예비 리스크 분석과 Tax workflow control을 위한 자료입니다. 신고 목적 세액 산출, 법률의견, 세무신고서, 투자 추천을 대체하지 않습니다.
