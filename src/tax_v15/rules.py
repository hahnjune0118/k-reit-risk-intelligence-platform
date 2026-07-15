from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pandas as pd

from .models import as_decimal


class RuleUnavailableError(ValueError):
    """Raised when no officially verified rule is available for a calculation."""


@dataclass(frozen=True)
class TaxRule:
    rule_code: str
    tax_name: str
    tax_classification: str
    bracket_start: Decimal | None
    bracket_end: Decimal | None
    base_amount: Decimal | None
    marginal_rate: Decimal | None
    fair_market_value_ratio: Decimal | None
    multiplier: Decimal | None
    law_name: str
    article: str
    paragraph: str
    exact_clause_summary: str
    source_url: str


class TaxRuleBook:
    def __init__(self, rules: pd.DataFrame, tax_year: int):
        self.tax_year = int(tax_year)
        frame = rules.copy() if rules is not None else pd.DataFrame()
        if frame.empty:
            self._rules = frame
            return
        frame["tax_year"] = pd.to_numeric(frame["tax_year"], errors="coerce")
        source_ok = frame["source_url"].fillna("").astype(str).str.startswith(("https://", "http://"))
        self._rules = frame[
            frame["tax_year"].eq(self.tax_year)
            & frame["validation_status"].fillna("").astype(str).eq("official_verified")
            & source_ok
        ].copy()

    def _convert(self, row: pd.Series) -> TaxRule:
        return TaxRule(
            rule_code=str(row.get("rule_code", "")),
            tax_name=str(row.get("tax_name", "")),
            tax_classification=str(row.get("tax_classification", "")),
            bracket_start=as_decimal(row.get("bracket_start")),
            bracket_end=as_decimal(row.get("bracket_end")),
            base_amount=as_decimal(row.get("base_amount")),
            marginal_rate=as_decimal(row.get("marginal_rate")),
            fair_market_value_ratio=as_decimal(row.get("fair_market_value_ratio")),
            multiplier=as_decimal(row.get("multiplier")),
            law_name=str(row.get("law_name", "")),
            article=str(row.get("article", "")),
            paragraph=str(row.get("paragraph", "")),
            exact_clause_summary=str(row.get("exact_clause_summary", "")),
            source_url=str(row.get("source_url", "")),
        )

    def one(self, rule_code: str) -> TaxRule:
        if self._rules.empty:
            raise RuleUnavailableError(f"{self.tax_year}년 공식 검증 규칙이 없습니다: {rule_code}")
        rows = self._rules[self._rules["rule_code"].astype(str).eq(rule_code)]
        if len(rows) != 1:
            raise RuleUnavailableError(
                f"{self.tax_year}년 공식 검증 규칙을 하나로 확정할 수 없습니다: {rule_code} ({len(rows)}건)"
            )
        return self._convert(rows.iloc[0])

    def brackets(self, rule_code: str) -> list[TaxRule]:
        if self._rules.empty:
            raise RuleUnavailableError(f"{self.tax_year}년 공식 검증 누진 규칙이 없습니다: {rule_code}")
        rows = self._rules[self._rules["rule_code"].astype(str).eq(rule_code)].copy()
        if rows.empty:
            raise RuleUnavailableError(f"{self.tax_year}년 공식 검증 누진 규칙이 없습니다: {rule_code}")
        rows["_start"] = pd.to_numeric(rows["bracket_start"], errors="coerce").fillna(0)
        rows = rows.sort_values("_start")
        return [self._convert(row) for _, row in rows.iterrows()]


def progressive_amount(tax_base: Decimal, brackets: list[TaxRule]) -> tuple[Decimal, TaxRule]:
    if tax_base < 0:
        raise ValueError("과세표준은 음수일 수 없습니다.")
    for rule in brackets:
        start = rule.bracket_start or Decimal("0")
        end = rule.bracket_end
        if tax_base >= start and (end is None or tax_base <= end):
            if rule.marginal_rate is None:
                raise RuleUnavailableError(f"누진세율이 없습니다: {rule.rule_code}")
            amount = (rule.base_amount or Decimal("0")) + (tax_base - start) * rule.marginal_rate
            return amount, rule
    raise RuleUnavailableError(f"과세표준 {tax_base}에 적용할 누진 구간이 없습니다.")
