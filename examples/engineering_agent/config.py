"""Configuration settings for TRACEFORGE Engineering Intelligence Agent."""
import os
from pydantic import BaseModel


class AgentConfig(BaseModel):
    collector_url: str = os.getenv("TRACEFORGE_COLLECTOR_URL", "http://localhost:8000")
    agent_name: str = "TRACEFORGE Engineering Intelligence Agent"
    default_service: str = "checkout-api"
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")


config = AgentConfig()
