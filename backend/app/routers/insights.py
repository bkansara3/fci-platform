from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Failure, Insight
from app.schemas import InsightRequest, InsightOut
from app.ai.graph import run_fci_pipeline
from app.auth import require_admin

router = APIRouter(prefix="/insights") # Note the prefix here to match /api/v1/insights

# ── RESTORED: GET Endpoints for the React UI ────────────────────────────────

@router.get("/groups")
def get_insight_groups(db: Session = Depends(get_db)):
    """Groups failures by service and error type for the frontend to display."""
    groups = (
        db.query(
            Failure.service_name,
            Failure.error_type,
            func.count(Failure.id).label("count")
        )
        .group_by(Failure.service_name, Failure.error_type)
        .order_by(func.count(Failure.id).desc())
        .all()
    )
    return [{"service_name": g[0], "error_type": g[1], "count": g[2]} for g in groups]

@router.get("", response_model=list[InsightOut])
@router.get("/", response_model=list[InsightOut], include_in_schema=False)
def get_insights(db: Session = Depends(get_db)):
    """Fetches all previously generated AI insights from the database."""
    return db.query(Insight).order_by(Insight.generated_at.desc()).all()


# ── OUR NEW: AI Generation Endpoint ─────────────────────────────────────────

def build_trace_tree(records):
    """Helper function to convert flat database rows into a nested trace tree for the AI."""
    spans = {}
    for r in records:
        span_dict = {
            "id": r.id,
            "service_name": r.service_name,
            "error_type": r.error_type,
            "endpoint": r.endpoint,
            "span_id": r.span_id,
            "parent_span_id": r.parent_span_id,
            "children": []
        }
        spans[r.span_id] = span_dict

    root_spans = []
    for span_id, span in spans.items():
        parent_id = span["parent_span_id"]
        if parent_id and parent_id in spans:
            spans[parent_id]["children"].append(span)
        else:
            root_spans.append(span)
            
    return root_spans

@router.post("/generate", response_model=InsightOut)
def generate_insight(req: InsightRequest, db: Session = Depends(get_db), user = Depends(require_admin)):
    
    # ── PATH A: DISTRIBUTED TRACE ANALYSIS ──
    if req.trace_id:
        records = db.query(Failure).filter(Failure.trace_id == req.trace_id).all()
        if not records:
            raise HTTPException(status_code=404, detail="Trace not found")
            
        trace_tree = build_trace_tree(records)
        
        result = run_fci_pipeline(
            trace_id=req.trace_id,
            trace_tree=trace_tree
        )
        
        insight = Insight(
            service_name="Distributed Trace (Order Flow)",
            error_type="Cascading Failure",
            failure_count=len(records),
            root_cause=result["root_cause"],
            risk_level=result["risk_level"],
            risk_summary=result["risk_summary"],
            recommended_fixes=result["recommended_fixes"],
            remediation_actions=result["remediation_actions"],
            confidence=result["confidence"],
            graph_trace=result["trace"],
            failure_ids=[r.id for r in records]
        )
        db.add(insight)
        db.commit()
        db.refresh(insight)
        return insight

    # ── PATH B: STANDARD AGGREGATED ANALYSIS ──
    elif req.service_name and req.error_type:
        records = db.query(Failure).filter(
            Failure.service_name == req.service_name,
            Failure.error_type == req.error_type
        ).all()
        
        if not records:
            raise HTTPException(status_code=404, detail="No failures found for this service/error combo")

        failure_dicts = [
            {"id": r.id, "timestamp": r.timestamp.isoformat() if r.timestamp else None, "endpoint": r.endpoint} 
            for r in records
        ]
        
        result = run_fci_pipeline(
            service_name=req.service_name,
            error_type=req.error_type,
            failures=failure_dicts
        )
        
        insight = Insight(
            service_name=req.service_name,
            error_type=req.error_type,
            failure_count=len(records),
            root_cause=result["root_cause"],
            risk_level=result["risk_level"],
            risk_summary=result["risk_summary"],
            recommended_fixes=result["recommended_fixes"],
            remediation_actions=result["remediation_actions"],
            confidence=result["confidence"],
            graph_trace=result["trace"],
            failure_ids=[r.id for r in records]
        )
        db.add(insight)
        db.commit()
        db.refresh(insight)
        return insight
        
    else:
        raise HTTPException(status_code=400, detail="Must provide either trace_id OR service_name + error_type")