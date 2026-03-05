"""
WhatsApp Cloud API client.

Sends a text message to a WhatsApp number via the Meta Graph API.
All credentials are read from environment variables:

  WHATSAPP_ACCESS_TOKEN    – permanent or temporary access token from Meta
  WHATSAPP_PHONE_NUMBER_ID – the numeric phone-number ID of your business line
  WHATSAPP_RECIPIENT_NUMBER – the recipient's phone number in E.164 format
                              (e.g. "15551234567"). For self-chat this is
                              your own number.
  WHATSAPP_API_VERSION     – (optional) Graph API version, default "v19.0"

The module deliberately raises ``WhatsAppClientError`` for all API-level
failures so callers can handle them without inspecting raw HTTP responses.
"""

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.facebook.com"
_DEFAULT_API_VERSION = "v19.0"


class WhatsAppClientError(Exception):
    """Raised when the WhatsApp Cloud API returns an error."""


def _get_required_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise WhatsAppClientError(
            f"Required environment variable '{name}' is not set."
        )
    return value


def send_text_message(
    text: str,
    *,
    access_token: str | None = None,
    phone_number_id: str | None = None,
    recipient_number: str | None = None,
    api_version: str | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    """Send *text* to *recipient_number* via the WhatsApp Cloud API.

    Parameters default to the corresponding environment variables when not
    supplied explicitly, which is the normal production path.

    Returns the parsed JSON response body on success.
    Raises :exc:`WhatsAppClientError` on any API or network error.
    """
    access_token = access_token or _get_required_env("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = phone_number_id or _get_required_env("WHATSAPP_PHONE_NUMBER_ID")
    recipient_number = recipient_number or _get_required_env("WHATSAPP_RECIPIENT_NUMBER")
    api_version = api_version or os.environ.get("WHATSAPP_API_VERSION", _DEFAULT_API_VERSION)

    url = f"{_GRAPH_BASE}/{api_version}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_number,
        "type": "text",
        "text": {"body": text},
    }

    logger.debug("Sending WhatsApp message to %s via phone_number_id=%s", recipient_number, phone_number_id)

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        raise WhatsAppClientError(f"Network error calling WhatsApp API: {exc}") from exc

    if not response.ok:
        raise WhatsAppClientError(
            f"WhatsApp API returned {response.status_code}: {response.text}"
        )

    return response.json()
