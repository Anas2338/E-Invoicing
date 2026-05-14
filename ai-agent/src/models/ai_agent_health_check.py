from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
from sqlalchemy import Index

from .automation_base import automation_metadata


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class AIAgentHealthCheck(SQLModel, table=True):
    """
    Model for AI Agent health check results.
    Generated every hour by the agent's health check job.
    """
    metadata = automation_metadata
    __tablename__ = "ai_agent_health_check"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Health check metadata
    check_timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    overall_status: HealthStatus = Field(index=True)

    # Invoice statistics
    pending_invoice_count: int = Field(ge=0)
    failed_invoice_count: int = Field(ge=0)
    processing_backlog: int = Field(ge=0)

    # Failure analysis
    failure_patterns: dict = Field(sa_column=Column(JSON))
    common_errors: dict = Field(sa_column=Column(JSON))

    # External service health
    fbr_api_status: str = Field(max_length=50)
    fbr_api_latency_ms: Optional[int] = Field(default=None, ge=0)
    database_status: str = Field(max_length=50)
    database_latency_ms: Optional[int] = Field(default=None, ge=0)

    # System resources
    agent_cpu_percent: Optional[float] = Field(default=None, ge=0, le=100)
    agent_memory_mb: Optional[int] = Field(default=None, ge=0)

    # Anomalies and recommendations
    anomalies_detected: list[str] = Field(default=[], sa_column=Column(JSON))
    recommended_actions: list[str] = Field(default=[], sa_column=Column(JSON))

    # Agent metadata
    agent_version: str = Field(max_length=50)
    agent_uptime_seconds: int = Field(ge=0)

    __table_args__ = (
        # Index for time-based queries
        Index(
            "idx_health_check_timestamp",
            "check_timestamp",
            postgresql_using="btree",
            postgresql_ops={"check_timestamp": "DESC"}
        ),
        # Index for status-based queries
        Index(
            "idx_health_check_status",
            "overall_status",
            "check_timestamp",
            postgresql_using="btree",
            postgresql_ops={"check_timestamp": "DESC"}
        ),
    )
