from datetime import datetime, timezone
from typing import Dict, Optional, Any
from src.interfaces.evaluator import BaseEvaluator
from src.models.entities import MetricPayload, AlertEvent


class FreshnessEvaluator(BaseEvaluator[Dict[str, Any]]):
    """
    Evaluates whether a metric's timestamp is too old.
    Ensures naive timestamps are treated as UTC if naive.
    """

    def evaluate(self, payload: MetricPayload, config: Dict[str, Any]) -> Optional[AlertEvent]:
        max_age_seconds = config.get("max_age_seconds")
        severity = config.get("severity", "high")

        if not max_age_seconds:
            return None
            
        now = datetime.now(timezone.utc)
        
        # Make timestamp aware if it's naive (assume UTC)
        payload_tz = payload.timestamp
        if payload_tz.tzinfo is None:
            payload_tz = payload_tz.replace(tzinfo=timezone.utc)
            
        age_seconds = (now - payload_tz).total_seconds()

        if age_seconds > max_age_seconds:
            return AlertEvent(
                metric_id=payload.metric_id,
                evaluator_type="freshness",
                severity=severity,
                message=f"Data for {payload.metric_id} is stale. Age: {age_seconds:.1f}s (Max: {max_age_seconds}s)",
                timestamp=now,
                context={
                    "age_seconds": age_seconds,
                    "max_age_seconds": max_age_seconds,
                    "payload_timestamp": payload.timestamp.isoformat()
                }
            )

        return None
