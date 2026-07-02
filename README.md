# K-REIT Risk Intelligence Platform

K-REIT Risk Intelligence Platform is a Streamlit-based public portfolio application that links REIT disclosures, macroeconomic indicators, asset-level information, and official land price / assessed value data to support Tax and Assurance-oriented risk analysis.

Current stable public version: v11

## Project Overview

The platform organizes REIT financial disclosures, asset-level information, debt schedules, macro indicators, and official-price data into a practical workflow for accounting and consulting digital transformation use cases. It is designed as a public portfolio version focused on transparent source basis, reproducible calculations, and professional review checklists.

The app is a preliminary analytics and workflow-support tool. It does not provide an audit opinion, tax filing, legal advice, credit rating, investment recommendation, or formal valuation opinion.

## Current v11 Scope

v11 is named **Tax & Assurance Focus**. It refocuses the active public UI on stable modules:

1. General Info & Scenario
2. Assurance
3. Tax
4. Methodology & Data Sources

The active public app disables Deals mode and active KRX API dependency. Future v12/v13 modules may include KRX-based market-implied valuation and Deals analysis after the data connection and valuation workflow are hardened.

## Active Modes

### 1. General Info & Scenario

Reviews the baseline REIT risk profile, macro scenario assumptions, asset concentration, tenant exposure, debt maturity, NAV, FFO, interest coverage, and stress sensitivity.

### 2. Assurance

Translates scenario and disclosure indicators into audit planning, RMM mapping, KAM candidates, going-concern considerations, and internal-control response checklists.

### 3. Tax

Uses official land price / assessed value data, CSV uploads, or proxy assumptions to estimate holding-tax pressure and FFO cash-outflow impact.

### 4. Methodology & Data Sources

Explains data sources, calculation basis, source reliability, API key handling, limitations, and versioning conventions.

## Data Sources

- DART: financial statements and recent disclosure lists
- ECOS: macroeconomic indicators and interest-rate history
- V-World / official land price API: official land price and assessed value inputs for Tax mode
- Internal CSV files: bundled disclosure-based data for stable public demonstration

## Security Note

API keys are handled through Streamlit Secrets, environment variables, or optional manual password inputs. API keys are not displayed in the UI and are never passed into widget default values. Debug and status outputs are sanitized before display.

Supported Streamlit Cloud secret names:

```toml
ECOS_API_KEY = "..."
DART_API_KEY = "..."
REALTY_PRICE_API_KEY = "..."
```

`KRX_API_KEY` may be used by future archived modules, but it is not required for v11 public runtime.

## Running Locally

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Optional development checks:

```powershell
py -m pip install -r requirements-dev.txt
py -m compileall -q . -x "(\.git|\.venv|venv|__pycache__|\.cache|\.vscode)"
py -m pytest -q
```

## Versioning

Future material feature updates should increment the version sequentially: v12, v13, etc. Keep the visible app version in `config.py` and the `VERSION` file aligned.

## Roadmap

Future v12/v13 modules may include:

- KRX-based market-implied valuation
- Deals analysis and valuation backtesting
- broader multi-REIT benchmarking
- additional data-quality and reconciliation workflows
