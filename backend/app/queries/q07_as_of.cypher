MATCH (a:Service)-[r:DEPENDS_ON|DEPENDED_ON]->(b:Service)
WHERE r.valid_from <= $t AND (r.valid_to IS NULL OR r.valid_to > $t)
RETURN a.id AS a, b.id AS b, r.fact_id AS fact_id
