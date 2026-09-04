import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from collector.app.db import check_db_health, get_db, init_db
from collector.app.evaluators import EvaluationEngine
from collector.app.models import EvaluationModel, SpanModel, TraceModel
from collector.app.schemas import (
    AnalyticsSummaryResponse,
    EvaluationReportResponse,
    EvaluationResponse,
    EvaluationRunRequest,
    HealthResponse,
    TraceIngestRequest,
    TraceListResponse,
    TraceResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("traceforge.collector")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for table initialization."""
    try:
        init_db()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning(f"Could not initialize DB on startup: {e}")
    yield



app = FastAPI(
    title="TRACEFORGE Collector & REST API",
    version="0.1.0",
    description="Telemetry collector and REST API for TRACEFORGE AI observability platform",
    lifespan=lifespan,
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
def serve_dashboard():
    """Serve TRACEFORGE Visual Web Dashboard."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "TRACEFORGE Collector Active"}



@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    db_ok = check_db_health()
    return HealthResponse(
        status="ok",
        database="ok" if db_ok else "unavailable",
    )


@app.post(
    "/api/v1/traces",
    response_model=TraceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Traces"],
)
def ingest_trace(
    payload: TraceIngestRequest,
    db: Session = Depends(get_db),
) -> TraceResponse:
    """Ingest trace and span telemetry payload safely and idempotently."""
    try:
        try:
            init_db()
        except Exception:
            pass
        # Idempotent Upsert for Trace
        existing_trace = db.query(TraceModel).filter_by(trace_id=payload.trace_id).first()
        if existing_trace:
            existing_trace.name = payload.name
            existing_trace.start_time = payload.start_time
            existing_trace.end_time = payload.end_time
            existing_trace.duration_ms = payload.duration_ms
            existing_trace.status = payload.status
            existing_trace.attributes = {**existing_trace.attributes, **payload.attributes}
            trace_record = existing_trace
        else:
            trace_record = TraceModel(
                trace_id=payload.trace_id,
                name=payload.name,
                start_time=payload.start_time,
                end_time=payload.end_time,
                duration_ms=payload.duration_ms,
                status=payload.status,
                attributes=payload.attributes,
            )
            db.add(trace_record)

        # Idempotent Upsert for Spans
        for span_data in payload.spans:
            existing_span = db.query(SpanModel).filter_by(span_id=span_data.span_id).first()
            if existing_span:
                existing_span.trace_id = payload.trace_id
                existing_span.parent_span_id = span_data.parent_span_id
                existing_span.name = span_data.name
                existing_span.span_type = span_data.span_type
                existing_span.start_time = span_data.start_time
                existing_span.end_time = span_data.end_time
                existing_span.duration_ms = span_data.duration_ms
                existing_span.status = span_data.status
                existing_span.attributes = {**existing_span.attributes, **span_data.attributes}
            else:
                span_record = SpanModel(
                    span_id=span_data.span_id,
                    trace_id=payload.trace_id,
                    parent_span_id=span_data.parent_span_id,
                    name=span_data.name,
                    span_type=span_data.span_type,
                    start_time=span_data.start_time,
                    end_time=span_data.end_time,
                    duration_ms=span_data.duration_ms,
                    status=span_data.status,
                    attributes=span_data.attributes,
                )
                db.add(span_record)

        db.commit()
        db.refresh(trace_record)
        return TraceResponse.model_validate(trace_record)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to ingest trace {payload.trace_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trace ingestion failed: {str(e)}",
        )


@app.get(
    "/api/v1/traces/{trace_id}",
    response_model=TraceResponse,
    tags=["Traces"],
)
def get_trace(
    trace_id: str,
    db: Session = Depends(get_db),
) -> TraceResponse:
    """Retrieve complete trace and nested spans by trace_id."""
    trace_record = db.query(TraceModel).filter_by(trace_id=trace_id).first()
    if not trace_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace with ID '{trace_id}' not found.",
        )
    return TraceResponse.model_validate(trace_record)


@app.get(
    "/api/v1/traces",
    response_model=TraceListResponse,
    tags=["Traces"],
)
def list_traces(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of traces to return"),
    offset: int = Query(0, ge=0, description="Number of traces to skip"),
    db: Session = Depends(get_db),
) -> TraceListResponse:
    """List stored traces with pagination."""
    total = db.query(TraceModel).count()
    traces = (
        db.query(TraceModel)
        .order_by(TraceModel.start_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = [TraceResponse.model_validate(t) for t in traces]
    return TraceListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@app.post(
    "/api/v1/evaluations/run/{trace_id}",
    response_model=EvaluationReportResponse,
    status_code=status.HTTP_200_OK,
    tags=["Evaluations"],
)
def run_evaluations(
    trace_id: str,
    req: EvaluationRunRequest = EvaluationRunRequest(),
    db: Session = Depends(get_db),
) -> EvaluationReportResponse:
    """Run automated behavioral evaluation suite against a target trace."""
    trace_record = db.query(TraceModel).filter_by(trace_id=trace_id).first()
    if not trace_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace with ID '{trace_id}' not found.",
        )

    engine = EvaluationEngine(
        target_latency_ms=req.target_latency_ms or 3000.0,
        max_tokens=req.max_tokens or 2000,
        max_cost=req.max_cost or 0.05,
    )
    results = engine.run_all(trace_record)

    db_evals = []
    for r in results:
        existing = (
            db.query(EvaluationModel)
            .filter_by(trace_id=trace_id, eval_type=r.eval_type)
            .first()
        )
        if existing:
            existing.score = r.score
            existing.status = r.status
            existing.details = r.details
            existing.created_at = r.created_at
            db_evals.append(existing)
        else:
            new_eval = EvaluationModel(
                eval_id=r.eval_id,
                trace_id=r.trace_id,
                eval_type=r.eval_type,
                score=r.score,
                status=r.status,
                details=r.details,
                created_at=r.created_at,
            )
            db.add(new_eval)
            db_evals.append(new_eval)

    db.commit()
    for e in db_evals:
        db.refresh(e)

    overall = (
        "FAIL"
        if any(e.status == "FAIL" for e in db_evals)
        else ("WARN" if any(e.status == "WARN" for e in db_evals) else "PASS")
    )

    return EvaluationReportResponse(
        trace_id=trace_id,
        total_evaluations=len(db_evals),
        overall_status=overall,
        evaluations=[EvaluationResponse.model_validate(e) for e in db_evals],
    )


@app.get(
    "/api/v1/traces/{trace_id}/evaluations",
    response_model=EvaluationReportResponse,
    tags=["Evaluations"],
)
def get_trace_evaluations(
    trace_id: str,
    db: Session = Depends(get_db),
) -> EvaluationReportResponse:
    """Fetch stored evaluation report for a trace."""
    trace_record = db.query(TraceModel).filter_by(trace_id=trace_id).first()
    if not trace_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace with ID '{trace_id}' not found.",
        )

    db_evals = db.query(EvaluationModel).filter_by(trace_id=trace_id).all()
    overall = (
        "FAIL"
        if any(e.status == "FAIL" for e in db_evals)
        else ("WARN" if any(e.status == "WARN" for e in db_evals) else ("PASS" if db_evals else "UNEVALUATED"))
    )

    return EvaluationReportResponse(
        trace_id=trace_id,
        total_evaluations=len(db_evals),
        overall_status=overall,
        evaluations=[EvaluationResponse.model_validate(e) for e in db_evals],
    )


@app.get(
    "/api/v1/analytics/summary",
    response_model=AnalyticsSummaryResponse,
    tags=["Analytics"],
)
def get_analytics_summary(
    db: Session = Depends(get_db),
) -> AnalyticsSummaryResponse:
    """Get aggregated trace analytics, token economics, and latency SLA percentiles."""
    traces = db.query(TraceModel).all()
    total_traces = len(traces)
    total_spans = db.query(SpanModel).count()

    evals = db.query(EvaluationModel).all()
    passed_evals = sum(1 for e in evals if e.status == "PASS")
    failed_evals = sum(1 for e in evals if e.status == "FAIL")
    total_evals = len(evals)
    pass_rate = round((passed_evals / max(1, total_evals)) * 100.0, 2) if total_evals > 0 else 100.0

    total_tokens = 0
    total_cost = 0.0
    durations = []

    for t in traces:
        if t.duration_ms is not None:
            durations.append(t.duration_ms)
        for s in t.spans:
            if s.span_type == "llm":
                attrs = s.attributes or {}
                total_tokens += int(attrs.get("total_tokens", 0))
                total_cost += float(attrs.get("cost", 0.0))

    durations.sort()
    n = len(durations)
    p50 = round(durations[int(n * 0.5)] if n > 0 else 0.0, 2)
    p90 = round(durations[int(n * 0.9)] if n > 0 else 0.0, 2)
    p99 = round(durations[int(n * 0.99)] if n > 0 else 0.0, 2)

    return AnalyticsSummaryResponse(
        total_traces=total_traces,
        total_spans=total_spans,
        passed_evaluations=passed_evals,
        failed_evaluations=failed_evals,
        pass_rate_percent=pass_rate,
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost, 6),
        p50_duration_ms=p50,
        p90_duration_ms=p90,
        p99_duration_ms=p99,
    )


