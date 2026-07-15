"""Compatibility entry point for the active v15 Tax review UI.

The v14 company-level Snapshot implementation is archived at
``archive/v14/ui_tax_v14.py`` and is intentionally excluded from runtime imports.
"""

from ui_tax_v15 import render_tax_mode

__all__ = ["render_tax_mode"]
