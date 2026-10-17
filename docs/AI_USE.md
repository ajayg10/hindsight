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

## Phase 4a — 2026-10-16

Google Antigravity assisted with:
- Implementing CLI and live storm runner in `scripts/run_storm.py` supporting both `--mode demo` (paced output) and `--mode fast`.
- Implementing FastAPI war room backend in `backend/app/main.py` providing `/api/graph` (Cytoscape elements), `/api/events` (SSE real-time stream), `/api/storm/run`, `/api/storm/approve`, and `/api/explain/{answer_id}`.
- Building modern, responsive war room UI (`frontend/index.html`, `frontend/index.css`, `frontend/app.js`) with Cytoscape.js interactive topology canvas, 6 agent crew lanes, live SSE terminal ticker, and operator approval gate.
- Updating `docker-compose.yml` to declare the `web` service on port 8000.
- Writing and executing `scripts/test_phase4a.py` verifying all endpoints, Cytoscape graph serialization, and storm execution.

## Phase 4b — 2026-10-16

Google Antigravity assisted with:
- Implementing pure-Python TF-IDF comparison engine in `backend/app/baseline.py` demonstrating Graph OFF (keyword similarity recommending stale R-7) vs Graph ON (Hindsight policy refusing R-7 due to ADR-17 and executing R-12).
- Implementing Time Scrubber API (`/api/timeline/as-of`) for interactive counterfactual switching between legacy Pre-ADR-17 (`checkout-api -> cache-a`) and current architecture.
- Implementing counterfactual session fork creation via native FalkorDB `GRAPH.COPY` (`/api/fork/create`) with measured copy latency (< 70ms) and verified fork isolation (mutations in a fork do not affect the source, and vice versa).
- Implementing Organizational Memory summary API (`/api/memory/summary`) across episodic, architectural, and social graph memories.
- Implementing interactive Why Drawer in the frontend with syntax-highlighted Cypher, policy badge, and linked evidence subgraphs.
- Building Graph OFF vs ON comparison modal and Organizational Memory Explorer modal in the frontend war room.
- Writing and executing `scripts/test_phase4b.py` confirming 100% test pass on live FalkorDB engine.

## Idea Evaluation, Spec & Build Prompt Formulation — 2026-10-15

Large language models (OpenAI ChatGPT & Claude) assisted the project author with:
- Brainstorming and stress-testing the initial project concept against the hackathon tracks (Connected Data, Memory & Coordination, Company Brain).
- Refining architectural trade-offs: evaluating FalkorDB native capabilities (GRAPH.COPY, single-graph serialization, algo.pageRank/betweenness) against multi-tenant operational graph requirements.
- Drafting and formalizing the engineering specification, acceptance criteria, and golden invariant constraints (14-service blast radius, ADR-17 validity, Priya on leave routing to Marco, R-7 stale vs R-12 valid).
- Structuring the multi-phase prompt strategy to ensure verifiable test gates and avoid premature feature claims.

All architectural decisions, graph schemas, algorithm selection, and policy rules were directed and approved by the project author.

## Hardening & Deployment — 2026-10-17

Google Antigravity assisted with:
- Fixing Investigator-A heuristic scoring formula to accurately produce 1.00 at 1 hop and 0.95 at 2 hops, logging concrete formula inputs, and adding unit tests with partial coverage.
- Renaming both investigator score outputs from "confidence" to "heuristic score" across backend tools, events, and UI badges.
- Disclosing the calibration of parameter $k=0.17$ in $1 - \exp(-k \cdot E)$ for `EXPERT_IN` derived scores to match seeded evidence.
- Anchoring all fact ledger validity dates strictly to `DemoClock.frozen()` (asserting ADR-17 `valid_to == clock - 6 days`).
- Building production deployment architecture (`docker-compose.prod.yml`, `Caddyfile`, `deploy.sh`) featuring internal-only FalkorDB network, unbuffered reverse-proxying for SSE (`flush_interval -1`), and automatic TLS via Caddy.
- Implementing per-visitor session isolation via `POST /api/session` creating `s:{session_id}` forks via native `GRAPH.COPY` (< 55ms) with 30-minute TTL cleanup.
- Implementing caller-scoped session Reset that re-copies the fork without ever mutating the golden tenant graph (`t:parcelo`).
- Adding visible top-bar toggle for Graph OFF / Graph ON with warning banners and live session fork status chips.
- Adding API rate-limiting (120 req/min), Race worker cap (32 max), SSE keepalive heartbeats, and securing the public `/mcp` server in read-only mode (`persist_answer=False`).

## Scale Enrichment & Synthetic Baseline Benchmark — 2026-10-17

Google Antigravity assisted with:
- Enriching the `t:parcelo` seed to ~3,000 nodes (2,846 nodes, 6,933 edges) using batched UNWIND Cypher queries across 15 engineers, 300 docs, 500 threads, 2,000 messages, and 120 past incident episodes.
- Authoring `scripts/verify_enriched_invariants.py` strictly verifying that all 4 golden invariants remain 100% intact at scale (14-service blast radius, 3 stale docs, Priya 0.91 / Marco 0.74 routing, and R-7 refused / R-12 selected), and measuring multi-hop traversal latency at scale (p50: 0.385 ms, p95: 0.636 ms, N=50).
- Expanding the 20-storm evaluation harness (`backend/eval/storms.py`) to benchmark Hindsight against a flat keyword/TF-IDF baseline across both Dev (Storms 1..10) and Held-Out (Storms 11..20) sets.
- Reporting all benchmark metrics honestly with synthetic storm labeling (Top-1: 55.6%-66.7%, Top-3: 100.0%, Who-to-Page: 94.4%, Blast Recall: 95.6%, Multi-Fault: 100% vs Baseline: 0.0% root-cause, 0.0% who-to-page).
