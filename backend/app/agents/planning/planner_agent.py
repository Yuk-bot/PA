from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4
import logging

from agents.planning.schemas import (
    FreeSlotItem,
    GlobalPlan,
    PlanSummary,
    SubtaskSchema,
    TaskPlanSchema,
)

logger = logging.getLogger("agents.planning.planner")

DEFAULT_BREAK_MINUTES = 10
LONG_SESSION_BREAK_MINUTES = 15


def _parse_deadline(deadline_str: Optional[str], timezone_str: str = "UTC") -> Optional[datetime]:
    if not deadline_str:
        return None
    try:
        dt = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
        mapping = {
            "IST": 5.5,
            "UTC": 0.0,
            "GMT": 0.0,
        }
        offset_hours = mapping.get(timezone_str.upper(), 0.0)
        is_midnight = (dt.hour == 0 and dt.minute == 0 and dt.second == 0)
        dl = (dt + timedelta(hours=offset_hours)).replace(tzinfo=None)
        if is_midnight:
            dl = dl.replace(hour=23, minute=59, second=59)
        return dl
    except Exception:
        return None


def _consume_from_slots(slots: List[List], minutes: int) -> None:
    remaining = minutes
    for slot in slots:
        if remaining <= 0:
            break
        consume = min(remaining, slot[2])
        slot[0] = slot[0] + timedelta(minutes=consume)
        slot[2] -= consume
        remaining -= consume


def _schedule_all(
    task_plans: List[TaskPlanSchema],
    free_slots: List[FreeSlotItem],
    preferred_session_duration: int,
    timezone_str: str = "UTC",
) -> Tuple[List[TaskPlanSchema], PlanSummary]:
    sorted_slots_meta = sorted(
        free_slots,
        key=lambda s: (s.date_str, not s.is_productive, s.start),
    )
    slot_state: List[List] = [[s.start, s.end, s.duration_minutes] for s in sorted_slots_meta]

    work_since_break = 0
    breaks_inserted = 0
    total_scheduled_minutes = 0
    all_warnings: List[str] = []
    updated_plans: List[TaskPlanSchema] = []

    for tp in task_plans:
        deadline_dt = _parse_deadline(tp.task_deadline, timezone_str)
        updated_subtasks: List[SubtaskSchema] = []
        unplaced_count = 0

        for subtask in tp.subtasks:
            if work_since_break >= preferred_session_duration:
                break_len = LONG_SESSION_BREAK_MINUTES if work_since_break >= 90 else DEFAULT_BREAK_MINUTES
                _consume_from_slots(slot_state, break_len)
                breaks_inserted += 1
                work_since_break = 0

            needed = subtask.estimated_minutes
            placed = False

            for slot in slot_state:
                slot_start, slot_end, slot_dur = slot
                if slot_dur < needed:
                    continue
                if deadline_dt and slot_start > deadline_dt:
                    continue

                sched_start = slot_start
                sched_end = slot_start + timedelta(minutes=needed)
                slot[0] = sched_end
                slot[2] = slot_dur - needed

                updated_subtasks.append(subtask.model_copy(update={
                    "scheduled_start": sched_start.isoformat(),
                    "scheduled_end": sched_end.isoformat(),
                }))
                work_since_break += needed
                total_scheduled_minutes += needed
                placed = True
                break

            if not placed:
                updated_subtasks.append(subtask)
                unplaced_count += 1

        last_end: Optional[datetime] = None
        for s in updated_subtasks:
            if s.scheduled_end:
                try:
                    dt = datetime.fromisoformat(s.scheduled_end)
                    if last_end is None or dt > last_end:
                        last_end = dt
                except Exception:
                    pass

        can_complete = tp.can_complete_on_time
        warning = tp.warning

        if unplaced_count > 0:
            can_complete = False
            msg = f"'{tp.task_title}': {unplaced_count} subtask(s) could not be scheduled — insufficient free time."
            warning = warning or msg
            all_warnings.append(msg)

        if deadline_dt and last_end and last_end > deadline_dt:
            can_complete = False
            msg = f"'{tp.task_title}': some subtasks fall after the deadline."
            warning = warning or msg
            if msg not in all_warnings:
                all_warnings.append(msg)

        if warning and warning not in all_warnings:
            all_warnings.append(warning)

        updated_plans.append(tp.model_copy(update={
            "subtasks": updated_subtasks,
            "can_complete_on_time": can_complete,
            "warning": warning,
        }))

    all_subtasks = [s for tp in updated_plans for s in tp.subtasks]
    scheduled_sub = sum(1 for s in all_subtasks if s.scheduled_start)
    dates_used = set()
    for s in all_subtasks:
        if s.scheduled_start:
            try:
                dates_used.add(datetime.fromisoformat(s.scheduled_start).date())
            except Exception:
                pass

    span_days = 0
    if len(dates_used) > 1:
        span_days = (max(dates_used) - min(dates_used)).days + 1
    elif dates_used:
        span_days = 1

    summary = PlanSummary(
        total_tasks=len(updated_plans),
        tasks_scheduled=sum(1 for tp in updated_plans if tp.can_complete_on_time),
        tasks_cannot_complete=sum(1 for tp in updated_plans if not tp.can_complete_on_time),
        total_subtasks=len(all_subtasks),
        scheduled_subtasks=scheduled_sub,
        unscheduled_subtasks=len(all_subtasks) - scheduled_sub,
        total_scheduled_hours=round(total_scheduled_minutes / 60, 1),
        warnings=all_warnings,
        breaks_inserted=breaks_inserted,
        schedule_days_span=span_days,
    )

    return updated_plans, summary


def generate_global_plan(
    uid: str,
    task_plans: List[TaskPlanSchema],
    free_slots: List[FreeSlotItem],
    preferred_session_duration: int,
    timezone_str: str = "UTC",
) -> GlobalPlan:
    scheduled_plans, summary = _schedule_all(task_plans, free_slots, preferred_session_duration, timezone_str)
    return GlobalPlan(
        plan_id=str(uuid4()),
        user_id=uid,
        status="active",
        summary=summary,
        task_plans=scheduled_plans,
    )
