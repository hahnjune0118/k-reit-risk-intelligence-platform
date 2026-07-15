from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit


RELEVANT_KEYWORDS = (
    "자산",
    "소재지",
    "주소",
    "소유",
    "신탁",
    "지분",
    "portfolio",
    "property",
    "address",
    "ownership",
    "trust",
)


@dataclass(frozen=True)
class PdfExtractionResult:
    status: str
    page_count: int
    relevant_pages: tuple[int, ...]
    ocr_pages: tuple[int, ...]
    evidence: str
    error_type: str = ""


class _PdfLinkParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.links: list[tuple[str, str]] = []
        self._href = ""
        self._label_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        self._href = dict(attrs).get("href") or ""
        self._label_parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._label_parts.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._href:
            return
        absolute = urljoin(self.base_url, self._href)
        path = urlsplit(absolute).path.lower()
        if path.endswith(".pdf"):
            label = " ".join(part for part in self._label_parts if part).strip()
            self.links.append((absolute, label or path.rsplit("/", 1)[-1]))
        self._href = ""
        self._label_parts = []


def discover_pdf_links(html_text: str, base_url: str) -> list[tuple[str, str]]:
    parser = _PdfLinkParser(base_url)
    parser.feed(html_text or "")
    unique: dict[str, str] = {}
    for url, label in parser.links:
        unique.setdefault(url, label)
    return list(unique.items())


def _matching_lines(text: str, keywords: tuple[str, ...]) -> list[str]:
    normalized = [line.strip() for line in text.splitlines() if line.strip()]
    return [line for line in normalized if any(keyword.lower() in line.lower() for keyword in keywords)]


def extract_pdf_evidence(
    content: bytes,
    *,
    keywords: tuple[str, ...] = RELEVANT_KEYWORDS,
    allow_ocr: bool = True,
) -> PdfExtractionResult:
    """Extract only relevant PDF pages and attempt OCR on image-only pages.

    OCR is best-effort because PyMuPDF delegates OCR to a local Tesseract runtime.
    A missing OCR runtime is recorded instead of turning an unverified page into data.
    """
    try:
        import pymupdf
    except ImportError:
        return PdfExtractionResult("dependency_missing", 0, (), (), "", "ImportError")

    relevant_pages: list[int] = []
    ocr_pages: list[int] = []
    evidence: list[str] = []
    text_seen = False
    ocr_failed = False
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            for page_number, page in enumerate(document, start=1):
                text = page.get_text("text") or ""
                if not text.strip() and allow_ocr:
                    try:
                        text_page = page.get_textpage_ocr(dpi=200, full=True)
                        text = page.get_text("text", textpage=text_page) or ""
                        if text.strip():
                            ocr_pages.append(page_number)
                    except Exception:
                        ocr_failed = True
                if text.strip():
                    text_seen = True
                hits = _matching_lines(text, keywords)
                if hits:
                    relevant_pages.append(page_number)
                    evidence.extend(f"p.{page_number} {line}" for line in hits[:3])
            page_count = len(document)
    except Exception as exc:
        return PdfExtractionResult("extract_failed", 0, (), (), "", type(exc).__name__)

    if relevant_pages:
        status = "extracted_with_ocr" if ocr_pages else "extracted_text"
    elif text_seen:
        status = "extracted_no_keyword_hit"
    elif ocr_failed:
        status = "ocr_runtime_unavailable"
    else:
        status = "ocr_required"
    return PdfExtractionResult(
        status=status,
        page_count=page_count,
        relevant_pages=tuple(relevant_pages),
        ocr_pages=tuple(ocr_pages),
        evidence=" | ".join(evidence)[:1500],
    )
