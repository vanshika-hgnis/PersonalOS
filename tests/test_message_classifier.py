"""
Tests for src/lambdas/message_classifier.py
"""

import pytest
from src.lambdas.message_classifier import classify_message


class TestClassifyUrl:
    def test_http_link_classified_as_url(self):
        msg = {"text": "Check this out: https://example.com/article"}
        result = classify_message(msg)
        assert result["type"] == "url"
        assert "link" in result["tags"]
        assert "https://example.com/article" in result["urls"]

    def test_www_link_classified_as_url(self):
        msg = {"text": "Visit www.example.com"}
        result = classify_message(msg)
        assert result["type"] == "url"

    def test_url_has_domain_metadata(self):
        msg = {"text": "https://example.com/page"}
        result = classify_message(msg)
        assert result["metadata"].get("domain") == "example.com"


class TestClassifyPdf:
    def test_pdf_url_classified_as_pdf(self):
        msg = {"text": "Download: https://example.com/report.pdf"}
        result = classify_message(msg)
        assert result["type"] == "pdf"
        assert "pdf" in result["tags"]

    def test_pdf_filename_in_text_classified_as_pdf(self):
        msg = {"text": "I'm sharing document.pdf with you"}
        result = classify_message(msg)
        assert result["type"] == "pdf"


class TestClassifyNote:
    def test_plain_text_classified_as_note(self):
        msg = {"text": "Remember to call the dentist tomorrow"}
        result = classify_message(msg)
        assert result["type"] == "note"
        assert "note" in result["tags"]

    def test_short_text_classified_as_unknown(self):
        msg = {"text": "ok"}
        result = classify_message(msg)
        assert result["type"] == "unknown"

    def test_note_has_word_count(self):
        msg = {"text": "This is a longer note about something important"}
        result = classify_message(msg)
        assert result["type"] == "note"
        assert result["metadata"]["word_count"] >= 3


class TestClassifyMedia:
    def test_media_mime_type_classified_as_media(self):
        msg = {"text": "", "media_type": "image/jpeg", "media_url": ""}
        result = classify_message(msg)
        assert result["type"] == "media"

    def test_media_url_classified_as_media(self):
        msg = {"text": "", "media_type": "", "media_url": "https://cdn.example.com/photo.jpg"}
        result = classify_message(msg)
        assert result["type"] == "media"


class TestClassifyEmpty:
    def test_empty_message_classified_as_unknown(self):
        msg = {"text": ""}
        result = classify_message(msg)
        assert result["type"] == "unknown"

    def test_missing_text_classified_as_unknown(self):
        result = classify_message({})
        assert result["type"] == "unknown"


class TestKeywordsAndCategories:
    def test_keywords_extracted(self):
        msg = {"text": "I need to schedule a meeting for the project deadline"}
        result = classify_message(msg)
        assert len(result["keywords"]) > 0

    def test_keyword_categories_populated(self):
        msg = {"text": "Check this article for your research analysis"}
        result = classify_message(msg)
        assert "research" in result["keyword_categories"]


class TestLambdaHandler:
    def test_handler_returns_200_for_valid_message(self):
        from src.lambdas.message_classifier import lambda_handler
        import json
        event = {
            "body": json.dumps({"message": {"text": "https://example.com"}})
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200

    def test_handler_returns_200_for_direct_message(self):
        from src.lambdas.message_classifier import lambda_handler
        import json
        event = {"body": json.dumps({"text": "A note message"})}
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200
