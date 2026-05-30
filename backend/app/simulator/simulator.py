import random
import time
import threading
import requests
from datetime import datetime, timezone

# Same failure scenarios as seeder — but sends via HTTP not direct DB
SCENARIOS = [
    {
        "service_name": "payment-service",
        "endpoints":    ["/api/payments", "/api/refunds", "/api/subscriptions"],
        "failures": [
            {
                "error_type":    "DependencyFailure",
                "weight":        5,
                "messages":      [
                    "Stripe API returned 503: Service Unavailable",
                    "Circuit breaker OPEN: 15 failures in 60s",
                    "Payment gateway connection reset by peer",
                ],
                "stack_trace":   "stripe.error.APIConnectionError\n  File 'app/gateways/stripe.py', line 89"
            },
            {
                "error_type":    "DatabaseConnectionError",
                "weight":        3,
                "messages":      [
                    "Deadlock on table 'transactions': rolled back",
                    "Too many connections: pool_size=10 exceeded",
                ],
                "stack_trace":   "sqlalchemy.exc.OperationalError: Deadlock\n  File 'app/repositories/transaction.py', line 67"
            },
            {
                "error_type":    "ConfigurationError",
                "weight":        1,
                "messages":      ["Missing env var: STRIPE_WEBHOOK_SECRET"],
                "stack_trace":   "KeyError: 'STRIPE_WEBHOOK_SECRET'\n  File 'app/core/config.py', line 12"
            },
        ]
    },
    {
        "service_name": "user-service",
        "endpoints":    ["/api/users", "/api/auth/login", "/api/auth/refresh"],
        "failures": [
            {
                "error_type":    "DatabaseConnectionError",
                "weight":        4,
                "messages":      [
                    "Connection to postgres://db:5432 refused after 3 retries",
                    "Max pool size exceeded",
                ],
                "stack_trace":   "sqlalchemy.exc.OperationalError\n  File 'app/db/session.py', line 45"
            },
            {
                "error_type":    "AuthenticationError",
                "weight":        3,
                "messages":      [
                    "JWT signature verification failed: token tampered",
                    "Token expired at 2024-01-15T10:00:00Z",
                ],
                "stack_trace":   "jose.exceptions.JWTError\n  File 'app/middleware/auth.py', line 78"
            },
            {
                "error_type":    "TimeoutError",
                "weight":        2,
                "messages":      ["Redis cache lookup timed out after 5000ms"],
                "stack_trace":   "asyncio.TimeoutError\n  File 'app/services/cache.py', line 34"
            },
        ]
    },
    {
        "service_name": "inventory-service",
        "endpoints":    ["/api/inventory", "/api/warehouse/sync", "/api/reservations"],
        "failures": [
            {
                "error_type":    "TimeoutError",
                "weight":        4,
                "messages":      [
                    "Warehouse sync RPC timed out after 10000ms",
                    "ElasticSearch query timed out: query_time=30001ms",
                ],
                "stack_trace":   "grpc.RpcError: DEADLINE_EXCEEDED\n  File 'app/clients/warehouse.py', line 45"
            },
            {
                "error_type":    "DependencyFailure",
                "weight":        3,
                "messages":      [
                    "Kafka consumer lag exceeded threshold: lag=50000",
                    "Redis cluster node unreachable: 192.168.1.5:6379",
                ],
                "stack_trace":   "ConnectionError: Redis cluster failed\n  File 'app/cache/redis_cluster.py', line 23"
            },
        ]
    },
]

INGEST_URL = "http://127.0.0.1:8001/api/v1/failures/ingest"


def _pick_weighted(failures):
    total = sum(f["weight"] for f in failures)
    r = random.uniform(0, total)
    cumulative = 0
    for f in failures:
        cumulative += f["weight"]
        if r <= cumulative:
            return f
    return failures[-1]


def _send_one_failure():
    """Pick a random service and send one failure to the ingest endpoint."""
    svc = random.choice(SCENARIOS)
    failure = _pick_weighted(svc["failures"])

    endpoint = random.choice(svc["endpoints"])

    payload = {
        "service_name":     svc["service_name"],
        "endpoint":         endpoint,
        "http_method":      random.choice(["GET"]),
        "status_code":      500,
        "error_type":       failure["error_type"],
        "error_message":    random.choice(failure["messages"]),
        "stack_trace":      failure["stack_trace"],
        "request_metadata": {
            "trace_id":   f"trace-{random.randint(100000, 999999)}",
            "region":     random.choice(["ap-south-1", "us-east-1", "eu-west-1"]),
            "user_agent": "internal-service/1.0",
        },
        "environment": "production",
    }

    try:
        response = requests.post(INGEST_URL, json=payload, timeout=3)
        if response.status_code == 201:
            data = response.json()
            print(f"[Simulator] ✓ #{data['id']} {svc['service_name']} → {failure['error_type']}")
        else:
            print(f"[Simulator] ✗ Ingest failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[Simulator] ✗ Could not reach FCI: {e}")


def run_simulator(interval_seconds: int = 10):
    """
    Runs forever in a background thread.
    Sends one failure every `interval_seconds` seconds.
    """
    print(f"[Simulator] Started — sending 1 failure every {interval_seconds}s")
    # Small initial delay so FastAPI fully starts first
    time.sleep(5)

    while True:
        _send_one_failure()
        time.sleep(interval_seconds)


def start_simulator_thread(interval_seconds: int = 10):
    """Start simulator as a daemon thread — dies when main process dies."""
    thread = threading.Thread(
        target=run_simulator,
        args=(interval_seconds,),
        daemon=True,        # ← automatically stops when FastAPI stops
        name="fci-simulator"
    )
    thread.start()
    return thread