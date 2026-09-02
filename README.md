# TRACEFORGE

> Behavioral CI/CD and Runtime Intelligence Platform for AI Applications.

TRACEFORGE Foundation v0.1 provides an end-to-end local vertical slice for capturing, ingesting, persisting, and querying execution traces from AI agents, LLM calls, retrieval engines, and tools.

---

## Architecture Overview

```
[ Example Agent App ]
         │
  (TRACEFORGE SDK)
         │
 (OpenTelemetry API)
         │
         ▼
[ FastAPI Collector ] ──POST /api/v1/traces──► [ PostgreSQL ]
                                                      ▲
[ REST API / Consumer ] ──GET /api/v1/traces/{id}─────┘
```

---

## Component Layout

- `sdk/traceforge/`: Python SDK built on OpenTelemetry API for wrapping trace & span executions.
- `collector/app/`: FastAPI server for receiving telemetry payloads (`main.py`, `schemas.py`) and PostgreSQL storage persistence (`db.py`, `models.py`).
- `examples/basic_agent/`: Minimal runnable script simulating nested agent operations (`agent_run` -> `llm_call`, `retrieval`, `tool_call`).
- `tests/`: Automated unit and integration test suite (`test_sdk.py`, `test_api.py`, `test_storage.py`).
- `docs/`: Product specification (`product.md`) and technical architecture details (`architecture.md`).

---

## Getting Started

### 1. Environment Setup & Dependencies

Requires **Python 3.12+**.

```bash
# Create and activate a virtual environment
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate

# Install dependencies and local packages in editable mode
pip install -e ".[dev]"
```

### 2. Configuration & Environment Variables

Configure application settings via environment variables or a local `.env` file:

```env
DATABASE_URL=postgresql+psycopg://traceforge:traceforge_dev_pass@localhost:5432/traceforge
TRACEFORGE_COLLECTOR_URL=http://localhost:8000/api/v1/traces
HOST=0.0.0.0
PORT=8000
```

### 3. Start PostgreSQL Database

Launch the local PostgreSQL 16 container via Docker Compose:

```bash
docker compose up -d postgres
```

Verify that PostgreSQL container is running and healthy:

```bash
docker compose ps
```

### 4. Start TRACEFORGE Collector & REST API

Run the FastAPI server using `uvicorn`:

```bash
uvicorn collector.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The service will automatically create database tables (`traces` and `spans`) upon startup.

Check health status:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"ok","database":"ok"}
```

### 5. Run the Showcase Agent Application

In a separate terminal:

```bash
python examples/showcase_agent/main.py
```

Output:
```
🚀 Starting TRACEFORGE End-to-End Showcase Agent Application...
📌 [TRACE CREATED] Trace ID: a2923d86b435089276886de2a0b6e256
  🔍 [SPAN: retrieval] Executing vector database retrieval...
  🤖 [SPAN: llm] Calling LLM engine (claude-3-5-sonnet)...
  🗄️ [SPAN: database] Querying account database...
  🛠️ [SPAN: tool] Executing billing upgrade action...
✅ Showcase Agent execution finished!

✨ Evaluation Completed! Overall Status: PASS
   ✅ [latency_sla] Score: 1.0 | Status: PASS
   ✅ [token_budget] Score: 1.0 | Status: PASS
   ✅ [retrieval_relevancy] Score: 1.0 | Status: PASS
```

### 6. Interactive CLI Tool (`traceforge-cli`)

Use the built-in command-line tool to inspect traces, visualize span waterfalls, run behavioral evaluations, and view platform metrics:

```bash
# List recent recorded traces
python -m traceforge.cli list

# Inspect a trace with span waterfall rendering
python -m traceforge.cli get <TRACE_ID>

# Run automated behavioral evaluation suite
python -m traceforge.cli eval <TRACE_ID>

# View aggregate runtime analytics and SLA metrics
python -m traceforge.cli stats
```

### 7. REST API Endpoints

- `POST /api/v1/traces`: Ingest telemetry payload safely and idempotently.
- `GET /api/v1/traces`: List recorded traces with pagination (`limit`, `offset`).
- `GET /api/v1/traces/{trace_id}`: Fetch complete trace hierarchy and span waterfall details.
- `POST /api/v1/evaluations/run/{trace_id}`: Trigger automated behavioral evaluations (Latency SLA, Token Budget, Retrieval Relevancy).
- `GET /api/v1/traces/{trace_id}/evaluations`: Retrieve evaluation report for a trace.
- `GET /api/v1/analytics/summary`: Aggregate metrics (total traces, total tokens, total cost, pass rate, p50/p90/p99 duration).

---

## Automated Test Suite

Execute the comprehensive pytest suite:

```bash
pytest -v
```

Tests cover:
- SDK trace & span creation, timing, decorator ergonomics, context hierarchy, and attribute recording.
- SDK exporter graceful failure handling on network errors.
- REST API health check, ingestion, pagination, evaluation scoring, analytics, and 422/404 error handling.
- Ingestion safe idempotence for duplicate submissions.
- Behavioral evaluation rules (`LatencyEvaluator`, `TokenBudgetEvaluator`, `RetrievalRelevancyEvaluator`).
- SQLAlchemy 2.0 trace, span, and evaluation model persistence.

