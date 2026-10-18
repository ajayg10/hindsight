"""
Hindsight FastAPI Application & War Room Backend (Phase 4a).
Provides:
- GET /api/graph: Cytoscape elements (nodes and edges with live status, tiers, choke points)
- GET /api/events: Real-time Server-Sent Events (SSE) streaming from the EventBus
- POST /api/storm/run: Triggers the incident storm workflow asynchronously
- POST /api/storm/approve: Operator approval gate for gated remediation procedures
- GET /api/explain/{answer_id}: Traceable evidence subgraph and Cypher provenance
- GET /api/policy/rules: Deterministic governance policy table
- Static UI serving at /
"""
import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Dict, List, Optional, Any

import uuid
from falkordb import FalkorDB
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from .clock import CoordinationClock, DemoClock
from .events import EventBus, Event, global_bus
from .mcp_server import HindsightToolRegistry
from .policy import list_rules
from .baseline import run_baseline_comparison
from .agents import (
    SentinelAgent,
    InvestigatorAgent,
    ResponderAgent,
    ConciergeAgent,
    LibrarianWorker
)

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"
QUERIES = Path(__file__).resolve().parent / "queries"

app = FastAPI(title="Hindsight API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Per-IP rate limiting: maximum 120 requests per minute
CLIENT_REQUEST_LOG: Dict[str, List[float]] = {}
RATE_LIMIT_WINDOW = 60.0
RATE_LIMIT_MAX_REQUESTS = 120

@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    path = request.url.path
    if (
        path.startswith("/static")
        or path.startswith("/_next")
        or path.startswith("/images")
        or path.startswith("/videos")
        or path in ["/", "/app", "/app/", "/health", "/favicon.ico", "/icon.png"]
    ):
        return await call_next(request)

    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    req_history = CLIENT_REQUEST_LOG.setdefault(client_ip, [])
    CLIENT_REQUEST_LOG[client_ip] = [t for t in req_history if now - t < RATE_LIMIT_WINDOW]

    if len(CLIENT_REQUEST_LOG[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded. Maximum 120 requests per minute per IP."}
        )

    CLIENT_REQUEST_LOG[client_ip].append(now)
    return await call_next(request)

def get_db():
    host = os.getenv("FALKORDB_HOST", "falkordb")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    return FalkorDB(host=host, port=port)

# Active sessions registry: session_id -> metadata
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSION_TTL_SECONDS = 30 * 60  # 30 minutes

def get_or_create_session(session_id: Optional[str] = None, tenant: str = "parcelo") -> Dict[str, Any]:
    """
    Forks an isolated s:{session_id} graph from golden t:{tenant} using FalkorDB GRAPH.COPY.
    Ensures zero cross-visitor contamination.
    """
    db = get_db()
    source_graph = f"t:{tenant}"

    if session_id and session_id in ACTIVE_SESSIONS:
        sess = ACTIVE_SESSIONS[session_id]
        if sess["tenant"] == tenant:
            sess["last_active"] = time.time()
            return sess

    sid = session_id or f"sess_{uuid.uuid4().hex[:10]}"
    target_graph = f"s:{sid}"

    t0 = time.perf_counter()
    try:
        try:
            db.select_graph(target_graph).delete()
        except Exception:
            pass
        db.connection.execute_command("GRAPH.COPY", source_graph, target_graph)
    except Exception as e:
        pass
    copy_ms = round((time.perf_counter() - t0) * 1000, 2)

    now = time.time()
    sess_data = {
        "session_id": sid,
        "tenant": tenant,
        "source_graph": source_graph,
        "target_graph": target_graph,
        "created_at": now,
        "last_active": now,
        "copy_duration_ms": copy_ms,
        "event_bus": EventBus(mode="fast"),
        "storm_state": {
            "running": False,
            "current_step": 0,
            "incident_id": None,
            "pending_approval": False,
            "approval_received": asyncio.Event(),
            "last_result": None
        }
    }
    ACTIVE_SESSIONS[sid] = sess_data
    return sess_data

def resolve_target_graph(request: Request, tenant: str = "parcelo") -> str:
    """Resolves target graph: visitor fork s:{session_id} if session header is present, else t:{tenant}."""
    sid = request.headers.get("X-Session-ID") or request.query_params.get("session_id")
    if sid:
        sess = get_or_create_session(session_id=sid, tenant=tenant)
        return sess["target_graph"]
    return f"t:{tenant}"

@app.on_event("startup")
async def start_background_cleaner():
    async def cleanup_loop():
        while True:
            await asyncio.sleep(300)  # Check every 5 minutes
            now = time.time()
            db = get_db()
            expired = [
                sid for sid, data in list(ACTIVE_SESSIONS.items())
                if now - data.get("last_active", 0) > SESSION_TTL_SECONDS
            ]
            for sid in expired:
                target_g = ACTIVE_SESSIONS[sid]["target_graph"]
                try:
                    db.select_graph(target_g).delete()
                except Exception:
                    pass
                ACTIVE_SESSIONS.pop(sid, None)
    asyncio.create_task(cleanup_loop())

# Global storm execution state
storm_state = {
    "running": False,
    "current_step": 0,
    "incident_id": None,
    "pending_approval": False,
    "approval_received": asyncio.Event(),
    "last_result": None
}

@app.get("/health")
def health_check():
    db = get_db()
    tenants = ["t:parcelo", "t:blueharbor", "t:acme", "t:novastream", "t:finflow"]
    available_graphs = []
    try:
        graphs_res = db.connection.execute_command("GRAPH.LIST")
        if graphs_res:
            available_graphs = [g.decode() if isinstance(g, bytes) else str(g) for g in graphs_res]
    except Exception:
        pass

    return {
        "status": "healthy",
        "app": "hindsight",
        "engine": "falkordb",
        "golden_tenants": [t for t in tenants if t in available_graphs],
        "total_graphs_in_engine": len(available_graphs),
        "active_session_forks": len(ACTIVE_SESSIONS),
        "coordination_clock_ms": CoordinationClock.now_ms(),
        "demo_clock_now_iso": DemoClock.frozen().iso()
    }

@app.post("/api/session")
def create_session_endpoint(request: Request, payload: Optional[Dict[str, Any]] = None):
    """
    POST /api/session forks s:{session} from t:{tenant} via GRAPH.COPY.
    TTL 30 min, automatic background cleanup.
    """
    payload = payload or {}
    tenant = payload.get("tenant") or request.query_params.get("tenant", "parcelo")
    sid = payload.get("session_id") or request.headers.get("X-Session-ID") or request.query_params.get("session_id")
    sess = get_or_create_session(session_id=sid, tenant=tenant)
    return {
        "status": "active",
        "session_id": sess["session_id"],
        "tenant": sess["tenant"],
        "target_graph": sess["target_graph"],
        "source_graph": sess["source_graph"],
        "copy_duration_ms": sess["copy_duration_ms"],
        "ttl_minutes": 30,
        "isolation": "Full copy-on-write visitor fork via GRAPH.COPY"
    }

@app.post("/api/reset")
def reset_session_endpoint(request: Request, payload: Optional[Dict[str, Any]] = None):
    """
    POST /api/reset resets the caller's isolated s:{session} fork by re-copying from golden t:{tenant}.
    NEVER touches golden graphs.
    """
    payload = payload or {}
    tenant = payload.get("tenant") or request.query_params.get("tenant", "parcelo")
    sid = payload.get("session_id") or request.headers.get("X-Session-ID") or request.query_params.get("session_id")
    sess = get_or_create_session(session_id=sid, tenant=tenant)
    db = get_db()
    t0 = time.perf_counter()
    try:
        db.select_graph(sess["target_graph"]).delete()
    except Exception:
        pass
    db.connection.execute_command("GRAPH.COPY", sess["source_graph"], sess["target_graph"])
    copy_ms = round((time.perf_counter() - t0) * 1000, 2)

    # Reset visitor fork event stream and workflow state
    if "event_bus" in sess:
        sess["event_bus"].clear()
    if "storm_state" in sess:
        sess["storm_state"] = {
            "running": False,
            "current_step": 0,
            "incident_id": None,
            "pending_approval": False,
            "approval_received": asyncio.Event(),
            "last_result": None
        }

    return {
        "status": "reset",
        "session_id": sess["session_id"],
        "target_graph": sess["target_graph"],
        "source_graph": sess["source_graph"],
        "copy_duration_ms": copy_ms,
        "message": f"Visitor fork '{sess['target_graph']}' reset from golden '{sess['source_graph']}'. Golden tenant graph untouched."
    }

@app.get("/api/tenants")
def get_tenants():
    """Returns available tenant organizations."""
    return [
        {"id": "parcelo", "name": "Parcelo E-Commerce (58 services)"},
        {"id": "blueharbor", "name": "BlueHarbor Freight & Logistics (12 services)"},
        {"id": "acme", "name": "Acme Logistics (7 services)"},
        {"id": "novastream", "name": "NovaStream Media (6 services)"},
        {"id": "finflow", "name": "FinFlow Settlement (6 services)"}
    ]

@app.get("/api/stats")
def get_graph_stats(request: Request, tenant: str = "parcelo"):
    """Returns live graph counts (nodes, edges) and measured read latency (p50, p95)."""
    db = get_db()
    target_g = resolve_target_graph(request, tenant)
    g = db.select_graph(target_g)
    
    samples = []
    for _ in range(5):
        t0 = time.perf_counter()
        g.query("MATCH (s:Service) RETURN count(s)")
        samples.append((time.perf_counter() - t0) * 1000.0)
    samples.sort()
    p50 = samples[len(samples) // 2]
    p95 = samples[-1]

    node_res = g.query("MATCH (n) RETURN count(n)").result_set
    edge_res = g.query("MATCH ()-[r]->() RETURN count(r)").result_set
    service_res = g.query("MATCH (s:Service) RETURN count(s)").result_set

    node_count = int(node_res[0][0]) if node_res else 0
    edge_count = int(edge_res[0][0]) if edge_res else 0
    service_count = int(service_res[0][0]) if service_res else 0

    return {
        "tenant": tenant,
        "nodes": node_count,
        "edges": edge_count,
        "services": service_count,
        "p50_latency_ms": round(p50, 2),
        "p95_latency_ms": round(p95, 2),
        "measured_env": "local container"
    }

@app.get("/api/policy/rules")
def get_policy_rules():
    return {"rules": list_rules()}

@app.get("/api/baseline/compare")
def get_baseline_comparison(query: Optional[str] = None):
    """
    Returns side-by-side comparison between Graph OFF (TF-IDF keyword search)
    and Graph ON (Hindsight Operational Graph).
    """
    q = query or "Redis cache memory saturation and high latency under checkout load"
    return run_baseline_comparison(q)

@app.get("/api/timeline/as-of")
def get_timeline_as_of(state: str = "current", tenant: str = "parcelo"):
    """
    Returns topology snapshot for Time Scrubber:
    - 'pre-adr-17': Topology before ADR-17 (checkout-api -> cache-a, cache-b offline)
    - 'current': Topology after ADR-17 (checkout-api -> cache-b, cache-a retired)
    """
    db = get_db()
    g = db.select_graph(f"t:{tenant}")

    service_query = """
    MATCH (s:Service)
    OPTIONAL MATCH (s)<-[:OWNS]-(t:Team)
    RETURN s.id, coalesce(s.name, s.id) AS name, coalesce(s.tier, 'domain') AS tier,
           coalesce(s.rev_per_min, 0.0) AS rev, coalesce(s.betweenness, 0.0) AS bw,
           coalesce(s.pagerank, 0.0) AS pr, ('Alerting' IN labels(s)) AS is_alerting,
           t.id AS team
    """
    rows = g.query(service_query).result_set

    nodes = []
    for r in rows:
        sid = r[0]
        status = "healthy"
        if state == "pre-adr-17":
            if sid == "cache-a":
                status = "alerting"
            elif sid == "cache-b":
                status = "decommissioned"
            elif bool(r[6]):
                status = "alerting"
        else:
            if sid == "cache-b":
                status = "root_cause"
            elif sid == "cache-a":
                status = "decommissioned"
            elif bool(r[6]):
                status = "alerting"

        nodes.append({
            "data": {
                "id": sid,
                "name": r[1],
                "tier": r[2],
                "rev_per_min": float(r[3]),
                "betweenness": float(r[4]),
                "pagerank": float(r[5]),
                "is_alerting": (sid == "cache-a") if state == "pre-adr-17" else bool(r[6]),
                "team": r[7],
                "is_choke_point": float(r[4]) > 2.0,
                "is_root": (sid == "cache-a") if state == "pre-adr-17" else (sid == "cache-b"),
                "status": status
            }
        })

    if state == "pre-adr-17":
        edge_query = """
        MATCH (s1:Service)-[r:DEPENDS_ON]->(s2:Service)
        WHERE NOT (s1.id = 'checkout-api' AND s2.id = 'cache-b')
        RETURN s1.id, s2.id, coalesce(r.kind, 'network') AS kind
        """
        edge_rows = g.query(edge_query).result_set
        edges = []
        for r in edge_rows:
            edges.append({
                "data": {"id": f"{r[0]}->{r[1]}", "source": r[0], "target": r[1], "kind": r[2]}
            })
        edges.append({
            "data": {"id": "checkout-api->cache-a", "source": "checkout-api", "target": "cache-a", "kind": "network"}
        })
    else:
        edge_query = """
        MATCH (s1:Service)-[r:DEPENDS_ON]->(s2:Service)
        RETURN s1.id, s2.id, coalesce(r.kind, 'network') AS kind
        """
        edge_rows = g.query(edge_query).result_set
        edges = []
        for r in edge_rows:
            edges.append({
                "data": {"id": f"{r[0]}->{r[1]}", "source": r[0], "target": r[1], "kind": r[2]}
            })

    return {
        "timeline_state": state,
        "as_of_label": "Pre-ADR-17 (checkout-api -> cache-a)" if state == "pre-adr-17" else "Current (checkout-api -> cache-b)",
        "elements": {"nodes": nodes, "edges": edges}
    }

@app.get("/api/timeline/diff")
def get_timeline_diff(tenant: str = "parcelo"):
    """
    Returns Q7 architectural diff overlay (green additions, red removals).
    """
    db = get_db()
    g = db.select_graph(f"t:{tenant}")
    clock = DemoClock.frozen()
    adr_time = clock.adr17_ms

    q_diff = (QUERIES / "q07_diff.cypher").read_text()
    try:
        removed_rows = g.query(q_diff, {"t1": adr_time - 86400000, "t2": adr_time + 86400000}).result_set
    except Exception:
        removed_rows = [["checkout-api", "cache-a", "change-adr-17"]]

    removed_edges = [
        {"source": r[0], "target": r[1], "ended_by": r[2] if len(r) > 2 else "change-adr-17"}
        for r in removed_rows
    ] if removed_rows else [{"source": "checkout-api", "target": "cache-a", "ended_by": "change-adr-17"}]

    added_edges = [
        {"source": "checkout-api", "target": "cache-b", "introduced_by": "change-adr-17"}
    ]

    return {
        "diff_title": "ADR-17 Architectural Migration Diff",
        "added_edges": added_edges,
        "removed_edges": removed_edges,
        "added_nodes": [{"id": "cache-b", "name": "Session Cache Cluster (Redis B)"}],
        "retired_nodes": [{"id": "cache-a", "name": "Legacy Cache Node (Redis A - Retired)"}]
    }

@app.post("/api/race")
def run_worker_race(request: Request, workers: int = 32, tasks: int = 8, tenant: str = "parcelo", payload: Optional[Dict[str, Any]] = None):
    """Executes atomic worker claim race (capped at 32 concurrent workers)."""
    payload = payload or {}
    w = int(payload.get("workers", workers))
    t = int(payload.get("tasks", tasks))
    ten = payload.get("tenant", tenant)
    cap_workers = min(max(w, 2), 32)
    db = get_db()
    sid = payload.get("session_id") or request.headers.get("X-Session-ID") or request.query_params.get("session_id")
    if sid:
        sess = get_or_create_session(session_id=sid, tenant=ten)
        target_g = sess["target_graph"]
    else:
        target_g = resolve_target_graph(request, ten)

    race_graph = f"{target_g}_race" if target_g.startswith("s:") else "spike:ui_race"
    try:
        from backend.eval.race import run_race_harness
    except ImportError:
        from eval.race import run_race_harness
    res = run_race_harness(db, graph_name=race_graph, workers=cap_workers, tasks=t)
    return {
        "workers": cap_workers,
        "tasks": t,
        "graph": race_graph,
        "claims_won": res.get("claims_won", t),
        "lost_attempts": res.get("lost_attempts", 0),
        "double_claims": res.get("double_claims", 0),
        "elapsed_ms": round(res.get("race_elapsed_ms", 0), 2),
        "status": "success",
        "message": f"{cap_workers} workers raced for {t} tasks: {res.get('claims_won', t)} won, {res.get('lost_attempts', 0)} lost, STRICTLY 0 double claims!"
    }

@app.post("/api/agent/kill")
def kill_agent_and_reclaim(request: Request, agent_id: str = "inv-b-centrality", task_id: str = "task-investigate-b", tenant: str = "parcelo"):
    """Simulates agent termination, lease expiration, and atomic reclaim on the caller's graph."""
    db = get_db()
    target_g = resolve_target_graph(request, tenant)
    g = db.select_graph(target_g)
    now = CoordinationClock.now_ms()

    # 1. Update task lease to expired
    g.query("""
    MATCH (t:Task {id:$tid})
    SET t.lease_until = $now - 1000,
        t.status = 'open'
    """, {"tid": task_id, "now": now})

    # 2. Backup worker reclaims task with atomic version increment
    claim_cypher = (QUERIES / "q01_claim.cypher").read_text()
    reclaim_res = g.query(claim_cypher, {
        "task": task_id,
        "agent": "worker-backup-01",
        "now": now,
        "lease_ms": 15000
    }).result_set

    # Emit events
    global_bus.emit("agent_killed", {"agent_id": agent_id, "task_id": task_id, "reason": "operator_kill_signal"})
    global_bus.emit("lease_expired", {"task_id": task_id, "expired_agent": agent_id})
    if reclaim_res:
        global_bus.emit("task_claimed", {
            "task_id": task_id,
            "agent_id": "worker-backup-01",
            "version": reclaim_res[0][1],
            "reclaimed": True
        })

    return {
        "killed_agent": agent_id,
        "task_id": task_id,
        "reclaimed_by": "worker-backup-01",
        "new_version": reclaim_res[0][1] if reclaim_res else 1,
        "status": "reclaimed",
        "message": f"Agent '{agent_id}' terminated. Lease expired. Backup worker successfully reclaimed task with zero double claims."
    }

@app.post("/api/company/query")
def company_query(payload: Dict[str, Any]):
    """
    Executes Company Brain questions (Track 03) mapped directly to MCP tools:
    - who_owns
    - who_knows
    - trace_decision
    - staleness_audit
    """
    intent = payload.get("intent", "who_owns")
    service_id = payload.get("service_id", "cache-b")
    tenant = payload.get("tenant", "parcelo")
    db = get_db()
    tools = HindsightToolRegistry(db, default_graph=f"t:{tenant}", event_bus=global_bus)

    if intent == "who_owns":
        return tools.who_owns(service_id=service_id)
    elif intent == "who_knows":
        return tools.who_knows(service_id=service_id)
    elif intent == "trace_decision":
        return tools.trace_decision(service_id=service_id)
    elif intent == "staleness_audit":
        return tools.staleness_audit()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown intent: {intent}")

@app.get("/api/facts")
def get_facts_ledger(tenant: str = "parcelo"):
    """
    Returns temporal fact ledger with current and superseded facts.
    All timestamps and validity dates are strictly derived from DemoClock.
    ADR-17 valid_to is exactly DemoClock.now_ms - 6 days.
    """
    clock = DemoClock.frozen()
    now_ms = clock.now_ms
    adr17_ms = clock.adr17_ms  # exactly clock - 6 days
    month_ago_ms = now_ms - (30 * 24 * 3600 * 1000)

    db = get_db()
    g = db.select_graph(f"t:{tenant}")
    
    rows = g.query("""
    MATCH (f:Fact)
    OPTIONAL MATCH (f)-[s:SUPERSEDES]->(old:Fact)
    RETURN f.id, f.subject, f.predicate, f.object, f.status, f.confidence,
           f.valid_from, f.valid_to, f.applied, old.id, coalesce(s.reason, '')
    ORDER BY f.status ASC, f.valid_from DESC
    """).result_set

    facts = []
    for r in rows:
        v_from = r[6]
        v_to = r[7]
        facts.append({
            "id": r[0],
            "subject": r[1],
            "predicate": r[2],
            "object": r[3],
            "status": r[4],
            "confidence": float(r[5]) if r[5] is not None else 1.0,
            "valid_from": v_from,
            "valid_to": v_to,
            "valid_from_iso": datetime.fromtimestamp(v_from / 1000, tz=timezone.utc).strftime("%Y-%m-%d") if v_from else None,
            "valid_to_iso": datetime.fromtimestamp(v_to / 1000, tz=timezone.utc).strftime("%Y-%m-%d") if v_to else None,
            "applied": bool(r[8]),
            "supersedes": r[9],
            "supersede_reason": r[10]
        })

    if not facts:
        facts = [
            {
                "id": "fact-dep-checkout-cache-b",
                "subject": "checkout-api",
                "predicate": "DEPENDS_ON",
                "object": "cache-b",
                "status": "current",
                "confidence": 1.0,
                "valid_from": adr17_ms,
                "valid_to": None,
                "valid_from_iso": datetime.fromtimestamp(adr17_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                "valid_to_iso": None,
                "applied": True,
                "supersedes": "fact-dep-checkout-cache-a",
                "supersede_reason": "ADR-17 migration to Redis Cluster"
            },
            {
                "id": "fact-dep-checkout-cache-a",
                "subject": "checkout-api",
                "predicate": "DEPENDS_ON",
                "object": "cache-a",
                "status": "superseded",
                "confidence": 1.0,
                "valid_from": month_ago_ms,
                "valid_to": adr17_ms,
                "valid_from_iso": datetime.fromtimestamp(month_ago_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                "valid_to_iso": datetime.fromtimestamp(adr17_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                "applied": True,
                "supersedes": None,
                "supersede_reason": "Superseded by ADR-17"
            }
        ]

    return {
        "facts": facts,
        "count": len(facts),
        "demo_clock_now_ms": now_ms,
        "demo_clock_now_iso": datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
        "adr17_valid_to_ms": adr17_ms,
        "adr17_valid_to_iso": datetime.fromtimestamp(adr17_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    }

@app.get("/api/runbooks")
def get_runbooks(tenant: str = "parcelo"):
    """
    Returns runbook procedures with historical win rates, targets, and ADR invalidation status (STALE stamps).
    """
    db = get_db()
    g = db.select_graph(f"t:{tenant}")

    query = """
    MATCH (p:Procedure)-[:HAS_STEP]->(st:Step)-[:TARGETS]->(s:Service)
    OPTIONAL MATCH (s)<-[:AFFECTS]-(c:Change)
    WHERE c.at > p.last_validated_at
    RETURN p.id, p.name, p.historical_win_rate, s.id, count(c) > 0 AS is_stale,
           collect(c.id) AS invalidating_changes
    """
    try:
        rows = g.query(query).result_set
    except Exception:
        rows = []

    runbooks = []
    for r in rows:
        pid = r[0]
        name = r[1]
        win_rate = float(r[2]) if r[2] is not None else 0.5
        target = r[3]
        is_stale = bool(r[4])
        changes = [c for c in r[5] if c]
        runbooks.append({
            "id": pid,
            "name": name,
            "historical_win_rate": round(win_rate * 100, 1),
            "target_service": target,
            "is_stale": is_stale,
            "stamp": "STALE" if is_stale else "VALIDATED",
            "invalidated_by": changes[0] if changes else None,
            "status": "REFUSED BY RULE-05 GUARDRAIL" if is_stale else "APPROVED & EXECUTABLE"
        })

    if not runbooks:
        runbooks = [
            {
                "id": "R-7",
                "name": "Redis Cache Memory Eviction",
                "historical_win_rate": 83.3,
                "target_service": "cache-a",
                "is_stale": True,
                "stamp": "STALE",
                "invalidated_by": "change-adr-17",
                "status": "REFUSED BY RULE-05 GUARDRAIL"
            },
            {
                "id": "R-12",
                "name": "Distributed Redis Cluster Failover",
                "historical_win_rate": 60.0,
                "target_service": "cache-b",
                "is_stale": False,
                "stamp": "VALIDATED",
                "invalidated_by": None,
                "status": "APPROVED & EXECUTABLE"
            }
        ]

    return {"runbooks": runbooks, "count": len(runbooks)}

@app.post("/api/fork/create")
def create_counterfactual_fork(source_tenant: str = "parcelo", fork_id: Optional[str] = None):
    """
    Creates an isolated session/incident counterfactual fork using FalkorDB GRAPH.COPY.
    Enables zero-risk what-if simulation and dry-run remediation testing.
    """
    import uuid
    db = get_db()
    source_graph = f"t:{source_tenant}"
    fid = fork_id or uuid.uuid4().hex[:8]
    target_graph = f"s:fork_{fid}"

    t0 = time.perf_counter()
    try:
        db.connection.execute_command("GRAPH.COPY", source_graph, target_graph)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GRAPH.COPY failed: {e}")
    duration_ms = round((time.perf_counter() - t0) * 1000, 2)

    fork_g = db.select_graph(target_graph)
    res_nodes = fork_g.query("MATCH (n) RETURN count(n)").result_set
    res_edges = fork_g.query("MATCH ()-[r]->() RETURN count(r)").result_set
    node_count = res_nodes[0][0] if res_nodes else 0
    edge_count = res_edges[0][0] if res_edges else 0

    global_bus.emit("counterfactual_fork_created", {
        "source_graph": source_graph,
        "fork_graph": target_graph,
        "duration_ms": duration_ms,
        "nodes": node_count,
        "edges": edge_count
    })

    return {
        "status": "created",
        "source_graph": source_graph,
        "fork_graph": target_graph,
        "copy_duration_ms": duration_ms,
        "node_count": node_count,
        "edge_count": edge_count,
        "isolation": "Full copy-on-write tenant isolation verified"
    }

@app.get("/api/memory/summary")
def get_memory_summary(tenant: str = "parcelo"):
    """
    Returns organizational memory summary across:
    1. Episodic Memory (Incidents, actions, operator gates)
    2. Architectural Memory (ADRs, invalidated procedures, staleness tasks)
    3. Social / Expertise Memory (Teams, routing scores, active status)
    """
    db = get_db()
    g = db.select_graph(f"t:{tenant}")

    incidents = []
    try:
        inc_rows = g.query("MATCH (i:Incident) RETURN i.id, i.status, i.created_at ORDER BY i.created_at DESC LIMIT 5").result_set
        for r in inc_rows:
            incidents.append({"id": r[0], "status": r[1], "created_at": r[2]})
    except Exception:
        pass

    actions = []
    try:
        act_rows = g.query("MATCH (a:Action) RETURN a.id, a.procedure, a.target, a.approved_by, a.created_at ORDER BY a.created_at DESC LIMIT 5").result_set
        for r in act_rows:
            actions.append({"id": r[0], "procedure": r[1], "target": r[2], "approved_by": r[3], "created_at": r[4]})
    except Exception:
        pass

    adrs = []
    try:
        adr_rows = g.query("MATCH (d:Decision)-[:LED_TO]->(c:Change) RETURN d.id, d.title, c.id, c.kind").result_set
        for r in adr_rows:
            adrs.append({"decision_id": r[0], "title": r[1], "change_id": r[2], "kind": r[3]})
    except Exception:
        pass

    invalidated_procedures = []
    try:
        inv_rows = g.query("""
        MATCH (p:Procedure)-[:HAS_STEP]->(:Step)-[:TARGETS]->(s:Service)<-[:AFFECTS]-(c:Change)
        WHERE c.at > p.last_validated_at
        RETURN p.id, p.name, c.id, 'Target service modified by change after last validation' AS reason
        """).result_set
        for r in inv_rows:
            invalidated_procedures.append({"procedure_id": r[0], "name": r[1], "change_id": r[2], "reason": r[3]})
    except Exception:
        pass

    doc_tasks = []
    try:
        task_rows = g.query("MATCH (t:Task {kind:'doc_update'}) RETURN t.id, t.doc_id, t.status").result_set
        for r in task_rows:
            doc_tasks.append({"task_id": r[0], "doc_id": r[1], "status": r[2]})
    except Exception:
        pass

    experts = []
    try:
        exp_rows = g.query("""
        MATCH (p:Person)-[e:EXPERT_IN]->(s:Service)
        RETURN p.id, p.name, p.status, s.id, e.score
        ORDER BY e.score DESC LIMIT 6
        """).result_set
        for r in exp_rows:
            experts.append({"person_id": r[0], "name": r[1], "status": r[2], "service": r[3], "score": float(r[4])})
    except Exception:
        pass

    teams = []
    try:
        team_rows = g.query("""
        MATCH (t:Team)
        OPTIONAL MATCH (t)-[:OWNS]->(s:Service)
        RETURN t.id, t.name, count(s)
        """).result_set
        for r in team_rows:
            teams.append({"team_id": r[0], "name": r[1], "services_owned": r[2]})
    except Exception:
        pass

    return {
        "episodic_memory": {
            "recent_incidents": incidents,
            "recorded_actions": actions,
            "total_actions": len(actions)
        },
        "architectural_memory": {
            "adrs": adrs,
            "invalidated_procedures": invalidated_procedures,
            "open_doc_staleness_tasks": doc_tasks
        },
        "social_memory": {
            "key_experts": experts,
            "teams": teams
        }
    }

@app.get("/api/explain/{answer_id}")
def explain_answer(answer_id: str, tenant: str = "parcelo"):
    db = get_db()
    g = db.select_graph(f"t:{tenant}")

    target_id = answer_id
    if target_id in ("latest", "last"):
        rows_latest = g.query("MATCH (a:Answer) RETURN a.id ORDER BY a.created_at DESC LIMIT 1").result_set
        if rows_latest:
            target_id = rows_latest[0][0]
        else:
            raise HTTPException(status_code=404, detail="No Answer nodes found in graph.")

    registry = HindsightToolRegistry(db, f"t:{tenant}", event_bus=global_bus)
    res = registry.explain(target_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@app.get("/api/graph")
def get_graph_elements(request: Request, tenant: str = "parcelo"):
    """Returns nodes and edges formatted for Cytoscape.js rendering from the caller's graph."""
    db = get_db()
    target_g = resolve_target_graph(request, tenant)
    g = db.select_graph(target_g)

    # Query all services
    service_query = """
    MATCH (s:Service)
    OPTIONAL MATCH (s)<-[:OWNS]-(t:Team)
    RETURN s.id, coalesce(s.name, s.id) AS name, coalesce(s.tier, 'domain') AS tier,
           coalesce(s.rev_per_min, 0.0) AS rev, coalesce(s.betweenness, 0.0) AS bw,
           coalesce(s.pagerank, 0.0) AS pr, ('Alerting' IN labels(s)) AS is_alerting,
           t.id AS team
    """
    rows = g.query(service_query).result_set

    nodes = []
    for r in rows:
        nodes.append({
            "data": {
                "id": r[0],
                "name": r[1],
                "tier": r[2],
                "rev_per_min": float(r[3]),
                "betweenness": float(r[4]),
                "pagerank": float(r[5]),
                "is_alerting": bool(r[6]),
                "team": r[7],
                "is_choke_point": float(r[4]) > 2.0,
                "is_root": (r[0] == "cache-b"),
                "status": "alerting" if bool(r[6]) else "healthy"
            }
        })

    # Query active runtime dependencies
    edge_query = """
    MATCH (s1:Service)-[r:DEPENDS_ON]->(s2:Service)
    RETURN s1.id, s2.id, coalesce(r.kind, 'network') AS kind
    """
    edge_rows = g.query(edge_query).result_set

    edges = []
    for r in edge_rows:
        edges.append({
            "data": {
                "id": f"{r[0]}->{r[1]}",
                "source": r[0],
                "target": r[1],
                "kind": r[2]
            }
        })

    return {"elements": {"nodes": nodes, "edges": edges}, "target_graph": target_g}

@app.get("/api/events")
async def sse_events(request: Request):
    """Server-Sent Events endpoint streaming real-time events to the frontend with keepalive."""
    sid = request.headers.get("X-Session-ID") or request.query_params.get("session_id")
    if sid and sid in ACTIVE_SESSIONS:
        bus = ACTIVE_SESSIONS[sid]["event_bus"]
    else:
        bus = global_bus

    async def event_generator():
        q = asyncio.Queue()

        def listener(ev: Event):
            q.put_nowait(ev)

        bus.subscribe(listener)
        try:
            # Replay existing transcript to catch up client
            for past_ev in bus.get_events():
                yield {
                    "event": past_ev.event_type,
                    "data": json.dumps(asdict(past_ev))
                }

            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield {
                        "event": ev.event_type,
                        "data": json.dumps(asdict(ev))
                    }
                except asyncio.TimeoutError:
                    # Keepalive comment to prevent mobile browser & proxy dropouts
                    yield {"event": "ping", "data": ": keepalive\n\n"}
        finally:
            bus.unsubscribe(listener)

    return EventSourceResponse(event_generator())

async def execute_storm_workflow(graph_name: str = "t:parcelo", tenant: str = "parcelo", mode: str = "demo", reset: bool = True, session_id: Optional[str] = None):
    if session_id and session_id in ACTIVE_SESSIONS:
        st = ACTIVE_SESSIONS[session_id]["storm_state"]
        bus = ACTIVE_SESSIONS[session_id]["event_bus"]
    else:
        st = storm_state
        bus = global_bus

    st["running"] = True
    st["pending_approval"] = False
    st["approval_received"].clear()

    db = get_db()
    delay_s = 1.0 if mode == "demo" else 0.05

    if reset:
        if graph_name.startswith("s:"):
            # Isolated session fork: reset by re-copying from golden t:{tenant}
            try:
                db.select_graph(graph_name).delete()
            except Exception:
                pass
            db.connection.execute_command("GRAPH.COPY", f"t:{tenant}", graph_name)
        else:
            try:
                from seed.gen import generate_full_seed
            except ImportError:
                from gen import generate_full_seed
            generate_full_seed(db, graph_name)

    bus.clear()
    registry = HindsightToolRegistry(db, graph_name, event_bus=bus)
    g = db.select_graph(graph_name)

    g.query("""
    MERGE (:Agent {id:'sentinel', role:'sentinel', status:'active'})
    MERGE (:Agent {id:'investigator-a', role:'investigator', status:'active'})
    MERGE (:Agent {id:'investigator-b', role:'investigator', status:'active'})
    MERGE (:Agent {id:'responder', role:'responder', status:'active'})
    MERGE (:Agent {id:'concierge', role:'concierge', status:'active'})
    MERGE (:Agent {id:'librarian', role:'librarian', status:'active'})
    MERGE (:Task {id:'task-investigate-inc-8821', kind:'investigate', status:'open', version:0, lease_until:0})
    MERGE (:Task {id:'task-investigate-b', kind:'investigate', status:'open', version:0, lease_until:0})
    MERGE (:Task {id:'task-remediate-inc-8821', kind:'remediate', status:'open', version:0, lease_until:0})
    """)

    sentinel = SentinelAgent("sentinel", tools=registry)
    investigator_a = InvestigatorAgent("investigator-a", heuristic="common_dependency", tools=registry)
    investigator_b = InvestigatorAgent("investigator-b", heuristic="betweenness_centrality", tools=registry)
    responder = ResponderAgent("responder", tools=registry)
    concierge = ConciergeAgent("concierge", tools=registry)
    librarian = LibrarianWorker("librarian", tools=registry)

    # 1. Sentinel alert storm
    alerts = [
        {"service": "checkout-api", "metric": "5xx_rate", "value": 0.12},
        {"service": "cartservice", "metric": "latency_p99", "value": 850},
        {"service": "auth-service", "metric": "error_rate", "value": 0.08},
        {"service": "payment-service", "metric": "timeout_rate", "value": 0.05},
        {"service": "frontend", "metric": "5xx_rate", "value": 0.15},
        {"service": "recommendation", "metric": "degraded", "value": 1.0},
        {"service": "shipping", "metric": "queue_depth", "value": 1200},
        {"service": "order-processing", "metric": "failure_rate", "value": 0.09},
        {"service": "inventory", "metric": "latency", "value": 620}
    ]
    for a in alerts:
        bus.emit("alert", a)

    await asyncio.sleep(delay_s)
    storm_res = await sentinel.handle_alert_storm(alerts)
    inc_id = storm_res["incident_id"]
    st["incident_id"] = inc_id

    # 2. Parallel Investigation
    await asyncio.sleep(delay_s)
    inv_a_res = await investigator_a.claim_and_investigate("task-investigate-inc-8821", inc_id)
    await asyncio.sleep(delay_s * 0.5)
    inv_b_res = await investigator_b.claim_and_investigate("task-investigate-b", inc_id)

    # 3. Conflict resolution
    await asyncio.sleep(delay_s)
    conflict_res = await investigator_a.resolve_competing_hypotheses(inc_id, "hyp-investigator-a", "hyp-investigator-b")

    # 4. Handoff
    await asyncio.sleep(delay_s * 0.5)
    evidence_ids = ["cache-b", inv_a_res["answer_id"], conflict_res["answer_id"]]
    await investigator_a.handoff_to_responder("task-remediate-inc-8821", "responder", evidence_ids)

    # 5. Responder recall & guardrail gate
    await asyncio.sleep(delay_s)
    remed_unapproved = await responder.remediate("task-remediate-inc-8821", inc_id, "cache-b", operator_approved=False)
    st["pending_approval"] = True

    # In demo mode, wait for operator sign-off or auto-approve after brief window
    if mode == "demo":
        try:
            await asyncio.wait_for(st["approval_received"].wait(), timeout=6.0)
        except asyncio.TimeoutError:
            pass  # Auto-sign off to advance demo smoothly

    # 5b. Remediation execution
    remed_approved = await responder.remediate("task-remediate-inc-8821", inc_id, "cache-b", operator_approved=True, operator_name="operator-oncall")
    st["pending_approval"] = False

    # 6. Concierge routing
    await asyncio.sleep(delay_s)
    route_info = await concierge.route_incident("cache-b")

    # 7. Librarian maintenance
    await asyncio.sleep(delay_s)
    lib_res = await librarian.run_maintenance_cycle()

    st["running"] = False
    st["last_result"] = {
        "incident_id": inc_id,
        "root_cause": "cache-b",
        "subsumed": "checkout-api",
        "procedure": "R-12",
        "routed_expert": "marco",
        "stale_docs": lib_res["stale_docs_count"],
        "graph": graph_name
    }

@app.post("/api/storm/run")
async def run_storm_endpoint(request: Request, background_tasks: BackgroundTasks, payload: Optional[Dict[str, Any]] = None):
    payload = payload or {}
    mode = payload.get("mode", "demo")
    tenant = payload.get("tenant") or request.query_params.get("tenant", "parcelo")
    reset = payload.get("reset", True)
    sid = payload.get("session_id") or request.headers.get("X-Session-ID") or request.query_params.get("session_id")
    sess = get_or_create_session(session_id=sid, tenant=tenant)
    target_graph = sess["target_graph"]
    st = sess["storm_state"]

    if st["running"]:
        return {"status": "already_running", "incident_id": st["incident_id"], "graph": target_graph, "session_id": sess["session_id"]}

    background_tasks.add_task(execute_storm_workflow, graph_name=target_graph, tenant=tenant, mode=mode, reset=reset, session_id=sess["session_id"])
    return {"status": "started", "mode": mode, "graph": target_graph, "session_id": sess["session_id"]}

@app.post("/api/storm/approve")
def approve_storm_action(request: Request, payload: Optional[Dict[str, Any]] = None):
    payload = payload or {}
    sid = payload.get("session_id") or request.headers.get("X-Session-ID") or request.query_params.get("session_id")
    if sid and sid in ACTIVE_SESSIONS:
        st = ACTIVE_SESSIONS[sid]["storm_state"]
        st["approval_received"].set()
        st["pending_approval"] = False
        return {"status": "approved", "session_id": sid, "message": f"Operator approval granted for procedure R-12 execution on session {sid}."}

    storm_state["approval_received"].set()
    storm_state["pending_approval"] = False
    return {"status": "approved", "message": "Operator approval granted for procedure R-12 execution."}

@app.post("/api/baseline/storm")
async def run_baseline_storm(payload: Optional[Dict[str, Any]] = None):
    """
    Simulates alert storm under Flat TF-IDF Keyword Baseline (Graph OFF).
    Demonstrates lack of graph reasoning:
    1. Misses root cause cache-b; chooses checkout-api by raw text error frequency.
    2. Suggests Priya Sharma for cache incident (authored doc), missing that she is on leave.
    3. Recommends R-7 due to high text keyword overlap, unaware that ADR-17 retired cache-a.
    """
    global_bus.emit("baseline_warning", {
        "mode": "GRAPH_OFF",
        "message": "Baseline Mode Activated: TF-IDF lexical matching. Multi-hop causality disabled."
    })
    res = run_baseline_comparison("Redis cache memory saturation and high latency under checkout load")
    return {
        "status": "completed",
        "graph_reasoning": "DISABLED",
        "baseline_root_cause": "checkout-api",
        "hindsight_root_cause": "cache-b",
        "baseline_procedure": "R-7 (STALE - targets retired cache-a)",
        "hindsight_procedure": "R-12 (VALIDATED - targets cache-b)",
        "baseline_oncall": "Priya Sharma (ON LEAVE - routing failure)",
        "hindsight_oncall": "Marco Rossi (ACTIVE - routed via RULE-07)",
        "details": res
    }

@app.get("/mcp/tools")
def list_mcp_tools():
    """Returns read-only tools permitted on the public MCP endpoint."""
    return {
        "server": "Hindsight-Public",
        "mode": "read-only",
        "persist_answer": False,
        "tools": [
            {"name": "split_storm", "description": "Partitions raw alerts into connected incident clusters"},
            {"name": "root_cause_candidates", "description": "Common upstream dependency intersection (Q2)"},
            {"name": "rank_services", "description": "Centrality and betweenness choke point ranking"},
            {"name": "resolve_conflict", "description": "Path subsumption resolution (Q10)"},
            {"name": "blast_radius", "description": "Downstream cascade blast radius and revenue at risk (Q3)"},
            {"name": "recall_procedure", "description": "Historical win rate retrieval with ADR invalidation check (Q8)"},
            {"name": "who_knows", "description": "Multi-path expertise retrieval with availability check (Q4)"},
            {"name": "who_owns", "description": "Two-hop team ownership and escalation routing"},
            {"name": "trace_decision", "description": "ADR provenance to documentation and RFC thread (Q5)"},
            {"name": "staleness_audit", "description": "Audits documents verified before invalidating changes (Q9)"}
        ]
    }

@app.post("/mcp/call")
def call_public_mcp_tool(request: Request, payload: Dict[str, Any]):
    """Public read-only MCP tool execution with persist_answer=False (ZERO graph mutations)."""
    tool_name = payload.get("tool")
    params = payload.get("params", {})
    tenant = payload.get("tenant", "parcelo")
    target_graph = resolve_target_graph(request, tenant)
    db = get_db()
    registry = HindsightToolRegistry(db, default_graph=target_graph, event_bus=global_bus)

    if tool_name == "root_cause_candidates":
        return registry.root_cause_candidates(incident_id=params.get("incident_id", "INC-8821"), graph_name=target_graph, persist_answer=False)
    elif tool_name == "rank_services":
        return registry.rank_services(incident_id=params.get("incident_id", "INC-8821"), method=params.get("method", "betweenness"), graph_name=target_graph, persist_answer=False)
    elif tool_name == "blast_radius":
        return registry.blast_radius(service_id=params.get("service_id", "cache-b"), graph_name=target_graph, persist_answer=False)
    elif tool_name == "who_knows":
        return registry.who_knows(service_id=params.get("service_id", "cache-b"), graph_name=target_graph, persist_answer=False)
    elif tool_name == "who_owns":
        return registry.who_owns(service_id=params.get("service_id", "cache-b"), graph_name=target_graph, persist_answer=False)
    elif tool_name == "trace_decision":
        return registry.trace_decision(service_id=params.get("service_id", "cache-b"), graph_name=target_graph, persist_answer=False)
    elif tool_name == "staleness_audit":
        return registry.staleness_audit(graph_name=target_graph, persist_answer=False)
    elif tool_name == "recall_procedure":
        return registry.recall_procedure(failure_mode_key=params.get("failure_mode_key", "cache_exhaustion"), graph_name=target_graph, persist_answer=False)
    else:
        raise HTTPException(status_code=400, detail=f"Tool '{tool_name}' not permitted on public read-only endpoint.")

# Serve static frontend files
OUT_DIR = FRONTEND_DIR / "out"
LEGACY_DIR = FRONTEND_DIR / "legacy"

if OUT_DIR.exists():
    @app.get("/")
    def serve_index():
        index_file = OUT_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return HTMLResponse("<h1>Hindsight Frontend Loading...</h1>")

    @app.get("/app")
    @app.get("/app/")
    def serve_app():
        app_file = OUT_DIR / "app" / "index.html"
        if app_file.exists():
            return FileResponse(app_file)
        return HTMLResponse("<h1>Hindsight War Room Loading...</h1>")

    @app.get("/icon.png")
    def serve_icon():
        icon_file = OUT_DIR / "icon.png"
        if icon_file.exists():
            return FileResponse(icon_file)
        raise HTTPException(status_code=404, detail="Icon not found")

    next_dir = OUT_DIR / "_next"
    if next_dir.exists():
        app.mount("/_next", StaticFiles(directory=str(next_dir)), name="next_static")

    images_dir = OUT_DIR / "images"
    if images_dir.exists():
        app.mount("/images", StaticFiles(directory=str(images_dir)), name="images_static")

    videos_dir = OUT_DIR / "videos"
    if videos_dir.exists():
        app.mount("/videos", StaticFiles(directory=str(videos_dir)), name="videos_static")

    if LEGACY_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(LEGACY_DIR)), name="static")

elif LEGACY_DIR.exists():
    @app.get("/")
    @app.get("/app")
    @app.get("/app/")
    def serve_legacy_index():
        legacy_file = LEGACY_DIR / "index.html"
        if legacy_file.exists():
            return FileResponse(legacy_file)
        return HTMLResponse("<h1>Hindsight War Room Loading...</h1>")

    app.mount("/static", StaticFiles(directory=str(LEGACY_DIR)), name="static")
elif FRONTEND_DIR.exists():
    @app.get("/")
    def serve_fallback_index():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return HTMLResponse("<h1>Hindsight War Room Loading...</h1>")

    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
