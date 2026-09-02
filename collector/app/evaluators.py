import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

from collector.app.models import TraceModel


class EvaluationResult(BaseModel):
    eval_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    trace_id: str
    eval_type: str
    score: float
    status: str  # "PASS", "FAIL", "WARN"
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LatencyEvaluator:
    """Evaluates trace latency against target SLA thresholds."""

    def __init__(self, target_ms: float = 3000.0, warn_ratio: float = 0.8):
        self.target_ms = target_ms
        self.warn_ratio = warn_ratio

    def evaluate(self, trace: TraceModel) -> EvaluationResult:
        duration_ms = trace.duration_ms or 0.0
        if duration_ms <= self.target_ms * self.warn_ratio:
            score = 1.0
            status = "PASS"
        elif duration_ms <= self.target_ms:
            score = round(1.0 - (duration_ms - (self.target_ms * self.warn_ratio)) / (self.target_ms * (1 - self.warn_ratio)), 2)
            status = "WARN"
        else:
            score = max(0.0, round(self.target_ms / duration_ms, 2))
            status = "FAIL"

        return EvaluationResult(
            trace_id=trace.trace_id,
            eval_type="latency_sla",
            score=score,
            status=status,
            details={
                "duration_ms": duration_ms,
                "target_ms": self.target_ms,
                "threshold_exceeded": duration_ms > self.target_ms,
            },
        )


class TokenBudgetEvaluator:
    """Evaluates total LLM token usage and cost bounds across all spans."""

    def __init__(self, max_tokens: int = 2000, max_cost: float = 0.05):
        self.max_tokens = max_tokens
        self.max_cost = max_cost

    def evaluate(self, trace: TraceModel) -> EvaluationResult:
        total_tokens = 0
        total_cost = 0.0
        llm_count = 0

        for span in trace.spans:
            if span.span_type == "llm":
                llm_count += 1
                attrs = span.attributes or {}
                total_tokens += int(attrs.get("total_tokens", 0))
                total_cost += float(attrs.get("cost", 0.0))

        token_ok = total_tokens <= self.max_tokens
        cost_ok = total_cost <= self.max_cost

        if token_ok and cost_ok:
            status = "PASS"
            score = 1.0
        elif token_ok or cost_ok:
            status = "WARN"
            score = 0.5
        else:
            status = "FAIL"
            score = 0.0

        return EvaluationResult(
            trace_id=trace.trace_id,
            eval_type="token_budget",
            score=score,
            status=status,
            details={
                "total_tokens": total_tokens,
                "max_tokens": self.max_tokens,
                "total_cost": round(total_cost, 6),
                "max_cost": self.max_cost,
                "llm_spans_count": llm_count,
            },
        )


class RetrievalRelevancyEvaluator:
    """Evaluates vector search top_k vs documents retrieved ratio."""

    def evaluate(self, trace: TraceModel) -> EvaluationResult:
        retrieval_spans = [s for s in trace.spans if s.span_type == "retrieval"]
        if not retrieval_spans:
            return EvaluationResult(
                trace_id=trace.trace_id,
                eval_type="retrieval_relevancy",
                score=1.0,
                status="PASS",
                details={"retrieval_spans_count": 0, "message": "No retrieval spans to evaluate"},
            )

        total_retrieved = 0
        total_top_k = 0
        for s in retrieval_spans:
            attrs = s.attributes or {}
            retrieved = int(attrs.get("documents_retrieved", 0))
            top_k = int(attrs.get("top_k", 1))
            total_retrieved += retrieved
            total_top_k += top_k

        ratio = total_retrieved / max(1, total_top_k)
        if ratio >= 0.8:
            status = "PASS"
            score = round(min(1.0, ratio), 2)
        elif ratio >= 0.5:
            status = "WARN"
            score = round(ratio, 2)
        else:
            status = "FAIL"
            score = round(ratio, 2)

        return EvaluationResult(
            trace_id=trace.trace_id,
            eval_type="retrieval_relevancy",
            score=score,
            status=status,
            details={
                "total_retrieved": total_retrieved,
                "total_top_k": total_top_k,
                "retrieval_ratio": round(ratio, 2),
            },
        )


class EvaluationEngine:
    """Orchestrates behavioral evaluations on trace executions."""

    def __init__(self, target_latency_ms: float = 3000.0, max_tokens: int = 2000, max_cost: float = 0.05):
        self.latency_evaluator = LatencyEvaluator(target_ms=target_latency_ms)
        self.token_evaluator = TokenBudgetEvaluator(max_tokens=max_tokens, max_cost=max_cost)
        self.retrieval_evaluator = RetrievalRelevancyEvaluator()

    def run_all(self, trace: TraceModel) -> list[EvaluationResult]:
        return [
            self.latency_evaluator.evaluate(trace),
            self.token_evaluator.evaluate(trace),
            self.retrieval_evaluator.evaluate(trace),
        ]
