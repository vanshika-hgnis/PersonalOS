"""
Resource organizer Lambda.

Takes a classified message and stores it in the appropriate logical
folder defined by ``config/rules.json`` under ``storage.folders``.

In production this would write to S3 / DynamoDB.  Here we use an
in-memory store so that the module is fully testable without AWS
credentials, and expose a ``get_all_resources`` helper for inspection.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_DEFAULT_RULES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "rules.json"
)

# In-memory resource store  {folder: [resource, ...]}
_RESOURCE_STORE: dict[str, list[dict]] = {}


def _load_storage_config(rules_path: str) -> dict:
    try:
        with open(rules_path, encoding="utf-8") as fh:
            rules = json.load(fh)
        return rules.get("storage", {})
    except FileNotFoundError:
        logger.warning("Rules file not found: %s", rules_path)
        return {}
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON in rules file %s: %s", rules_path, exc)
        return {}


def organize_resource(
    message: dict,
    classification: dict,
    rules_path: str = _DEFAULT_RULES_PATH,
) -> dict:
    """Organise a classified message into the correct resource folder.

    Returns the resource record that was stored.
    """
    storage_cfg = _load_storage_config(rules_path)
    folders = storage_cfg.get("folders", {})
    base_path = storage_cfg.get("base_path", "resources")

    msg_type = classification.get("type", "unknown")
    folder = folders.get(msg_type, folders.get("unknown", "inbox"))
    storage_path = f"{base_path}/{folder}"

    resource = {
        "message_id": message.get("message_id", ""),
        "timestamp": message.get("timestamp") or datetime.now(tz=timezone.utc).isoformat(),
        "type": msg_type,
        "tags": classification.get("tags", []),
        "urls": classification.get("urls", []),
        "keywords": classification.get("keywords", []),
        "keyword_categories": classification.get("keyword_categories", {}),
        "text": message.get("text", ""),
        "metadata": classification.get("metadata", {}),
        "storage_path": storage_path,
    }

    _RESOURCE_STORE.setdefault(storage_path, []).append(resource)
    logger.info("Stored resource type='%s' at '%s'", msg_type, storage_path)
    return resource


def get_all_resources() -> dict[str, list[dict]]:
    """Return the entire in-memory resource store (useful for testing)."""
    return dict(_RESOURCE_STORE)


def get_resources_by_type(msg_type: str, rules_path: str = _DEFAULT_RULES_PATH) -> list[dict]:
    """Return all stored resources of the given *msg_type*."""
    storage_cfg = _load_storage_config(rules_path)
    folders = storage_cfg.get("folders", {})
    base_path = storage_cfg.get("base_path", "resources")
    folder = folders.get(msg_type, folders.get("unknown", "inbox"))
    storage_path = f"{base_path}/{folder}"
    return list(_RESOURCE_STORE.get(storage_path, []))


def clear_resources() -> None:
    """Clear the in-memory store (useful for test isolation)."""
    _RESOURCE_STORE.clear()


# ---------------------------------------------------------------------------
# AWS Lambda entry-point
# ---------------------------------------------------------------------------

def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda handler – organises a pre-classified message."""
    try:
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        message = body.get("message", {})
        classification = body.get("classification", {})
        resource = organize_resource(message, classification)

        return {
            "statusCode": 200,
            "body": json.dumps(resource),
        }
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Error organising resource: %s", exc)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(exc)}),
        }
