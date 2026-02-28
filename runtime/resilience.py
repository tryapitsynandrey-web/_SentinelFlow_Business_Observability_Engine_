import asyncio
import time
from typing import Callable, Awaitable, TypeVar, Dict, Any

T = TypeVar("T")

class CircuitState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreakerOpenException(Exception):
    def __init__(self, message: str = "Circuit is OPEN"):
        super().__init__(message)

class CircuitBreaker:
    def __init__(self, failure_threshold: int, reset_timeout_seconds: float) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    async def call(self, coro_factory: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            if self.state == CircuitState.OPEN:
                now = time.perf_counter()
                if now - self.last_failure_time > self.reset_timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerOpenException()

        try:
            result = await coro_factory()
        except Exception:
            async with self._lock:
                if self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.OPEN
                    self.last_failure_time = time.perf_counter()
                else:
                    self.failures += 1
                    if self.failures >= self.failure_threshold:
                        self.state = CircuitState.OPEN
                        self.last_failure_time = time.perf_counter()
            raise
        else:
            async with self._lock:
                self.failures = 0
                self.state = CircuitState.CLOSED
            return result

class CheckResilience:
    def __init__(
        self,
        max_inflight: int,
        timeout_seconds: float,
        cb_enabled: bool,
        failure_threshold: int,
        reset_timeout_seconds: float
    ):
        self._semaphore = asyncio.Semaphore(max_inflight)
        self.timeout_seconds = timeout_seconds
        self.cb_enabled = cb_enabled
        self.circuit_breaker = CircuitBreaker(failure_threshold, reset_timeout_seconds)

    async def execute(self, coro_factory: Callable[[], Awaitable[T]]) -> T:
        async with self._semaphore:
            if self.cb_enabled:
                return await self.circuit_breaker.call(coro_factory)
            else:
                return await coro_factory()

class ResilienceManager:
    def __init__(self) -> None:
        self._checks: Dict[str, CheckResilience] = {}
        self._lock = asyncio.Lock()

    async def for_check(self, check_id: str, cfg: Dict[str, Any]) -> CheckResilience:
        async with self._lock:
            if check_id not in self._checks:
                max_inflight = int(cfg.get("max_inflight", 10))
                timeout_seconds = float(cfg.get("timeout_seconds", 15.0))
                cb_cfg = cfg.get("circuit_breaker", {})
                
                cb_enabled = bool(cb_cfg.get("enabled", True))
                failure_threshold = int(cb_cfg.get("failure_threshold", 5))
                reset_timeout_seconds = float(cb_cfg.get("reset_timeout_seconds", 30.0))
                
                self._checks[check_id] = CheckResilience(
                    max_inflight=max_inflight,
                    timeout_seconds=timeout_seconds,
                    cb_enabled=cb_enabled,
                    failure_threshold=failure_threshold,
                    reset_timeout_seconds=reset_timeout_seconds
                )
            return self._checks[check_id]
