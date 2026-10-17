import sys
import os
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falkordb import FalkorDB
from backend.app.clock import DemoClock

clock = DemoClock.frozen()
print(f"DemoClock frozen now_ms: {clock.now_ms} ({datetime.fromtimestamp(clock.now_ms/1000, tz=timezone.utc).isoformat()})")
print(f"DemoClock adr17_ms (clock - 6d): {clock.adr17_ms} ({datetime.fromtimestamp(clock.adr17_ms/1000, tz=timezone.utc).isoformat()})")

host = os.getenv("FALKORDB_HOST", "localhost")
port = int(os.getenv("FALKORDB_PORT", "6379"))
db = FalkorDB(host=host, port=port)
g = db.select_graph("t:parcelo")

res = g.query("MATCH (f:Fact) RETURN f.id, f.subject, f.predicate, f.object, f.status, f.valid_from, f.valid_to").result_set
print(f"Fact nodes count: {len(res)}")
for r in res:
    vf_iso = datetime.fromtimestamp(r[5]/1000, tz=timezone.utc).isoformat() if r[5] else "None"
    vt_iso = datetime.fromtimestamp(r[6]/1000, tz=timezone.utc).isoformat() if r[6] else "None"
    print(f"  Fact {r[0]}: {r[1]} -[{r[2]}]-> {r[3]}, status={r[4]}, valid_from={r[5]} ({vf_iso}), valid_to={r[6]} ({vt_iso})")

edges = g.query("MATCH (a)-[r:DEPENDED_ON]->(b) RETURN a.id, type(r), b.id, r.valid_from, r.valid_to").result_set
print(f"DEPENDED_ON edges count: {len(edges)}")
for e in edges:
    vf_iso = datetime.fromtimestamp(e[3]/1000, tz=timezone.utc).isoformat() if e[3] else "None"
    vt_iso = datetime.fromtimestamp(e[4]/1000, tz=timezone.utc).isoformat() if e[4] else "None"
    print(f"  Edge: {e[0]} -[{e[1]}]-> {e[2]}, valid_from={e[3]} ({vf_iso}), valid_to={e[4]} ({vt_iso})")
