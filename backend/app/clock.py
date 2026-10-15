"""
Dual clock architecture for Hindsight:
1. DemoClock: Injected synthetic business timeline (frozen at 2026-10-15T03:11:00+05:30)
   used for incident episodes, ADR-17, historical facts, and temporal decay.
2. CoordinationClock: Real-world epoch time (milliseconds)
   used for agent task leasing, heartbeats, concurrency races, and lease expiration.
"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import time

SIX_DAYS_MS = 6 * 24 * 3600 * 1000

@dataclass
class DemoClock:
    """Synthetic business timeline for graph entities, decay, and as-of queries."""
    now_ms: int

    @classmethod
    def frozen(cls):
        # Scenario time is synthetic and independent of the real event clock.
        # Frozen at 2026-10-15T03:11:00+05:30
        dt = datetime.fromisoformat("2026-10-15T03:11:00+05:30")
        return cls(int(dt.timestamp() * 1000))

    @classmethod
    def now(cls) -> int:
        return cls.frozen().now_ms

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


class CoordinationClock:
    """Real epoch time used for leases, worker heartbeats, and live agent coordination."""

    @staticmethod
    def now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def is_expired(lease_until_ms: int) -> bool:
        return CoordinationClock.now_ms() > lease_until_ms
