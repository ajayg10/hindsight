MATCH (d:Decision {id:$id})
OPTIONAL MATCH p1 = (d)-[:RECORDED_IN]->(:Doc)
OPTIONAL MATCH p2 = (d)-[:DISCUSSED_IN]->(:Thread)<-[:IN]-(:Message)<-[:AUTHORED]-(:Person)
OPTIONAL MATCH p3 = (d)-[:SUPERSEDES*1..3]->(:Decision)
RETURN d.id AS decision_id, d.title AS title, d.at AS at,
       [n IN nodes(p1) | {id: n.id, title: n.title}] AS doc_path,
       [n IN nodes(p2) | {id: n.id, text: coalesce(n.text, n.name, n.id), label: labels(n)[0]}] AS thread_path,
       p3 IS NOT NULL AS has_prior_decision
