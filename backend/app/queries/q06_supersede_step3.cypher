MATCH (f:Fact {id:$new_id})
SET f.applied = true
RETURN f.id AS fact_id, f.applied AS applied
