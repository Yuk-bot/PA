"""
Calendar Cross-Reference Service — Inbox Intelligence Agent

Wraps the existing GoogleCalendarClient to provide two capabilities:
  1. Detect if an extracted task already exists in Google Calendar
  2. Detect scheduling conflicts between an extracted task and calendar events

Zero new OAuth code — reuses get_stored_credentials() and GoogleCalendarClient
exactly as used by calender/router.py.

The IIA does NOT modify Calendar. It only reads.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from agents.inbox.schemas import CalendarMatchResult, ConflictMetadata, ExtractedTask
from agents.inbox.duplicate_service import _normalise_title, _jaccard_similarity, _tokenise
from calender.calender_client import GoogleCalendarClient
from calender.oauth_handler import get_stored_credentials
from models.schemas import CalendarEvent

logger = logging.getLogger("agents.inbox.calendar_service")

# Jaccard threshold for calendar title matching (slightly looser than task dup)
CALENDAR_TITLE_THRESHOLD: float = 0.50


# ---------------------------------------------------------------------------
# Client factory — wraps existing infra
# ---------------------------------------------------------------------------

def get_calendar_client(uid: str) -> Optional[GoogleCalendarClient]:
    """
    Returns an authenticated GoogleCalendarClient for the given user.
    Returns None if credentials are unavailable or not connected.
    """
    creds = get_stored_credentials(uid)
    if not creds or not creds.connected:
        logger.info("No connected calendar credentials for user '%s'.", uid)
        return None
    try:
        return GoogleCalendarClient(creds, uid)
    except Exception as exc:
        logger.warning("Failed to build calendar client for user '%s': %s", uid, exc)
        return None


# ---------------------------------------------------------------------------
# Date parsing helpers
# ---------------------------------------------------------------------------

def _parse_task_date(extracted: ExtractedTask) -> Optional[datetime]:
    """Parses the extracted task's date from due_date or deadline fields."""
    from agents.inbox.duplicate_service import _parse_flexible_date
    return _parse_flexible_date(extracted.due_date) or _parse_flexible_date(extracted.deadline)


def _event_title_similarity(extracted_title: str, event_title: str) -> float:
    """Returns Jaccard similarity between normalised titles."""
    norm_a = _normalise_title(extracted_title)
    norm_b = _normalise_title(event_title)
    if norm_a == norm_b:
        return 1.0
    return _jaccard_similarity(_tokenise(norm_a), _tokenise(norm_b))


def _event_dates_overlap(
    event: CalendarEvent,
    task_date: Optional[datetime],
    tolerance_hours: int = 48,
) -> bool:
    """
    Returns True if the calendar event's date is within tolerance of the task date.
    """
    if task_date is None:
        return False
    try:
        event_start = event.start
        if hasattr(event_start, "tzinfo") and event_start.tzinfo is not None:
            event_start = event_start.replace(tzinfo=None)
        diff_hours = abs((event_start - task_date).total_seconds()) / 3600
        return diff_hours <= tolerance_hours
    except Exception:
        return False


def _event_time_conflicts(
    event: CalendarEvent,
    task_date: Optional[datetime],
) -> bool:
    """
    Returns True if the task's date/time falls within the event's time range.
    Used for conflict detection (different from duplicate detection).
    """
    if task_date is None or event.is_all_day:
        return False
    try:
        event_start = event.start
        event_end = event.end
        if hasattr(event_start, "tzinfo") and event_start.tzinfo is not None:
            event_start = event_start.replace(tzinfo=None)
        if hasattr(event_end, "tzinfo") and event_end.tzinfo is not None:
            event_end = event_end.replace(tzinfo=None)
        return event_start <= task_date <= event_end
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Core calendar functions
# ---------------------------------------------------------------------------

def find_matching_event(
    client: GoogleCalendarClient,
    extracted: ExtractedTask,
    days_ahead: int = 60,
) -> Tuple[bool, Optional[str]]:
    """
    Checks whether an extracted task already corresponds to a Calendar event.

    Strategy:
    - Fetch upcoming events (default 60 days to capture most deadlines).
    - For each event, compute title similarity.
    - If similarity >= threshold AND dates are within 48 hours → it's a match.

    Returns:
        (already_in_calendar, event_id_or_None)
    """
    try:
        events: List[CalendarEvent] = client.get_events(max_results=50, days_ahead=days_ahead)
    except Exception as exc:
        logger.warning("Calendar event fetch failed: %s", exc)
        return False, None

    task_date = _parse_task_date(extracted)

    for event in events:
        sim = _event_title_similarity(extracted.title, event.title)
        if sim >= CALENDAR_TITLE_THRESHOLD:
            if task_date is None or _event_dates_overlap(event, task_date):
                logger.info(
                    "Calendar match found: extracted='%s' ↔ event='%s' (sim=%.2f)",
                    extracted.title, event.title, sim
                )
                return True, event.event_id

    return False, None


def detect_conflicts(
    client: GoogleCalendarClient,
    extracted: ExtractedTask,
    days_ahead: int = 60,
) -> Optional[ConflictMetadata]:
    """
    Checks whether the extracted task's scheduled time overlaps with any
    existing calendar event. Used to populate conflict_metadata.

    The IIA DOES NOT resolve conflicts — it only reports them.

    Returns:
        ConflictMetadata if a conflict is found, None otherwise.
    """
    task_date = _parse_task_date(extracted)
    if task_date is None:
        return None  # No time info → no conflict possible

    try:
        events: List[CalendarEvent] = client.get_events(max_results=50, days_ahead=days_ahead)
    except Exception as exc:
        logger.warning("Calendar fetch for conflict detection failed: %s", exc)
        return None

    for event in events:
        if _event_time_conflicts(event, task_date):
            # Verify it's not the same event we already matched
            logger.info(
                "Conflict detected: extracted task '%s' at %s overlaps event '%s'",
                extracted.title, task_date, event.title
            )
            return ConflictMetadata(
                conflicting_event_id=event.event_id,
                conflicting_event_title=event.title,
                conflict_start=event.start.isoformat() if event.start else None,
                conflict_end=event.end.isoformat() if event.end else None,
            )

    return None


def build_calendar_match_result(
    uid: str,
    extracted: ExtractedTask,
) -> CalendarMatchResult:
    """
    Entry point for the calendar cross-reference step.
    Combines match detection + conflict detection into one result.

    Gracefully returns a default CalendarMatchResult if the calendar
    client is unavailable (e.g. user hasn't connected calendar).
    """
    client = get_calendar_client(uid)
    if not client:
        logger.info(
            "Calendar not available for user '%s' — skipping cross-reference.", uid
        )
        return CalendarMatchResult(already_in_calendar=False)

    # Check if already in calendar
    already_in_calendar, event_id = find_matching_event(client, extracted)

    conflict: Optional[ConflictMetadata] = None
    if not already_in_calendar:
        # Only check for conflicts if it's NOT already the same event
        conflict = detect_conflicts(client, extracted)

    return CalendarMatchResult(
        already_in_calendar=already_in_calendar,
        calendar_event_id=event_id,
        conflict_detected=conflict is not None,
        conflict_metadata=conflict,
    )


def get_calendar_event_titles(uid: str, days_ahead: int = 60) -> List[Tuple[str, Optional[str]]]:
    """
    Returns a list of (event_title, event_start_date_str) for all upcoming events.
    Used by the duplicate service to compare calendar event names.
    Returns empty list if calendar is unavailable.
    """
    client = get_calendar_client(uid)
    if not client:
        return []
    try:
        events = client.get_events(max_results=100, days_ahead=days_ahead)
        result = []
        for event in events:
            date_str = event.start.strftime("%Y-%m-%d") if event.start else None
            result.append((event.title, date_str))
        return result
    except Exception as exc:
        logger.warning("Could not fetch calendar titles for user '%s': %s", uid, exc)
        return []
