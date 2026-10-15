# Hindsight

The on-call crew that remembers every outage, knows who really knows, and refuses
to trust its own stale memory.

Fresh Graph Hacks project, started 2026-10-15. Planned tracks: Agents That Act on
Connected Data, Agent Memory and Coordination, and Company Brain. This is currently
**Phase 0 scaffolding**, not a working application or a completed track claim.

## Phase gate

Phase 0 is BLOCKED: this workspace has no Docker executable or daemon socket,
and cannot create a rootless user namespace. No real FalkorDB spike has run.
See [docs/VERIFIED.md](docs/VERIFIED.md). Phase 1 must not start until the acceptance
report says PASS. Documentation evidence is separate from runtime verification.

## Run Phase 0 on a Docker host

Requires Docker Engine with Compose v2. FalkorDB is not exposed on any host port.

```sh
docker compose up -d --wait falkordb
docker compose --profile verify run --rm spikes
```

The second command writes `docs/phase0-results.json` and `docs/VERIFIED.md`.
It exits nonzero if a required check fails. Optional feature failures are accepted
only when their listed fallback is successfully exercised. It uses the requested
`latest` image; record/pin its digest before later phases:

```sh
docker image inspect falkordb/falkordb:latest --format '{{index .RepoDigests 0}}'
```

Set `FALKORDB_IMAGE=falkordb/falkordb@sha256:...` to rerun the same version.
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

## Known limitations / fallback plan

- Q6 will use ordered, retry-idempotent requests; two requests are **not an atomic
  transaction**. Recovery and serialization must be designed and tested in Phase 2.
- If `GRAPH.COPY` is unavailable, replay statements into a new graph; benchmark it.
- If betweenness is unavailable, use PageRank plus path counts and disclose the approximation.
- If WCC label projection is unavailable, compute connectivity from Cypher adjacency.
  CDLP is not equivalent to disconnected components.
- If bound `shortestPath` syntax fails, use a verified alternate form or bounded
  traversal with minimum length; if zero-hop fails, include alert nodes separately.
- Single-graph write serialization has not been measured; do not claim throughput
  scaling or simultaneous read execution until the harness supplies evidence.
- No cross-graph queries; ID references are composed in the application layer.
- Seed RDB, application, UI, deployment and submission assets are deferred to their phases.

## Build order

0. Container spikes and scaffolding (blocked).
1. Schema/loader/planted seed and core query acceptance.
2. Memory/coordination and concurrency acceptance.
3. Policy agents, MCP and answer provenance.
4. API, SSE and war-room UI.
5. Evaluation, scale and deployment.
6. Submission and bug bash; feature freeze Oct 18, 18:00 IST.

See [AI disclosure](docs/AI_USE.md), [model status](docs/DATA_MODEL.md), and
[query status](docs/QUERIES.md). Track claims will be added only when implemented.
