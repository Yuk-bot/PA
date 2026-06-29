from typing import Dict, Any, Optional
from agent_runtime.memory.base import BaseMemoryService

class SessionMemory(BaseMemoryService):
    """
    Session Memory: Ephemeral storage scoped to the active conversation session.
    Persists across multiple agent hops during the same conversation turn.
    """
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    async def get(self, user_id: str, session_id: str, key: str) -> Optional[Any]:
        return self._store.get(session_id, {}).get(key)

    async def set(self, user_id: str, session_id: str, key: str, value: Any) -> None:
        if session_id not in self._store:
            self._store[session_id] = {}
        self._store[session_id][key] = value

    async def get_all(self, user_id: str, session_id: str) -> Dict[str, Any]:
        return self._store.get(session_id, {}).copy()

    async def clear(self, user_id: str, session_id: str) -> None:
        if session_id in self._store:
            self._store[session_id].clear()
