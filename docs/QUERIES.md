# Query verification status and design

## Status Summary

- **Q1 (Atomic task claim)**: VERIFIED (Phase 0 concurrency test: 20 workers, 8 tasks, 0 double claims).
- **Q2 (Root-cause candidates)**: Stays as written (`*0..5` verified natively).
- **Q3 (Blast radius)**: Ready for Phase 1 golden slice.
- **Q4 (Who knows)**: Ready for Phase 1 golden slice (Priya on leave -> Marco reroute).
- **Q5 (Trace decision)**: Ready for Phase 2/3.
- **Q6 (Fact supersession & live edge transition)**: **Redesigned into 3 idempotent requests** (FalkorDB does not support multi-statement single queries).
- **Q7 (Time travel & diff)**: Ready for Phase 1 golden slice.
- **Q8 (Procedure recall & invalidation)**: Ready for Phase 2.
- **Q9 (Handoff with context packet)**: Ready for Phase 2.
- **Q10 (Hypothesis conflict by path subsumption)**: **Rewritten to WITH-form** (verified in FalkorDB; handles both path subsumption and disconnected multi-fault).
- **critical_path**: **Rewritten to WITH-form**.

---

## Query Redesigns & Formats

### Q6: Three Idempotent Requests (Fact Supersession & Edge Transition)

Because FalkorDB rejects multi-statement queries in a single round-trip, Q6 is broken into three idempotent steps with an `applied: false` guard:

#### Request 6a: Create the new Fact with `applied: false` and close the old fact
```cypher
MATCH (old:Fact {subject:$s, predicate:$p, status:'current'})
WHERE old.object <> $o
SET old.status = 'superseded', old.valid_to = $now
CREATE (new:Fact {id:$new_id, subject:$s, predicate:$p, object:$o,
                  status:'current', confidence:$conf, valid_from:$now, applied:false})
CREATE (new)-[:SUPERSEDES {reason:$reason}]->(old)
WITH new
MATCH (src {id:$source_id})
CREATE (new)-[:SUPPORTED_BY]->(src)
RETURN new.id
```
*(If no prior fact exists, 6a creates the new Fact directly with `applied: false`).*

#### Request 6b: Close the old live edge into history and MERGE the new live edge
```cypher
OPTIONAL MATCH (a:Service {id:$a})-[old_edge:DEPENDS_ON]->(b_old:Service)
WHERE old_edge.fact_id = $old_fact_id OR old_edge.ended_by IS NULL
FOREACH (_ IN CASE WHEN old_edge IS NOT NULL THEN [1] ELSE [] END |
    CREATE (a)-[:DEPENDED_ON {valid_from:old_edge.valid_from, valid_to:$now,
                              fact_id:old_edge.fact_id, ended_by:$source_id}]->(b_old)
    DELETE old_edge
)
WITH a
MATCH (b_new:Service {id:$b})
MERGE (a)-[r:DEPENDS_ON {fact_id:$new_id}]->(b_new)
ON CREATE SET r.valid_from = $now, r.kind = $kind
```

#### Request 6c: Mark fact as applied
```cypher
MATCH (f:Fact {id:$new_id})
SET f.applied = true
RETURN f.id, f.applied
```

#### Librarian Repair Sweep (replays 6b-6c for any unapplied fact)
```cypher
MATCH (f:Fact {status:'current', applied:false})
RETURN f.id, f.subject, f.predicate, f.object, f.valid_from
```

---

### Q10: Hypothesis Conflict by Path Subsumption (Rewritten WITH-form)

Verified on FalkorDB: `shortestPath` must be in a `WITH` or `RETURN` clause.

```cypher
MATCH (h1:Hypothesis {incident:$inc, status:'open'})-[:ROOT]->(s1:Service),
      (h2:Hypothesis {incident:$inc, status:'open'})-[:ROOT]->(s2:Service)
WHERE h1.id <> h2.id
WITH h1, h2, shortestPath((s2)-[:DEPENDS_ON*1..5]->(s1)) AS p
WHERE p IS NOT NULL
RETURN h1.id AS subsuming, h2.id AS subsumed, length(p) AS hops, p
```
- **Connected**: `s2` transitively depends on `s1`, so `h1` subsumes `h2` (`hops >= 1`).
- **No path (Disconnected)**: `p IS NULL`. `WHERE p IS NOT NULL` filters it out cleanly, leaving both hypotheses active as a multi-fault incident.

### critical_path (Rewritten WITH-form)

```cypher
MATCH (a:Service {id:$a}), (b:Service {id:$b})
WITH a, b, shortestPath((a)-[:DEPENDS_ON*1..10]->(b)) AS p
WHERE p IS NOT NULL
RETURN p, length(p) AS hops
```
