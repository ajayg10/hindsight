import os
import sys
import time

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from falkordb import FalkorDB
from backend.app.mcp_server import HindsightToolRegistry

def verify():
    host = os.getenv("FALKORDB_HOST", "localhost")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    db = FalkorDB(host=host, port=port)
    g = db.select_graph("t:parcelo")
    registry = HindsightToolRegistry(db, default_graph="t:parcelo")

    print("=== VERIFYING ENRICHED GRAPH SCALE & INVARIANTS ===")
    nodes = g.query("MATCH (n) RETURN count(n)").result_set[0][0]
    edges = g.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0]
    print(f"Graph Scale: {nodes} nodes, {edges} edges")
    assert nodes > 2000, f"Expected >2000 nodes, got {nodes}"

    # 1. Invariant 1: 14-service blast radius ($3,000/min) from cache-b
    blast = registry.blast_radius(service_id="cache-b", persist_answer=False)
    impacted = blast["impacted_services"]
    rev_at_risk = blast["rev_per_min"]
    print(f"1. Blast Radius: {len(impacted)} services, ${rev_at_risk:,.2f}/min")
    assert len(impacted) == 14, f"Expected 14 services in blast radius, got {len(impacted)}"
    assert rev_at_risk == 3000.0, f"Expected $3,000/min revenue at risk, got {rev_at_risk}"

    # 2. Invariant 2: Exactly 3 Stale Docs
    audit = registry.staleness_audit(persist_answer=False)
    stale_docs = audit["stale_docs"]
    stale_ids = [d["doc_id"] for d in stale_docs]
    print(f"2. Staleness Audit: {len(stale_docs)} stale docs found: {stale_ids}")
    assert len(stale_docs) == 3, f"Expected exactly 3 stale docs, got {len(stale_docs)}: {stale_ids}"
    assert "doc-checkout-arch" in stale_ids
    assert "doc-cart-ops" in stale_ids
    assert "doc-auth-spec" in stale_ids

    who = registry.who_knows(service_id="cache-b", persist_answer=False)
    routed = who["routed_expert"]
    candidates = who["candidates"]
    print(f"3. Expert Routing: Routed to {routed} (primary: {who['primary_expert']}, on_leave: {who['primary_on_leave']})")
    print(f"   Candidates: {[(c['person'], c['score'], c['status']) for c in candidates]}")
    
    priya = next(c for c in candidates if c["person"] == "priya")
    marco = next(c for c in candidates if c["person"] == "marco")
    assert round(priya["score"], 2) == 0.91, f"Priya score expected 0.91, got {priya['score']}"
    assert priya["status"] == "leave"

    assert round(marco["score"], 2) == 0.74, f"Marco score expected 0.74, got {marco['score']}"
    assert marco["status"] == "active"
    assert routed == "marco", f"Should route to Marco (active), got {routed}"

    # Verify underlying EXPERT_IN evidence counts
    expert_edges = g.query("MATCH (p:Person)-[e:EXPERT_IN]->(s:Service {id:'cache-b'}) RETURN p.id, e.score, e.evidence_count").result_set
    edge_map = {r[0]: (float(r[1]), int(r[2])) for r in expert_edges}
    assert edge_map["priya"][1] == 14, f"Priya evidence count expected 14, got {edge_map['priya'][1]}"
    assert edge_map["marco"][1] == 8, f"Marco evidence count expected 8, got {edge_map['marco'][1]}"

    # 4. Invariant 4: R-7 Stale, R-12 Valid
    r7_res = registry.recall_procedure(failure_mode_key="cache_exhaustion", persist_answer=False)
    selected = r7_res["selected_procedure"]
    refused = r7_res["refused_procedures"]
    print(f"4. Procedure Recall: Selected={selected['id']}, Refused={[r['id'] for r in refused]}")
    assert selected["id"] == "R-12", f"Expected R-12 selected, got {selected['id']}"
    assert any(r["id"] == "R-7" for r in refused), "Expected R-7 in refused procedures"

    # 5. Measure Latency at Scale (N=50)
    latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        g.query("MATCH (s:Service {id:'cache-b'})<-[:DEPENDS_ON*1..4]-(dep:Service) RETURN count(dep)")
        latencies.append((time.perf_counter() - t0) * 1000.0)
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    print(f"5. Measured Multi-Hop Read Latency at {nodes} nodes (N=50): p50={p50:.3f}ms, p95={p95:.3f}ms")

    print("\n>>> ALL 4 GOLDEN INVARIANTS STRICTLY PRESERVED AT ENRICHED SCALE! <<<")

if __name__ == "__main__":
    verify()
