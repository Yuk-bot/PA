"""
Suggestion Storage Service — Inbox Intelligence Agent

Handles Firestore CRUD for suggested tasks.
Firestore path: users/{uid}/suggested_tasks/{suggestion_id}

The IIA ONLY creates SuggestedTask documents.
It NEVER creates documents in the top-level 'tasks' collection.
Actual task creation belongs to downstream agents.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.inbox.schemas import SuggestedTask
from db.firebase import firebase_db

logger = logging.getLogger("agents.inbox.suggestion_service")

# Firestore collection name for suggested tasks (scoped under user document)
SUGGESTIONS_COLLECTION = "suggested_tasks"


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def store_suggestion(uid: str, suggestion: SuggestedTask) -> str:
    """
    Persists a SuggestedTask to Firestore.

    Returns:
        The suggestion_id of the stored document.
    Raises:
        Exception: If Firestore write fails (caller should handle gracefully).
    """
    doc_ref = (
        firebase_db.collection("users")
        .document(uid)
        .collection(SUGGESTIONS_COLLECTION)
        .document(suggestion.suggestion_id)
    )
    data = suggestion.model_dump()
    data["updated_at"] = datetime.utcnow().timestamp()
    doc_ref.set(data)
    logger.info(
        "Suggestion '%s' stored for user '%s': title='%s'",
        suggestion.suggestion_id, uid, suggestion.title
    )
    return suggestion.suggestion_id


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def get_existing_suggestions(
    uid: str,
    status_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Returns all suggestion documents for a user.

    Args:
        uid: Firebase user ID.
        status_filter: If provided, only return suggestions with these statuses.
                       Defaults to ["suggested"] (active, not dismissed/accepted).

    Returns:
        List of suggestion dicts.
    """
    if status_filter is None:
        status_filter = ["suggested"]

    try:
        query = (
            firebase_db.collection("users")
            .document(uid)
            .collection(SUGGESTIONS_COLLECTION)
        )
        # Apply status filter
        for status in status_filter:
            # Firestore does not support OR natively; fetch all and filter in Python
            pass

        docs = query.stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            if status_filter and data.get("status") not in status_filter:
                continue
            results.append(data)
        logger.debug(
            "Retrieved %d suggestion(s) for user '%s'.", len(results), uid
        )
        return results

    except Exception as exc:
        logger.warning("Failed to retrieve suggestions for user '%s': %s", uid, exc)
        return []


def get_suggestion_by_id(uid: str, suggestion_id: str) -> Optional[Dict[str, Any]]:
    """Returns a single suggestion by ID."""
    try:
        doc = (
            firebase_db.collection("users")
            .document(uid)
            .collection(SUGGESTIONS_COLLECTION)
            .document(suggestion_id)
            .get()
        )
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as exc:
        logger.warning(
            "Failed to retrieve suggestion '%s' for user '%s': %s", suggestion_id, uid, exc
        )
        return None


# ---------------------------------------------------------------------------
# Lifecycle updates
# ---------------------------------------------------------------------------

def mark_suggestion_status(uid: str, suggestion_id: str, status: str) -> bool:
    """
    Updates the status of a suggestion (e.g. 'dismissed', 'accepted', 'expired').
    Returns True on success, False on failure.
    """
    try:
        (
            firebase_db.collection("users")
            .document(uid)
            .collection(SUGGESTIONS_COLLECTION)
            .document(suggestion_id)
            .update({
                "status": status,
                "updated_at": datetime.utcnow().timestamp(),
            })
        )
        logger.info(
            "Suggestion '%s' status updated to '%s' for user '%s'.",
            suggestion_id, status, uid
        )
        return True
    except Exception as exc:
        logger.warning(
            "Failed to update suggestion '%s' status: %s", suggestion_id, exc
        )
        return False


def dismiss_suggestion(uid: str, suggestion_id: str) -> bool:
    """Marks a suggestion as dismissed. Convenience wrapper."""
    return mark_suggestion_status(uid, suggestion_id, "dismissed")


# ---------------------------------------------------------------------------
# Existing task fetching (for duplicate detection)
# ---------------------------------------------------------------------------

def get_existing_user_tasks(uid: str, limit: int = 200) -> List[Dict[str, Any]]:
    """
    Fetches user's actual tasks from the top-level 'tasks' collection.
    Used by the duplicate detection service to avoid re-suggesting tasks
    that already exist as real tasks.
    """
    try:
        docs = (
            firebase_db.collection("tasks")
            .where("uid", "==", uid)
            .limit(limit)
            .stream()
        )
        results = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            results.append(data)
        return results
    except Exception as exc:
        logger.warning("Failed to fetch tasks for duplicate check (user '%s'): %s", uid, exc)
        return []
