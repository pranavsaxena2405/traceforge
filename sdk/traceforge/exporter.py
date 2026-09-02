import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional, Sequence
import httpx
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

logger = logging.getLogger("traceforge.sdk.exporter")


class TraceForgeExporter(SpanExporter):
    """OpenTelemetry SpanExporter that sends formatted trace payloads to TRACEFORGE Collector."""

    def __init__(self, collector_url: Optional[str] = None, timeout: float = 5.0):
        self.collector_url = (
            collector_url
            or os.getenv("TRACEFORGE_COLLECTOR_URL")
            or "http://localhost:8000/api/v1/traces"
        )
        self.timeout = timeout
        self._client = httpx.Client(timeout=self.timeout)

    def _to_hex_trace_id(self, trace_id_int: int) -> str:
        return f"{trace_id_int:032x}"

    def _to_hex_span_id(self, span_id_int: Optional[int]) -> Optional[str]:
        if not span_id_int or span_id_int == 0:
            return None
        return f"{span_id_int:016x}"

    def _ns_to_datetime_str(self, timestamp_ns: int) -> str:
        dt = datetime.fromtimestamp(timestamp_ns / 1e9, tz=timezone.utc)
        return dt.isoformat()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export completed OpenTelemetry readable spans to TRACEFORGE Collector API."""
        if not spans:
            return SpanExportResult.SUCCESS

        # Group spans by trace_id
        traces_map: dict[str, list[ReadableSpan]] = {}
        for span in spans:
            trace_id_hex = self._to_hex_trace_id(span.context.trace_id)
            if trace_id_hex not in traces_map:
                traces_map[trace_id_hex] = []
            traces_map[trace_id_hex].append(span)

        for trace_id_hex, trace_spans in traces_map.items():
            # Find root span (span with no parent or parent span_id == 0)
            root_span = next(
                (s for s in trace_spans if not s.parent or s.parent.span_id == 0),
                trace_spans[0],
            )

            # Format trace attributes
            trace_attrs = dict(root_span.attributes or {})
            trace_status = (
                "ERROR"
                if any(s.status.status_code.name == "ERROR" for s in trace_spans)
                else "OK"
            )

            span_payloads: list[dict[str, Any]] = []
            for s in trace_spans:
                s_attrs = dict(s.attributes or {})
                span_type = str(s_attrs.pop("traceforge.span_type", "agent"))
                parent_id = self._to_hex_span_id(s.parent.span_id if s.parent else None)

                start_dt_str = self._ns_to_datetime_str(s.start_time)
                end_dt_str = self._ns_to_datetime_str(s.end_time)
                duration_ms = round((s.end_time - s.start_time) / 1e6, 3)

                span_payloads.append(
                    {
                        "span_id": self._to_hex_span_id(s.context.span_id),
                        "trace_id": trace_id_hex,
                        "parent_span_id": parent_id,
                        "name": s.name,
                        "span_type": span_type,
                        "start_time": start_dt_str,
                        "end_time": end_dt_str,
                        "duration_ms": duration_ms,
                        "status": s.status.status_code.name if s.status.status_code.name != "UNSET" else "OK",
                        "attributes": s_attrs,
                    }
                )

            start_dt_str = self._ns_to_datetime_str(root_span.start_time)
            end_dt_str = self._ns_to_datetime_str(
                max(s.end_time for s in trace_spans)
            )
            total_duration_ms = round(
                (max(s.end_time for s in trace_spans) - root_span.start_time) / 1e6, 3
            )

            payload = {
                "trace_id": trace_id_hex,
                "name": root_span.name,
                "start_time": start_dt_str,
                "end_time": end_dt_str,
                "duration_ms": total_duration_ms,
                "status": trace_status,
                "attributes": trace_attrs,
                "spans": span_payloads,
            }

            try:
                response = self._client.post(self.collector_url, json=payload)
                if response.status_code not in (200, 201):
                    logger.warning(
                        f"TRACEFORGE Collector returned HTTP {response.status_code}: {response.text}"
                    )
            except Exception as exc:
                # Graceful handling of network / exporter failure
                logger.warning(
                    f"TRACEFORGE Exporter failed to send trace {trace_id_hex} to {self.collector_url}: {exc}"
                )

        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        self._client.close()
