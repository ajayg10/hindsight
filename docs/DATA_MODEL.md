# Graph data model — planned, not implemented

Phase 1 will create the company brain, episode/fact/procedure memory, and
coordination nodes described in the project brief. Phase 0 uses disposable
synthetic test graphs only. No production schema or planted scenario is loaded.

Tenant graphs `t:{tenant}`, session forks `s:{session}`, and operator graphs
`u:{tenant}:{user}` will be separate graphs. Cross-graph references use IDs and
application composition; no cross-graph Cypher is promised.
