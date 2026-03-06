import time
from src.core.policies import AlertPolicy

def test_alert_policy_first_seen_dispatches():
    policy = AlertPolicy()
    
    should_dispatch = policy.should_dispatch(
        metric_id="api_status",
        evaluator_type="threshold",
        severity="high",
        cooldown_seconds=300,
        dedupe_window_seconds=3600
    )
    
    assert should_dispatch is True

def test_alert_policy_dedupe_blocks_subsequent():
    policy = AlertPolicy()
    
    # First should pass
    policy.should_dispatch("reqs", "threshold", "high", 300, 3600)
    
    # Second identical should be blocked by dedupe window
    should_dispatch = policy.should_dispatch("reqs", "threshold", "high", 300, 3600)
    
    assert should_dispatch is False

def test_alert_policy_different_severity_bypasses_dedupe():
    policy = AlertPolicy()
    
    policy.should_dispatch("reqs", "threshold", "high", 300, 3600)
    
    # Different severity creates a different fingerprint
    should_dispatch = policy.should_dispatch("reqs", "threshold", "critical", 300, 3600)
    
    assert should_dispatch is True

def test_purge_old_state():
    policy = AlertPolicy()
    policy.should_dispatch("old_reqs", "threshold", "high", 300, 3600)
    
    # Pretend it's 2 days old by purging anything older than 1 second, then waiting 1 sec
    time.sleep(1.1)
    policy.purge_old_state(max_age_seconds=1)
    
    # The fingerprint should be removed from memory
    assert len(policy._last_seen) == 0
    assert len(policy._last_dispatched) == 0
