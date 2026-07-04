from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
import logging

from agents.planning.schemas import SubtaskSchema, TaskPlanSchema

logger = logging.getLogger("agents.planning.priority")

_PRIORITY_VALUES: Dict[str, int] = {"high": 3, "medium": 2, "low": 1}


from datetime import timedelta

def _days_until(deadline_str: Optional[str], timezone_str: str = "UTC") -> float:
    if not deadline_str:
        return 365.0
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
            
        # Get current local time (relative to user's local day clock)
        # Base on UTC time to remain consistent across local machines and cloud servers
        local_now = datetime.utcnow() + timedelta(hours=offset_hours)
        delta = (dl - local_now).total_seconds() / 86400
        return max(0.01, delta)
    except Exception:
        return 365.0


def _score(task: Dict, timezone_str: str = "UTC") -> float:
    pv = _PRIORITY_VALUES.get(task.get("priority", "medium"), 2)
    days = _days_until(task.get("deadline"), timezone_str)
    return round(pv * 0.4 + (1.0 / days) * 0.6, 4)


def _feasibility_warning(task: Dict, subtasks: List[SubtaskSchema], working_hours_per_day: float = 8.0, timezone_str: str = "UTC") -> tuple[bool, Optional[str]]:
    total_minutes = sum(s.estimated_minutes for s in subtasks)
    deadline = task.get("deadline")
    if not deadline:
        return True, None

    days = _days_until(deadline, timezone_str)
    if days <= 0:
        return False, "Deadline has already passed."

    max_available_minutes = days * working_hours_per_day * 60
    if total_minutes > max_available_minutes:
        hours_needed = round(total_minutes / 60, 1)
        if days < 1.0:
            hours_remain = round(days * 24, 1)
            time_display = f"{hours_remain} hours"
        else:
            time_display = f"{round(days, 1)} days"
        wh_display = round(working_hours_per_day, 1)
        if wh_display.is_integer():
            wh_display = int(wh_display)
        return False, (
            f"Requires ~{hours_needed}h of work but only {time_display} remain "
            f"(assuming {wh_display}h/day). Lower-priority tasks may not be scheduled."
        )
    return True, None


def prioritize_tasks(
    tasks: List[Dict],
    subtasks_map: Dict[str, List[SubtaskSchema]],
    total_free_minutes: int,
    working_hours_per_day: float = 8.0,
    timezone_str: str = "UTC",
) -> List[TaskPlanSchema]:
    task_plans: List[TaskPlanSchema] = []
    cumulative_minutes = 0

    for task in tasks:
        task_id = task.get("id") or task.get("task_id", "")
        subtasks = subtasks_map.get(task_id, [])
        score = _score(task, timezone_str)
        can_complete, warning = _feasibility_warning(task, subtasks, working_hours_per_day, timezone_str)

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
