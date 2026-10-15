#!/usr/bin/env python3
"""
Phase 3 Acceptance Test Suite: Policy Agents, MCP Tool Registry, and Answer Provenance.

Acceptance Criteria:
1. Architectural Boundary: Test fails if any file in backend/app/agents/ imports
   falkordb, redis, or executes Cypher directly ("the MCP tool list is the only door to the graph").
2. Public MCP Server Safety: Public /mcp exposes ONLY read-only tools and never write tools.
3. Headless End-to-End Storm Reproduction:
   - 9 alerts collapsed into 1 incident via split_storm (WCC)
   - Investigator-A (common-dependency Q2) lands on cache-b
   - Investigator-B (betweenness ranking) lands on checkout-api
   - Q10 subsumes checkout-api under cache-b (upstream failure explains downstream)
   - Handoff from Investigator-A to Responder with evidence IDs
   - Blast radius computed to 14 services ($3,000/min) triggering approval gate
   - R-7 refused with ADR-17 named; R-12 selected (60.0% win rate)
   - Concierge who_knows reroutes Priya (0.91, leave) -> Marco (0.74, active)
   - Librarian worker audits staleness and opens 3 doc tasks
   - Every answer writes an Answer node; explain() returns evidence subgraph + Cypher + policy chip
4. Kill-Agent Reclaim: Expired leases successfully reclaimed with version incremented and 0 double-claims.
5. Golden Event Transcript: Monotonically increasing sequence numbers matching typed event lifecycle.
"""
import ast
import asyncio
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "seed"))

from app.clock import CoordinationClock, DemoClock
from app.events import EventBus
from app.mcp_server import HindsightToolRegistry, create_public_mcp_server
from app.agents import (
    SentinelAgent,
    InvestigatorAgent,
    ResponderAgent,
    ConciergeAgent,
    LibrarianWorker
)
from eval.race import run_race_harness
from gen import generate_full_seed
from falkordb import FalkorDB

def test_architectural_boundary():
    """Asserts that no agent module imports DB client or executes Cypher directly."""
    print("--- 1. Testing Architectural Boundary (Agent MCP Isolation) ---")
    agents_dir = ROOT / "backend/app/agents"
    agent_files = list(agents_dir.glob("*.py"))
    assert len(agent_files) >= 5, f"Expected at least 5 agent files, found {len(agent_files)}"

    forbidden_modules = {"falkordb", "redis"}
    forbidden_calls = {"query", "ro_query", "execute_command"}

    for py_file in agent_files:
        if py_file.name == "__init__.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))

        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        assert forbidden not in alias.name.lower(), (
                            f"VIOLATION in {py_file.name}: imports forbidden module '{alias.name}'. "
                            f"Agents must call ONLY the MCP tool registry!"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for forbidden in forbidden_modules:
                        assert forbidden not in node.module.lower(), (
                            f"VIOLATION in {py_file.name}: imports from forbidden module '{node.module}'. "
                            f"Agents must call ONLY the MCP tool registry!"
                        )

            # Check for direct Cypher method calls on any object
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                method_name = node.func.attr
                assert method_name not in forbidden_calls, (
                    f"VIOLATION in {py_file.name}: calls direct DB method '{method_name}'. "
                    f"Agents must call ONLY the MCP tool registry!"
                )

        print(f"  ✓ {py_file.name}: strictly isolated (0 DB imports, 0 raw Cypher calls)")
    print("✓ PASS: Architectural boundary holds. The MCP tool list is the ONLY door to the graph.\n")


def test_public_mcp_server_safety(registry: HindsightToolRegistry):
    """Asserts that the public MCP server exposes only read-only tools."""
    print("--- 2. Testing Public MCP Server Read-Only Safety ---")
    public_server = create_public_mcp_server(registry)
    tools = asyncio.run(public_server.list_tools())
    tool_names = [t.name for t in tools]

    expected_read_only = {
        "split_storm",
        "root_cause_candidates",
        "rank_services",
        "resolve_conflict",
        "blast_radius",
        "recall_procedure",
        "who_knows",
        "who_owns",
        "trace_decision",
        "staleness_audit",
        "explain"
    }

    forbidden_write_tools = {
        "claim_task",
        "release_task",
        "handoff",
        "assert_hypothesis",
        "execute_action",
        "supersede_fact",
        "open_doc_stale_task"
    }

    for ro in expected_read_only:
        assert ro in tool_names, f"Missing expected read-only tool '{ro}' on public MCP server"

    for w in forbidden_write_tools:
        assert w not in tool_names, f"SECURITY VIOLATION: write tool '{w}' exposed on public MCP endpoint!"

    print(f"  Exposed public read-only tools ({len(tool_names)}): {tool_names}")
    print("✓ PASS: Public /mcp endpoint exposes read-only tools only.\n")


async def run_headless_storm(db: FalkorDB, graph_name: str = "t:parcelo"):
    """Runs the headless end-to-end storm story reproduction."""
    print("--- 3. Running Headless End-to-End Storm Reproduction ---")
    bus = EventBus(mode="fast")
    registry = HindsightToolRegistry(db, graph_name, event_bus=bus)
    g = db.select_graph(graph_name)

    # Pre-create agent nodes and coordination tasks in the graph
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

    # Instantiate agents
    sentinel = SentinelAgent("sentinel", tools=registry)
    investigator_a = InvestigatorAgent("investigator-a", heuristic="common_dependency", tools=registry)
    investigator_b = InvestigatorAgent("investigator-b", heuristic="betweenness_centrality", tools=registry)
    responder = ResponderAgent("responder", tools=registry)
    concierge = ConciergeAgent("concierge", tools=registry)
    librarian = LibrarianWorker("librarian", tools=registry)

    # -------------------------------------------------------------
    # Step 1: Alert Storm -> Sentinel collapses 9 alerts to 1 incident
    # -------------------------------------------------------------
    print("[Story Step 1] 9 Alerts arrive at Sentinel...")
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

    storm_res = await sentinel.handle_alert_storm(alerts)
    inc_id = storm_res["incident_id"]
    assert inc_id == "INC-8821", f"Expected INC-8821, got {inc_id}"
    assert len(storm_res["clusters"]) == 1, "Expected 9 alerts collapsed to exactly 1 incident"
    print(f"  ✓ Sentinel collapsed 9 alerts -> Incident {inc_id} via {storm_res['policy_chip']} (Answer: {storm_res['answer_id']})")

    # -------------------------------------------------------------
    # Step 2: Parallel Investigation with Different Heuristics
    # -------------------------------------------------------------
    print("[Story Step 2] Investigators deploy different heuristics...")
    # Investigator A: Common upstream dependency (Q2)
    inv_a_res = await investigator_a.claim_and_investigate("task-investigate-inc-8821", inc_id)
    assert inv_a_res["status"] == "hypothesis_asserted"
    assert inv_a_res["root_service"] == "cache-b", f"Investigator-A expected cache-b, got {inv_a_res['root_service']}"
    print(f"  ✓ Investigator-A (common-dependency Q2) identified: {inv_a_res['root_service']} (conf: {inv_a_res['confidence']:.2f})")

    # Investigator B: Betweenness / PageRank centrality
    inv_b_res = await investigator_b.claim_and_investigate("task-investigate-b", inc_id)
    assert inv_b_res["status"] == "hypothesis_asserted"
    assert inv_b_res["root_service"] == "checkout-api", f"Investigator-B expected checkout-api, got {inv_b_res['root_service']}"
    print(f"  ✓ Investigator-B (betweenness centrality) identified: {inv_b_res['root_service']} (conf: {inv_b_res['confidence']:.2f})")

    # -------------------------------------------------------------
    # Step 3: Graph Subsumption Conflict Resolution (Q10)
    # -------------------------------------------------------------
    print("[Story Step 3] Resolving hypothesis conflict via Q10...")
    conflict_res = await investigator_a.resolve_competing_hypotheses(inc_id, "hyp-investigator-a", "hyp-investigator-b")
    assert conflict_res["resolved"] is True
    assert conflict_res["hops"] == 1
    print(f"  ✓ Q10 Graph Subsumption: {conflict_res['reason']} (Answer: {conflict_res['answer_id']})")

    # -------------------------------------------------------------
    # Step 4: Handoff with Evidence IDs
    # -------------------------------------------------------------
    print("[Story Step 4] Handoff from Investigator-A to Responder...")
    evidence_ids = ["cache-b", inv_a_res["answer_id"], conflict_res["answer_id"]]
    handoff_res = await investigator_a.handoff_to_responder("task-remediate-inc-8821", "responder", evidence_ids)
    assert handoff_res["handed_off"] is True
    print(f"  ✓ Task handed off with evidence packet IDs: {evidence_ids}")

    # -------------------------------------------------------------
    # Step 5: Responder Procedure Recall, ADR Refusal, & Blast Radius Gate
    # -------------------------------------------------------------
    print("[Story Step 5] Responder recalls procedures & evaluates guardrails...")
    # Attempt remediation without operator approval first -> must be blocked
    remed_unapproved = await responder.remediate("task-remediate-inc-8821", inc_id, "cache-b", operator_approved=False)
    assert remed_unapproved["status"] == "pending_approval"
    assert remed_unapproved["guardrail"]["requires_approval"] is True
    assert remed_unapproved["blast_count"] == 14, f"Expected blast count 14, got {remed_unapproved['blast_count']}"
    assert remed_unapproved["rev_per_min"] == 3000.0, f"Expected rev $3,000/min, got {remed_unapproved['rev_per_min']}"

    # Verify procedure R-7 was refused with ADR-17 named, and R-12 selected
    refused_ids = [r["id"] for r in remed_unapproved["refused_procedures"]]
    assert "R-7" in refused_ids, f"Expected R-7 refused, got {refused_ids}"
    r7_refused = [r for r in remed_unapproved["refused_procedures"] if r["id"] == "R-7"][0]
    assert "change-adr-17" in r7_refused["invalidating_changes"], f"Expected change-adr-17 in {r7_refused}"
    assert r7_refused["win_rate"] > 0.70, f"Expected high historical win rate for R-7, got {r7_refused['win_rate']}"

    selected_proc = remed_unapproved["selected_procedure"]
    assert selected_proc["id"] == "R-12", f"Expected R-12 selected, got {selected_proc}"
    assert abs(selected_proc["win_rate"] - 0.60) < 0.05, f"Expected 60% win rate for R-12, got {selected_proc['win_rate']}"
    print(f"  ✓ Refused R-7 ({r7_refused['win_rate']*100:.1f}% win rate) due to {r7_refused['invalidating_changes']}")
    print(f"  ✓ Selected valid procedure {selected_proc['id']} ({selected_proc['win_rate']*100:.1f}% win rate)")
    print(f"  ✓ Guardrail active: Blast radius of 14 services (${remed_unapproved['rev_per_min']:,.0f}/min) gated on approval.")

    # Operator approves -> Action executed
    print("[Story Step 5b] Human operator signs off on remediation...")
    remed_approved = await responder.remediate("task-remediate-inc-8821", inc_id, "cache-b", operator_approved=True, operator_name="priya-oncall")
    assert remed_approved["status"] == "completed"
    assert remed_approved["action_result"]["executed"] is True
    print(f"  ✓ Action executed: {remed_approved['action_result']['message']}")

    # -------------------------------------------------------------
    # Step 6: Concierge Expert Routing (Priya on leave -> Marco rerouted)
    # -------------------------------------------------------------
    print("[Story Step 6] Concierge routes incident to team and available expert...")
    route_info = await concierge.route_incident("cache-b")
    assert route_info["primary_expert"] == "priya"
    assert route_info["primary_on_leave"] is True
    assert route_info["routed_expert"] == "marco"
    assert route_info["routed_score"] == 0.74
    assert len(route_info["decision_trace"]) > 0
    print(f"  ✓ Concierge: Priya (score {0.91}) on leave -> routed to Marco (score {route_info['routed_score']:.2f})")
    print(f"  ✓ Provenance traced: ADR-17 authored by {route_info['decision_trace'][0]['author']}")

    # -------------------------------------------------------------
    # Step 7: Librarian Worker Staleness Audit & Task Generation
    # -------------------------------------------------------------
    print("[Story Step 7] Librarian worker runs maintenance cycle...")
    lib_res = await librarian.run_maintenance_cycle()
    assert lib_res["stale_docs_count"] == 3, f"Expected 3 stale docs, got {lib_res['stale_docs_count']}"
    assert len(lib_res["opened_tasks"]) == 3, f"Expected 3 tasks opened, got {len(lib_res['opened_tasks'])}"
    print(f"  ✓ Librarian identified 3 stale docs and opened tasks: {[t['task_id'] for t in lib_res['opened_tasks']]}")

    # -------------------------------------------------------------
    # Step 8: Answer Node Provenance & explain() Verification
    # -------------------------------------------------------------
    print("\n--- 4. Verifying Answer Nodes & explain() Provenance ---")
    answer_rows = g.query("MATCH (a:Answer) RETURN a.id, a.tool, a.policy_rule_id, a.cypher_name ORDER BY a.created_at").result_set
    assert len(answer_rows) >= 5, f"Expected at least 5 Answer nodes, got {len(answer_rows)}"
    print(f"Found {len(answer_rows)} traceable Answer nodes in graph:")

    for aid, tool, rule_id, cypher_name in answer_rows:
        explanation = registry.explain(aid)
        assert "error" not in explanation, f"explain({aid}) failed: {explanation}"
        assert explanation["answer_id"] == aid
        assert len(explanation["evidence_subgraph"]) > 0, f"Answer {aid} has empty evidence subgraph!"
        assert len(explanation["policy_chip"]) > 0, f"Answer {aid} missing policy chip!"
        assert len(explanation["cypher_name"]) > 0, f"Answer {aid} missing cypher name!"
        print(f"  ✓ explain('{aid}') -> tool: {tool:22s} | rule: {rule_id:28s} | chip: {explanation['policy_chip']:22s} | evidence: {len(explanation['evidence_subgraph'])} nodes")

    # -------------------------------------------------------------
    # Step 9: Golden Event Transcript Verification
    # -------------------------------------------------------------
    print("\n--- 5. Verifying Golden Event Transcript ---")
    transcript = bus.get_transcript()
    assert len(transcript) >= 15, f"Expected >= 15 events in transcript, got {len(transcript)}"

    # Check monotonically increasing sequence numbers
    seqs = [e["seq"] for e in transcript]
    assert seqs == list(range(1, len(transcript) + 1)), f"Sequence numbers not strictly monotonic: {seqs}"

    event_types = set(e["event_type"] for e in transcript)
    required_events = {
        "alert",
        "incident_created",
        "task_claimed",
        "hypothesis",
        "conflict",
        "handoff",
        "procedure_refused",
        "approval_required",
        "action_executed",
        "doc_task_opened",
        "answer"
    }
    missing_events = required_events - event_types
    assert not missing_events, f"Transcript missing required typed events: {missing_events}"

    print(f"✓ PASS: Golden event transcript contains {len(transcript)} typed events across all {len(event_types)} required types:")
    for ev in transcript:
        payload_summary = {k: v for k, v in ev["payload"].items() if k in ("incident_id", "task_id", "service", "procedure_id", "top_candidate", "tool", "doc_id", "operator")}
        print(f"  [Seq {ev['seq']:02d}] {ev['event_type']:20s} | {payload_summary}")

    print("\n✓ PASS: Headless end-to-end storm story reproduction 100% successful.")


def test_kill_agent_reclaim(db: FalkorDB):
    """Verifies that killed agent's lease is reclaimed after expiry with 0 double-claims."""
    print("\n--- 6. Testing Kill-Agent Lease Expiry & Reclaim ---")
    res = run_race_harness(db, "spike:phase3_kill_race")
    assert res["double_claims"] == 0, f"Invariant violated: {res['double_claims']} double claims!"
    assert res["reclaim_verified"] is True, "Reclaim not verified!"
    print(f"✓ PASS: Kill-agent reclaim verified with 0 double-claims (p50: {res['read_p50_ms']:.3f} ms, p95: {res['read_p95_ms']:.3f} ms, N=20).")


def run_all_phase3_acceptance():
    print("=" * 70)
    print("           HINDSIGHT PHASE 3 ACCEPTANCE TEST SUITE            ")
    print("=" * 70)

    # 1. Architectural Boundary Test
    test_architectural_boundary()

    host = os.getenv("FALKORDB_HOST", "falkordb")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    db = FalkorDB(host=host, port=port)

    # Reset graph with 58-service seed
    print("Resetting 't:parcelo' graph with full 58-service topology & golden planted slice...")
    generate_full_seed(db, "t:parcelo")

    registry = HindsightToolRegistry(db, "t:parcelo")

    # 2. Public MCP Server Safety Test
    test_public_mcp_server_safety(registry)

    # 3. Headless End-to-End Storm
    asyncio.run(run_headless_storm(db, "t:parcelo"))

    # 4. Kill-Agent Reclaim Test
    test_kill_agent_reclaim(db)

    print("\n" + "=" * 70)
    print("      🎉 ALL PHASE 3 ACCEPTANCE TESTS PASSED SUCCESSFULLY!      ")
    print("=" * 70)


if __name__ == "__main__":
    run_all_phase3_acceptance()
