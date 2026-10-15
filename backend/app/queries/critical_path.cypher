MATCH (a:Service {id:$a}), (b:Service {id:$b})
WITH a, b, shortestPath((a)-[:DEPENDS_ON*1..10]->(b)) AS p
WHERE p IS NOT NULL
RETURN p, length(p) AS hops
