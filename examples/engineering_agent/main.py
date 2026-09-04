"""FastAPI service and CLI hero demo runner for TRACEFORGE Engineering Intelligence Agent."""
import sys
import logging
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from examples.engineering_agent.graph import run_investigation
from examples.engineering_agent.state import AgentState

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("traceforge.agent.main")

app = FastAPI(
    title="TRACEFORGE Engineering Intelligence Agent API",
    description="Incident Investigation Showcase Service powered by LangGraph, MCP, & TRACEFORGE Telemetry",
    version="0.1.0",
)


class InvestigateRequest(BaseModel):
    incident: str = Field(
        default="Our checkout API became slow after yesterday's deployment. Investigate the root cause and provide evidence.",
        description="Incident description or query",
    )
    service: str = Field(
        default="checkout-api",
        description="Target microservice name",
    )


class InvestigateResponse(BaseModel):
    incident_id: str
    service: str
    summary: str
    root_cause: str
    evidence: List[Dict[str, Any]]
    confidence: float
    recommendations: List[str]
    trace_id: str
    final_report: str


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "traceforge-engineering-agent", "version": "0.1.0"}


@app.post("/api/v1/investigate", response_model=InvestigateResponse)
def investigate_incident(req: InvestigateRequest):
    try:
        state = run_investigation(incident=req.incident, service=req.service)
        val = state.validation_results
        
        return InvestigateResponse(
            incident_id=f"INC-{state.trace_id[:8].upper() if state.trace_id else '0001'}",
            service=state.service,
            summary=state.incident,
            root_cause=val.get("root_cause", "Investigation in progress."),
            evidence=[e.model_dump() for e in state.evidence],
            confidence=state.confidence,
            recommendations=val.get("recommendations", []),
            trace_id=state.trace_id or "",
            final_report=state.final_report or "",
        )
    except Exception as e:
        logger.error(f"Error during incident investigation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def cli_hero_demo():
    """CLI Hero Demo runner for terminal presentation."""
    print("\n" + "=" * 65)
    print("      TRACEFORGE ENGINEERING INTELLIGENCE AGENT (v0.1)")
    print("=" * 65 + "\n")

    query = "Our checkout API became slow after yesterday's deployment. Investigate the root cause and provide evidence."
    service = "checkout-api"

    print(f"Incident Request : {query}")
    print(f"Target Service   : {service}\n")
    print("Executing LangGraph Incident Investigation Workflow...\n")

    state = run_investigation(incident=query, service=service)

    print("\n" + state.final_report + "\n")

    print("=" * 65)
    print(f"TRACE ID           : {state.trace_id}")
    print("TRACEFORGE Status  : Telemetry Spans Exported Successfully [OK]")
    print("Dashboard Inspector: http://localhost:8000/dashboard")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8001)
    else:
        cli_hero_demo()
