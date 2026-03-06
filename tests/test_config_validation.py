import pytest
from pydantic import ValidationError
from src.config.parser import AppConfig

def test_valid_minimal_config():
    data = {
        "global": {
            "concurrency_limit": 5,
            "default_timeout_seconds": 10.0,
            "scheduler_mode": "run_once",
            "interval_seconds": 60
        },
        "checks": [
            {
                "metric_id": "test_metric",
                "ingestor": {
                    "type": "http_api",
                    "url": "http://example.com"
                },
                "evaluators": [
                    {
                        "type": "threshold",
                        "operator": ">",
                        "value": 100
                    }
                ],
                "alert_policy": {
                    "cooldown_seconds": 0,
                    "dedupe_window_seconds": 0,
                    "severity": "high"
                },
                "handlers": [
                    {
                        "type": "slack_webhook",
                        "webhook_url_env_key": "TEST_KEY"
                    }
                ]
            }
        ]
    }
    
    config = AppConfig(**data)
    assert config.global_config.concurrency_limit == 5
    assert len(config.checks) == 1
    assert config.checks[0].ingestor.type == "http_api"

def test_config_missing_required_fields():
    data = {"global": {}}
    with pytest.raises(ValidationError) as exc_info:
        AppConfig(**data)
    assert "checks" in str(exc_info.value)

def test_config_invalid_enum():
    data = {
        "checks": [
            {
                "metric_id": "test",
                "ingestor": {"type": "invalid_type", "url": "http://x.com"},
                "evaluators": [{"type": "threshold", "operator": ">", "value": 1}],
                "handlers": [{"type": "slack_webhook", "webhook_url_env_key": "X"}]
            }
        ]
    }
    with pytest.raises(ValidationError) as exc_info:
         AppConfig(**data)
    assert "Input should be 'http_api'" in str(exc_info.value)

def test_threshold_evaluator_invalid_operator():
     data = {
         "checks": [
             {
                 "metric_id": "t",
                 "ingestor": {"type": "http_api", "url": "http://x"},
                 "evaluators": [{"type": "threshold", "operator": "INVALID", "value": 1}],
                 "handlers": [{"type": "slack_webhook", "webhook_url_env_key": "X"}]
             }
         ]
     }
     with pytest.raises(ValidationError):
          AppConfig(**data)
