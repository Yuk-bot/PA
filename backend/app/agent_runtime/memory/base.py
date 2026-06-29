from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import datetime
from pydantic import BaseModel, Field

class MemoryEntry(BaseModel):
    key: str
    value: Any
    updated_at: float = Field(default_factory=lambda: datetime.datetime.utcnow().timestamp())

class BaseMemoryService(ABC):
    """
    Interface for structured three-layer memory storage.
    """
    @abstractmethod
    async def get(self, user_id: str, session_id: str, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, user_id: str, session_id: str, key: str, value: Any) -> None:
        pass

    @abstractmethod
    async def get_all(self, user_id: str, session_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def clear(self, user_id: str, session_id: str) -> None:
        pass
