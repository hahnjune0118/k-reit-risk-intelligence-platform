import os
import re
from dataclasses import dataclass
from urllib.parse import quote, quote_plus

import pandas as pd
import streamlit as st


API_SECRET_NAMES = {
    "ECOS": "ECOS_API_KEY",
    "DART": "DART_API_KEY",
    "KRX": "KRX_API_KEY",
    "V-World": "REALTY_PRICE_API_KEY",
}

API_PROVIDER_ALIASES = {
    "ECOS": "ECOS",
    "DART": "DART",
    "KRX": "KRX",
    "V-WORLD": "V-World",
    "VWORLD": "V-World",
    "REALTY": "V-World",
    "REALTY_PRICE": "V-World",
}

SESSION_SECRET_KEYS = {
    "ECOS": "ecos_api_key",
    "DART": "dart_api_key",
    "KRX": "krx_api_key",
    "V-World": "realty_price_api_key",
}


@dataclass(frozen=True)
class ApiConnection:
    provider: str
    secret_name: str
    key: str
    source: str
    configured: bool
    status: str
    message: str


def _canonical_provider(provider: str) -> str:
    normalized = str(provider or "").strip()
    return API_PROVIDER_ALIASES.get(normalized.upper(), normalized)


def _secret_value(name: str) -> str:
    try:
        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return ""


def get_api_key(provider: str, manual_value: str = "") -> ApiConnection:
    provider = _canonical_provider(provider)
    secret_name = API_SECRET_NAMES.get(provider, provider)
    manual_value = (manual_value or "").strip()

    if manual_value:
        key = manual_value
        source = "manual"
    else:
        key = _secret_value(secret_name)
        source = "st.secrets" if key else ""
        if not key:
            key = os.getenv(secret_name, "").strip()
            source = "environment" if key else "none"

    configured = bool(key)
    status = "loaded" if configured else "not_configured"
    message = f"{provider} API Key가 설정되어 있습니다." if configured else f"{provider} API Key가 설정되지 않았습니다."
    return ApiConnection(
        provider=provider,
        secret_name=secret_name,
        key=key,
        source=source,
        configured=configured,
        status=status,
        message=message,
    )


def _known_secret_values() -> set[str]:
    values = set()
    for provider, secret_name in API_SECRET_NAMES.items():
        env_value = os.getenv(secret_name, "").strip()
        if env_value:
            values.add(env_value)
        secret_value = _secret_value(secret_name)
        if secret_value:
            values.add(secret_value)
        try:
            session_value = str(st.session_state.get(SESSION_SECRET_KEYS[provider], "")).strip()
            if session_value:
                values.add(session_value)
        except Exception:
            pass
    return values


def sanitize_secret_text(text) -> str:
    if text is None:
        return ""
    redacted = str(text)

    # ECOS embeds the API key in the URL path.
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
    redacted = re.sub(
        r"(?i)(\bauthorization\b\s+bearer\s+)[^&\s\"',}<>]+",
        r"\1[REDACTED]",
        redacted,
    )

    redacted = re.sub(
        r"(?i)(\b(?:key|apiKey|api_key|serviceKey|service_key|ServiceKey|crtfc_key|AUTH_KEY|token|access_token)\b\s*[:=]\s*[\"']?)([^&\s\"',}<>]+)",
        r"\1[REDACTED]",
        redacted,
    )

    for secret in sorted(_known_secret_values(), key=len, reverse=True):
        if len(secret) < 4:
            continue
        for candidate in {secret, quote(secret, safe=""), quote_plus(secret)}:
            redacted = redacted.replace(candidate, "[REDACTED]")
    return redacted


def sanitize_secret_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    sanitized = df.copy()
    for col in sanitized.select_dtypes(include=["object", "string"]).columns:
        sanitized[col] = sanitized[col].apply(sanitize_secret_text)
    return sanitized
