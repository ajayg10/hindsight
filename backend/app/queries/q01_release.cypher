MATCH (t:Task {id:$task})
WHERE t.claimed_by = $agent
SET t.status = 'done', t.completed_at = $now
RETURN t.id, t.status
