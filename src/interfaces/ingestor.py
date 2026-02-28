from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Dict, Any, Awaitable

from src.models.entities import MetricPayload


ConfigType = TypeVar("ConfigType", bound=Dict[str, Any])


class BaseIngestor(ABC, Generic[ConfigType]):
    """
    Inbound data acquisition contract.

    Requirements:
    - May perform I/O
    - Must not retain business state
    - Should be idempotent
    - Should raise domain-specific errors on failure
    """

    def startup(self) -> Awaitable[None]:
        async def _noop() -> None:
            return None
        return _noop()

    def shutdown(self) -> Awaitable[None]:
        async def _noop() -> None:
            return None
        return _noop()

    @abstractmethod
    def fetch(
        self,
        metric_id: str,
        config: ConfigType,
    ) -> Awaitable[MetricPayload]:
        """
        Fetches metric data and returns a strictly typed MetricPayload.
        """
        ...