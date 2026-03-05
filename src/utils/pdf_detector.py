"""
PDF detector utility.

Determines whether a message or URL refers to a PDF document by
inspecting URL paths, file extensions, and MIME-type hints embedded
in message text.
"""

import re
from typing import Optional
from src.utils.url_extractor import extract_urls, is_pdf_url

_PDF_MIME_PATTERN = re.compile(
    r"application/pdf|Content-Type:\s*application/pdf",
    re.IGNORECASE,
)

_PDF_FILENAME_PATTERN = re.compile(
    r"\b[\w\-]+\.pdf\b",
    re.IGNORECASE,
)


def detect_pdf_in_message(text: str) -> dict:
    """Analyse *text* for PDF references.

    Returns a dict with:
        - ``is_pdf`` (bool): True if any PDF was detected.
        - ``pdf_urls`` (list[str]): URLs that point to PDF files.
        - ``pdf_filenames`` (list[str]): Bare filenames ending in ``.pdf``.
    """
    urls = extract_urls(text)
    pdf_urls = [url for url in urls if is_pdf_url(url)]
    pdf_filenames = _PDF_FILENAME_PATTERN.findall(text)
    # Deduplicate filenames while preserving order
    seen: set[str] = set()
    unique_filenames: list[str] = []
    for name in pdf_filenames:
        lower = name.lower().strip()
        if lower not in seen:
            seen.add(lower)
            unique_filenames.append(name.strip())

    return {
        "is_pdf": bool(pdf_urls or unique_filenames),
        "pdf_urls": pdf_urls,
        "pdf_filenames": unique_filenames,
    }


def get_pdf_filename(url: str) -> Optional[str]:
    """Extract the filename component from a PDF URL, or None if not available."""
    from urllib.parse import urlparse, unquote
    parsed = urlparse(url)
    path = unquote(parsed.path)
    filename = path.split("/")[-1]
    return filename if filename.lower().endswith(".pdf") else None
