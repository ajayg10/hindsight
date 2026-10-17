#!/usr/bin/env python3
"""
Test Suite for Public MCP Read-Only Immutability Invariant:
Asserts that calling public MCP tools performs ZERO graph mutations (node/edge counts remain strictly identical).
"""
import asyncio
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from falkordb import FalkorDB
from app.mcp_server import HindsightToolRegistry, create_public_mcp_server
from app.events import global_bus

def test_public_mcp_immutability():
    print("\n════════════════════════════════════════════════════════════════════")
    print("      ⚡ HINDSIGHT PUBLIC MCP READ-ONLY IMMUTABILITY TEST ⚡       ")
    print("════════════════════════════════════════════════════════════════════\n")

    host = os.getenv("FALKORDB_HOST", "falkordb")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    db = FalkorDB(host=host, port=port)
    graph_name = "t:parcelo"
    g = db.select_graph(graph_name)

    # Initial node and edge counts
    nodes_before = g.query("MATCH (n) RETURN count(n)").result_set[0][0]
    edges_before = g.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0]
    print(f"Graph count BEFORE public MCP queries: {nodes_before} nodes, {edges_before} edges.")

    registry = HindsightToolRegistry(db, default_graph=graph_name, event_bus=global_bus)
    public_srv = create_public_mcp_server(registry)

    # Call each public MCP tool via public_srv.call_tool
    tool_calls = [
        ("split_storm", {"alerts": [{"service": "checkout-api"}]}),
        ("root_cause_candidates", {"incident_id": "INC-8821"}),
        ("rank_services", {"incident_id": "INC-8821", "method": "betweenness"}),
        ("resolve_conflict", {"incident_id": "INC-8821", "hypothesis_a": "hyp-a", "hypothesis_b": "hyp-b"}),
        ("blast_radius", {"service_id": "cache-b"}),
        ("recall_procedure", {"failure_mode_key": "cache_exhaustion"}),
        ("who_knows", {"service_id": "cache-b"}),
        ("who_owns", {"service_id": "cache-b"}),
        ("trace_decision", {"service_id": "cache-b"}),
        ("staleness_audit", {}),
        ("explain", {"answer_id": "ans-transient-test123"})
    ]

    print(f"Testing {len(tool_calls)} public MCP tool invocations...")

    for name, args in tool_calls:
        res = asyncio.run(public_srv.call_tool(name, args))
        # Extract content payload
        if hasattr(res, "content"):
            content_val = res.content[0].text if res.content else "{}"
            payload = json.loads(content_val) if isinstance(content_val, str) else content_val
        elif isinstance(res, tuple):
            payload = res[0]
        else:
            payload = res

        print(f"  ✓ Called public tool '{name}': returned {type(payload)}")

    # Post count check
    nodes_after = g.query("MATCH (n) RETURN count(n)").result_set[0][0]
    edges_after = g.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0]
    print(f"\nGraph count AFTER public MCP queries:  {nodes_after} nodes, {edges_after} edges.")

    assert nodes_after == nodes_before, f"CRITICAL: Nodes changed from {nodes_before} to {nodes_after}!"
    assert edges_after == edges_before, f"CRITICAL: Edges changed from {edges_before} to {edges_after}!"

    print("  ✓ Verified: 0 Answer nodes written to graph.")
    print("  ✓ Verified: 0 [:USED] edges added to graph.")
    print("  ✓ Verified: Node count delta = 0, Edge count delta = 0.")
    print("\n════════════════════════════════════════════════════════════════════")
    print("       🎉 PUBLIC MCP IMMUTABILITY INVARIANT FULLY PASSED!          ")
    print("════════════════════════════════════════════════════════════════════\n")

if __name__ == "__main__":
    test_public_mcp_immutability()
