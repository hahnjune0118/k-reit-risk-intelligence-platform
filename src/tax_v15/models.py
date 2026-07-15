from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

from .constants import RESULT_STATUSES


def as_decimal(value: Any) -> Decimal | None:
    if value is None or value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


@dataclass(frozen=True)
class CalculationResult:
    tax_name: str
    status: str
    calculated_tax: Decimal | None = None
    official_value: Decimal | None = None
    tax_base: Decimal | None = None
    tax_rate: Decimal | None = None
    fair_market_value_ratio: Decimal | None = None
    multiplier: Decimal | None = None
    base_amount: Decimal | None = None
    bracket: str = ""
    formula_text: str = ""
    law_name: str = ""
    article: str = ""
    source_url: str = ""
    input_source: str = ""
    issues: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.status not in RESULT_STATUSES:
            raise ValueError(f"지원하지 않는 계산 상태입니다: {self.status}")
        if self.status not in {"verified_notice", "official_source_calculated", "not_applicable"}:
            if self.calculated_tax is not None:
                raise ValueError("검증되지 않은 상태에는 계산 세액을 저장할 수 없습니다.")

    @property
    def is_calculated(self) -> bool:
        return self.calculated_tax is not None and self.status in {
            "verified_notice",
            "official_source_calculated",
            "not_applicable",
        }

    @classmethod
    def blocked(cls, tax_name: str, status: str, *issues: str) -> "CalculationResult":
        return cls(tax_name=tax_name, status=status, issues=tuple(issue for issue in issues if issue))
