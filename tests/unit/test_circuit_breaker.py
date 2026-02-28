import pytest
import asyncio
from runtime.resilience import CircuitBreaker, CircuitState, CircuitBreakerOpenException

@pytest.mark.asyncio
async def test_circuit_breaker_flow() -> None:
    cb = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=0.1)

    async def success_op() -> str:
        return "ok"

    async def fail_op() -> str:
        raise ValueError("Network error")

    # 1. Closed state works
    res = await cb.call(success_op)
    assert res == "ok"
    assert cb.state == CircuitState.CLOSED
    assert cb.failures == 0

    # 2. First failure
    with pytest.raises(ValueError):
        await cb.call(fail_op)
    assert cb.state == CircuitState.CLOSED
    assert cb.failures == 1

    # 3. Second failure triggers open
    with pytest.raises(ValueError):
        await cb.call(fail_op)
    assert cb.state == CircuitState.OPEN

    # 4. Immediate call fails fast
    with pytest.raises(CircuitBreakerOpenException):
        await cb.call(success_op)

    # 5. Wait for reset timeout -> Half-Open -> Success -> Closed
    await asyncio.sleep(0.15)
    
    # First call after sleep transitions to half-open implicitly and succeeds
    res = await cb.call(success_op)
    assert res == "ok"
    assert cb.state == CircuitState.CLOSED
    assert cb.failures == 0

@pytest.mark.asyncio
async def test_circuit_breaker_half_open_failure() -> None:
    cb = CircuitBreaker(failure_threshold=1, reset_timeout_seconds=0.1)

    async def fail_op() -> str:
        raise ValueError("Network error")

    with pytest.raises(ValueError):
        await cb.call(fail_op)
        
    assert cb.state == CircuitState.OPEN

    # Wait for reset timeout
    await asyncio.sleep(0.15)

    # Fails immediately back into OPEN
    with pytest.raises(ValueError):
        await cb.call(fail_op)

    assert cb.state == CircuitState.OPEN
