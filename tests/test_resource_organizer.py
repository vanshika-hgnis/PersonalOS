"""
Tests for src/lambdas/resource_organizer.py
"""

import pytest
from src.lambdas.resource_organizer import (
    organize_resource,
    get_all_resources,
    get_resources_by_type,
    clear_resources,
)


@pytest.fixture(autouse=True)
def reset_store():
    """Clear the in-memory store before every test."""
    clear_resources()
    yield
    clear_resources()


class TestOrganizeResource:
    def test_url_stored_in_links_folder(self):
        message = {"message_id": "1", "text": "https://example.com", "timestamp": ""}
        classification = {"type": "url", "tags": ["link"], "urls": ["https://example.com"],
                          "keywords": [], "keyword_categories": {}, "metadata": {}}
        resource = organize_resource(message, classification)
        assert resource["storage_path"] == "resources/links"
        assert resource["type"] == "url"

    def test_pdf_stored_in_documents_folder(self):
        message = {"message_id": "2", "text": "https://example.com/doc.pdf", "timestamp": ""}
        classification = {"type": "pdf", "tags": ["pdf"], "urls": ["https://example.com/doc.pdf"],
                          "keywords": [], "keyword_categories": {}, "metadata": {}}
        resource = organize_resource(message, classification)
        assert resource["storage_path"] == "resources/documents"

    def test_note_stored_in_notes_folder(self):
        message = {"message_id": "3", "text": "Remember the dentist", "timestamp": ""}
        classification = {"type": "note", "tags": ["note"], "urls": [],
                          "keywords": ["remember", "dentist"], "keyword_categories": {},
                          "metadata": {"word_count": 3}}
        resource = organize_resource(message, classification)
        assert resource["storage_path"] == "resources/notes"

    def test_unknown_stored_in_inbox(self):
        message = {"message_id": "4", "text": "", "timestamp": ""}
        classification = {"type": "unknown", "tags": [], "urls": [],
                          "keywords": [], "keyword_categories": {}, "metadata": {}}
        resource = organize_resource(message, classification)
        assert resource["storage_path"] == "resources/inbox"

    def test_resource_contains_all_fields(self):
        message = {"message_id": "5", "text": "Test note content here", "timestamp": "2024-01-01T00:00:00Z"}
        classification = {"type": "note", "tags": ["note"], "urls": [],
                          "keywords": ["test", "note", "content"],
                          "keyword_categories": {}, "metadata": {}}
        resource = organize_resource(message, classification)
        assert "message_id" in resource
        assert "timestamp" in resource
        assert "type" in resource
        assert "tags" in resource
        assert "urls" in resource
        assert "keywords" in resource
        assert "storage_path" in resource


class TestGetResourcesByType:
    def test_get_url_resources(self):
        message = {"message_id": "10", "text": "https://example.com", "timestamp": ""}
        classification = {"type": "url", "tags": ["link"], "urls": ["https://example.com"],
                          "keywords": [], "keyword_categories": {}, "metadata": {}}
        organize_resource(message, classification)
        resources = get_resources_by_type("url")
        assert len(resources) == 1
        assert resources[0]["type"] == "url"

    def test_get_all_resources(self):
        msg1 = {"message_id": "11", "text": "https://example.com", "timestamp": ""}
        cls1 = {"type": "url", "tags": [], "urls": [], "keywords": [],
                "keyword_categories": {}, "metadata": {}}
        msg2 = {"message_id": "12", "text": "A note", "timestamp": ""}
        cls2 = {"type": "note", "tags": [], "urls": [], "keywords": [],
                "keyword_categories": {}, "metadata": {}}
        organize_resource(msg1, cls1)
        organize_resource(msg2, cls2)
        all_resources = get_all_resources()
        total = sum(len(v) for v in all_resources.values())
        assert total == 2

    def test_empty_store_returns_empty(self):
        resources = get_resources_by_type("url")
        assert resources == []
