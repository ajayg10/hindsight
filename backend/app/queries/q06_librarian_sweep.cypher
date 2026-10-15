MATCH (f:Fact {status:'current', applied:false})
RETURN f.id AS id, f.subject AS s, f.predicate AS p, f.object AS o, f.valid_from AS valid_from
