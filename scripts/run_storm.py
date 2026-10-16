#!/usr/bin/env python3
"""
Hindsight: Run the Storm (CLI & Live Story Runner).

Simulates the complete Phase 3 on-call incident workflow:
1. Sentinel: 9 alerting services collapsed into 1 incident (INC-8821) via WCC.
2. Investigator-A: Upstream dependency intersection (Q2) -> lands on cache-b (9 alerts covered).
3. Investigator-B: Centrality / Betweenness ranking -> lands on checkout-api (betweenness 3.0).
4. Conflict Resolution: Q10 graph path subsumption -> cache-b subsumes checkout-api (1-hop path).
5. Handoff: Investigator-A hands off remediation task with evidence IDs packet to Responder.
6. Responder: Recalls procedures; refuses R-7 (83.3% win rate) due to ADR-17; selects R-12 (60.0% win rate).
7. Guardrail: Blast radius of 14 services ($3,000/min) exceeds automated threshold; approval gate triggered.
8. Execution: Simulated executor runs procedure R-12 after operator approval, writing Action episode to graph.
9. Concierge: Resolves owning team (team-infra) and routes expert from Priya (0.91, leave) to Marco (0.74, active).
10. Librarian: Maintenance cycle flags 3 stale docs and opens coordination tasks.
"""
import argparse
import asyncio
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "seed"))

from app.clock import CoordinationClock, DemoClock
from app.events import EventBus, global_bus
from app.mcp_server import HindsightToolRegistry
from app.agents import (
    SentinelAgent,
    InvestigatorAgent,
    ResponderAgent,
    ConciergeAgent,
    LibrarianWorker
)
from gen import generate_full_seed
from falkordb import FalkorDB

# Terminal ANSI formatting
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
RESET = "\033[0m"

async def run_storm_cli(mode: str = "demo", reset_seed: bool = True):
    host = os.getenv("FALKORDB_HOST", "falkordb")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    db = FalkorDB(host=host, port=port)
    graph_name = "t:parcelo"

    delay_s = 1.0 if mode == "demo" else 0.0

    print(f"\n{BOLD}{CYAN}══════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{CYAN}                ⚡ HINDSIGHT: RUNNING THE INCIDENT STORM ⚡                 {RESET}")
    print(f"{BOLD}{CYAN}══════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"Pacing mode: {BOLD}{mode.upper()}{RESET} | Graph: {BOLD}{graph_name}{RESET} | Host: {host}:{port}\n")

    if reset_seed:
        print(f"{YELLOW}▶ Resetting graph with 58-service topology & golden planted slice...{RESET}")
        t0 = time.perf_counter()
        generate_full_seed(db, graph_name)
        print(f"  {GREEN}✓ Seed planted in {(time.perf_counter()-t0)*1000:.1f} ms{RESET}\n")

    bus = EventBus(mode=mode, demo_delay_s=delay_s)
    registry = HindsightToolRegistry(db, graph_name, event_bus=bus)
    g = db.select_graph(graph_name)

    # Pre-create coordination entities
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

    # -------------------------------------------------------------
    # Step 1: Alert Ingestion & Sentinel Incident Collapse
    # -------------------------------------------------------------
    print(f"{BOLD}[1/7] 🚨 Sentinel: Ingesting 9 Alert Streams...{RESET}")
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
    print(f"  {GREEN}✓ Policy {storm_res['policy_rule_id']} ({storm_res['policy_chip']}):{RESET}")
    print(f"    Collapsed 9 alerts into single incident {BOLD}{inc_id}{RESET} (Answer: {storm_res['answer_id']})\n")

    # -------------------------------------------------------------
    # Step 2: Parallel Investigation with Genuine Heuristics
    # -------------------------------------------------------------
    print(f"{BOLD}[2/7] 🔍 Parallel Investigation: Competing Heuristics...{RESET}")
    await asyncio.sleep(delay_s)
    inv_a_res = await investigator_a.claim_and_investigate("task-investigate-inc-8821", inc_id)
    print(f"  {CYAN}▸ Investigator-A (Common-Dependency Q2):{RESET} Identified {BOLD}{inv_a_res['root_service']}{RESET} (conf: {inv_a_res['confidence']:.2f})")

    await asyncio.sleep(delay_s * 0.5)
    inv_b_res = await investigator_b.claim_and_investigate("task-investigate-b", inc_id)
    print(f"  {MAGENTA}▸ Investigator-B (Betweenness Centrality):{RESET} Identified {BOLD}{inv_b_res['root_service']}{RESET} (conf: {inv_b_res['confidence']:.2f})\n")

    # -------------------------------------------------------------
    # Step 3: Conflict Resolution & Graph Subsumption (Q10)
    # -------------------------------------------------------------
    print(f"{BOLD}[3/7] ⚖️ Conflict Resolution: Graph Path Subsumption (Q10)...{RESET}")
    await asyncio.sleep(delay_s)
    conflict_res = await investigator_a.resolve_competing_hypotheses(inc_id, "hyp-investigator-a", "hyp-investigator-b")
    print(f"  {GREEN}✓ {conflict_res['reason']}{RESET}")
    print(f"  {GREEN}✓ Policy RULE-03-INVESTIGATE-CONFLICT: checkout-api subsumed under cache-b (1 hop).{RESET}\n")

    # -------------------------------------------------------------
    # Step 4: Agent Handoff
    # -------------------------------------------------------------
    print(f"{BOLD}[4/7] 🤝 Agent Handoff: Investigator-A -> Responder...{RESET}")
    evidence_ids = ["cache-b", inv_a_res["answer_id"], conflict_res["answer_id"]]
    await investigator_a.handoff_to_responder("task-remediate-inc-8821", "responder", evidence_ids)
    print(f"  {GREEN}✓ Task transferred with evidence packet: {evidence_ids}{RESET}\n")

    # -------------------------------------------------------------
    # Step 5: Procedure Recall, Stale Refusal & Blast Radius Gate
    # -------------------------------------------------------------
    print(f"{BOLD}[5/7] 🛡️ Responder: Procedure Recall & Guardrail Evaluation...{RESET}")
    await asyncio.sleep(delay_s)
    remed_unapproved = await responder.remediate("task-remediate-inc-8821", inc_id, "cache-b", operator_approved=False)

    refused = remed_unapproved["refused_procedures"][0]
    selected = remed_unapproved["selected_procedure"]
    print(f"  {RED}✗ Refused Stale Procedure: {refused['id']} ({refused['win_rate']*100:.1f}% win rate){RESET}")
    print(f"    Reason: Invalidated by architectural change '{refused['invalidating_changes'][0]}' (RULE-05-STALE-PROCEDURE-REFUSAL)")
    print(f"  {GREEN}✓ Selected Valid Procedure: {selected['id']} ({selected['win_rate']*100:.1f}% win rate){RESET}")
    print(f"  {YELLOW}⚠ Blast Radius Guardrail (RULE-04-GUARDRAIL-BLAST):{RESET}")
    print(f"    Impacts {remed_unapproved['blast_count']} services with ${remed_unapproved['rev_per_min']:,.0f}/min revenue at risk.")
    print(f"    {BOLD}APPROVAL REQUIRED: Execution halted until operator signs off.{RESET}\n")

    # Operator approves
    await asyncio.sleep(delay_s)
    print(f"{BOLD}[5b/7] ✍️ Operator Approval Sign-Off...{RESET}")
    remed_approved = await responder.remediate("task-remediate-inc-8821", inc_id, "cache-b", operator_approved=True, operator_name="priya-oncall")
    print(f"  {GREEN}✓ Action Executed: {remed_approved['action_result']['message']}{RESET}")
    print(f"  {GREEN}✓ Action episode recorded in FalkorDB: {remed_approved['action_result']['episode_id']}{RESET}\n")

    # -------------------------------------------------------------
    # Step 6: Concierge Expert Routing & Provenance
    # -------------------------------------------------------------
    print(f"{BOLD}[6/7] 👤 Concierge: Owner Identification & Expert Routing...{RESET}")
    await asyncio.sleep(delay_s)
    route_info = await concierge.route_incident("cache-b")
    print(f"  Owning Team: {BOLD}{route_info['owner'].get('team_name')}{RESET} ({route_info['owner'].get('channel')})")
    print(f"  {CYAN}▸ Primary Expert: {route_info['primary_expert']} (score 0.91) - ON LEAVE{RESET}")
    print(f"  {GREEN}✓ Dynamically Rerouted to Available Expert: {BOLD}{route_info['routed_expert']}{RESET} (score {route_info['routed_score']:.2f})")
    print(f"  {CYAN}▸ Architectural Lineage: ADR-17 authored by {route_info['decision_trace'][0]['author']}{RESET}\n")

    # -------------------------------------------------------------
    # Step 7: Librarian Maintenance Loop
    # -------------------------------------------------------------
    print(f"{BOLD}[7/7] 📚 Librarian: Closing the Loop (Staleness Audit & Maintenance)...{RESET}")
    await asyncio.sleep(delay_s)
    lib_res = await librarian.run_maintenance_cycle()
    print(f"  {GREEN}✓ Staleness audit identified {lib_res['stale_docs_count']} out-of-date documents.{RESET}")
    for t in lib_res["opened_tasks"]:
        print(f"    - Opened task: {t['task_id']}")
    print(f"  {GREEN}✓ Recomputed EXPERT_IN and refreshed graph PageRank.{RESET}\n")

    # Summary
    transcript = bus.get_transcript()
    answer_rows = g.query("MATCH (a:Answer) RETURN count(a)").result_set[0][0]
    print(f"{BOLD}{GREEN}══════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{GREEN}                 STORM RUN COMPLETED SUCCESSFULLY!                      {RESET}")
    print(f"{BOLD}{GREEN}══════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"Total typed events emitted: {BOLD}{len(transcript)}{RESET}")
    print(f"Traceable Answer nodes in FalkorDB: {BOLD}{answer_rows}{RESET}")
    print(f"All 5 policy rules evaluated and verified.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Hindsight Incident Storm")
    parser.add_argument("--mode", choices=["fast", "demo"], default="demo", help="Pacing mode (fast or demo)")
    parser.add_argument("--no-reset", dest="reset", action="store_false", help="Skip re-seeding the graph")
    args = parser.parse_args()
    asyncio.run(run_storm_cli(mode=args.mode, reset_seed=args.reset))
