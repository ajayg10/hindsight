"""
Sentinel Agent.
Monitors incoming alerts, groups connected alerting services into a single incident via WCC,
and opens coordination tasks on the graph.
Calls ONLY the Hindsight MCP tool registry via asyncio.to_thread.
"""
import asyncio
from typing import Dict, List, Optional, Any

class SentinelAgent:
    def __init__(self, agent_id: str = "sentinel", tools: Any = None):
        self.agent_id = agent_id
        self.tools = tools

    async def handle_alert_storm(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Collapses alerting services into incidents using WCC tool,
        and opens coordination task for investigation.
        """
        # Call MCP tool registry
        split_result = await asyncio.to_thread(self.tools.split_storm, alerts)
        incident_id = split_result["incident_id"]

        return {
            "agent_id": self.agent_id,
            "incident_id": incident_id,
            "clusters": split_result["clusters"],
            "policy_rule_id": split_result["policy_rule_id"],
            "policy_chip": split_result["policy_chip"],
            "answer_id": split_result["answer_id"]
        }
