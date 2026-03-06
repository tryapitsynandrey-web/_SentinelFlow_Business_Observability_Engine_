import pytest
from datetime import datetime, timezone
from src.core.evaluators.thresholds import ThresholdEvaluator
from src.models.entities import MetricPayload

@pytest.fixture
def evaluator():
    return ThresholdEvaluator()

def create_payload(value: float | None) -> MetricPayload:
    return MetricPayload(
        metric_id="test_metric",
        timestamp=datetime.now(timezone.utc),
        value=value
    )

def test_threshold_less_than_breach(evaluator):
    payload = create_payload(value=50)
    config = {"operator": "<", "value": 100, "severity": "medium"}
    
    event = evaluator.evaluate(payload, config)
    assert event is not None
    assert event.severity == "medium"
    assert "breached threshold" in event.message

def test_threshold_less_than_safe(evaluator):
    payload = create_payload(value=150)
    config = {"operator": "<", "value": 100}
    
    event = evaluator.evaluate(payload, config)
    assert event is None

def test_threshold_exact_boundary_safe(evaluator):
    payload = create_payload(value=100)
    config = {"operator": "<", "value": 100}
    
    event = evaluator.evaluate(payload, config)
    assert event is None

def test_threshold_between_breach(evaluator):
    payload = create_payload(value=50)
    config = {"operator": "between", "value": [40, 60]}
    
    event = evaluator.evaluate(payload, config)
    assert event is not None

def test_threshold_missing_value_policy(evaluator):
    # Policy: Missing numeric values evaluating against a threshold MUST alert
    payload = create_payload(value=None)
    config = {"operator": "<", "value": 100}
    
    event = evaluator.evaluate(payload, config)
    assert event is not None
    assert "Missing numeric value" in event.message
