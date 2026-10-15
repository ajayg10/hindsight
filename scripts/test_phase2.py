#!/usr/bin/env python3
"""
Phase 2 Acceptance Test Suite: Memory and Coordination.
Verifies:
1. Q8 procedure recall: computed win rates, R-7 refused due to ADR-17 change, R-12 selected.
2. Q1 Race harness & lease expiry: 20 workers x 8 tasks, 0 double claims, killed worker task reclaimed.
3. Q10 Hypothesis subsumption: A subsumes B via path; unrelated root C stands as multi-fault.
4. Q9 Handoff: context packet CARRIES exact evidence node IDs.
5. Q6 3-step idempotent supersession & Librarian crash-injection sweep: no duplicate edges.
6. Q5 Decision provenance: ADR-17 traces to Doc and back to Priya's original chat message.
7. Librarian recompute: EXPERT_IN reproduces Priya (0.91) > Marco (0.74).
"""
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "seed"))

from app.clock import DemoClock, CoordinationClock
from app.librarian import (
    recompute_expertise, sweep_unapplied_facts, decay_sweep, induce_procedures
)
from eval.race import run_race_harness
from gen import generate_full_seed
from falkordb import FalkorDB

def run_phase2_acceptance():
    host = os.getenv("FALKORDB_HOST", "falkordb")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    db = FalkorDB(host=host, port=port)

    print("Step 0: Generating 58-service seed into 't:parcelo'...")
    generate_full_seed(db, "t:parcelo")
    g = db.select_graph("t:parcelo")

    clock = DemoClock.frozen()
    now_business = clock.now_ms
    queries_dir = ROOT / "backend/app/queries"

    # =========================================================================
    # 1. Q8 Procedure Recall & Stale Runbook Refusal
    # =========================================================================
    print("\n--- 1. Testing Q8 (Procedure Recall with Computed Win Rates) ---")
    q08_cypher = (queries_dir / "q08_procedure.cypher").read_text()
    q08_res = g.query(q08_cypher, {
        "fm": "cache_exhaustion",
        "now": now_business,
        "hl": 30 * 24 * 3600 * 1000
    }).result_set
    print("Q8 Returned Procedures:")
    for p in q08_res:
        print(f"  {p[0]} ({p[1]}): win_rate={p[2]:.2f}, invalidating_changes={p[3]}, changes={p[4]}")

    assert len(q08_res) >= 2, f"Expected at least R-7 and R-12, got {len(q08_res)}"
    p_dict = {p[0]: p for p in q08_res}

    r7 = p_dict["R-7"]
    r12 = p_dict["R-12"]

    # R-7 has invalidating change 'change-adr-17' because its target cache-a was retired
    assert r7[3] >= 1, f"Expected R-7 invalidating >= 1, got {r7[3]}"
    assert "change-adr-17" in r7[4], f"Expected change-adr-17 in R-7 invalidating changes, got {r7[4]}"
    assert r7[2] > 0.70, f"Expected R-7 raw decayed win rate > 0.70, got {r7[2]}"

    # R-12 is valid and safe (invalidating = 0)
    assert r12[3] == 0, f"Expected R-12 invalidating == 0, got {r12[3]}"
    assert 0.50 <= r12[2] <= 0.70, f"Expected R-12 win rate ~0.60, got {r12[2]}"

    # Responder policy: pick first procedure where invalidating == 0
    valid_picks = [p for p in q08_res if p[3] == 0]
    selected_procedure = valid_picks[0]
    assert selected_procedure[0] == "R-12", f"Expected R-12 selected, got {selected_procedure[0]}"
    print(f"✓ PASS: Crew refuses R-7 (invalidated by {r7[4]}), successfully picks valid {selected_procedure[0]} ({selected_procedure[2]:.1%} win rate)")

    # =========================================================================
    # 2. Concurrency Race & Lease Expiry Harness (eval/race.py)
    # =========================================================================
    print("\n--- 2. Testing Race Harness & Lease Expiry (eval/race.py) ---")
    race_res = run_race_harness(db, "spike:race_phase2")
    assert race_res["double_claims"] == 0, "Race harness invariant failed!"
    assert race_res["reclaim_verified"] is True, "Lease expiry reclaim failed!"
    print(f"✓ PASS: 20-worker race completed with 0 double claims and verified lease-expiry reclaim")

    # =========================================================================
    # 3. Q10 Hypothesis Subsumption & Multi-Fault
    # =========================================================================
    print("\n--- 3. Testing Q10 (Hypothesis Conflict & Subsumption) ---")
    g.query("""
    CREATE (a1:Agent {id:'inv-a', role:'investigator'}), (a2:Agent {id:'inv-b', role:'investigator'})
    CREATE (h1:Hypothesis {id:'hypo-a', incident:'INC-STORM', status:'open', score:0.9})
    CREATE (h2:Hypothesis {id:'hypo-b', incident:'INC-STORM', status:'open', score:0.7})
    CREATE (h3:Hypothesis {id:'hypo-c', incident:'INC-STORM', status:'open', score:0.5})

    WITH h1, h2, h3
    MATCH (cb:Service {id:'cache-b'}), (chk:Service {id:'checkout-api'}), (cat:Service {id:'catalogue'})
    CREATE (h1)-[:ROOT]->(cb)
    CREATE (h2)-[:ROOT]->(chk)
    CREATE (h3)-[:ROOT]->(cat)
    """)

    q10_cypher = (queries_dir / "q10_conflict.cypher").read_text()
    q10_res = g.query(q10_cypher, {"inc": "INC-STORM"}).result_set
    print("Q10 Subsumptions detected:", q10_res)

    # Since checkout-api depends on cache-b: hypo-a (root cache-b) subsumes hypo-b (root checkout-api)
    subsumed_pairs = [(r[0], r[1], r[2]) for r in q10_res]
    assert ("hypo-a", "hypo-b", 1) in subsumed_pairs, f"Expected hypo-a to subsume hypo-b at hop 1, got {subsumed_pairs}"
    print("✓ PASS: Upstream hypo-a (cache-b) subsumes downstream hypo-b (checkout-api) via path length 1")

    # hypo-c (catalogue) has no dependency path to cache-b, so it is NOT subsumed (multi-fault stands)
    c_subsumed = [r for r in q10_res if r[1] == "hypo-c" or r[0] == "hypo-c"]
    assert len(c_subsumed) == 0, f"Expected hypo-c to remain un-subsumed as multi-fault, got {c_subsumed}"
    print("✓ PASS: Independent root hypo-c stands un-subsumed (multi-fault correctly recognized)")

    # =========================================================================
    # 4. Q9 Handoff with Context Packet
    # =========================================================================
    print("\n--- 4. Testing Q9 (Handoff with CARRIES Evidence Packet) ---")
    g.query("""
    CREATE (t_handoff:Task {id:'task-handoff-demo', status:'claimed', claimed_by:'inv-b', version:1})
    CREATE (resp:Agent {id:'agent-responder', role:'responder'})
    """)
    q09_cypher = (queries_dir / "q09_handoff.cypher").read_text()
    evidence_ids = ["cache-b", "checkout-api", "change-adr-17"]
    h_res = g.query(q09_cypher, {
        "task": "task-handoff-demo",
        "from": "inv-b",
        "to": "agent-responder",
        "hid": "handoff-001",
        "now": CoordinationClock.now_ms(),
        "reason": "Subsumed by hypo-a; handing off blast radius evidence packet to Responder",
        "packet_ids": evidence_ids
    }).result_set
    print("Q9 Handoff result:", h_res)
    assert h_res[0][1] == 3, f"Expected 3 carried evidence nodes, got {h_res[0][1]}"

    # Verify CARRIES edges
    carried = g.query("""
    MATCH (h:Handoff {id:'handoff-001'})-[:CARRIES]->(n)
    RETURN n.id
    """).result_set
    carried_ids = {r[0] for r in carried}
    assert carried_ids == set(evidence_ids), f"Expected carried IDs {evidence_ids}, got {carried_ids}"
    print(f"✓ PASS: Handoff handoff-001 carries exact evidence node IDs {carried_ids}")

    # =========================================================================
    # 5. Q6 Fact Supersession (3 Idempotent Steps + Crash Injection Sweep)
    # =========================================================================
    print("\n--- 5. Testing Q6 (3-Step Idempotent Supersession & Crash Recovery) ---")
    step1 = (queries_dir / "q06_supersede_step1.cypher").read_text()
    step2 = (queries_dir / "q06_supersede_step2.cypher").read_text()
    step3 = (queries_dir / "q06_supersede_step3.cypher").read_text()

    # Normal supersession test:
    g.query("CREATE (:Fact {id:'fact-test-old', subject:'svc-x', predicate:'depends_on', object:'svc-y', status:'current', confidence:1.0, valid_from:1000, applied:true})")
    g.query("CREATE (:Service {id:'svc-x'}), (:Service {id:'svc-y'}), (:Service {id:'svc-z'}), (:Doc {id:'doc-src-test'})")
    g.query("MATCH (x:Service {id:'svc-x'}), (y:Service {id:'svc-y'}) CREATE (x)-[:DEPENDS_ON {fact_id:'fact-test-old', valid_from:1000}]->(y)")

    # Execute step 1: create new fact with applied=false
    f1 = g.query(step1, {
        "s": "svc-x", "p": "depends_on", "o": "svc-z",
        "new_id": "fact-test-new", "conf": 0.95, "now": 2000,
        "reason": "Topology refactor", "source_id": "doc-src-test"
    }).result_set
    assert f1 == [["fact-test-new"]], f"Step 1 failed: {f1}"

    # Verify old fact is superseded and new fact is applied=false
    assert g.query("MATCH (f:Fact {id:'fact-test-old'}) RETURN f.status").result_set == [["superseded"]]
    assert g.query("MATCH (f:Fact {id:'fact-test-new'}) RETURN f.applied").result_set == [[False]]

    # Step 2: transition edge
    g.query(step2, {
        "a": "svc-x", "b": "svc-z", "old_fact_id": "fact-test-old",
        "new_id": "fact-test-new", "now": 2000, "source_id": "doc-src-test", "kind": "network"
    })
    # Step 3: set applied=true
    g.query(step3, {"new_id": "fact-test-new"})
    assert g.query("MATCH (f:Fact {id:'fact-test-new'}) RETURN f.applied").result_set == [[True]]
    print("✓ PASS: Normal Q6 3-step supersession executed and applied=true verified")

    # CRASH INJECTION TEST:
    # Simulate step 1 completing, then agent dies before step 2 and step 3!
    print("Testing Crash Injection: Agent aborts after Step 1...")
    g.query("CREATE (:Service {id:'svc-c1'}), (:Service {id:'svc-c2'}), (:Service {id:'svc-c3'})")
    g.query("MATCH (c1:Service {id:'svc-c1'}), (c2:Service {id:'svc-c2'}) CREATE (c1)-[:DEPENDS_ON {fact_id:'fact-c-old', valid_from:1000}]->(c2)")
    g.query("CREATE (:Fact {id:'fact-c-old', subject:'svc-c1', predicate:'depends_on', object:'svc-c2', status:'current', confidence:1.0, valid_from:1000, applied:true})")

    # Step 1 runs: create new fact pointing svc-c1 -> svc-c3 with applied=false
    g.query(step1, {
        "s": "svc-c1", "p": "depends_on", "o": "svc-c3",
        "new_id": "fact-c-new", "conf": 0.90, "now": 3000,
        "reason": "Emergency migration", "source_id": "doc-src-test"
    })
    # Crash simulated! Agent died here. fact-c-new exists with applied=false
    unapplied_pre = g.query("MATCH (f:Fact {status:'current', applied:false}) RETURN f.id").result_set
    assert ["fact-c-new"] in unapplied_pre, f"Unapplied fact should exist post-crash, got {unapplied_pre}"
    print(f"Unapplied fact identified: {unapplied_pre}. Running Librarian sweep...")

    # Librarian sweeps and replays steps 2 and 3:
    replayed = sweep_unapplied_facts(db, "t:parcelo", now=3000)
    assert "fact-c-new" in replayed, f"Librarian failed to replay unapplied fact: {replayed}"

    # Verify post-sweep consistency: applied is True, no duplicate live edges
    assert g.query("MATCH (f:Fact {id:'fact-c-new'}) RETURN f.applied").result_set == [[True]]
    live_c1_c3 = g.query("MATCH (x:Service {id:'svc-c1'})-[r:DEPENDS_ON]->(y:Service {id:'svc-c3'}) RETURN count(r)").result_set[0][0]
    assert live_c1_c3 == 1, f"Expected exactly 1 live edge after repair, got {live_c1_c3}"
    print("✓ PASS: Crash recovery sweep replayed unapplied fact and restored graph consistency with 0 duplicate edges")

    # =========================================================================
    # 6. Q5 Trace Decision Provenance (ADR-17 back to Priya's Message)
    # =========================================================================
    print("\n--- 6. Testing Q5 (Trace Decision Provenance to Doc & Chat Message) ---")
    q05_cypher = (queries_dir / "q05_trace_decision.cypher").read_text()
    q05_res = g.query(q05_cypher, {"id": "ADR-17"}).result_set
    print("Q5 Decision Trace:", q05_res)
    assert len(q05_res) >= 1, "Expected ADR-17 decision record"
    dec_id, dec_title, dec_at, doc_path, thread_path, has_prior = q05_res[0]

    # Verify Doc Path
    assert any("doc-adr-17" in str(node) for node in doc_path), f"doc-adr-17 missing from doc_path: {doc_path}"
    # Verify Thread & Message Path back to Priya
    thread_text = str(thread_path)
    assert "thread-adr-17" in thread_text, "thread-adr-17 missing from thread_path"
    assert "msg-priya-adr17" in thread_text, "msg-priya-adr17 missing from thread_path"
    assert "Priya Sharma" in thread_text or "priya" in thread_text, "Priya missing from message author path"
    print(f"✓ PASS: ADR-17 provenance traced to Doc (doc-adr-17) and chat thread back to Priya Sharma's original proposal message")

    # =========================================================================
    # 7. Librarian EXPERT_IN Recompute
    # =========================================================================
    print("\n--- 7. Testing Librarian EXPERT_IN Recompute ---")
    exp_rows = recompute_expertise(db, "t:parcelo", now=now_business)
    print("Recomputed Expertise rows:")
    for r in exp_rows:
        print(f"  {r[0]} on {r[1]}: score={r[2]}, evidence_count={r[3]}")

    cb_experts = {r[0]: r[2] for r in exp_rows if r[1] == "cache-b"}
    assert "priya" in cb_experts and "marco" in cb_experts, f"Priya and Marco expected in cache-b experts: {cb_experts}"
    assert cb_experts["priya"] > cb_experts["marco"], f"Expected Priya > Marco ordering, got Priya={cb_experts['priya']}, Marco={cb_experts['marco']}"
    assert math.isclose(cb_experts["priya"], 0.91, abs_tol=0.05), f"Priya score {cb_experts['priya']} not close to 0.91"
    assert math.isclose(cb_experts["marco"], 0.74, abs_tol=0.05), f"Marco score {cb_experts['marco']} not close to 0.74"
    print(f"✓ PASS: Librarian recomputed EXPERT_IN evidence paths, reproducing Priya ({cb_experts['priya']}) > Marco ({cb_experts['marco']})")

    print("\n==========================================")
    print("PHASE 2 ACCEPTANCE: ALL ASSERTIONS PASSED!")
    print("==========================================")

if __name__ == "__main__":
    run_phase2_acceptance()
