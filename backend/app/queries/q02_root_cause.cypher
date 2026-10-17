UNWIND $alerting AS sid
MATCH p = (a:Service {id:sid})-[:DEPENDS_ON*0..5]->(c:Service)
WITH c, count(DISTINCT a) AS hits, min(length(p)) AS nearest
WHERE hits >= ceil(size($alerting) * 0.5) OR hits >= 2
RETURN c.id AS id, c.name AS name, nearest, c.pagerank AS pr, hits, size($alerting) AS total_alerts
ORDER BY hits DESC, nearest ASC, pr DESC LIMIT 5
