from typing import Dict, Any, Optional
import datetime
from pydantic import BaseModel

from db.firebase import firebase_db

class StateManager:
    """
    Manages shared execution state, enforcing permission restrictions on mutations.
    Prevents uncontrolled mutations by ensuring only agents with "w" or "rw"
    permissions on specific keys can update them.
    """
    def __init__(self, session_id: str, state_data: Dict[str, Any]) -> None:
        self.session_id = session_id
        self._state_data = state_data.copy()

    @staticmethod
    async def load_from_db(user_id: str, session_id: str) -> "StateManager":
        doc_ref = (
            firebase_db.collection("users")
            .document(user_id)
            .collection("sessions")
            .document(session_id)
            .collection("state")
            .document("current")
        )
        doc = doc_ref.get()
        state_data = doc.to_dict().get("state_data", {}) if doc.exists else {}
        return StateManager(session_id, state_data)

    async def save_to_db(self, user_id: str) -> None:
        doc_ref = (
            firebase_db.collection("users")
            .document(user_id)
            .collection("sessions")
            .document(self.session_id)
            .collection("state")
            .document("current")
        )
        doc_ref.set({
            "session_id": self.session_id,
            "state_data": self._state_data,
            "updated_at": datetime.datetime.utcnow().timestamp()
        })

    def get(self, key: str, agent_permissions: Dict[str, str]) -> Any:
        """
        Retrieves a state key if the agent has read permission.
        """
        # Checks permission: default read-only if not specified, or checks keys
        if not self._check_permission(key, agent_permissions, "r"):
            raise PermissionError(f"Agent unauthorized to read state key: '{key}'")
        return self._state_data.get(key)

    def set(self, key: str, value: Any, agent_permissions: Dict[str, str]) -> None:
        """
        Sets a state key if the agent has write permission.
        """
        if not self._check_permission(key, agent_permissions, "w"):
            raise PermissionError(f"Agent unauthorized to write/mutate state key: '{key}'")
        self._state_data[key] = value

    def to_dict(self) -> Dict[str, Any]:
        return self._state_data.copy()

    def _check_permission(self, key: str, permissions: Dict[str, str], access_type: str) -> bool:
        """
        Validates if key access conforms to agent permissions.
        permissions dict format: e.g. {"*": "rw"} or {"current_task": "rw", "priorities": "r"}
        """
        if "*" in permissions:
            allowed_access = permissions["*"]
        else:
            allowed_access = permissions.get(key, "r" if access_type == "r" else "")
        
        return access_type in allowed_access
