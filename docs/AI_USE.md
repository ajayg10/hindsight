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

