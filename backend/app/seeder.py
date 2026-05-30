import random
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models import Failure

SERVICES = [
    {
        "name": "payment-service",
        "endpoints": ["/api/payments", "/api/payments/{id}/process", "/api/refunds", "/api/subscriptions"],
        "scenarios": [
            {"error_type": "DependencyFailure", "weight": 5,
             "messages": ["Stripe API returned 503: Service Unavailable", "Circuit breaker OPEN for stripe-gateway: 15 failures in 60s", "Payment gateway connection reset by peer"],
             "stack": "stripe.error.APIConnectionError: Error communicating with Stripe\n  File 'app/gateways/stripe.py', line 89, in charge_card\n  File 'app/services/payment.py', line 156, in process_payment"},
            {"error_type": "DatabaseConnectionError", "weight": 3,
             "messages": ["Deadlock on table 'transactions': rolled back", "Lock wait timeout exceeded for ledger update", "Too many connections: pool_size=10 exceeded"],
             "stack": "sqlalchemy.exc.OperationalError: Deadlock found\n  File 'app/repositories/transaction.py', line 67, in record_transaction"},
            {"error_type": "ConfigurationError", "weight": 1,
             "messages": ["Missing env var: STRIPE_WEBHOOK_SECRET", "Invalid config: PAYMENT_TIMEOUT_MS must be integer"],
             "stack": "KeyError: 'STRIPE_WEBHOOK_SECRET'\n  File 'app/core/config.py', line 12, in validate_config"},
        ],
    },
    {
        "name": "user-service",
        "endpoints": ["/api/users", "/api/users/{id}", "/api/auth/login", "/api/auth/refresh"],
        "scenarios": [
            {"error_type": "DatabaseConnectionError", "weight": 4,
             "messages": ["Connection to postgres://db:5432/users refused after 3 retries", "SSL connection error: certificate verify failed", "Max pool size exceeded"],
             "stack": "sqlalchemy.exc.OperationalError: could not connect to server\n  File 'app/db/session.py', line 45, in get_db\n  File 'app/services/user.py', line 23, in get_user"},
            {"error_type": "AuthenticationError", "weight": 3,
             "messages": ["JWT signature verification failed: token tampered", "Token expired at 2024-01-15T10:00:00Z", "Invalid issuer: expected 'auth-service'"],
             "stack": "jose.exceptions.JWTError: Signature verification failed\n  File 'app/middleware/auth.py', line 78, in verify_token"},
            {"error_type": "TimeoutError", "weight": 2,
             "messages": ["Request to notification-service timed out after 5000ms", "Redis cache lookup timed out"],
             "stack": "asyncio.TimeoutError\n  File 'app/services/notification.py', line 34, in notify_user"},
        ],
    },
    {
        "name": "inventory-service",
        "endpoints": ["/api/inventory", "/api/inventory/{sku}", "/api/warehouse/sync", "/api/reservations"],
        "scenarios": [
            {"error_type": "TimeoutError", "weight": 4,
             "messages": ["Warehouse sync RPC timed out after 10000ms", "ElasticSearch query timed out: query_time=30001ms", "Batch update blocked waiting for distributed lock"],
             "stack": "grpc.RpcError: StatusCode.DEADLINE_EXCEEDED\n  File 'app/clients/warehouse.py', line 45, in sync_stock"},
            {"error_type": "DependencyFailure", "weight": 3,
             "messages": ["Supplier API returned 500", "Kafka consumer lag exceeded threshold: lag=50000", "Redis cluster node unreachable: 192.168.1.5:6379"],
             "stack": "ConnectionError: Failed to connect to Redis cluster\n  File 'app/cache/redis_cluster.py', line 23, in get_cached_stock"},
            {"error_type": "DataValidationError", "weight": 1,
             "messages": ["Stock quantity cannot be negative: sku=PROD-123, quantity=-5", "Invalid warehouse code 'WH-999'"],
             "stack": "pydantic.ValidationError: 1 validation error for StockUpdate\n  quantity: must be > 0"},
        ],
    },
]


def _pick_weighted(scenarios):
    total = sum(s["weight"] for s in scenarios)
    r = random.uniform(0, total)
    cumulative = 0
    for s in scenarios:
        cumulative += s["weight"]
        if r <= cumulative:
            return s
    return scenarios[-1]


def seed_failures(db: Session, count: int = 150) -> int:
    existing = db.query(Failure).count()
    if existing >= count:
        return 0  # already seeded

    now = datetime.now(timezone.utc)
    records = []
    weights = [4, 3, 3]
    total_w = sum(weights)

    for svc, w in zip(SERVICES, weights):
        n = round(count * w / total_w)
        for _ in range(n):
            scenario = _pick_weighted(svc["scenarios"])
            endpoint = random.choice(svc["endpoints"]).replace("{id}", str(random.randint(100, 999))).replace("{sku}", f"PROD-{random.randint(10, 99)}")

            # Spread timestamps over last 48h with business-hour weighting
            hour_offset = random.choices(
                range(0, 48),
                weights=[
                    # More failures during business hours (9-18)
                    3 if (h % 24) in range(9, 18) else 1
                    for h in range(48)
                ]
            )[0]
            minute_offset = random.randint(0, 59)
            ts = now - timedelta(hours=hour_offset, minutes=minute_offset)

            records.append(Failure(
                service_name=svc["name"],
                endpoint=endpoint,
                http_method=random.choice(["GET", "POST", "PUT", "DELETE"]),
                status_code=500,
                error_type=scenario["error_type"],
                error_message=random.choice(scenario["messages"]),
                stack_trace=scenario["stack"],
                request_metadata={
                    "trace_id": f"trace-{random.randint(100000, 999999)}",
                    "user_agent": "internal-service/1.0",
                    "region": random.choice(["ap-south-1", "us-east-1", "eu-west-1"]),
                },
                environment="production",
                timestamp=ts,
            ))

    db.bulk_save_objects(records)
    db.commit()
    return len(records)
