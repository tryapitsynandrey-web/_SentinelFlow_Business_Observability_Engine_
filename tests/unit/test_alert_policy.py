"""Tests for AlertPolicy deduplication and cooldown logic."""
import pytest
from datetime import datetime, timedelta, timezone

from src.core.policies import AlertPolicy
from src.models.entities import AlertEvent


@pytest.fixture
def alert_policy() -> AlertPolicy:
    return AlertPolicy()


@pytest.fixture
def sample_alert() -> AlertEvent:
    return AlertEvent(
        metric_id="test_metric",
        severity="high",
        message="Testing",
        evaluator_type="test",
        timestamp=datetime.now(timezone.utc),
        context={"value": 10.0},
    )


def test_alert_policy_first_dispatch(
    alert_policy: AlertPolicy, sample_alert: AlertEvent
) -> None:
    result = alert_policy.should_dispatch(
        sample_alert.metric_id,
        sample_alert.evaluator_type,
        sample_alert.severity,
        3600,
        300,
        event=sample_alert,
    )
    assert result is True


def test_alert_policy_cooldown_suppression(
    alert_policy: AlertPolicy, sample_alert: AlertEvent
) -> None:
    # First dispatch allowed
    assert (
        alert_policy.should_dispatch(
            sample_alert.metric_id,
            sample_alert.evaluator_type,
            sample_alert.severity,
            3600,
            300,
            event=sample_alert,
        )
        is True
    )

    # Immediate subsequent dispatch suppressed (within dedupe window)
    assert (
        alert_policy.should_dispatch(
            sample_alert.metric_id,
            sample_alert.evaluator_type,
            sample_alert.severity,
            3600,
            300,
            event=sample_alert,
        )
        is False
    )


def test_alert_policy_different_severity(
    alert_policy: AlertPolicy, sample_alert: AlertEvent
) -> None:
    alert_policy.should_dispatch(
        sample_alert.metric_id,
        sample_alert.evaluator_type,
        sample_alert.severity,
        3600,
        300,
        event=sample_alert,
    )

    # Same metric, different severity -> should dispatch
    new_alert = AlertEvent(
        metric_id="test_metric",
        severity="critical",
        message="Testing escalation",
        evaluator_type="test",
        timestamp=datetime.now(timezone.utc),
        context={"value": 15.0},
    )
    assert (
        alert_policy.should_dispatch(
            new_alert.metric_id,
            new_alert.evaluator_type,
            new_alert.severity,
            3600,
            300,
            event=new_alert,
        )
        is True
    )


def test_alert_policy_purge_old_state(alert_policy: AlertPolicy) -> None:
    alert = AlertEvent(
        metric_id="test_metric",
        severity="high",
        message="Testing",
        evaluator_type="test",
        timestamp=datetime.now(timezone.utc),
    )
    alert_policy.should_dispatch(
        alert.metric_id,
        alert.evaluator_type,
        alert.severity,
        3600,
        300,
        event=alert,
    )

    fp = "test_metric:test:high"
    assert fp in alert_policy._last_dispatched

    # purge_old_state uses max_age_seconds (not max_age_hours)
    alert_policy.purge_old_state(max_age_seconds=0)
    assert fp not in alert_policy._last_dispatched
