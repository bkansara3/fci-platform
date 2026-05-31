import json
import time
from datetime import datetime, timezone
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from app.ai.mock_llm import MockFCILLM

# ── State schema ────────────────────────────────────────────────────────────
class FCIState(TypedDict):
    # inputs (Standard Aggregated)
    service_name: str
    error_type: str
    failures: list[dict]
    
    # inputs (Distributed Trace additions)
    trace_id: str | None
    trace_tree: list[dict] | None

    # computed by planner
    patterns: list[str]
    failure_rate_per_hour: float
    peak_hour: int
    affected_endpoints: list[str]

    # computed by analyzer (LLM output)
    root_cause: str
    risk_level: str
    risk_summary: str
    recommended_fixes: list[str]
    remediation_actions: list[str]
    confidence: float

    # computed by risk_assessor
    blast_radius: str
    escalating: bool
    mttr_estimate: str

    # execution trace (for UI)
    trace: list[dict]

def _trace(state: FCIState, node: str, output: dict) -> list[dict]:
    return state.get("trace", []) + [{
        "node": node,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output": output,
    }]

# ── Node 1: Planner ──────────────────────────────────────────────────────────
def planner(state: FCIState) -> FCIState:
    """Identify failure patterns or map out a distributed trace tree."""
    
    # ── Path A: Distributed Trace Analysis ──
    if state.get("trace_id") and state.get("trace_tree"):
        tree = state["trace_tree"]
        patterns = [
            f"Cascading failure detected for order trace {state['trace_id']}",
            f"Impacted {len(tree)} top-level operations.",
            "Failure propagated through parent-child span relationships."
        ]
        out = {"patterns": patterns, "mode": "distributed_trace"}
        return {
            **state,
            "patterns": patterns,
            "failure_rate_per_hour": 1.0, # Not applicable for single trace
            "peak_hour": datetime.now(timezone.utc).hour,
            "affected_endpoints": [t.get("endpoint", "") for t in tree],
            "trace": _trace(state, "planner", out),
        }

    # ── Path B: Standard Aggregated Analysis ──
    failures = state["failures"]
    n = len(failures)
    hour_counts: dict[int, int] = {}
    
    for f in failures:
        ts = f.get("timestamp")
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                hour_counts[dt.hour] = hour_counts.get(dt.hour, 0) + 1
            except Exception:
                pass

    peak_hour = max(hour_counts, key=lambda h: hour_counts[h]) if hour_counts else 12
    total_hours = len(hour_counts) or 1
    rate = round(n / total_hours, 2)
    endpoints = list({f.get("endpoint", "/unknown") for f in failures})[:5]

    patterns = [f"Detected {n} failures across {len(endpoints)} endpoints"]
    if rate > 10: patterns.append(f"High failure rate: {rate}/hr — possible cascading failure")
    elif rate > 5: patterns.append(f"Elevated failure rate: {rate}/hr — sustained degradation")
    
    out = {"patterns": patterns, "rate": rate, "peak_hour": peak_hour, "endpoints": endpoints}
    return {
        **state,
        "patterns": patterns,
        "failure_rate_per_hour": rate,
        "peak_hour": peak_hour,
        "affected_endpoints": endpoints,
        "trace": _trace(state, "planner", out),
    }

# ── Node 2: Analyzer (LLM) ───────────────────────────────────────────────────
_llm = MockFCILLM()

def analyzer(state: FCIState) -> FCIState:
    """Call the LLM with structured context to get root-cause analysis."""
    
    if state.get("trace_id"):
        prompt = (
            f"TRACE_ID: {state['trace_id']}\n"
            f"TRACE_TREE_JSON: {json.dumps(state['trace_tree'])}\n"
            "You are a Principal SRE. Analyze this distributed trace JSON. "
            "Identify the deepest child node that failed first (the root cause) "
            "and explain how it cascaded up to the parent services."
        )
    else:
        prompt = (
            f"SERVICE: {state['service_name']}\n"
            f"ERROR_TYPE: {state['error_type']}\n"
            f"COUNT: {len(state['failures'])}\n"
            f"RATE_PER_HOUR: {state['failure_rate_per_hour']}\n"
            f"PATTERNS: {'; '.join(state['patterns'])}\n"
            f"ENDPOINTS: {', '.join(state['affected_endpoints'])}\n"
            "Analyze this failure group and respond with a JSON object."
        )

    raw = _llm.invoke(prompt)
    result = json.loads(raw)

    out = {
        "root_cause": result["root_cause"][:120] + "...",
        "risk_level": result["risk_level"],
        "confidence": result["confidence"],
    }
    
    return {
        **state,
        "root_cause": result["root_cause"],
        "risk_level": result["risk_level"],
        "risk_summary": result["risk_summary"],
        "recommended_fixes": result["recommended_fixes"],
        "remediation_actions": result["remediation_actions"],
        "confidence": result["confidence"],
        "trace": _trace(state, "analyzer", out),
    }

# ── Node 3 & 4 remain unchanged... ───────────────────────────────────────────
def risk_assessor(state: FCIState) -> FCIState:
    n = len(state.get("failures", [])) or 1
    rate = state["failure_rate_per_hour"]
    risk = state["risk_level"]

    blast_map = {
        "critical": "All users of this service — immediate action required",
        "high": "~30–60% of traffic affected — significant user impact",
        "medium": "~10–30% of traffic affected — degraded experience for some users",
        "low": "Minimal impact — <10% of traffic affected",
    }
    
    # If this is a trace analysis, blast radius is specific to the order
    if state.get("trace_id"):
        blast_radius = "Single Distributed Transaction (Order Flow)"
        escalating = False
        mttr = "Requires manual intervention for this specific order"
    else:
        blast_radius = blast_map.get(risk, "Unknown impact scope")
        escalating = rate > 8.0
        mttr_map = {
            "critical": "< 30 minutes",
            "high": "30–60 minutes",
            "medium": "1–4 hours",
            "low": "Next business day",
        }
        mttr = mttr_map.get(risk, "Unknown")

    out = {"blast_radius": blast_radius, "escalating": escalating, "mttr": mttr}
    return {
        **state,
        "blast_radius": blast_radius,
        "escalating": escalating,
        "mttr_estimate": mttr,
        "trace": _trace(state, "risk_assessor", out),
    }

def synthesizer(state: FCIState) -> FCIState:
    enriched_summary = (
        f"{state['risk_summary']} "
        f"Blast radius: {state['blast_radius']}. "
        f"{'⚠ Failure rate is escalating.' if state['escalating'] else ''} "
        f"Estimated resolution time: {state['mttr_estimate']}."
    )
    out = {"final_risk_summary": enriched_summary, "pipeline": "complete"}
    return {
        **state,
        "risk_summary": enriched_summary,
        "trace": _trace(state, "synthesizer", out),
    }

def build_fci_graph():
    graph = StateGraph(FCIState)
    graph.add_node("planner", planner)
    graph.add_node("analyzer", analyzer)
    graph.add_node("risk_assessor", risk_assessor)
    graph.add_node("synthesizer", synthesizer)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "analyzer")
    graph.add_edge("analyzer", "risk_assessor")
    graph.add_edge("risk_assessor", "synthesizer")
    graph.add_edge("synthesizer", END)
    return graph.compile()

fci_graph = build_fci_graph()

def run_fci_pipeline(
    service_name: str = "", 
    error_type: str = "", 
    failures: list = None,
    trace_id: str = None,
    trace_tree: list = None
) -> dict:
    """Entry point updated to support both modes."""
    initial_state: FCIState = {
        "service_name": service_name,
        "error_type": error_type,
        "failures": failures or [],
        "trace_id": trace_id,
        "trace_tree": trace_tree,
        "patterns": [],
        "failure_rate_per_hour": 0.0,
        "peak_hour": 0,
        "affected_endpoints": [],
        "root_cause": "",
        "risk_level": "medium",
        "risk_summary": "",
        "recommended_fixes": [],
        "remediation_actions": [],
        "confidence": 0.0,
        "blast_radius": "",
        "escalating": False,
        "mttr_estimate": "",
        "trace": [],
    }
    return fci_graph.invoke(initial_state)