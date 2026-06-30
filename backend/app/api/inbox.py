

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel

from agent_runtime.execution.engine import ExecutionEngine
from agent_runtime.schemas.models import ExecutionContext, ExecutionMetadata
from agents.inbox.schemas import IIAOutput
from agents.inbox.suggestion_service import (
    dismiss_suggestion,
    get_existing_suggestions,
)
from middleware.auth import verify_token

import datetime

logger = logging.getLogger("api.inbox")

router = APIRouter(prefix="/api/inbox", tags=["Inbox"])
_engine = ExecutionEngine()



class InboxSyncRequest(BaseModel):
   
    deep_sync: bool = False   # Bypasses the 5-minute cooldown and performs a deep sync


class InboxSyncResponse(BaseModel):
   
    success: bool
    suggestions_created: int = 0
    emails_fetched: int = 0
    emails_processed: int = 0
    emails_filtered: int = 0
    duplicates_detected: int = 0
    calendar_matches: int = 0
    suggestion_ids: List[str] = []
    warnings: List[str] = []
    error: Optional[str] = None


class SuggestionResponse(BaseModel):
   
    suggestion_id: str
    title: str
    description: Optional[str] = None
    deadline: Optional[str] = None
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    task_category: Optional[str] = None
    urgency: Optional[str] = None
    confidence: float
    source: str
    source_subject: Optional[str] = None
    source_sender_email: Optional[str] = None
    already_in_calendar: bool
    conflict_detected: bool
    status: str
    created_at: float


class SuggestionsListResponse(BaseModel):
  
    suggestions: List[SuggestionResponse]
    count: int


class DismissResponse(BaseModel):
    """Response from a dismiss action."""
    success: bool
    suggestion_id: str

@router.post("/sync", response_model=InboxSyncResponse)
async def trigger_inbox_sync(
    body: InboxSyncRequest = InboxSyncRequest(),
    user: dict = Depends(verify_token),
) -> InboxSyncResponse:
    print(f"API INBOX SYNC TRIGGERED for user: {user.get('uid')}")
    uid = user["uid"]
    session_id = f"inbox_sync_{uid}"
    execution_id = str(uuid4())

    logger.info("Inbox sync triggered for user '%s' (deep=%s)", uid, body.deep_sync)

    try:
        from agents.inbox.agent import InboxIntelligenceAgent
        agent = InboxIntelligenceAgent()

        input_data: Dict[str, Any] = {"deep_sync": body.deep_sync}

        result = await _engine.execute_agent(
            agent=agent,
            user_id=uid,
            session_id=session_id,
            input_data=input_data,
            state_data={},
            working_memory={},
            session_memory={},
            long_term_memory={},
        )

        if not result.success:
            logger.warning("Inbox sync failed for user '%s': %s", uid, result.error)
            print(f"API INBOX SYNC RESULT: FAILED - {result.error}")
            return InboxSyncResponse(
                success=False,
                error=result.error or "Sync failed.",
            )

        output_data = result.output_data
        response = InboxSyncResponse(
            success=True,
            suggestions_created=output_data.get("suggestions_created", 0),
            emails_fetched=output_data.get("emails_fetched", 0),
            emails_processed=output_data.get("emails_processed", 0),
            emails_filtered=output_data.get("emails_filtered", 0),
            duplicates_detected=output_data.get("duplicates_detected", 0),
            calendar_matches=output_data.get("calendar_matches", 0),
            suggestion_ids=output_data.get("suggested_task_ids", []),
            warnings=output_data.get("warnings", []),
        )
        print(f"API INBOX SYNC RESULT: SUCCESS - Fetched: {response.emails_fetched}, Filtered: {response.emails_filtered}, Suggestions: {response.suggestions_created}")
        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error during inbox sync for user '%s': %s", uid, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Inbox sync failed: {exc}"
        )


@router.get("/suggestions", response_model=SuggestionsListResponse)
async def list_suggestions(
    user: dict = Depends(verify_token),
) -> SuggestionsListResponse:

    uid = user["uid"]
    try:
        raw = get_existing_suggestions(uid, status_filter=["suggested"])
        suggestions = []
        for s in raw:
            try:
                suggestions.append(SuggestionResponse(
                    suggestion_id=s.get("suggestion_id", ""),
                    title=s.get("title", ""),
                    description=s.get("description"),
                    deadline=s.get("deadline"),
                    due_date=s.get("due_date"),
                    due_time=s.get("due_time"),
                    location=s.get("location"),
                    meeting_link=s.get("meeting_link"),
                    task_category=s.get("task_category"),
                    urgency=s.get("urgency"),
                    confidence=float(s.get("confidence", 0.0)),
                    source=s.get("source", "gmail"),
                    source_subject=s.get("source_subject"),
                    source_sender_email=s.get("source_sender_email"),
                    already_in_calendar=bool(s.get("already_in_calendar", False)),
                    conflict_detected=bool(s.get("conflict_detected", False)),
                    status=s.get("status", "suggested"),
                    created_at=float(s.get("created_at", 0)),
                ))
            except Exception as exc:
                logger.warning("Could not parse suggestion: %s", exc)
                continue

        return SuggestionsListResponse(suggestions=suggestions, count=len(suggestions))

    except Exception as exc:
        logger.exception("Failed to list suggestions for user '%s': %s", uid, exc)
        raise HTTPException(status_code=500, detail=f"Failed to list suggestions: {exc}")


@router.post("/suggestions/{suggestion_id}/dismiss", response_model=DismissResponse)
async def dismiss_suggestion_endpoint(
    suggestion_id: str = Path(..., description="Suggestion ID to dismiss"),
    user: dict = Depends(verify_token),
) -> DismissResponse:
   
    uid = user["uid"]
    try:
        success = dismiss_suggestion(uid, suggestion_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Suggestion '{suggestion_id}' not found or could not be dismissed."
            )
        return DismissResponse(success=True, suggestion_id=suggestion_id)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to dismiss suggestion '%s' for user '%s'", suggestion_id, uid)
        raise HTTPException(status_code=500, detail=f"Dismiss failed: {exc}")
