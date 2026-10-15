#!/usr/bin/env python3
"""
Automated acceptance tests for Phase 1 (Golden Slice).
Asserts:
1. Root cause candidate = cache-b
2. Blast radius = 14 services
3. who_knows = Marco (Priya excluded on leave), and Priya without filter
4. As-of before ADR-17 returns checkout-api -> cache-a, as-of now returns -> cache-b
5. Betweenness flags choke point services
6. 3 docs stale by path
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "seed"))

from app.clock import DemoClock
from plant import ALERTING_SERVICES
from gen import generate_full_seed
from falkordb import FalkorDB

def run_phase1_acceptance():
    host = os.getenv("FALKORDB_HOST", "falkordb")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    db = FalkorDB(host=host, port=port)
    
    print("Generating full seed (58 services) into graph 't:parcelo'...")
    gen_res = generate_full_seed(db, "t:parcelo")
    print("Seed summary:", gen_res)
    assert gen_res["total_services"] == 58, f"Expected 58 services, got {gen_res['total_services']}"
    g = db.select_graph("t:parcelo")

    clock = DemoClock.frozen()
    now = clock.now_ms
    half_life_ms = 30 * 24 * 3600 * 1000

    # Read Cypher queries
    queries_dir = ROOT / "backend/app/queries"
    q02 = (queries_dir / "q02_root_cause.cypher").read_text()
    q03 = (queries_dir / "q03_blast_radius.cypher").read_text()
    q04 = (queries_dir / "q04_who_knows.cypher").read_text()
    q04_all = (queries_dir / "q04_who_knows_all.cypher").read_text()
    q07_as_of = (queries_dir / "q07_as_of.cypher").read_text()

    # 1. Assert Root Cause = cache-b
    print("\n--- 1. Testing Q2 (Root Cause Candidates) ---")
    res_q2 = g.query(q02, {"alerting": ALERTING_SERVICES}).result_set
    print("Q2 Candidates (top 5):", res_q2)
    assert len(res_q2) >= 1, "Expected at least one common ancestor candidate"
    top_candidate = res_q2[0][0]
    top_nearest = res_q2[0][2]
    assert top_candidate == "cache-b", f"Expected root cause 'cache-b', got '{top_candidate}'"
    assert top_nearest == 1, f"Expected nearest hop 1 to alerting nodes, got {top_nearest}"
    print("✓ PASS: Root cause candidate #1 is 'cache-b' with nearest hop = 1")

    # 2. Assert Blast Radius = 14 services
    print("\n--- 2. Testing Q3 (Blast Radius) ---")
    res_q3 = g.query(q03, {"svc": "cache-b"}).result_set
    print(f"Q3 Blast Radius: {len(res_q3)} services returned")
    for r in res_q3:
        print(f"  {r[0]} ({r[1]}): {r[2]} hops, ${r[3]}/min")
    assert len(res_q3) == 14, f"Expected exactly 14 services in blast radius, got {len(res_q3)}"
    total_rev = sum(r[3] for r in res_q3)
    assert total_rev > 0, "Expected positive revenue at risk"
    print(f"✓ PASS: Blast radius is exactly 14 services (${total_rev:,}/min at risk)")

    # 3. Assert who_knows with and without leave filter
    print("\n--- 3. Testing Q4 (Who Knows Expertise) ---")
    res_q4 = g.query(q04, {"svc": "cache-b", "now": now, "half_life_ms": half_life_ms}).result_set
    print("Q4 Active on-call experts (Priya on leave excluded):", res_q4)
    assert len(res_q4) >= 1, "Expected at least one active expert"
    top_active_expert = res_q4[0][0]
    assert top_active_expert == "marco", f"Expected Marco ranked #1 when Priya on leave, got {top_active_expert}"
    print(f"✓ PASS: Top active expert is Marco ({res_q4[0][1]}) with effective score {res_q4[0][2]:.3f}")

    res_q4_all = g.query(q04_all, {"svc": "cache-b", "now": now, "half_life_ms": half_life_ms}).result_set
    print("Q4 All experts unfiltered (showing status):", res_q4_all)
    assert res_q4_all[0][0] == "priya", f"Expected Priya ranked #1 without leave filter, got {res_q4_all[0][0]}"
    assert res_q4_all[0][3] == "leave", f"Expected Priya status 'leave', got {res_q4_all[0][3]}"
    print(f"✓ PASS: Unfiltered top expert is Priya ({res_q4_all[0][1]}) with status '{res_q4_all[0][3]}'")

    # 4. Assert Time Travel: As-of before ADR-17 vs As-of Now
    print("\n--- 4. Testing Q7 (Time Travel / As-Of) ---")
    before_adr17 = clock.before_adr17_ms
    res_before = g.query(q07_as_of, {"t": before_adr17}).result_set
    edges_before = {(r[0], r[1]) for r in res_before}
    assert ("checkout-api", "cache-a") in edges_before, "Expected checkout-api -> cache-a before ADR-17"
    assert ("checkout-api", "cache-b") not in edges_before, "checkout-api -> cache-b should not exist before ADR-17"
    print("✓ PASS: As-of before ADR-17 returns 'checkout-api -> cache-a'")

    res_now = g.query(q07_as_of, {"t": now}).result_set
    edges_now = {(r[0], r[1]) for r in res_now}
    assert ("checkout-api", "cache-b") in edges_now, "Expected checkout-api -> cache-b as of now"
    assert ("checkout-api", "cache-a") not in edges_now, "checkout-api -> cache-a should not be active as of now"
    print("✓ PASS: As-of now returns 'checkout-api -> cache-b'")

    # 5. Assert Betweenness Centrality flags choke points
    print("\n--- 5. Testing Betweenness Choke Points ---")
    res_bw = g.query("MATCH (s:Service) WHERE s.betweenness IS NOT NULL RETURN s.id, s.name, s.betweenness ORDER BY s.betweenness DESC LIMIT 5").result_set
    print("Top Betweenness Choke Points:", res_bw)
    assert len(res_bw) > 0, "Expected computed betweenness scores"
    bw_dict = {r[0]: r[2] for r in res_bw}
    assert "checkout-api" in bw_dict and bw_dict["checkout-api"] >= 10.0, f"Expected checkout-api choke point >= 10.0, got {bw_dict.get('checkout-api')}"
    top_id = res_bw[0][0]
    print(f"✓ PASS: Betweenness correctly flags choke points with 'checkout-api' ({bw_dict['checkout-api']}) and top choke point '{top_id}' ({res_bw[0][2]})")

    # 6. Assert 3 Stale Docs
    print("\n--- 6. Testing Staleness Audit ---")
    stale_query = """
    MATCH (d:Doc)-[:DESCRIBES]->(s:Service)-[r:DEPENDS_ON|DEPENDED_ON]->(:Service)
    WHERE r.valid_from > d.last_verified_at OR r.valid_to > d.last_verified_at
    RETURN d.id, d.title, s.name, count(r) AS changed_deps
    ORDER BY changed_deps DESC
    """
    res_stale = g.query(stale_query).result_set
    print("Stale Docs found:", res_stale)
    assert len(res_stale) == 3, f"Expected exactly 3 stale docs, got {len(res_stale)}"
    print(f"✓ PASS: Exactly 3 docs flagged stale by dependency invalidation path")

    print("\n==========================================")
    print("PHASE 1 ACCEPTANCE: ALL ASSERTIONS PASSED!")
    print("==========================================")

if __name__ == "__main__":
    run_phase1_acceptance()
