from __future__ import annotations

from decimal import Decimal
from typing import Mapping

import pandas as pd

from ..constants import CALCULABLE_SOURCE_STATUSES
from ..models import as_decimal


END_DIGIT_TREATMENT_UNIT = Decimal("10")
END_DIGIT_TREATMENT_METHOD = "10원 미만 끝수 미계산"
END_DIGIT_TREATMENT_LEGAL_BASIS = (
    "지방회계법 제55조(지방회계법 시행령 제67조의 예외 대상 여부 별도 검토)"
)


def truncate_to_ten_won(amount: Decimal) -> Decimal:
    """Drop the remainder below KRW 10 without using binary floating point."""
    if not isinstance(amount, Decimal):
        raise TypeError("끝수 처리 금액은 Decimal이어야 합니다.")
    if amount < 0:
        raise ValueError("끝수 처리 금액은 음수일 수 없습니다.")
    return (amount // END_DIGIT_TREATMENT_UNIT) * END_DIGIT_TREATMENT_UNIT


def source_is_calculable(row: Mapping, required_fields: list[str]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    status = str(row.get("validation_status", "")).strip()
    if status not in CALCULABLE_SOURCE_STATUSES:
        issues.append(f"입력 검증 상태가 계산 허용 상태가 아닙니다: {status or '미입력'}")
    source_url = str(row.get("source_url", "") or "").strip()
    if not source_url.startswith(("https://", "http://")):
        issues.append("공식 입력값의 source_url이 없습니다.")
    for field in required_fields:
        value = row.get(field)
        if value is None or value is pd.NA or (isinstance(value, str) and not value.strip()):
            issues.append(f"필수 입력값이 없습니다: {field}")
            continue
        try:
            if pd.isna(value):
                issues.append(f"필수 입력값이 없습니다: {field}")
        except (TypeError, ValueError):
            pass
    return not issues, issues


def require_decimal(row: Mapping, field: str) -> Decimal:
    value = as_decimal(row.get(field))
    if value is None:
        raise ValueError(f"필수 숫자 입력값이 없습니다: {field}")
    return value


def bracket_label(start: Decimal | None, end: Decimal | None) -> str:
    start_text = f"{start:,.0f}" if start is not None else "0"
    end_text = f"{end:,.0f}" if end is not None else "초과 상한 없음"
    return f"{start_text} ~ {end_text}원"
