"""
MockFCILLM — a LangChain BaseLLM that simulates an AI model.

Instead of calling an external API, it uses a rule-based engine keyed on
error_type and failure patterns to produce realistic, varied analysis.
Swap _call() for a real LLM (OpenAI, Anthropic, etc.) with zero changes
to the LangGraph pipeline.
"""

import json
import random
from typing import Any, Optional
from langchain_core.language_models import BaseLLM
from langchain_core.outputs import LLMResult, Generation
from langchain_core.callbacks.manager import CallbackManagerForLLMRun


# ── Analysis templates per error type ──────────────────────────────────────

ANALYSIS_KB = {
    "DatabaseConnectionError": {
        "causes": [
            "Connection pool exhaustion due to long-running queries holding connections. "
            "A recent schema migration likely added a missing index on a high-traffic table, "
            "causing full table scans that hold DB connections beyond the pool timeout.",
            "Primary replica failover in progress. The DB primary node became unreachable "
            "after a brief network partition. Connection strings still point to the old primary, "
            "causing all new connections to fail until DNS TTL expires.",
            "Max connection limit hit on the database server. A background ETL job started "
            "at the same time as peak traffic, consuming all available slots.",
        ],
        "fixes": [
            "Run EXPLAIN ANALYZE on the slowest queries and add missing indexes",
            "Increase connection pool size and add connection timeout settings",
            "Add database connection health-check with circuit breaker pattern",
            "Review and optimize long-running transactions holding connections",
            "Set statement_timeout to prevent runaway queries",
        ],
        "actions": [
            "Check pg_stat_activity for blocked/long-running queries immediately",
            "Kill idle connections: SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state='idle'",
            "Verify DB replica health and failover status",
            "Alert the DBA team and review recent migration history",
        ],
        "risk_range": (0.7, 0.95),
    },
    "DependencyFailure": {
        "causes": [
            "Circuit breaker tripped on the downstream payment gateway. "
            "15 consecutive timeouts within 60 seconds triggered the open state. "
            "This is consistent with a Stripe/payment provider partial outage visible "
            "on their status page.",
            "Upstream authentication service is rate-limiting requests. "
            "Recent traffic spike (3x normal volume) exceeded the per-service rate limit "
            "configured in the API gateway, causing cascading 429 → 500 errors.",
            "A third-party SDK was updated in the last deployment and introduced "
            "a breaking API contract change with the external dependency.",
        ],
        "fixes": [
            "Implement fallback/cached response for non-critical dependency calls",
            "Add retry with exponential backoff and jitter",
            "Tune circuit breaker thresholds to match SLA requirements",
            "Pin third-party SDK versions to avoid unintended breaking upgrades",
            "Add upstream health check endpoint to dependency proxy",
        ],
        "actions": [
            "Check upstream service status page for ongoing incidents",
            "Enable fallback mode / degraded-service flag",
            "Review circuit breaker state: half-open probing every 30s",
            "Notify upstream team and open incident ticket",
        ],
        "risk_range": (0.65, 0.92),
    },
    "TimeoutError": {
        "causes": [
            "ElasticSearch cluster under memory pressure is experiencing JVM GC pauses "
            "of 8–12 seconds, causing query timeouts on all search-backed endpoints. "
            "A large batch reindex job started 2 hours ago is competing for heap.",
            "Downstream gRPC service is overloaded. Pod auto-scaling lagged behind a "
            "sudden traffic spike, causing request queues to build up and timeouts to cascade.",
            "Network congestion between availability zones introduced 400ms+ latency on "
            "inter-service calls. Combined with the default 500ms timeout, most cross-AZ "
            "calls are now failing.",
        ],
        "fixes": [
            "Increase timeout thresholds for known-slow dependencies",
            "Add request hedging for latency-sensitive operations",
            "Tune pod auto-scaling: lower CPU threshold, increase scale-up speed",
            "Move to async processing for operations that can tolerate delay",
            "Add per-request deadline propagation via context",
        ],
        "actions": [
            "Check pod CPU/memory metrics for all dependent services",
            "Pause the batch reindex job if ES cluster is the bottleneck",
            "Manually scale up affected pods to handle backlog",
            "Review and adjust HPA min/max replica counts",
        ],
        "risk_range": (0.6, 0.88),
    },
    "AuthenticationError": {
        "causes": [
            "JWT signing key was rotated as part of a scheduled security operation, "
            "but not all services have received the new public key yet. "
            "Tokens signed with the new key fail verification on services still "
            "holding the old public key.",
            "Redis session cache TTL is too short — sessions expire before users "
            "complete long operations, causing mid-flow authentication failures "
            "that appear as 500 errors to the client.",
            "A new deployment changed the expected JWT audience claim but the "
            "auth middleware was not updated, causing all incoming tokens to fail validation.",
        ],
        "fixes": [
            "Implement key rotation with overlap period (old + new key both valid)",
            "Extend session TTL or implement session sliding expiry",
            "Add JWT validation unit tests covering all claim fields",
            "Use a dedicated auth library rather than custom JWT parsing",
            "Add metrics on token validation failures to detect key mismatches early",
        ],
        "actions": [
            "Roll back the key rotation if overlap period was missed",
            "Verify all services are serving the correct JWKS endpoint",
            "Check Redis connectivity and TTL settings for session keys",
            "Review the last deployment diff for auth middleware changes",
        ],
        "risk_range": (0.55, 0.85),
    },
    "ConfigurationError": {
        "causes": [
            "A required environment variable was not injected into the new deployment. "
            "The Kubernetes secret was updated but the pods were not restarted, "
            "so they continue running with the stale (missing) configuration.",
            "Config server (Consul/Vault/SSM) is experiencing intermittent connectivity issues. "
            "Services that fetch config at startup succeed, but those with dynamic "
            "config refresh are failing on reload.",
            "A feature flag toggled in the config service has an invalid value type — "
            "expected boolean, received string 'true', causing a parse error at runtime.",
        ],
        "fixes": [
            "Add config validation on startup with a fail-fast guard",
            "Use config schema validation (e.g. Pydantic Settings) to catch type errors",
            "Implement config hot-reload with fallback to last known good config",
            "Add config health-check endpoint for ops visibility",
            "Document all required env vars in a .env.example committed to the repo",
        ],
        "actions": [
            "Restart affected pods to pick up the latest secret/config values",
            "Verify Kubernetes secrets are correctly mounted in the pod spec",
            "Check config server connectivity from within the affected pod",
            "Roll back the last config change if the issue started post-deployment",
        ],
        "risk_range": (0.5, 0.80),
    },
    "DataValidationError": {
        "causes": [
            "A client library was updated and is now sending an additional required field "
            "that the server schema does not expect, causing validation to reject valid requests.",
            "Null values are propagating from an upstream service into fields "
            "that are declared non-nullable, indicating a data contract violation "
            "introduced in a recent upstream API change.",
            "A database migration added a NOT NULL constraint on an existing column "
            "without backfilling historical rows, causing reads of old records to fail validation.",
        ],
        "fixes": [
            "Add backward-compatible schema versioning to the API",
            "Use strict null checks and validate at service boundaries",
            "Add migration tests that verify data integrity post-migration",
            "Implement API contract tests (e.g. Pact) between services",
            "Log validation errors with the full rejected payload for debugging",
        ],
        "actions": [
            "Identify which client/upstream service is sending malformed data",
            "Add a temporary validation bypass with logging to unblock users",
            "Backfill null values in the affected DB column",
            "Coordinate with the upstream team to fix the data contract",
        ],
        "risk_range": (0.45, 0.75),
    },
}

DEFAULT_ANALYSIS = {
    "causes": ["An unexpected runtime error is causing repeated failures. Further investigation of the service logs and recent deployment history is recommended."],
    "fixes": ["Add detailed error logging", "Review recent code changes", "Add unit tests for the failing code path"],
    "actions": ["Check service logs for stack traces", "Review recent deployments", "Escalate to the service owner"],
    "risk_range": (0.5, 0.7),
}


class MockFCILLM(BaseLLM):
    """
    Mock LLM that simulates AI analysis for FCI.
    Produces deterministic-ish responses based on error_type patterns.
    Replace _call() with a real LLM provider (OpenAI, Anthropic, etc.)
    without changing anything else in the pipeline.
    """

    model_name: str = "mock-fci-analyst-v1"

    @property
    def _llm_type(self) -> str:
        return "mock_fci"

    def _generate(
        self,
        prompts: list[str],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> LLMResult:
        generations = []
        for prompt in prompts:
            text = self._analyze(prompt)
            generations.append([Generation(text=text)])
        return LLMResult(generations=generations)

    def _analyze(self, prompt: str) -> str:
        """Parse prompt context and generate structured JSON analysis."""
        
        # ── 1. Intercept Distributed Trace Requests ──
        trace_id = self._extract(prompt, "TRACE_ID")
        if trace_id:
            return json.dumps({
                "root_cause": "The deepest node in the trace (payment-service or inventory-service) failed due to an external dependency timeout, causing parent services to fail via broken HTTP connections.",
                "risk_level": "high",
                "risk_summary": "Cascading distributed failure detected. The failure originated at the bottom of the stack and propagated upward, resulting in a dropped order.",
                "recommended_fixes": [
                    "Implement circuit breakers in the parent services to fail fast.",
                    "Ensure the root dependency has proper retry logic with exponential backoff.",
                    "Add dead-letter queues to catch dropped orders during async transitions."
                ],
                "remediation_actions": [
                    "Check external API status pages (e.g., Stripe, Warehouse).",
                    "Manually replay the failed order sequence.",
                    "Review timeout configurations on internal inter-service calls."
                ],
                "confidence": 0.95
            })

        # ── 2. Standard Aggregated Analysis (Existing Logic) ──
        error_type = self._extract(prompt, "ERROR_TYPE")
        service = self._extract(prompt, "SERVICE")
        count = int(self._extract(prompt, "COUNT") or "1")

        kb = ANALYSIS_KB.get(error_type, DEFAULT_ANALYSIS)
        cause = random.choice(kb["causes"])
        fixes = random.sample(kb["fixes"], min(3, len(kb["fixes"])))
        actions = kb["actions"][:3]
        conf_min, conf_max = kb["risk_range"]
        confidence = round(random.uniform(conf_min, conf_max), 2)

        if count >= 50 or error_type in ("DatabaseConnectionError", "DependencyFailure"):
            risk = "critical" if count >= 80 else "high"
        elif count >= 20:
            risk = "high" if error_type == "TimeoutError" else "medium"
        else:
            risk = "medium" if count >= 10 else "low"

        risk_summaries = {
            "critical": f"{service} is critically impaired — {count} failures indicate a systemic outage affecting all users.",
            "high": f"{service} is degraded — {count} failures are impacting a significant portion of traffic.",
            "medium": f"{service} is experiencing elevated errors — {count} failures warrant monitoring and investigation.",
            "low": f"{service} shows intermittent errors — {count} failures are within tolerable bounds but should be tracked.",
        }

        return json.dumps({
            "root_cause": cause,
            "risk_level": risk,
            "risk_summary": risk_summaries[risk],
            "recommended_fixes": fixes,
            "remediation_actions": actions,
            "confidence": confidence,
        })

    def _extract(self, prompt: str, key: str) -> str:
        for line in prompt.splitlines():
            if line.startswith(f"{key}:"):
                return line[len(key) + 1:].strip()
        return ""
