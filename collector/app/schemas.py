from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class SpanBase(BaseModel):
    span_id: str = Field(..., description="Unique 16-character hex span identifier")
    trace_id: str = Field(..., description="Unique 32-character hex trace identifier")
    parent_span_id: Optional[str] = Field(None, description="Parent span identifier if child span")
    name: str = Field(..., description="Name of operation")
    span_type: str = Field(
        "agent",
        description="Type of span: agent, llm, retrieval, tool, mcp, database, http",
    )
    start_time: datetime = Field(..., description="UTC start timestamp")
    end_time: datetime = Field(..., description="UTC end timestamp")
    duration_ms: float = Field(..., description="Duration in milliseconds")
    status: str = Field("OK", description="Execution status: OK, ERROR, UNSET")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Metadata attributes")


class SpanCreate(SpanBase):
    pass


class SpanResponse(SpanBase):
    model_config = {"from_attributes": True}


class TraceIngestRequest(BaseModel):
    trace_id: str = Field(..., description="Unique 32-character hex trace identifier")
    name: str = Field(..., description="Root span / trace operation name")
    start_time: datetime = Field(..., description="UTC start timestamp")
    end_time: Optional[datetime] = Field(None, description="UTC end timestamp")
    duration_ms: Optional[float] = Field(None, description="Duration in milliseconds")
    status: str = Field("OK", description="Execution status: OK, ERROR, UNSET")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Metadata attributes")
    spans: list[SpanCreate] = Field(default_factory=list, description="Nested spans in this trace")


class TraceResponse(BaseModel):
    trace_id: str
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    spans: list[SpanResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TraceListResponse(BaseModel):
    total: int = Field(..., description="Total count of recorded traces")
    limit: int = Field(..., description="Pagination limit")
    offset: int = Field(..., description="Pagination offset")
    items: list[TraceResponse] = Field(default_factory=list, description="List of trace summaries")


class HealthResponse(BaseModel):
    status: str = "ok"
    database: str = "ok"


class EvaluationResponse(BaseModel):
    eval_id: str
    trace_id: str
    eval_type: str
    score: float
    status: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class EvaluationRunRequest(BaseModel):
    target_latency_ms: Optional[float] = Field(3000.0, description="Target SLA latency threshold in ms")
    max_tokens: Optional[int] = Field(2000, description="Maximum total tokens allowed")
    max_cost: Optional[float] = Field(0.05, description="Maximum total LLM cost allowed in USD")


class EvaluationReportResponse(BaseModel):
    trace_id: str
    total_evaluations: int
    overall_status: str
    evaluations: list[EvaluationResponse] = Field(default_factory=list)


class AnalyticsSummaryResponse(BaseModel):
    total_traces: int
    total_spans: int
    passed_evaluations: int
    failed_evaluations: int
    pass_rate_percent: float
    total_tokens: int
    total_cost_usd: float
    p50_duration_ms: float
    p90_duration_ms: float
    p99_duration_ms: float


