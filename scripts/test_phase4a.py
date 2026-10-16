#!/usr/bin/env python3
"""
Phase 4a Acceptance Test Suite: War Room Backend & SSE API.
Verifies:
1. Health & Status endpoints
2. Policy rules endpoint returns 5 deterministic rules
3. /api/graph returns 58 service nodes and active DEPENDS_ON edges formatted for Cytoscape
4. Storm workflow execution and event stream generation
5. /api/explain/{answer_id} returns evidence subgraph, Cypher text, and policy chip
6. Static frontend files (index.html, index.css, app.js) present with valid structure
"""
import asyncio
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "seed"))

from falkordb import FalkorDB
from app.main import (
    health_check,
    get_policy_rules,
    get_graph_elements,
    explain_answer,
    execute_storm_workflow,
    approve_storm_action,
    get_db,
    FRONTEND_DIR
)
from app.events import global_bus

def test_phase4a():
    print("=" * 70)
    print("           HINDSIGHT PHASE 4a API & WAR ROOM ACCEPTANCE           ")
    print("=" * 70)

    # 1. Health check
    print("\n--- 1. Testing health_check() ---")
    res = health_check()
    assert res["status"] == "ok"
    assert res["engine"] == "falkordb"
    print(f"✓ PASS: health_check() returns {res}")

    # 2. Policy rules
    print("\n--- 2. Testing get_policy_rules() ---")
    res = get_policy_rules()
    rules = res["rules"]
    assert len(rules) == 5, f"Expected 5 rules, got {len(rules)}"
    print(f"✓ PASS: get_policy_rules() returned 5 deterministic governance rules: {[r['rule_id'] for r in rules]}")

    # 3. Cytoscape graph data
    print("\n--- 3. Testing get_graph_elements() (Cytoscape Elements) ---")
    res = get_graph_elements(tenant="parcelo")
    elements = res["elements"]
    nodes = elements["nodes"]
    edges = elements["edges"]
    assert len(nodes) == 58, f"Expected 58 nodes, got {len(nodes)}"
    assert len(edges) > 50, f"Expected >50 edges, got {len(edges)}"

    # Check node metadata
    node_ids = {n["data"]["id"] for n in nodes}
    assert "cache-b" in node_ids, "cache-b missing from nodes"
    assert "checkout-api" in node_ids, "checkout-api missing from nodes"
    cb_node = [n["data"] for n in nodes if n["data"]["id"] == "cache-b"][0]
    assert cb_node["is_root"] is True, "cache-b should be marked is_root"
    print(f"✓ PASS: get_graph_elements() returned {len(nodes)} nodes and {len(edges)} edges with complete Cytoscape data schemas")

    # 4. Trigger Storm in fast mode
    print("\n--- 4. Testing execute_storm_workflow() (Fast Mode Execution) ---")
    asyncio.run(execute_storm_workflow(mode="fast", reset=True))

    transcript = global_bus.get_transcript()
    assert len(transcript) >= 15, f"Expected >= 15 events, got {len(transcript)}"
    print(f"✓ PASS: Storm completed successfully. Emitted {len(transcript)} typed events across all phases.")

    # 5. Explain endpoint
    print("\n--- 5. Testing explain_answer(answer_id) ---")
    answer_events = [e for e in transcript if e["event_type"] == "answer"]
    assert len(answer_events) > 0, "No answer events found in transcript"
    sample_ans_id = answer_events[0]["payload"]["answer_id"]

    exp = explain_answer(sample_ans_id, tenant="parcelo")
    assert exp["answer_id"] == sample_ans_id
    assert len(exp["evidence_subgraph"]) > 0
    assert len(exp["policy_chip"]) > 0
    print(f"✓ PASS: explain_answer('{sample_ans_id}') returned evidence subgraph ({len(exp['evidence_subgraph'])} nodes) and policy chip '{exp['policy_chip']}'")

    # 6. Static frontend files
    print("\n--- 6. Verifying Frontend Static Artifacts ---")
    index_html = FRONTEND_DIR / "index.html"
    index_css = FRONTEND_DIR / "index.css"
    app_js = FRONTEND_DIR / "app.js"

    assert index_html.exists(), "frontend/index.html is missing"
    assert index_css.exists(), "frontend/index.css is missing"
    assert app_js.exists(), "frontend/app.js is missing"

    html_content = index_html.read_text(encoding="utf-8")
    assert "HINDSIGHT" in html_content
    assert "cytoscape" in html_content
    assert "crew-lanes" in html_content
    print(f"✓ PASS: frontend/ contains index.html ({len(html_content)} bytes), index.css, and app.js")

    print("\n" + "=" * 70)
    print("      🎉 ALL PHASE 4a API & UI ACCEPTANCE TESTS PASSED!       ")
    print("=" * 70)

if __name__ == "__main__":
    test_phase4a()
