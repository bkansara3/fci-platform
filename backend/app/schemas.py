from pydantic import BaseModel
from datetime import datetime
from typing import Any


class FailureOut(BaseModel):
    id:               int
    service_name:     str
    endpoint:         str
    http_method:      str
    status_code:      int
    error_type:       str
    error_message:    str
    stack_trace:      str | None
    request_metadata: dict | None
    environment:      str
    timestamp:        datetime

    # ── Tracing ──
    trace_id:       str | None
    correlation_id: str | None
    span_id:        str | None
    parent_span_id: str | None

    model_config = {"from_attributes": True}


class PaginatedFailures(BaseModel):
    items: list[FailureOut]
    total: int
    page: int
    page_size: int


class AnalyticsResponse(BaseModel):
    total_failures: int
    failures_last_hour: int
    top_services: list[dict]
    top_error_types: list[dict]
    time_series: list[dict]
    heatmap: list[dict]


class InsightOut(BaseModel):
    id: int
    service_name: str
    error_type: str
    failure_count: int
    root_cause: str
    risk_level: str
    risk_summary: str
    recommended_fixes: list[str]
    remediation_actions: list[str]
    confidence: float
    graph_trace: list[dict] | None
    generated_at: datetime
    failure_ids: list[int]

    model_config = {"from_attributes": True}


class InsightRequest(BaseModel):
    # Make all fields optional so the frontend can send EITHER a trace_id OR service/error
    service_name: str | None = None
    error_type: str | None = None
    trace_id: str | None = None

class FailureIngestRequest(BaseModel):
    service_name:     str
    endpoint:         str
    http_method:      str        = "GET"
    status_code:      int        = 500
    error_type:       str
    error_message:    str
    stack_trace:      str | None = None
    request_metadata: dict | None = None
    environment:      str        = "production"

    # ── Tracing fields (all optional — not every service sends them) ──
    trace_id:       str | None = None
    correlation_id: str | None = None
    span_id:        str | None = None
    parent_span_id: str | None = None    
