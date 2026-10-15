"""
Responder Agent.
Selects and executes remediation procedures:
- Recalls procedures from graph memory, skipping ones invalidated by ADRs (refusing R-7, selecting R-12)
- Evaluates blast radius (14 services) and triggers approval gate
- Defaults to dry_run / approval required until operator signs off
- Calls simulated executor writing Action episode to graph
Calls ONLY the Hindsight MCP tool registry via asyncio.to_thread.
"""
import asyncio
from typing import Dict, List, Optional, Any

class ResponderAgent:
    def __init__(self, agent_id: str = "responder", tools: Any = None):
        self.agent_id = agent_id
        self.tools = tools

    async def remediate(self, task_id: str, incident_id: str, target_service: str = "cache-b", operator_approved: bool = False, operator_name: Optional[str] = None) -> Dict[str, Any]:
        """Runs the remediation workflow through MCP tools."""
        # 1. Claim remediation task
        claim_res = await asyncio.to_thread(self.tools.claim_task, task_id, self.agent_id)

        # 2. Recall procedure
        proc_res = await asyncio.to_thread(self.tools.recall_procedure, "cache_exhaustion")
        selected_proc = proc_res.get("selected_procedure")
        refused_procs = proc_res.get("refused_procedures", [])

        # 3. Evaluate blast radius & safety guardrail
        blast_res = await asyncio.to_thread(self.tools.blast_radius, target_service)
        guardrail = blast_res["guardrail"]

        # 4. Attempt execution
        # If approval required and not yet approved, execution is gated
        action_res = await asyncio.to_thread(
            self.tools.execute_action,
            procedure_id=selected_proc["id"] if selected_proc else "R-12",
            dry_run=(not operator_approved),
            approved=operator_approved,
            operator=operator_name
        )

        return {
            "agent_id": self.agent_id,
            "task_id": task_id,
            "incident_id": incident_id,
            "target_service": target_service,
            "selected_procedure": selected_proc,
            "refused_procedures": refused_procs,
            "blast_count": blast_res["blast_count"],
            "rev_per_min": blast_res["rev_per_min"],
            "guardrail": guardrail,
            "action_result": action_res,
            "status": "completed" if operator_approved else "pending_approval"
        }
