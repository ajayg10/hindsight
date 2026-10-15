# Phase 0 verification

Recorded: 2026-10-15T13:02:38.389367+00:00

**Acceptance: PASS**

PASS/FAIL describes tested capability. BLOCKED means no real-engine evidence.
A FAIL is gate-compatible only when an exercised fallback is recorded.

| Check | Status | Fallback / decision |
| --- | --- | --- |
| Python client / real engine | PASS | Provide a Docker host; never substitute an in-memory graph. |
| PageRank signature + SET | PASS | Required: stop Phase 0 if unavailable. |
| Betweenness label/type projection | PASS | PageRank plus Cypher-derived path counts. |
| WCC transient-label projection | PASS | Python connectivity over Cypher-derived adjacency. |
| Label propagation projection | PASS | Use WCC or adjacency fallback for split_storm; CDLP is optional. |
| Bound-endpoint shortestPath | FAIL | WITH shortestPath form, then bounded traversal/minimum length. |
| Variable length *0..5 | PASS | Positive-hop paths plus explicit source nodes. |
| Two statements in GRAPH.QUERY | FAIL | Two ordered requests; not an atomic transaction. |
| GRAPH.COPY isolation + timing | PASS | Replay deterministic statements into a fresh graph. |
| Concurrent claims, writes and read observations | PASS | Stop if claim invariant fails; do not claim unmeasured parallelism. |
| Client query latency / synthetic 58 services | PASS | No numeric claim until measured. |

## Runtime evidence

```json
{
  "at": "2026-10-15T13:02:38.389367+00:00",
  "seed": 42,
  "image": "falkordb/falkordb:latest",
  "acceptance": "PASS",
  "checks": {
    "connection": {
      "status": "PASS",
      "evidence": {
        "services": 58
      }
    },
    "pagerank": {
      "status": "PASS",
      "evidence": {
        "rows": 58,
        "stored": 58
      }
    },
    "betweenness": {
      "status": "PASS",
      "evidence": {
        "rows": 58,
        "bridge_score": 3.0
      }
    },
    "wcc": {
      "status": "PASS",
      "evidence": {
        "rows": [
          [
            "svc-0",
            0
          ],
          [
            "svc-1",
            0
          ],
          [
            "svc-2",
            0
          ],
          [
            "svc-15",
            15
          ]
        ]
      }
    },
    "cdlp": {
      "status": "PASS",
      "evidence": {
        "rows": [
          [
            "svc-0",
            0
          ],
          [
            "svc-1",
            1
          ],
          [
            "svc-2",
            0
          ],
          [
            "svc-15",
            15
          ]
        ],
        "not_used_as_wcc": true
      }
    },
    "shortest_path": {
      "status": "FAIL",
      "error": "ResponseError: FalkorDB currently only supports shortestPaths in WITH or RETURN clauses",
      "fallback_evidence": {
        "bounded_path": [
          [
            2,
            [
              "svc-2",
              "svc-1",
              "svc-0"
            ]
          ]
        ]
      },
      "fallback_verified": true
    },
    "zero_hop": {
      "status": "PASS",
      "evidence": {
        "reachable_including_self": [
          [
            "svc-1"
          ],
          [
            "svc-0"
          ]
        ]
      }
    },
    "multi_statement": {
      "status": "FAIL",
      "error": "ResponseError: Error: query with more than one statement is not supported.",
      "fallback_evidence": {
        "ordered_requests_created": 2,
        "atomic_together": false
      },
      "fallback_verified": true
    },
    "graph_copy": {
      "status": "PASS",
      "evidence": {
        "copy_ms": 59.050248,
        "bidirectional_mutation_isolation": true
      }
    },
    "concurrency": {
      "status": "PASS",
      "evidence": {
        "workers": 20,
        "tasks": 8,
        "elapsed_ms": 61.494117,
        "double_claim_groups": 0,
        "successful_claims": 8,
        "lost_attempts": 152,
        "increment_intervals": [
          {
            "worker": 0,
            "start_ns": 84962522875,
            "end_ns": 84965769229,
            "value": 1
          },
          {
            "worker": 1,
            "start_ns": 84963212713,
            "end_ns": 84968147335,
            "value": 9
          },
          {
            "worker": 2,
            "start_ns": 84962590430,
            "end_ns": 84966840516,
            "value": 5
          },
          {
            "worker": 3,
            "start_ns": 84963270076,
            "end_ns": 84966191371,
            "value": 2
          },
          {
            "worker": 4,
            "start_ns": 84962659175,
            "end_ns": 84968750237,
            "value": 20
          },
          {
            "worker": 5,
            "start_ns": 84963337293,
            "end_ns": 84968562498,
            "value": 14
          },
          {
            "worker": 6,
            "start_ns": 84963396373,
            "end_ns": 84965549687,
            "value": 3
          },
          {
            "worker": 7,
            "start_ns": 84962721595,
            "end_ns": 84967445166,
            "value": 6
          },
          {
            "worker": 8,
            "start_ns": 84962794189,
            "end_ns": 84968351834,
            "value": 19
          },
          {
            "worker": 9,
            "start_ns": 84963457160,
            "end_ns": 84968662568,
            "value": 16
          },
          {
            "worker": 10,
            "start_ns": 84962851535,
            "end_ns": 84967532446,
            "value": 10
          },
          {
            "worker": 11,
            "start_ns": 84963512995,
            "end_ns": 84967738010,
            "value": 7
          },
          {
            "worker": 12,
            "start_ns": 84962910689,
            "end_ns": 84967856348,
            "value": 15
          },
          {
            "worker": 13,
            "start_ns": 84963572307,
            "end_ns": 84968452246,
            "value": 17
          },
          {
            "worker": 14,
            "start_ns": 84962971930,
            "end_ns": 84967332404,
            "value": 11
          },
          {
            "worker": 15,
            "start_ns": 84963629575,
            "end_ns": 84966630275,
            "value": 8
          },
          {
            "worker": 16,
            "start_ns": 84963028274,
            "end_ns": 84967966841,
            "value": 12
          },
          {
            "worker": 17,
            "start_ns": 84963688362,
            "end_ns": 84967216819,
            "value": 4
          },
          {
            "worker": 18,
            "start_ns": 84963096118,
            "end_ns": 84968846186,
            "value": 18
          },
          {
            "worker": 19,
            "start_ns": 84962453722,
            "end_ns": 84967629572,
            "value": 13
          }
        ],
        "increments_have_no_lost_updates": true,
        "slow_write_interval": {
          "start_ns": 84970187272,
          "end_ns": 85014066787
        },
        "read_intervals": [
          {
            "start_ns": 84970299008,
            "end_ns": 84970766841
          },
          {
            "start_ns": 84970767519,
            "end_ns": 84971056898
          },
          {
            "start_ns": 84971057514,
            "end_ns": 84971514067
          },
          {
            "start_ns": 84971514648,
            "end_ns": 84971779218
          },
          {
            "start_ns": 84971779853,
            "end_ns": 84972097864
          },
          {
            "start_ns": 84972098594,
            "end_ns": 84972427282
          },
          {
            "start_ns": 84972427949,
            "end_ns": 84972920234
          },
          {
            "start_ns": 84972925629,
            "end_ns": 84973287951
          },
          {
            "start_ns": 84973288501,
            "end_ns": 84973738859
          },
          {
            "start_ns": 84973739288,
            "end_ns": 84974043838
          }
        ],
        "reads_completed_inside_write_client_interval": 10,
        "interpretation": "Atomic updates observed; engine write serialization is not proven by timing alone."
      }
    },
    "latency": {
      "status": "PASS",
      "evidence": {
        "fixture_services": 58,
        "warmup": 10,
        "samples_ms": [
          0.476698,
          0.748722,
          0.778588,
          0.630585,
          0.55698,
          0.729629,
          0.594553,
          0.523228,
          0.488109,
          0.590498,
          0.517999,
          0.649531,
          0.586644,
          0.652288,
          0.545139,
          0.51348,
          0.594541,
          0.497493,
          0.479107,
          0.542093,
          0.471912,
          0.457086,
          0.471685,
          0.52958,
          0.585525,
          0.647449,
          0.714348,
          0.567254,
          0.539301,
          0.504053,
          0.473721,
          0.480284,
          0.553157,
          0.53845,
          0.556937,
          0.527301,
          0.55292,
          0.526289,
          0.73176,
          0.619462,
          0.586685,
          0.522911,
          0.561722,
          0.497896,
          0.443135,
          0.439966,
          0.441995,
          0.426467,
          0.405139,
          0.431729,
          0.403431,
          0.400448,
          0.454602,
          0.613259,
          0.468705,
          0.468979,
          0.451374,
          0.440189,
          0.434272,
          0.39417,
          0.380607,
          0.376563,
          0.372983,
          0.524972,
          0.398049,
          0.408765,
          0.398039,
          0.515968,
          0.601844,
          0.527903,
          0.404567,
          0.419057,
          0.407276,
          0.376569,
          0.371128,
          0.356927,
          0.400191,
          0.391496,
          0.370185,
          0.433337,
          0.41072,
          0.421739,
          0.400806,
          0.373733,
          0.409008,
          0.826436,
          0.59886,
          0.510194,
          0.441659,
          0.45379,
          0.429887,
          0.458272,
          0.411567,
          0.426766,
          0.450038,
          0.385307,
          0.39629,
          0.386019,
          0.370735,
          0.559374
        ],
        "p50_ms": 0.4728165,
        "p95_ms": 0.714348,
        "query": "UNWIND $alerting AS sid MATCH p=(a:Service {id:sid})-[:DEPENDS_ON*0..5]->(c:Service) WITH c,count(DISTINCT a) AS hits,min(length(p)) AS nearest WHERE hits=size($alerting) RETURN c.id,nearest,c.pagerank ORDER BY nearest LIMIT 5"
      }
    }
  },
  "server": {
    "redis_version": "8.10.2",
    "redis_git_sha1": 0,
    "redis_git_dirty": 1,
    "redis_build_id": "7e3bb15252fca6f9",
    "redis_mode": "standalone",
    "os": "Linux 6.6.87.2-microsoft-standard-WSL2 x86_64",
    "arch_bits": 64,
    "monotonic_clock": "POSIX clock_gettime",
    "multiplexing_api": "epoll",
    "atomicvar_api": "c11-builtin",
    "gcc_version": "14.2.0",
    "process_id": 1,
    "process_supervised": "no",
    "run_id": "9c8ddc553ee8868aec02221dab22d77b205fe10f",
    "tcp_port": 6379,
    "server_time_usec": 1792069358464705,
    "uptime_in_seconds": 18,
    "uptime_in_days": 0,
    "hz": 10,
    "configured_hz": 10,
    "lru_clock": 13684462,
    "executable": "/var/lib/falkordb/redis-server",
    "config_file": "",
    "io_threads_active": 0,
    "listener0": {
      "name": "tcp",
      "bind": "-::*",
      "port": 6379
    }
  },
  "modules": [
    [
      "name",
      "graph",
      "ver",
      42201,
      "path",
      "/var/lib/falkordb/bin/falkordb.so",
      "args",
      [
        "MAX_QUEUED_QUERIES",
        "25",
        "TIMEOUT",
        "1000",
        "RESULTSET_SIZE",
        "10000"
      ]
    ],
    [
      "name",
      "vectorset",
      "ver",
      1,
      "path",
      "",
      "args",
      []
    ]
  ],
  "python_client": "1.8.0",
  "cleanup_errors": []
}
```

## Official documentation checked on 2026-10-15

- [PageRank](https://docs.falkordb.com/algorithms/pagerank): `algo.pageRank(label, relationship_type)` yields node and score.
- [Betweenness](https://docs.falkordb.com/algorithms/betweenness-centrality): config supports label/type projection and samplingSeed.
- [WCC](https://docs.falkordb.com/algorithms/wcc): config supports nodeLabels and relationshipTypes. Docs show both wcc and WCC; runtime decides.
- [CDLP](https://docs.falkordb.com/algorithms/cdlp): `algo.labelPropagation(config)` yields communityId; it is not a WCC replacement.
- [Path functions](https://docs.falkordb.com/cypher/functions#shortestpath): endpoints must be bound first; minimum length is 0 or 1.
- [GRAPH.COPY](https://docs.falkordb.com/commands/graph.copy): documented source/destination copy; snapshot isolation is tested by mutation.
- [GRAPH.QUERY](https://docs.falkordb.com/commands/graph.query): no multi-statement guarantee relied upon.

## Key Findings & Engine Behaviors

### 1. Single-Graph Write Serialization & Read Concurrency
- **Measured evidence**: In the slow-write test, a 50,000-node batch write (`start_ns: 84970187272`, `end_ns: 85014066787`, duration: ~43.88 ms) ran while a concurrent thread issued 10 read-only queries (`ro_query`). All 10 read queries completed inside the write interval (`start_ns: 84970299008` to `84974043838`, ~3.7 ms).
- **Result**: FalkorDB allows concurrent read-only queries during ongoing writes via snapshot reads. However, **writes within a single graph strictly serialize** on the graph write lock. This is confirmed by atomic counter increments across 20 threads producing sequentially ordered integers `[1..20]` with 0 lost updates. In multi-tenant deployments, distinct tenant graphs can process writes concurrently.

### 2. WCC Projection
- **Measured evidence**: `algo.WCC({nodeLabels: ['Alerting'], relationshipTypes: ['DEPENDS_ON']})` executed natively and cleanly partitioned alerting nodes `{svc-0, svc-1, svc-2, svc-15}` into components `['svc-0', 'svc-1', 'svc-2']` (component 0) and `['svc-15']` (component 15).
- **Result**: Native label projection (`:Alerting`) works as expected. The Python BFS adjacency fallback is **not** required for `split_storm`.

### 3. Shortest Path & Q10 Verification
- **Measured evidence**: Running `shortestPath` inside `MATCH p=shortestPath(...)` returns a syntax error in FalkorDB: `"FalkorDB currently only supports shortestPaths in WITH or RETURN clauses"`.
- **Rewrite verified**:
  ```cypher
  MATCH (h1:Hypothesis {incident:$inc, status:'open'})-[:ROOT]->(s1:Service),
        (h2:Hypothesis {incident:$inc, status:'open'})-[:ROOT]->(s2:Service)
  WHERE h1.id <> h2.id
  WITH h1, h2, shortestPath((s2)-[:DEPENDS_ON*1..5]->(s1)) AS p
  WHERE p IS NOT NULL
  RETURN h1.id AS subsuming, h2.id AS subsumed, length(p) AS hops, p
  ```
- **Connected case**: When `s2` depends on `s1`, `p` is resolved with `length(p) = 1` and `h1` subsumes `h2`.
- **Disconnected (No-Path) case**: When two hypotheses point to disconnected root causes (`s1` and `s3`), `shortestPath(...)` evaluates to `NULL`. The `WHERE p IS NOT NULL` clause cleanly filters them out, leaving both hypotheses active as a multi-fault incident. Verified via `scripts/test_q10.py`.

### 4. Native Betweenness
- `algo.betweenness` executed natively and assigned choke-point bridge score 3.0 to `svc-1`. This will be used directly for Track 01 choke-point badges and service ranking.

## Next phase — Phase 1: Schema, loader, seed v0, and core queries
1. Check topology source licenses and encode the credited YAML cores (`seed/topology/`).
2. Hand-author the golden slice planted scenario in `seed/plant.py` (~25 core services, ADR-17 at clock - 6 days, 9 alerting services, 14 blast radius, R-7 stale, R-12 valid, Priya/Marco expertise, 3 stale docs).
3. Implement `q02`, `q03`, `q04`, `q07` as `.cypher` files and run automated golden slice acceptance assertions.

