from sqlalchemy import Column, Integer, String, DateTime, Text, Float, JSON
from datetime import datetime, timezone
from app.database import Base


class Failure(Base):
    __tablename__ = "failures"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    service_name     = Column(String(100), nullable=False, index=True)
    endpoint         = Column(String(255), nullable=False)
    http_method      = Column(String(10), default="GET")
    status_code      = Column(Integer, default=500)
    error_type       = Column(String(100), nullable=False, index=True)
    error_message    = Column(Text, nullable=False)
    stack_trace      = Column(Text, nullable=True)
    request_metadata = Column(JSON, nullable=True)
    environment      = Column(String(50), default="production")
    timestamp        = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # ── Distributed tracing columns ──────────────────────
    trace_id         = Column(String(100), nullable=True, index=True)
    # One trace_id ties order→inventory→payment together

    correlation_id   = Column(String(100), nullable=True, index=True)
    # Business identifier — order_id, user_id, session_id etc

    span_id          = Column(String(100), nullable=True)
    # Identifies this specific service call within the trace

    parent_span_id   = Column(String(100), nullable=True)
    # Which service called this one

class Insight(Base):
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(100), nullable=False)
    error_type = Column(String(100), nullable=False)
    failure_count = Column(Integer, nullable=False)
    root_cause = Column(Text, nullable=False)
    risk_level = Column(String(20), nullable=False)
    risk_summary = Column(Text, nullable=False)
    recommended_fixes = Column(JSON, nullable=False)
    remediation_actions = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False)
    graph_trace = Column(JSON, nullable=True)   # LangGraph execution steps
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    failure_ids = Column(JSON, nullable=False)
