from __future__ import annotations

from html import escape
from io import BytesIO

import pandas as pd


def dataframe_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")


def review_pack_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            safe_name = name[:31]
            frame.to_excel(writer, sheet_name=safe_name, index=False)
    return buffer.getvalue()


def review_document_html(title: str, memo_markdown: str) -> bytes:
    html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;max-width:980px;margin:40px auto;line-height:1.65;color:#222}}pre{{white-space:pre-wrap;font:inherit}}h1{{border-bottom:2px solid #d8a800;padding-bottom:12px}}</style>
</head><body><h1>{escape(title)}</h1><pre>{escape(memo_markdown)}</pre></body></html>"""
    return html.encode("utf-8")
