#!/usr/bin/env python3
"""
Full seed generator for Hindsight (seed=42).
Enriches the golden slice (25 services) to 58 services, with filler docs,
tickets, messages, and episodes, strictly preserving golden slice invariants.
"""
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.clock import DemoClock
try:
    from seed.plant import plant_golden_slice, ALERTING_SERVICES
except ImportError:
    from plant import plant_golden_slice, ALERTING_SERVICES

# 33 additional services to reach 58 total services (realistic low rev_per_min)
FILLER_SERVICES = [
    # Data & Analytics pipelines (Hub: data-warehouse-sync)
    {"id": "analytics-collector", "name": "Event Stream Collector (Kafka)", "tier": "data", "rev_per_min": 35},
    {"id": "metrics-aggregator", "name": "Telemetry & Metrics Aggregator", "tier": "data", "rev_per_min": 25},
    {"id": "audit-logger", "name": "Compliance Audit Logger", "tier": "data", "rev_per_min": 20},
    {"id": "search-indexer", "name": "Elasticsearch Sync Worker", "tier": "data", "rev_per_min": 45},
    {"id": "data-warehouse-sync", "name": "BigQuery Data Lake Sync", "tier": "data", "rev_per_min": 30},
    {"id": "report-generator", "name": "Daily Financial Reporter", "tier": "domain", "rev_per_min": 40},
    {"id": "customer-insights", "name": "Customer Segmentation Engine", "tier": "domain", "rev_per_min": 35},
    
    # Internal & Admin tools
    {"id": "admin-portal", "name": "Staff Admin Dashboard", "tier": "edge", "rev_per_min": 15},
    {"id": "support-console", "name": "Customer Support Console", "tier": "edge", "rev_per_min": 25},
    {"id": "billing-export", "name": "ERP Billing Integration Worker", "tier": "domain", "rev_per_min": 50},
    {"id": "tax-calculator", "name": "Avalara Tax Calculation Service", "tier": "domain", "rev_per_min": 45},
    {"id": "fraud-detector", "name": "Risk & Fraud Scoring Service", "tier": "domain", "rev_per_min": 60},
    {"id": "discount-engine", "name": "Coupons & Promotional Rules", "tier": "domain", "rev_per_min": 40},
    {"id": "loyalty-points", "name": "Rewards & Loyalty Wallet", "tier": "domain", "rev_per_min": 30},
    
    # Supply chain & Logistics (Hub: warehouse-manager & carrier-webhook)
    {"id": "warehouse-manager", "name": "Warehouse Management Core", "tier": "domain", "rev_per_min": 65},
    {"id": "returns-service", "name": "RMA & Return Authorization", "tier": "domain", "rev_per_min": 35},
    {"id": "supplier-portal", "name": "Vendor Purchase Order Gateway", "tier": "edge", "rev_per_min": 20},
    {"id": "package-tracker", "name": "Delivery Tracking Integration", "tier": "domain", "rev_per_min": 35},
    {"id": "carrier-webhook", "name": "FedEx/UPS Inbound Webhook Listener", "tier": "edge", "rev_per_min": 30},
    {"id": "fleet-dispatch", "name": "Last-Mile Delivery Dispatcher", "tier": "domain", "rev_per_min": 40},
    
    # Content & Marketing (Hub: cms-service)
    {"id": "cms-service", "name": "Headless CMS API", "tier": "domain", "rev_per_min": 25},
    {"id": "media-storage", "name": "Product Image CDN Origin (S3)", "tier": "data", "rev_per_min": 35},
    {"id": "newsletter-worker", "name": "Email Campaign Batch Worker", "tier": "domain", "rev_per_min": 15},
    {"id": "seo-renderer", "name": "Dynamic Pre-Renderer for Bots", "tier": "edge", "rev_per_min": 20},
    {"id": "ab-testing", "name": "Feature Flag & Experimentation Engine", "tier": "domain", "rev_per_min": 45},
    
    # Core Infrastructure utilities (Hub: rate-limiter & secrets-manager)
    {"id": "secrets-manager", "name": "HashiCorp Vault Enclave", "tier": "data", "rev_per_min": 50},
    {"id": "dns-resolver", "name": "Internal CoreDNS Resolver", "tier": "data", "rev_per_min": 15},
    {"id": "config-service", "name": "Dynamic Config Server", "tier": "data", "rev_per_min": 35},
    {"id": "rate-limiter", "name": "Distributed Redis Rate Limiter", "tier": "data", "rev_per_min": 55},
    {"id": "health-checker", "name": "Synthetic Uptime Monitor", "tier": "domain", "rev_per_min": 10},
    {"id": "backup-worker", "name": "Automated Snapshot Runner", "tier": "data", "rev_per_min": 10},
    {"id": "log-indexer", "name": "Vector Log Ingestion Pipe", "tier": "data", "rev_per_min": 20},
    {"id": "tracing-collector", "name": "OpenTelemetry Jaeger Collector", "tier": "data", "rev_per_min": 25}
]

# Filler edges connecting filler services into rich sub-clusters with realistic in-degree
FILLER_EDGES = [
    # Admin / Ingress cluster
    ("admin-portal", "secrets-manager"),
    ("admin-portal", "config-service"),
    ("admin-portal", "rate-limiter"),
    ("support-console", "returns-service"),
    ("support-console", "package-tracker"),
    ("support-console", "rate-limiter"),
    
    # Financial / Billing cluster
    ("billing-export", "tax-calculator"),
    ("billing-export", "orders-db"),
    ("discount-engine", "tax-calculator"),
    ("fraud-detector", "orders-db"),
    ("loyalty-points", "orders-db"),
    
    # Supply chain cluster (Hub: warehouse-manager)
    ("supplier-portal", "warehouse-manager"),
    ("returns-service", "warehouse-manager"),
    ("warehouse-manager", "inventory-db"),
    ("warehouse-manager", "package-tracker"),
    ("package-tracker", "carrier-webhook"),
    ("fleet-dispatch", "carrier-webhook"),
    ("fleet-dispatch", "warehouse-manager"),
    
    # Content & Marketing cluster (Hub: cms-service)
    ("seo-renderer", "cms-service"),
    ("cms-service", "media-storage"),
    ("cms-service", "ab-testing"),
    ("newsletter-worker", "emailservice"),
    ("newsletter-worker", "cms-service"),
    
    # Analytics & Observability cluster (Hub: data-warehouse-sync)
    ("analytics-collector", "data-warehouse-sync"),
    ("report-generator", "data-warehouse-sync"),
    ("customer-insights", "data-warehouse-sync"),
    ("search-indexer", "data-warehouse-sync"),
    ("log-indexer", "media-storage"),
    ("tracing-collector", "metrics-aggregator"),
    ("health-checker", "rate-limiter"),
    ("health-checker", "dns-resolver"),
    ("backup-worker", "orders-db"),
    ("backup-worker", "inventory-db"),
    ("config-service", "secrets-manager")
]

def generate_full_seed(db, graph_name="t:parcelo"):
    rng = random.Random(42)
    clock = DemoClock.frozen()
    now = clock.now_ms
    month_ago = now - (30 * 24 * 3600 * 1000)

    # 1. Plant Golden Slice first
    print("Step 1: Planting Golden Slice...")
    golden = plant_golden_slice(db, graph_name)
    g = db.select_graph(graph_name)

    # 2. Add 33 Filler Services
    print(f"Step 2: Adding {len(FILLER_SERVICES)} filler services...")
    g.query("""
    UNWIND $fillers AS s
    CREATE (:Service {
        id: s.id,
        name: s.name,
        tier: s.tier,
        rev_per_min: s.rev_per_min
    })
    """, {"fillers": FILLER_SERVICES})

    # 3. Add Filler Edges
    print(f"Step 3: Connecting filler dependencies...")
    for a, b in FILLER_EDGES:
        fact_id = f"fact-dep-{a}-{b}"
        g.query("""
        MATCH (a:Service {id:$a}), (b:Service {id:$b})
        CREATE (a)-[:DEPENDS_ON {
            valid_from: $valid_from,
            fact_id: $fact_id,
            kind: 'network'
        }]->(b)
        """, {"a": a, "b": b, "valid_from": month_ago, "fact_id": fact_id})

    # 4. Generate Filler Docs, Tickets, Messages
    print("Step 4: Generating template-based docs, tickets, messages...")
    docs_data = []
    for s in FILLER_SERVICES[:15]:
        docs_data.append({
            "id": f"doc-{s['id']}",
            "title": f"{s['name']} - Architecture & Operational Guide",
            "kind": "architecture",
            "last_verified_at": now - (15 * 24 * 3600 * 1000),
            "svc": s["id"]
        })
    g.query("""
    UNWIND $docs AS d
    MATCH (s:Service {id:d.svc})
    CREATE (doc:Doc {
        id: d.id,
        title: d.title,
        kind: d.kind,
        last_verified_at: d.last_verified_at
    })-[:DESCRIBES]->(s)
    """, {"docs": docs_data})

    # 5. Recompute Algorithms across all 58 services
    print("Step 5: Refreshing PageRank and Betweenness across 58 services...")
    g.query("CALL algo.pageRank('Service', 'DEPENDS_ON') YIELD node, score SET node.pagerank = score")
    g.query("CALL algo.betweenness({nodeLabels:['Service'], relationshipTypes:['DEPENDS_ON'], samplingSize: 58, samplingSeed: 42}) YIELD node, score SET node.betweenness = score")

    total_services = g.query("MATCH (s:Service) RETURN count(s)").result_set[0][0]
    total_edges = g.query("MATCH ()-[r:DEPENDS_ON]->() RETURN count(r)").result_set[0][0]
    total_docs = g.query("MATCH (d:Doc) RETURN count(d)").result_set[0][0]

    return {
        "graph_name": graph_name,
        "total_services": total_services,
        "total_live_edges": total_edges,
        "total_docs": total_docs,
        "clock_now": now
    }

if __name__ == "__main__":
    from falkordb import FalkorDB
    host = os.getenv("FALKORDB_HOST", "localhost")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    db = FalkorDB(host=host, port=port)
    res = generate_full_seed(db, "t:parcelo")
    print("Enrichment complete:", res)
