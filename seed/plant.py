#!/usr/bin/env python3
"""
Planted scenario generator for Hindsight golden slice.
Deterministic (seed=42), exact numbers, no hardcoded weekdays.
Credited base: Google Online Boutique & Weaveworks Sock Shop.
"""
import os
import sys
from pathlib import Path

# Ensure backend can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.clock import DemoClock

ALERTING_SERVICES = [
    "mobile-gateway", "web-gateway", "frontend", "edge-router", "adservice",
    "paymentservice", "orders", "checkout-api", "cartservice"
]

SERVICES = [
    # Hubs & Targets
    {"id": "cache-b", "name": "Session Cache Cluster (Redis B)", "tier": "data", "rev_per_min": 25000},
    {"id": "cache-a", "name": "Legacy Cache Node (Redis A - Retired)", "tier": "data", "rev_per_min": 0},
    {"id": "checkout-api", "name": "Checkout API Gateway", "tier": "domain", "rev_per_min": 22000},
    {"id": "cartservice", "name": "Cart Service", "tier": "data", "rev_per_min": 14000},
    {"id": "auth-service", "name": "Authentication Service", "tier": "domain", "rev_per_min": 18000},
    {"id": "session-service", "name": "User Session Service", "tier": "domain", "rev_per_min": 12000},
    
    # Hop 2
    {"id": "paymentservice", "name": "Payment Service", "tier": "domain", "rev_per_min": 20000},
    {"id": "orders", "name": "Orders Service", "tier": "domain", "rev_per_min": 19000},
    {"id": "user", "name": "User Profile Service", "tier": "domain", "rev_per_min": 9000},
    {"id": "recommendationservice", "name": "Recommendation Engine", "tier": "domain", "rev_per_min": 8000},
    {"id": "productcatalogservice", "name": "Product Catalog Service", "tier": "domain", "rev_per_min": 11000},
    
    # Hop 3
    {"id": "frontend", "name": "Storefront Web App", "tier": "edge", "rev_per_min": 24000},
    {"id": "edge-router", "name": "Edge Ingress Router", "tier": "edge", "rev_per_min": 21000},
    {"id": "adservice", "name": "Ad Banner Service", "tier": "domain", "rev_per_min": 5000},
    
    # Hop 4
    {"id": "mobile-gateway", "name": "Mobile API Gateway", "tier": "edge", "rev_per_min": 16000},
    {"id": "web-gateway", "name": "Web Ingress Gateway", "tier": "edge", "rev_per_min": 17000},
    
    # Side / Independent Services (do NOT depend on cache-b)
    {"id": "shippingservice", "name": "Shipping Dispatcher", "tier": "domain", "rev_per_min": 6000},
    {"id": "shipping", "name": "Carrier Integration", "tier": "domain", "rev_per_min": 6000},
    {"id": "queue-master", "name": "Async Task Queue (RabbitMQ)", "tier": "data", "rev_per_min": 4000},
    {"id": "emailservice", "name": "Customer Notification Mailer", "tier": "domain", "rev_per_min": 3000},
    {"id": "catalogue", "name": "Sock Catalogue Service", "tier": "domain", "rev_per_min": 5000},
    {"id": "inventory-db", "name": "Warehouse Inventory DB", "tier": "data", "rev_per_min": 7000},
    {"id": "orders-db", "name": "Relational Orders Store", "tier": "data", "rev_per_min": 15000},
    {"id": "currencyservice", "name": "Currency Exchange Rates", "tier": "domain", "rev_per_min": 4000},
    {"id": "notification-service", "name": "SMS & Push Gateway", "tier": "domain", "rev_per_min": 3500}
]

def plant_golden_slice(db, graph_name="t:parcelo"):
    clock = DemoClock.frozen()
    now = clock.now_ms
    adr17_time = clock.adr17_ms
    before_adr17 = clock.before_adr17_ms
    month_ago = now - (30 * 24 * 3600 * 1000)

    try:
        db.connection.execute_command("GRAPH.DELETE", graph_name)
    except Exception:
        pass

    g = db.select_graph(graph_name)

    # 1. Create Services
    g.query("""
    UNWIND $services AS s
    CREATE (:Service {
        id: s.id,
        name: s.name,
        tier: s.tier,
        rev_per_min: s.rev_per_min
    })
    """, {"services": SERVICES})

    # 2. Plant Live Dependencies
    live_edges = [
        # Hop 1 to cache-b
        ("checkout-api", "cache-b"),
        ("cartservice", "cache-b"),
        ("auth-service", "cache-b"),
        ("session-service", "cache-b"),
        # Hop 2
        ("paymentservice", "checkout-api"),
        ("orders", "checkout-api"),
        ("user", "auth-service"),
        ("recommendationservice", "cartservice"),
        ("productcatalogservice", "session-service"),
        # Hop 3
        ("frontend", "paymentservice"),
        ("frontend", "recommendationservice"),
        ("frontend", "productcatalogservice"),
        ("edge-router", "orders"),
        ("edge-router", "user"),
        ("adservice", "recommendationservice"),
        # Hop 4
        ("mobile-gateway", "frontend"),
        ("web-gateway", "edge-router"),
        # Side connections
        ("shippingservice", "shipping"),
        ("shipping", "queue-master"),
        ("orders", "orders-db"),
        ("productcatalogservice", "catalogue"),
        ("catalogue", "inventory-db"),
        ("checkout-api", "emailservice"),
        ("frontend", "currencyservice"),
        ("user", "notification-service")
    ]

    for a, b in live_edges:
        edge_valid_from = adr17_time if (a in ["checkout-api", "cartservice", "auth-service"] and b == "cache-b") else month_ago
        fact_id = f"fact-dep-{a}-{b}"
        g.query("""
        MATCH (a:Service {id:$a}), (b:Service {id:$b})
        CREATE (a)-[:DEPENDS_ON {
            valid_from: $valid_from,
            fact_id: $fact_id,
            kind: 'network'
        }]->(b)
        """, {"a": a, "b": b, "valid_from": edge_valid_from, "fact_id": fact_id})

    # 3. Plant Closed History: checkout-api -> cache-a (superseded by ADR-17)
    g.query("""
    MATCH (a:Service {id:'checkout-api'}), (b:Service {id:'cache-a'})
    CREATE (a)-[:DEPENDED_ON {
        valid_from: $month_ago,
        valid_to: $adr17_time,
        fact_id: 'fact-dep-checkout-cache-a',
        ended_by: 'change-adr-17'
    }]->(b)
    """, {"month_ago": month_ago, "adr17_time": adr17_time})

    # 4. Plant ADR-17 Decision and Change
    g.query("""
    MATCH (old_svc:Service {id:'cache-a'}), (new_svc:Service {id:'cache-b'})
    CREATE (d:Decision {
        id: 'ADR-17',
        title: 'ADR-17: Migrate Session Cache from cache-a to Redis Cluster cache-b',
        at: $adr17_time
    })
    CREATE (c:Change {
        id: 'change-adr-17',
        at: $adr17_time,
        kind: 'migration_and_deprecation'
    })
    CREATE (d)-[:LED_TO]->(c)
    CREATE (c)-[:AFFECTS]->(old_svc)
    CREATE (c)-[:AFFECTS]->(new_svc)
    """, {"adr17_time": adr17_time})

    # 5. Plant Teams & People
    g.query("""
    CREATE (t_infra:Team {id:'core-infra', name:'Core Infrastructure'})
    CREATE (t_checkout:Team {id:'checkout-team', name:'Checkout & Payments'})
    CREATE (t_edge:Team {id:'edge-team', name:'Edge Systems'})

    CREATE (p_priya:Person {id:'priya', name:'Priya Sharma', status:'leave'})
    CREATE (p_marco:Person {id:'marco', name:'Marco Rossi', status:'active'})
    CREATE (p_alex:Person {id:'alex', name:'Alex Chen', status:'oncall'})

    CREATE (p_priya)-[:MEMBER_OF]->(t_infra)
    CREATE (p_marco)-[:MEMBER_OF]->(t_infra)
    CREATE (p_alex)-[:MEMBER_OF]->(t_checkout)

    WITH t_infra, t_checkout
    MATCH (s_cache_b:Service {id:'cache-b'}), (s_cache_a:Service {id:'cache-a'}), (s_chk:Service {id:'checkout-api'})
    CREATE (t_infra)-[:OWNS {valid_from:$month_ago}]->(s_cache_b)
    CREATE (t_infra)-[:OWNS {valid_from:$month_ago}]->(s_cache_a)
    CREATE (t_checkout)-[:OWNS {valid_from:$month_ago}]->(s_chk)
    """, {"month_ago": month_ago})

    # 6. Plant Expertise (Priya 0.91 on leave, Marco 0.74 active with INC-0412)
    one_day_ms = 86400 * 1000
    g.query("""
    MATCH (priya:Person {id:'priya'}), (marco:Person {id:'marco'}), (cb:Service {id:'cache-b'})
    CREATE (priya)-[:EXPERT_IN {
        score: 0.91,
        evidence_count: 14,
        last_evidence_at: $last_evidence_priya,
        computed_at: $now
    }]->(cb)
    CREATE (marco)-[:EXPERT_IN {
        score: 0.74,
        evidence_count: 8,
        last_evidence_at: $last_evidence_marco,
        computed_at: $now
    }]->(cb)

    CREATE (inc:Episode {
        id: 'INC-0412',
        kind: 'incident',
        outcome: 'success',
        t_start: $inc_start,
        t_end: $inc_end
    })
    CREATE (inc)-[:INVOLVED]->(cb)
    CREATE (marco)-[:RESOLVED]->(inc)
    """, {
        "now": now,
        "last_evidence_priya": now - (one_day_ms // 2),
        "last_evidence_marco": now - (one_day_ms // 2),
        "inc_start": now - (12 * one_day_ms),
        "inc_end": now - (12 * one_day_ms) + 1800000
    })

    # 7. Plant FailureMode & Procedures (R-7 stale by ADR-17 path; R-12 valid ~61%)
    g.query("""
    CREATE (fm:FailureMode {
        key: 'cache_exhaustion',
        name: 'Cache Memory Exhaustion / Stampede'
    })

    // R-7 targets cache-a (validated before ADR-17 -> stale)
    CREATE (r7:Procedure {
        id: 'R-7',
        name: 'Restart Redis Cache Node',
        status: 'trusted',
        version: 2,
        last_validated_at: $r7_val_at
    })
    CREATE (r7)-[:APPLIES_TO]->(fm)
    WITH r7, fm
    MATCH (ca:Service {id:'cache-a'})
    CREATE (s1:Step {ord:1, tool:'restart_service', params:'{"target":"cache-a"}'})-[:TARGETS]->(ca)
    CREATE (r7)-[:HAS_STEP]->(s1)

    // R-12 targets cache-b (validated after ADR-17 -> valid)
    WITH fm
    CREATE (r12:Procedure {
        id: 'R-12',
        name: 'Flush Key Prefix & Scale Replicas',
        status: 'trusted',
        version: 1,
        last_validated_at: $r12_val_at
    })
    CREATE (r12)-[:APPLIES_TO]->(fm)
    WITH r12
    MATCH (cb:Service {id:'cache-b'})
    CREATE (s2:Step {ord:1, tool:'flush_cache_keys', params:'{"target":"cache-b"}'})-[:TARGETS]->(cb)
    CREATE (r12)-[:HAS_STEP]->(s2)
    """, {
        "r7_val_at": adr17_time - one_day_ms,    # 1 day before ADR-17
        "r12_val_at": adr17_time + one_day_ms   # 1 day after ADR-17
    })

    # 8. Plant Past Episodes for Procedure Decayed Win Rates
    # R-7: 5 uses before ADR-17, all success -> high raw win rate
    # R-12: 3 uses after ADR-17, 2 success, 1 fail -> (2+1)/(3+2) = 60% win rate
    g.query("""
    MATCH (r7:Procedure {id:'R-7'}), (r12:Procedure {id:'R-12'})
    CREATE (:Episode {id:'ep-r7-1'})-[:USED {outcome:'success', at:$t1}]->(r7)
    CREATE (:Episode {id:'ep-r7-2'})-[:USED {outcome:'success', at:$t2}]->(r7)
    CREATE (:Episode {id:'ep-r7-3'})-[:USED {outcome:'success', at:$t3}]->(r7)
    CREATE (:Episode {id:'ep-r7-4'})-[:USED {outcome:'success', at:$t4}]->(r7)

    CREATE (:Episode {id:'ep-r12-1'})-[:USED {outcome:'success', at:$t5}]->(r12)
    CREATE (:Episode {id:'ep-r12-2'})-[:USED {outcome:'success', at:$t6}]->(r12)
    CREATE (:Episode {id:'ep-r12-3'})-[:USED {outcome:'failure', at:$t7}]->(r12)
    """, {
        "t1": adr17_time - (10 * one_day_ms),
        "t2": adr17_time - (8 * one_day_ms),
        "t3": adr17_time - (5 * one_day_ms),
        "t4": adr17_time - (2 * one_day_ms),
        "t5": adr17_time + (2 * one_day_ms),
        "t6": adr17_time + (3 * one_day_ms),
        "t7": adr17_time + (4 * one_day_ms)
    })

    # 9. Plant 3 Stale Docs (last_verified_at before ADR-17)
    doc_ver_at = adr17_time - one_day_ms
    g.query("""
    MATCH (s_chk:Service {id:'checkout-api'}), (s_cart:Service {id:'cartservice'}), (s_auth:Service {id:'auth-service'})
    CREATE (d1:Doc {
        id: 'doc-checkout-arch',
        title: 'Checkout Architecture & Caching Guide',
        kind: 'runbook',
        last_verified_at: $doc_ver_at
    })-[:DESCRIBES]->(s_chk)

    CREATE (d2:Doc {
        id: 'doc-cart-ops',
        title: 'Cart Storage & Session Cache Manual',
        kind: 'architecture',
        last_verified_at: $doc_ver_at
    })-[:DESCRIBES]->(s_cart)

    CREATE (d3:Doc {
        id: 'doc-auth-spec',
        title: 'Authentication & Token Cache Specification',
        kind: 'runbook',
        last_verified_at: $doc_ver_at
    })-[:DESCRIBES]->(s_auth)
    """, {"doc_ver_at": doc_ver_at})

    # 10. Tag Alerting Services
    g.query("""
    UNWIND $alerting AS sid
    MATCH (s:Service {id:sid})
    SET s:Alerting
    """, {"alerting": ALERTING_SERVICES})

    # 11. Run Algorithms to set PageRank & Betweenness
    g.query("CALL algo.pageRank('Service', 'DEPENDS_ON') YIELD node, score SET node.pagerank = score")
    g.query("CALL algo.betweenness({nodeLabels:['Service'], relationshipTypes:['DEPENDS_ON'], samplingSize: 25, samplingSeed: 42}) YIELD node, score SET node.betweenness = score")

    return {
        "services": len(SERVICES),
        "alerting": len(ALERTING_SERVICES),
        "clock_now": now,
        "adr17_time": adr17_time
    }

if __name__ == "__main__":
    from falkordb import FalkorDB
    host = os.getenv("FALKORDB_HOST", "localhost")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    db = FalkorDB(host=host, port=port)
    res = plant_golden_slice(db, "t:parcelo")
    print("Golden slice planted successfully:", res)
