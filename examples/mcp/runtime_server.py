"""Operations & Runtime MCP Server providing microservice health, logs, deployment status, and metrics."""
import logging
from typing import Any, Dict, List
from pydantic import BaseModel

logger = logging.getLogger("traceforge.mcp.runtime")


class ServiceHealth(BaseModel):
    service_name: str
    status: str  # "degraded", "healthy", "down"
    p95_latency_ms: float
    error_rate_percent: float
    active_instances: int


class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    trace_context: Dict[str, str]


class DeploymentStatus(BaseModel):
    service_name: str
    current_version: str
    previous_version: str
    deployed_at: str
    deployed_by: str
    status: str  # "completed", "failed", "in_progress"


class ServiceMetric(BaseModel):
    service_name: str
    metric: str
    window: str
    timestamps: List[str]
    values: List[float]
    unit: str


class RuntimeMCPServer:
    """Deterministic Runtime Operations MCP Server for incident investigation."""

    def __init__(self):
        self._services = ["checkout-api", "payment-gateway", "inventory-service", "user-auth"]

    def list_services(self) -> List[str]:
        """Expose list_services tool."""
        return self._services

    def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """Expose get_service_health tool."""
        if service_name not in self._services:
            raise ValueError(f"Service '{service_name}' does not exist in runtime registry.")
        
        if service_name == "checkout-api":
            return ServiceHealth(
                service_name="checkout-api",
                status="degraded",
                p95_latency_ms=2850.0,  # Spiked from 120ms to 2850ms
                error_rate_percent=4.8,  # Increased from 0.01%
                active_instances=4,
            ).model_dump()
        
        return ServiceHealth(
            service_name=service_name,
            status="healthy",
            p95_latency_ms=85.0,
            error_rate_percent=0.0,
            active_instances=2,
        ).model_dump()

    def get_recent_logs(self, service_name: str, minutes: int = 30) -> List[Dict[str, Any]]:
        """Expose get_recent_logs tool."""
        if service_name == "checkout-api":
            return [
                LogEntry(
                    timestamp="2026-09-03T15:05:12Z",
                    level="WARN",
                    message="Slow query detected in validate_loyalty_discount: query execution took 2450ms across 42 sub-queries",
                    trace_context={"trace_id": "a1b2c3d4e5f60001", "span_id": "0001"},
                ).model_dump(),
                LogEntry(
                    timestamp="2026-09-03T15:08:45Z",
                    level="ERROR",
                    message="HTTP 504 Gateway Timeout: database connection pool exhausted waiting for loyalty lookup response",
                    trace_context={"trace_id": "a1b2c3d4e5f60002", "span_id": "0002"},
                ).model_dump(),
                LogEntry(
                    timestamp="2026-09-03T15:12:00Z",
                    level="INFO",
                    message="Service checkout-api handling 85 requests/sec with average duration 2610ms",
                    trace_context={"trace_id": "a1b2c3d4e5f60003", "span_id": "0003"},
                ).model_dump(),
            ]
        return []

    def get_deployment_status(self, service_name: str) -> Dict[str, Any]:
        """Expose get_deployment_status tool."""
        if service_name == "checkout-api":
            return DeploymentStatus(
                service_name="checkout-api",
                current_version="v1.8.0",
                previous_version="v1.7.9",
                deployed_at="2026-09-03T14:45:00Z",
                deployed_by="alex.dev@acmecorp.com",
                status="completed",
            ).model_dump()
        
        return DeploymentStatus(
            service_name=service_name,
            current_version="v2.1.0",
            previous_version="v2.0.4",
            deployed_at="2026-08-28T09:00:00Z",
            deployed_by="ci-cd-bot",
            status="completed",
        ).model_dump()

    def get_service_metrics(self, service_name: str, metric: str = "latency", window: str = "1h") -> Dict[str, Any]:
        """Expose get_service_metrics tool."""
        if service_name == "checkout-api":
            if metric == "latency":
                return ServiceMetric(
                    service_name="checkout-api",
                    metric="latency_p95",
                    window=window,
                    timestamps=["14:00", "14:30", "15:00", "15:30", "16:00"],
                    values=[115.0, 120.0, 2450.0, 2850.0, 2790.0],
                    unit="ms",
                ).model_dump()
            elif metric in ("db_queries", "queries"):
                return ServiceMetric(
                    service_name="checkout-api",
                    metric="db_queries_per_req",
                    window=window,
                    timestamps=["14:00", "14:30", "15:00", "15:30", "16:00"],
                    values=[2.0, 2.0, 44.0, 48.0, 45.0],
                    unit="queries/req",
                ).model_dump()
        
        return ServiceMetric(
            service_name=service_name,
            metric=metric,
            window=window,
            timestamps=["14:00", "14:30", "15:00", "15:30", "16:00"],
            values=[85.0, 85.0, 84.0, 86.0, 85.0],
            unit="ms",
        ).model_dump()
