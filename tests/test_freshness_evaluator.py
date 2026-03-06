import pytest
from datetime import datetime, timezone, timedelta
from src.core.evaluators.freshness import FreshnessEvaluator
from src.models.entities import MetricPayload

@pytest.fixture
def evaluator():
    return FreshnessEvaluator()

def test_freshness_safe(evaluator):
    five_secs_ago = datetime.now(timezone.utc) - timedelta(seconds=5)
    payload = MetricPayload(metric_id="test", timestamp=five_secs_ago, value=1)
    config = {"max_age_seconds": 60, "severity": "high"}
    
    event = evaluator.evaluate(payload, config)
    assert event is None

def test_freshness_stale_breach(evaluator):
    two_mins_ago = datetime.now(timezone.utc) - timedelta(seconds=120)
    payload = MetricPayload(metric_id="test", timestamp=two_mins_ago, value=1)
    config = {"max_age_seconds": 60, "severity": "critical"}
    
    event = evaluator.evaluate(payload, config)
    assert event is not None
    assert event.severity == "critical"
    assert "is stale" in event.message

def test_freshness_naive_timestamp_policy(evaluator):
    # Policy: Naive timestamps are treated as UTC
    now_naive = datetime.utcnow() # Naive
    ten_mins_ago_naive = now_naive - timedelta(seconds=600)
    
    payload = MetricPayload(metric_id="test", timestamp=ten_mins_ago_naive, value=1)
    config = {"max_age_seconds": 60}
    
    event = evaluator.evaluate(payload, config)
    assert event is not None
    assert "is stale" in event.message
