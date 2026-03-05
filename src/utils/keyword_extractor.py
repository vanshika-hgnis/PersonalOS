"""
Keyword extractor utility.

Extracts meaningful keywords from message text and maps them to
categories defined in the JSON rule configuration.
"""

import re
import json
import logging
import os
from typing import Optional


_STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "is", "it", "as", "be",
        "this", "that", "are", "was", "were", "been", "have", "has",
        "had", "do", "does", "did", "will", "would", "could", "should",
        "may", "might", "i", "you", "he", "she", "we", "they",
        "me", "him", "her", "us", "them", "my", "your", "his",
        "our", "its", "not", "so", "if", "then", "than", "there",
        "their", "what", "which", "who", "how", "when", "where", "why",
    }
)

_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*")

_DEFAULT_RULES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "rules.json"
)


def _load_keyword_categories(rules_path: Optional[str] = None) -> dict[str, list[str]]:
    path = rules_path or _DEFAULT_RULES_PATH
    try:
        with open(path, encoding="utf-8") as fh:
            rules = json.load(fh)
        return rules.get("keyword_categories", {})
    except FileNotFoundError:
        logging.getLogger(__name__).warning("Rules file not found: %s", path)
        return {}
    except json.JSONDecodeError as exc:
        logging.getLogger(__name__).warning("Invalid JSON in rules file %s: %s", path, exc)
        return {}


def extract_keywords(text: str, min_length: int = 3) -> list[str]:
    """Return meaningful keywords extracted from *text*.

    Removes stopwords and short tokens.  Order preserving, duplicates removed.
    """
    if not text:
        return []
    tokens = _TOKEN_PATTERN.findall(text.lower())
    seen: set[str] = set()
    keywords: list[str] = []
    for token in tokens:
        if token not in seen and token not in _STOPWORDS and len(token) >= min_length:
            seen.add(token)
            keywords.append(token)
    return keywords


def categorize_keywords(
    keywords: list[str], rules_path: Optional[str] = None
) -> dict[str, list[str]]:
    """Map *keywords* to their matching categories from the rules config.

    Returns a dict of ``{category: [matched_keywords]}``.
    Only categories with at least one match are included.
    """
    categories = _load_keyword_categories(rules_path)
    result: dict[str, list[str]] = {}
    keyword_set = set(kw.lower() for kw in keywords)
    for category, category_keywords in categories.items():
        matches = [kw for kw in category_keywords if kw.lower() in keyword_set]
        if matches:
            result[category] = matches
    return result
