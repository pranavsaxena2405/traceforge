# TRACEFORGE Architecture

## Component Overview

TRACEFORGE Foundation v0.1 consists of five logical components:

```
[ Application / Agent ]
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

1. **SDK (`sdk/traceforge`)**: Captures traces and spans using OpenTelemetry primitives. Wraps executions in context managers (`with trace(...)`, `with span(...)`) and exports telemetry over HTTP to the Collector.
2. **Collector (`collector/app`)**: FastAPI service exposing `/api/v1/traces` to receive telemetry payloads and persist them to PostgreSQL.
3. **Storage (`collector/app/db.py`, `collector/app/models.py`)**: PostgreSQL relational persistence using SQLAlchemy 2.0. Stores trace summaries and span hierarchies.
4. **REST API (`collector/app/main.py`)**: Exposes GET endpoints to fetch stored traces and evaluate span trees.
5. **Example (`examples/basic_agent`)**: Demonstrates SDK tracing of simulated AI workflows (`agent_run` -> `llm_call`, `retrieval`, `tool_call`).

---

## Technical Decisions

### Ingestion Contract (v0.1)
- **Decision**: Milestone v0.1 uses a clean, OTel-aligned custom JSON REST ingestion payload (`POST /api/v1/traces`).
- **Clarification**: v0.1 is **NOT** a full native OTLP receiver (it does not process raw gRPC/Protobuf OTLP byte streams). Using an OTel-aligned JSON payload keeps the local vertical slice lightweight, reliable, and easily inspectable while preserving OpenTelemetry field semantics (`trace_id`, `span_id`, `parent_span_id`, timestamps, status, attributes).

### Ingestion Idempotency Strategy
- **Decision**: Ingestion at `POST /api/v1/traces` is safely idempotent for repeated submissions of identical `trace_id` and `span_id` records.
- **Strategy**: When a trace payload is received, the collector checks for existing `trace_id` and `span_id` records in PostgreSQL. Existing records are updated with the latest end timestamps, status, and merged attributes, while missing records are inserted. This guarantees that retries, network flushes, or duplicate exports do not corrupt the database or produce duplicate key errors.

### Extensible AI Telemetry Model
Spans store generic key-value attributes in a JSON column, allowing future AI metadata attributes to be recorded without schema migrations:
- **LLM**: `provider`, `model`, `input_tokens`, `output_tokens`, `total_tokens`, `prompt_version`, `temperature`, `cost`.
- **Retrieval**: `query`, `top_k`, `documents_retrieved`.
- **Tool/MCP**: `tool_name`, `server_name`, `operation`, `success`.

### Why OpenTelemetry?
OpenTelemetry provides vendor-neutral tracing primitives (`TracerProvider`, `Tracer`, `Span`, `SpanExporter`). Leveraging OTel prevents vendor lock-in and allows TRACEFORGE to standardize telemetry collection.

### Why FastAPI?
FastAPI offers asynchronous request handling, native Pydantic v2 validation, OpenAPI documentation generation, and high throughput for local trace ingestion.

### Why PostgreSQL & SQLAlchemy 2.x?
PostgreSQL provides robust relational semantics, indexing, JSON/JSONB support, and strict transaction handling. SQLAlchemy 2.0 offers modern declarative typing and unit-of-work persistence patterns.

### Why Kafka / Redis / ClickHouse / Kubernetes are NOT used in v0.1
To deliver a complete, runnable vertical slice without operational complexity, distributed stream processors (Kafka), caching layers (Redis), OLAP databases (ClickHouse), and orchestration platforms (Kubernetes) are intentionally deferred until scale demands them in future milestones.

---

## Data Flow & Trace Model

### Trace Model
- `trace_id`: 32-character hex string (OTel standard trace ID).
- `name`: Root span / trace operation name.
- `start_time`: UTC ISO timestamp.
- `end_time`: UTC ISO timestamp (optional/nullable until finished).
- `duration_ms`: Execution duration in milliseconds.
- `status`: Execution status (`OK`, `ERROR`, `UNSET`).
- `attributes`: Dynamic JSON dictionary of metadata.

### Span Model
- `span_id`: 16-character hex string (OTel standard span ID).
- `trace_id`: Foreign key referencing parent trace.
- `parent_span_id`: 16-character hex string of parent span (null for root).
- `name`: Span operation name.
- `span_type`: Category (`agent`, `llm`, `retrieval`, `tool`, `mcp`, `database`, `http`).
- `start_time`: UTC ISO timestamp.
- `end_time`: UTC ISO timestamp.
- `duration_ms`: Execution duration in milliseconds.
- `status`: Span execution status (`OK`, `ERROR`).
- `attributes`: Flexible key-value attribute store.
