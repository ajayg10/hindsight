MATCH (fm:FailureMode {key:$fm})<-[:APPLIES_TO]-(pr:Procedure)
WHERE pr.status IN ['trusted','candidate']
OPTIONAL MATCH (pr)-[:HAS_STEP]->(:Step)-[:TARGETS]->(:Service)<-[:AFFECTS]-(c:Change)
WHERE c.at > pr.last_validated_at
WITH pr, count(DISTINCT c) AS invalidating, collect(DISTINCT c.id) AS invalidating_changes
OPTIONAL MATCH (:Episode)-[u:USED]->(pr)
WITH pr, invalidating, invalidating_changes,
     sum(CASE WHEN u.outcome = 'success' THEN 0.5 ^ (($now - u.at)/$hl) ELSE 0 END) AS wins,
     sum(0.5 ^ (($now - u.at)/$hl)) AS total
RETURN pr.id AS id, pr.name AS name, (wins + 1.0)/(total + 2.0) AS win_rate, invalidating, invalidating_changes
ORDER BY invalidating ASC, win_rate DESC
