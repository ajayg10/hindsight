MATCH (t:Task {id:$task}), (f:Agent {id:$from}), (to:Agent {id:$to})
WHERE t.claimed_by = $from
SET t.claimed_by = $to, t.version = t.version + 1
CREATE (h:Handoff {id:$hid, at:$now, reason:$reason})
CREATE (h)-[:FROM]->(f), (h)-[:TO]->(to), (h)-[:FOR]->(t)
WITH h
UNWIND $packet_ids AS nid
MATCH (n {id:nid})
CREATE (h)-[:CARRIES]->(n)
RETURN h.id AS handoff_id, count(n) AS carried
