"""Comprehensive Pytest test suite for TRACEFORGE Engineering Intelligence Agent showcase."""
import pytest
from fastapi.testclient import TestClient

from examples.mcp.github_server import GitHubMCPServer
from examples.mcp.runtime_server import RuntimeMCPServer
from examples.engineering_agent.state import AgentState, EvidenceItem
from examples.engineering_agent.llm import LLMInterface
from examples.engineering_agent.graph import build_investigation_graph, run_investigation
from examples.engineering_agent.main import app


def test_mcp_github_server_schemas_and_tools():
    """Verify GitHub MCP server tools return structured valid data."""
    github = GitHubMCPServer()
    
    # 1. get_repository
    repo = github.get_repository("acme-corp/checkout-api")
    assert repo["name"] == "acme-corp/checkout-api"
    assert repo["owner"] == "acme-corp"

    # 2. list_recent_commits
    commits = github.list_recent_commits("acme-corp/checkout-api", limit=2)
    assert len(commits) == 2
    assert commits[0]["sha"] == "86a5672"

    # 3. get_commit
    commit = github.get_commit("acme-corp/checkout-api", "86a5672")
    assert "loyalty" in commit["message"]
    assert "unindexed" in commit["diff_summary"].lower()

    # 4. get_pull_request
    pr = github.get_pull_request("acme-corp/checkout-api", 142)
    assert pr["number"] == 142
    assert pr["status"] == "merged"

    # Invalid repo
    with pytest.raises(ValueError):
        github.get_repository("invalid/repo")


def test_mcp_runtime_server_schemas_and_tools():
    """Verify Operations & Runtime MCP server tools return structured metrics and logs."""
    runtime = RuntimeMCPServer()

    # 1. list_services
    services = runtime.list_services()
    assert "checkout-api" in services

    # 2. get_service_health
    health = runtime.get_service_health("checkout-api")
    assert health["status"] == "degraded"
    assert health["p95_latency_ms"] > 1000.0

    # 3. get_deployment_status
    deploy = runtime.get_deployment_status("checkout-api")
    assert deploy["current_version"] == "v1.8.0"

    # 4. get_recent_logs
    logs = runtime.get_recent_logs("checkout-api", minutes=30)
    assert len(logs) > 0
    assert any("Slow query" in l["message"] for l in logs)

    # 5. get_service_metrics
    metrics = runtime.get_service_metrics("checkout-api", metric="latency")
    assert metrics["metric"] == "latency_p95"
    assert len(metrics["values"]) > 0


def test_agent_state_transitions():
    """Test Pydantic AgentState data model validation."""
    state = AgentState(incident="Test latency issue", service="checkout-api")
    assert state.service == "checkout-api"
    assert len(state.evidence) == 0

    item = EvidenceItem(
        source="github",
        tool_used="github.get_commit",
        summary="Found suspicious commit 86a5672",
        details={"sha": "86a5672"},
    )
    state.evidence.append(item)
    assert len(state.evidence) == 1
    assert state.evidence[0].source == "github"


def test_llm_interface_deterministic_reasoning():
    """Test LLM abstraction layer deterministic reasoning over evidence."""
    llm = LLMInterface(provider="mock")
    evidence = [
        {"source": "github", "summary": "Commit 86a5672 introduced unindexed database query"},
        {"source": "runtime", "summary": "p95 latency spiked to 2850ms"},
        {"source": "logs", "summary": "Slow query detected in validate_loyalty_discount"},
    ]

    result = llm.reason_over_evidence("Find root cause", evidence)
    assert result["validated"] is True
    assert result["confidence"] >= 0.90
    assert "86a5672" in result["root_cause"] or "N+1" in result["root_cause"]


def test_langgraph_graph_compilation_and_execution():
    """Test compiling and executing the LangGraph StateGraph workflow."""
    graph = build_investigation_graph()
    assert graph is not None

    final_state = run_investigation(
        incident="Checkout API latency spiked after deployment",
        service="checkout-api",
    )

    assert final_state.final_report is not None
    assert "ROOT CAUSE" in final_state.final_report
    assert final_state.confidence > 0.8
    assert final_state.trace_id is not None


def test_fastapi_agent_endpoints():
    """Test FastAPI Agent HTTP endpoints (POST /api/v1/investigate and GET /health)."""
    client = TestClient(app)

    # 1. Health check
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    # 2. Investigate endpoint
    payload = {
        "incident": "Checkout API latency regression",
        "service": "checkout-api",
    }
    res_inv = client.post("/api/v1/investigate", json=payload)
    assert res_inv.status_code == 200

    data = res_inv.json()
    assert "incident_id" in data
    assert data["service"] == "checkout-api"
    assert data["confidence"] > 0.80
    assert len(data["evidence"]) > 0
    assert "86a5672" in data["root_cause"] or "N+1" in data["root_cause"] or "database" in data["root_cause"].lower()
