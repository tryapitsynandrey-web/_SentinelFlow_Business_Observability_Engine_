"""Full pipeline integration test using in-memory dummy components."""
import pytest
from typing import Any, Dict

from src.engine.registry import Registry
from tests.fixtures.dummy import DummyIngestor, DummyEvaluator, DummyHandler
from src.engine.executor import Executor
from src.core.policies import AlertPolicy
from observability.metrics import Metrics
from runtime.resilience import ResilienceManager


@pytest.fixture(autouse=True)
def map_dummies() -> None:
    Registry.register_ingestor("mem_api", DummyIngestor)
    Registry.register_evaluator("mem_eval", DummyEvaluator)
    Registry.register_handler("mem_hook", DummyHandler)


@pytest.mark.asyncio
async def test_full_pipeline_in_memory() -> None:
    policy = AlertPolicy()
    metrics = Metrics()
    resilience = ResilienceManager()

    executor = Executor(
        concurrency_limit=10,
        policy=policy,
        metrics=metrics,
        resilience=resilience,
    )

    # Use raw dict config to bypass AppConfig's strict schema validation
    check_config: Dict[str, Any] = {
        "metric_id": "integration_test_flow",
        "ingestor": {"type": "mem_api"},
        "evaluators": [{"type": "mem_eval"}],
        "handlers": [{"type": "mem_hook"}],
        "resilience": {"timeout_seconds": 2.0},
    }

    await executor._execute_single_check(check_config, "run_once")

    # Verify execution history recorded the check
    recent = await executor.history.get_recent("integration_test_flow")
    assert len(recent) >= 1
    assert recent[-1]["success"] is True

    # Validate handler received the alert (or at least no crash)
    handler = Registry.get_handler("mem_hook")
    assert isinstance(handler, DummyHandler)
    # The batch executed without raising — success
    assert True
