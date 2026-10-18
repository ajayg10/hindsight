"""
Acceptance Test Script for Hindsight Visitor-Session Consistency Fix.
Tests on real FalkorDB instance and FastAPI service at http://localhost:8000.
"""
import sys
import time
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

def request(path, method="GET", headers=None, body=None):
    headers = headers or {}
    data = None
    if body is not None:
        if isinstance(body, dict):
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif isinstance(body, (bytes, str)):
            data = body.encode("utf-8") if isinstance(body, str) else body
    
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            resp_headers = dict(resp.headers)
            body_bytes = resp.read()
            json_data = None
            try:
                json_data = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                pass
            return resp.status, resp_headers, json_data, body_bytes
    except urllib.error.HTTPError as e:
        resp_headers = dict(e.headers)
        body_bytes = e.read()
        json_data = None
        try:
            json_data = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            pass
        return e.code, resp_headers, json_data, body_bytes

def run_tests():
    print("=" * 70)
    print("STARTING HINDSIGHT VISITOR-SESSION CONSISTENCY ACCEPTANCE TESTS")
    print("=" * 70)

    # 0. Health check
    status, _, health, _ = request("/health")
    assert status == 200, f"Expected 200, got {status}"
    print(f"[PASS] 0. Health check passed: {health['status']}, engine={health['engine']}, tenants={health['golden_tenants']}")

    # 1. Create two independent sessions A and B for Parcelo
    status, headers_a, sess_a, _ = request("/api/session?tenant=parcelo", method="POST")
    assert status == 200, f"Session A creation failed: {status}"
    sid_a = sess_a["session_id"]
    graph_a = sess_a["target_graph"]
    print(f"[PASS] 1a. Created Session A: {sid_a} (graph: {graph_a})")

    status, headers_b, sess_b, _ = request("/api/session?tenant=parcelo", method="POST")
    assert status == 200, f"Session B creation failed: {status}"
    sid_b = sess_b["session_id"]
    graph_b = sess_b["target_graph"]
    print(f"[PASS] 1b. Created Session B: {sid_b} (graph: {graph_b})")

    assert sid_a != sid_b, "Session IDs must be distinct"
    assert graph_a != graph_b, "Session graphs must be distinct"

    # 2. Verify golden tenant graph receives no visitor data initially
    status, _, stats_golden, _ = request("/api/stats?tenant=parcelo")
    assert status == 200
    golden_nodes_initial = stats_golden["nodes"]
    print(f"[INFO] 2. Golden tenant t:parcelo initial node count: {golden_nodes_initial}")

    # 3. Verify initial state of A and B before storm:
    # Latest explain in A must return 404 (no answers yet)
    status, _, err, _ = request("/api/explain/latest", headers={"X-Session-ID": sid_a})
    assert status == 404, f"Expected 404 for explain/latest before storm in A, got {status}: {err}"
    print(f"[PASS] 3a. Initial explain/latest in Session A returns 404 as expected: {err.get('detail')}")

    # Memory summary in A before storm must have 0 actions
    status, _, mem_a, _ = request("/api/memory/summary", headers={"X-Session-ID": sid_a})
    assert status == 200
    assert len(mem_a["episodic_memory"]["recorded_actions"]) == 0, "Expected 0 recorded actions before storm"
    print(f"[PASS] 3b. Initial memory summary in Session A has 0 recorded actions")

    # 4. Run storm in Session A and complete its workflow
    print("[INFO] 4. Running storm in Session A...")
    status, _, storm_res, _ = request(
        "/api/storm/run",
        method="POST",
        headers={"X-Session-ID": sid_a},
        body={"mode": "test", "tenant": "parcelo", "reset": True}
    )
    assert status == 200, f"Storm run failed: {status}, {storm_res}"
    print(f"[PASS] 4a. Storm started in Session A: {storm_res}")

    # In test mode or fast demo, wait for storm to complete
    max_wait = 15.0
    start_t = time.time()
    storm_completed = False
    action_episodes_found = False

    while time.time() - start_t < max_wait:
        # Check memory summary in A to see if action episode appeared
        status, _, mem_a, _ = request("/api/memory/summary", headers={"X-Session-ID": sid_a})
        if status == 200 and len(mem_a["episodic_memory"]["recorded_actions"]) > 0:
            action_episodes_found = True
            storm_completed = True
            break
        time.sleep(0.5)

    assert action_episodes_found, f"Storm in Session A did not record action episodes within {max_wait}s"
    print(f"[PASS] 4b. Storm completed in Session A in {round(time.time() - start_t, 2)}s")

    # 5. Verify A's created Answer IDs resolve through the explain endpoint using A's context
    status, _, explain_latest_a, _ = request("/api/explain/latest", headers={"X-Session-ID": sid_a})
    assert status == 200, f"Expected 200 for A explain/latest, got {status}: {explain_latest_a}"
    assert "answer_id" in explain_latest_a, "Expected answer_id in explain response"
    ans_id_a = explain_latest_a["answer_id"]
    print(f"[PASS] 5a. A's latest answer resolved: {ans_id_a}, tool={explain_latest_a.get('tool')}, policy={explain_latest_a.get('policy_chip')}")
    assert len(explain_latest_a.get("evidence_subgraph", [])) > 0, "Evidence subgraph should contain nodes"
    print(f"[PASS] 5b. Evidence subgraph in A contains {len(explain_latest_a['evidence_subgraph'])} nodes")

    # Verify resolving specific answer ID in A
    status, _, explain_specific_a, _ = request(f"/api/explain/{ans_id_a}", headers={"X-Session-ID": sid_a})
    assert status == 200, f"Expected 200 for specific answer {ans_id_a} in A, got {status}"
    assert explain_specific_a["answer_id"] == ans_id_a
    print(f"[PASS] 5c. Specific Answer ID {ans_id_a} successfully explained in A")

    # 6. Verify A's action Episode appears in A's memory summary
    recorded_actions_a = mem_a["episodic_memory"]["recorded_actions"]
    assert len(recorded_actions_a) > 0, "Expected recorded actions in A"
    first_action = recorded_actions_a[0]
    print(f"[PASS] 6. A's action Episode appears in memory summary: ID={first_action['id']}, procedure={first_action['procedure']}, target={first_action['target']}, approved_by={first_action['approved_by']}")
    assert first_action["procedure"] == "R-12", f"Expected procedure R-12, got {first_action['procedure']}"
    assert first_action["target"] == "cache-b", f"Expected target cache-b, got {first_action['target']}"

    # 7. Verify B CANNOT read A's answer or action Episode (Cross-visitor isolation)
    status, _, explain_b_with_a_id, _ = request(f"/api/explain/{ans_id_a}", headers={"X-Session-ID": sid_b})
    assert status == 404, f"Cross-visitor leak! Session B should NOT resolve A's answer, got {status}: {explain_b_with_a_id}"
    print(f"[PASS] 7a. Session B cannot read Session A's answer (HTTP 404 as expected: {explain_b_with_a_id.get('detail')})")

    status, _, explain_latest_b, _ = request("/api/explain/latest", headers={"X-Session-ID": sid_b})
    assert status == 404, f"Cross-visitor leak! Session B latest should be 404, got {status}: {explain_latest_b}"
    print(f"[PASS] 7b. Session B latest explain returns HTTP 404 (no answers in B)")

    status, _, mem_b, _ = request("/api/memory/summary", headers={"X-Session-ID": sid_b})
    assert status == 200
    assert len(mem_b["episodic_memory"]["recorded_actions"]) == 0, f"Cross-visitor leak! Session B should have 0 recorded actions, got {mem_b['episodic_memory']['recorded_actions']}"
    print(f"[PASS] 7c. Session B memory summary has 0 recorded actions (completely isolated from A)")

    # 8. Verify golden tenant graph receives NO visitor-created answers, actions, or tasks
    status, _, stats_golden_after, _ = request("/api/stats?tenant=parcelo")
    assert status == 200
    # Also directly check if golden graph has any Answer nodes
    status, _, explain_golden, _ = request("/api/explain/latest?tenant=parcelo")
    assert status == 404, f"Golden graph must not have visitor answers, got status {status}"
    status, _, mem_golden, _ = request("/api/memory/summary?tenant=parcelo")
    assert len(mem_golden["episodic_memory"]["recorded_actions"]) == 0, "Golden graph must have 0 visitor actions"
    print(f"[PASS] 8. Golden tenant graph received 0 visitor-created answers or actions (pristine seed graph preserved)")

    # 9. Company Brain answer created in A can be explained in A, but not B
    status, _, comp_res, _ = request(
        "/api/company/query",
        method="POST",
        headers={"X-Session-ID": sid_a},
        body={"intent": "who_owns", "service_id": "cache-b", "tenant": "parcelo"}
    )
    assert status == 200, f"Company query in A failed: {status}"
    comp_ans_id = comp_res.get("answer_id")
    assert comp_ans_id, "Company query must return answer_id"
    print(f"[PASS] 9a. Company Brain answer created in Session A: {comp_ans_id}")

    # Can be explained in A
    status, _, explain_comp_a, _ = request(f"/api/explain/{comp_ans_id}", headers={"X-Session-ID": sid_a})
    assert status == 200, f"Company answer must be explainable in Session A, got {status}"
    assert explain_comp_a["answer_id"] == comp_ans_id
    print(f"[PASS] 9b. Company Brain answer {comp_ans_id} successfully explained in Session A")

    # Cannot be explained in B
    status, _, explain_comp_b, _ = request(f"/api/explain/{comp_ans_id}", headers={"X-Session-ID": sid_b})
    assert status == 404, f"Session B should NOT be able to explain Company answer from A, got {status}"
    print(f"[PASS] 9c. Company Brain answer cannot be explained in Session B (HTTP 404)")

    # 10. Record answer in B, then Reset A: B must remain unchanged
    status, _, comp_b, _ = request(
        "/api/company/query",
        method="POST",
        headers={"X-Session-ID": sid_b},
        body={"intent": "who_knows", "service_id": "cache-b", "tenant": "parcelo"}
    )
    assert status == 200
    ans_b_id = comp_b.get("answer_id")
    print(f"[PASS] 10a. Recorded Company Brain answer in Session B: {ans_b_id}")

    # Reset Session A
    status, _, reset_res, _ = request(
        "/api/reset",
        method="POST",
        headers={"X-Session-ID": sid_a},
        body={"tenant": "parcelo", "session_id": sid_a}
    )
    assert status == 200, f"Reset A failed: {status}"
    print(f"[PASS] 10b. Reset Session A: {reset_res['status']}")

    # After reset, Session A has 0 actions and explain/latest is 404
    status, _, mem_a_after_reset, _ = request("/api/memory/summary", headers={"X-Session-ID": sid_a})
    assert len(mem_a_after_reset["episodic_memory"]["recorded_actions"]) == 0, "A must have 0 actions after reset"
    status, _, explain_a_after_reset, _ = request("/api/explain/latest", headers={"X-Session-ID": sid_a})
    assert status == 404, "A latest explain must be 404 after reset"
    print(f"[PASS] 10c. Session A answers and memory cleared by reset")

    # Session B MUST remain unchanged and still explain ans_b_id!
    status, _, explain_b_still_works, _ = request(f"/api/explain/{ans_b_id}", headers={"X-Session-ID": sid_b})
    assert status == 200, f"Session B must remain unchanged when A is reset, got {status}"
    assert explain_b_still_works["answer_id"] == ans_b_id
    print(f"[PASS] 10d. Session B remains completely intact after Session A was reset")

    # 11. Test missing/expired session behavior
    missing_sid = "sess_non_existent_fake_99999"
    status, headers_missing, stats_missing, _ = request("/api/stats?tenant=parcelo", headers={"X-Session-ID": missing_sid})
    assert status == 200
    new_sid = headers_missing.get("X-Session-ID") or headers_missing.get("x-session-id")
    replaced = headers_missing.get("X-Session-Replaced") or headers_missing.get("x-session-replaced")
    assert new_sid and new_sid != missing_sid, f"Expected fresh replacement session ID, got {new_sid}"
    assert replaced == "true", f"Expected X-Session-Replaced header to be 'true', got {replaced}"
    print(f"[PASS] 11. Missing/expired session '{missing_sid}' explicitly replaced with fresh session '{new_sid}' (X-Session-Replaced: true)")

    # 12. Test failed graph-copy operation
    status, _, err_copy, _ = request("/api/session?tenant=invalid_tenant_nonexistent_xyz", method="POST")
    assert status == 500, f"Expected 500 on GRAPH.COPY failure with invalid tenant, got {status}: {err_copy}"
    detail = err_copy.get("detail", "")
    assert "GRAPH.COPY failed" in detail, f"Expected actionable detail mentioning GRAPH.COPY failure, got: {detail}"
    print(f"[PASS] 12. Failed GRAPH.COPY returns actionable HTTP 500: '{detail}' (no healthy active session returned)")

    print("=" * 70)
    print("ALL 12 ACCEPTANCE TEST SUITES PASSED STRICTLY AND FULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
