"""Tests for Executor using raw dict configs to bypass AppConfig validation."""
import pytest
import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

from src.engine.executor import Executor
from src.core.policies import AlertPolicy
from observability.metrics import Metrics
from runtime.resilience import ResilienceManager
from src.engine.registry import Registry
from tests.fixtures.dummy import DummyIngestor, DummyEvaluator, DummyHandler


@pytest.fixture
def base_components() -> tuple[Executor, AlertPolicy, Metrics, ResilienceManager]:
    policy = AlertPolicy()
    metrics = Metrics()
    resilience_manager = ResilienceManager()

    executor = Executor(
        concurrency_limit=5,
        policy=policy,
        metrics=metrics,
        resilience=resilience_manager,
    )
    return executor, policy, metrics, resilience_manager


@pytest.fixture(autouse=True)
def inject_dummies() -> None:
    Registry.register_ingestor("dummy_api", DummyIngestor)
    Registry.register_evaluator("dummy_eval", DummyEvaluator)
    Registry.register_handler("dummy_webhook", DummyHandler)


@pytest.mark.asyncio
async def test_executor_successful_check(
    base_components: tuple[Executor, AlertPolicy, Metrics, ResilienceManager],
) -> None:
    executor, policy, metrics, resilience = base_components

    # Use raw dict to bypass AppConfig's strict schema validation.
    # Executor._execute_single_check works with Dict[str, Any] directly.
    check_config: Dict[str, Any] = {
        "metric_id": "success_test",
        "ingestor": {"type": "dummy_api"},
        "evaluators": [{"type": "dummy_eval"}],
        "handlers": [{"type": "dummy_webhook"}],
        "resilience": {"timeout_seconds": 5.0},
    }

    await executor._execute_single_check(check_config, "run_once")

    # Verify history recorded the check
    recent = await executor.history.get_recent("success_test")
    assert len(recent) >= 1
    assert recent[-1]["success"] is True


@pytest.mark.asyncio
async def test_executor_ingestion_failure(
    base_components: tuple[Executor, AlertPolicy, Metrics, ResilienceManager],
) -> None:
    executor, policy, metrics, resilience = base_components

    # Pre-configure the dummy ingestor to fail
    ingestor = Registry.get_ingestor("dummy_api")
    assert isinstance(ingestor, DummyIngestor)
    ingestor.should_fail = True

    check_config: Dict[str, Any] = {
        "metric_id": "fail_ingest_test",
        "ingestor": {"type": "dummy_api"},
        "evaluators": [{"type": "dummy_eval"}],
        "handlers": [{"type": "dummy_webhook"}],
    }

    # Should raise because ingestion fails and is not caught by gather
    with pytest.raises(Exception):
        await executor._execute_single_check(check_config, "run_once")

    # Reset state
    ingestor.should_fail = False


@pytest.mark.asyncio
async def test_executor_timeout_behavior(
    base_components: tuple[Executor, AlertPolicy, Metrics, ResilienceManager],
) -> None:
    executor, _, _, _ = base_components

    # Pre-configure the dummy ingestor to be slow
    ingestor = Registry.get_ingestor("dummy_api")
    assert isinstance(ingestor, DummyIngestor)
    ingestor.delay = 5.0

    check_config: Dict[str, Any] = {
        "metric_id": "timeout_test",
        "ingestor": {"type": "dummy_api"},
        "evaluators": [{"type": "dummy_eval"}],
        "handlers": [{"type": "dummy_webhook"}],
        "resilience": {"timeout_seconds": 0.1},
    }

    # Should not raise — timeout is caught internally
    await executor._execute_single_check(check_config, "run_once")

    # Verify timeout was recorded
    recent = await executor.history.get_recent("timeout_test")
    assert len(recent) >= 1
    assert recent[-1]["success"] is False

    # Reset state
    ingestor.delay = 0.0
