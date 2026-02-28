"""Tests for ExecutionHistory async ring buffer."""
import pytest

from src.core.history import ExecutionHistory


@pytest.fixture
def execution_history() -> ExecutionHistory:
    return ExecutionHistory(max_size=5)


@pytest.mark.asyncio
async def test_execution_history_add_and_retrieve(
    execution_history: ExecutionHistory,
) -> None:
    await execution_history.add_result(
        check_id="test_check", success=True, duration_ms=10.0
    )

    recent = await execution_history.get_recent("test_check")
    assert len(recent) == 1
    assert recent[0]["success"] is True


@pytest.mark.asyncio
async def test_execution_history_ring_buffer_overflow(
    execution_history: ExecutionHistory,
) -> None:
    for i in range(10):
        await execution_history.add_result(
            check_id="shared_check", success=True, duration_ms=i * 1.0
        )

    recent = await execution_history.get_recent("shared_check")
    assert len(recent) == 5  # Max size is 5
    assert recent[-1]["duration_ms"] == 9.0
