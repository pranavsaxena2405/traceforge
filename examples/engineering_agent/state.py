"""State schema for LangGraph Engineering Intelligence Agent workflow."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    source: str  # "github", "runtime", "logs", "metrics"
    tool_used: str
    summary: str
    details: Dict[str, Any]
    severity: str = "medium"


class AgentState(BaseModel):
    """Pydantic state object used in LangGraph state graph transitions."""

    incident: str = Field(description="Incident description or query from user")
    service: str = Field(default="checkout-api", description="Target microservice name")
    findings: Dict[str, Any] = Field(default_factory=dict, description="Categorized findings")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Collected structured evidence")
    hypotheses: List[str] = Field(default_factory=list, description="Candidate root cause hypotheses")
    selected_hypothesis: Optional[str] = Field(default=None, description="Hypothesis selected for validation")
    validation_results: Dict[str, Any] = Field(default_factory=dict, description="Validation evidence & outcome")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="Log of executed MCP tools")
    errors: List[str] = Field(default_factory=list, description="Encountered errors or retries")
    final_report: Optional[str] = Field(default=None, description="Generated Root Cause Analysis report")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score of RCA")
    trace_id: Optional[str] = Field(default=None, description="TRACEFORGE Trace ID")
    is_validated: bool = Field(default=False, description="Flag indicating hypothesis validation status")
    retry_count: int = Field(default=0, description="Number of investigation retry iterations")
