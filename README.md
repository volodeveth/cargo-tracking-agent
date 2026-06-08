# Cargo Tracking Agent

A Python service that accepts a list of AWB and sea-container numbers, auto-detects the type of each number, fetches current tracking status from available online sources, and returns a unified, schema-stable JSON with events, ETA/ETD, current status, source provenance, quality metrics, and per-number errors.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [How It Works](#how-it-works)
4. [Run Locally](#run-locally)
5. [Run with Docker](#run-with-docker)
6. [Input Formats](#input-formats)
7. [Output Format](#output-format)
8. [Supported Sources](#supported-sources)
9. [Status Reference](#status-reference)
10. [Error Codes](#error-codes)
11. [Quality and Risk](#quality-and-risk)
12. [Optional Features](#optional-features)
13. [How to Add a New Connector](#how-to-add-a-new-connector)
14. [Limitations and Known Issues](#limitations-and-known-issues)
15. [Acceptance Criteria Map](#acceptance-criteria-map)

---

## Overview

Cargo Tracking Agent processes a batch of shipment identifiers in a single request:

- **AWB (Air Waybill)** numbers in the format `NNN-NNNNNNNN` (e.g., `080-38652331`)
- **Sea container** numbers in ISO 6346 format `AAAA NNNNNNN` (e.g., `TLLU4912250`)

Each number is processed independently — one failure never blocks the rest. The output is a schema-stable JSON that is identical in structure regardless of the source or the error state, making it safe to integrate downstream.

---

## Architecture

```
API / CLI / Web UI
      │
Input Parser ──► Number Type Detector ──► Source Router
      │                                        │
      │                          ┌─────────────┴──────────────┐
      │                          ▼                            ▼
      │                  Source Connectors (Protocol)   (fallback chain)
      │                   ├ TrackTraceAirConnector
      │                   ├ TrackTraceContainerConnector
      │                   ├ CarrierWebsiteConnector
      │                   ├ CargoAiConnector (optional, API)
      │                   └ FixtureConnector (demo/tests)
      │                          │
      ▼                          ▼
   Parser  ◄──────────  Raw Response (HTML/JSON)
      │
Status Normalizer (deterministic dict + optional LLM fallback)
      │
Quality Scorer ──► JSON Response Builder ──► Output (full + short)
      │
Logger / Debug Artifacts (per-number step log)
```

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `config.py` | Pydantic-settings; all tuning via env variables |
| `models/enums.py` | `NumberType`, `NormalizedStatus`, `ErrorCode`, `RiskLevel` enums |
| `models/schemas.py` | Pydantic v2 request/response models |
| `detection/detector.py` | `detect_type()`, `normalize_number()`, ISO 6346 check digit |
| `detection/awb_prefixes.py` | AWB prefix → carrier lookup table |
| `connectors/base.py` | `Connector` Protocol + `ConnectorResult` dataclass |
| `connectors/registry.py` | Named connector instances |
| `connectors/track_trace_air.py` | Live Playwright scraper for track-trace.com air cargo |
| `connectors/track_trace_container.py` | Live Playwright scraper for track-trace.com container |
| `connectors/carrier_website.py` | Generic carrier-website fallback connector |
| `connectors/cargoai.py` | Optional CargoAI REST API connector |
| `connectors/fixture.py` | Parses saved HTML fixtures (always works without internet) |
| `parsers/track_trace_parser.py` | BeautifulSoup HTML → `ParsedTracking` |
| `parsers/dates.py` | Raw datetime strings → ISO 8601 `DateInfo` |
| `normalization/normalizer.py` | `raw_status` → `NormalizedStatus` (deterministic rule tables) |
| `normalization/rules_air.py` | Air-cargo keyword → status mapping |
| `normalization/rules_container.py` | Container keyword → status mapping |
| `normalization/translate_uk.py` | `NormalizedStatus` → Ukrainian string (static dict) |
| `quality/scorer.py` | Confidence score, `data_complete`, `missing_fields`, warnings |
| `quality/risk.py` | `risk_level`, `delay_detected`, reasons |
| `llm/assistant.py` | Optional OpenAI-compatible LLM; deterministic fallback if disabled |
| `storage/db.py` | SQLite schema |
| `storage/cache.py` | Result cache with TTL |
| `storage/history.py` | Status history + diff on re-check |
| `pipeline/orchestrator.py` | Single-shipment end-to-end processing |
| `pipeline/router.py` | Build ordered connector chain per number type |
| `pipeline/queue.py` | `asyncio.Queue` bounded worker pool |
| `pipeline/builder.py` | Assemble `TrackingResponse` / `ShortResult` |
| `scheduler/recheck.py` | APScheduler job that re-tracks non-delivered shipments |
| `webhook/notifier.py` | POST on status change with HMAC signature |
| `export/excel.py` | Excel export via openpyxl |
| `export/sheets.py` | Optional Google Sheets export |
| `api/app.py` | FastAPI application wiring |
| `api/routes.py` | `POST /track`, `POST /track/file`, `GET /results`, `GET /export` |
| `api/web.py` | Upload UI (HTML page) |
| `cli.py` | CLI entry: read JSON/CSV → write JSON |

---

## How It Works

1. **Input parsing** — JSON or CSV is read into `ShipmentInput` objects.
2. **Type detection** — `detect_type()` applies regex patterns:
   - `^\d{3}-?\d{8}$` → `air_awb`
   - `^[A-Z]{4}\d{7}$` → `sea_container`
   - anything else → `unknown` + `INVALID_FORMAT` error
3. **Source routing** — `router.py` builds an ordered connector chain for the detected type:
   - Air AWB: `TrackTraceAirConnector` → `CarrierWebsiteConnector` → `CargoAiConnector` → `FixtureConnector`
   - Container: `TrackTraceContainerConnector` → `CarrierWebsiteConnector` → `FixtureConnector`
4. **Connector fallback** — connectors are tried in order; first `OK` result wins. Live connectors use Playwright to scrape track-trace.com. If a live site returns a CAPTCHA or is unavailable the connector returns `CAPTCHA_REQUIRED` or `SOURCE_UNAVAILABLE` and the next connector in the chain is tried. The `FixtureConnector` at the end of the chain parses saved HTML sample pages and always provides a result for the two demo numbers (`080-38652331` and `TLLU4912250`).
5. **Parsing** — BeautifulSoup extracts events, dates (ETD/ETA/actual), and route from the raw HTML.
6. **Normalization** — deterministic keyword-rule tables map `raw_status` text to a `NormalizedStatus` enum value. If the optional LLM is enabled and the result is still `unknown`, the LLM proposes a value from the allowed enum; the proposal is validated and discarded if invalid.
7. **Quality and risk scoring** — confidence, missing fields, delay detection, and risk level are computed deterministically.
8. **Output** — `build_response()` assembles a `TrackingResponse`; CLI writes it to a JSON file or stdout.

The live connector path uses Playwright (real browser automation). Running without a Playwright-accessible Chromium still works via the fixture fallback — the full parse/normalize/quality pipeline is exercised without any internet access.

---

## Run Locally

### Requirements

- Python 3.11+
- (optional) Chromium for live scraping

### Steps

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 2. Install the package in editable mode with dev dependencies
pip install -e ".[dev]"

# 3. (Optional) Install Chromium for live track-trace.com scraping
playwright install chromium

# 4. Copy the example env file and adjust as needed
cp .env.example .env

# 5. Run the CLI
python -m tracking_agent.cli --input examples/input.json --output examples/output.json

# Print to stdout instead of writing a file
python -m tracking_agent.cli --input examples/input.json
```

### Run the API

```bash
uvicorn tracking_agent.api.app:app --reload
```

Open http://localhost:8000 for the file-upload web UI (accepts `.csv` or `.xlsx`).

Track via `curl`:

```bash
curl -X POST http://localhost:8000/track \
  -H "Content-Type: application/json" \
  -d '{
    "shipments": [
      {"id": "s1", "number": "080-38652331"},
      {"id": "s2", "number": "TLLU4912250"}
    ]
  }'
```

### Run tests

```bash
pytest -q
```

---

## Run with Docker

```bash
# Copy and configure env
cp .env.example .env

# Build and start
docker compose up
```

The API is available at http://localhost:8000.

---

## Input Formats

### JSON

```json
{
  "shipments": [
    {"id": "internal-001", "number": "080-38652331"},
    {"id": "internal-002", "number": "501-20285134"},
    {"id": "internal-006", "number": "TLLU4912250"},
    {"id": "internal-011", "number": "hello-bad-number"}
  ]
}
```

Optional fields on each shipment: `type` (hint, not trusted blindly), `carrier`, `comment`.

### CSV

```csv
id,number
internal-001,080-38652331
internal-006,TLLU4912250
```

---

## Output Format

### Full format (default)

The top-level envelope:

```json
{
  "request_id": "cli-728edc30",
  "checked_at": "2026-06-08T11:58:43.479070Z",
  "summary": {"total": 4, "success": 2, "failed": 2},
  "results": [...]
}
```

Each result contains: `input`, `detected`, `tracking`, `source`, `quality`, `risk`, `errors`, `debug`.

Air AWB result snippet (from `examples/output.json`):

```json
{
  "input": {"id": "internal-001", "number": "080-38652331", "type": null, "carrier": null, "comment": null},
  "detected": {
    "type": "air_awb",
    "normalized_number": "080-38652331",
    "carrier": {"name": "LOT Polish Airlines", "code": "LO", "source": "awb_prefix"}
  },
  "tracking": {
    "current_status": "in_transit",
    "raw_status": "In transit / transfer (MAN)",
    "status_uk": "У дорозі",
    "last_event": {
      "event_name": "In transit / transfer (MAN)",
      "location": "DOH",
      "datetime": "2026-06-07T06:10:00+02:00",
      "is_actual": true
    },
    "dates": {
      "etd": {"datetime": "2026-06-05T18:00:00+08:00", "timezone": "+08:00", "timezone_confidence": "source_provided"},
      "eta": {"datetime": "2026-06-08T10:30:00+02:00", "timezone": "+02:00", "timezone_confidence": "source_provided"},
      "actual_departure": null,
      "actual_arrival": null
    },
    "route": {"origin": "HKG", "destination": "WAW", "transit_points": []},
    "events": [
      {"event_name": "Cargo received from shipper (RCS)", "normalized_status": "received", "location": "HKG", "datetime": "2026-06-05T09:15:00+08:00"},
      {"event_name": "Departed from origin airport (DEP)", "normalized_status": "departed", "location": "HKG", "datetime": "2026-06-05T18:45:00+08:00"},
      {"event_name": "In transit / transfer (MAN)", "normalized_status": "in_transit", "location": "DOH", "datetime": "2026-06-07T06:10:00+02:00"}
    ]
  },
  "source": {"primary_source": "track-trace.com/aircargo", "final_source": "fixtures", "url": "fixture://air_080-38652331.html"},
  "quality": {"confidence": 0.7, "data_complete": false, "missing_fields": ["actual_departure", "actual_arrival"], "warnings": []},
  "risk": {"risk_level": "medium", "delay_detected": true, "reasons": ["past_eta"]},
  "errors": [{"code": "PARTIAL_DATA", "message": "Some key fields are missing", "source": "fixtures"}]
}
```

### Short format

`ShortResult` is a compact integration-friendly format containing: `id`, `number`, `type`, `current_status`, `eta`, `etd`, `last_event_at`, `source`, `errors`.

---

## Supported Sources

| Source | Type | Notes |
|---|---|---|
| `track-trace.com/aircargo` | Live (Playwright) | Primary for air AWB; returns `CAPTCHA_REQUIRED` if blocked |
| `track-trace.com/container` | Live (Playwright) | Primary for sea containers; returns `CAPTCHA_REQUIRED` if blocked |
| `carrier_website` | Live (stub) | Generic fallback; extend per carrier |
| `cargoai` | API (optional) | Requires `CARGOAI_API_KEY`; skipped without a key |
| `fixtures` | Local HTML files | Always-available fallback; parses `fixtures/` directory |

### Fallback chain

The router tries connectors in order. The first connector that returns `OK` terminates the chain. If a live connector fails (network error, timeout, CAPTCHA, login required), the error is recorded per-connector and the next connector is tried. The final `FixtureConnector` uses `fixtures/index.json` to look up pre-saved HTML pages — if no fixture exists for a number it returns `NOT_FOUND`.

---

## Status Reference

`normalized_status` is always one of these values:

| Value | Meaning |
|---|---|
| `not_found` | No tracking data found at any source |
| `created` | Shipment record created |
| `booked` | Booking confirmed |
| `received` | Cargo received by carrier |
| `in_origin_terminal` | Cargo accepted at origin terminal |
| `departed` | Departed from origin airport / port |
| `in_transit` | In transit or at transfer point |
| `arrived` | Arrived at destination airport / port |
| `customs` | Under customs clearance |
| `ready_for_pickup` | Available for pickup / notified |
| `delivered` | Delivered to consignee |
| `container_picked_up` | Empty container picked up (sea) |
| `container_returned` | Empty container returned to depot (sea) |
| `exception` | Exception, hold, or delay flagged by carrier |
| `unknown` | Raw status present but no rule matched |

Each result also includes `status_uk` — the same status in Ukrainian.

---

## Error Codes

All errors use one of eight codes (never free-form strings):

| Code | Meaning |
|---|---|
| `INVALID_FORMAT` | Number does not match AWB or container regex |
| `NOT_FOUND` | All sources returned no tracking data |
| `SOURCE_UNAVAILABLE` | Connector could not reach the source |
| `TIMEOUT` | Connector request exceeded the configured timeout |
| `CAPTCHA_REQUIRED` | Live site blocked the request with a CAPTCHA |
| `LOGIN_REQUIRED` | Source requires authentication not provided |
| `PARSING_FAILED` | Source returned data that could not be parsed |
| `PARTIAL_DATA` | Data retrieved but some expected fields are absent |

Errors are a list on each result; `PARTIAL_DATA` is non-blocking (result still counts as partial success).

---

## Quality and Risk

### Quality block

| Field | Description |
|---|---|
| `confidence` | 0.0–1.0; based on presence of events, dates, and route |
| `data_complete` | `true` only when all key fields are populated |
| `missing_fields` | List of field names that are absent |
| `warnings` | Non-fatal notices (e.g. `invalid_check_digit`, `status_normalized_by_llm`) |

### Risk block

| Field | Description |
|---|---|
| `risk_level` | `low` / `medium` / `high` |
| `delay_detected` | `true` when current time is past ETA and status is not a terminal state |
| `reasons` | List of contributing factors (`past_eta`, `exception_status`) |

Risk logic:
- `delay_detected=true` → `medium`
- `exception_status` in reasons → `high`
- Otherwise → `low`

---

## Optional Features

All optional features have a deterministic fallback and are safe to leave disabled.

| Feature | Env variable(s) | Default | Notes |
|---|---|---|---|
| LLM status normalization | `LLM_ENABLED`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | Disabled | OpenAI-compatible; uses OpenRouter by default. Proposes `NormalizedStatus` for unknown raw statuses; proposal validated against enum, discarded if invalid. Never invents dates or facts. |
| Webhook on status change | `WEBHOOK_URL`, `WEBHOOK_SECRET` | Disabled | POST with HMAC-SHA256 signature header; retries on failure; silently off when `WEBHOOK_URL` is empty |
| Scheduled re-check | `RECHECK_ENABLED`, `RECHECK_INTERVAL_MINUTES` | Disabled | APScheduler re-tracks all non-delivered numbers in history every N minutes |
| Google Sheets export | install `.[sheets]` + set service-account env vars | Disabled | Requires `google-api-python-client` extra and a service-account credentials file; falls back to Excel silently |
| Result cache | `CACHE_TTL_MINUTES` | 60 min | SQLite-backed; keyed on normalized number |
| Debug artifacts | `DEBUG_ARTIFACTS` | Disabled | Saves raw HTML and screenshots per number to `data/debug/` |

---

## How to Add a New Connector

1. **Implement** the `Connector` Protocol in a new file under `src/tracking_agent/connectors/`:

```python
# src/tracking_agent/connectors/my_carrier.py
from __future__ import annotations
from ..models.enums import NumberType
from .base import Connector, ConnectorResult, ConnectorStatus, ErrorCode


class MyCarrierConnector:
    name = "my-carrier"
    supports = (NumberType.AIR_AWB,)

    async def fetch(self, normalized_number: str, number_type: NumberType) -> ConnectorResult:
        # Call the carrier API or scrape its website.
        # Return ConnectorResult with status=ConnectorStatus.OK and raw_html=...
        # on success, or status=ConnectorStatus.ERROR and error_code=... on failure.
        ...
```

The `Connector` Protocol requires three attributes: `name` (str), `supports` (tuple of `NumberType`), and an async `fetch(normalized_number, number_type) -> ConnectorResult` method.

2. **Register** the connector in `src/tracking_agent/connectors/registry.py`:

```python
from .my_carrier import MyCarrierConnector

def all_connectors():
    return {
        ...
        "my-carrier": MyCarrierConnector(),
    }
```

3. **Add it to the chain** in `src/tracking_agent/pipeline/router.py`:

```python
def build_chain(number_type: NumberType, use_fixtures: bool):
    reg = all_connectors()
    chain = []
    if number_type == NumberType.AIR_AWB:
        chain = [reg["track-trace.com/aircargo"], reg["my-carrier"], reg["carrier_website"], reg["cargoai"]]
    ...
```

The new connector will be tried in order; if it fails the next connector in the chain is tried automatically.

---

## Limitations and Known Issues

- **Live sites require CAPTCHA** — track-trace.com frequently triggers a CAPTCHA for automated requests. When this happens the connector returns `CAPTCHA_REQUIRED` and the pipeline falls through to the next connector (ultimately fixtures). The structured error is preserved in the response.
- **Fixtures used for demo** — `examples/output.json` and the test suite use fixture HTML pages stored in `fixtures/`. Only `080-38652331` (air) and `TLLU4912250` (container) have fixtures; other numbers return `NOT_FOUND` from the fixture connector.
- **ISO 6346 check digit** — the detector validates the check digit and appends a `invalid_check_digit` warning when it mismatches, but does not reject the number or stop processing.
- **SQLite connections** — connections are opened and closed per-operation; there is no explicit connection pool or `PRAGMA` tuning. Suitable for a prototype; replace with PostgreSQL for production load.
- **Google Sheets** — requires the optional `.[sheets]` extra (`pip install -e ".[sheets]"`) and a service-account credentials file; gracefully disabled without them.
- **LLM normalization** — only activates when `LLM_ENABLED=true` and a valid `LLM_API_KEY` is set; output is always validated against the `NormalizedStatus` enum before use.
- **Playwright Chromium** — must be installed separately (`playwright install chromium`) for live scraping; the package itself does not install it automatically.

---

## Acceptance Criteria Map

| TЗ §13 criterion | Coverage |
|---|---|
| Runs locally from README | `Run Locally` section above |
| Accepts JSON list of shipment numbers | `POST /track`, `--input` CLI, `examples/input.json` |
| Each number processed independently | `pipeline/queue.py` worker pool; errors isolated per result |
| Auto-detects type (AWB / container) | `detection/detector.py` |
| Separate logic for AWB and container | `rules_air.py`, `rules_container.py`, per-type connector chains |
| Returns valid JSON | Pydantic v2 schemas enforce structure; `examples/output.json` |
| `normalized_status` + `raw_status` | Both fields present on every tracking result |
| ETA/ETD when available | `dates.etd`, `dates.eta` (ISO 8601 with timezone) |
| Container pickup / return fields | `container_picked_up`, `container_returned` statuses + events |
| Events list | `tracking.events[]` with `event_name`, `location`, `datetime`, `normalized_status` |
| Source provenance block | `source.primary_source`, `source.final_source`, `source.url` |
| Errors block with clear codes | `errors[]` with 8-member `ErrorCode` enum |
| No hardcoded tracking numbers | All numbers come from input; fixtures keyed by runtime-detected normalized number |
| Extensible connectors | `Connector` Protocol — one file + registration, no core changes needed |
| README with run / input / output / connector guide | This document |
