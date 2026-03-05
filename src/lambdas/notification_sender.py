"""
Notification sender Lambda.

Sends alerts and notifications for newly organised resources based
on the notification rules defined in ``config/rules.json``.

Supported channels (configurable via ``rules.json``):
  - ``log``  – writes to Python logger (always available)

Additional channels (sns, email, slack, etc.) can be added by
extending ``_CHANNEL_HANDLERS`` below.
"""

import json
import logging
import os
from typing import Any

from src.utils.whatsapp_client import WhatsAppClientError, send_text_message

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_DEFAULT_RULES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "rules.json"
)


def _load_notification_rules(rules_path: str) -> dict:
    try:
        with open(rules_path, encoding="utf-8") as fh:
            rules = json.load(fh)
        return rules.get("notification_rules", {})
    except FileNotFoundError:
        logger.warning("Rules file not found: %s", rules_path)
        return {}
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON in rules file %s: %s", rules_path, exc)
        return {}


def _render_template(template: str, resource: dict, classification: dict) -> str:
    """Fill simple ``{key}`` placeholders in *template*."""
    metadata = classification.get("metadata", {})
    urls = classification.get("urls", [])
    variables = {
        "type": classification.get("type", ""),
        "url": urls[0] if urls else "",
        "title": metadata.get("title", metadata.get("domain", "")),
        "filename": metadata.get("filename", ""),
        "preview": metadata.get("preview", resource.get("text", "")[:80]),
        "tags": ", ".join(classification.get("tags", [])),
        "storage_path": resource.get("storage_path", ""),
    }
    try:
        return template.format(**variables)
    except KeyError:
        return template


def _send_log(message: str) -> dict:
    logger.info("[NOTIFICATION] %s", message)
    return {"channel": "log", "message": message, "status": "sent"}


def _send_whatsapp(message: str) -> dict:
    """Send *message* to the configured self-chat WhatsApp number."""
    try:
        response = send_text_message(message)
        message_id = (response.get("messages") or [{}])[0].get("id", "")
        logger.info("[NOTIFICATION] WhatsApp message sent (id=%s)", message_id)
        return {"channel": "whatsapp", "message": message, "status": "sent", "whatsapp_message_id": message_id}
    except WhatsAppClientError as exc:
        logger.error("[NOTIFICATION] WhatsApp send failed: %s", exc)
        return {"channel": "whatsapp", "message": message, "status": "error", "error": str(exc)}


_CHANNEL_HANDLERS = {
    "log": _send_log,
    "whatsapp": _send_whatsapp,
}


def send_notification(
    resource: dict,
    classification: dict,
    rules_path: str = _DEFAULT_RULES_PATH,
) -> dict:
    """Send notifications for a classified resource based on the rules.

    Returns a summary dict with ``enabled``, ``channels_attempted``,
    and per-channel results.
    """
    notification_rules = _load_notification_rules(rules_path)
    msg_type = classification.get("type", "unknown")
    rule = notification_rules.get(msg_type, {})

    if not rule.get("enabled", False):
        logger.debug("Notifications disabled for type '%s'", msg_type)
        return {"enabled": False, "type": msg_type, "channels_attempted": []}

    template = rule.get("message_template", "New {type} resource saved.")
    rendered = _render_template(template, resource, classification)
    channels = rule.get("channels", ["log"])

    channel_results: list[dict] = []
    for channel in channels:
        handler = _CHANNEL_HANDLERS.get(channel)
        if handler:
            result = handler(rendered)
            channel_results.append(result)
        else:
            logger.warning("Unknown notification channel '%s'", channel)
            channel_results.append(
                {"channel": channel, "status": "unknown_channel"}
            )

    return {
        "enabled": True,
        "type": msg_type,
        "message": rendered,
        "channels_attempted": channel_results,
    }


# ---------------------------------------------------------------------------
# AWS Lambda entry-point
# ---------------------------------------------------------------------------

def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda handler – sends notifications for a resource."""
    try:
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        resource = body.get("resource", {})
        classification = body.get("classification", {})
        result = send_notification(resource, classification)

        return {
            "statusCode": 200,
            "body": json.dumps(result),
        }
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Error sending notification: %s", exc)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(exc)}),
        }
