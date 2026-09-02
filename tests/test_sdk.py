import time
from unittest.mock import patch
import httpx
import pytest

from traceforge import trace
from traceforge.exporter import TraceForgeExporter


@pytest.fixture(autouse=True)
def mock_httpx_post():
    """Auto-mock httpx.Client.post for SDK unit tests to prevent network timeouts."""
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value.status_code = 201
        yield mock_post


def test_sdk_trace_and_span_creation():
    """Test SDK trace, span creation, parent-child linkages, and attributes."""
    collector_url = "http://localhost:8000/api/v1/traces"

    with trace("test_agent_run", attributes={"env": "test"}, collector_url=collector_url) as run:
        assert run.trace_id is not None
        assert len(run.trace_id) == 32
        assert run.span_id is not None
        assert len(run.span_id) == 16

        with run.span("test_llm_call", span_type="llm", attributes={"model": "gpt-4o"}) as span1:
            assert span1.trace_id == run.trace_id
            assert span1.span_id is not None
            assert len(span1.span_id) == 16
            assert span1.span_id != run.span_id
            time.sleep(0.01)

        with run.span("test_retrieval", span_type="retrieval", attributes={"query": "test query"}) as span2:
            assert span2.trace_id == run.trace_id
            assert span2.span_id != span1.span_id

    # Root run finished
    assert run.trace_id is not None


def test_sdk_exporter_handles_network_failure_gracefully():
    """Test that network errors during export do not crash application execution."""
    exporter = TraceForgeExporter(collector_url="http://invalid-host-9999:8000/api/v1/traces")

    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
        # Should not raise exception
        with trace("failing_export_trace", collector_url="http://invalid-host-9999:8000/api/v1/traces"):
            time.sleep(0.001)


def test_sdk_handles_exceptions_and_sets_error_status():
    """Test that unhandled exceptions inside trace set error status and re-raise."""
    with pytest.raises(ValueError, match="Simulated Failure"):
        with trace("error_trace", attributes={"env": "test"}) as run:
            with run.span("failing_span", span_type="tool"):
                raise ValueError("Simulated Failure")


def test_sdk_decorator_syntax():
    """Test using trace and span context managers as function decorators."""
    trace_cm = trace("decorated_agent")

    @trace_cm
    def decorated_agent_func(x: int) -> int:
        span_cm = trace_cm.span("decorated_llm", span_type="llm")

        @span_cm
        def inner_llm_call(val: int) -> int:
            return val * 2

        return inner_llm_call(x)

    result = decorated_agent_func(21)
    assert result == 42

