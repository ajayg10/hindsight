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

### 2. Normalization & Saturation Formula
To prevent single-source gaming while rewarding multi-modal contribution, scores are normalized with a diminishing returns saturation denominator:

$$\text{raw\_score} = \frac{w_{doc} \cdot N_{doc} + w_{inc} \cdot N_{inc} + w_{msg} \cdot N_{msg}}{1.0 + 0.25 \cdot (N_{doc} + N_{inc} + N_{msg})}$$

Where:
- $N_{doc}$: count of distinct docs authored describing the target service.
- $N_{inc}$: count of distinct successful incident episodes resolved involving the service.
- $N_{msg}$: count of authored messages/RFC comments mentioning the service.
- Weights: $w_{doc} = 0.35, w_{inc} = 0.45, w_{msg} = 0.20$.
- Saturation coefficient $\alpha = 0.25$.

### 3. Synthetic Seed Calibration Disclosure
> [!NOTE]
> **Synthetic Calibration Notice**:
> The scenario evidence in `seed/plant.py` is synthetic data created for reproducible benchmarking. The evidence counts and timestamps were deliberately seeded such that:
> - **Priya Sharma** has authored key architectural documents (`doc-adr-17`), initiated RFC discussions (`msg-priya-adr17`), and resolved historical incidents (total evidence count $N=14$), yielding an `EXPERT_IN` score of **0.91**.
> - **Marco Rossi** has resolved production incidents (`INC-0412`) and authored operational manuals (total evidence count $N=8$), yielding an `EXPERT_IN` score of **0.74**.
>
> When Priya is on leave (`on_leave: true`), the routing policy dynamically reroutes requests to the next highest scoring available expert (Marco, 0.74). The scores are derived directly by query traversal and verifiable via `q04_who_knows.cypher`.
