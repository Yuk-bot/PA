"""
Event constants and factory helpers — Inbox Intelligence Agent

All event names used by the IIA are defined here as string constants.
Factory functions produce runtime Event objects (agent_runtime.schemas.models.Event)
that are published via the InMemoryEventBus.

Consumers (downstream agents or monitoring) subscribe to these event names.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional
from uuid import uuid4

from agent_runtime.schemas.models import Event

# ---------------------------------------------------------------------------
# Event name constants
# ---------------------------------------------------------------------------

INBOX_SYNC_STARTED = "InboxSyncStarted"
INBOX_SYNC_COMPLETED = "InboxSyncCompleted"
EMAIL_FILTERED = "EmailFiltered"
TASK_EXTRACTED = "TaskExtracted"
TASK_REJECTED = "TaskRejected"
DUPLICATE_DETECTED = "DuplicateDetected"
CALENDAR_MATCH_DETECTED = "CalendarMatchDetected"
SUGGESTIONS_CREATED = "SuggestionsCreated"
EVALUATION_FAILED = "EvaluationFailed"
EXECUTION_COMPLETED = "ExecutionCompleted"

# All event names emitted by the IIA (for subscription filtering)
IIA_EVENT_NAMES = frozenset([
    INBOX_SYNC_STARTED,
    INBOX_SYNC_COMPLETED,
    EMAIL_FILTERED,
    TASK_EXTRACTED,
    TASK_REJECTED,
    DUPLICATE_DETECTED,
    CALENDAR_MATCH_DETECTED,
    SUGGESTIONS_CREATED,
    EVALUATION_FAILED,
    EXECUTION_COMPLETED,
])


# ---------------------------------------------------------------------------
# Internal factory helper
# ---------------------------------------------------------------------------

def _make_event(
    event_name: str,
    payload: Dict[str, Any],
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Event:
    return Event(
        event_id=str(uuid4()),
        event_name=event_name,
        payload=payload,
        timestamp=time.time(),
        user_id=user_id,
        session_id=session_id,
        version="v1",
    )


# ---------------------------------------------------------------------------
# Event factories
# ---------------------------------------------------------------------------

def make_inbox_sync_started_event(
    uid: str,
    session_id: str,
    history_id: Optional[str] = None,
) -> Event:
    return _make_event(
        INBOX_SYNC_STARTED,
        payload={"user_id": uid, "history_id": history_id},
        user_id=uid,
        session_id=session_id,
    )


def make_inbox_sync_completed_event(
    uid: str,
    session_id: str,
    emails_fetched: int,
    new_history_id: Optional[str] = None,
) -> Event:
    return _make_event(
        INBOX_SYNC_COMPLETED,
        payload={
            "user_id": uid,
            "emails_fetched": emails_fetched,
            "new_history_id": new_history_id,
        },
        user_id=uid,
        session_id=session_id,
    )


def make_email_filtered_event(
    uid: str,
    session_id: str,
    message_id: str,
    reason: str,
) -> Event:
    return _make_event(
        EMAIL_FILTERED,
        payload={"user_id": uid, "message_id": message_id, "reason": reason},
        user_id=uid,
        session_id=session_id,
    )


def make_task_extracted_event(
    uid: str,
    session_id: str,
    suggestion_id: str,
    title: str,
    confidence: float,
    source_message_id: str,
) -> Event:
    return _make_event(
        TASK_EXTRACTED,
        payload={
            "user_id": uid,
            "suggestion_id": suggestion_id,
            "title": title,
            "confidence": confidence,
            "source_message_id": source_message_id,
        },
        user_id=uid,
        session_id=session_id,
    )


def make_task_rejected_event(
    uid: str,
    session_id: str,
    message_id: str,
    confidence: float,
    threshold: float,
) -> Event:
    return _make_event(
        TASK_REJECTED,
        payload={
            "user_id": uid,
            "message_id": message_id,
            "confidence": confidence,
            "threshold": threshold,
            "reason": f"Confidence {confidence:.2f} below threshold {threshold:.2f}",
        },
        user_id=uid,
        session_id=session_id,
    )


def make_duplicate_detected_event(
    uid: str,
    session_id: str,
    extracted_title: str,
    matched_title: Optional[str],
    matched_id: Optional[str],
    similarity_score: float,
) -> Event:
    return _make_event(
        DUPLICATE_DETECTED,
        payload={
            "user_id": uid,
            "extracted_title": extracted_title,
            "matched_title": matched_title,
            "matched_id": matched_id,
            "similarity_score": similarity_score,
        },
        user_id=uid,
        session_id=session_id,
    )


def make_calendar_match_detected_event(
    uid: str,
    session_id: str,
    title: str,
    calendar_event_id: Optional[str],
    conflict_detected: bool,
) -> Event:
    return _make_event(
        CALENDAR_MATCH_DETECTED,
        payload={
            "user_id": uid,
            "title": title,
            "calendar_event_id": calendar_event_id,
            "conflict_detected": conflict_detected,
        },
        user_id=uid,
        session_id=session_id,
    )


def make_suggestions_created_event(
    uid: str,
    session_id: str,
    count: int,
    suggestion_ids: list,
) -> Event:
    return _make_event(
        SUGGESTIONS_CREATED,
        payload={
            "user_id": uid,
            "count": count,
            "suggestion_ids": suggestion_ids,
        },
        user_id=uid,
        session_id=session_id,
    )


def make_evaluation_failed_event(
    uid: str,
    session_id: str,
    reason: str,
    retry_count: int,
) -> Event:
    return _make_event(
        EVALUATION_FAILED,
        payload={
            "user_id": uid,
            "reason": reason,
            "retry_count": retry_count,
        },
        user_id=uid,
        session_id=session_id,
    )


def make_execution_completed_event(
    uid: str,
    session_id: str,
    suggestions_created: int,
    latency_ms: float,
) -> Event:
    return _make_event(
        EXECUTION_COMPLETED,
        payload={
            "user_id": uid,
            "suggestions_created": suggestions_created,
            "latency_ms": latency_ms,
        },
        user_id=uid,
        session_id=session_id,
    )
