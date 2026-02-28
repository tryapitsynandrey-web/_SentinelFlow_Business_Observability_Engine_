from datetime import datetime, timezone
from typing import Any, Dict, Optional, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SeverityLevel = Literal["low", "medium", "high", "critical"]


class MetricPayload(BaseModel):
    """
    Immutable domain payload representing a fetched metric.
    Must contain either:
        - value (numerical metric)
        - or raw_data (structured payload)
    """

    model_config = ConfigDict(frozen=True)

    metric_id: str
    timestamp: datetime
    value: Optional[float] = None
    raw_data: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_payload(self) -> "MetricPayload":
        if self.value is None and self.raw_data is None:
            raise ValueError("MetricPayload must contain either value or raw_data.")

        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware.")

        return self


class AlertEvent(BaseModel):
    """
    Immutable domain event emitted by evaluators.
    """

    model_config = ConfigDict(frozen=True)

    metric_id: str
    evaluator_type: str
    severity: SeverityLevel
    message: str
    timestamp: datetime
    context: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_timestamp(self) -> "AlertEvent":
        if self.timestamp.tzinfo is None:
            raise ValueError("AlertEvent timestamp must be timezone-aware.")
        return self