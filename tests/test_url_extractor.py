"""
Tests for src/utils/url_extractor.py
"""

import pytest
from src.utils.url_extractor import extract_urls, is_pdf_url, get_domain


class TestExtractUrls:
    def test_single_https_url(self):
        text = "Check this out: https://example.com/page"
        assert extract_urls(text) == ["https://example.com/page"]

    def test_single_http_url(self):
        text = "Visit http://example.com today"
        assert extract_urls(text) == ["http://example.com"]

    def test_www_url(self):
        text = "Go to www.example.com for more"
        assert extract_urls(text) == ["www.example.com"]

    def test_multiple_urls(self):
        text = "See https://a.com and https://b.com"
        urls = extract_urls(text)
        assert set(urls) == {"https://a.com", "https://b.com"}
        assert len(urls) == 2

    def test_empty_text(self):
        assert extract_urls("") == []

    def test_no_url(self):
        assert extract_urls("Just a plain note with no links.") == []

    def test_none_text(self):
        assert extract_urls(None) == []


class TestIsPdfUrl:
    def test_pdf_extension_in_path(self):
        assert is_pdf_url("https://example.com/doc.pdf") is True

    def test_pdf_in_query_string(self):
        assert is_pdf_url("https://example.com/view?file=report.pdf") is True

    def test_non_pdf_url(self):
        assert is_pdf_url("https://example.com/page") is False

    def test_pdf_uppercase_extension(self):
        assert is_pdf_url("https://example.com/report.PDF") is True

    def test_html_url(self):
        assert is_pdf_url("https://example.com/index.html") is False


class TestGetDomain:
    def test_https_url(self):
        assert get_domain("https://example.com/path") == "example.com"

    def test_http_url(self):
        assert get_domain("http://sub.example.com") == "sub.example.com"

    def test_www_url(self):
        assert get_domain("www.example.com") == "www.example.com"

    def test_empty_string(self):
        result = get_domain("")
        assert result is None or result == ""
