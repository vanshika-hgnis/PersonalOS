# PersonalOS
Personal OS workflow automation system that processes messages from WhatsApp self-chat to automatically organize links, PDFs, and notes into structured resources.

## Overview

PersonalOS is an event-driven workflow automation system built on Python AWS Lambda functions. It receives WhatsApp self-chat messages via webhook, classifies the content, organizes it into structured folders, and sends notifications – all in real time.

**Key capabilities:**
- Classifies 100+ messages/day into URLs, PDFs, notes, and media
- Extracts URLs, PDF filenames, and keywords automatically
- Routes resources to the correct structured folder (links / documents / notes / media / inbox)
- Sends per-type notifications based on JSON-configurable rules
- Modular design for extending with new channels or integrations

---

## Architecture

```
WhatsApp Self-Chat
       │
       ▼ (HTTP POST)
┌─────────────────────┐
│  webhook_receiver   │  ← Validates signature, parses payload
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  message_classifier │  ← URL / PDF / note / media / unknown
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  resource_organizer │  ← Stores in resources/{links,documents,notes,media,inbox}
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ notification_sender │  ← Logs / alerts via configurable channels
└─────────────────────┘
```

---

## Prerequisites

- **Python 3.11+** (the type-hint syntax used requires 3.10+; 3.11 is recommended)
- **pip** (comes with Python)
- A **Meta developer account** with a WhatsApp Business app (only needed for live webhook testing – unit tests run entirely offline)

---

## Setup & Installation

### 1 – Clone the repository

```bash
git clone https://github.com/vanshika-hgnis/PersonalOS.git
cd PersonalOS
```

### 2 – Create and activate a virtual environment

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 3 – Install dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file (or export the variables in your shell) before running the system.  
**Never commit this file** – it contains secrets.

```dotenv
# ── Webhook security ───────────────────────────────────────────────────────
# Secret used to verify the HMAC-SHA256 signature on every incoming webhook.
# Set the same value in the Meta app's webhook settings.
WEBHOOK_SECRET=your_webhook_secret_here

# Token checked during the one-time webhook verification handshake.
# Must match the "Verify token" you enter in the Meta app dashboard.
VERIFY_TOKEN=my_verify_token

# ── WhatsApp Cloud API credentials ─────────────────────────────────────────
# Permanent or temporary access token from the Meta app dashboard.
WHATSAPP_ACCESS_TOKEN=your_access_token_here

# Numeric Phone Number ID shown on the Meta app's "API Setup" page.
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here

# Recipient phone number in E.164 format.
# For self-chat (testing) use your own number, e.g. "15551234567".
WHATSAPP_RECIPIENT_NUMBER=your_whatsapp_number_here

# (Optional) Meta Graph API version. Defaults to v19.0.
# WHATSAPP_API_VERSION=v19.0
```

Load the file in your shell session before running any commands:

```bash
# macOS / Linux
export $(grep -v '^#' .env | xargs)

# Or install python-dotenv and call load_dotenv() in your code
```

---

## Running Tests

All tests are fully offline and do not require real WhatsApp credentials.

```bash
# Run the full test suite
python -m pytest tests/ -v

# Run only webhook-related tests
python -m pytest tests/test_webhook_receiver.py tests/test_whatsapp_client.py -v
```

---

## Testing the WhatsApp Webhook Locally

The steps below let you receive real WhatsApp messages on your local machine without deploying to AWS.

### Step 1 – Run a local HTTP server

The `lambda_handler` function in `webhook_receiver.py` follows the AWS API Gateway event format.  
The simplest way to expose it locally is a small Flask adapter.

Create a file `local_server.py` in the project root:

```python
"""Minimal dev server - converts Flask requests to Lambda-style events."""
import os
from flask import Flask, request
from src.lambdas.webhook_receiver import lambda_handler

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    event = {
        "httpMethod": request.method,
        "queryStringParameters": dict(request.args),
        "headers": dict(request.headers),
        "body": request.get_data(as_text=True),
    }
    result = lambda_handler(event, None)
    return app.response_class(
        response=result.get("body", ""),
        status=result.get("statusCode", 200),
        mimetype="application/json",
    )

if __name__ == "__main__":
    app.run(port=5000, debug=True)
```

Install Flask and run:

```bash
pip install flask python-dotenv
python local_server.py
```

### Step 2 – Expose your local server with ngrok

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 5000
```

Copy the **Forwarding HTTPS URL** (e.g. `https://abc123.ngrok-free.app`).

### Step 3 – Register the webhook with Meta

1. Go to [Meta for Developers](https://developers.facebook.com/) → your WhatsApp app → **Configuration**.
2. Under **Webhook**, click **Edit**.
3. Set **Callback URL** to `https://abc123.ngrok-free.app/webhook`.
4. Set **Verify Token** to the value of `VERIFY_TOKEN` in your `.env` file.
5. Click **Verify and Save** – Meta sends a `GET` request that the server handles automatically.
6. Subscribe to the **messages** field under *Webhook Fields*.

### Step 4 – Send a test message to yourself

Send a WhatsApp message **to yourself** (self-chat) from your registered phone number.  
Watch the local server logs – you should see the message classified and a notification logged:

```
INFO:src.lambdas.webhook_receiver:Processed message <id> as 'url'
INFO:src.lambdas.notification_sender:Sent notification for type 'url' via log
```

### Step 5 – Simulate a webhook event with curl

You can test the full pipeline without ngrok by posting a mock payload to the local server:

```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "id": "test-001",
            "timestamp": "1700000000",
            "from": "15551234567",
            "text": {"body": "Check out https://example.com"}
          }]
        }
      }]
    }]
  }'
```

Expected response:

```json
{"processed": 1, "results": [{"message_id": "test-001", "classification": {"type": "url", ...}, "status": "processed"}]}
```

---

## Project Structure

```
PersonalOS/
├── config/
│   └── rules.json              # Classification, keyword & notification rules
├── src/
│   ├── lambdas/
│   │   ├── webhook_receiver.py     # AWS Lambda – WhatsApp webhook entry-point
│   │   ├── message_classifier.py  # AWS Lambda – classifies incoming messages
│   │   ├── resource_organizer.py  # AWS Lambda – organizes resources into folders
│   │   └── notification_sender.py # AWS Lambda – sends alerts / notifications
│   └── utils/
│       ├── url_extractor.py    # Extracts & analyses URLs from text
│       ├── pdf_detector.py     # Detects PDF URLs and bare filenames
│       └── keyword_extractor.py # Extracts keywords and maps to categories
├── tests/
│   ├── test_url_extractor.py
│   ├── test_pdf_detector.py
│   ├── test_keyword_extractor.py
│   ├── test_message_classifier.py
│   ├── test_resource_organizer.py
│   ├── test_notification_sender.py
│   └── test_webhook_receiver.py    # End-to-end integration tests
├── requirements.txt
└── pytest.ini
```

---

## Configuration (`config/rules.json`)

All classification, keyword mapping, notification, and storage rules are driven by a single JSON file.

| Section | Purpose |
|---|---|
| `classification_rules` | Defines tags and patterns for each message type |
| `keyword_categories` | Maps keywords to categories (productivity, research, …) |
| `notification_rules` | Per-type notification templates and channels |
| `storage` | Base path and per-type folder names |

### Message types

| Type | Detection logic |
|---|---|
| `pdf` | URL ending in `.pdf` **or** bare `filename.pdf` in text |
| `url` | Any `http://`, `https://`, or `www.` link |
| `note` | Plain text with ≥ 3 words and no URLs |
| `media` | Message with a `media_type` or `media_url` |
| `unknown` | Does not match any rule |

---

## Lambda Functions

### `webhook_receiver`
- Handles WhatsApp webhook **verification** (`GET hub.verify_token`)
- Validates HMAC-SHA256 payload signature (`X-Hub-Signature-256`)
- Parses the payload and fans messages out to the classifier and organizer

**Environment variables:**

| Variable | Default | Description |
|---|---|---|
| `WEBHOOK_SECRET` | *(empty)* | HMAC secret for signature verification |
| `VERIFY_TOKEN` | `my_verify_token` | Token used during webhook registration |

### `message_classifier`
Classifies a message dict and returns `type`, `tags`, `urls`, `keywords`, `keyword_categories`, and `metadata`.

### `resource_organizer`
Stores the classified resource in the appropriate folder.  In production, swap the in-memory store for S3/DynamoDB writes.

### `notification_sender`
Sends notifications for the resource.  Channels are pluggable via `_CHANNEL_HANDLERS` (currently `log`; extend with SNS, Slack, email, etc.).

---

## Extending the System

**Add a new notification channel** (e.g. Slack):
1. Implement `_send_slack(message: str) -> dict` in `notification_sender.py`
2. Register it: `_CHANNEL_HANDLERS["slack"] = _send_slack`
3. Add `"slack"` to the desired type's `channels` list in `rules.json`

**Add a new resource type:**
1. Add a new entry under `classification_rules` in `rules.json`
2. Add the matching folder under `storage.folders`
3. Add detection logic in `message_classifier.classify_message`

