#!/usr/bin/env python3
"""
Multi-Tenant Seeder for Hindsight.
Plants:
1. t:blueharbor - Freight logistics architecture with SAME service names as Parcelo
   but DIFFERENT dependency topology, planted root cause (paymentservice instead of cache-b),
   different owning team (merchant-payments), and active expert (Elena Vance).
2. 3 tiny tenants:
   - t:acme (Acme Logistics, 7 services)
   - t:novastream (NovaStream Media, 6 services)
   - t:finflow (FinFlow Settlement, 6 services)
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import falkordb
from app.clock import DemoClock

def get_db():
    return falkordb.FalkorDB(host="falkordb", port=6379)

def seed_blueharbor(db):
    """
    Seeds t:blueharbor:
    Uses same service names as Parcelo, but:
    - checkout-api, cartservice, orders, and frontend all depend on paymentservice.
    - cache-b is an auxiliary media cache, NOT the root cause.
    - Root cause for ['checkout-api', 'cartservice', 'paymentservice', 'frontend'] is paymentservice!
    """
    g_name = "t:blueharbor"
    try:
        db.connection.execute_command("GRAPH.DELETE", g_name)
    except Exception:
        pass

    g = db.select_graph(g_name)
    now = DemoClock.frozen().now_ms

    # 1. Services
    services = [
        {"id": "paymentservice", "name": "Payment Gateway Core", "tier": "domain", "rev_per_min": 450},
        {"id": "checkout-api", "name": "Freight Booking API", "tier": "domain", "rev_per_min": 350},
        {"id": "cartservice", "name": "Cargo Cart Service", "tier": "data", "rev_per_min": 200},
        {"id": "orders", "name": "Shipment Orders Engine", "tier": "domain", "rev_per_min": 300},
        {"id": "frontend", "name": "Shipper Portal Web App", "tier": "edge", "rev_per_min": 400},
        {"id": "edge-router", "name": "Logistics Ingress Router", "tier": "edge", "rev_per_min": 380},
        {"id": "auth-service", "name": "Carrier Auth Service", "tier": "domain", "rev_per_min": 250},
        {"id": "postgres-primary", "name": "Relational Ledger (PostgreSQL)", "tier": "data", "rev_per_min": 500},
        {"id": "cache-b", "name": "Auxiliary Document Cache", "tier": "data", "rev_per_min": 50},
        {"id": "customs-service", "name": "Customs Clearance API", "tier": "domain", "rev_per_min": 180},
        {"id": "tracking-service", "name": "Real-time Telematics Tracking", "tier": "domain", "rev_per_min": 220},
        {"id": "fleet-dispatch", "name": "Vessel & Fleet Dispatcher", "tier": "domain", "rev_per_min": 280}
    ]

    g.query("""
    UNWIND $services AS s
    CREATE (:Service {
        id: s.id,
        name: s.name,
        tier: s.tier,
        rev_per_min: s.rev_per_min,
        pagerank: 0.05,
        betweenness: 1.0
    })
    """, {"services": services})

    # 2. Topology: checkout-api, cartservice, orders all depend on paymentservice!
    edges = [
        ("frontend", "checkout-api"),
        ("frontend", "cartservice"),
        ("checkout-api", "paymentservice"),
        ("cartservice", "paymentservice"),
        ("orders", "paymentservice"),
        ("orders", "postgres-primary"),
        ("checkout-api", "auth-service"),
        ("edge-router", "frontend"),
        ("customs-service", "paymentservice"),
        ("tracking-service", "postgres-primary"),
        ("fleet-dispatch", "tracking-service")
    ]

    for a, b in edges:
        g.query("""
        MATCH (a:Service {id:$a}), (b:Service {id:$b})
        CREATE (a)-[:DEPENDS_ON {kind:'network', valid_from:$now}]->(b)
        """, {"a": a, "b": b, "now": now - 86400000})

    # 3. Ownership & Expertise: Elena Vance owns paymentservice
    g.query("""
    CREATE (p_elena:Person {id:'elena', name:'Elena Vance', status:'active', email:'elena@blueharbor.io'})
    CREATE (p_dmitri:Person {id:'dmitri', name:'Dmitri Petrov', status:'active', email:'dmitri@blueharbor.io'})
    CREATE (t_pay:Team {id:'merchant-payments', name:'Merchant & Freight Payments', slack_channel:'#freight-payments'})
    CREATE (p_elena)-[:MEMBER_OF]->(t_pay)
    CREATE (p_dmitri)-[:MEMBER_OF]->(t_pay)
    WITH t_pay, p_elena
    MATCH (ps:Service {id:'paymentservice'})
    CREATE (t_pay)-[:OWNS {valid_from:$now}]->(ps)
    CREATE (p_elena)-[:EXPERT_IN {
        score: round((1.0 - exp(-0.17 * 12)) * 100.0) / 100.0,
        evidence_count: 12,
        last_evidence_at: $now,
        computed_at: $now
    }]->(ps)
    """, {"now": now})

    # 4. Procedure: R-15 (Valid for paymentservice)
    g.query("""
    CREATE (fm:FailureMode {key:'payment_gateway_exhaustion', name:'Payment Gateway Connection Saturation'})
    CREATE (r15:Procedure {
        id: 'R-15',
        name: 'Payment Gateway Circuit Breaker Reset & Pool Flush',
        status: 'trusted',
        version: 3,
        last_validated_at: $now
    })
    CREATE (r15)-[:APPLIES_TO]->(fm)
    WITH r15
    MATCH (ps:Service {id:'paymentservice'})
    CREATE (s1:Step {ord:1, tool:'reset_circuit_breaker', params:'{"target":"paymentservice"}'})-[:TARGETS]->(ps)
    CREATE (r15)-[:HAS_STEP]->(s1)

    // Episode: 1 historical win
    CREATE (ep:Episode {id:'INC-BH-109', kind:'incident', outcome:'success', t_start:$now-86400000, t_end:$now-86400000+1800000})
    CREATE (ep)-[:USED {outcome:'success', at:$now-86400000}]->(r15)
    CREATE (ep)-[:INVOLVED]->(ps)
    """, {"now": now})

    # Refresh PageRank & Betweenness
    try:
        g.query("CALL algo.pageRank('Service', 'DEPENDS_ON')")
        g.query("CALL algo.betweenness('Service', 'DEPENDS_ON')")
    except Exception:
        pass

    return g_name

def seed_tiny_tenant(db, tenant_id: str, company_name: str, services: list, edges: list):
    g_name = f"t:{tenant_id}"
    try:
        db.connection.execute_command("GRAPH.DELETE", g_name)
    except Exception:
        pass

    g = db.select_graph(g_name)
    now = DemoClock.frozen().now_ms

    g.query("""
    UNWIND $services AS s
    CREATE (:Service {
        id: s.id,
        name: s.name,
        tier: s.tier,
        rev_per_min: s.rev_per_min,
        pagerank: 0.1,
        betweenness: 1.0
    })
    """, {"services": services})

    for a, b in edges:
        g.query("""
        MATCH (a:Service {id:$a}), (b:Service {id:$b})
        CREATE (a)-[:DEPENDS_ON {kind:'network', valid_from:$now}]->(b)
        """, {"a": a, "b": b, "now": now - 86400000})

    # Add team and owner
    g.query("""
    CREATE (p:Person {id:'lead-' + $tid, name:$cname + ' Lead', status:'active'})
    CREATE (t:Team {id:'team-' + $tid, name:$cname + ' Core Team', slack_channel:'#' + $tid + '-ops'})
    CREATE (p)-[:MEMBER_OF]->(t)
    WITH t, p
    MATCH (s:Service {id:$first_svc})
    CREATE (t)-[:OWNS {valid_from:$now}]->(s)
    CREATE (p)-[:EXPERT_IN {score: 0.85, evidence_count: 8, computed_at:$now}]->(s)
    """, {"tid": tenant_id, "cname": company_name, "first_svc": services[0]["id"], "now": now})

    return g_name

def seed_all_tenants():
    db = get_db()
    print("Seeding multi-tenant graphs into FalkorDB...")

    # 1. BlueHarbor
    bh = seed_blueharbor(db)
    print(f"  ✓ Seeded {bh} (BlueHarbor Freight & Logistics)")

    # 2. Acme Logistics
    acme_services = [
        {"id": "dispatch-api", "name": "Dispatch Orchestrator", "tier": "domain", "rev_per_min": 120},
        {"id": "fleet-tracker", "name": "GPS Telematics Worker", "tier": "domain", "rev_per_min": 80},
        {"id": "driver-app", "name": "Driver Mobile Backend", "tier": "edge", "rev_per_min": 100},
        {"id": "telematics-db", "name": "TimescaleDB Telematics Store", "tier": "data", "rev_per_min": 150},
        {"id": "geo-router", "name": "Turn-by-Turn Routing Engine", "tier": "domain", "rev_per_min": 90},
        {"id": "acme-auth", "name": "Acme IAM Service", "tier": "domain", "rev_per_min": 70},
        {"id": "acme-notify", "name": "Customer SMS Dispatcher", "tier": "domain", "rev_per_min": 40}
    ]
    acme_edges = [
        ("driver-app", "dispatch-api"),
        ("dispatch-api", "fleet-tracker"),
        ("fleet-tracker", "telematics-db"),
        ("dispatch-api", "geo-router"),
        ("driver-app", "acme-auth"),
        ("dispatch-api", "acme-notify")
    ]
    seed_tiny_tenant(db, "acme", "Acme Logistics", acme_services, acme_edges)
    print(f"  ✓ Seeded t:acme (7 services)")

    # 3. NovaStream Media
    nova_services = [
        {"id": "video-edge", "name": "HLS Video CDN Origin", "tier": "edge", "rev_per_min": 250},
        {"id": "transcoder", "name": "FFmpeg Distributed Transcoder", "tier": "domain", "rev_per_min": 180},
        {"id": "hls-packager", "name": "Adaptive Bitrate Packager", "tier": "domain", "rev_per_min": 140},
        {"id": "metadata-api", "name": "Show & Catalog Metadata API", "tier": "domain", "rev_per_min": 90},
        {"id": "media-store", "name": "Video Chunks S3 Store", "tier": "data", "rev_per_min": 300},
        {"id": "nova-auth", "name": "Subscriber Entitlements", "tier": "domain", "rev_per_min": 110}
    ]
    nova_edges = [
        ("video-edge", "hls-packager"),
        ("hls-packager", "transcoder"),
        ("transcoder", "media-store"),
        ("video-edge", "metadata-api"),
        ("video-edge", "nova-auth")
    ]
    seed_tiny_tenant(db, "novastream", "NovaStream Media", nova_services, nova_edges)
    print(f"  ✓ Seeded t:novastream (6 services)")

    # 4. FinFlow Settlement
    fin_services = [
        {"id": "settlement-api", "name": "Interbank Settlement Core", "tier": "domain", "rev_per_min": 800},
        {"id": "ledger-db", "name": "Immutable Double-Entry Ledger", "tier": "data", "rev_per_min": 950},
        {"id": "compliance-worker", "name": "AML & Sanctions Screening", "tier": "domain", "rev_per_min": 400},
        {"id": "swift-gateway", "name": "ISO 20022 SWIFT Gateway", "tier": "edge", "rev_per_min": 600},
        {"id": "risk-engine", "name": "Real-time Credit Exposure Engine", "tier": "domain", "rev_per_min": 500},
        {"id": "fin-auth", "name": "mTLS Bank Key Enclave", "tier": "data", "rev_per_min": 350}
    ]
    fin_edges = [
        ("swift-gateway", "settlement-api"),
        ("settlement-api", "compliance-worker"),
        ("settlement-api", "ledger-db"),
        ("settlement-api", "risk-engine"),
        ("settlement-api", "fin-auth")
    ]
    seed_tiny_tenant(db, "finflow", "FinFlow Settlement", fin_services, fin_edges)
    print(f"  ✓ Seeded t:finflow (6 services)")

    print("\nAll 5 tenants successfully seeded in FalkorDB (t:parcelo, t:blueharbor, t:acme, t:novastream, t:finflow).")

if __name__ == "__main__":
    seed_all_tenants()
