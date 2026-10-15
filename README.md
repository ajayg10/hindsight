# Hindsight

The on-call crew that remembers every outage, knows who really knows, and refuses
to trust its own stale memory.

Fresh Graph Hacks project, started 2026-10-15. Planned tracks: Agents That Act on
Connected Data, Agent Memory and Coordination, and Company Brain. This is currently
**Phase 0 scaffolding**, not a working application or a completed track claim.

## Phase gate

Phase 0 has **PASSED**: verified against a live FalkorDB engine container on 2026-10-15.
All 11 checks passed or had their verified fallbacks confirmed.
See [docs/VERIFIED.md](docs/VERIFIED.md) and [docs/phase0-results.json](docs/phase0-results.json).

Pinned engine image digest:
```
falkordb/falkordb@sha256:b0bdcac2cbaff989e77cb0610439b7a9289e86de033ccbbd4368b66fb680ae7a
```

## Run Phase 0 on a Docker host

Requires Docker Engine with Compose v2. FalkorDB is not exposed on any host port.

```sh
docker compose up -d --wait falkordb
docker compose --profile verify run --rm spikes
```

The second command writes `docs/phase0-results.json` and `docs/VERIFIED.md`.
It exits nonzero if a required check fails. Optional feature failures are accepted
only when their listed fallback is successfully exercised. Pinned digest:
`FALKORDB_IMAGE=falkordb/falkordb@sha256:b0bdcac2cbaff989e77cb0610439b7a9289e86de033ccbbd4368b66fb680ae7a`.
For a host Python client, use the loopback-only override:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --wait
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-spikes.txt
.venv/bin/python scripts/phase0.py
```

Disposable spike graphs use `spike:` names and are removed in `finally`.
No benchmark is currently reported. Latency samples are client round trips on a
synthetic 58-service fixture, not production latency. The race harness uses real
concurrent client threads with no application claim mutex. Atomic increments and
read/write completion observations do not alone prove internal write serialization.

## Architecture — planned

React/Cytoscape UI → FastAPI/SSE → shared MCP tool registry → FalkorDB tenant graph.
Async policy workers will call the same registry and coordinate through graph state.
TF-IDF will be a separate Graph OFF comparison using the same synthetic documents.
Actions will be simulated and approval gated.

## Data and reproducibility

Phase 0 fixture is fully synthetic, generated with seed 42; it is not the company
seed or an 18-month simulation. No public topology has been imported yet; license
checks and credits are required before Phase 1. `DemoClock` freezes synthetic
business time at 2026-10-15 03:11 IST. Real wall time is used only for measurements.
Priya and Marco will be fictional character aliases, not records of real people.

## Known limitations / verified engine behavior

- **Single-graph write serialization**: FalkorDB serializes writes within a single graph via its per-graph write lock. Concurrent read-only queries during ongoing writes are supported via snapshot isolation.
- **Q6 Fact supersession**: Broken into 3 idempotent requests with `Fact.applied: false` guard and Librarian sweep, since FalkorDB does not support multi-statement single queries.
- **Q10 & critical_path**: Uses `WITH shortestPath(...) AS p WHERE p IS NOT NULL` syntax, which correctly resolves path hops when connected and evaluates to `NULL` for disconnected multi-fault incidents.
- **Betweenness & WCC**: Native `algo.betweenness` and `algo.WCC` (via `:Alerting` label projection) work natively.
- **Tenancy**: No cross-graph Cypher queries; ID references are composed in the application layer.

## Build order

0. Container spikes and scaffolding (PASSED).
1. Schema/loader/planted seed and core query acceptance (PASSED).
2. Memory/coordination and concurrency acceptance.
3. Policy agents, MCP and answer provenance.
4. API, SSE and war-room UI.
5. Evaluation, scale and deployment.
6. Submission and bug bash; feature freeze Oct 18, 18:00 IST.

See [AI disclosure](docs/AI_USE.md), [model status](docs/DATA_MODEL.md), and
[query status](docs/QUERIES.md). Track claims will be added only when implemented.
