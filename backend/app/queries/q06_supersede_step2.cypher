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
RETURN r.fact_id AS live_edge_fact_id
