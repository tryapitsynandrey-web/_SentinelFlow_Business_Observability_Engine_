import asyncio
import time
from enum import Enum
from typing import Optional

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    """
    Async-safe circuit breaker.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        
        self._lock = asyncio.Lock()

    async def allow_request(self) -> bool:
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                if self.last_failure_time is not None:
                    elapsed = time.monotonic() - self.last_failure_time
                    if elapsed >= self.recovery_timeout:
                        self.state = CircuitState.HALF_OPEN
                        return True
                return False
                
            # HALF_OPEN state allows 1 request conceptually, but here we'll just allow it until failure or success
            if self.state == CircuitState.HALF_OPEN:
                return True
                
            return False

    async def record_success(self) -> None:
        async with self._lock:
            self.failures = 0
            self.state = CircuitState.CLOSED
            self.last_failure_time = None

    async def record_failure(self) -> None:
        async with self._lock:
            self.failures += 1
            self.last_failure_time = time.monotonic()
            
            if self.state == CircuitState.CLOSED and self.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
            elif self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
