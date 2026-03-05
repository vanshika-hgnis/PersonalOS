"""
URL extractor utility.

Extracts all URLs from a text message using regex pattern matching.
Also detects whether a URL points to a PDF document.
"""

import re
from typing import Optional
from urllib.parse import urlparse

# Regex pattern that matches http/https/www URLs
_URL_PATTERN = re.compile(
    r"(https?://[^\s]+|www\.[^\s]+)",
    re.IGNORECASE,
)

_PDF_EXTENSIONS = {".pdf"}
_PDF_QUERY_INDICATORS = {"pdf", ".pdf"}


def extract_urls(text: str) -> list[str]:
    """Return a list of all URLs found in *text*."""
    if not text:
        return []
    return _URL_PATTERN.findall(text)


def is_pdf_url(url: str) -> bool:
    """Return True if *url* points to a PDF file."""
    parsed = urlparse(url.lower())
    path = parsed.path
    # Check file extension in path
    if any(path.endswith(ext) for ext in _PDF_EXTENSIONS):
        return True
    # Check query string for pdf indicators
    query = parsed.query.lower()
    if any(indicator in query for indicator in _PDF_QUERY_INDICATORS):
        return True
    return False


def get_domain(url: str) -> Optional[str]:
    """Return the domain of *url*, or None if parsing fails."""
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        return parsed.netloc or None
    except Exception:
        return None
