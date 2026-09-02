from datetime import datetime, timezone
from fastapi import status
import pytest

from collector.app.models import SpanModel, TraceModel
from collector.app.evaluators import LatencyEvaluator, TokenBudgetEvaluator, RetrievalRelevancyEvaluator, EvaluationEngine
from traceforge.cli import main as cli_main


def test_evaluator_unit_logic():
    """Test unit logic of LatencyEvaluator, TokenBudgetEvaluator, and RetrievalRelevancyEvaluator."""
    now = datetime.now(timezone.utc)
    trace = TraceModel(
        trace_id="test_eval_trace_001",
        name="unit_eval_trace",
        start_time=now,
        end_time=now,
        duration_ms=1500.0,
        status="OK",
        attributes={},
        spans=[
            SpanModel(
                span_id="s1",
                trace_id="test_eval_trace_001",
                parent_span_id=None,
                name="llm_span",
                span_type="llm",
                start_time=now,
                end_time=now,
                duration_ms=500.0,
                status="OK",
                attributes={"total_tokens": 500, "cost": 0.002},
            ),
            SpanModel(
                span_id="s2",
                trace_id="test_eval_trace_001",
                parent_span_id=None,
                name="retrieval_span",
                span_type="retrieval",
                start_time=now,
                end_time=now,
                duration_ms=200.0,
                status="OK",
                attributes={"top_k": 5, "documents_retrieved": 5},
            ),
        ],
    )

    # 1. Latency Check
    lat_eval = LatencyEvaluator(target_ms=3000.0)
    res_lat = lat_eval.evaluate(trace)
    assert res_lat.status == "PASS"
    assert res_lat.score == 1.0

    # 2. Token Budget Check
    tok_eval = TokenBudgetEvaluator(max_tokens=1000, max_cost=0.01)
    res_tok = tok_eval.evaluate(trace)
    assert res_tok.status == "PASS"
    assert res_tok.score == 1.0

    # 3. Retrieval Relevancy Check
    ret_eval = RetrievalRelevancyEvaluator()
    res_ret = ret_eval.evaluate(trace)
    assert res_ret.status == "PASS"
    assert res_ret.score == 1.0

    # 4. Engine Run All
    engine = EvaluationEngine()
    results = engine.run_all(trace)
    assert len(results) == 3


def test_api_evaluation_and_analytics_endpoints(client):
    """Test evaluation run, fetch evaluation, and analytics summary endpoints."""
    trace_id = "eval_api_trace_9999"
    start_time = datetime.now(timezone.utc).isoformat()

    # Ingest test trace payload
    payload = {
        "trace_id": trace_id,
        "name": "eval_test_trace",
        "start_time": start_time,
        "end_time": start_time,
        "duration_ms": 1200.0,
        "status": "OK",
        "attributes": {},
        "spans": [
            {
                "span_id": "sp_eval_1",
                "trace_id": trace_id,
                "parent_span_id": None,
                "name": "llm_call",
                "span_type": "llm",
                "start_time": start_time,
                "end_time": start_time,
                "duration_ms": 600.0,
                "status": "OK",
                "attributes": {"total_tokens": 400, "cost": 0.002},
            }
        ],
    }

    ingest_resp = client.post("/api/v1/traces", json=payload)
    assert ingest_resp.status_code == status.HTTP_201_CREATED

    # 1. Run Evaluation
    eval_req = {"target_latency_ms": 3000.0, "max_tokens": 2000, "max_cost": 0.05}
    run_resp = client.post(f"/api/v1/evaluations/run/{trace_id}", json=eval_req)
    assert run_resp.status_code == status.HTTP_200_OK
    report = run_resp.json()
    assert report["trace_id"] == trace_id
    assert report["overall_status"] in ("PASS", "WARN", "FAIL")
    assert report["total_evaluations"] == 3

    # 2. Fetch Stored Evaluation Report
    get_eval_resp = client.get(f"/api/v1/traces/{trace_id}/evaluations")
    assert get_eval_resp.status_code == status.HTTP_200_OK
    get_report = get_eval_resp.json()
    assert get_report["total_evaluations"] == 3

    # 3. Analytics Summary
    stats_resp = client.get("/api/v1/analytics/summary")
    assert stats_resp.status_code == status.HTTP_200_OK
    stats = stats_resp.json()
    assert stats["total_traces"] >= 1
    assert stats["total_spans"] >= 1
    assert "pass_rate_percent" in stats
