"""Tests for Scheduler run-once and daemon modes."""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from src.engine.scheduler import Scheduler
from src.engine.executor import Executor
from src.config.parser import AppConfig


@pytest.fixture
def mock_executor() -> MagicMock:
    executor = MagicMock(spec=Executor)
    executor.execute_batch = AsyncMock(return_value=None)
    return executor


@pytest.mark.asyncio
async def test_scheduler_run_once(mock_executor: MagicMock) -> None:
    scheduler = Scheduler(executor=mock_executor)

    # Build a minimal valid AppConfig by mocking it
    config = MagicMock(spec=AppConfig)

    await scheduler.run_once(config)
    mock_executor.execute_batch.assert_called_once_with(config)


@pytest.mark.asyncio
async def test_scheduler_daemon_mode_cancellation(mock_executor: MagicMock) -> None:
    scheduler = Scheduler(executor=mock_executor)

    # Plain MagicMock allows nested attribute access (spec= blocks it)
    config = MagicMock()
    config.global_config.interval_seconds = 1

    task = asyncio.create_task(scheduler.run_daemon(config))

    # Let it run briefly
    await asyncio.sleep(0.1)

    # Cancel the daemon
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert mock_executor.execute_batch.called
