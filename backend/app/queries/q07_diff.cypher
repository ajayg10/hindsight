MATCH (a:Service)-[r:DEPENDED_ON]->(b:Service)
WHERE r.valid_from <= $t1 AND r.valid_to > $t1 AND r.valid_to <= $t2
RETURN a.id AS removed_from, b.id AS removed_to, r.ended_by AS ended_by
