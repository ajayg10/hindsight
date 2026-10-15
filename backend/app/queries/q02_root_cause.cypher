UNWIND $alerting AS sid
MATCH p = (a:Service {id:sid})-[:DEPENDS_ON*0..5]->(c:Service)
WITH c, count(DISTINCT a) AS hits, min(length(p)) AS nearest
WHERE hits = size($alerting)
RETURN c.id AS id, c.name AS name, nearest, c.pagerank AS pr
ORDER BY nearest ASC, pr DESC LIMIT 5
