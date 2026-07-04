from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import logging

from agents.planning.schemas import FreeSlotItem
from calender.calender_client import GoogleCalendarClient
from calender.oauth_handler import get_stored_credentials

logger = logging.getLogger("agents.planning.free_slot_service")

MIN_SLOT_MINUTES = 15


def _parse_hhmm(time_str: str) -> Tuple[int, int]:
    parts = time_str.strip().split(":")
    return int(parts[0]), int(parts[1])


def _parse_productive_ranges(raw: List[str]) -> List[Tuple[int, int, int, int]]:
    result = []
    for entry in raw:
        try:
            start_s, end_s = entry.split("-")
            sh, sm = _parse_hhmm(start_s)
            eh, em = _parse_hhmm(end_s)
            result.append((sh, sm, eh, em))
        except Exception:
            continue
    return result


def _is_productive(dt: datetime, ranges: List[Tuple[int, int, int, int]]) -> bool:
    for sh, sm, eh, em in ranges:
        slot_start = dt.replace(hour=sh, minute=sm, second=0, microsecond=0)
        slot_end = dt.replace(hour=eh, minute=em, second=0, microsecond=0)
        if slot_start <= dt < slot_end:
            return True
    return False


def _build_default_slots(
    working_hours_start: str,
    working_hours_end: str,
    productive_ranges: List[Tuple[int, int, int, int]],
    days_ahead: int,
) -> List[FreeSlotItem]:
    sh, sm = _parse_hhmm(working_hours_start)
    eh, em = _parse_hhmm(working_hours_end)
    slots = []
    today = datetime.now().replace(second=0, microsecond=0)

    for offset in range(days_ahead):
        day = today.date() + timedelta(days=offset)
        work_start = datetime.combine(day, datetime.min.time()).replace(hour=sh, minute=sm)
        work_end = datetime.combine(day, datetime.min.time()).replace(hour=eh, minute=em)

        if offset == 0:
            work_start = max(work_start, today)

        if work_start >= work_end:
            continue

        duration = int((work_end - work_start).total_seconds() / 60)
        if duration >= MIN_SLOT_MINUTES:
            slots.append(FreeSlotItem(
                start=work_start,
                end=work_end,
                duration_minutes=duration,
                date_str=day.isoformat(),
                is_productive=_is_productive(work_start, productive_ranges),
            ))
    return slots


def get_multi_day_free_slots(
    uid: str,
    working_hours_start: str,
    working_hours_end: str,
    productive_hours_raw: List[str],
    days_ahead: int = 14,
) -> List[FreeSlotItem]:
    sh, sm = _parse_hhmm(working_hours_start)
    eh, em = _parse_hhmm(working_hours_end)
    productive_ranges = _parse_productive_ranges(productive_hours_raw)

    creds = get_stored_credentials(uid)
    if not creds or not creds.connected:
        logger.warning("No calendar credentials — falling back to working-hours slots")
        return _build_default_slots(working_hours_start, working_hours_end, productive_ranges, days_ahead)

    try:
        client = GoogleCalendarClient(creds, uid)
        events = client.get_events(max_results=200, days_ahead=days_ahead)
    except Exception as exc:
        logger.error(f"Calendar fetch failed: {exc}")
        return _build_default_slots(working_hours_start, working_hours_end, productive_ranges, days_ahead)

    today = datetime.now().replace(second=0, microsecond=0)
    free_slots: List[FreeSlotItem] = []

    for offset in range(days_ahead):
        day = today.date() + timedelta(days=offset)
        work_start = datetime.combine(day, datetime.min.time()).replace(hour=sh, minute=sm)
        work_end = datetime.combine(day, datetime.min.time()).replace(hour=eh, minute=em)

        if offset == 0:
            work_start = max(work_start, today)
        if work_start >= work_end:
            continue

        day_events = []
        for e in events:
            if e.is_all_day:
                continue
            es = e.start.replace(tzinfo=None) if e.start.tzinfo else e.start
            ee = e.end.replace(tzinfo=None) if e.end.tzinfo else e.end
            if es.date() <= day <= ee.date():
                es = max(es, work_start)
                ee = min(ee, work_end)
                if es < ee:
                    day_events.append((es, ee))

        day_events.sort(key=lambda x: x[0])

        current = work_start
        for ev_start, ev_end in day_events:
            if ev_start > current:
                gap = int((ev_start - current).total_seconds() / 60)
                if gap >= MIN_SLOT_MINUTES:
                    free_slots.append(FreeSlotItem(
                        start=current,
                        end=ev_start,
                        duration_minutes=gap,
                        date_str=day.isoformat(),
                        is_productive=_is_productive(current, productive_ranges),
                    ))
            current = max(current, ev_end)

        if current < work_end:
            gap = int((work_end - current).total_seconds() / 60)
            if gap >= MIN_SLOT_MINUTES:
                free_slots.append(FreeSlotItem(
                    start=current,
                    end=work_end,
                    duration_minutes=gap,
                    date_str=day.isoformat(),
                    is_productive=_is_productive(current, productive_ranges),
                ))

    return free_slots
