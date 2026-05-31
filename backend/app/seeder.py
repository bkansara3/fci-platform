import random
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models import Failure

SERVICES = {
    "cart-service": {
        "endpoints": ["/api/cart/add", "/api/cart/checkout"],
        "scenarios": [
            {"error_type": "RedisConnectionError", "weight": 4, "messages": ["Timeout connecting to Redis cluster: port 6379"], "stack": "redis.exceptions.TimeoutError\n  File 'app/cache.py', line 112"},
            {"error_type": "ValidationException", "weight": 2, "messages": ["Cart is empty or contains invalid items"], "stack": "app.exceptions.ValidationError\n  File 'app/services/cart.py', line 45"}
        ]
    },
    "order-service": {
        "endpoints": ["/api/orders/create", "/api/orders/validate"],
        "scenarios": [
            {"error_type": "DatabaseTimeout", "weight": 5, "messages": ["Postgres connection pool exhausted"], "stack": "sqlalchemy.exc.TimeoutError\n  File 'app/db.py', line 88"},
            {"error_type": "StateConflictError", "weight": 2, "messages": ["Order state transition invalid: PENDING to SHIPPED"], "stack": "app.domain.order.py\n  File 'app/domain/order.py', line 201"}
        ]
    },
    "inventory-service": {
        "endpoints": ["/api/inventory/reserve", "/api/inventory/release"],
        "scenarios": [
            {"error_type": "StockUnavailableException", "weight": 3, "messages": ["Item SKU-99382 out of stock across all warehouses"], "stack": "app.services.inventory.py\n  File 'app/services/inventory.py', line 33"},
            {"error_type": "DeadlockDetected", "weight": 3, "messages": ["Transaction deadlock on table 'stock_levels'"], "stack": "psycopg2.errors.DeadlockDetected\n  File 'app/repositories/stock.py', line 67"}
        ]
    },
    "payment-service": {
        "endpoints": ["/api/payments/process", "/api/payments/refund"],
        "scenarios": [
            {"error_type": "DependencyFailure", "weight": 5, "messages": ["Stripe API returned 503: Service Unavailable", "Payment gateway connection reset"], "stack": "stripe.error.APIConnectionError\n  File 'app/gateways/stripe.py', line 89"},
            {"error_type": "FraudBlockedException", "weight": 1, "messages": ["Transaction blocked by anti-fraud AI model"], "stack": "app.security.fraud.py\n  File 'app/security/fraud.py', line 12"}
        ]
    },
    "notification-service": {
        "endpoints": ["kafka_consumer_group: order_events"],
        "scenarios": [
            {"error_type": "SMTPConnectionError", "weight": 4, "messages": ["Failed to connect to SendGrid SMTP relay"], "stack": "smtplib.SMTPConnectError\n  File 'app/email/sender.py', line 45"},
            {"error_type": "TemplateRenderError", "weight": 1, "messages": ["Missing context variable 'user_name' in receipt.html"], "stack": "jinja2.exceptions.UndefinedError\n  File 'app/templates/render.py', line 22"}
        ]
    }
}

def _pick_weighted(scenarios):
    total = sum(s["weight"] for s in scenarios)
    r = random.uniform(0, total)
    cumulative = 0
    for s in scenarios:
        cumulative += s["weight"]
        if r <= cumulative:
            return s
    return scenarios[-1]

def _generate_timestamp(now):
    """Spreads timestamps over the last 48h with business-hour weighting."""
    hour_offset = random.choices(
        range(0, 48),
        weights=[3 if (h % 24) in range(9, 18) else 1 for h in range(48)]
    )[0]
    minute_offset = random.randint(0, 59)
    return now - timedelta(hours=hour_offset, minutes=minute_offset)

def seed_failures(db: Session, count: int = 250) -> int:
    existing = db.query(Failure).count()
    if existing >= count:
        return 0  # Already seeded

    now = datetime.now(timezone.utc)
    records = []
    
    # Generate failures until we hit the desired count
    while len(records) < count:
        is_distributed_trace = random.random() < 0.30 # 30% chance to generate a cascading failure chain
        
        ts = _generate_timestamp(now)
        trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        correlation_id = f"ORD-{random.randint(10000, 99999)}"
        
        if is_distributed_trace:
            # Create a realistic cascading trace: Payment fails -> causes Inventory to fail -> causes Order to fail
            payment_span = f"span-{uuid.uuid4().hex[:8]}"
            inventory_span = f"span-{uuid.uuid4().hex[:8]}"
            order_span = f"span-{uuid.uuid4().hex[:8]}"
            
            chain = [
                ("order-service", order_span, None),
                ("inventory-service", inventory_span, order_span),
                ("payment-service", payment_span, inventory_span)
            ]
            
            for svc_name, span, parent_span in chain:
                scenario = _pick_weighted(SERVICES[svc_name]["scenarios"])
                records.append(Failure(
                    service_name=svc_name,
                    endpoint=random.choice(SERVICES[svc_name]["endpoints"]),
                    http_method="POST",
                    status_code=500,
                    error_type=scenario["error_type"],
                    error_message=random.choice(scenario["messages"]),
                    stack_trace=scenario["stack"],
                    environment="production",
                    timestamp=ts,
                    
                    # ── Top-Level Tracing Fields ──
                    trace_id=trace_id,
                    correlation_id=correlation_id,
                    span_id=span,
                    parent_span_id=parent_span,
                    
                    request_metadata={"region": "ap-south-1"}
                ))
        else:
            # Generate a standard isolated failure
            svc_name = random.choice(list(SERVICES.keys()))
            scenario = _pick_weighted(SERVICES[svc_name]["scenarios"])
            is_async = (svc_name == "notification-service")
            
            records.append(Failure(
                service_name=svc_name,
                endpoint=random.choice(SERVICES[svc_name]["endpoints"]),
                http_method="ASYNC" if is_async else random.choice(["GET", "POST"]),
                status_code=500,
                error_type=scenario["error_type"],
                error_message=random.choice(scenario["messages"]),
                stack_trace=scenario["stack"],
                environment="production",
                timestamp=ts,
                
                # ── Top-Level Tracing Fields ──
                trace_id=trace_id,
                correlation_id=correlation_id,
                span_id=f"span-{uuid.uuid4().hex[:8]}",
                parent_span_id=None,
                
                request_metadata={"region": "ap-south-1"}
            ))

    # Truncate to exact count in case the chain pushed it slightly over
    records = records[:count]

    db.bulk_save_objects(records)
    db.commit()
    return len(records)