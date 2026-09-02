import argparse
import os
import sys
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")



def get_collector_url() -> str:
    url = os.getenv("TRACEFORGE_COLLECTOR_URL", "http://localhost:8000")
    if url.endswith("/api/v1/traces"):
        url = url[:-14]
    return url.rstrip("/")


def cmd_list(args):
    base_url = get_collector_url()
    try:
        resp = httpx.get(f"{base_url}/api/v1/traces?limit={args.limit}&offset={args.offset}")
        if resp.status_code != 200:
            print(f"❌ Error fetching traces: HTTP {resp.status_code} - {resp.text}")
            sys.exit(1)

        data = resp.json()
        items = data.get("items", [])
        total = data.get("total", 0)

        print(f"\n📊 TRACEFORGE Traces (Total: {total}, Showing: {len(items)})\n" + "=" * 90)
        print(f"{'TRACE ID':<34} | {'NAME':<18} | {'STATUS':<6} | {'DURATION':<10} | {'SPANS'}")
        print("-" * 90)

        for item in items:
            t_id = item.get("trace_id", "")
            name = item.get("name", "")[:18]
            status = item.get("status", "OK")
            duration = f"{item.get('duration_ms', 0):.1f}ms"
            spans_cnt = len(item.get("spans", []))
            print(f"{t_id:<34} | {name:<18} | {status:<6} | {duration:<10} | {spans_cnt}")

        print("=" * 90 + "\n")
    except Exception as e:
        print(f"❌ Failed to connect to TRACEFORGE Collector at {base_url}: {e}")
        sys.exit(1)


def cmd_get(args):
    base_url = get_collector_url()
    t_id = args.trace_id
    try:
        resp = httpx.get(f"{base_url}/api/v1/traces/{t_id}")
        if resp.status_code == 404:
            print(f"❌ Trace '{t_id}' not found.")
            sys.exit(1)
        elif resp.status_code != 200:
            print(f"❌ Error fetching trace: HTTP {resp.status_code} - {resp.text}")
            sys.exit(1)

        trace = resp.json()
        print(f"\n🔍 TRACE DETAILS: {trace['name']} ({trace['trace_id']})")
        print(f"Status: {trace['status']} | Duration: {trace.get('duration_ms', 0):.2f}ms | Start: {trace['start_time']}")
        print("\n🌊 Span Waterfall Visualization:\n" + "=" * 80)

        spans = trace.get("spans", [])
        # Build parent -> children tree
        span_map = {s["span_id"]: s for s in spans}
        children_map = {}
        roots = []

        for s in spans:
            pid = s.get("parent_span_id")
            if not pid or pid not in span_map:
                roots.append(s)
            else:
                children_map.setdefault(pid, []).append(s)

        def print_span(span, depth=0):
            indent = "  " * depth + ("└─ " if depth > 0 else "• ")
            stype = span.get("span_type", "agent").upper()
            duration = f"{span.get('duration_ms', 0):.1f}ms"
            attrs = span.get("attributes", {})
            attr_summary = ", ".join(f"{k}={v}" for k, v in list(attrs.items())[:3])
            if attr_summary:
                attr_summary = f" ({attr_summary})"

            print(f"{indent}[{stype}] {span['name']} - {duration} [{span['status']}]{attr_summary}")
            for child in children_map.get(span["span_id"], []):
                print_span(child, depth + 1)

        for root in roots:
            print_span(root)

        print("=" * 80 + "\n")
    except Exception as e:
        print(f"❌ Failed to query trace '{t_id}': {e}")
        sys.exit(1)


def cmd_eval(args):
    base_url = get_collector_url()
    t_id = args.trace_id
    try:
        req_body = {
            "target_latency_ms": args.latency,
            "max_tokens": args.max_tokens,
            "max_cost": args.max_cost,
        }
        resp = httpx.post(f"{base_url}/api/v1/evaluations/run/{t_id}", json=req_body)
        if resp.status_code == 404:
            print(f"❌ Trace '{t_id}' not found for evaluation.")
            sys.exit(1)
        elif resp.status_code != 200:
            print(f"❌ Error running evaluation: HTTP {resp.status_code} - {resp.text}")
            sys.exit(1)

        report = resp.json()
        overall = report.get("overall_status", "UNKNOWN")
        icon = "✅" if overall == "PASS" else ("⚠️" if overall == "WARN" else "❌")

        print(f"\n🧪 TRACE BEHAVIORAL EVALUATION REPORT {icon}")
        print(f"Trace ID: {report['trace_id']} | Overall Status: {overall} | Evaluated Rules: {report['total_evaluations']}")
        print("=" * 85)
        print(f"{'EVALUATION RULE':<22} | {'STATUS':<6} | {'SCORE':<5} | {'DETAILS'}")
        print("-" * 85)

        for ev in report.get("evaluations", []):
            etype = ev.get("eval_type", "")
            status = ev.get("status", "")
            score = f"{ev.get('score', 0.0):.2f}"
            details = ", ".join(f"{k}={v}" for k, v in ev.get("details", {}).items())
            print(f"{etype:<22} | {status:<6} | {score:<5} | {details}")

        print("=" * 85 + "\n")
    except Exception as e:
        print(f"❌ Failed to evaluate trace '{t_id}': {e}")
        sys.exit(1)


def cmd_stats(args):
    base_url = get_collector_url()
    try:
        resp = httpx.get(f"{base_url}/api/v1/analytics/summary")
        if resp.status_code != 200:
            print(f"❌ Error fetching analytics: HTTP {resp.status_code} - {resp.text}")
            sys.exit(1)

        stats = resp.json()
        print("\n📈 TRACEFORGE RUNTIME INTELLIGENCE & ANALYTICS")
        print("=" * 60)
        print(f"Total Traces Captured  : {stats['total_traces']}")
        print(f"Total Spans Executed  : {stats['total_spans']}")
        print(f"Evaluation Pass Rate   : {stats['pass_rate_percent']:.1f}% ({stats['passed_evaluations']} passed / {stats['failed_evaluations']} failed)")
        print(f"Total LLM Tokens Used  : {stats['total_tokens']:,}")
        print(f"Est. LLM Cost (USD)    : ${stats['total_cost_usd']:.4f}")
        print("-" * 60)
        print("Latency SLA Percentiles:")
        print(f"  • p50 Duration       : {stats['p50_duration_ms']:.1f} ms")
        print(f"  • p90 Duration       : {stats['p90_duration_ms']:.1f} ms")
        print(f"  • p99 Duration       : {stats['p99_duration_ms']:.1f} ms")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"❌ Failed to fetch analytics summary: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="TRACEFORGE Developer Platform CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # list
    p_list = subparsers.add_parser("list", help="List recent recorded traces")
    p_list.add_argument("--limit", type=int, default=20, help="Max traces to show")
    p_list.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    p_list.set_defaults(func=cmd_list)

    # get
    p_get = subparsers.add_parser("get", help="Inspect a trace and display span waterfall")
    p_get.add_argument("trace_id", type=str, help="Trace ID to inspect")
    p_get.set_defaults(func=cmd_get)

    # eval
    p_eval = subparsers.add_parser("eval", help="Run behavioral evaluation suite on a trace")
    p_eval.add_argument("trace_id", type=str, help="Trace ID to evaluate")
    p_eval.add_argument("--latency", type=float, default=3000.0, help="Target SLA latency in ms")
    p_eval.add_argument("--max-tokens", type=int, default=2000, help="Max allowed LLM tokens")
    p_eval.add_argument("--max-cost", type=float, default=0.05, help="Max allowed LLM cost in USD")
    p_eval.set_defaults(func=cmd_eval)

    # stats
    p_stats = subparsers.add_parser("stats", help="View platform aggregate analytics and SLAs")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
