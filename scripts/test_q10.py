from falkordb import FalkorDB

def main():
    db = FalkorDB(host="falkordb", port=6379)
    g = db.select_graph("spike:q10_test")
    try:
        g.query("CREATE (:Service {id:'s1'}), (:Service {id:'s2'}), (:Service {id:'s3'})")
        g.query("MATCH (s1:Service {id:'s1'}), (s2:Service {id:'s2'}) CREATE (s2)-[:DEPENDS_ON]->(s1)")
        g.query("""
        MATCH (s1:Service {id:'s1'}), (s2:Service {id:'s2'}), (s3:Service {id:'s3'})
        CREATE (h1:Hypothesis {id:'h1', incident:'inc1', status:'open'})-[:ROOT]->(s1),
               (h2:Hypothesis {id:'h2', incident:'inc1', status:'open'})-[:ROOT]->(s2),
               (h3:Hypothesis {id:'h3', incident:'inc1', status:'open'})-[:ROOT]->(s3)
        """)

        print("Hypotheses:", g.query("MATCH (h:Hypothesis)-[:ROOT]->(s:Service) RETURN h.id, s.id").result_set)
        print("Edges:", g.query("MATCH (a:Service)-[r:DEPENDS_ON]->(b:Service) RETURN a.id, b.id").result_set)

        # Exact user Q10 query:
        q10 = """
        MATCH (h1:Hypothesis {incident:$inc, status:'open'})-[:ROOT]->(s1:Service),
              (h2:Hypothesis {incident:$inc, status:'open'})-[:ROOT]->(s2:Service)
        WHERE h1.id <> h2.id
        WITH h1, h2, shortestPath((s2)-[:DEPENDS_ON*1..5]->(s1)) AS p
        WHERE p IS NOT NULL
        RETURN h1.id AS subsuming, h2.id AS subsumed, length(p) AS hops
        """
        res = g.query(q10, {"inc": "inc1"})
        print("Q10 with path result:", res.result_set)
        assert res.result_set == [["h1", "h2", 1]], f"Unexpected result: {res.result_set}"

        # Test no-path case:
        q_nopath = """
        MATCH (h1:Hypothesis {incident:$inc, status:'open'})-[:ROOT]->(s1:Service),
              (h3:Hypothesis {incident:$inc, status:'open'})-[:ROOT]->(s3:Service)
        WHERE h1.id = 'h1' AND h3.id = 'h3'
        WITH h1, h3, shortestPath((s3)-[:DEPENDS_ON*1..5]->(s1)) AS p
        RETURN h1.id, h3.id, p, p IS NOT NULL AS has_path
        """
        res2 = g.query(q_nopath, {"inc": "inc1"})
        print("Q10 no-path result:", res2.result_set)
        assert res2.result_set == [["h1", "h3", None, False]], f"Unexpected: {res2.result_set}"

        print("Q10 VERIFICATION: ALL PASSED!")
    finally:
        try:
            db.connection.execute_command("GRAPH.DELETE", "spike:q10_test")
        except Exception:
            pass

if __name__ == "__main__":
    main()
