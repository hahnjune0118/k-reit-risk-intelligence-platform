from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.tax_v15.constants import PROJECT_ROOT


CACHE_DIR = PROJECT_ROOT / ".cache" / "v15"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def add_common_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--tax-year", type=int, default=2026)
    parser.add_argument("--reit-code", default="")
    parser.add_argument("--refresh-sources", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    return parser


def request_with_retry(
    method: str,
    url: str,
    *,
    max_attempts: int = 3,
    timeout: int = 30,
    session: requests.Session | None = None,
    **kwargs,
) -> requests.Response:
    client = session or requests.Session()
    error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.request(method, url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            error = exc
            if attempt < max_attempts:
                time.sleep(attempt)
    raise RuntimeError(f"공식 출처 조회 실패({max_attempts}회): {url}") from error


def cache_path(namespace: str, key: str, suffix: str = ".json") -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    path = CACHE_DIR / namespace / f"{digest}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_checkpoint(name: str, payload: dict) -> None:
    path = CACHE_DIR / "checkpoints" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_checkpoint(name: str) -> dict:
    path = CACHE_DIR / "checkpoints" / f"{name}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
