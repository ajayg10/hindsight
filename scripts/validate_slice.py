# Quick validation of 25-service golden slice topology
services = [
    "cache-b", "cache-a", "checkout-api", "cartservice", "auth-service", "session-service",
    "paymentservice", "orders", "user", "recommendationservice", "productcatalogservice",
    "frontend", "edge-router", "adservice", "mobile-gateway", "web-gateway",
    "shippingservice", "shipping", "queue-master", "emailservice", "catalogue",
    "inventory-db", "orders-db", "currencyservice", "notification-service"
]

edges = [
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
    
    # Independent / side services (do not connect to cache-b)
    ("shippingservice", "shipping"),
    ("shipping", "queue-master"),
    ("orders", "orders-db"),
    ("productcatalogservice", "catalogue"),
    ("catalogue", "inventory-db"),
    ("checkout-api", "emailservice"),
    ("frontend", "currencyservice"),
    ("user", "notification-service")
]

# Compute reverse reachability from cache-b within 1..4 hops
from collections import deque

adj = {}
for u, v in edges:
    adj.setdefault(u, []).append(v)

# find all nodes d such that d can reach cache-b in 1..4 hops
def get_hops(source, target, max_hops=4):
    q = deque([(source, 0)])
    visited = {source: 0}
    while q:
        curr, h = q.popleft()
        if curr == target:
            return h
        if h < max_hops:
            for nxt in adj.get(curr, []):
                if nxt not in visited or visited[nxt] > h + 1:
                    visited[nxt] = h + 1
                    q.append((nxt, h + 1))
    return None

upstream = {}
for s in services:
    if s == "cache-b":
        continue
    h = get_hops(s, "cache-b", 4)
    if h is not None:
        upstream[s] = h

print("Total services:", len(services))
print("Upstream count (blast radius):", len(upstream))
print("Upstream nodes by hop:", sorted(upstream.items(), key=lambda x: (x[1], x[0])))

# Check 9 alerting services
alerting = [
    "mobile-gateway", "web-gateway", "frontend", "edge-router", "adservice",
    "paymentservice", "orders", "checkout-api", "cartservice"
]
print("Alerting count:", len(alerting))

# Find common ancestors of alerting
ancestors = {}
for a in alerting:
    # all reachable from a within 0..5 hops
    q = deque([(a, 0)])
    vis = {a: 0}
    while q:
        curr, h = q.popleft()
        if h < 5:
            for nxt in adj.get(curr, []):
                if nxt not in vis or vis[nxt] > h + 1:
                    vis[nxt] = h + 1
                    q.append((nxt, h + 1))
    for anc, d in vis.items():
        ancestors.setdefault(anc, []).append(d)

common = {k: v for k, v in ancestors.items() if len(v) == len(alerting)}
print("Common ancestors of all 9 alerting:", {k: (len(v), min(v)) for k, v in common.items()})
