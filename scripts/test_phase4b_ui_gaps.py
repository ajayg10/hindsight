import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "app"))

from app.main import (
    get_graph_stats,
    run_worker_race,
    kill_agent_and_reclaim,
    company_query,
    get_facts_ledger,
    get_runbooks,
    get_timeline_diff
)

def test_ui_endpoints():
    # 1. Test stats for all tenants
    for t in ["parcelo", "blueharbor", "acme", "novastream", "finflow"]:
        d = get_graph_stats(tenant=t)
        print(f"Stats [{t}]: {d['nodes']} nodes, {d['edges']} edges, p50: {d['p50_latency_ms']}ms")
        assert d["nodes"] > 0
        assert d["edges"] > 0

    # 2. Test worker race (capped at 32)
    race_data = run_worker_race(workers=32, tasks=8)
    print("Race (32 workers):", race_data)
    assert race_data["workers"] == 32
    assert race_data["claims_won"] == 8
    assert race_data["claims_won"] + race_data["lost_attempts"] == 32 * 8
    assert race_data["double_claims"] == 0

    # 3. Test kill agent & atomic reclaim
    kill_data = kill_agent_and_reclaim(agent_id="inv-b-centrality", task_id="task-investigate-b")
    print("Kill agent:", kill_data)
    assert kill_data["status"] == "reclaimed"
    assert kill_data["reclaimed_by"] == "worker-backup-01"

    # 4. Test Company Brain questions (all 4 intents mapped to MCP tools)
    intents = [
        ("who_owns", "cache-b", "RULE-06-OWNERSHIP-ROUTING", "Team Ownership"),
        ("who_knows", "cache-b", "RULE-07-EXPERT-ROUTING", "Expert Routing"),
        ("trace_decision", "cache-b", "RULE-08-DECISION-PROVENANCE", "Decision Provenance"),
        ("staleness_audit", "", "RULE-09-DOC-STALENESS-AUDIT", "Doc Staleness Audit")
    ]
    for intent, svc, expected_rule_id, expected_chip in intents:
        res = company_query({"intent": intent, "service_id": svc, "tenant": "parcelo"})
        print(f"Company Question [{intent}]: rule_id={res.get('policy_rule_id')} chip={res.get('policy_chip')} tool={res.get('tool')}")
        assert res.get("policy_rule_id") == expected_rule_id, f"Expected {expected_rule_id}, got {res.get('policy_rule_id')}"
        assert res.get("policy_chip") == expected_chip, f"Expected {expected_chip}, got {res.get('policy_chip')}"
        assert res.get("tool") == intent, f"Expected tool {intent}, got {res.get('tool')}"

    # 5. Test Fact Ledger
    facts_data = get_facts_ledger(tenant="parcelo")
    print(f"Fact Ledger: {len(facts_data['facts'])} facts found")
    statuses = [f["status"] for f in facts_data["facts"]]
    assert "current" in statuses
    assert "superseded" in statuses

    # 6. Test Runbooks
    rb_data = get_runbooks(tenant="parcelo")
    print("Runbooks:", [(rb["id"], rb["stamp"], f"{rb['historical_win_rate']}%") for rb in rb_data["runbooks"]])
    r7 = next(rb for rb in rb_data["runbooks"] if rb["id"] == "R-7")
    r12 = next(rb for rb in rb_data["runbooks"] if rb["id"] == "R-12")
    assert r7["stamp"] == "STALE"
    assert r7["is_stale"] is True
    assert r12["stamp"] == "VALIDATED"
    assert r12["is_stale"] is False

    # 7. Test Q7 Timeline Diff
    diff_data = get_timeline_diff(tenant="parcelo")
    print("Timeline Diff:", diff_data["diff_title"])
    assert len(diff_data["added_edges"]) > 0
    assert len(diff_data["removed_edges"]) > 0

    print("\n>>> ALL UI GAP ENDPOINTS AND POLICIES PASSED WITH 100% ACCURACY! <<<")

if __name__ == "__main__":
    test_ui_endpoints()
