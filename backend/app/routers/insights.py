from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db
from app.models import Failure, Insight
from app.schemas import InsightOut, InsightRequest
from app.ai.graph import run_fci_pipeline

router = APIRouter(prefix="/insights", tags=["insights"])


def _failure_to_dict(f: Failure) -> dict:
    return {
        "id": f.id,
        "endpoint": f.endpoint,
        "error_message": f.error_message,
        "timestamp": f.timestamp.isoformat() if f.timestamp else None,
    }


@router.get("", response_model=list[InsightOut])
def list_insights(db: Session = Depends(get_db)):
    rows = db.query(Insight).order_by(Insight.generated_at.desc()).limit(50).all()
    return [InsightOut.model_validate(r) for r in rows]


@router.post("/generate", response_model=InsightOut)
def generate_insight(req: InsightRequest, db: Session = Depends(get_db)):
    failures = (
        db.query(Failure)
        .filter(Failure.service_name == req.service_name)
        .filter(Failure.error_type == req.error_type)
        .order_by(Failure.timestamp.desc())
        .limit(30)
        .all()
    )
    if not failures:
        raise HTTPException(status_code=404, detail=f"No failures found for {req.service_name}/{req.error_type}")

    failure_dicts = [_failure_to_dict(f) for f in failures]

    # Run LangGraph pipeline
    result = run_fci_pipeline(req.service_name, req.error_type, failure_dicts)

    insight = Insight(
        service_name=req.service_name,
        error_type=req.error_type,
        failure_count=len(failures),
        root_cause=result["root_cause"],
        risk_level=result["risk_level"],
        risk_summary=result["risk_summary"],
        recommended_fixes=result["recommended_fixes"],
        remediation_actions=result["remediation_actions"],
        confidence=result["confidence"],
        graph_trace=result["trace"],
        generated_at=datetime.now(timezone.utc),
        failure_ids=[f.id for f in failures],
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return InsightOut.model_validate(insight)


@router.get("/groups")
def get_failure_groups(db: Session = Depends(get_db)):
    """Return distinct (service, error_type) combos with counts — for the UI dropdown."""
    from sqlalchemy import func
    rows = (
        db.query(Failure.service_name, Failure.error_type, func.count(Failure.id).label("count"))
        .group_by(Failure.service_name, Failure.error_type)
        .order_by(func.count(Failure.id).desc())
        .all()
    )
    return [{"service_name": r[0], "error_type": r[1], "count": r[2]} for r in rows]
