"""LangGraph workflow definition for TRACEFORGE Engineering Intelligence Agent with TRACEFORGE telemetry instrumentation."""
import logging
import time
from typing import Any, Dict, Literal
from langgraph.graph import StateGraph, START, END

from traceforge import trace
from examples.engineering_agent.state import AgentState, EvidenceItem
from examples.engineering_agent.llm import LLMInterface
from examples.mcp.github_server import GitHubMCPServer
from examples.mcp.runtime_server import RuntimeMCPServer

logger = logging.getLogger("traceforge.agent.graph")

github_mcp = GitHubMCPServer()
runtime_mcp = RuntimeMCPServer()
llm_engine = LLMInterface()


def understand_incident_node(state: AgentState) -> Dict[str, Any]:
    """Node 1: Understand incident details and scope target service."""
    t0 = time.time()
    service = state.service or "checkout-api"
    logger.info(f"[Node: understand_incident] Analyzing incident for service: {service}")
    
    findings = {
        "incident_summary": state.incident,
        "target_service": service,
        "investigation_plan": [
            "Inspect recent commits & PRs on GitHub MCP",
            "Check service health & deployment status on Runtime MCP",
            "Fetch recent log warnings & database metric spikes",
        ]
    }
    
    return {
        "findings": findings,
        "service": service,
    }


def investigate_code_node(state: AgentState) -> Dict[str, Any]:
    """Node 2: Investigate code repository & commits via GitHub MCP tools."""
    service = state.service
    repo_name = f"acme-corp/{service}"
    new_evidence = list(state.evidence)
    new_tool_calls = list(state.tool_calls)
    new_errors = list(state.errors)

    logger.info(f"[Node: investigate_code] Querying GitHub MCP for {repo_name}...")

    # Tool Call 1: get_repository
    try:
        repo_data = github_mcp.get_repository(repo_name)
        new_tool_calls.append({"tool": "github.get_repository", "args": {"repository": repo_name}, "success": True})
        new_evidence.append(EvidenceItem(
            source="github",
            tool_used="github.get_repository",
            summary=f"Repository {repo_name} found (Language: {repo_data.get('language')})",
            details=repo_data,
        ))
    except Exception as e:
        new_errors.append(f"github.get_repository error: {str(e)}")
        new_tool_calls.append({"tool": "github.get_repository", "args": {"repository": repo_name}, "success": False, "error": str(e)})

    # Tool Call 2: list_recent_commits
    try:
        commits = github_mcp.list_recent_commits(repo_name, limit=3)
        new_tool_calls.append({"tool": "github.list_recent_commits", "args": {"repository": repo_name, "limit": 3}, "success": True})
        new_evidence.append(EvidenceItem(
            source="github",
            tool_used="github.list_recent_commits",
            summary=f"Retrieved {len(commits)} recent commits for {repo_name}",
            details={"commits": commits},
        ))

        # Tool Call 3: get_commit for suspicious commit
        for c in commits:
            if "promo" in c["message"].lower() or "loyalty" in c["message"].lower() or c["sha"] == "86a5672":
                commit_details = github_mcp.get_commit(repo_name, c["sha"])
                new_tool_calls.append({"tool": "github.get_commit", "args": {"commit_sha": c["sha"]}, "success": True})
                new_evidence.append(EvidenceItem(
                    source="github",
                    tool_used="github.get_commit",
                    summary=f"Commit {c['sha']} introduced loyalty discount unindexed query loop",
                    details=commit_details,
                    severity="high",
                ))
    except Exception as e:
        new_errors.append(f"github commit investigation error: {str(e)}")

    # Tool Call 4: get_pull_request
    try:
        pr_data = github_mcp.get_pull_request(repo_name, 142)
        new_tool_calls.append({"tool": "github.get_pull_request", "args": {"pr_number": 142}, "success": True})
        new_evidence.append(EvidenceItem(
            source="github",
            tool_used="github.get_pull_request",
            summary=f"PR #142 '{pr_data['title']}' merged by {pr_data['author']}",
            details=pr_data,
        ))
    except Exception as e:
        new_errors.append(f"github.get_pull_request error: {str(e)}")

    return {
        "evidence": new_evidence,
        "tool_calls": new_tool_calls,
        "errors": new_errors,
    }


def investigate_runtime_node(state: AgentState) -> Dict[str, Any]:
    """Node 3: Investigate microservice runtime health, logs, deployment & metrics via Runtime MCP tools."""
    service = state.service
    new_evidence = list(state.evidence)
    new_tool_calls = list(state.tool_calls)
    new_errors = list(state.errors)

    logger.info(f"[Node: investigate_runtime] Querying Runtime MCP for {service}...")

    # Tool Call 1: get_service_health
    try:
        health = runtime_mcp.get_service_health(service)
        new_tool_calls.append({"tool": "runtime.get_service_health", "args": {"service_name": service}, "success": True})
        new_evidence.append(EvidenceItem(
            source="runtime",
            tool_used="runtime.get_service_health",
            summary=f"Service status: {health['status'].upper()}, p95 latency: {health['p95_latency_ms']}ms",
            details=health,
            severity="high" if health["status"] == "degraded" else "low",
        ))
    except Exception as e:
        new_errors.append(f"runtime.get_service_health error: {str(e)}")

    # Tool Call 2: get_deployment_status
    try:
        deploy = runtime_mcp.get_deployment_status(service)
        new_tool_calls.append({"tool": "runtime.get_deployment_status", "args": {"service_name": service}, "success": True})
        new_evidence.append(EvidenceItem(
            source="runtime",
            tool_used="runtime.get_deployment_status",
            summary=f"Deployed version {deploy['current_version']} at {deploy['deployed_at']}",
            details=deploy,
        ))
    except Exception as e:
        new_errors.append(f"runtime.get_deployment_status error: {str(e)}")

    # Tool Call 3: get_recent_logs
    try:
        logs = runtime_mcp.get_recent_logs(service, minutes=30)
        new_tool_calls.append({"tool": "runtime.get_recent_logs", "args": {"service_name": service}, "success": True})
        new_evidence.append(EvidenceItem(
            source="logs",
            tool_used="runtime.get_recent_logs",
            summary=f"Captured {len(logs)} recent log entries with slow queries and DB pool timeouts",
            details={"logs": logs},
            severity="high",
        ))
    except Exception as e:
        new_errors.append(f"runtime.get_recent_logs error: {str(e)}")

    # Tool Call 4: get_service_metrics
    try:
        metrics = runtime_mcp.get_service_metrics(service, metric="latency", window="1h")
        new_tool_calls.append({"tool": "runtime.get_service_metrics", "args": {"service_name": service, "metric": "latency"}, "success": True})
        new_evidence.append(EvidenceItem(
            source="metrics",
            tool_used="runtime.get_service_metrics",
            summary=f"Latency metric spiked from 120ms to 2850ms",
            details=metrics,
            severity="high",
        ))
    except Exception as e:
        new_errors.append(f"runtime.get_service_metrics error: {str(e)}")

    return {
        "evidence": new_evidence,
        "tool_calls": new_tool_calls,
        "errors": new_errors,
    }


def formulate_hypothesis_node(state: AgentState) -> Dict[str, Any]:
    """Node 4: Synthesize evidence and formulate candidate root cause hypothesis."""
    logger.info("[Node: formulate_hypothesis] Synthesizing hypotheses from collected evidence...")
    evidence_dicts = [e.model_dump() for e in state.evidence]
    
    result = llm_engine.reason_over_evidence(
        prompt="Formulate root cause hypothesis",
        evidence=evidence_dicts,
    )

    hypotheses = state.hypotheses + [result["hypothesis"]]
    
    return {
        "hypotheses": hypotheses,
        "selected_hypothesis": result["hypothesis"],
        "confidence": result["confidence"],
    }


def validate_hypothesis_node(state: AgentState) -> Dict[str, Any]:
    """Node 5: Validate hypothesis against collected evidence."""
    hypothesis = state.selected_hypothesis
    logger.info(f"[Node: validate_hypothesis] Validating selected hypothesis...")

    evidence_dicts = [e.model_dump() for e in state.evidence]
    result = llm_engine.reason_over_evidence(
        prompt=f"Validate hypothesis: {hypothesis}",
        evidence=evidence_dicts,
    )

    is_validated = result.get("validated", False)
    validation_results = {
        "hypothesis": hypothesis,
        "is_validated": is_validated,
        "confidence": result.get("confidence", 0.0),
        "root_cause": result.get("root_cause"),
        "recommendations": result.get("recommendations", []),
    }

    return {
        "is_validated": is_validated,
        "validation_results": validation_results,
        "confidence": result.get("confidence", 0.0),
        "retry_count": state.retry_count + (0 if is_validated else 1),
    }


def should_reinvestigate_router(state: AgentState) -> Literal["generate_report", "investigate_code"]:
    """Conditional edge router: proceed to RCA report if validated, or loop to retry if insufficient evidence."""
    if state.is_validated or state.retry_count >= 2:
        return "generate_report"
    logger.warning("[Router] Hypothesis not validated on first attempt. Routing to re-investigate code...")
    return "investigate_code"


def generate_report_node(state: AgentState) -> Dict[str, Any]:
    """Node 6: Produce final Root Cause Analysis (RCA) report."""
    logger.info("[Node: generate_report] Generating Root Cause Analysis (RCA) report...")
    v = state.validation_results
    
    report_lines = [
        "## TRACEFORGE ENGINEERING INTELLIGENCE REPORT",
        "",
        f"**Target Service**: `{state.service}`",
        f"**Incident**: {state.incident}",
        f"**Investigation Status**: {'[OK] Validated' if state.is_validated else '[INCONCLUSIVE]'}",
        f"**Confidence Score**: {int(state.confidence * 100)}%",
        "",
        "### ROOT CAUSE",
        v.get("root_cause", "Investigation in progress."),
        "",
        "### COLLECTED EVIDENCE",
    ]

    for idx, item in enumerate(state.evidence, 1):
        report_lines.append(f"{idx}. [{item.source.upper()}] `{item.tool_used}` - {item.summary}")

    report_lines.extend([
        "",
        "### RECOMMENDATIONS",
    ])

    for rec in v.get("recommendations", []):
        report_lines.append(f"- {rec}")

    final_report = "\n".join(report_lines)

    return {
        "final_report": final_report,
    }


def build_investigation_graph() -> Any:
    """Build and compile the explicit LangGraph StateGraph workflow."""
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("understand_incident", understand_incident_node)
    workflow.add_node("investigate_code", investigate_code_node)
    workflow.add_node("investigate_runtime", investigate_runtime_node)
    workflow.add_node("formulate_hypothesis", formulate_hypothesis_node)
    workflow.add_node("validate_hypothesis", validate_hypothesis_node)
    workflow.add_node("generate_report", generate_report_node)

    # Add Edges
    workflow.add_edge(START, "understand_incident")
    workflow.add_edge("understand_incident", "investigate_code")
    workflow.add_edge("investigate_code", "investigate_runtime")
    workflow.add_edge("investigate_runtime", "formulate_hypothesis")
    workflow.add_edge("formulate_hypothesis", "validate_hypothesis")
    
    # Conditional Edge
    workflow.add_conditional_edges(
        "validate_hypothesis",
        should_reinvestigate_router,
        {
            "generate_report": "generate_report",
            "investigate_code": "investigate_code",
        }
    )

    workflow.add_edge("generate_report", END)

    return workflow.compile()


def run_investigation(incident: str, service: str = "checkout-api") -> AgentState:
    """Public execution entrypoint for running the LangGraph Agent instrumented with TRACEFORGE telemetry."""
    graph = build_investigation_graph()
    initial_state = AgentState(incident=incident, service=service)

    # Instrument complete workflow with TRACEFORGE trace context
    with trace("incident_investigation", attributes={
        "agent.name": "TRACEFORGE Engineering Intelligence Agent",
        "service.name": service,
        "incident.query": incident,
    }) as trace_ctx:
        initial_state.trace_id = trace_ctx.trace_id

        # Node 1 Span
        with trace_ctx.span("understand_incident", span_type="agent", attributes={"node.name": "understand_incident"}):
            node1_output = understand_incident_node(initial_state)
            current_state = initial_state.model_copy(update=node1_output)

        # Node 2 Span
        with trace_ctx.span("investigate_code", span_type="agent", attributes={"node.name": "investigate_code"}):
            node2_output = investigate_code_node(current_state)
            current_state = current_state.model_copy(update=node2_output)

        # Node 3 Span
        with trace_ctx.span("investigate_runtime", span_type="agent", attributes={"node.name": "investigate_runtime"}):
            node3_output = investigate_runtime_node(current_state)
            current_state = current_state.model_copy(update=node3_output)

        # Node 4 Span
        with trace_ctx.span("formulate_hypothesis", span_type="agent", attributes={"node.name": "formulate_hypothesis"}):
            node4_output = formulate_hypothesis_node(current_state)
            current_state = current_state.model_copy(update=node4_output)

        # Node 5 Span
        with trace_ctx.span("validate_hypothesis", span_type="agent", attributes={"node.name": "validate_hypothesis"}):
            node5_output = validate_hypothesis_node(current_state)
            current_state = current_state.model_copy(update=node5_output)

        # Conditional Routing Execution
        next_step = should_reinvestigate_router(current_state)
        if next_step == "investigate_code":
            with trace_ctx.span("re_investigate_code", span_type="agent", attributes={"node.name": "re_investigate_code", "retry": True}):
                retry_output = investigate_code_node(current_state)
                current_state = current_state.model_copy(update=retry_output)

        # Node 6 Span
        with trace_ctx.span("generate_report", span_type="agent", attributes={"node.name": "generate_report", "confidence": current_state.confidence}):
            node6_output = generate_report_node(current_state)
            final_state = current_state.model_copy(update=node6_output)

        return final_state
