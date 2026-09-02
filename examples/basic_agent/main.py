import os
import sys
import time

# Ensure sdk directory is on path for direct execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../sdk")))

from traceforge import trace


def run_simulated_agent():
    print("[TRACEFORGE] Starting Basic Agent Simulation...")

    with trace(
        "agent_run",
        attributes={"user_id": "usr_99812", "agent_version": "v1.2.0"},
    ) as run:
        print(f"[TRACE] Created Trace ID: {run.trace_id}")

        # 1. Retrieval Span
        print("  [SPAN: retrieval] Simulating retrieval phase...")
        with run.span(
            "retrieval",
            span_type="retrieval",
            attributes={
                "query": "What are TRACEFORGE system requirements?",
                "top_k": 3,
                "documents_retrieved": 3,
            },
        ):
            time.sleep(0.05)

        # 2. LLM Call Span
        print("  [SPAN: llm] Simulating LLM call phase...")
        with run.span(
            "llm_call",
            span_type="llm",
            attributes={
                "provider": "openai",
                "model": "gpt-4o",
                "temperature": 0.2,
                "input_tokens": 450,
                "output_tokens": 120,
                "total_tokens": 570,
                "cost": 0.0035,
            },
        ):
            time.sleep(0.1)

        # 3. Tool Call Span
        print("  [SPAN: tool] Simulating tool call phase...")
        with run.span(
            "tool_call",
            span_type="tool",
            attributes={
                "tool_name": "web_search",
                "server_name": "search_cluster_1",
                "operation": "execute_search",
                "success": True,
            },
        ):
            time.sleep(0.03)

    print("[TRACEFORGE] Agent run completed successfully!")
    print(f"[INFO] Fetch trace at: http://localhost:8000/api/v1/traces/{run.trace_id}")


if __name__ == "__main__":
    run_simulated_agent()
