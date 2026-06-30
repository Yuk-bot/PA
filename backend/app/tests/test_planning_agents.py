from datetime import datetime, timedelta
import pytest

from agents.planning.schemas import SubtaskSchema, TaskPlanSchema, FreeSlotItem
from agents.planning.decomposition_agent import decompose_task
from agents.planning.priority_agent import prioritize_tasks
from agents.planning.planner_agent import generate_global_plan


def test_decomposition_fallback():
    task = {
        "id": "t1",
        "title": "Build PA App",
        "description": "Create task decomposer",
        "estimated_hours": 3.0,
        "priority": "high",
    }
    subtasks = decompose_task(task)
    assert len(subtasks) >= 1
    for s in subtasks:
        assert s.task_id == "t1"
        assert 15 <= s.estimated_minutes <= 120


def test_priority_agent():
    tasks = [
        {"id": "t1", "title": "Task 1", "priority": "high", "deadline": (datetime.now() + timedelta(days=2)).isoformat()},
        {"id": "t2", "title": "Task 2", "priority": "low", "deadline": (datetime.now() + timedelta(days=10)).isoformat()},
    ]
    subtasks_map = {
        "t1": [SubtaskSchema(task_id="t1", title="Sub 1", estimated_minutes=60)],
        "t2": [SubtaskSchema(task_id="t2", title="Sub 2", estimated_minutes=60)],
    }
    plans = prioritize_tasks(tasks, subtasks_map, 1000)
    assert len(plans) == 2
    assert plans[0].task_id == "t1"
    assert plans[1].task_id == "t2"
    assert plans[0].priority_score > plans[1].priority_score


def test_engagement_planner():
    tp1 = TaskPlanSchema(
        task_id="t1",
        task_title="Task 1",
        task_deadline=(datetime.now() + timedelta(days=2)).isoformat(),
        task_priority="high",
        subtasks=[SubtaskSchema(subtask_id="s1", task_id="t1", title="Sub 1", estimated_minutes=45)],
    )
    free_slots = [
        FreeSlotItem(
            start=datetime.now() + timedelta(hours=1),
            end=datetime.now() + timedelta(hours=3),
            duration_minutes=120,
            date_str=(datetime.now() + timedelta(hours=1)).date().isoformat(),
            is_productive=True,
        )
    ]
    plan = generate_global_plan("test_user", [tp1], free_slots, 60)
    assert plan.user_id == "test_user"
    assert plan.summary.total_tasks == 1
    assert plan.summary.scheduled_subtasks == 1
    assert plan.task_plans[0].subtasks[0].scheduled_start is not None
