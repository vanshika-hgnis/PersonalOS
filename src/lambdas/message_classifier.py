"""
Message classifier Lambda.

Classifies an incoming WhatsApp message into one of:
  - ``url``   – message contains a web link (non-PDF)
  - ``pdf``   – message contains a link to / name of a PDF document
  - ``note``  – plain text note (no URLs)
  - ``media`` – image / video / audio attachment
  - ``unknown`` – does not match any rule

Classification uses the rules defined in ``config/rules.json``.
"""

import json
import logging
import os
from typing import Any

from src.utils.url_extractor import extract_urls, is_pdf_url, get_domain
from src.utils.pdf_detector import detect_pdf_in_message
from src.utils.keyword_extractor import extract_keywords, categorize_keywords

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_DEFAULT_RULES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "rules.json"
)


def _load_rules(rules_path: str) -> dict:
    try:
        with open(rules_path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        logger.warning("Rules file not found: %s", rules_path)
        return {}
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON in rules file %s: %s", rules_path, exc)
        return {}


def classify_message(message: dict, rules_path: str = _DEFAULT_RULES_PATH) -> dict:
    """Classify a single WhatsApp *message* dict.

    Expected *message* keys
    -----------------------
    ``text``        : str  – message body text (optional)
    ``media_type``  : str  – MIME type of attached media (optional)
    ``media_url``   : str  – URL of attached media (optional)
    ``timestamp``   : str  – ISO-8601 timestamp (optional)
    ``message_id``  : str  – unique identifier (optional)

    Returns a classification result dict with keys:
    ``type``, ``tags``, ``urls``, ``keywords``,
    ``keyword_categories``, ``metadata``.
    """
    rules = _load_rules(rules_path)
    classification_rules = rules.get("classification_rules", {})

    text = message.get("text", "") or ""
    media_type = message.get("media_type", "") or ""
    media_url = message.get("media_url", "") or ""

    # --- Media detection (highest specificity) ---
    if media_type or media_url:
        media_rule = classification_rules.get("media", {})
        return _build_result(
            msg_type="media",
            tags=media_rule.get("tags", ["media"]),
            urls=[],
            text=text,
            rules_path=rules_path,
        )

    # --- URL / PDF detection ---
    urls = extract_urls(text)
    pdf_info = detect_pdf_in_message(text)
    if pdf_info["is_pdf"]:
        pdf_rule = classification_rules.get("pdf", {})
        filename = pdf_info["pdf_filenames"][0] if pdf_info["pdf_filenames"] else None
        return _build_result(
            msg_type="pdf",
            tags=pdf_rule.get("tags", ["document", "pdf"]),
            urls=pdf_info["pdf_urls"] or urls,
            text=text,
            rules_path=rules_path,
            extra={"filename": filename},
        )
    if urls:
        url_rule = classification_rules.get("url", {})
        return _build_result(
            msg_type="url",
            tags=url_rule.get("tags", ["link", "web"]),
            urls=urls,
            text=text,
            rules_path=rules_path,
            extra={"domain": get_domain(urls[0])},
        )

    # --- Note detection ---
    note_rule = classification_rules.get("note", {})
    words = text.split()
    min_words = note_rule.get("min_word_count", 3)
    if text and len(words) >= min_words:
        return _build_result(
            msg_type="note",
            tags=note_rule.get("tags", ["note", "text"]),
            urls=[],
            text=text,
            rules_path=rules_path,
            extra={"word_count": len(words), "preview": text[:100]},
        )

    return _build_result(
        msg_type="unknown",
        tags=[],
        urls=[],
        text=text,
        rules_path=rules_path,
    )


def _build_result(
    msg_type: str,
    tags: list[str],
    urls: list[str],
    text: str,
    rules_path: str,
    extra: dict | None = None,
) -> dict:
    keywords = extract_keywords(text)
    kw_categories = categorize_keywords(keywords, rules_path=rules_path)
    result = {
        "type": msg_type,
        "tags": tags,
        "urls": urls,
        "keywords": keywords,
        "keyword_categories": kw_categories,
        "metadata": extra or {},
    }
    return result


# ---------------------------------------------------------------------------
# AWS Lambda entry-point
# ---------------------------------------------------------------------------

def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda handler – classifies a message from an API Gateway event.

    The Lambda expects a JSON body with the message payload.
    """
    try:
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        message = body.get("message", body)
        result = classify_message(message)

        logger.info("Classified message as '%s'", result["type"])
        return {
            "statusCode": 200,
            "body": json.dumps(result),
        }
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Error classifying message: %s", exc)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(exc)}),
        }
