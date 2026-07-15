from __future__ import annotations

import argparse
import time

import pandas as pd

from src.tax_v15.acquisition import discover_pdf_links, extract_pdf_evidence
from src.tax_v15.constants import PROJECT_ROOT, V15_DATA_DIR
from src.tax_v15.schemas import coerce_to_schema, ensure_v15_csv_files

from .common import add_common_arguments, cache_path, request_with_retry, sha256_bytes, utc_now, write_checkpoint


MAX_PDFS_PER_SITE = 8
MAX_PDF_BYTES = 50 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (compatible; K-REIT-Risk-Intelligence/15.0; public-data-review)"


def _clean_text(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _cache_reference(path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return ""


def _row(
    *,
    reit_name: str,
    document_type: str,
    document_name: str,
    source_url: str,
    local_cache_path: str = "",
    sha256: str = "",
    extraction_status: str,
    relevant_pages: str = "",
    notes: str = "",
) -> dict:
    return {
        "reit_name": reit_name,
        "document_type": document_type,
        "document_name": document_name,
        "document_date": "",
        "source_url": source_url,
        "local_cache_path": local_cache_path,
        "sha256": sha256,
        "downloaded_at": utc_now(),
        "extraction_status": extraction_status,
        "relevant_pages": relevant_pages,
        "notes": notes,
    }


def _read_or_download(url: str, *, suffix: str, offline: bool, refresh_sources: bool) -> tuple[bytes, str, str]:
    cached = cache_path("raw_documents" if suffix == ".pdf" else "source_documents", url, suffix)
    if offline:
        if not cached.exists():
            raise FileNotFoundError("오프라인 캐시 없음")
        return cached.read_bytes(), "cached_official_source", _cache_reference(cached)
    if cached.exists() and not refresh_sources:
        return cached.read_bytes(), "cached_official_source", _cache_reference(cached)
    response = request_with_retry("GET", url, headers={"User-Agent": USER_AGENT})
    content = response.content
    cached.write_bytes(content)
    return content, "downloaded_official_source", _cache_reference(cached)


def run(
    *,
    offline: bool = False,
    dry_run: bool = False,
    reit_code: str = "",
    refresh_sources: bool = False,
) -> pd.DataFrame:
    ensure_v15_csv_files()
    reits = pd.read_csv(V15_DATA_DIR / "reit_master.csv", dtype={"stock_code": "string"})
    if reit_code:
        reits = reits[reits["stock_code"].eq(reit_code)]
    existing_path = V15_DATA_DIR / "source_document_manifest.csv"
    existing = pd.read_csv(existing_path) if existing_path.exists() and existing_path.stat().st_size else pd.DataFrame()
    rows: list[dict] = []

    for _, reit in reits.iterrows():
        reit_name = _clean_text(reit["reit_name"])
        url = _clean_text(reit.get("official_website", ""))
        if not url:
            rows.append(
                _row(
                    reit_name=reit_name,
                    document_type="official_website",
                    document_name="공식 홈페이지",
                    source_url="",
                    extraction_status="manual_review_required",
                    notes="리츠정보시스템에 공식 홈페이지 URL이 없습니다.",
                )
            )
        else:
            try:
                content, status, local_path = _read_or_download(
                    url,
                    suffix=".html",
                    offline=offline,
                    refresh_sources=refresh_sources,
                )
                html_text = content.decode("utf-8", errors="ignore")
                pdf_links = discover_pdf_links(html_text, url)[:MAX_PDFS_PER_SITE]
                rows.append(
                    _row(
                        reit_name=reit_name,
                        document_type="official_website",
                        document_name="공식 홈페이지",
                        source_url=url,
                        local_cache_path=local_path,
                        sha256=sha256_bytes(content),
                        extraction_status=status,
                        relevant_pages="HTML",
                        notes=f"공식 홈페이지에서 직접 연결된 PDF {len(pdf_links)}건 식별",
                    )
                )
                for pdf_url, label in pdf_links:
                    try:
                        pdf_content, pdf_status, pdf_path = _read_or_download(
                            pdf_url,
                            suffix=".pdf",
                            offline=offline,
                            refresh_sources=refresh_sources,
                        )
                        if len(pdf_content) > MAX_PDF_BYTES:
                            raise ValueError("PDF_SIZE_LIMIT")
                        if not pdf_content.lstrip().startswith(b"%PDF"):
                            raise ValueError("NOT_A_PDF_RESPONSE")
                        extraction = extract_pdf_evidence(pdf_content, allow_ocr=True)
                        page_text = ",".join(str(page) for page in extraction.relevant_pages)
                        notes = (
                            f"수집={pdf_status}; 추출={extraction.status}; 전체 {extraction.page_count}페이지; "
                            f"OCR 페이지={','.join(map(str, extraction.ocr_pages)) or '없음'}"
                        )
                        if extraction.evidence:
                            notes = f"{notes}; 근거={extraction.evidence}"
                        rows.append(
                            _row(
                                reit_name=reit_name,
                                document_type="official_pdf",
                                document_name=label,
                                source_url=pdf_url,
                                local_cache_path=pdf_path,
                                sha256=sha256_bytes(pdf_content),
                                extraction_status=extraction.status,
                                relevant_pages=page_text,
                                notes=notes,
                            )
                        )
                    except Exception as exc:
                        rows.append(
                            _row(
                                reit_name=reit_name,
                                document_type="official_pdf",
                                document_name=label,
                                source_url=pdf_url,
                                extraction_status="download_failed",
                                notes=f"3회 이내 재시도 후 실패: {type(exc).__name__}",
                            )
                        )
                    time.sleep(0.2)
            except Exception as exc:
                rows.append(
                    _row(
                        reit_name=reit_name,
                        document_type="official_website",
                        document_name="공식 홈페이지",
                        source_url=url,
                        extraction_status="download_failed",
                        notes=f"3회 이내 재시도 후 실패 또는 오프라인 캐시 없음: {type(exc).__name__}",
                    )
                )

        dart_corp_code = _clean_text(reit.get("dart_corp_code", ""))
        rows.append(
            _row(
                reit_name=reit_name,
                document_type="dart_filings",
                document_name="DART 정기공시·투자보고서",
                source_url="https://dart.fss.or.kr/",
                extraction_status="manual_review_required" if not dart_corp_code else "source_index_ready",
                notes=(
                    "DART 고유번호 미확인으로 문서 목록 자동 수집 보류"
                    if not dart_corp_code
                    else "DART 고유번호 확인; 공시문서별 후속 수집 대상"
                ),
            )
        )

    result = coerce_to_schema(pd.concat([existing, pd.DataFrame(rows)], ignore_index=True), "source_document_manifest.csv")
    result = result.drop_duplicates(["reit_name", "document_type", "source_url"], keep="last")
    if not dry_run:
        result.to_csv(existing_path, index=False, encoding="utf-8-sig")
        write_checkpoint("collect_reit_documents", {"completed_at": utc_now(), "rows": len(result)})
    return result


def main() -> None:
    args = add_common_arguments(
        argparse.ArgumentParser(description="상장리츠 공식 홈페이지·PDF Source Manifest 구축")
    ).parse_args()
    frame = run(
        offline=args.offline,
        dry_run=args.dry_run,
        reit_code=args.reit_code,
        refresh_sources=args.refresh_sources,
    )
    print(f"Source Manifest: {len(frame)}건")


if __name__ == "__main__":
    main()
