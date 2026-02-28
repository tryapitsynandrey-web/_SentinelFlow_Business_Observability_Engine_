from datetime import datetime, timezone
from typing import Dict, Optional, Any
from src.interfaces.evaluator import BaseEvaluator
from src.models.entities import MetricPayload, AlertEvent


class ThresholdEvaluator(BaseEvaluator[Dict[str, Any]]):
    """
    Evaluates whether a numeric metric breaches a defined threshold.
    """

    def evaluate(self, payload: MetricPayload, config: Dict[str, Any]) -> Optional[AlertEvent]:
        # Handle explicitly missing data against a threshold rule
        if payload.value is None:
            return AlertEvent(
                metric_id=payload.metric_id,
                evaluator_type="threshold",
                severity=config.get("severity", "high"),
                message="Missing numeric value to evaluate threshold.",
                timestamp=datetime.now(timezone.utc),
                context={"operator": config.get("operator"), "expected": config.get("value")}
            )

        operator = config.get("operator")
        raw_val = config.get("value")
        severity = config.get("severity", "high")

        # Explicitly validate that we indeed got a float, int, or a list of them
        # Pydantic handles this at config load, but mypy doesn't know here.
        threshold_val: float | list[float] | None = None
        
        if isinstance(raw_val, (int, float)):
            threshold_val = float(raw_val)
        elif isinstance(raw_val, list) and len(raw_val) == 2:
            threshold_val = [float(raw_val[0]), float(raw_val[1])]
        elif isinstance(raw_val, str):
            try:
                threshold_val = float(raw_val)
            except ValueError:
                pass
                
        if threshold_val is None:
             return None # Pydantic guards this, but for type-checker safety

        is_breach = False

        if operator == "<" and isinstance(threshold_val, float):
            is_breach = payload.value < threshold_val
        elif operator == "<=" and isinstance(threshold_val, float):
            is_breach = payload.value <= threshold_val
        elif operator == ">" and isinstance(threshold_val, float):
            is_breach = payload.value > threshold_val
        elif operator == ">=" and isinstance(threshold_val, float):
            is_breach = payload.value >= threshold_val
        elif operator == "between" and isinstance(threshold_val, list):
            lower, upper = threshold_val
            is_breach = lower <= payload.value <= upper

        if is_breach:
            return AlertEvent(
                metric_id=payload.metric_id,
                evaluator_type="threshold",
                severity=severity,
                message=f"Metric {payload.metric_id} value '{payload.value}' breached threshold '{operator} {threshold_val}'",
                timestamp=datetime.now(timezone.utc),
                context={
                    "value": payload.value,
                    "operator": operator,
                    "threshold_val": threshold_val
                }
            )

        return None
