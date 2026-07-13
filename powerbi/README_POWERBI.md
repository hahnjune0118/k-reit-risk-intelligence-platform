# Power BI Export Layer

This folder contains the v14 Power BI-ready export surface for the K-REIT Risk Intelligence Platform tax workflow.

## Generate

Run from the repository root:

```powershell
py scripts\export_powerbi_dataset.py
```

To write to a different folder:

```powershell
py scripts\export_powerbi_dataset.py --output-dir C:\path\to\exports
```

The script writes UTF-8-BOM CSV files to `powerbi/exports/` so Korean labels open correctly in Power BI and Excel.

## Tables

- `dim_reit.csv`: REIT master dimension. Use `stock_code` as text.
- `fact_reit_kpi.csv`: latest company KPI and peer metrics.
- `fact_tax_bridge.csv`: holding tax bridge stages for each company.
- `fact_tax_issue.csv`: tax issue matrix with risk sort keys.
- `fact_tax_request.csv`: request list with priority sort keys.
- `fact_tax_reconciliation.csv`: asset-level or company-level holding tax reconciliation.
- `fact_ffo_stress.csv`: FFO cash-outflow stress scenarios.
- `fact_tax_validation.csv`: input validation, fallback status, and calculation limitations.
- `dim_source_policy.csv`: source policy labels, reliability levels, and limitation text.

## Model

Recommended relationships:

- `dim_reit[stock_code]` 1:* each fact table `stock_code`
- `dim_source_policy[source_type]` 1:* fact tables that contain `source_type`

Sort columns:

- Risk: `risk_sort` where 높음=1, 주의=2, 데이터 부족=3, 정상=4
- Priority: `priority_sort` where 높음=1, 중간=2, 낮음=3
- Source reliability: `reliability_sort`

## Units

- Columns ending in `_eok` are 억원.
- Ratio fields are decimals, not formatted strings.
- `stock_code` should be imported as text in Power BI.

## Source Policy

The export reuses the v14 source policy and tax calculation modules. Estimated values keep `source_type` and `source_note` so visuals can distinguish official disclosure, API or snapshot data, peer snapshot estimates, sample estimates, and data-insufficient cases.

The dataset is for preliminary risk intelligence and tax review workflow control. It is not a filing calculation, legal opinion, tax return, or investment recommendation.
