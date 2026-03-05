# PersonalOS — Personal Knowledge Automation System

**Tech:** Python, AWS Lambda, API Gateway, WhatsApp Cloud API, Webhooks, REST APIs, JSON

## Overview

Designed an event-driven automation system that ingests WhatsApp self-chat messages via **WhatsApp Cloud API webhooks** and organizes links, PDFs, and notes into structured resources.

## Features

- **Lambda Message Handlers** — Built Python AWS Lambda handlers to parse incoming webhook payloads, extract URLs/PDF references, and generate normalized metadata for downstream workflows.

- **JSON Rules Engine** — Implemented a JSON-based rules engine to classify content (tags/categories/priority) and trigger configurable actions (store, notify, route).

- **REST API Integrations** — Integrated external services using REST APIs to push categorized resources into productivity/tools endpoints (extensible connector pattern).

- **Reliability** — Added deduplication, validation, and error handling to improve ingestion reliability and avoid repeated processing.

- **Throughput** — Designed for 100+ messages/day throughput, targeting ~80% reduction in manual link/document organization time.

## Architecture

```
WhatsApp Cloud API
       │  webhook (POST)
       ▼
  API Gateway
       │
       ▼
  AWS Lambda  ──►  JSON Rules Engine  ──►  REST API connectors
                         │
                         ▼
               Structured Resource Store
```

## Setup

1. Configure your **WhatsApp Cloud API** webhook URL to point to the API Gateway endpoint.
2. Deploy the Lambda functions with the required environment variables (see `.env.example`).
3. Customize the `rules.json` file to define your classification tags, categories, and routing actions.

