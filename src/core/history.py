import asyncio
from typing import Dict, List, Any
from collections import deque

class ExecutionHistory:
    def __init__(self, max_size: int = 100) -> None:
        self.max_size = max_size
        self._history: Dict[str, deque[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def add_result(self, check_id: str, success: bool, duration_ms: float) -> None:
        async with self._lock:
            if check_id not in self._history:
                self._history[check_id] = deque(maxlen=self.max_size)
            self._history[check_id].append({
                "success": success,
                "duration_ms": duration_ms
            })

    async def get_recent(self, check_id: str) -> List[Dict[str, Any]]:
        async with self._lock:
            if check_id not in self._history:
                return []
            return list(self._history[check_id])
