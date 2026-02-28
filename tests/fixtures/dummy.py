import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.interfaces.ingestor import BaseIngestor
from src.interfaces.evaluator import BaseEvaluator
from src.interfaces.handler import BaseHandler
from src.models.entities import MetricPayload, AlertEvent


class DummyIngestor(BaseIngestor[Dict[str, Any]]):
    def __init__(self) -> None:
        self.should_fail: bool = False
        self.return_value: float = 42.0
        self.delay: float = 0.0

    async def fetch(self, metric_id: str, config: Dict[str, Any]) -> MetricPayload:
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        if self.should_fail:
            raise ValueError("Simulated ingestion error")
        return MetricPayload(
            metric_id=metric_id,
            timestamp=datetime.now(timezone.utc),
            value=self.return_value,
            raw_data={},
        )


class DummyEvaluator(BaseEvaluator[Dict[str, Any]]):
    def __init__(self) -> None:
        self.should_breach: bool = False
        self.should_fail: bool = False
        self.severity: str = "high"

    def evaluate(
        self, payload: MetricPayload, config: Dict[str, Any]
    ) -> Optional[AlertEvent]:
        if self.should_fail:
            raise RuntimeError("Simulated evaluator error")

        if self.should_breach:
            return AlertEvent(
                metric_id=payload.metric_id,
                evaluator_type="dummy",
                severity="high",
                message="Simulated breach",
                timestamp=datetime.now(timezone.utc),
                context={"value": payload.value},
            )
        return None


class DummyHandler(BaseHandler[Dict[str, Any]]):
    def __init__(self) -> None:
        self.should_fail: bool = False
        self.dispatched_alerts: List[AlertEvent] = []

    async def dispatch(self, event: AlertEvent, config: Dict[str, Any]) -> None:
        if self.should_fail:
            raise ConnectionError("Simulated dispatch error")
        self.dispatched_alerts.append(event)
