# Codex Handoff — K-REIT Risk Intelligence Platform

## 1. Project identity

Project name: **K-REIT Risk Intelligence Platform**

One-line description:

> A disclosure-based analytics platform that links listed Korean REIT disclosures, macro indicators, market prices, asset-level exposure, debt schedules, and tax-relevant assessed values to identify early risk signals for Assurance, Tax, and Deals use cases.

Current product stage:

- Current stable version: `reits_analysis_app_v10_holding_tax_general_scenario.py`
- Current focus: **Phase 1 — SK REIT deep-dive enhancement**
- Not yet focus: full listed-REIT peer comparison, NLP disclosure mining, large-scale map analytics

Strategic positioning:

- Not a simple clone of MOLIT REIT information system, DART, ECOS, KRX, or Korea Real Estate Board sources.
- Source systems provide raw data.
- This app connects and interprets data to produce early-warning signals and advisory/audit/tax insights.

## 2. Current version to continue from

Use this file as the starting point:

```text
reits_analysis_app_v10_holding_tax_general_scenario.py
```

Recommended rename in local repo:

```text
app.py
```

Relevant current package:

```text
reits_analysis_app_v10_holding_tax_general_scenario.zip
```

Supporting report for Notion/GitHub explanation:

```text
K_REIT_Risk_Intelligence_Project_Report.md
```

## 3. Local Windows setup

Recommended structure:

```text
reits_analysis_app/
  app.py
  requirements.txt
  data/
    sk_reit_asset_metrics.csv
    sk_reit_latest_kpis.csv
    sk_reit_debt_schedule_20260331.csv
    sk_reit_debt_summary_20260331.csv
    sk_reit_consolidated_financials.csv
    sk_reit_parent_direct_assets_20260331.csv
    sk_reit_data_dictionary.csv
    sk_reit_additional_source_plan.csv
```

Install packages:

```powershell
py -m pip install -r requirements.txt
```

Run:

```powershell
py -m streamlit run app.py
```

If the project path contains square brackets, Korean characters, or spaces, use `-LiteralPath`:

```powershell
Set-Location -LiteralPath "G:\내 드라이브\학업\한양대학교\[경제금융학과]\...\reits_analysis_app"
py -m streamlit run app.py
```

## 4. Required packages

```text
streamlit
pandas
plotly
requests
```

## 5. Product architecture so far

The app evolved through these stages:

### v1 — Basic REIT risk screener

- Basic overview of SK REIT.
- Portfolio/lease snapshot.
- Debt/refinancing risk.
- Valuation / FFO / NAV sections.
- Sources and data model.

### v2 — Management Watchlist and DD question bank

- Added management watchlist.
- Added due diligence questions.
- Added source confidence summary.
- Added scenario controls.

### v3 — Risk score decomposition

- Added REIT-level risk decomposition.
- Added asset-level risk score decomposition.

### v4 — Interactive scenario simulator

- Added user-controlled scenario simulator.
- Interest-rate shock, debt-refinancing share, FFO downside, cap-rate expansion.
- Produced stressed FFO, stressed ICR, dividend cushion, NAV impact, LTV proxy.

### v5 — One-page consulting view

- Removed multi-tab structure.
- Consolidated into one-page consulting dashboard.
- Moved stress scenario controls to sidebar.
- Reduced chart/table size.
- Removed secondary table fields such as rank_by_value and asset_type from main view.

### v6 — ECOS macro scenario

- Added ECOS API key input.
- Added macro-based scenario overlay: boom/neutral/recession.
- Used ECOS data as current macro baseline, not as official forecast.

### v7 — DART and five-year history

- Added DART API key input.
- Added DART financial statement retrieval concept for SK REIT.
- Added five-year historical macro/financial visualization.
- Added formula/theory explanations for NAV, FFO, cap rate, LTV, and interest coverage.

### v8 — User modes and KRX

- Added user modes.
- Added KRX API key and endpoint inputs.
- Added market cap, P/NAV, NAV discount.
- Added market-implied risk interpretation.

### v9 — Transmission engine

- Added macro → REIT financials → market price transmission diagnostics.
- Added KRX CSV fallback.
- Added correlation/sensitivity screening.
- Added market discount vs scenario NAV damage comparison.

### v10 — Assurance / Tax / Deals modes

- Refocused user modes into professional service groups:
  - Assurance
  - Tax
  - Deals
- Assurance: RMM, KAM, going concern, internal control audit points.
- Tax: holding tax / disposal tax proxy.
- Deals: NAV, FFO, dividend-yield valuation and backtesting.

### v10.1 — General info separation and holding-tax depth

- Split common information into `General Info & Scenario`.
- Kept `Assurance`, `Tax`, and `Deals` as separate modes.
- Removed disposal tax from Tax mode.
- Deepened holding-tax analysis.
- Added assessed value / official price API structure using Korea Real Estate Board or official price endpoint.
- Added CSV fallback for official land price and building standard value.
- Added five-year holding-tax trend.
- Added clickable formula and tax-base explanation.

## 6. Known coding errors encountered and fixes

### Error 1 — `NameError: rate_shock_bp is not defined`

Cause:

- A stress scenario table was computed before the sidebar slider variable `rate_shock_bp` was defined.

Fix:

- Moved `custom_stress = build_custom_stress_table(...)` below the sidebar slider definitions.

### Error 2 — `StreamlitDuplicateElementId`

Cause:

- Duplicate Streamlit sliders/selectboxes had same generated IDs.

Fix:

- Removed duplicate controls.
- Added explicit `key=` values to sidebar widgets.

### Error 3 — `TypeError: positive() got an unexpected keyword argument 'upper'`

Cause:

- Pandas scalar result used `.clip(upper=100)`, but scalar numeric objects do not accept pandas-style `clip` parameters.

Fix:

```python
risk_value = min(float(value), 100.0)
```

### Error 4 — ECOS API key input not applying

Cause:

- Streamlit `text_input` did not reliably commit value on Enter in browser/IME context.

Fix:

- Replaced loose text input with `st.form` and explicit submit button.

### Error 5 — `NameError: os is not defined`

Cause:

- `_default_ecos_key()` used `os.getenv()` but `import os` was missing.

Fix:

```python
import os
```

### Error 6 — `requests` package missing

Cause:

- API calls required `requests`, but package was not in requirements initially.

Fix:

- Added `requests` to `requirements.txt`.

### Error 7 — Confusing policy-rate decimals

Cause:

- Policy-rate changes were displayed as percentage changes or annual average deltas with many decimals.

Fix:

- Display policy-rate level as percent with two decimals.
- Display policy-rate change as basis points.
- Round policy-rate change to 25bp increments when appropriate.
- Keep decimals for market rates such as government bond yields, corporate bond yields, and cap rates.

## 7. Current screen design

Current sidebar mode choices:

```text
General Info & Scenario
Assurance
Tax
Deals
```

### General Info & Scenario

Purpose:

- Show common REIT overview.
- Show macro scenario assumptions.
- Show FFO/NAV/market-price transmission logic.
- Keep this separate from professional-service-specific analysis.

### Assurance

Purpose:

- Help identify RMM for financial statement audit and internal control audit.
- Prioritize which real estate assets require closer audit procedures.
- Support KAM candidate analysis.
- Support going-concern early-warning analysis without overstating conclusions.

Important outputs:

- Audit priority asset list.
- RMM mapping.
- KAM candidate suggestions.
- Going-concern review signals.
- Internal control audit points.

### Tax

Purpose:

- Estimate and analyze holding-tax burden by asset.
- Use official land price / assessed value / standard building value when available.
- Show how land-price changes affected holding tax over the last five years.

Important outputs:

- Official land price / building standard value import area.
- Tax base formulas in a clickable expander.
- Land tax, building tax, city planning tax, local education surtax proxies.
- Five-year holding-tax trend.
- Holding tax increase rate by asset.

Important boundary:

- Do not present this as filing-ready tax calculation.
- It is a preliminary estimator for screening and advisory discussion.

### Deals

Purpose:

- Analyze buy-side and sell-side value cases.
- Estimate market value through NAV, FFO, and dividend-yield approaches.
- Compare estimated value with actual KRX market cap.
- Evaluate model fit using historical KRX price and market cap data.

Important outputs:

- NAV-based equity value.
- FFO-based equity value.
- Dividend-yield-based equity value.
- Backtesting vs historical market cap.
- Buy-side / sell-side advisory implications.

## 8. Next development roadmap

### v11 — SK REIT final stabilization

Goal:

- Make v10.1 robust, clean, and interview-demo-ready.

Tasks:

1. Refactor long `app.py` into modules:
   - `api_ecos.py`
   - `api_dart.py`
   - `api_krx.py`
   - `api_real_estate_board.py`
   - `calculations_tax.py`
   - `calculations_valuation.py`
   - `calculations_assurance.py`
   - `ui_general.py`
   - `ui_assurance.py`
   - `ui_tax.py`
   - `ui_deals.py`
2. Add robust error handling.
3. Add data source status badges.
4. Add unit-style validation functions for core calculations.
5. Add sample CSV templates for KRX and official price imports.
6. Polish README for GitHub.

### v12 — Peer comparison

Goal:

- Expand from SK REIT single-case analysis to listed K-REIT peer comparison.

Initial peer group:

- SK REIT
- Lotte REIT
- Shinhan Alpha REIT
- ESR Kendall Square REIT
- Koramco The One REIT
- Hanwha REIT
- Samsung FN REIT
- IGIS Value Plus REIT
- Mastern Premier REIT
- JR Global REIT

Outputs:

- P/NAV ranking.
- Dividend yield ranking.
- FFO payout ranking.
- Debt maturity risk ranking.
- Cap-rate sensitivity ranking.
- Assurance RMM ranking.
- Tax holding-cost sensitivity ranking.
- Deals valuation-gap ranking.

### v13 — Asset and geo analytics

Goal:

- Analyze institutional commercial real estate capital flows using listed REIT assets.

Outputs:

- Asset map.
- CBD / GBD / YBD / Pangyo / logistics zones exposure.
- Asset-type composition.
- Regional assessed-value change.
- Regional cap-rate sensitivity.

### v14 — Disclosure NLP early-warning system

Goal:

- Parse disclosure documents for risk keywords and changed language.

Risk keywords:

- 차환
- 담보권
- 임대차계약 변경
- 주요 임차인 변경
- 공실
- 감정평가
- 평가손실
- 신용등급
- 특수관계자
- 계속기업
- 유동성
- 약정 위반
- 배당정책 변경

Outputs:

- Source-linked risk flags.
- Deals risk paragraphs.
- Assurance RMM/KAM hints.

## 9. Coding rules for Codex

When continuing this project, follow these rules:

1. Do not rewrite the whole app unless necessary.
2. Make changes incrementally.
3. Preserve the current mode structure:
   - General Info & Scenario
   - Assurance
   - Tax
   - Deals
4. Keep source basis labels:
   - `공시값`
   - `API값`
   - `CSV 업로드값`
   - `추정값/proxy`
5. Keep tax warnings clear.
6. Do not treat DART financial statements as sufficient for FFO/NAV/WALE.
7. Separate K-IFRS financial statements from REIT investment-report KPIs.
8. For policy rates, use bp change; avoid messy percentage-change displays.
9. For market rates and cap rates, decimals are acceptable.
10. Do not overstate model precision.
11. Every API integration must have fallback handling.
12. Every user-facing calculation should have an explanation or expander.

## 10. Suggested first Codex prompt

Copy and paste this into Windows Codex after opening the repo:

```text
You are continuing development of my K-REIT Risk Intelligence Platform.

Please read these files first:
1. app.py
2. README_REITS.md if present
3. K_REIT_Risk_Intelligence_Project_Report.md if present
4. CODEX_HANDOFF_K_REIT_RISK_INTELLIGENCE.md if present

Current stable version is based on reits_analysis_app_v10_holding_tax_general_scenario.py.

The project is a Streamlit app for SK REIT deep-dive analysis. It connects REIT disclosures, ECOS macro indicators, DART financials, KRX market prices, asset-level data, debt schedules, and holding-tax assessed-value data. The current user modes are:
- General Info & Scenario
- Assurance
- Tax
- Deals

Do not rewrite the app from scratch. First inspect the code structure and tell me:
1. The main functions and sections.
2. Any obvious bugs or fragile areas.
3. A safe refactoring plan to split this large app.py into modules without changing behavior.

After that, wait for my approval before editing files.
```

## 11. Interview explanation

Use this short explanation in interviews:

> I initially tried to build a commercial real estate tenant-level rent and NOI analysis tool, but realized that private asset-level lease data was difficult to validate. I pivoted to listed Korean REITs because DART, REIT investment reports, IR materials, ECOS macro indicators, KRX market prices, and official assessed-value data can be connected and source-checked. The final product is not just a dashboard. It is a risk-intelligence platform that links macro shocks, asset valuation, FFO, NAV, debt maturity, market cap, and tax burden to identify early risk signals for Assurance, Tax, and Deals use cases.

## 12. GitHub README structure

Recommended GitHub README sections:

1. Project overview
2. Why this project matters
3. Difference from existing REIT information systems
4. Data sources
5. App architecture
6. User modes
7. Key calculations
8. Screenshots
9. Development history and debugging log
10. Limitations
11. Roadmap
12. How to run locally

## 13. Current limitation statement

Use this limitation statement clearly:

> This project is a preliminary risk screening and advisory analytics prototype. It is not a statutory audit conclusion, tax filing calculator, investment recommendation, or formal valuation opinion. DART, ECOS, KRX, REIT investment reports, and assessed-value APIs have different reporting bases and update cycles; therefore, source basis labels and reconciliation checks are essential.
