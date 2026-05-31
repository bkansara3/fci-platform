from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Failure
from app.schemas import FailureOut, PaginatedFailures
from pydantic import BaseModel
from datetime import datetime, timezone
from app.auth import require_admin
router = APIRouter(prefix="/failures", tags=["failures"])


@router.get("", response_model=PaginatedFailures)
def list_failures(
    service: str | None = Query(None),
    error_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Failure)
    if service:
        q = q.filter(Failure.service_name.ilike(f"%{service}%"))
    if error_type:
        q = q.filter(Failure.error_type.ilike(f"%{error_type}%"))
    total = q.count()
    items = q.order_by(Failure.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedFailures(
        items=[FailureOut.model_validate(f) for f in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{failure_id}", response_model=FailureOut)
def get_failure(failure_id: int, db: Session = Depends(get_db)):
    f = db.query(Failure).filter(Failure.id == failure_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Not found")
    return FailureOut.model_validate(f)



class FailureIngestRequest(BaseModel):
    service_name:     str
    endpoint:         str
    http_method:      str = "GET"
    status_code:      int = 500
    error_type:       str
    error_message:    str
    stack_trace:      str | None = None
    request_metadata: dict | None = None
    environment:      str = "production"
    # ── Store tracing fields (Added these back!) ──
    trace_id:       str | None = None
    correlation_id: str | None = None
    span_id:        str | None = None
    parent_span_id: str | None = None

@router.post("/ingest", status_code=201)
def ingest_failure(
    payload: FailureIngestRequest,
    db: Session = Depends(get_db)
):
    failure = Failure(
        service_name     = payload.service_name,
        endpoint         = payload.endpoint,
        http_method      = payload.http_method,
        status_code      = payload.status_code,
        error_type       = payload.error_type,
        error_message    = payload.error_message,
        stack_trace      = payload.stack_trace,
        request_metadata = payload.request_metadata,
        environment      = payload.environment,
        timestamp        = datetime.now(timezone.utc),

         # ── Store tracing fields ──────────────────────
        trace_id         = payload.trace_id,
        correlation_id   = payload.correlation_id,
        span_id          = payload.span_id,
        parent_span_id   = payload.parent_span_id,
    )
    db.add(failure)
    db.commit()
    db.refresh(failure)
    print(f"[FCI] Ingested failure #{failure.id} — {failure.service_name}/{failure.error_type}")
    return {"id": failure.id, "message": "failure captured"}


# ── New endpoint: find all failures for a trace ────────────
@router.get("/trace/{trace_id}")
def get_failures_by_trace(
    trace_id: str,
    db: Session = Depends(get_db)
    
):
    """
    Given a trace_id, return ALL failures across ALL services
    that share that trace. This shows the full failure journey.
    """
    failures = (
        db.query(Failure)
        .filter(Failure.trace_id == trace_id)
        .order_by(Failure.timestamp.asc())   # chronological order
        .all()
    )
    return [FailureOut.model_validate(f) for f in failures]

# ── New endpoint: find by correlation (order_id etc) ───────
@router.get("/correlation/{correlation_id}")
def get_failures_by_correlation(
    correlation_id: str,
    db: Session = Depends(get_db)
    
):
    """
    Find all failures related to a business entity
    e.g. order_id=ORD-123 failed across multiple services
    """
    failures = (
        db.query(Failure)
        .filter(Failure.correlation_id == correlation_id)
        .order_by(Failure.timestamp.asc())
        .all()
    )
    return [FailureOut.model_validate(f) for f in failures]