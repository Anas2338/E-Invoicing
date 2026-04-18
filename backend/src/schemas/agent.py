"""
Agent status schemas for AI Agent monitoring endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class AIAgentHealthCheckResponse(BaseModel):
    """Response model for AI Agent health check."""

    id: UUID
    check_timestamp: datetime
    overall_status: str

    # Invoice statistics
    pending_invoice_count: int
    failed_invoice_count: int
    processing_backlog: int

    # Failure analysis
    failure_patterns: dict
    common_errors: dict

    # External service health
    fbr_api_status: str
    fbr_api_latency_ms: Optional[int]
    database_status: str
    database_latency_ms: Optional[int]

    # System resources
    agent_cpu_percent: Optional[float]
    agent_memory_mb: Optional[int]

    # Anomalies and recommendations
    anomalies_detected: List[str]
    recommended_actions: List[str]

    # Agent metadata
    agent_version: str
    agent_uptime_seconds: int

    class Config:
        from_attributes = True


class AIAgentDecisionLog(BaseModel):
    """Response model for AI Agent decision log entry."""

    id: UUID
    automation_invoice_id: UUID
    action: str
    status: str
    details: dict
    timestamp: datetime

    class Config:
        from_attributes = True


class AIAgentDecisionListResponse(BaseModel):
    """Response model for paginated AI Agent decision list."""

    decisions: List[AIAgentDecisionLog]
    total: int
    page: int
    page_size: int
    total_pages: int


class AIAgentStatusSummary(BaseModel):
    """Summary of AI Agent current status."""

    is_running: bool
    last_health_check: Optional[datetime]
    overall_status: Optional[str]
    pending_invoices: int
    failed_invoices: int
    processing_backlog: int
    anomalies_count: int
    agent_version: str
    agent_uptime_seconds: int
