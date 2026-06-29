from typing import Dict, Any, List, Optional
import datetime
from uuid import uuid4
from pydantic import BaseModel, Field

from db.firebase import firebase_db
from agent_runtime.config import settings

class SessionData(BaseModel):
    id: str
    app_name: str
    user_id: str
    current_workflow: Optional[str] = None
    active_execution: Optional[str] = None
    execution_history: List[Dict[str, Any]] = Field(default_factory=list)
    temporary_context: Dict[str, Any] = Field(default_factory=dict)
    updated_at: float = Field(default_factory=lambda: datetime.datetime.utcnow().timestamp())

class SessionManager:
    """
    Manages session metadata and lifecycle.
    Persists data to Firestore under users/{uid}/sessions/{session_id}
    """
    def __init__(self) -> None:
        pass

    def _get_collection(self, user_id: str):
        return firebase_db.collection("users").document(user_id).collection("sessions")

    async def create_session(
        self,
        app_name: str,
        user_id: str,
        session_id: Optional[str] = None,
        current_workflow: Optional[str] = None
    ) -> SessionData:
        sid = session_id or str(uuid4())
        session = SessionData(
            id=sid,
            app_name=app_name,
            user_id=user_id,
            current_workflow=current_workflow
        )
        await self.save_session(session)
        return session

    async def get_session(self, user_id: str, session_id: str) -> Optional[SessionData]:
        doc_ref = self._get_collection(user_id).document(session_id)
        doc = doc_ref.get()
        if doc.exists:
            return SessionData.model_validate(doc.to_dict())
        return None

    async def save_session(self, session: SessionData) -> None:
        session.updated_at = datetime.datetime.utcnow().timestamp()
        doc_ref = self._get_collection(session.user_id).document(session.id)
        doc_ref.set(session.model_dump())

    async def list_sessions(self, user_id: str) -> List[SessionData]:
        docs = self._get_collection(user_id).stream()
        sessions = []
        for doc in docs:
            sessions.append(SessionData.model_validate(doc.to_dict()))
        return sessions

    async def delete_session(self, user_id: str, session_id: str) -> None:
        self._get_collection(user_id).document(session_id).delete()
