import random
import time
import requests
import uuid

# --- Configuration ---
INGEST_URL = "http://127.0.0.1:8001/api/v1/failures/ingest"


SCENARIOS = {
    "cart-service": {
        "endpoints": ["/api/cart/add", "/api/cart/checkout"],
        "failures": [
            {"type": "RedisConnectionError", "msg": "Timeout connecting to Redis cluster: port 6379", "stack": "redis.exceptions.TimeoutError\n  File 'app/cache.py', line 112"},
            {"type": "ValidationException", "msg": "Cart is empty or contains invalid items", "stack": "app.exceptions.ValidationError\n  File 'app/services/cart.py', line 45"}
        ]
    },
    "order-service": {
        "endpoints": ["/api/orders/create", "/api/orders/validate"],
        "failures": [
            {"type": "DatabaseTimeout", "msg": "Postgres connection pool exhausted", "stack": "sqlalchemy.exc.TimeoutError\n  File 'app/db.py', line 88"},
            {"type": "StateConflictError", "msg": "Order state transition invalid: PENDING to SHIPPED", "stack": "app.domain.order.py\n  File 'app/domain/order.py', line 201"}
        ]
    },
    "inventory-service": {
        "endpoints": ["/api/inventory/reserve", "/api/inventory/release"],
        "failures": [
            {"type": "StockUnavailableException", "msg": "Item SKU-99382 out of stock across all warehouses", "stack": "app.services.inventory.py\n  File 'app/services/inventory.py', line 33"},
            {"type": "DeadlockDetected", "msg": "Transaction deadlock on table 'stock_levels'", "stack": "psycopg2.errors.DeadlockDetected\n  File 'app/repositories/stock.py', line 67"}
        ]
    },
    "payment-service": {
        "endpoints": ["/api/payments/process", "/api/payments/refund"],
        "failures": [
            {"type": "DependencyFailure", "msg": "Stripe API returned 503: Service Unavailable", "stack": "stripe.error.APIConnectionError\n  File 'app/gateways/stripe.py', line 89"},
            {"type": "FraudBlockedException", "msg": "Transaction blocked by anti-fraud AI model", "stack": "app.security.fraud.py\n  File 'app/security/fraud.py', line 12"}
        ]
    },
    "notification-service": {
        "endpoints": ["kafka_consumer_group: order_events", "kafka_consumer_group: user_alerts"],
        "failures": [
            {"type": "SMTPConnectionError", "msg": "Failed to connect to SendGrid SMTP relay", "stack": "smtplib.SMTPConnectError\n  File 'app/email/sender.py', line 45"},
            {"type": "TemplateRenderError", "msg": "Missing context variable 'user_name' in receipt.html", "stack": "jinja2.exceptions.UndefinedError\n  File 'app/templates/render.py', line 22"}
        ]
    }
}

def _send_to_fci(payload: dict):
    """Helper function to cleanly send the payload and handle logs."""
    try:
        response = requests.post(INGEST_URL, json=payload, timeout=3)
        if response.status_code == 201:
            print(f"[Simulator] ✓ Ingested | {payload['service_name']} → {payload['error_type']}")
        else:
            print(f"[Simulator] ✗ HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[Simulator] ✗ Connection failed: {e}")

def _send_random_single_failure():
    """Fires a standard, isolated API failure from any random service."""
    svc_name = random.choice(list(SCENARIOS.keys()))
    svc_data = SCENARIOS[svc_name]
    failure = random.choice(svc_data["failures"])
    
    # Notification service is heavily async
    method = "ASYNC" if svc_name == "notification-service" else random.choice(["GET", "POST"])

    payload = {
        "service_name":     svc_name,
        "endpoint":         random.choice(svc_data["endpoints"]),
        "http_method":      method,
        "status_code":      500,
        "error_type":       failure["type"],
        "error_message":    failure["msg"],
        "stack_trace":      failure["stack"],
        "environment":      "production",
        "trace_id":         f"trace-{uuid.uuid4().hex[:12]}",
        "span_id":          f"span-{uuid.uuid4().hex[:8]}",
        "parent_span_id":   None, 
        "request_metadata": {"user_agent": "fci-random-simulator"}
    }
    print(f"\n[Simulator] ⚡ Firing isolated {method} failure...")
    _send_to_fci(payload)

def _simulate_distributed_flow():
    """
    Simulates a full user journey that builds a trace tree.
    It randomly decides WHICH service in the chain will crash.
    """
    trace_id       = f"trace-{uuid.uuid4().hex[:12]}"
    correlation_id = f"ORD-{random.randint(10000, 99999)}"
    
    print(f"\n[Simulator] 📦 Starting Distributed Flow (trace={trace_id})")

    # The chain of services involved in an order
    flow_steps = ["cart-service", "order-service", "inventory-service", "payment-service", "notification-service"]
    
    # Randomly pick where the architecture breaks
    failing_service = random.choice(flow_steps)
    
    parent_span = None
    
    for step in flow_steps:
        current_span = f"span-{uuid.uuid4().hex[:8]}"
        
        # If this step succeeds, just log it locally (don't send to FCI)
        if step != failing_service:
            print(f"   ↳ {step} ✅ (span: {current_span})")
            parent_span = current_span # Pass the baton to the next service
            time.sleep(0.2)
            continue
            
        # 💥 WE HIT THE FAILING SERVICE! 💥
        print(f"   ↳ {step} ❌ CRASHED! (span: {current_span}, parent: {parent_span})")
        
        failure = random.choice(SCENARIOS[step]["failures"])
        is_async = (step == "notification-service")
        
        payload = {
            "service_name":  step,
            "endpoint":      random.choice(SCENARIOS[step]["endpoints"]),
            "http_method":   "ASYNC" if is_async else "POST",
            "status_code":   500,
            "error_type":    failure["type"],
            "error_message": failure["msg"],
            "stack_trace":   failure["stack"],
            "environment":   "production",
            
            # ── The Tracing Glue ──
            "trace_id":       trace_id,
            "correlation_id": correlation_id,    
            "span_id":        current_span,
            "parent_span_id": parent_span, 

            "request_metadata": {
                "order_id": correlation_id,
                "flow_type": "async_pubsub" if is_async else "sync_api"
            }
        }
        
        _send_to_fci(payload)
        break # Stop the loop. The trace dies here.

def run_simulator(interval_seconds: int = 10):
    print(f"=================================================")
    print(f"🚀 FCI Unified Traffic Simulator Started")
    print(f"🎯 Target URL: {INGEST_URL}")
    print(f"=================================================\n")
    
    time.sleep(1) 

    while True:
        # 60% chance for a complex distributed trace flow
        # 40% chance for background noise (isolated single service errors)
        if random.random() < 0.60:
            _simulate_distributed_flow()
        else:
            _send_random_single_failure()

        time.sleep(interval_seconds)

if __name__ == "__main__":
    run_simulator(interval_seconds=6)