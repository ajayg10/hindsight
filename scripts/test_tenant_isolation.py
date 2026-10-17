#!/usr/bin/env python3
"""
Multi-Tenant Isolation Acceptance Test.
Proves:
1. Identical alert shape ['checkout-api', 'cartservice', 'paymentservice', 'frontend'] yields:
   - In t:parcelo: isolates to root cause 'cache-b' (owning team: core-infra, expert: Marco/Priya)
   - In t:blueharbor: isolates to root cause 'paymentservice' (owning team: merchant-payments, expert: Elena Vance)
2. Graph isolation: mutations in t:parcelo have zero effect on t:blueharbor.
3. Multi-tenant existence: all 5 tenant graphs exist with verified service counts.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import falkordb
from app.mcp_server import HindsightToolRegistry
from app.events import EventBus

def run_tenant_isolation_test():
    print("\n════════════════════════════════════════════════════════════════════")
    print("       ⚡ HINDSIGHT MULTI-TENANT ISOLATION ACCEPTANCE TEST ⚡       ")
    print("════════════════════════════════════════════════════════════════════\n")

    db = falkordb.FalkorDB(host="falkordb", port=6379)
    bus = EventBus()

    # 1. Verify existence of all 5 tenant graphs
    tenants = ["parcelo", "blueharbor", "acme", "novastream", "finflow"]
    print("[1/4] Verifying 5 tenant graphs exist in FalkorDB...")
    for t in tenants:
        g = db.select_graph(f"t:{t}")
        cnt = g.query("MATCH (s:Service) RETURN count(s)").result_set[0][0]
        print(f"  • t:{t:<12} -> {cnt} services")
        assert cnt > 0, f"Tenant t:{t} has 0 services!"
    print("  ✓ All 5 tenant graphs verified.\n")

    # 2. Test identical alert shape yields DIFFERENT isolated answers
    alert_shape = ["checkout-api", "cartservice", "paymentservice", "frontend"]
    print(f"[2/4] Testing identical alert shape: {alert_shape}...")

    # Query Parcelo
    tools_parcelo = HindsightToolRegistry(db, default_graph="t:parcelo", event_bus=bus)
    ans_parcelo = tools_parcelo.root_cause_candidates("INC-PARCELO-TEST", alerting_services=alert_shape, persist_answer=False)
    top_parcelo = ans_parcelo["top_candidate"]
    team_parcelo = tools_parcelo.who_owns(top_parcelo, persist_answer=False)
    expert_parcelo = tools_parcelo.who_knows(top_parcelo, persist_answer=False)

    print(f"  ▸ Tenant t:parcelo:")
    print(f"    - Root Cause isolated : {top_parcelo}")
    print(f"    - Owning Team         : {team_parcelo.get('team_name')} ({team_parcelo.get('team_id')})")
    print(f"    - Routed Expert       : {expert_parcelo.get('routed_expert')} (Score: {expert_parcelo.get('routed_score')})")

    # Query BlueHarbor
    tools_bh = HindsightToolRegistry(db, default_graph="t:blueharbor", event_bus=bus)
    ans_bh = tools_bh.root_cause_candidates("INC-BH-TEST", alerting_services=alert_shape, persist_answer=False)
    top_bh = ans_bh["top_candidate"]
    team_bh = tools_bh.who_owns(top_bh, persist_answer=False)
    expert_bh = tools_bh.who_knows(top_bh, persist_answer=False)

    print(f"  ▸ Tenant t:blueharbor:")
    print(f"    - Root Cause isolated : {top_bh}")
    print(f"    - Owning Team         : {team_bh.get('team_name')} ({team_bh.get('team_id')})")
    print(f"    - Routed Expert       : {expert_bh.get('routed_expert')} (Score: {expert_bh.get('routed_score')})")

    # STRICT ISOLATION ASSERTIONS
    assert top_parcelo == "cache-b", f"Expected cache-b in parcelo, got {top_parcelo}"
    assert top_bh == "paymentservice", f"Expected paymentservice in blueharbor, got {top_bh}"
    assert top_parcelo != top_bh, "Root causes between tenants must differ!"

    assert team_parcelo.get("team_id") == "core-infra"
    assert team_bh.get("team_id") == "merchant-payments"
    assert team_parcelo.get("team_id") != team_bh.get("team_id")

    assert expert_parcelo.get("routed_expert") == "marco"
    assert expert_bh.get("routed_expert") == "elena"
    assert expert_parcelo.get("routed_expert") != expert_bh.get("routed_expert")
    print("  ✓ PASS: Identical alert shape yields completely distinct root causes, teams, and experts across tenants.\n")

    # 3. Test Mutation & Snapshot Isolation between tenant graphs
    print("[3/4] Testing Mutation Isolation between t:parcelo and t:blueharbor...")
    g_parcelo = db.select_graph("t:parcelo")
    g_bh = db.select_graph("t:blueharbor")

    bh_nodes_before = g_bh.query("MATCH (n) RETURN count(n)").result_set[0][0]
    
    # Mutate parcelo
    g_parcelo.query("CREATE (:TestIsolationProbe {tenant:'parcelo', t:timestamp()})")
    
    bh_nodes_after = g_bh.query("MATCH (n) RETURN count(n)").result_set[0][0]
    assert bh_nodes_before == bh_nodes_after, f"BlueHarbor node count mutated! Before: {bh_nodes_before}, After: {bh_nodes_after}"
    
    # Clean probe
    g_parcelo.query("MATCH (p:TestIsolationProbe) DELETE p")
    print("  ✓ PASS: Graph mutation in t:parcelo has zero side-effects on t:blueharbor (strict tenant isolation).\n")

    # 4. Procedure Recall Isolation
    print("[4/4] Testing Procedure Recall Isolation...")
    proc_parcelo = tools_parcelo.recall_procedure(failure_mode_key="cache_exhaustion", persist_answer=False)
    assert proc_parcelo["selected_procedure"]["id"] == "R-12"
    assert any(r["id"] == "R-7" for r in proc_parcelo["refused_procedures"])

    proc_bh = tools_bh.recall_procedure(failure_mode_key="payment_gateway_exhaustion", persist_answer=False)
    assert proc_bh["selected_procedure"]["id"] == "R-15"
    print("  ✓ PASS: Tenant-specific procedure memories isolated (R-12 for parcelo vs R-15 for blueharbor).\n")

    print("════════════════════════════════════════════════════════════════════")
    print("    🎉 MULTI-TENANT ISOLATION ACCEPTANCE: ALL ASSERTIONS PASSED!    ")
    print("════════════════════════════════════════════════════════════════════\n")

if __name__ == "__main__":
    run_tenant_isolation_test()
