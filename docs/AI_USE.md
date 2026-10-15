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

## Phase 2 — 2026-10-15

Google Antigravity assisted with:
- Implementing split clock architecture in `backend/app/clock.py`: `DemoClock` for synthetic business timeline and `CoordinationClock` for live agent leasing and heartbeats.
- Implementing coordination Cypher queries: `q01_release.cypher`, `q09_handoff.cypher`, `q08_procedure.cypher`, `q05_trace_decision.cypher`, and Q6 three-step idempotent queries (`q06_supersede_step1.cypher`, `q06_supersede_step2.cypher`, `q06_supersede_step3.cypher`, `q06_librarian_sweep.cypher`).
- Writing `backend/eval/race.py` to test 20-worker concurrency (0 double claims), lease expiry and reclaim, and read latency during writes.
- Implementing `backend/app/librarian.py` to recompute `EXPERT_IN` from evidence paths, sweep unapplied facts, decay aged facts, and induce candidate procedures.
- Writing and executing `scripts/test_phase2.py` asserting all Phase 2 acceptance criteria on the live FalkorDB engine.

## Phase 3 — 2026-10-15

Google Antigravity assisted with:
- Tightening Phase 2 race harness in `backend/eval/race.py`: logging write window timestamps (`write_start`, `write_end`) and each read query's timestamps, strictly asserting that all 20 reads (`N=20`) overlapped inside the write window on the same graph without blocking (measured p50: 0.446 ms, p95: 1.005 ms).
- Documenting the complete graph schema, `EXPERT_IN` derivation formula (weights: doc 0.35, inc 0.45, msg 0.20, saturation 0.25), and disclosing synthetic seeded calibration in `docs/DATA_MODEL.md`.
- Implementing `backend/app/policy.py` encoding the 5 explicit deterministic governance rules (`RULE-01-SPLIT-STORM`, `RULE-02-ROOT-CAUSE`, `RULE-03-INVESTIGATE-CONFLICT`, `RULE-04-GUARDRAIL-BLAST`, `RULE-05-STALE-PROCEDURE-REFUSAL`).
- Implementing `backend/app/events.py` in-process typed event bus with monotonically increasing sequence numbers and pacing modes (`fast` vs `demo`).
- Implementing `backend/app/mcp_server.py` official Python MCP SDK tool registry: strictly separating read-only vs write tools, creating `(:Answer)` nodes with `[:USED]` provenance edges, and providing `explain(answer_id)` for auditability. Creating a public `/mcp` server exposing only read-only tools.
- Implementing asynchronous worker agents in `backend/app/agents/` (`sentinel.py`, `investigator.py` with distinct common-dependency vs betweenness heuristics, `responder.py` with blast radius guardrail and approval gate, `concierge.py` with expert rerouting, and `librarian.py` worker).
- Enforcing architectural isolation via AST analysis in `scripts/test_phase3.py` ensuring agents never import `falkordb`, `redis`, or run raw Cypher.
- Running and verifying the headless end-to-end storm story reproduction and kill-agent lease reclaim in `scripts/test_phase3.py` against live FalkorDB engine.



