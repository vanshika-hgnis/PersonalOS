"""
Tests for src/lambdas/notification_sender.py
"""

import logging
from unittest.mock import MagicMock, patch

import pytest
from src.lambdas.notification_sender import send_notification, _send_whatsapp


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


class TestSendWhatsAppChannel:
    """Tests for the WhatsApp notification channel handler."""

    def test_send_whatsapp_success(self):
        """_send_whatsapp returns status=sent when the API call succeeds."""
        mock_response = {"messages": [{"id": "wamid.abc123"}]}
        with patch("src.lambdas.notification_sender.send_text_message", return_value=mock_response) as mock_send:
            result = _send_whatsapp("Hello self!")
        mock_send.assert_called_once_with("Hello self!")
        assert result["channel"] == "whatsapp"
        assert result["status"] == "sent"
        assert result["whatsapp_message_id"] == "wamid.abc123"
        assert result["message"] == "Hello self!"

    def test_send_whatsapp_api_error_returns_error_status(self):
        """_send_whatsapp returns status=error (not raises) when the API fails."""
        from src.utils.whatsapp_client import WhatsAppClientError
        with patch("src.lambdas.notification_sender.send_text_message", side_effect=WhatsAppClientError("bad token")):
            result = _send_whatsapp("Hello self!")
        assert result["channel"] == "whatsapp"
        assert result["status"] == "error"
        assert "bad token" in result["error"]

    def test_send_whatsapp_missing_credentials_returns_error_status(self):
        """_send_whatsapp returns status=error when env vars are missing."""
        import os
        # Clear credentials in a scope-limited way to avoid test pollution
        cleared = {k: "" for k in ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_RECIPIENT_NUMBER")}
        with patch.dict(os.environ, cleared):
            for var in cleared:
                os.environ.pop(var, None)
            result = _send_whatsapp("Test message")
        assert result["channel"] == "whatsapp"
        assert result["status"] == "error"

    def test_send_notification_includes_whatsapp_channel(self):
        """send_notification attempts the whatsapp channel for url type."""
        mock_response = {"messages": [{"id": "wamid.xyz"}]}
        resource = {"storage_path": "resources/links", "text": ""}
        classification = {
            "type": "url",
            "tags": ["link", "web"],
            "urls": ["https://example.com"],
            "metadata": {"domain": "example.com"},
        }
        with patch("src.lambdas.notification_sender.send_text_message", return_value=mock_response):
            result = send_notification(resource, classification)
        channel_names = [ch["channel"] for ch in result["channels_attempted"]]
        assert "whatsapp" in channel_names
        whatsapp_result = next(ch for ch in result["channels_attempted"] if ch["channel"] == "whatsapp")
        assert whatsapp_result["status"] == "sent"
