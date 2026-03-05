"""
Tests for src/lambdas/notification_sender.py
"""

import logging
import pytest
from src.lambdas.notification_sender import send_notification


class TestSendNotification:
    def test_url_notification_sent(self, caplog):
        resource = {"storage_path": "resources/links", "text": ""}
        classification = {
            "type": "url",
            "tags": ["link", "web"],
            "urls": ["https://example.com"],
            "metadata": {"domain": "example.com"},
        }
        with caplog.at_level(logging.INFO):
            result = send_notification(resource, classification)
        assert result["enabled"] is True
        assert len(result["channels_attempted"]) > 0
        assert result["channels_attempted"][0]["status"] == "sent"

    def test_pdf_notification_sent(self, caplog):
        resource = {"storage_path": "resources/documents", "text": ""}
        classification = {
            "type": "pdf",
            "tags": ["pdf"],
            "urls": ["https://example.com/doc.pdf"],
            "metadata": {"filename": "doc.pdf"},
        }
        with caplog.at_level(logging.INFO):
            result = send_notification(resource, classification)
        assert result["enabled"] is True

    def test_note_notification_sent(self, caplog):
        resource = {"storage_path": "resources/notes", "text": "Call the dentist"}
        classification = {
            "type": "note",
            "tags": ["note"],
            "urls": [],
            "metadata": {"preview": "Call the dentist", "word_count": 3},
        }
        with caplog.at_level(logging.INFO):
            result = send_notification(resource, classification)
        assert result["enabled"] is True
        assert "Call the dentist" in result["message"]

    def test_media_notification_disabled(self):
        resource = {"storage_path": "resources/media", "text": ""}
        classification = {"type": "media", "tags": ["media"], "urls": [], "metadata": {}}
        result = send_notification(resource, classification)
        assert result["enabled"] is False

    def test_unknown_type_notification_disabled(self):
        resource = {"storage_path": "resources/inbox", "text": ""}
        classification = {"type": "unknown", "tags": [], "urls": [], "metadata": {}}
        result = send_notification(resource, classification)
        assert result["enabled"] is False

    def test_notification_message_rendered(self):
        resource = {"storage_path": "resources/links", "text": ""}
        classification = {
            "type": "url",
            "tags": ["link"],
            "urls": ["https://example.com"],
            "metadata": {"domain": "example.com"},
        }
        result = send_notification(resource, classification)
        assert result["message"] != ""
        assert len(result["message"]) > 0


class TestLambdaHandler:
    def test_handler_returns_200(self):
        import json
        from src.lambdas.notification_sender import lambda_handler
        event = {
            "body": json.dumps({
                "resource": {"storage_path": "resources/notes", "text": ""},
                "classification": {
                    "type": "note",
                    "tags": ["note"],
                    "urls": [],
                    "metadata": {"preview": "Test note"},
                },
            })
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200
