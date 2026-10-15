# AI assistance disclosure

## Phase 0 — 2026-10-15

OpenAI Codex assisted with repository scaffolding, Docker Compose configuration,
reading the official FalkorDB documentation, drafting the verification harness,
and documenting runtime blockers.

Google Antigravity assisted with connecting to the Docker daemon via WSL2 host,
orchestrating container builds, executing the verification suite against live
FalkorDB `latest` (`sha256:b0bdcac2cbaff989e77cb0610439b7a9289e86de033ccbbd4368b66fb680ae7a`),
and recording verified runtime evidence in `docs/VERIFIED.md`.
No runtime outcome or benchmark was invented. All metrics (p50/p95 latency,
concurrency race results, algorithm outputs) were measured directly by the harness.

All generated code must be reviewed and explained by the participant before submission.
No external LLM inference, private data, or generated narration is used by this scaffold.

## Phase 1 — 2026-10-15

Google Antigravity assisted with:
- Encoding topology YAML files under `seed/topology/` credited to Google Online Boutique (Apache 2.0) and Weaveworks Sock Shop (Apache 2.0).
- Hand-authoring `seed/plant.py` golden slice (~25 core services) with exact invariants: ADR-17 at clock - 6 days, 9 alerting services with common ancestor `cache-b`, strictly 14 services in blast radius, R-7 stale, R-12 valid, Priya (0.91, leave) routing to Marco (0.74, active), and 3 stale docs.
- Writing Cypher queries (`q02_root_cause.cypher`, `q03_blast_radius.cypher`, `q04_who_knows.cypher`, `q04_who_knows_all.cypher`, `q07_as_of.cypher`, `q07_diff.cypher`, `q10_conflict.cypher`, `critical_path.cypher`).
- Writing and executing `scripts/test_phase1.py` against the live FalkorDB container, asserting all 6 acceptance criteria.
- Implementing `seed/gen.py` to enrich the topology to 58 services with filler docs and services while preserving all golden slice invariants.
- Updating `docs/VERIFIED.md` and `docs/QUERIES.md` with write serialization findings, WCC projection details, Q10 WITH-form rewrite, and Q6 three-step idempotent redesign.


