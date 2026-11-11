"""Usage caps for a public demo, where anyone on the internet spends the owner's API quota.

Two counters, both in memory: one per UTC day for everybody, one per browser session. They reset
when the process restarts, which is fine for their job: they bound what a burst of visitors or a
script can cost, they are not accounting. 0 disables a cap (the default, for local use).
"""

import threading
from datetime import UTC, datetime


class DailyBudget:
    """At most `limit` units per UTC day, shared by every thread of the process."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._day = ""
        self._used = 0
        self._lock = threading.Lock()

    def take(self, now: datetime | None = None) -> bool:
        """Count one use and return True, or return False when today's budget is spent."""
        if self.limit <= 0:
            return True
        day = (now or datetime.now(UTC)).strftime("%Y-%m-%d")
        with self._lock:
            if day != self._day:
                self._day, self._used = day, 0
            if self._used >= self.limit:
                return False
            self._used += 1
            return True

    @property
    def left(self) -> int | None:
        return None if self.limit <= 0 else max(0, self.limit - self._used)


def refusal(daily: DailyBudget, session_used: int, session_limit: int) -> str | None:
    """None when the question may run (and it is then counted), else the message to show."""
    if session_limit > 0 and session_used >= session_limit:
        return (
            f"This demo answers {session_limit} questions per visit. "
            "Clone the repository to run it without limits."
        )
    if not daily.take():
        return "The demo has used today's quota of its free model. It resets at midnight UTC."
    return None
