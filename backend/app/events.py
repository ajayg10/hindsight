"""
Hindsight In-Process Typed Event Bus.
Emits typed events with monotonically increasing sequence numbers.
Supports configurable pacing:
- 'fast': 0ms delay for automated tests and CI
- 'demo': paced delay for live demonstration and visualization

Typed Events:
- alert: alert received on service
- task_claimed: agent claimed coordination task
- lease_expired: lease expired and reclaimed
- handoff: agent handed off task with evidence IDs
- hypothesis: root cause hypothesis proposed
- conflict: hypothesis conflict detected and resolved
- procedure_refused: procedure refused due to architectural change
- fact_superseded: fact supersession recorded
- approval_required: blast radius exceeds threshold, approval gate opened
- answer: tool generated traceable answer node
- action_executed: remediation procedure action executed
"""
import asyncio
from dataclasses import dataclass, asdict, field
import time
from typing import Dict, List, Optional, Any, Callable

EVENT_TYPES = {
    "alert",
    "task_claimed",
    "lease_expired",
    "agent_killed",
    "worker_race",
    "handoff",
    "hypothesis",
    "conflict",
    "procedure_refused",
    "fact_superseded",
    "approval_required",
    "answer",
    "action_executed",
    "incident_created",
    "doc_task_opened",
    "counterfactual_fork_created"
}

@dataclass
class Event:
    seq: int
    event_type: str
    timestamp_ms: int
    payload: Dict[str, Any]

class EventBus:
    def __init__(self, mode: str = "fast", demo_delay_s: float = 0.5):
        self.mode = mode  # "fast" or "demo"
        self.demo_delay_s = demo_delay_s
        self._seq = 0
        self._events: List[Event] = []
        self._subscribers: List[Callable[[Event], Any]] = []

    def set_mode(self, mode: str, demo_delay_s: float = 0.5):
        assert mode in ("fast", "demo"), f"Unknown mode: {mode}"
        self.mode = mode
        self.demo_delay_s = demo_delay_s

    def subscribe(self, callback: Callable[[Event], Any]):
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Event], Any]):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def emit(self, event_type: str, payload: Dict[str, Any], timestamp_ms: Optional[int] = None) -> Event:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"Unknown event type: {event_type}. Allowed: {EVENT_TYPES}")
        self._seq += 1
        if timestamp_ms is None:
            timestamp_ms = int(time.time() * 1000)
        ev = Event(
            seq=self._seq,
            event_type=event_type,
            timestamp_ms=timestamp_ms,
            payload=payload
        )
        self._events.append(ev)
        for sub in self._subscribers:
            try:
                res = sub(ev)
                if asyncio.iscoroutine(res):
                    asyncio.create_task(res)
            except Exception:
                pass
        return ev

    async def emit_async(self, event_type: str, payload: Dict[str, Any], timestamp_ms: Optional[int] = None) -> Event:
        ev = self.emit(event_type, payload, timestamp_ms)
        if self.mode == "demo" and self.demo_delay_s > 0:
            await asyncio.sleep(self.demo_delay_s)
        return ev

    def get_events(self) -> List[Event]:
        return list(self._events)

    def get_transcript(self) -> List[Dict[str, Any]]:
        return [asdict(e) for e in self._events]

    def clear(self):
        self._seq = 0
        self._events.clear()

# Global default event bus instance
global_bus = EventBus(mode="fast")
