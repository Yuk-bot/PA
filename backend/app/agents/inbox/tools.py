"""
Tool Registrations — Inbox Intelligence Agent

Registers all IIA tools with the global ToolRegistry using the existing
@tool decorator. The agent accesses these through ToolRegistry.get_authorized_tools()
via its tool_permissions list — identical to how MockTestAgent works in tests.

Each tool is a thin wrapper over its corresponding service function so that:
  1. Services remain directly unit-testable without tool infrastructure.
  2. Tools can be discovered and permission-gated by the runtime.

These registrations execute on import (triggered by agents/inbox/__init__.py).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from agent_runtime.registry.tool import ToolRegistry

logger = logging.getLogger("agents.inbox.tools")

# ---------------------------------------------------------------------------
# Tool: Gmail email fetching
# ---------------------------------------------------------------------------

@ToolRegistry.register(
    name="gmail_fetch_emails",
    description=(
        "Fetches new or modified Gmail emails since the last sync using the user's "
        "stored Google OAuth credentials. Supports incremental sync via History API."
    ),
)
def gmail_fetch_emails(uid: str, history_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetches incremental emails for a user from Gmail.

    Args:
        uid: Firebase user ID.
        history_id: Gmail history ID from the previous sync, or None for first run.

    Returns:
        Dict with 'emails' (list of RawEmail dicts) and 'new_history_id'.
    """
    from agents.inbox.gmail_service import fetch_incremental_emails, InboxSyncState
    sync_state = InboxSyncState(history_id=history_id)
    emails, new_history_id = fetch_incremental_emails(uid, sync_state)
    return {
        "emails": [e.model_dump() for e in emails],
        "new_history_id": new_history_id,
        "count": len(emails),
    }


# ---------------------------------------------------------------------------
# Tool: Email relevance filter
# ---------------------------------------------------------------------------

@ToolRegistry.register(
    name="filter_email",
    description=(
        "Applies rule-based relevance filtering to a single email. "
        "Returns whether the email is actionable and why."
    ),
)
def filter_email(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies the rule-based email filter to a single email dict.

    Args:
        email_data: A dict representation of a RawEmail.

    Returns:
        FilterResult as a dict with 'is_relevant' and 'reason'.
    """
    from agents.inbox.schemas import RawEmail
    from agents.inbox.filter_service import filter_email as _filter
    email = RawEmail(**email_data)
    result = _filter(email)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Tool: LLM task extraction
# ---------------------------------------------------------------------------

@ToolRegistry.register(
    name="extract_task_from_email",
    description=(
        "Extracts a structured task from a filtered email using Gemini LLM. "
        "Returns the extracted task or None if the email is not actionable."
    ),
)
def extract_task_from_email(email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Calls the LLM extraction service on a single email.

    Args:
        email_data: A dict representation of a filtered RawEmail.

    Returns:
        ExtractedTask as a dict, or None if extraction failed or confidence is low.
    """
    from agents.inbox.schemas import RawEmail
    from agents.inbox.extraction_service import extract_task_from_email as _extract
    email = RawEmail(**email_data)
    result = _extract(email)
    return result.model_dump() if result else None


# ---------------------------------------------------------------------------
# Tool: Duplicate detection
# ---------------------------------------------------------------------------

@ToolRegistry.register(
    name="check_duplicate",
    description=(
        "Checks an extracted task for duplicates against existing tasks, "
        "suggested tasks, and calendar event titles using title similarity and date proximity."
    ),
)
def check_duplicate(
    extracted_task_data: Dict[str, Any],
    existing_tasks: List[Dict[str, Any]],
    existing_suggestions: List[Dict[str, Any]],
    calendar_titles: Optional[List[List[Any]]] = None,
) -> Dict[str, Any]:
    """
    Checks for duplicate tasks.

    Args:
        extracted_task_data: ExtractedTask as a dict.
        existing_tasks: List of existing task dicts.
        existing_suggestions: List of existing suggestion dicts.
        calendar_titles: Optional list of [event_title, event_date_str] pairs.

    Returns:
        DuplicateResult as a dict.
    """
    from agents.inbox.schemas import ExtractedTask
    from agents.inbox.duplicate_service import check_all_duplicates
    extracted = ExtractedTask(**extracted_task_data)
    cal_titles = [(t[0], t[1] if len(t) > 1 else None) for t in (calendar_titles or [])]
    result = check_all_duplicates(extracted, existing_tasks, existing_suggestions, cal_titles)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Tool: Calendar cross-reference
# ---------------------------------------------------------------------------

@ToolRegistry.register(
    name="check_calendar_match",
    description=(
        "Checks if an extracted task already exists in Google Calendar and "
        "detects scheduling conflicts. Does not modify Calendar."
    ),
)
def check_calendar_match(
    uid: str,
    extracted_task_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Performs calendar cross-reference for an extracted task.

    Args:
        uid: Firebase user ID.
        extracted_task_data: ExtractedTask as a dict.

    Returns:
        CalendarMatchResult as a dict.
    """
    from agents.inbox.schemas import ExtractedTask
    from agents.inbox.calendar_service import build_calendar_match_result
    extracted = ExtractedTask(**extracted_task_data)
    result = build_calendar_match_result(uid, extracted)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Tool: Store suggested task
# ---------------------------------------------------------------------------

@ToolRegistry.register(
    name="store_suggested_task",
    description=(
        "Persists a structured task suggestion to Firestore. "
        "Creates a SuggestedTask document — never an actual task."
    ),
)
def store_suggested_task(
    uid: str,
    suggestion_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Stores a SuggestedTask in Firestore.

    Args:
        uid: Firebase user ID.
        suggestion_data: SuggestedTask as a dict.

    Returns:
        Dict with 'suggestion_id' and 'success'.
    """
    from agents.inbox.schemas import SuggestedTask
    from agents.inbox.suggestion_service import store_suggestion
    suggestion = SuggestedTask(**suggestion_data)
    suggestion_id = store_suggestion(uid, suggestion)
    return {"suggestion_id": suggestion_id, "success": True}


logger.debug("IIA tools registered: gmail_fetch_emails, filter_email, extract_task_from_email, "
             "check_duplicate, check_calendar_match, store_suggested_task")
