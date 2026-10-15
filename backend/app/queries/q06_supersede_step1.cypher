OPTIONAL MATCH (old:Fact {subject:$s, predicate:$p, status:'current'})
WHERE old.object <> $o
SET old.status = 'superseded', old.valid_to = $now
MERGE (new:Fact {id:$new_id})
ON CREATE SET new.subject = $s, new.predicate = $p, new.object = $o,
              new.status = 'current', new.confidence = $conf, new.valid_from = $now, new.applied = false
WITH new, [o IN collect(old) WHERE o IS NOT NULL] AS old_facts
FOREACH (o IN old_facts |
    CREATE (new)-[:SUPERSEDES {reason:$reason}]->(o)
)
WITH new
MATCH (src {id:$source_id})
MERGE (new)-[:SUPPORTED_BY]->(src)
RETURN new.id AS fact_id
