from datetime import datetime, timezone
from typing import Dict, Any


class AlertPolicy:
    """
    Stateful router for deduplicating alerts and enforcing cooldowns.
    """

    def __init__(self) -> None:
        self._last_seen: Dict[str, datetime] = {}
        self._last_dispatched: Dict[str, datetime] = {}
        self._failure_counts: Dict[str, int] = {}

    def _generate_fingerprint(
        self,
        metric_id: str,
        evaluator_type: str,
        severity: str,
    ) -> str:
        return f"{metric_id}:{evaluator_type}:{severity}"

    def should_dispatch(
        self,
        metric_id: str,
        evaluator_type: str,
        severity: str,
        cooldown_seconds: int,
        dedupe_window_seconds: int,
        event: Any = None,
    ) -> bool:
        now: datetime = datetime.now(timezone.utc)
        fingerprint: str = self._generate_fingerprint(
            metric_id, evaluator_type, severity
        )

        last_dispatched = self._last_dispatched.get(fingerprint)

        self._last_seen[fingerprint] = now

        if last_dispatched is not None:
            elapsed = (now - last_dispatched).total_seconds()
            if elapsed < dedupe_window_seconds:
                self._failure_counts[fingerprint] = self._failure_counts.get(fingerprint, 0) + 1
                return False

        count = self._failure_counts.pop(fingerprint, 0)
        if count > 0 and hasattr(event, "message"):
            event.message += f" (Occurred {count} times in last window)"

        self._last_dispatched[fingerprint] = now
        return True

    def purge_old_state(self, max_age_seconds: int = 86400) -> None:
        now: datetime = datetime.now(timezone.utc)

        for fingerprint in list(self._last_seen.keys()):
            seen_time = self._last_seen[fingerprint]
            if (now - seen_time).total_seconds() > max_age_seconds:
                del self._last_seen[fingerprint]

        for fingerprint in list(self._last_dispatched.keys()):
            dispatch_time = self._last_dispatched[fingerprint]
            if (now - dispatch_time).total_seconds() > max_age_seconds:
                del self._last_dispatched[fingerprint]