# Hindsight Graph Data Model & Evidence Calibration

## Overview & Graph Hierarchy
Hindsight maintains graph-native state partitioned across three tenant graph tiers:
1. **Tenant Business & Infrastructure Graph (`t:{tenant}`)**: Canonical company brain containing service dependency topology, decision records (ADRs), incident history, runbooks/procedures, and employee expertise.
2. **Session / Incident Ephemeral Graph (`s:{session}`)**: Fork created via `GRAPH.COPY` for sandboxed remediation plans, counterfactual what-if simulation, and isolated agent hypothesis exploration.
3. **Operator Personal Graph (`u:{tenant}:{user}`)**: Operator preferences, pending approval queues, and notification digests.

Cross-graph interactions occur via application composition and the MCP tool interface; agents never execute cross-graph Cypher queries directly.

---

## Node & Relationship Types

### 1. Topology & Architecture
- `(:Service {id, name, tier, rev_per_min, pagerank, betweenness, status})`
- `(:Service)-[:DEPENDS_ON {protocol, timeout_ms, kind}]->(:Service)`: Active runtime runtime dependency.
- `(:Service)-[:DEPENDED_ON {retired_at, adr}]->(:Service)`: Historical / closed dependency.
- `(:Service)-[:OWNS {valid_from}]->(:Team)`

### 2. Organizational Memory & Provenance
- `(:Person {id, name, email, role, on_call, on_leave, tz})`
- `(:Team {id, name, slack_channel})`
- `(:Person)-[:MEMBER_OF]->(:Team)`
- `(:Doc {id, title, kind, last_verified_at, content_ref})`
- `(:Thread {id, title, channel})`
- `(:Message {id, text, at})`
- `(:Decision {id, title, at})`
- `(:Change {id, at, kind})`
- **Lineage Edges**:
  - `(:Person)-[:AUTHORED]->(:Doc|:Message|:Decision)`
  - `(:Decision)-[:LED_TO]->(:Change)`
  - `(:Decision)-[:RECORDED_IN]->(:Doc)`
  - `(:Decision)-[:DISCUSSED_IN]->(:Thread)`
  - `(:Message)-[:IN]->(:Thread)`
  - `(:Message)-[:MENTIONS]->(:Service)`
  - `(:Doc)-[:DESCRIBES]->(:Service)`
  - `(:Change)-[:AFFECTS]->(:Service)`

### 3. Procedures & Operational Memory
- `(:FailureMode {key, name})`
- `(:Procedure {id, name, status, version, last_validated_at})`
- `(:Step {ord, tool, params})`
- `(:Procedure)-[:APPLIES_TO]->(:FailureMode)`
- `(:Procedure)-[:HAS_STEP]->(:Step)`
- `(:Step)-[:TARGETS]->(:Service)`
- `(:Episode {id, kind, outcome, t_start, t_end})`
- `(:Episode)-[:USED {outcome, at}]->(:Procedure)`
- `(:Episode)-[:INVOLVED]->(:Service)`
- `(:Person)-[:RESOLVED]->(:Episode)`

### 4. Facts & Temporal Knowledge (Q6 Triples)
- `(:Fact {id, subject, predicate, object, confidence, valid_from, valid_to, status, applied, source_id, kind})`
- `(:Fact)-[:SUPERSEDES]->(:Fact)`
- `(:Fact)-[:SUPPORTED_BY]->(:Doc|:Episode|:Message)`

### 5. Coordination & Task Execution (Track 02)
- `(:Agent {id, role, status, heartbeat_at})`
- `(:Incident {id, status, severity, created_at, blast_radius})`
- `(:Task {id, kind, status, version, lease_until, payload})`
- `(:Hypothesis {id, incident, status, confidence, heuristic})`
- `(:Agent)-[:CLAIMED {at, lease_ms, version}]->(:Task)`
- `(:Agent)-[:HANDED_OFF_TO {at, evidence_ids}]->(:Agent)`
- `(:Hypothesis)-[:ROOT]->(:Service)`
- `(:Hypothesis)-[:SUBSUMES {hops}]->(:Hypothesis)`

### 6. Answer Provenance & MCP Auditing (Track 01 / 03)
- `(:Answer {id, tool, cypher_name, policy_rule_id, created_at, summary})`
- `(:Answer)-[:USED]->(:Service|:Doc|:Person|:Procedure|:Fact|:Change)`: Traceable evidence nodes backing the answer.

---

## EXPERT_IN Score Derivation & Calibration

The `(:Person)-[:EXPERT_IN]->(:Service)` relationship is **derived by graph traversal**, not hand-written. The Librarian maintenance worker recomputes expertise scores across the evidence graph.

### 1. Evidence Paths & Weights
The score aggregates three distinct forms of operational evidence:
1. **Authored Documentation ($w_{doc} = 0.35$)**:
   `MATCH (p:Person)-[:AUTHORED]->(d:Doc)-[:DESCRIBES]->(s:Service)`
   Captures documented design authority and architectural ownership.
2. **Resolved Incidents ($w_{inc} = 0.45$)**:
   `MATCH (p:Person)-[:RESOLVED]->(e:Episode {outcome:'success'})-[:INVOLVED]->(s:Service)`
   Captures recent hands-on debugging, firefighting, and operational experience.
3. **Recorded Design Discussions / Tickets ($w_{msg} = 0.20$)**:
   `MATCH (p:Person)-[:AUTHORED]->(m:Message)-[:MENTIONS]->(s:Service)`
   Captures active participation in technical proposals and architecture threads.

### 2. Bounded Exponential Saturation Formula
To prevent score inflation while ensuring mathematical bounding on $[0, 1)$ with diminishing returns, scores are computed using a bounded exponential saturation model:

$$\text{score} = 1 - \exp(-k \cdot E)$$

Where:
- $E = N_{doc} + N_{inc} + N_{msg}$: Total evidence count across authored documents, resolved incidents, and architecture discussion messages.
- $k = 0.17$: Exponential decay/saturation constant calibrated to benchmark domain evidence.
- The score is rounded to two decimal places: $\text{round}((1.0 - \exp(-0.17 \cdot E)) \cdot 100.0) / 100.0$.
- Mathematical properties:
  - $\text{score}(0) = 0.0$ (no unearned expertise).
  - $\lim_{E \to \infty} \text{score}(E) = 1.0$ (strictly bounded, immune to asymptotic overflow).
  - Monotonically strictly increasing ($\frac{d}{dE} > 0$).
  - Naturally produces diminishing returns per incremental evidence item.

### 3. Seed Calibration Disclosure
> [!NOTE]
> **Synthetic Calibration Notice**:
> The operational evidence subgraph in `seed/plant.py` seeds concrete evidence nodes:
> - **Priya Sharma**: 2 authored docs (`doc-adr-17`, `doc-cache-b-spec`), 2 resolved incidents (`INC-0301`, `INC-0342`), and 10 architecture messages (`msg-priya-adr17`, `msg-priya-1..9`), giving total evidence count $E=14$.
>   $$\text{score} = 1 - \exp(-0.17 \times 14) = 1 - \exp(-2.38) = 1 - 0.09255 \approx \mathbf{0.91}$$
> - **Marco Rossi**: 1 authored runbook (`doc-cache-b-ops`), 2 resolved incidents (`INC-0412`, `INC-0377`), and 5 operational tuning messages (`msg-marco-1..5`), giving total evidence count $E=8$.
>   $$\text{score} = 1 - \exp(-0.17 \times 8) = 1 - \exp(-1.36) = 1 - 0.25666 \approx \mathbf{0.74}$$
> - **Alex Chen**: 0 evidence items on `cache-b`, yielding score $0.0$.
>
> When Priya is on leave (`status: 'leave'`), the routing policy dynamically reroutes requests to the next highest scoring active expert (Marco, 0.74). The scores are derived directly by query traversal and verifiable via `q04_who_knows.cypher`. No hardcoded names or literals exist in the calculation engine.
