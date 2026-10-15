#!/usr/bin/env python3
"""Real-engine Phase 0 gate. No mocks, application locks, or fabricated metrics."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import statistics
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
CHECKS = {
    'connection': ('Python client / real engine', 'Provide a Docker host; never substitute an in-memory graph.'),
    'pagerank': ('PageRank signature + SET', 'Required: stop Phase 0 if unavailable.'),
    'betweenness': ('Betweenness label/type projection', 'PageRank plus Cypher-derived path counts.'),
    'wcc': ('WCC transient-label projection', 'Python connectivity over Cypher-derived adjacency.'),
    'cdlp': ('Label propagation projection', 'Use WCC or adjacency fallback for split_storm; CDLP is optional.'),
    'shortest_path': ('Bound-endpoint shortestPath', 'WITH shortestPath form, then bounded traversal/minimum length.'),
    'zero_hop': ('Variable length *0..5', 'Positive-hop paths plus explicit source nodes.'),
    'multi_statement': ('Two statements in GRAPH.QUERY', 'Two ordered requests; not an atomic transaction.'),
    'graph_copy': ('GRAPH.COPY isolation + timing', 'Replay deterministic statements into a fresh graph.'),
    'concurrency': ('Concurrent claims, writes and read observations', 'Stop if claim invariant fails; do not claim unmeasured parallelism.'),
    'latency': ('Client query latency / synthetic 58 services', 'No numeric claim until measured.'),
}


def write_report(report):
    docs = ROOT / 'docs'
    docs.mkdir(exist_ok=True)
    (docs / 'phase0-results.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = ['# Phase 0 verification', '', f"Recorded: {report['at']}", '',
             f"**Acceptance: {report['acceptance']}**", '',
             'PASS/FAIL describes tested capability. BLOCKED means no real-engine evidence.',
             'A FAIL is gate-compatible only when an exercised fallback is recorded.', '',
             '| Check | Status | Fallback / decision |', '| --- | --- | --- |']
    for key, (name, fallback) in CHECKS.items():
        item = report['checks'].get(key, {'status': 'BLOCKED', 'error': 'Not executed'})
        decision = item.get('decision', fallback).replace('|', '\\|')
        lines.append(f"| {name} | {item['status']} | {decision} |")
    lines += ['', '## Runtime evidence', '', '```json', json.dumps(report, indent=2), '```', '',
              '## Official documentation checked on 2026-10-15', '',
              '- [PageRank](https://docs.falkordb.com/algorithms/pagerank): `algo.pageRank(label, relationship_type)` yields node and score.',
              '- [Betweenness](https://docs.falkordb.com/algorithms/betweenness-centrality): config supports label/type projection and samplingSeed.',
              '- [WCC](https://docs.falkordb.com/algorithms/wcc): config supports nodeLabels and relationshipTypes. Docs show both wcc and WCC; runtime decides.',
              '- [CDLP](https://docs.falkordb.com/algorithms/cdlp): `algo.labelPropagation(config)` yields communityId; it is not a WCC replacement.',
              '- [Path functions](https://docs.falkordb.com/cypher/functions#shortestpath): endpoints must be bound first; minimum length is 0 or 1.',
              '- [GRAPH.COPY](https://docs.falkordb.com/commands/graph.copy): documented source/destination copy; snapshot isolation is tested by mutation.',
              '- [GRAPH.QUERY](https://docs.falkordb.com/commands/graph.query): no multi-statement guarantee relied upon.', '',
              '## Interpretation', '',
              'All fixtures are synthetic. Timing uses perf_counter_ns and includes network/client overhead.',
              'Concurrent client intervals and atomic increments do not prove engine scheduling internals.',
              'Read/write overlap is an observed completion interval, not a promise of snapshot semantics.',
              'Q6 ordered requests need retry recovery; they are not atomic together.', '',
              '## Next phase — only after this gate passes', '',
              '1. Check topology source licenses and encode the credited YAML cores.',
              '2. Implement seed=42 loader and the ADR-17/R-7/R-12 planted scenario.',
              '3. Implement Q2/Q3/Q4/Q7 and run planted-scenario acceptance assertions.', '']
    (docs / 'VERIFIED.md').write_text('\n'.join(lines))


def fixture():
    rng = random.Random(42)
    nodes = [{'id': f'svc-{i}', 'rev': rng.randint(1, 20)} for i in range(58)]
    edges = [{'a': f'svc-{i}', 'b': f'svc-{1 if i == 2 else 0}'} for i in range(1, 15)]
    edges += [{'a': f'svc-{i}', 'b': 'svc-15'} for i in range(16, 58)]
    return nodes, edges


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--blocked', help='Record a confirmed environment blocker without claiming runtime checks')
    args = parser.parse_args()
    report = {'at': datetime.now(timezone.utc).isoformat(), 'seed': 42,
              'image': os.getenv('FALKORDB_IMAGE', 'falkordb/falkordb:latest'),
              'acceptance': 'BLOCKED', 'checks': {}}
    if args.blocked:
        report['blocker'] = args.blocked
        for key in CHECKS:
            report['checks'][key] = {'status': 'BLOCKED', 'error': args.blocked}
        write_report(report)
        print('Phase 0 BLOCKED:', args.blocked)
        return 2
    try:
        from falkordb import FalkorDB
        db = FalkorDB(host=os.getenv('FALKORDB_HOST', 'localhost'),
                      port=int(os.getenv('FALKORDB_PORT', '6379')),
                      password=os.getenv('FALKORDB_PASSWORD') or None,
                      socket_connect_timeout=5, socket_timeout=30)
        db.connection.ping()
        report['server'] = db.connection.info('server')
        report['modules'] = db.connection.execute_command('MODULE', 'LIST')
        report['modules'] = json.loads(json.dumps(report['modules'], default=lambda x: x.decode() if isinstance(x, bytes) else str(x)))
        report['python_client'] = importlib.metadata.version('falkordb')
    except Exception as exc:
        report['blocker'] = f'{type(exc).__name__}: {exc}'
        write_report(report)
        print(report['blocker'])
        return 2

    prefix = f'spike:{uuid.uuid4().hex}'
    graph_names = []
    def new_graph(suffix):
        name = f'{prefix}:{suffix}'
        graph_names.append(name)
        return db.select_graph(name)
    g = new_graph('core')
    nodes, edges = fixture()
    def load(target):
        target.query('UNWIND $nodes AS n CREATE (:Service {id:n.id, rev_per_min:n.rev})', {'nodes': nodes})
        target.query('UNWIND $edges AS e MATCH (a:Service {id:e.a}), (b:Service {id:e.b}) CREATE (a)-[:DEPENDS_ON]->(b)', {'edges': edges})
    def check(key, fn, fallback=None):
        try:
            report['checks'][key] = {'status': 'PASS', 'evidence': fn()}
        except Exception as exc:
            item = {'status': 'FAIL', 'error': f'{type(exc).__name__}: {exc}'}
            if fallback:
                try:
                    item['fallback_evidence'] = fallback()
                    item['fallback_verified'] = True
                except Exception as err:
                    item['fallback_error'] = f'{type(err).__name__}: {err}'
            report['checks'][key] = item
        print(key, report['checks'][key]['status'], flush=True)
    try:
        def connect():
            load(g)
            n = g.query('MATCH (s:Service) RETURN count(s)').result_set[0][0]
            assert n == 58, n
            return {'services': n}
        check('connection', connect)
        if report['checks']['connection']['status'] != 'PASS':
            raise RuntimeError('Fixture creation failed; later checks cannot be trusted')
        def pr():
            rows = g.query("CALL algo.pageRank('Service','DEPENDS_ON') YIELD node,score SET node.pagerank=score RETURN node.id,score").result_set
            assert len(rows) == 58 and all(math.isfinite(r[1]) for r in rows)
            stored = g.query('MATCH (s:Service) WHERE s.pagerank IS NOT NULL RETURN count(s)').result_set[0][0]
            assert stored == 58
            return {'rows': len(rows), 'stored': stored}
        check('pagerank', pr)
        def path_counts():
            rows = g.query('MATCH p=(a:Service)-[:DEPENDS_ON*1..5]->(b:Service) RETURN b.id, count(p)').result_set
            assert rows and dict(rows)['svc-0'] == 14
            return {'path_counts': rows, 'pagerank_required_separately': True}
        def between():
            rows = g.query("CALL algo.betweenness({nodeLabels:['Service'],relationshipTypes:['DEPENDS_ON'],samplingSize:58,samplingSeed:42}) YIELD node,score RETURN node.id,score").result_set
            assert len(rows) == 58 and dict(rows)['svc-1'] > 0
            return {'rows': len(rows), 'bridge_score': dict(rows)['svc-1']}
        check('betweenness', between, path_counts)
        g.query("MATCH (s:Service) WHERE s.id IN ['svc-0','svc-1','svc-2','svc-15'] SET s:Alerting")
        config = "{nodeLabels:['Alerting'],relationshipTypes:['DEPENDS_ON']}"
        def adjacency():
            rows = g.query('MATCH (a:Alerting)-[:DEPENDS_ON]->(b:Alerting) RETURN a.id,b.id').result_set
            ids = {r[0] for r in g.query('MATCH (a:Alerting) RETURN a.id').result_set}
            neighbors = {i: set() for i in ids}
            for a,b in rows:
                neighbors[a].add(b); neighbors[b].add(a)
            components = []
            while ids:
                seen = set(); todo = [min(ids)]
                while todo:
                    i = todo.pop()
                    if i not in seen:
                        seen.add(i); todo.extend(neighbors[i] - seen)
                ids -= seen; components.append(sorted(seen))
            assert sorted(components) == [['svc-0','svc-1','svc-2'], ['svc-15']]
            return {'components': components, 'adjacency': rows}
        def wcc():
            rows = g.query(f'CALL algo.WCC({config}) YIELD node,componentId RETURN node.id,componentId').result_set
            groups = {}
            for sid,c in rows: groups.setdefault(c, []).append(sid)
            assert sorted(sorted(v) for v in groups.values()) == [['svc-0','svc-1','svc-2'], ['svc-15']]
            return {'rows': rows}
        check('wcc', wcc, adjacency)
        def cdlp():
            rows = g.query(f'CALL algo.labelPropagation({config}) YIELD node,communityId RETURN node.id,communityId').result_set
            assert {r[0] for r in rows} == {'svc-0','svc-1','svc-2','svc-15'}
            return {'rows': rows, 'not_used_as_wcc': True}
        check('cdlp', cdlp, adjacency)
        def shortest():
            rows = g.query("MATCH (a:Service {id:'svc-2'}),(b:Service {id:'svc-0'}) MATCH p=shortestPath((a)-[:DEPENDS_ON*1..5]->(b)) RETURN length(p),[n IN nodes(p)|n.id]").result_set
            assert rows == [[2, ['svc-2','svc-1','svc-0']]], rows
            missing = g.query("MATCH (a:Service {id:'svc-0'}),(b:Service {id:'svc-15'}) WITH shortestPath((a)-[:DEPENDS_ON*1..5]->(b)) AS p RETURN length(p)").result_set
            assert missing == [[None]], missing
            return {'connected': rows, 'disconnected': missing}
        def bounded():
            rows = g.query("MATCH p=(:Service {id:'svc-2'})-[:DEPENDS_ON*1..5]->(:Service {id:'svc-0'}) RETURN length(p),[n IN nodes(p)|n.id] ORDER BY length(p) LIMIT 1").result_set
            assert rows == [[2,['svc-2','svc-1','svc-0']]]
            return {'bounded_path': rows}
        check('shortest_path', shortest, bounded)
        def zero():
            rows = g.query("MATCH p=(:Service {id:'svc-1'})-[:DEPENDS_ON*0..5]->(s:Service) RETURN DISTINCT s.id").result_set
            assert {r[0] for r in rows} == {'svc-1','svc-0'}
            return {'reachable_including_self': rows}
        def zero_fallback():
            rows = g.query("MATCH (:Service {id:'svc-1'})-[:DEPENDS_ON*1..5]->(s:Service) RETURN DISTINCT s.id UNION MATCH (s:Service {id:'svc-1'}) RETURN s.id").result_set
            assert {r[0] for r in rows} == {'svc-1','svc-0'}
            return {'positive_hop_union': rows}
        check('zero_hop', zero, zero_fallback)
        def multi():
            g.query('CREATE (:MultiProbe {v:1}); CREATE (:MultiProbe {v:2})')
            n = g.query('MATCH (n:MultiProbe) RETURN count(n)').result_set[0][0]
            assert n == 2, n
            return {'created_nodes': n, 'q6_still_uses_two_requests': True}
        def ordered():
            g.query('CREATE (:OrderedProbe {v:1})')
            g.query('CREATE (:OrderedProbe {v:2})')
            n = g.query('MATCH (n:OrderedProbe) RETURN count(n)').result_set[0][0]
            assert n == 2
            return {'ordered_requests_created': n, 'atomic_together': False}
        check('multi_statement', multi, ordered)
        def copy():
            dest = new_graph('copy')
            start = time.perf_counter_ns()
            db.connection.execute_command('GRAPH.COPY', g.name, dest.name)
            ms = (time.perf_counter_ns() - start) / 1e6
            assert dest.query('MATCH (s:Service) RETURN count(s)').result_set == [[58]]
            dest.query("MATCH (s:Service {id:'svc-0'}) SET s.copy_only=1")
            assert g.query("MATCH (s:Service {id:'svc-0'}) RETURN s.copy_only").result_set == [[None]]
            g.query("MATCH (s:Service {id:'svc-0'}) SET s.source_only=1")
            assert dest.query("MATCH (s:Service {id:'svc-0'}) RETURN s.source_only").result_set == [[None]]
            return {'copy_ms': ms, 'bidirectional_mutation_isolation': True}
        def replay():
            dest = new_graph('replay'); start = time.perf_counter_ns(); load(dest)
            assert dest.query('MATCH (s:Service) RETURN count(s)').result_set == [[58]]
            assert dest.query('MATCH ()-[r:DEPENDS_ON]->() RETURN count(r)').result_set == [[56]]
            return {'replay_ms': (time.perf_counter_ns()-start)/1e6, 'services': 58, 'scope': 'spike fixture only; company seed remains unmeasured'}
        check('graph_copy', copy, replay)
        check('concurrency', lambda: concurrency(db, new_graph('race')))
        def latency():
            query = 'UNWIND $alerting AS sid MATCH p=(a:Service {id:sid})-[:DEPENDS_ON*0..5]->(c:Service) WITH c,count(DISTINCT a) AS hits,min(length(p)) AS nearest WHERE hits=size($alerting) RETURN c.id,nearest,c.pagerank ORDER BY nearest LIMIT 5'
            params = {'alerting': [f'svc-{i}' for i in range(1,10)]}
            if report['checks']['zero_hop']['status'] != 'PASS':
                query = query.replace('*0..5', '*1..5') # sources cannot be common ancestors in this fixture
            for _ in range(10): g.query(query, params)
            samples = []
            for _ in range(100):
                start = time.perf_counter_ns(); rows = g.query(query, params).result_set
                samples.append((time.perf_counter_ns()-start)/1e6)
                assert rows[0][0] == 'svc-0', rows
            return {'fixture_services':58, 'warmup':10, 'samples_ms':samples,
                    'p50_ms':statistics.median(samples), 'p95_ms':sorted(samples)[math.ceil(.95*len(samples))-1], 'query':query}
        check('latency', latency)
        report['acceptance'] = 'PASS' if all(
            report['checks'][k]['status'] == 'PASS' or report['checks'][k].get('fallback_verified') for k in CHECKS) else 'FAIL'
    except Exception as exc:
        report['fatal'] = f'{type(exc).__name__}: {exc}'
        report['acceptance'] = 'FAIL'
    finally:
        report['cleanup_errors'] = []
        for name in graph_names:
            try: db.connection.execute_command('GRAPH.DELETE', name)
            except Exception as exc:
                # A failed optional copy may never have created its destination.
                if db.connection.exists(name): report['cleanup_errors'].append(str(exc))
        if report['cleanup_errors']: report['acceptance'] = 'FAIL'
        write_report(report)
    print('Phase 0 acceptance:', report['acceptance'])
    return 0 if report['acceptance'] == 'PASS' else 1


def concurrency(db, g):
    """All synchronization is at client start only; graph conditional SET arbitrates claims."""
    workers, tasks = 20, 8
    g.query('UNWIND range(0,19) AS i CREATE (:Agent {id:toString(i)})')
    g.query("UNWIND range(0,7) AS i CREATE (:Task {id:toString(i),status:'open',version:0,lease_until:0})")
    claim = (ROOT/'backend/app/queries/q01_claim.cypher').read_text()
    invariant = (ROOT/'backend/app/queries/claim_invariant.cypher').read_text()
    barrier = threading.Barrier(workers)
    def worker(i):
        local = db.select_graph(g.name)
        barrier.wait(timeout=20)
        order = list(range(tasks)); random.Random(42+i).shuffle(order)
        won, lost = [], 0
        for t in order:
            rows = local.query(claim, {'task':str(t),'agent':str(i),'now':1000,'lease_ms':10000}).result_set
            if rows: won.extend(rows)
            else: lost += 1
        return {'wins':won,'lost_attempts':lost}
    start = time.perf_counter_ns()
    with ThreadPoolExecutor(max_workers=workers) as pool: results = list(pool.map(worker, range(workers)))
    elapsed = (time.perf_counter_ns()-start)/1e6
    winners = [r for result in results for r in result['wins']]
    double = g.query(invariant).result_set[0][0]
    nclaims = g.query('MATCH ()-[c:CLAIMED]->() RETURN count(c)').result_set[0][0]
    nclaimed = g.query("MATCH (t:Task {status:'claimed'}) RETURN count(t)").result_set[0][0]
    assert len(winners)==tasks==nclaims==nclaimed and double==0, (winners,nclaims,nclaimed,double)
    g.query('CREATE (:Counter {v:0})')
    barrier2 = threading.Barrier(workers)
    intervals=[]
    def increment(i):
        local=db.select_graph(g.name); barrier2.wait(timeout=20)
        begin=time.perf_counter_ns()
        rows=local.query('MATCH (n:Counter) SET n.v=n.v+1 RETURN n.v').result_set
        return {'worker':i,'start_ns':begin,'end_ns':time.perf_counter_ns(),'value':rows[0][0]}
    with ThreadPoolExecutor(max_workers=workers) as pool: intervals=list(pool.map(increment,range(workers)))
    assert sorted(i['value'] for i in intervals)==list(range(1,workers+1))
    # Slow write and read probe; client overlap is reported without claiming engine internals.
    started=threading.Event()
    def slow():
        local=db.select_graph(g.name); begin=time.perf_counter_ns(); started.set()
        local.query('UNWIND range(1,50000) AS i CREATE (:WriteProbe {v:i})')
        return {'start_ns':begin,'end_ns':time.perf_counter_ns()}
    reads=[]
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(slow); started.wait(timeout=20)
        for _ in range(10):
            begin=time.perf_counter_ns()
            db.select_graph(g.name).ro_query('MATCH (s:Task) RETURN count(s)')
            reads.append({'start_ns':begin,'end_ns':time.perf_counter_ns()})
        write=future.result()
    completed_during=sum(write['start_ns']<=r['start_ns'] and r['end_ns']<write['end_ns'] for r in reads)
    return {'workers':workers,'tasks':tasks,'elapsed_ms':elapsed,'double_claim_groups':double,
            'successful_claims':len(winners),'lost_attempts':sum(r['lost_attempts'] for r in results),
            'increment_intervals':intervals,'increments_have_no_lost_updates':True,
            'slow_write_interval':write,'read_intervals':reads,'reads_completed_inside_write_client_interval':completed_during,
            'interpretation':'Atomic updates observed; engine write serialization is not proven by timing alone.'}

if __name__ == '__main__':
    raise SystemExit(main())
