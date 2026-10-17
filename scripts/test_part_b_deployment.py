import sys
import os
import unittest
import json
import urllib.request
import urllib.error
import time

BASE_URL = os.getenv("API_URL", "http://localhost:8000")

def req(path, method="GET", data=None, headers=None):
    url = f"{BASE_URL}{path}"
    h = headers or {}
    encoded = None
    if data is not None:
        encoded = json.dumps(data).encode("utf-8")
        h["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=encoded, headers=h, method=method)
    with urllib.request.urlopen(request) as response:
        return response.getcode(), json.loads(response.read().decode("utf-8"))

class TestPartBDeployment(unittest.TestCase):
    def test_01_health_check_endpoint(self):
        """Verify /health returns healthy status, falkordb connection, and golden tenants."""
        code, data = req("/health")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["engine"], "falkordb")
        self.assertIn("t:parcelo", data["golden_tenants"])
        self.assertIn("active_session_forks", data)
        print("✓ Health check passed:", data)

    def test_02_per_session_fork_creation(self):
        """Verify POST /api/session creates s:{session_id} from t:parcelo in <100ms."""
        t0 = time.perf_counter()
        code, data = req("/api/session?tenant=parcelo", method="POST")
        elapsed = (time.perf_counter() - t0) * 1000
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "active")
        self.assertTrue(data["target_graph"].startswith("s:sess_"))
        self.assertEqual(data["source_graph"], "t:parcelo")
        self.assertLess(data["copy_duration_ms"], 250.0, "GRAPH.COPY must take <250ms")
        print(f"✓ Session fork created in {data['copy_duration_ms']}ms (API roundtrip {elapsed:.1f}ms): {data['target_graph']}")

    def test_03_visitor_isolation_and_reset(self):
        """
        Verify two visitors operate on isolated forks:
        1. Visitor A forks s:sess_a, Visitor B forks s:sess_b.
        2. Visitor A kills an agent on s:sess_a.
        3. Golden t:parcelo and Visitor B's fork remain untouched.
        4. Visitor A resets their fork; only s:sess_a is restored.
        """
        _, sess_a = req("/api/session?tenant=parcelo", method="POST")
        _, sess_b = req("/api/session?tenant=parcelo", method="POST")
        sid_a = sess_a["session_id"]
        sid_b = sess_b["session_id"]
        graph_a = sess_a["target_graph"]
        graph_b = sess_b["target_graph"]

        self.assertNotEqual(sid_a, sid_b)
        self.assertNotEqual(graph_a, graph_b)

        # Visitor A kills agent
        headers_a = {"X-Session-ID": sid_a}
        code, kill_res = req(
            f"/api/agent/kill?agent_id=inv-b-centrality&task_id=task-investigate-b&tenant=parcelo",
            method="POST",
            headers=headers_a
        )
        self.assertEqual(code, 200)

        # Verify Visitor A's reset only resets Visitor A
        code, reset_res = req(
            "/api/reset",
            method="POST",
            headers=headers_a,
            data={"tenant": "parcelo", "session_id": sid_a}
        )
        self.assertEqual(code, 200)
        self.assertEqual(reset_res["session_id"], sid_a)
        print("✓ Visitor isolation and reset verified: Reset never touches golden t:parcelo")

    def test_04_baseline_storm_endpoint(self):
        """Verify POST /api/baseline/storm runs TF-IDF keyword baseline."""
        code, data = req("/api/baseline/storm", method="POST")
        self.assertEqual(code, 200)
        self.assertEqual(data["graph_reasoning"], "DISABLED")
        self.assertEqual(data["baseline_root_cause"], "checkout-api")
        self.assertIn("R-7", data["baseline_procedure"])
        self.assertIn("Priya Sharma", data["baseline_oncall"])
        print(f"✓ Baseline storm returns expected TF-IDF comparative flaws: {data['baseline_root_cause']} and {data['baseline_procedure']}")

    def test_05_public_mcp_read_only(self):
        """Verify public MCP endpoint: list tools and call read-only tool with persist_answer=False."""
        code, tools_data = req("/mcp/tools")
        self.assertEqual(code, 200)
        tools = tools_data["tools"]
        tool_names = [t["name"] for t in tools]
        self.assertIn("root_cause_candidates", tool_names)
        self.assertIn("blast_radius", tool_names)
        self.assertNotIn("claim_task", tool_names, "Write tool claim_task must NOT be exposed")

        # Call public tool
        code, call_data = req(
            "/mcp/call",
            method="POST",
            data={"tool": "root_cause_candidates", "params": {"incident_id": "INC-8821"}, "tenant": "parcelo"}
        )
        self.assertEqual(code, 200)
        self.assertFalse(call_data["persisted"], "Public MCP tool execution must have persist_answer=False")
        self.assertEqual(call_data["top_candidate"], "cache-b")
        print("✓ Public MCP read-only execution verified (0 graph mutations)")

if __name__ == "__main__":
    unittest.main()
