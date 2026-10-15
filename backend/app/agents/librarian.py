"""
Librarian Worker Agent.
Runs asynchronous background maintenance cycles:
- Audits documentation staleness against recent architectural changes
- Opens coordination tasks for stale runbooks / architecture records
- Sweeps fact confidence decay
- Recomputes EXPERT_IN scores from operational evidence
- Refreshes graph PageRank and centrality metrics
Calls ONLY the Hindsight MCP tool registry via asyncio.to_thread.
"""
import asyncio
from typing import Dict, List, Optional, Any

class LibrarianWorker:
    def __init__(self, agent_id: str = "librarian", tools: Any = None):
        self.agent_id = agent_id
        self.tools = tools
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def run_maintenance_cycle(self) -> Dict[str, Any]:
        """Executes a single complete maintenance cycle."""
        # 1. Audit doc staleness
        audit_res = await asyncio.to_thread(self.tools.staleness_audit)
        stale_docs = audit_res.get("stale_docs", [])

        # 2. Open tasks for each stale document
        opened_tasks = []
        for doc in stale_docs:
            task = await asyncio.to_thread(
                self.tools.open_doc_stale_task,
                doc_id=doc["doc_id"],
                title=f"Update stale doc: {doc['title']}",
                assignee="marco"
            )
            opened_tasks.append(task)

        # 3. Decay sweep
        decay_res = await asyncio.to_thread(self.tools.decay_sweep)

        # 4. Recompute EXPERT_IN
        exp_res = await asyncio.to_thread(self.tools.recompute_expertise)

        # 5. Refresh PageRank and algorithms
        pr_res = await asyncio.to_thread(self.tools.refresh_algorithms)

        return {
            "agent_id": self.agent_id,
            "stale_docs_count": len(stale_docs),
            "opened_tasks": opened_tasks,
            "recomputed_experts": len(exp_res) if exp_res else 0,
            "status": "cycle_completed"
        }

    async def start(self, interval_s: float = 30.0):
        """Starts worker in background loop."""
        self._running = True
        while self._running:
            try:
                await self.run_maintenance_cycle()
            except Exception:
                pass
            await asyncio.sleep(interval_s)

    def stop(self):
        """Stops the background loop."""
        self._running = False
