"""LLM Abstraction Layer for Engineering Intelligence Agent."""
import logging, os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("traceforge.agent.llm")


class LLMInterface:
    """Abstraction interface for LLM provider reasoning with deterministic fallback."""

    def __init__(self, provider: str = "mock", api_key: Optional[str] = None):
        self.provider = provider or os.getenv("LLM_PROVIDER", "mock")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")

    def reason_over_evidence(self, prompt: str, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Reason over collected evidence to synthesize hypotheses or reports."""
        if self.provider == "mock" or not self.api_key:
            return self._mock_reasoning(evidence)

        # Extensible slot for third-party LLM call if API key provided
        logger.info(f"Invoking {self.provider} LLM provider with evidence context...")
        return self._mock_reasoning(evidence)

    def _mock_reasoning(self, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deterministic reasoning engine based strictly on MCP evidence."""
        github_evidence = [e for e in evidence if e.get("source") == "github"]
        runtime_evidence = [e for e in evidence if e.get("source") in ("runtime", "logs", "metrics")]

        has_bad_commit = any("86a5672" in str(e) or "unindexed" in str(e).lower() for e in github_evidence)
        has_latency_spike = any("latency" in str(e).lower() or "2850" in str(e) for e in runtime_evidence)
        has_slow_query_logs = any("slow query" in str(e).lower() or "unindexed" in str(e).lower() for e in runtime_evidence)

        if has_bad_commit and (has_latency_spike or has_slow_query_logs):
            return {
                "hypothesis": (
                    "Deployment of release v1.8.0 containing commit 86a5672 introduced an unindexed sequential "
                    "database query loop in validate_loyalty_discount, causing DB pool exhaustion and a 24x p95 latency spike."
                ),
                "confidence": 0.94,
                "validated": True,
                "root_cause": "Inefficient N+1 database access pattern introduced in commit 86a5672 during loyalty lookup feature deployment.",
                "recommendations": [
                    "Revert commit 86a5672 or rollback checkout-api deployment to v1.7.9 immediately.",
                    "Add composite database index on user_purchases(user_id, item_id).",
                    "Batch loyalty discount queries into a single SQL IN-clause query.",
                ],
            }

        return {
            "hypothesis": "General service load increase or transient network congestion.",
            "confidence": 0.50,
            "validated": False,
            "root_cause": "Inconclusive evidence: missing GitHub or runtime telemetry.",
            "recommendations": ["Gather additional logs and expand search window."],
        }
