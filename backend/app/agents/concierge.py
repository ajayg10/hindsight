"""
Concierge Agent.
Answers operational questions and routes incidents to verified human owners and experts:
- who_owns: finds owning team and primary on-call
- who_knows: identifies experts from derived graph evidence, routing around people on leave (Priya -> Marco)
- trace_decision: retrieves decision provenance from ADRs, threads, and authors
Calls ONLY the Hindsight MCP tool registry via asyncio.to_thread.
"""
import asyncio
from typing import Dict, List, Optional, Any

class ConciergeAgent:
    def __init__(self, agent_id: str = "concierge", tools: Any = None):
        self.agent_id = agent_id
        self.tools = tools

    async def route_incident(self, service_id: str = "cache-b") -> Dict[str, Any]:
        """Identifies owning team and routes to available expert."""
        # 1. Who owns
        owner_info = await asyncio.to_thread(self.tools.who_owns, service_id)

        # 2. Who knows (with on-leave routing)
        expert_info = await asyncio.to_thread(self.tools.who_knows, service_id)

        # 3. Decision provenance
        decision_info = await asyncio.to_thread(self.tools.trace_decision, service_id)

        return {
            "agent_id": self.agent_id,
            "service_id": service_id,
            "owner": owner_info.get("owner"),
            "primary_expert": expert_info.get("primary_expert"),
            "primary_on_leave": expert_info.get("primary_on_leave"),
            "routed_expert": expert_info.get("routed_expert"),
            "routed_score": expert_info.get("routed_score"),
            "expert_summary": expert_info.get("summary"),
            "decision_trace": decision_info.get("trace")
        }
