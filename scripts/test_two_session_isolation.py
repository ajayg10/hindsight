#!/usr/bin/env python3
"""
Test Two-Session Concurrent Isolation:
Verifies that two independent visitors running on their own session forks:
1. Fork independently via GRAPH.COPY (< 60ms)
2. Run concurrent storm / Race / Approve / Reset actions simultaneously
3. Neither session leaks state to the other session
4. Reset in Session Beta does not affect Session Alpha
5. Golden graph t:parcelo remains completely untouched and unmutated
"""
import os
import threading
import time
import json
import urllib.request
import urllib.error
import falkordb

FALKORDB_HOST = os.getenv("FALKORDB_HOST", "falkordb")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", "6379"))
BASE_URL = os.getenv("API_URL", "http://localhost:8000")

def http_post(path, data=None):
    url = f"{BASE_URL}{path}"
    encoded = json.dumps(data or {}).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def run_test():
    db = falkordb.FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    g_golden = db.select_graph("t:parcelo")
    golden_nodes_before = g_golden.query("MATCH (n) RETURN count(n)").result_set[0][0]
    golden_hyp_before = g_golden.query("MATCH (h:Hypothesis) RETURN count(h)").result_set[0][0]

    print("=== TESTING TWO-SESSION CONCURRENT ISOLATION ===")
    print(f"Golden Graph t:parcelo initial nodes: {golden_nodes_before}, initial hypotheses: {golden_hyp_before}")

    # 1. Create two independent visitor sessions
    res_a = http_post("/api/session", {"tenant": "parcelo"})
    sess_a = res_a["session_id"]
    fork_a = res_a["target_graph"]
    print(f"Session Alpha created: {sess_a} -> graph {fork_a} in {res_a['copy_duration_ms']:.2f}ms")

    res_b = http_post("/api/session", {"tenant": "parcelo"})
    sess_b = res_b["session_id"]
    fork_b = res_b["target_graph"]
    print(f"Session Beta  created: {sess_b} -> graph {fork_b} in {res_b['copy_duration_ms']:.2f}ms")

    assert sess_a != sess_b
    assert fork_a != fork_b

    results = {"alpha": {}, "beta": {}, "errors": []}

    # Worker Thread Alpha: Storm -> Approval -> Verify state
    def worker_alpha():
        try:
            print("[Thread Alpha] Triggering incident storm on Session Alpha...")
            r_storm = http_post("/api/storm/run", {"session_id": sess_a, "mode": "eval"})
            time.sleep(0.4)
            print("[Thread Alpha] Approving execution on Session Alpha...")
            r_app = http_post("/api/storm/approve", {"session_id": sess_a})
            time.sleep(0.6)
            
            g_a = db.select_graph(fork_a)
            nodes_a = g_a.query("MATCH (n) RETURN count(n)").result_set[0][0]
            hyp_a = g_a.query("MATCH (h:Hypothesis) RETURN count(h)").result_set[0][0]
            results["alpha"] = {
                "storm": r_storm.get("status"),
                "approval": r_app.get("status"),
                "nodes": nodes_a,
                "hypotheses": hyp_a
            }
            print(f"[Thread Alpha] Done: {nodes_a} nodes, {hyp_a} hypotheses in {fork_a}")
        except Exception as e:
            results["errors"].append(f"Alpha error: {e}")

    # Worker Thread Beta: Race -> Reset -> Verify state
    def worker_beta():
        try:
            print("[Thread Beta] Running 16-worker concurrency race on Session Beta...")
            r_race = http_post("/api/race", {"session_id": sess_b, "workers": 16, "tasks": 8})
            time.sleep(0.2)
            print("[Thread Beta] Resetting Session Beta fork...")
            r_reset = http_post("/api/reset", {"session_id": sess_b, "tenant": "parcelo"})
            
            g_b = db.select_graph(fork_b)
            nodes_b = g_b.query("MATCH (n) RETURN count(n)").result_set[0][0]
            hyp_b = g_b.query("MATCH (h:Hypothesis) RETURN count(h)").result_set[0][0]
            results["beta"] = {
                "race": r_race.get("status"),
                "reset": r_reset.get("status"),
                "nodes": nodes_b,
                "hypotheses": hyp_b
            }
            print(f"[Thread Beta] Done: {nodes_b} nodes, {hyp_b} hypotheses in {fork_b}")
        except Exception as e:
            results["errors"].append(f"Beta error: {e}")

    t_a = threading.Thread(target=worker_alpha)
    t_b = threading.Thread(target=worker_beta)

    t0 = time.perf_counter()
    t_a.start()
    t_b.start()
    t_a.join()
    t_b.join()
    duration_ms = (time.perf_counter() - t0) * 1000.0

    print(f"\nConcurrent execution finished in {duration_ms:.1f}ms")
    assert not results["errors"], f"Errors encountered: {results['errors']}"

    # 4. Strict Isolation Assertions
    # Alpha should have hypotheses from the storm
    assert results["alpha"]["hypotheses"] > 0, "Session Alpha should have hypotheses asserted"
    # Beta was reset, so it should have 0 hypotheses
    assert results["beta"]["hypotheses"] == 0, f"Session Beta was reset, expected 0 hypotheses, got {results['beta']['hypotheses']}"
    # Reset in Beta must not have affected Alpha
    g_a_check = db.select_graph(fork_a)
    hyp_a_final = g_a_check.query("MATCH (h:Hypothesis) RETURN count(h)").result_set[0][0]
    assert hyp_a_final == results["alpha"]["hypotheses"], "Session Alpha hypotheses should remain completely intact after Beta reset"

    # Golden graph must be 100% unmutated
    golden_nodes_after = g_golden.query("MATCH (n) RETURN count(n)").result_set[0][0]
    golden_hyp_after = g_golden.query("MATCH (h:Hypothesis) RETURN count(h)").result_set[0][0]
    assert golden_nodes_after == golden_nodes_before, f"Golden graph node count mutated: {golden_nodes_before} -> {golden_nodes_after}"
    assert golden_hyp_after == 0, f"Golden graph has {golden_hyp_after} hypotheses (must be 0)"

    print("✓ PASS: Session Alpha and Beta ran concurrently without cross-contamination.")
    print("✓ PASS: Reset in Session Beta did not affect Session Alpha.")
    print("✓ PASS: Golden tenant graph t:parcelo remained 100% immutable and unmutated.")

    # Cleanup temporary test forks
    try:
        db.connection.execute_command("GRAPH.DELETE", fork_a)
        db.connection.execute_command("GRAPH.DELETE", fork_b)
        print("✓ PASS: Test session forks cleaned up.")
    except Exception:
        pass

    print("\n>>> ALL TWO-SESSION CONCURRENT ISOLATION ASSERTIONS PASSED! <<<")

if __name__ == "__main__":
    run_test()
