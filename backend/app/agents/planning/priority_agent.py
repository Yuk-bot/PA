from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
import logging

from agents.planning.schemas import SubtaskSchema, TaskPlanSchema

logger = logging.getLogger("agents.planning.priority")

_PRIORITY_VALUES: Dict[str, int] = {"high": 3, "medium": 2, "low": 1}


from datetime import timedelta

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


def _days_until(deadline_str: Optional[str], timezone_str: str = "UTC") -> float:
    dl = _parse_deadline(deadline_str, timezone_str)
    if not dl:
        return 365.0
    try:
        mapping = {
            "IST": 5.5,
            "UTC": 0.0,
            "GMT": 0.0,
        }
        offset_hours = mapping.get(timezone_str.upper(), 0.0)
        local_now = datetime.utcnow() + timedelta(hours=offset_hours)
        delta = (dl - local_now).total_seconds() / 86400
        return max(0.01, delta)
    except Exception:
        return 365.0


def _score(task: Dict, timezone_str: str = "UTC") -> float:
    pv = _PRIORITY_VALUES.get(task.get("priority", "medium"), 2)
    days = _days_until(task.get("deadline"), timezone_str)
    return round(pv * 0.4 + (1.0 / days) * 0.6, 4)


def _free_minutes_before(free_slots: List[Any], deadline_dt: Optional[datetime]) -> int:
    if not deadline_dt:
        return sum(s.duration_minutes for s in free_slots)
    
    total = 0
    for slot in free_slots:
        if slot.end <= deadline_dt:
            total += slot.duration_minutes
        elif slot.start < deadline_dt:
            overlap = int((deadline_dt - slot.start).total_seconds() / 60)
            total += min(overlap, slot.duration_minutes)
    return total


def _feasibility_warning(
    task: Dict,
    subtasks: List[SubtaskSchema],
    free_minutes_before: int,
    timezone_str: str = "UTC",
) -> tuple[bool, Optional[str]]:
    total_minutes = sum(s.estimated_minutes for s in subtasks)
    deadline = task.get("deadline")
    if not deadline:
        return True, None

    dl = _parse_deadline(deadline, timezone_str)
    if not dl:
        return True, None

    if total_minutes > free_minutes_before:
        hours_needed = round(total_minutes / 60, 1)
        y_hours = round(free_minutes_before / 60, 1)
        deadline_formatted = dl.strftime("%b %d, %Y at %I:%M %p")
        return False, (
            f"Task cannot be completed because its deadline is {deadline_formatted} and "
            f"only {y_hours}h of free working hours remain, which is less than the required ~{hours_needed}h."
        )
    return True, None


def prioritize_tasks(
    tasks: List[Dict],
    subtasks_map: Dict[str, List[SubtaskSchema]],
    free_slots: List[Any],
    working_hours_per_day: float = 8.0,
    timezone_str: str = "UTC",
) -> List[TaskPlanSchema]:
    task_plans: List[TaskPlanSchema] = []
    cumulative_minutes = 0
    
    total_free_minutes = sum(s.duration_minutes for s in free_slots)

    for task in tasks:
        task_id = task.get("id") or task.get("task_id", "")
        subtasks = subtasks_map.get(task_id, [])
        score = _score(task, timezone_str)
        
        deadline_dt = _parse_deadline(task.get("deadline"), timezone_str)
        free_minutes_before = _free_minutes_before(free_slots, deadline_dt)
        
        can_complete, warning = _feasibility_warning(task, subtasks, free_minutes_before, timezone_str)

        task_minutes = sum(s.estimated_minutes for s in subtasks)
        cumulative_minutes += task_minutes

        if cumulative_minutes > total_free_minutes and not warning:
            warning = (
                "Insufficient free time to schedule all tasks. "
                "This task may not be fully accommodated."
            )
            can_complete = False

        task_plans.append(TaskPlanSchema(
            task_id=task_id,
            task_title=task.get("title", "Untitled"),
            task_deadline=task.get("deadline"),
            task_priority=task.get("priority", "medium"),
            priority_score=score,
            can_complete_on_time=can_complete,
            warning=warning,
            subtasks=subtasks,
        ))

    task_plans.sort(key=lambda tp: tp.priority_score, reverse=True)
    return task_plans
