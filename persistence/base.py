from abc import ABC, abstractmethod
from typing import Optional

class BaseStateStore(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        pass

    @abstractmethod
    async def set(self, key: str, value: str) -> None:
        pass
