MATCH (h1:Hypothesis {incident:$inc, status:'open'})-[:ROOT]->(s1:Service),
      (h2:Hypothesis {incident:$inc, status:'open'})-[:ROOT]->(s2:Service)
WHERE h1.id <> h2.id
WITH h1, h2, shortestPath((s2)-[:DEPENDS_ON*1..5]->(s1)) AS p
WHERE p IS NOT NULL
RETURN h1.id AS subsuming, h2.id AS subsumed, length(p) AS hops, p
