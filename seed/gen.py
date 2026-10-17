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

    # 4. Generate ~300 Docs, ~500 Threads, ~2,000 Messages, ~120 Past Incidents
    print("Step 4: Enriching graph with template-based docs, threads, messages, and episodes (~3,000 nodes)...")
    
    # 4a. 15 Template Engineers (preserves Priya and Marco evidence counts on cache-b)
    engineers = [
        {"id": f"eng-{i:02d}", "name": f"Engineer {i}", "role": "dev", "status": "active"}
        for i in range(1, 16)
    ]
    g.query("""
    UNWIND $engs AS e
    CREATE (:Person {id: e.id, name: e.name, role: e.role, status: e.status})
    """, {"engs": engineers})

    # 4b. 300 Docs: all verified recently (within last 5 days), strictly > adr17_time (preserves exactly 3 stale docs)
    enrich_svcs = [s["id"] for s in FILLER_SERVICES] + ["inventory", "shipping", "order-processing", "recommendation"]
    docs_data = []
    doc_kinds = ["architecture", "runbook", "spec", "slo", "troubleshooting"]
    for i in range(1, 301):
        svc_target = enrich_svcs[i % len(enrich_svcs)]
        author_id = engineers[i % len(engineers)]["id"]
        verified_at = now - (rng.randint(1, 5) * 86400 * 1000)
        docs_data.append({
            "id": f"doc-tmpl-{i:03d}",
            "title": f"{svc_target.capitalize()} - {doc_kinds[i % len(doc_kinds)].capitalize()} Document v{1 + (i % 3)}",
            "kind": doc_kinds[i % len(doc_kinds)],
            "last_verified_at": verified_at,
            "svc": svc_target,
            "author": author_id
        })

    for chunk in [docs_data[i:i+100] for i in range(0, len(docs_data), 100)]:
        g.query("""
        UNWIND $docs AS d
        MATCH (s:Service {id:d.svc}), (p:Person {id:d.author})
        CREATE (doc:Doc {
            id: d.id,
            title: d.title,
            kind: d.kind,
            last_verified_at: d.last_verified_at
        })-[:DESCRIBES]->(s)
        CREATE (p)-[:AUTHORED]->(doc)
        """, {"docs": chunk})

    # 4c. 500 Threads
    threads_data = []
    for i in range(1, 501):
        threads_data.append({
            "id": f"th-tmpl-{i:03d}",
            "title": f"Production Alert & Optimization Thread #{1000 + i}"
        })
    for chunk in [threads_data[i:i+100] for i in range(0, len(threads_data), 100)]:
        g.query("""
        UNWIND $threads AS th
        CREATE (:Thread {id: th.id, title: th.title})
        """, {"threads": chunk})

    # 4d. 2,000 Messages
    msgs_data = []
    sample_texts = [
        "Investigating latency spike on upstream gateway connection.",
        "Applied connection pool limit increase to prevent queue buildup.",
        "Rolling restart of worker replicas completed smoothly.",
        "Verified metrics dashboard; p99 latency returned to baseline.",
        "Documenting RCA and updating circuit breaker thresholds."
    ]
    for i in range(1, 2001):
        th_id = f"th-tmpl-{(i % 500) + 1:03d}"
        author_id = engineers[i % len(engineers)]["id"]
        svc_target = enrich_svcs[i % len(enrich_svcs)]
        msg_time = now - (rng.randint(2, 28) * 86400 * 1000)
        msgs_data.append({
            "id": f"msg-tmpl-{i:04d}",
            "text": sample_texts[i % len(sample_texts)],
            "at": msg_time,
            "th": th_id,
            "author": author_id,
            "svc": svc_target
        })

    for chunk in [msgs_data[i:i+200] for i in range(0, len(msgs_data), 200)]:
        g.query("""
        UNWIND $msgs AS m
        MATCH (th:Thread {id:m.th}), (p:Person {id:m.author}), (s:Service {id:m.svc})
        CREATE (msg:Message {id:m.id, text:m.text, at:m.at})
        CREATE (msg)-[:IN]->(th)
        CREATE (p)-[:AUTHORED]->(msg)
        CREATE (msg)-[:MENTIONS]->(s)
        """, {"msgs": chunk})

    # 4e. 120 Past Incidents / Episodes
    episodes_data = []
    for i in range(1, 121):
        svc_target = enrich_svcs[i % len(enrich_svcs)]
        resolver_id = engineers[i % len(engineers)]["id"]
        t_start = now - (rng.randint(5, 45) * 86400 * 1000)
        t_end = t_start + rng.randint(900000, 3600000)
        episodes_data.append({
            "id": f"INC-PAST-{i:03d}",
            "kind": "incident",
            "outcome": "success",
            "t_start": t_start,
            "t_end": t_end,
            "svc": svc_target,
            "resolver": resolver_id
        })

    for chunk in [episodes_data[i:i+50] for i in range(0, len(episodes_data), 50)]:
        g.query("""
        UNWIND $eps AS ep
        MATCH (s:Service {id:ep.svc}), (p:Person {id:ep.resolver})
        CREATE (e:Episode {
            id: ep.id,
            kind: ep.kind,
            outcome: ep.outcome,
            t_start: ep.t_start,
            t_end: ep.t_end
        })-[:INVOLVED]->(s)
        CREATE (p)-[:RESOLVED]->(e)
        """, {"eps": chunk})

    # 5. Recompute Algorithms across all 58 services
    print("Step 5: Refreshing PageRank, Betweenness, and Librarian Expertise...")
    g.query("CALL algo.pageRank('Service', 'DEPENDS_ON') YIELD node, score SET node.pagerank = score")
    try:
        from app.librarian import recompute_expertise
    except ImportError:
        from backend.app.librarian import recompute_expertise
    recompute_expertise(db, graph_name=graph_name, now=now)

    total_services = g.query("MATCH (s:Service) RETURN count(s)").result_set[0][0]
    total_edges = g.query("MATCH ()-[r:DEPENDS_ON]->() RETURN count(r)").result_set[0][0]
    total_docs = g.query("MATCH (d:Doc) RETURN count(d)").result_set[0][0]
    total_nodes = g.query("MATCH (n) RETURN count(n)").result_set[0][0]
    total_all_edges = g.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0]

    return {
        "graph_name": graph_name,
        "total_nodes": total_nodes,
        "total_edges": total_all_edges,
        "total_services": total_services,
        "total_live_depends_on": total_edges,
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
