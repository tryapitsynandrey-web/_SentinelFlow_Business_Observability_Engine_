from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Dict, Any, Awaitable

from src.models.entities import AlertEvent


ConfigType = TypeVar("ConfigType", bound=Dict[str, Any])


class BaseHandler(ABC, Generic[ConfigType]):
    """
    Outbound integration contract.

    Requirements:
    - May perform I/O
    - Must not mutate AlertEvent
    - Should be idempotent if possible
    - Should raise DispatchError on failure
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
    def dispatch(
        self,
        event: AlertEvent,
        config: ConfigType,
    ) -> Awaitable[None]:
        """
        Dispatches an event to an external system.
        """
        ...