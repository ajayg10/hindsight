"""
Investigator Agent.
Investigates root cause candidates using genuinely different graph heuristics:
- Investigator-A: Common upstream dependency intersection (Q2) -> lands on cache-b
- Investigator-B: Centrality / Betweenness ranking among alerting services -> lands on checkout-api
Coordinates exclusively via graph state: claims, hypotheses, conflict resolution, handoffs.
Calls ONLY the Hindsight MCP tool registry via asyncio.to_thread.
"""
import asyncio
from typing import Dict, List, Optional, Any

class InvestigatorAgent:
    def __init__(self, agent_id: str, heuristic: str, tools: Any = None):
        self.agent_id = agent_id
        self.heuristic = heuristic  # 'common_dependency' or 'betweenness_centrality'
        self.tools = tools

    async def claim_and_investigate(self, task_id: str, incident_id: str) -> Dict[str, Any]:
        """Claims investigation task and formulates hypothesis based on its heuristic."""
        # 1. Claim task
        claim_res = await asyncio.to_thread(self.tools.claim_task, task_id, self.agent_id)
        if not claim_res.get("claimed"):
            return {"agent_id": self.agent_id, "status": "claim_failed", "details": claim_res}

        # 2. Run heuristic via MCP tool registry
        if self.heuristic == "common_dependency":
            analysis = await asyncio.to_thread(self.tools.root_cause_candidates, incident_id)
            root_service = analysis["top_candidate"]
            confidence = 0.95
        else:
            analysis = await asyncio.to_thread(self.tools.rank_services, incident_id, method="betweenness")
            root_service = analysis["top_candidate"]
            confidence = 0.85

        # 3. Assert hypothesis into graph state
        hyp_res = await asyncio.to_thread(
            self.tools.assert_hypothesis,
            incident_id=incident_id,
            agent_id=self.agent_id,
            root_service=root_service,
            heuristic=self.heuristic,
            confidence=confidence
        )

        return {
            "agent_id": self.agent_id,
            "status": "hypothesis_asserted",
            "task_id": task_id,
            "hypothesis": hyp_res,
            "root_service": root_service,
            "confidence": confidence,
            "answer_id": analysis["answer_id"]
        }

    async def resolve_competing_hypotheses(self, incident_id: str, hypothesis_a: str, hypothesis_b: str) -> Dict[str, Any]:
        """Evaluates Q10 graph path subsumption between competing hypotheses."""
        return await asyncio.to_thread(self.tools.resolve_conflict, incident_id, hypothesis_a, hypothesis_b)

    async def handoff_to_responder(self, task_id: str, responder_id: str, evidence_ids: List[str]) -> Dict[str, Any]:
        """Hands off validated root cause to Responder with evidence IDs."""
        return await asyncio.to_thread(self.tools.handoff, task_id, self.agent_id, responder_id, evidence_ids)
