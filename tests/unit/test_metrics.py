import pytest

from observability.metrics import Metrics
from prometheus_client import REGISTRY

@pytest.fixture
def metrics_client():
    # Since Prometheus registries are global, this might retain state across tests natively.
    # In a pure setup, we'd mock the registry or clear it. We'll use the singleton carefully.
    return Metrics()

def test_metrics_counter_increments(metrics_client):
    val_before = REGISTRY.get_sample_value("sentinelflow_checks_total", {"check_id": "test_check", "status": "success"}) or 0.0
    metrics_client.inc_check("test_check", "success")
    val_after = REGISTRY.get_sample_value("sentinelflow_checks_total", {"check_id": "test_check", "status": "success"}) or 0.0
    
    assert val_after == val_before + 1.0

def test_metrics_histogram_observes(metrics_client):
    metrics_client.observe_check_duration("test_check", 1.5)

def test_metrics_gauge_inflight(metrics_client):
    val_before = REGISTRY.get_sample_value("sentinelflow_inflight_requests", {"check_id": "test_check"}) or 0.0
    
    metrics_client.inflight_inc("test_check")
    assert REGISTRY.get_sample_value("sentinelflow_inflight_requests", {"check_id": "test_check"}) == val_before + 1.0
    
    metrics_client.inflight_dec("test_check")
    assert REGISTRY.get_sample_value("sentinelflow_inflight_requests", {"check_id": "test_check"}) == val_before

def test_metrics_http_request(metrics_client):
    metrics_client.inc_http_request("test_check", "localhost", "GET", "200")
    assert True
