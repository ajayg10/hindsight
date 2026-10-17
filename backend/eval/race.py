#!/usr/bin/env python3
"""
Concurrency and Coordination Race Harness (Track 02).
Tests:
1. 20 concurrent workers racing for 8 tasks (asserts 0 double claims)
2. Lease expiry and task reclaim (worker killed -> lease expires -> reclaimer succeeds, version increments)
3. Read latency while write queries execute
"""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import random
import statistics
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.clock import CoordinationClock
from falkordb import FalkorDB

def run_race_harness(db, graph_name="spike:race", workers=20, tasks=8):
    try:
        db.connection.execute_command("GRAPH.DELETE", graph_name)
    except Exception:
        pass

    g = db.select_graph(graph_name)

    # Pre-create workers and open tasks
    g.query("UNWIND range(0, $w - 1) AS i CREATE (:Agent {id: toString(i), role:'investigator', status:'active'})", {"w": workers})
    g.query("UNWIND range(0, $t - 1) AS i CREATE (:Task {id: toString(i), kind:'investigate', status:'open', version:0, lease_until:0})", {"t": tasks})

    claim_cypher = (ROOT / "backend/app/queries/q01_claim.cypher").read_text()
    invariant_cypher = (ROOT / "backend/app/queries/claim_invariant.cypher").read_text()

    barrier = threading.Barrier(workers)

    def worker_fn(worker_id):
        local_db = FalkorDB(host=os.getenv("FALKORDB_HOST", "falkordb"), port=int(os.getenv("FALKORDB_PORT", "6379")))
        local_g = local_db.select_graph(graph_name)
        barrier.wait(timeout=15)

        order = list(range(tasks))
        random.Random(42 + worker_id).shuffle(order)
        wins, lost = [], 0

        for t in order:
            now = CoordinationClock.now_ms()
            # lease duration 20 seconds
            rows = local_g.query(claim_cypher, {
                "task": str(t),
                "agent": str(worker_id),
                "now": now,
                "lease_ms": 20000
            }).result_set
            if rows:
                wins.append(rows[0])
            else:
                lost += 1
        return {"worker": worker_id, "wins": wins, "lost": lost}

    start_ns = time.perf_counter_ns()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(worker_fn, range(workers)))
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1e6

    total_wins = sum(len(r["wins"]) for r in results)
    total_lost = sum(r["lost"] for r in results)

    # Invariant checks:
    double_claims = g.query(invariant_cypher).result_set[0][0]
    claimed_tasks = g.query("MATCH (t:Task {status:'claimed'}) RETURN count(t)").result_set[0][0]
    total_claim_edges = g.query("MATCH ()-[c:CLAIMED]->() RETURN count(c)").result_set[0][0]

    assert total_wins == tasks, f"Expected {tasks} tasks won, got {total_wins}"
    assert claimed_tasks == tasks, f"Expected {tasks} claimed tasks, got {claimed_tasks}"
    assert total_claim_edges == tasks, f"Expected {tasks} claim edges, got {total_claim_edges}"
    assert double_claims == 0, f"Invariant violated: {double_claims} double claim groups found!"

    print(f"--- 1. Worker Claim Race Results ---")
    print(f"Workers: {workers}, Tasks: {tasks}")
    print(f"Elapsed: {elapsed_ms:.2f} ms")
    print(f"Claims won: {total_wins}, Lost attempts: {total_lost}")
    print(f"Double-claim invariant: {double_claims} (STRICT PASS: 0 double claims)")

    # 2. Lease Expiry & Task Reclaim Test
    print(f"\n--- 2. Lease Expiry & Reclaim Test ---")
    g.query("CREATE (:Task {id:'task-kill-demo', kind:'investigate', status:'open', version:0, lease_until:0})")
    now_ms = CoordinationClock.now_ms()
    short_lease_ms = 400 # 400ms lease
    # Worker 0 claims with short lease
    claim1 = g.query(claim_cypher, {
        "task": "task-kill-demo",
        "agent": "0",
        "now": now_ms,
        "lease_ms": short_lease_ms
    }).result_set
    assert claim1 == [["task-kill-demo", 1]], f"Worker 0 initial claim failed: {claim1}"
    print("Worker 0 claimed 'task-kill-demo' (version: 1, lease: 400ms). Worker 0 stopped/killed.")

    # Immediate second claim by Worker 1 MUST fail (lease is active)
    attempt_early = g.query(claim_cypher, {
        "task": "task-kill-demo",
        "agent": "1",
        "now": now_ms + 100,
        "lease_ms": 10000
    }).result_set
    assert attempt_early == [], "Worker 1 should have failed to claim active lease!"
    print("Worker 1 early claim rejected while lease active (0 rows returned).")

    # Sleep past lease expiry
    time.sleep(0.5) # 500ms > 400ms
    reclaim_now = CoordinationClock.now_ms()
    reclaim = g.query(claim_cypher, {
        "task": "task-kill-demo",
        "agent": "1",
        "now": reclaim_now,
        "lease_ms": 10000
    }).result_set
    assert reclaim == [["task-kill-demo", 2]], f"Reclaim failed: {reclaim}"
    print(f"Worker 1 successfully reclaimed task after lease expiry! New version: {reclaim[0][1]}")

    invariant_after = g.query(invariant_cypher).result_set[0][0]
    assert invariant_after == 0, "Double-claim invariant violated after reclaim!"
    print(f"Double-claim invariant after reclaim: {invariant_after} (PASS)")

    # 3. Read Latency during Write Execution (assert strict overlap on same graph)
    print(f"\n--- 3. Read Latency during Ongoing Writes (same graph: '{graph_name}') ---")
    write_timestamps = {}
    write_started = threading.Event()

    def slow_write():
        local_db = FalkorDB(host=os.getenv("FALKORDB_HOST", "falkordb"), port=int(os.getenv("FALKORDB_PORT", "6379")))
        local_g = local_db.select_graph(graph_name)
        w_start = time.perf_counter_ns()
        write_timestamps["start_ns"] = w_start
        write_started.set()
        local_g.query("UNWIND range(1, 100000) AS i CREATE (:RaceWriteProbe {v:i})")
        w_end = time.perf_counter_ns()
        write_timestamps["end_ns"] = w_end

    read_intervals = []
    local_read_db = FalkorDB(host=os.getenv("FALKORDB_HOST", "falkordb"), port=int(os.getenv("FALKORDB_PORT", "6379")))
    local_read_g = local_read_db.select_graph(graph_name)

    with ThreadPoolExecutor(max_workers=1) as write_pool:
        future = write_pool.submit(slow_write)
        write_started.wait(timeout=5)
        for _ in range(20):
            t0 = time.perf_counter_ns()
            local_read_g.ro_query("MATCH (t:Task) RETURN count(t)")
            t1 = time.perf_counter_ns()
            read_intervals.append((t0, t1, (t1 - t0) / 1e6))
        future.result()

    w_start = write_timestamps["start_ns"]
    w_end = write_timestamps["end_ns"]
    w_duration_ms = (w_end - w_start) / 1e6
    read_samples = [d for _, _, d in read_intervals]

    overlapping_reads = [
        (i, r_start, r_end, dur)
        for i, (r_start, r_end, dur) in enumerate(read_intervals)
        if w_start <= r_start and r_end <= w_end
    ]

    print(f"Write query executed on '{graph_name}': duration={w_duration_ms:.2f} ms")
    print(f"Write window: [{w_start} .. {w_end}] ns")
    for i, (r_start, r_end, dur) in enumerate(read_intervals):
        offset_ms = (r_start - w_start) / 1e6
        inside = (w_start <= r_start and r_end <= w_end)
        print(f"  Read #{i+1:02d}: start={r_start} (+{offset_ms:.2f}ms), end={r_end}, latency={dur:.3f}ms, inside_window={inside}")

    assert len(overlapping_reads) == len(read_intervals), (
        f"Expected all {len(read_intervals)} reads to overlap write inside [{w_start}, {w_end}], "
        f"but only {len(overlapping_reads)} did."
    )

    p50 = statistics.median(read_samples)
    p95 = sorted(read_samples)[int(len(read_samples) * 0.95) - 1]
    print(f"Read queries during write (measured on a local container, N=20): p50: {p50:.3f} ms, p95: {p95:.3f} ms (100% overlapped)")

    # Cleanup
    try:
        db.connection.execute_command("GRAPH.DELETE", graph_name)
    except Exception:
        pass

    return {
        "race_elapsed_ms": elapsed_ms,
        "workers": workers,
        "tasks": tasks,
        "claims_won": total_wins,
        "lost_attempts": total_lost,
        "double_claims": double_claims,
        "reclaim_verified": True,
        "read_p50_ms": p50,
        "read_p95_ms": p95
    }

if __name__ == "__main__":
    host = os.getenv("FALKORDB_HOST", "localhost")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    db = FalkorDB(host=host, port=port)
    res = run_race_harness(db)
    print("Race harness completed successfully:", res)
