"""
Tests for src/utils/whatsapp_client.py
"""

import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.utils.whatsapp_client import (
    WhatsAppClientError,
    send_text_message,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CREDS = {
    "WHATSAPP_ACCESS_TOKEN": "test_token",
    "WHATSAPP_PHONE_NUMBER_ID": "123456789",
    "WHATSAPP_RECIPIENT_NUMBER": "15550001111",
}


def _mock_ok_response(message_id: str = "wamid.test001") -> MagicMock:
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = {"messages": [{"id": message_id}]}
    return resp


def _mock_error_response(status_code: int = 401, text: str = "Unauthorized") -> MagicMock:
    resp = MagicMock()
    resp.ok = False
    resp.status_code = status_code
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSendTextMessage:
    def test_sends_to_correct_url(self):
        """Posts to the correct Graph API endpoint."""
        with patch.dict(os.environ, _CREDS):
            with patch("requests.post", return_value=_mock_ok_response()) as mock_post:
                send_text_message("Hello!")
        url = mock_post.call_args[0][0]
        assert "123456789" in url
        assert url.endswith("/messages")
        assert url.startswith("https://graph.facebook.com/")

    def test_sends_bearer_token(self):
        """Includes Bearer auth header."""
        with patch.dict(os.environ, _CREDS):
            with patch("requests.post", return_value=_mock_ok_response()) as mock_post:
                send_text_message("Hello!")
        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test_token"

    def test_payload_structure(self):
        """Request body has the correct WhatsApp message structure."""
        with patch.dict(os.environ, _CREDS):
            with patch("requests.post", return_value=_mock_ok_response()) as mock_post:
                send_text_message("Hello self!")
        body = mock_post.call_args[1]["json"]
        assert body["messaging_product"] == "whatsapp"
        assert body["to"] == "15550001111"
        assert body["type"] == "text"
        assert body["text"]["body"] == "Hello self!"

    def test_returns_parsed_json_on_success(self):
        """Returns the API response body as a dict."""
        with patch.dict(os.environ, _CREDS):
            with patch("requests.post", return_value=_mock_ok_response("wamid.abc")):
                result = send_text_message("Hi")
        assert result["messages"][0]["id"] == "wamid.abc"

    def test_raises_on_http_error(self):
        """Raises WhatsAppClientError when the API returns a non-2xx status."""
        with patch.dict(os.environ, _CREDS):
            with patch("requests.post", return_value=_mock_error_response(401, "Unauthorized")):
                with pytest.raises(WhatsAppClientError, match="401"):
                    send_text_message("Hi")

    def test_raises_on_network_error(self):
        """Raises WhatsAppClientError when a network exception occurs."""
        with patch.dict(os.environ, _CREDS):
            with patch("requests.post", side_effect=requests.ConnectionError("timeout")):
                with pytest.raises(WhatsAppClientError, match="Network error"):
                    send_text_message("Hi")

    def test_raises_when_access_token_missing(self):
        """Raises WhatsAppClientError when WHATSAPP_ACCESS_TOKEN is not set."""
        env = {k: v for k, v in _CREDS.items() if k != "WHATSAPP_ACCESS_TOKEN"}
        clean_env = {k: "" for k in _CREDS}
        clean_env.update(env)
        with patch.dict(os.environ, clean_env):
            os.environ.pop("WHATSAPP_ACCESS_TOKEN", None)
            with pytest.raises(WhatsAppClientError, match="WHATSAPP_ACCESS_TOKEN"):
                send_text_message("Hi")

    def test_raises_when_phone_number_id_missing(self):
        """Raises WhatsAppClientError when WHATSAPP_PHONE_NUMBER_ID is not set."""
        env = {k: v for k, v in _CREDS.items() if k != "WHATSAPP_PHONE_NUMBER_ID"}
        clean_env = {k: "" for k in _CREDS}
        clean_env.update(env)
        with patch.dict(os.environ, clean_env):
            os.environ.pop("WHATSAPP_PHONE_NUMBER_ID", None)
            with pytest.raises(WhatsAppClientError, match="WHATSAPP_PHONE_NUMBER_ID"):
                send_text_message("Hi")

    def test_explicit_args_override_env_vars(self):
        """Explicit keyword arguments take precedence over env vars."""
        with patch("requests.post", return_value=_mock_ok_response()) as mock_post:
            send_text_message(
                "Hi",
                access_token="override_token",
                phone_number_id="999",
                recipient_number="15559999999",
            )
        headers = mock_post.call_args[1]["headers"]
        body = mock_post.call_args[1]["json"]
        assert headers["Authorization"] == "Bearer override_token"
        assert "999" in mock_post.call_args[0][0]
        assert body["to"] == "15559999999"

    def test_uses_default_api_version(self):
        """Uses v19.0 when WHATSAPP_API_VERSION is not set."""
        env = dict(_CREDS)
        env.pop("WHATSAPP_API_VERSION", None)
        with patch.dict(os.environ, env):
            os.environ.pop("WHATSAPP_API_VERSION", None)
            with patch("requests.post", return_value=_mock_ok_response()) as mock_post:
                send_text_message("Hi")
        url = mock_post.call_args[0][0]
        assert "v19.0" in url

    def test_custom_api_version(self):
        """Respects explicit api_version argument."""
        with patch.dict(os.environ, _CREDS):
            with patch("requests.post", return_value=_mock_ok_response()) as mock_post:
                send_text_message("Hi", api_version="v18.0")
        url = mock_post.call_args[0][0]
        assert "v18.0" in url
