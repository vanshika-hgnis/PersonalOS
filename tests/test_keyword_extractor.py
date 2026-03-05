"""
Tests for src/utils/keyword_extractor.py
"""

import pytest
from src.utils.keyword_extractor import extract_keywords, categorize_keywords


class TestExtractKeywords:
    def test_basic_extraction(self):
        keywords = extract_keywords("Buy this product at a great deal today")
        assert "buy" in keywords
        assert "product" in keywords
        assert "deal" in keywords

    def test_stopwords_removed(self):
        keywords = extract_keywords("the quick brown fox")
        assert "the" not in keywords
        assert "quick" in keywords
        assert "brown" in keywords
        assert "fox" in keywords

    def test_min_length_filter(self):
        keywords = extract_keywords("I go to a big store", min_length=4)
        assert "big" not in keywords
        assert "store" in keywords

    def test_deduplication(self):
        keywords = extract_keywords("buy buy buy")
        assert keywords.count("buy") == 1

    def test_empty_text(self):
        assert extract_keywords("") == []

    def test_none_text(self):
        assert extract_keywords(None) == []

    def test_case_insensitive(self):
        keywords = extract_keywords("Tutorial TUTORIAL tutorial")
        assert keywords.count("tutorial") == 1


class TestCategorizeKeywords:
    def test_productivity_category(self):
        keywords = ["todo", "meeting", "schedule"]
        result = categorize_keywords(keywords)
        assert "productivity" in result
        assert "todo" in result["productivity"]

    def test_research_category(self):
        keywords = ["article", "paper", "analysis"]
        result = categorize_keywords(keywords)
        assert "research" in result

    def test_no_match(self):
        keywords = ["xyz", "zzz", "aaa"]
        result = categorize_keywords(keywords)
        assert result == {}

    def test_multiple_categories(self):
        keywords = ["todo", "article", "buy"]
        result = categorize_keywords(keywords)
        assert "productivity" in result
        assert "research" in result
        assert "shopping" in result

    def test_empty_keywords(self):
        assert categorize_keywords([]) == {}
