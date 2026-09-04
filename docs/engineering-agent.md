# TRACEFORGE Engineering Intelligence Agent (LangGraph + MCP Showcase)

The **TRACEFORGE Engineering Intelligence Agent** is a production-style showcase application built on top of TRACEFORGE v0.1. It demonstrates how an AI engineering agent autonomously investigates production incidents by reasoning across multiple engineering systems using Model Context Protocol (MCP) tools, orchestrated via LangGraph, and monitored end-to-end with TRACEFORGE telemetry.

---

## Architecture Overview

```text
                    USER / API
                         |
                         v
             FastAPI Agent Service
             POST /api/v1/investigate
                         |
                         v
              LangGraph State Graph
                         |
          +--------------+--------------+
          |                             |
          v                             v
   GitHub MCP Server             Runtime MCP Server
   - get_repository              - list_services
   - list_recent_commits         - get_service_health
   - get_commit                  - get_deployment_status
   - get_pull_request            - get_recent_logs
                                 - get_service_metrics
          |                             |
          +--------------+--------------+
                         |
                         v
                  Evidence State
                         |
                         v
                   Hypothesis
                         |
                         v
             Validation & RCA Report
                         |
                         v
                   TRACEFORGE SDK
                         |
                         v
              Trace / Spans / Latency
```

---

## Key Components

1. **LangGraph Workflow (`examples/engineering_agent/graph.py`)**:
   - `understand_incident`: Parses incident query and targets microservice.
   - `investigate_code`: Queries GitHub MCP tools (`list_recent_commits`, `get_commit`, `get_pull_request`).
   - `investigate_runtime`: Queries Operations MCP tools (`get_service_health`, `get_recent_logs`, `get_service_metrics`).
   - `formulate_hypothesis`: Synthesizes evidence to isolate potential root causes.
   - `validate_hypothesis`: Validates hypothesis against telemetry evidence.
   - `should_reinvestigate`: Conditional routing edge.
   - `generate_report`: Produces structured Root Cause Analysis (RCA) report.

2. **MCP Tool Suite (`examples/mcp/`)**:
   - **GitHub MCP Server** (`github_server.py`): Code repos, commit SHAs, code diffs, PR metadata.
   - **Runtime MCP Server** (`runtime_server.py`): Microservice health, p95 latency, slow query log streams, deployment status.

3. **TRACEFORGE Telemetry**:
   - Every node and tool execution produces nested OpenTelemetry-aligned spans exported live to TRACEFORGE Collector.

---

## How to Run the Showcase

### 1. Start TRACEFORGE Collector
```powershell
.\.venv\Scripts\python.exe -m uvicorn collector.app.main:app --port 8000
```

### 2. Run CLI Hero Demo
```powershell
.\.venv\Scripts\python.exe examples/engineering_agent/main.py
```

### 3. Run FastAPI Agent Service
```powershell
.\.venv\Scripts\python.exe examples/engineering_agent/main.py --server
```

Submit investigation request:
```bash
curl -X POST http://localhost:8001/api/v1/investigate \
  -H "Content-Type: application/json" \
  -d '{"incident": "Checkout API latency spiked after deployment", "service": "checkout-api"}'
```

### 4. Inspect Live Telemetry Spans
Open TRACEFORGE Dashboard: **[http://localhost:8000/dashboard](http://localhost:8000/dashboard)**
