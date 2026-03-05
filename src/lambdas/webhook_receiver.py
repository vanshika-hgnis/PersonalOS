"""
Webhook receiver Lambda.

Entry-point for WhatsApp webhook events.  Validates the request,
parses the payload, and fans out to the classifier and resource
organizer for each message received.

Webhook verification (GET) and message delivery (POST) are both
handled here, following the WhatsApp Business Platform pattern.
"""

import hashlib
import hmac
import json
import logging
import os
from typing import Any

from src.lambdas.message_classifier import classify_message
from src.lambdas.resource_organizer import organize_resource
from src.lambdas.notification_sender import send_notification

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Shared secret used to verify WhatsApp webhook payloads.
# Set via the WEBHOOK_SECRET environment variable.
_WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
_VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_verify_token")


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

def _verify_signature(payload: str, signature_header: str, secret: str) -> bool:
    """Return True when the HMAC-SHA256 signature matches the payload."""
    if not secret or not signature_header:
        return False
    try:
        expected = "sha256=" + hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature_header)
    except Exception:  # pylint: disable=broad-except
        return False


# ---------------------------------------------------------------------------
# Payload parsing
# ---------------------------------------------------------------------------

def _extract_messages(payload: dict) -> list[dict]:
    """Extract individual message objects from a WhatsApp webhook payload."""
    messages: list[dict] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                # Normalise to a flat structure consumed by the classifier
                text_obj = msg.get("text", {})
                media_obj = (
                    msg.get("image")
                    or msg.get("video")
                    or msg.get("audio")
                    or msg.get("document")
                    or {}
                )
                messages.append(
                    {
                        "message_id": msg.get("id", ""),
                        "timestamp": msg.get("timestamp", ""),
                        "from": msg.get("from", ""),
                        "text": text_obj.get("body", "") if isinstance(text_obj, dict) else str(text_obj),
                        "media_type": media_obj.get("mime_type", ""),
                        "media_url": media_obj.get("link", ""),
                        "raw": msg,
                    }
                )
    return messages


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_webhook(payload: dict) -> list[dict]:
    """Process a full webhook payload; returns a list of processing results."""
    messages = _extract_messages(payload)
    results: list[dict] = []
    for message in messages:
        try:
            classification = classify_message(message)
            resource = organize_resource(message, classification)
            notification_result = send_notification(resource, classification)
            results.append(
                {
                    "message_id": message.get("message_id"),
                    "classification": classification,
                    "resource": resource,
                    "notification": notification_result,
                    "status": "processed",
                }
            )
            logger.info(
                "Processed message %s as '%s'",
                message.get("message_id"),
                classification.get("type"),
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to process message %s: %s", message.get("message_id"), exc)
            results.append(
                {
                    "message_id": message.get("message_id"),
                    "status": "error",
                    "error": str(exc),
                }
            )
    return results


# ---------------------------------------------------------------------------
# AWS Lambda entry-point
# ---------------------------------------------------------------------------

def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda handler for WhatsApp webhook events."""
    http_method = event.get("httpMethod", "POST").upper()
    query_params = event.get("queryStringParameters") or {}
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}

    # --- Webhook verification (GET) ---
    if http_method == "GET":
        mode = query_params.get("hub.mode", "")
        token = query_params.get("hub.verify_token", "")
        challenge = query_params.get("hub.challenge", "")
        if mode == "subscribe" and token == _VERIFY_TOKEN:
            logger.info("Webhook verification successful")
            return {"statusCode": 200, "body": challenge}
        logger.warning("Webhook verification failed")
        return {"statusCode": 403, "body": "Forbidden"}

    # --- Message delivery (POST) ---
    raw_body = event.get("body", "{}")
    if isinstance(raw_body, bytes):
        raw_body = raw_body.decode()

    signature = headers.get("x-hub-signature-256", "")
    if _WEBHOOK_SECRET and not _verify_signature(raw_body, signature, _WEBHOOK_SECRET):
        logger.warning("Invalid webhook signature")
        return {"statusCode": 403, "body": "Invalid signature"}

    try:
        payload = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse webhook body: %s", exc)
        return {"statusCode": 400, "body": "Invalid JSON"}

    results = process_webhook(payload)
    return {
        "statusCode": 200,
        "body": json.dumps({"processed": len(results), "results": results}),
    }
