from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.models import Failure
from app.schemas import AnalyticsResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsResponse)
def get_analytics(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    twenty_four_ago = now - timedelta(hours=24)

    total = db.query(func.count(Failure.id)).scalar()
    last_hour = db.query(func.count(Failure.id)).filter(Failure.timestamp >= one_hour_ago).scalar()

    top_services = [
        {"service_name": r[0], "count": r[1]}
        for r in db.query(Failure.service_name, func.count(Failure.id).label("c"))
        .group_by(Failure.service_name).order_by(func.count(Failure.id).desc()).limit(10)
    ]

    top_errors = [
        {"error_type": r[0], "count": r[1]}
        for r in db.query(Failure.error_type, func.count(Failure.id).label("c"))
        .group_by(Failure.error_type).order_by(func.count(Failure.id).desc()).limit(10)
    ]

    ts_rows = db.execute(text("""
        SELECT strftime('%Y-%m-%dT%H:00:00', timestamp) as bucket, COUNT(*) as count
        FROM failures WHERE timestamp >= :cutoff
        GROUP BY bucket ORDER BY bucket
    """), {"cutoff": twenty_four_ago.strftime("%Y-%m-%d %H:%M:%S")}).fetchall()
    
    time_series = [{"bucket": r[0], "count": r[1]} for r in ts_rows]

    hm_rows = db.execute(text("""
        SELECT service_name, CAST(strftime('%H', timestamp) AS INTEGER) as hour, COUNT(*) as count
        FROM failures WHERE timestamp >= :cutoff
        GROUP BY service_name, hour ORDER BY service_name, hour
    """), {"cutoff": twenty_four_ago.strftime("%Y-%m-%d %H:%M:%S")}).fetchall()
    heatmap = [{"service_name": r[0], "hour": r[1], "count": r[2]} for r in hm_rows]

    return AnalyticsResponse(
        total_failures=total,
        failures_last_hour=last_hour,
        top_services=top_services,
        top_error_types=top_errors,
        time_series=time_series,
        heatmap=heatmap,
    )
