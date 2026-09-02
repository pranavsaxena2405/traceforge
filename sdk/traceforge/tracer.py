import functools
from contextlib import AbstractContextManager
import logging
from typing import Any, Optional, Generator
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.trace import Status, StatusCode, Tracer

from traceforge.exporter import TraceForgeExporter

logger = logging.getLogger("traceforge.sdk.tracer")

_TRACER_PROVIDER: Optional[TracerProvider] = None
_EXPORTER: Optional[TraceForgeExporter] = None


def get_tracer(collector_url: Optional[str] = None) -> Tracer:
    """Retrieve or initialize the global OpenTelemetry Tracer configured with TRACEFORGE Exporter."""
    global _TRACER_PROVIDER, _EXPORTER
    if _TRACER_PROVIDER is None:
        _TRACER_PROVIDER = TracerProvider()
        _EXPORTER = TraceForgeExporter(collector_url=collector_url)
        _TRACER_PROVIDER.add_span_processor(SimpleSpanProcessor(_EXPORTER))
        otel_trace.set_tracer_provider(_TRACER_PROVIDER)
    return otel_trace.get_tracer("traceforge", "0.1.0")


class SpanContext(AbstractContextManager):
    """Context manager and function decorator wrapping an OpenTelemetry span execution."""

    def __init__(
        self,
        tracer: Tracer,
        name: str,
        span_type: str = "agent",
        attributes: Optional[dict[str, Any]] = None,
    ):
        self.tracer = tracer
        self.name = name
        self.span_type = span_type
        self.attributes = attributes or {}
        self._otel_span_cm = None
        self.span = None
        self.trace_id: Optional[str] = None
        self.span_id: Optional[str] = None

    def __enter__(self):
        # Attach span_type to OTel attributes
        all_attrs = {**self.attributes, "traceforge.span_type": self.span_type}
        self._otel_span_cm = self.tracer.start_as_current_span(
            self.name, attributes=all_attrs
        )
        self.span = self._otel_span_cm.__enter__()
        ctx = self.span.get_span_context()
        self.trace_id = f"{ctx.trace_id:032x}"
        self.span_id = f"{ctx.span_id:016x}"
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            self.span.record_exception(exc_val)
        else:
            self.span.set_status(Status(StatusCode.OK))
        return self._otel_span_cm.__exit__(exc_type, exc_val, exc_tb)

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper


class TraceContext(AbstractContextManager):
    """Context manager and function decorator representing a top-level TRACEFORGE Trace execution."""

    def __init__(
        self,
        name: str,
        attributes: Optional[dict[str, Any]] = None,
        collector_url: Optional[str] = None,
    ):
        self.name = name
        self.attributes = attributes or {}
        self.tracer = get_tracer(collector_url=collector_url)
        self._root_span_cm = None
        self.root_span = None
        self.trace_id: Optional[str] = None
        self.span_id: Optional[str] = None

    def __enter__(self):
        all_attrs = {**self.attributes, "traceforge.span_type": "agent"}
        self._root_span_cm = self.tracer.start_as_current_span(
            self.name, attributes=all_attrs
        )
        self.root_span = self._root_span_cm.__enter__()
        ctx = self.root_span.get_span_context()
        self.trace_id = f"{ctx.trace_id:032x}"
        self.span_id = f"{ctx.span_id:016x}"
        return self

    def span(
        self,
        name: str,
        span_type: str = "agent",
        attributes: Optional[dict[str, Any]] = None,
    ) -> SpanContext:
        """Create a child span within this trace context."""
        return SpanContext(
            tracer=self.tracer,
            name=name,
            span_type=span_type,
            attributes=attributes,
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.root_span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            self.root_span.record_exception(exc_val)
        else:
            self.root_span.set_status(Status(StatusCode.OK))
        return self._root_span_cm.__exit__(exc_type, exc_val, exc_tb)

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper


def trace(
    name: str,
    attributes: Optional[dict[str, Any]] = None,
    collector_url: Optional[str] = None,
) -> TraceContext:
    """Public SDK entrypoint for tracing an agent execution."""
    return TraceContext(name=name, attributes=attributes, collector_url=collector_url)

