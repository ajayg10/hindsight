MATCH (p:Person)-[e:EXPERT_IN]->(s:Service {id:$svc})
WHERE p.status <> 'leave'
WITH p, s, e.score * 0.5 ^ (($now - e.last_evidence_at) / $half_life_ms) AS eff
OPTIONAL MATCH (p)-[:MEMBER_OF]->(t:Team)-[:OWNS]->(s)
RETURN p.id AS id, p.name AS name, eff, t IS NOT NULL AS on_owning_team
ORDER BY eff DESC LIMIT 3
