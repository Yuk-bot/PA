from typing import Dict, Any, Optional
import datetime
from pydantic import BaseModel, Field
from db.firebase import firebase_db

class Checkpoint(BaseModel):
    checkpoint_id: str
    session_id: str
    user_id: str
    step_name: str
    state_data: Dict[str, Any] = Field(default_factory=dict)
    working_memory: Dict[str, Any] = Field(default_factory=dict)
    session_memory: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=lambda: datetime.datetime.utcnow().timestamp())

class CheckpointManager:
    """
    Checkpoint Manager enables state checkpoints to persist at each step
    of workflow execution, permitting pipeline recovery in case of system failures.
    Firestore collection: users/{uid}/sessions/{session_id}/checkpoints/{step_name}
    """
    def __init__(self) -> None:
        pass

    def _get_collection(self, user_id: str, session_id: str):
        return (
            firebase_db.collection("users")
            .document(user_id)
            .collection("sessions")
            .document(session_id)
            .collection("checkpoints")
        )

    async def save_checkpoint(
        self,
        user_id: str,
        session_id: str,
        step_name: str,
        state_data: Dict[str, Any],
        working_memory: Dict[str, Any],
        session_memory: Dict[str, Any]
    ) -> Checkpoint:
        cid = f"{session_id}_{step_name}"
        checkpoint = Checkpoint(
            checkpoint_id=cid,
            session_id=session_id,
            user_id=user_id,
            step_name=step_name,
            state_data=state_data,
            working_memory=working_memory,
            session_memory=session_memory
        )
        
        doc_ref = self._get_collection(user_id, session_id).document(step_name)
        doc_ref.set(checkpoint.model_dump())
        return checkpoint

    async def load_checkpoint(self, user_id: str, session_id: str, step_name: str) -> Optional[Checkpoint]:
        doc_ref = self._get_collection(user_id, session_id).document(step_name)
        doc = doc_ref.get()
        if doc.exists:
            return Checkpoint.model_validate(doc.to_dict())
        return None

    async def get_latest_checkpoint(self, user_id: str, session_id: str) -> Optional[Checkpoint]:
        docs = (
            self._get_collection(user_id, session_id)
            .order_by("timestamp", direction="DESCENDING")
            .limit(1)
            .stream()
        )
        for doc in docs:
            return Checkpoint.model_validate(doc.to_dict())
        return None

    async def clear_checkpoints(self, user_id: str, session_id: str) -> None:
        docs = self._get_collection(user_id, session_id).stream()
        for doc in docs:
            doc.reference.delete()
