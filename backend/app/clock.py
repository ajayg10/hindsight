"""Business time is injected; wall-clock time is reserved for benchmarks."""
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DemoClock:
    now_ms: int

    @classmethod
    def frozen(cls):
        # Scenario time is synthetic and independent of the real event clock.
        return cls(int(datetime.fromisoformat("2026-10-15T03:11:00+05:30").timestamp() * 1000))

    def advance(self, milliseconds: int):
        if milliseconds < 0:
            raise ValueError("Use an as-of query for time travel; execution time cannot rewind")
        self.now_ms += milliseconds
        return self.now_ms
