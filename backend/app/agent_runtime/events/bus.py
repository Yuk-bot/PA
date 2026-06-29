import asyncio
from typing import Dict, List, Callable, Awaitable
from agent_runtime.schemas.models import Event
from agent_runtime.events.interface import BaseEventBus

class InMemoryEventBus(BaseEventBus):
    """
    In-memory event bus implementation for immediate, sequential or asynchronous
    agent-trigger event propagation.
    """
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Event], Awaitable[None]]]] = {}

    async def publish(self, event: Event) -> None:
        """
        Publishes an event to all subscribers registered for the event_name.
        Invokes all subscribers asynchronously.
        """
        handlers = self._subscribers.get(event.event_name, [])
        if not handlers:
            return
        
        # Invoke all handlers concurrently
        tasks = [handler(event) for handler in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def subscribe(self, event_name: str, callback: Callable[[Event], Awaitable[None]]) -> None:
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        if callback not in self._subscribers[event_name]:
            self._subscribers[event_name].append(callback)

    async def unsubscribe(self, event_name: str, callback: Callable[[Event], Awaitable[None]]) -> None:
        if event_name in self._subscribers and callback in self._subscribers[event_name]:
            self._subscribers[event_name].remove(callback)
            if not self._subscribers[event_name]:
                del self._subscribers[event_name]
