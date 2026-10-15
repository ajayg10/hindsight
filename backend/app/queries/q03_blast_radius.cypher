MATCH p = (s:Service {id:$svc})<-[:DEPENDS_ON*1..4]-(d:Service)
WITH d, min(length(p)) AS hops
RETURN d.id AS id, d.tier AS tier, hops, d.rev_per_min AS rev_per_min
ORDER BY hops ASC, d.rev_per_min DESC
