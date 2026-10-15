MATCH (t:Task {id:$task})
WHERE t.status = 'open' OR (t.status = 'claimed' AND t.lease_until < $now)
SET t.status = 'claimed', t.claimed_by = $agent,
    t.lease_until = $now + $lease_ms, t.version = t.version + 1
WITH t
MATCH (a:Agent {id:$agent})
CREATE (a)-[:CLAIMED {version:t.version, at:$now}]->(t)
RETURN t.id, t.version
