from typing import Dict, Any, Optional
import datetime
from db.firebase import firebase_db
from agent_runtime.memory.base import BaseMemoryService

class LongTermMemory(BaseMemoryService):
    """
    Long-Term Memory: Persistent storage backed by Firestore.
    Stores user preferences, patterns, and historical information.
    Firestore path: users/{uid}/long_term_memory/{key}
    """
    def __init__(self) -> None:
        pass

    async def get(self, user_id: str, session_id: str, key: str) -> Optional[Any]:
        doc_ref = firebase_db.collection("users").document(user_id).collection("long_term_memory").document(key)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict().get("value")
        return None

    async def set(self, user_id: str, session_id: str, key: str, value: Any) -> None:
        doc_ref = firebase_db.collection("users").document(user_id).collection("long_term_memory").document(key)
        doc_ref.set({
            "key": key,
            "value": value,
            "updated_at": datetime.datetime.utcnow().timestamp()
        })

    async def get_all(self, user_id: str, session_id: str) -> Dict[str, Any]:
        docs = firebase_db.collection("users").document(user_id).collection("long_term_memory").stream()
        res = {}
        for doc in docs:
            data = doc.to_dict()
            res[data["key"]] = data["value"]
        return res

    async def clear(self, user_id: str, session_id: str) -> None:
        docs = firebase_db.collection("users").document(user_id).collection("long_term_memory").stream()
        for doc in docs:
            doc.reference.delete()
