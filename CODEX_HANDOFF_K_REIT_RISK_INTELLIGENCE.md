# Codex Handoff - K-REIT Risk Intelligence Platform

Current stable public version: v11

## Current Scope

v11 is the Tax & Assurance Focus public portfolio release. The active Streamlit modes are:

1. General Info & Scenario
2. Assurance
3. Tax
4. Methodology & Data Sources

The active public app excludes Deals mode and KRX API runtime dependency. The KRX and Deals code paths remain archived for a future KRX-based Deals valuation module.

## Runtime Entry Point

Use `app.py` as the Streamlit entry point:

```powershell
py -m streamlit run app.py
```

## Key Files

- `config.py`: app version constants and endpoint constants
- `api_manager.py`: secure API key loading and redaction
- `ui_layout.py`: public mode selector and introductory copy
- `ui_sidebar.py`: ECOS, DART, and V-World / official price API configuration
- `ui_general.py`: scenario and risk overview
- `ui_assurance.py`: audit-risk workflow
- `ui_tax.py`: holding-tax workflow
- `ui_methodology.py`: methodology and data-source page

## Security

API keys must never be passed into Streamlit widget `value=` arguments or displayed in UI output. Use `api_manager.get_api_key()` and `api_manager.sanitize_secret_text()` for API key handling and redaction.

## Versioning

Future material feature updates should increment the version sequentially: v12, v13, etc. Keep `VERSION`, `CHANGELOG.md`, and `config.py` aligned.
