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

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

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

