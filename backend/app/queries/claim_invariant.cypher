MATCH (:Agent)-[c:CLAIMED]->(t:Task)
WITH t, c.version AS v, count(*) AS n WHERE n > 1
RETURN count(*)
