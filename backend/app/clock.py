"""Business time is injected; wall-clock time is reserved for benchmarks."""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

SIX_DAYS_MS = 6 * 24 * 3600 * 1000

@dataclass
class DemoClock:
    now_ms: int

    @classmethod
    def frozen(cls):
        # Scenario time is synthetic and independent of the real event clock.
        # Frozen at 2026-10-15T03:11:00+05:30
        dt = datetime.fromisoformat("2026-10-15T03:11:00+05:30")
        return cls(int(dt.timestamp() * 1000))

    @property
    def adr17_ms(self) -> int:
        """ADR-17 is placed at exactly clock minus 6 days."""
        return self.now_ms - SIX_DAYS_MS

    @property
    def before_adr17_ms(self) -> int:
        """Scrubber point before ADR-17 (7 days ago)."""
        return self.now_ms - (7 * 24 * 3600 * 1000)

    def advance(self, milliseconds: int):
        if milliseconds < 0:
            raise ValueError("Use an as-of query for time travel; execution time cannot rewind")
        self.now_ms += milliseconds
        return self.now_ms

    def iso(self) -> str:
        return datetime.fromtimestamp(self.now_ms / 1000, tz=timezone.utc).isoformat()
