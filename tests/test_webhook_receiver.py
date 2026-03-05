"""
Integration tests for the full webhook → classify → organize → notify pipeline.
"""

import json
import pytest
from src.lambdas.resource_organizer import clear_resources, get_all_resources
from src.lambdas.webhook_receiver import process_webhook, lambda_handler


@pytest.fixture(autouse=True)
def reset_store():
    clear_resources()
    yield
    clear_resources()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_whatsapp_payload(text: str, message_id: str = "msg-001") -> dict:
    """Build a minimal WhatsApp webhook payload for a text message."""
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": message_id,
                                    "timestamp": "1700000000",
                                    "from": "1234567890",
                                    "text": {"body": text},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestProcessWebhook:
    def test_url_message_processed(self):
        payload = _make_whatsapp_payload("Check https://example.com out")
        results = process_webhook(payload)
        assert len(results) == 1
        assert results[0]["status"] == "processed"
        assert results[0]["classification"]["type"] == "url"

    def test_pdf_message_processed(self):
        payload = _make_whatsapp_payload("Download https://example.com/report.pdf")
        results = process_webhook(payload)
        assert results[0]["classification"]["type"] == "pdf"

    def test_note_message_processed(self):
        payload = _make_whatsapp_payload("Remember to buy groceries this evening")
        results = process_webhook(payload)
        assert results[0]["classification"]["type"] == "note"

    def test_resource_saved_after_processing(self):
        payload = _make_whatsapp_payload("https://example.com/article")
        process_webhook(payload)
        all_resources = get_all_resources()
        total = sum(len(v) for v in all_resources.values())
        assert total == 1

    def test_multiple_messages_in_one_payload(self):
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {"id": "1", "timestamp": "", "from": "", "text": {"body": "https://a.com"}},
                                    {"id": "2", "timestamp": "", "from": "", "text": {"body": "Take note of this reminder"}},
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        results = process_webhook(payload)
        assert len(results) == 2
        types = {r["classification"]["type"] for r in results if r["status"] == "processed"}
        assert "url" in types
        assert "note" in types

    def test_empty_payload_returns_empty_results(self):
        assert process_webhook({}) == []


class TestWebhookVerification:
    def test_get_with_correct_token_returns_challenge(self):
        import os
        os.environ["VERIFY_TOKEN"] = "my_verify_token"
        event = {
            "httpMethod": "GET",
            "queryStringParameters": {
                "hub.mode": "subscribe",
                "hub.verify_token": "my_verify_token",
                "hub.challenge": "abc123",
            },
            "headers": {},
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200
        assert response["body"] == "abc123"

    def test_get_with_wrong_token_returns_403(self):
        event = {
            "httpMethod": "GET",
            "queryStringParameters": {
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "abc123",
            },
            "headers": {},
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 403

    def test_post_with_valid_payload_returns_200(self):
        payload = _make_whatsapp_payload("https://example.com")
        event = {
            "httpMethod": "POST",
            "body": json.dumps(payload),
            "headers": {},
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200

    def test_post_with_invalid_json_returns_400(self):
        event = {
            "httpMethod": "POST",
            "body": "not-json",
            "headers": {},
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400
