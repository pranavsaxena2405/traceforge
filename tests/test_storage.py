from datetime import datetime, timezone
from collector.app.models import SpanModel, TraceModel


def test_storage_trace_and_span_persistence(db_session):
    """Test persistence of TraceModel and SpanModel directly via SQLAlchemy session."""
    trace_id = "00000000000000000000000000000001"
    span_id = "0000000000000001"
    now = datetime.now(timezone.utc)

    trace = TraceModel(
        trace_id=trace_id,
        name="storage_test_agent",
        start_time=now,
        end_time=now,
        duration_ms=50.0,
        status="OK",
        attributes={"user_id": "test_user"},
    )
    span = SpanModel(
        span_id=span_id,
        trace_id=trace_id,
        parent_span_id=None,
        name="storage_span",
        span_type="llm",
        start_time=now,
        end_time=now,
        duration_ms=50.0,
        status="OK",
        attributes={"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50},
    )

    db_session.add(trace)
    db_session.add(span)
    db_session.commit()

    # Query back
    saved_trace = db_session.query(TraceModel).filter_by(trace_id=trace_id).first()
    assert saved_trace is not None
    assert saved_trace.name == "storage_test_agent"
    assert len(saved_trace.spans) == 1
    assert saved_trace.spans[0].span_id == span_id
    assert saved_trace.spans[0].attributes["model"] == "gpt-4o"
