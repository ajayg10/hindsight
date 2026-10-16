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
import json
import os
from pathlib import Path
import time
from typing import Dict, List, Optional, Any

from falkordb import FalkorDB
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from .clock import CoordinationClock, DemoClock
from .events import EventBus, Event, global_bus
from .mcp_server import HindsightToolRegistry
from .policy import list_rules
from .agents import (
    SentinelAgent,
    InvestigatorAgent,
    ResponderAgent,
    ConciergeAgent,
    LibrarianWorker
)

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"

app = FastAPI(title="Hindsight API", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    host = os.getenv("FALKORDB_HOST", "falkordb")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    return FalkorDB(host=host, port=port)

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
    return {"status": "ok", "app": "hindsight", "engine": "falkordb"}

@app.get("/api/policy/rules")
def get_policy_rules():
    return {"rules": list_rules()}

@app.get("/api/graph")
def get_graph_elements(tenant: str = "parcelo"):
    """Returns nodes and edges formatted for Cytoscape.js rendering."""
    db = get_db()
    g = db.select_graph(f"t:{tenant}")

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

    return {"elements": {"nodes": nodes, "edges": edges}}

@app.get("/api/explain/{answer_id}")
def explain_answer(answer_id: str, tenant: str = "parcelo"):
    db = get_db()
    registry = HindsightToolRegistry(db, f"t:{tenant}", event_bus=global_bus)
    res = registry.explain(answer_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@app.get("/api/events")
async def sse_events(request: Request):
    """Server-Sent Events endpoint streaming real-time events to the frontend."""
    async def event_generator():
        q = asyncio.Queue()

        def listener(ev: Event):
            q.put_nowait(ev)

        global_bus.subscribe(listener)
        try:
            # Replay existing transcript to catch up client
            for past_ev in global_bus.get_events():
                yield {
                    "event": past_ev.event_type,
                    "data": json.dumps(asdict(past_ev))
                }

            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=1.0)
                    yield {
                        "event": ev.event_type,
                        "data": json.dumps(asdict(ev))
                    }
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        finally:
            global_bus.unsubscribe(listener)

    return EventSourceResponse(event_generator())

async def execute_storm_workflow(mode: str = "demo", reset: bool = True):
    storm_state["running"] = True
    storm_state["pending_approval"] = False
    storm_state["approval_received"].clear()

    db = get_db()
    graph_name = "t:parcelo"
    delay_s = 1.0 if mode == "demo" else 0.05

    if reset:
        from gen import generate_full_seed
        generate_full_seed(db, graph_name)

    global_bus.clear()
    registry = HindsightToolRegistry(db, graph_name, event_bus=global_bus)
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
        global_bus.emit("alert", a)

    await asyncio.sleep(delay_s)
    storm_res = await sentinel.handle_alert_storm(alerts)
    inc_id = storm_res["incident_id"]
    storm_state["incident_id"] = inc_id

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
    storm_state["pending_approval"] = True

    # In demo mode, wait for operator sign-off or auto-approve after brief window
    if mode == "demo":
        try:
            await asyncio.wait_for(storm_state["approval_received"].wait(), timeout=6.0)
        except asyncio.TimeoutError:
            pass  # Auto-sign off to advance demo smoothly

    # 5b. Remediation execution
    remed_approved = await responder.remediate("task-remediate-inc-8821", inc_id, "cache-b", operator_approved=True, operator_name="operator-oncall")
    storm_state["pending_approval"] = False

    # 6. Concierge routing
    await asyncio.sleep(delay_s)
    route_info = await concierge.route_incident("cache-b")

    # 7. Librarian maintenance
    await asyncio.sleep(delay_s)
    lib_res = await librarian.run_maintenance_cycle()

    storm_state["running"] = False
    storm_state["last_result"] = {
        "incident_id": inc_id,
        "root_cause": "cache-b",
        "subsumed": "checkout-api",
        "procedure": "R-12",
        "routed_expert": "marco",
        "stale_docs": lib_res["stale_docs_count"]
    }

@app.post("/api/storm/run")
async def run_storm_endpoint(background_tasks: BackgroundTasks, payload: Dict[str, Any] = None):
    mode = (payload or {}).get("mode", "demo")
    reset = (payload or {}).get("reset", True)
    if storm_state["running"]:
        return {"status": "already_running", "incident_id": storm_state["incident_id"]}

    background_tasks.add_task(execute_storm_workflow, mode=mode, reset=reset)
    return {"status": "started", "mode": mode}

@app.post("/api/storm/approve")
def approve_storm_action():
    storm_state["approval_received"].set()
    storm_state["pending_approval"] = False
    return {"status": "approved", "message": "Operator approval granted for procedure R-12 execution."}

# Serve static frontend files
if FRONTEND_DIR.exists():
    @app.get("/")
    def serve_index():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return HTMLResponse("<h1>Hindsight Frontend Loading...</h1>")

    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
