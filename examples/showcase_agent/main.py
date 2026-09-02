import os
import sys
import time
import httpx

# Ensure sdk directory is on path for direct execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../sdk")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from traceforge import trace



def run_showcase_agent():
    print("\n🚀 Starting TRACEFORGE End-to-End Showcase Agent Application...")
    collector_url = os.getenv("TRACEFORGE_COLLECTOR_URL", "http://localhost:8000/api/v1/traces")

    # 1. Start Top-Level Agent Trace
    with trace(
        "customer_support_agent",
        attributes={
            "user_id": "usr_alpha_99",
            "session_id": "sess_881920",
            "channel": "web_chat",
            "environment": "production",
        },
        collector_url=collector_url,
    ) as run:
        print(f"📌 [TRACE CREATED] Trace ID: {run.trace_id}")
        time.sleep(0.02)

        # 2. RAG Context Retrieval Phase
        print("  🔍 [SPAN: retrieval] Executing vector database retrieval...")
        with run.span(
            "vector_search",
            span_type="retrieval",
            attributes={
                "query": "How do I upgrade my account tier to enterprise?",
                "index_name": "support_knowledge_base",
                "top_k": 5,
                "documents_retrieved": 5,
                "vector_score_avg": 0.92,
            },
        ):
            time.sleep(0.06)

        # 3. LLM Reasoning & Intent Analysis Phase
        print("  🤖 [SPAN: llm] Calling LLM engine (claude-3-5-sonnet)...")
        with run.span(
            "llm_intent_analysis",
            span_type="llm",
            attributes={
                "provider": "anthropic",
                "model": "claude-3-5-sonnet",
                "temperature": 0.1,
                "input_tokens": 1250,
                "output_tokens": 340,
                "total_tokens": 1590,
                "cost": 0.0088,
            },
        ):
            time.sleep(0.12)

        # 4. Database Query Tool Phase
        print("  🗄️ [SPAN: database] Querying account database...")
        with run.span(
            "query_user_account",
            span_type="database",
            attributes={
                "database": "production_users",
                "operation": "SELECT current_tier, status FROM users WHERE id='usr_alpha_99'",
                "rows_returned": 1,
            },
        ):
            time.sleep(0.03)

        # 5. Billing Gateway Action Tool Phase
        print("  🛠️ [SPAN: tool] Executing billing upgrade action...")
        with run.span(
            "execute_tier_upgrade",
            span_type="tool",
            attributes={
                "tool_name": "billing_gateway",
                "action": "process_upgrade",
                "target_tier": "enterprise",
                "payment_verified": True,
                "success": True,
            },
        ):
            time.sleep(0.04)

    print("✅ Showcase Agent execution finished!")

    # 6. Auto-run Behavioral Evaluations via Collector API
    base_url = collector_url.replace("/api/v1/traces", "")
    eval_url = f"{base_url}/api/v1/evaluations/run/{run.trace_id}"
    print(f"\n🧪 Triggering automated behavioral evaluation suite on Trace '{run.trace_id}'...")

    try:
        resp = httpx.post(eval_url, json={"target_latency_ms": 3000.0, "max_tokens": 2000, "max_cost": 0.05})
        if resp.status_code == 200:
            report = resp.json()
            print(f"✨ Evaluation Completed! Overall Status: {report['overall_status']}")
            for ev in report.get("evaluations", []):
                icon = "✅" if ev['status'] == "PASS" else ("⚠️" if ev['status'] == "WARN" else "❌")
                print(f"   {icon} [{ev['eval_type']}] Score: {ev['score']} | Status: {ev['status']}")
        else:
            print(f"⚠️ Collector evaluation returned HTTP {resp.status_code}")
    except Exception as exc:
        print(f"⚠️ Evaluation check skipped (Collector offline): {exc}")

    print("\n💡 Test CLI Commands to inspect this trace:")
    print(f"   python -m traceforge.cli get {run.trace_id}")
    print(f"   python -m traceforge.cli eval {run.trace_id}")
    print("   python -m traceforge.cli stats\n")


if __name__ == "__main__":
    run_showcase_agent()
