from ui_tax_case_study import _decimal_tax_total, _format_eok, render_tax_mode


CORE_ASSET_RECALCULATION_LABEL = (
    "2026년 공식 과세기초자료와 확인된 법정 산식에 따른 보유세 재계산액"
)
GOLDEN_RECALCULATION_LABEL = CORE_ASSET_RECALCULATION_LABEL

__all__ = [
    "GOLDEN_RECALCULATION_LABEL",
    "CORE_ASSET_RECALCULATION_LABEL",
    "_decimal_tax_total",
    "_format_eok",
    "render_tax_mode",
]
