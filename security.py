import os
import re
from urllib.parse import quote, quote_plus

import streamlit as st


SECRET_NAMES = (
    "ECOS_API_KEY",
    "DART_API_KEY",
    "KRX_API_KEY",
    "REALTY_PRICE_API_KEY",
)

SESSION_SECRET_KEYS = (
    "ecos_api_key",
    "dart_api_key",
    "krx_api_key",
    "realty_price_api_key",
)


def get_secret_value(name: str, manual_value: str = "") -> str:
    manual_value = (manual_value or "").strip()
    if manual_value:
        return manual_value
    try:
        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return os.getenv(name, "").strip()


def _known_secret_values() -> set[str]:
    values = set()
    for name in SECRET_NAMES:
        env_value = os.getenv(name, "").strip()
        if env_value:
            values.add(env_value)
        try:
            if name in st.secrets:
                secret_value = str(st.secrets[name]).strip()
                if secret_value:
                    values.add(secret_value)
        except Exception:
            pass
    try:
        for session_key in SESSION_SECRET_KEYS:
            session_value = str(st.session_state.get(session_key, "")).strip()
            if session_value:
                values.add(session_value)
    except Exception:
        pass
    return values


def sanitize_secret_text(text) -> str:
    if text is None:
        return ""
    redacted = str(text)

    # ECOS puts the API key in the URL path rather than a query parameter.
    redacted = re.sub(
        r"(?i)(/api/(?:KeyStatisticList|StatisticSearch)/)([^/?#\s]+)(/json/)",
        r"\1[REDACTED]\3",
        redacted,
    )

    redacted = re.sub(
        r"(?i)(\bauthorization\b\s*[:=]\s*)(?:Bearer\s+)?[^&\s\"',}<>]+",
        r"\1[REDACTED]",
        redacted,
    )

    # Common query-string, header, and JSON-like key names.
    redacted = re.sub(
        r"(?i)(\b(?:key|apiKey|api_key|serviceKey|service_key|ServiceKey|crtfc_key|AUTH_KEY|authorization|token|access_token)\b\s*[:=]\s*[\"']?)([^&\s\"',}<>]+)",
        r"\1[REDACTED]",
        redacted,
    )

    for secret in sorted(_known_secret_values(), key=len, reverse=True):
        if len(secret) < 4:
            continue
        for candidate in {secret, quote(secret, safe=""), quote_plus(secret)}:
            redacted = redacted.replace(candidate, "[REDACTED]")
    return redacted
