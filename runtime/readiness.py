from typing import Dict

class Readiness:
    def __init__(self) -> None:
        self._is_ready: bool = False
        self._reason: str = "Initializing"

    def set_ready(self) -> None:
        self._is_ready = True
        self._reason = ""

    def set_not_ready(self, reason: str) -> None:
        self._is_ready = False
        self._reason = reason

    def snapshot(self) -> Dict[str, object]:
        return {
            "ready": self._is_ready,
            "reason": self._reason if not self._is_ready else None
        }
