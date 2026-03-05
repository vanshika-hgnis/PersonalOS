"""
Tests for src/utils/pdf_detector.py
"""

import pytest
from src.utils.pdf_detector import detect_pdf_in_message, get_pdf_filename


class TestDetectPdfInMessage:
    def test_pdf_url_detected(self):
        text = "Download the report at https://example.com/report.pdf"
        result = detect_pdf_in_message(text)
        assert result["is_pdf"] is True
        assert len(result["pdf_urls"]) == 1
        assert "https://example.com/report.pdf" in result["pdf_urls"]

    def test_bare_filename_detected(self):
        text = "I sent you document.pdf for review"
        result = detect_pdf_in_message(text)
        assert result["is_pdf"] is True
        assert "document.pdf" in result["pdf_filenames"]

    def test_non_pdf_url(self):
        text = "Visit https://example.com/page for info"
        result = detect_pdf_in_message(text)
        assert result["is_pdf"] is False
        assert result["pdf_urls"] == []

    def test_empty_message(self):
        result = detect_pdf_in_message("")
        assert result["is_pdf"] is False
        assert result["pdf_urls"] == []
        assert result["pdf_filenames"] == []

    def test_multiple_pdf_urls(self):
        text = "See https://a.com/x.pdf and https://b.com/y.pdf"
        result = detect_pdf_in_message(text)
        assert result["is_pdf"] is True
        assert len(result["pdf_urls"]) == 2

    def test_no_duplicate_filenames(self):
        text = "report.pdf and report.pdf are the same"
        result = detect_pdf_in_message(text)
        assert len(result["pdf_filenames"]) == 1


class TestGetPdfFilename:
    def test_simple_pdf_url(self):
        assert get_pdf_filename("https://example.com/docs/report.pdf") == "report.pdf"

    def test_non_pdf_url_returns_none(self):
        assert get_pdf_filename("https://example.com/page") is None

    def test_encoded_filename(self):
        result = get_pdf_filename("https://example.com/my%20report.pdf")
        assert result == "my report.pdf"
