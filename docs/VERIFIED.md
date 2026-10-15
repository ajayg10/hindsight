# Phase 0 verification

Recorded: 2026-10-15T12:16:43.410385+00:00

**Acceptance: BLOCKED**

PASS/FAIL describes tested capability. BLOCKED means no real-engine evidence.
A FAIL is gate-compatible only when an exercised fallback is recorded.

| Check | Status | Fallback / decision |
| --- | --- | --- |
| Python client / real engine | BLOCKED | Provide a Docker host; never substitute an in-memory graph. |
| PageRank signature + SET | BLOCKED | Required: stop Phase 0 if unavailable. |
| Betweenness label/type projection | BLOCKED | PageRank plus Cypher-derived path counts. |
| WCC transient-label projection | BLOCKED | Python connectivity over Cypher-derived adjacency. |
| Label propagation projection | BLOCKED | Use WCC or adjacency fallback for split_storm; CDLP is optional. |
| Bound-endpoint shortestPath | BLOCKED | WITH shortestPath form, then bounded traversal/minimum length. |
| Variable length *0..5 | BLOCKED | Positive-hop paths plus explicit source nodes. |
| Two statements in GRAPH.QUERY | BLOCKED | Two ordered requests; not an atomic transaction. |
| GRAPH.COPY isolation + timing | BLOCKED | Replay deterministic statements into a fresh graph. |
| Concurrent claims, writes and read observations | BLOCKED | Stop if claim invariant fails; do not claim unmeasured parallelism. |
| Client query latency / synthetic 58 services | BLOCKED | No numeric claim until measured. |

## Runtime evidence

```json
{
  "at": "2026-10-15T12:16:43.410385+00:00",
  "seed": 42,
  "image": "falkordb/falkordb:latest",
  "acceptance": "BLOCKED",
  "checks": {
    "connection": {
      "status": "BLOCKED",
      "error": "Docker executable and daemon socket absent; CapEff=0; rootless unshare -Ur fails with uid_map Operation not permitted. Installed FalkorDB client gets Connection refused on localhost:6379. All real-container spikes remain unexecuted."
    },
    "pagerank": {
      "status": "BLOCKED",
      "error": "Docker executable and daemon socket absent; CapEff=0; rootless unshare -Ur fails with uid_map Operation not permitted. Installed FalkorDB client gets Connection refused on localhost:6379. All real-container spikes remain unexecuted."
    },
    "betweenness": {
      "status": "BLOCKED",
      "error": "Docker executable and daemon socket absent; CapEff=0; rootless unshare -Ur fails with uid_map Operation not permitted. Installed FalkorDB client gets Connection refused on localhost:6379. All real-container spikes remain unexecuted."
    },
    "wcc": {
      "status": "BLOCKED",
      "error": "Docker executable and daemon socket absent; CapEff=0; rootless unshare -Ur fails with uid_map Operation not permitted. Installed FalkorDB client gets Connection refused on localhost:6379. All real-container spikes remain unexecuted."
    },
    "cdlp": {
      "status": "BLOCKED",
      "error": "Docker executable and daemon socket absent; CapEff=0; rootless unshare -Ur fails with uid_map Operation not permitted. Installed FalkorDB client gets Connection refused on localhost:6379. All real-container spikes remain unexecuted."
    },
    "shortest_path": {
      "status": "BLOCKED",
      "error": "Docker executable and daemon socket absent; CapEff=0; rootless unshare -Ur fails with uid_map Operation not permitted. Installed FalkorDB client gets Connection refused on localhost:6379. All real-container spikes remain unexecuted."
    },
    "zero_hop": {
      "status": "BLOCKED",
      "error": "Docker executable and daemon socket absent; CapEff=0; rootless unshare -Ur fails with uid_map Operation not permitted. Installed FalkorDB client gets Connection refused on localhost:6379. All real-container spikes remain unexecuted."
    },
    "multi_statement": {
      "status": "BLOCKED",
      "error": "Docker executable and daemon socket absent; CapEff=0; rootless unshare -Ur fails with uid_map Operation not permitted. Installed FalkorDB client gets Connection refused on localhost:6379. All real-container spikes remain unexecuted."
    },
    "graph_copy": {
      "status": "BLOCKED",
      "error": "Docker executable and daemon socket absent; CapEff=0; rootless unshare -Ur fails with uid_map Operation not permitted. Installed FalkorDB client gets Connection refused on localhost:6379. All real-container spikes remain unexecuted."
    },
    "concurrency": {
      "status": "BLOCKED",
      "error": "Docker executable and daemon socket absent; CapEff=0; rootless unshare -Ur fails with uid_map Operation not permitted. Installed FalkorDB client gets Connection refused on localhost:6379. All real-container spikes remain unexecuted."
    },
    "latency": {
      "status": "BLOCKED",
      "error": "Docker executable and daemon socket absent; CapEff=0; rootless unshare -Ur fails with uid_map Operation not permitted. Installed FalkorDB client gets Connection refused on localhost:6379. All real-container spikes remain unexecuted."
    }
  },
  "blocker": "Docker executable and daemon socket absent; CapEff=0; rootless unshare -Ur fails with uid_map Operation not permitted. Installed FalkorDB client gets Connection refused on localhost:6379. All real-container spikes remain unexecuted."
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

## Interpretation

All fixtures are synthetic. Timing uses perf_counter_ns and includes network/client overhead.
Concurrent client intervals and atomic increments do not prove engine scheduling internals.
Read/write overlap is an observed completion interval, not a promise of snapshot semantics.
Q6 ordered requests need retry recovery; they are not atomic together.

## Next phase — only after this gate passes

1. Check topology source licenses and encode the credited YAML cores.
2. Implement seed=42 loader and the ADR-17/R-7/R-12 planted scenario.
3. Implement Q2/Q3/Q4/Q7 and run planted-scenario acceptance assertions.
