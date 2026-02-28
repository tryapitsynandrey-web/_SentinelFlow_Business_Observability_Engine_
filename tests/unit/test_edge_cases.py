"""Tests for edge cases in entities, evaluators, and executor."""
import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from pydantic import ValidationError
from src.models.entities import MetricPayload
from src.core.evaluators.thresholds import ThresholdEvaluator


def test_very_large_metric_value() -> None:
    payload = MetricPayload(
        metric_id="test",
        timestamp=datetime.now(timezone.utc),
        value=1e100,
        raw_data={},
    )
    assert payload.value == 1e100


def test_missing_metric_value_defaults() -> None:
    with pytest.raises(ValidationError):
        MetricPayload()  # type: ignore[call-arg]


def test_evaluator_returning_none() -> None:
    evaluator = ThresholdEvaluator()
    payload = MetricPayload(
        metric_id="test",
        timestamp=datetime.now(timezone.utc),
        value=50.0,
        raw_data={},
    )

    # Actual signature: evaluate(payload, config)
    config: Dict[str, Any] = {"operator": ">", "value": 100, "severity": "high"}
    result = evaluator.evaluate(payload, config)
    assert result is None  # 50 is not > 100


def test_config_zero_concurrency() -> None:
    """asyncio.Semaphore(0) is valid but blocks all tasks.
    We verify Executor can be constructed — architecture doesn't reject it."""
    from src.engine.executor import Executor
    from src.core.policies import AlertPolicy
    from observability.metrics import Metrics
    from runtime.resilience import ResilienceManager

    # Semaphore(0) is valid in Python; we just verify construction works
    executor = Executor(
        concurrency_limit=0,
        policy=AlertPolicy(),
        metrics=Metrics(),
        resilience=ResilienceManager(),
    )
    assert executor is not None


def test_unexpected_exception_inside_evaluator() -> None:
    from tests.fixtures.dummy import DummyEvaluator

    evaluator = DummyEvaluator()
    evaluator.should_fail = True
    payload = MetricPayload(
        metric_id="test",
        timestamp=datetime.now(timezone.utc),
        value=1.0,
        raw_data={},
    )

    with pytest.raises(RuntimeError):
        evaluator.evaluate(payload, {})
