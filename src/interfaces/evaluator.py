from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional

from src.models.entities import MetricPayload, AlertEvent


ConfigType = TypeVar("ConfigType")


class BaseEvaluator(ABC, Generic[ConfigType]):
    """
    Stateless business logic evaluator.

    Requirements:
    - Must be pure and deterministic
    - Must not mutate payload
    - Must not perform I/O
    - Must not retain internal state between calls
    """

    @abstractmethod
    def evaluate(
        self,
        payload: MetricPayload,
        config: ConfigType,
    ) -> Optional[AlertEvent]:
        """
        Returns:
            AlertEvent if anomaly detected, else None.

        Must:
            - Be idempotent
            - Have no side effects
        """
        raise NotImplementedError