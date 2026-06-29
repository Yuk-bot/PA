import abc
from typing import Callable, Awaitable
from agent_runtime.schemas.models import Event

class BaseEventBus(abc.ABC):
    """
    Abstract Event Bus. Can be extended to support Pub/Sub, Firestore,
    or other messaging queues.
    """
    @abc.abstractmethod
    async def publish(self, event: Event) -> None:
        pass

    @abc.abstractmethod
    async def subscribe(self, event_name: str, callback: Callable[[Event], Awaitable[None]]) -> None:
        pass

    @abc.abstractmethod
    async def unsubscribe(self, event_name: str, callback: Callable[[Event], Awaitable[None]]) -> None:
        pass
