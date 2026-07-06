from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import uuid4
from typing import Optional, List, Dict, Any
from datetime import datetime


class SubtaskSchema(BaseModel):
    subtask_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    title: str
    description: str = ""
    estimated_minutes: int = 30
    scheduled_start: Optional[str] = None
    scheduled_end: Optional[str] = None
    order: int = 0
    status: str = "todo"


class TaskPlanSchema(BaseModel):
    task_id: str
    task_title: str
    task_deadline: Optional[str] = None
    task_priority: str = "medium"
    priority_score: float = 0.0
    can_complete_on_time: bool = True
    warning: Optional[str] = None
    subtasks: List[SubtaskSchema] = Field(default_factory=list)


class PlanSummary(BaseModel):
    total_tasks: int = 0
    tasks_scheduled: int = 0
    tasks_cannot_complete: int = 0
    total_subtasks: int = 0
    scheduled_subtasks: int = 0
    unscheduled_subtasks: int = 0
    total_scheduled_hours: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    breaks_inserted: int = 0
    schedule_days_span: int = 0


class GlobalPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    status: str = "active"
    created_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    updated_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    summary: Optional[PlanSummary] = None
    task_plans: List[TaskPlanSchema] = Field(default_factory=list)
    mixed_task_plans: Optional[List[TaskPlanSchema]] = None
    dependency_groups: Optional[List[List[str]]] = None
    difficulty_levels: Optional[Dict[str, str]] = None
    engagement_score: Optional[float] = None
    schedule_metrics: Optional[Dict[str, Any]] = None


class FreeSlotItem(BaseModel):
    start: datetime
    end: datetime
    duration_minutes: int
    date_str: str
    is_productive: bool = False


class SubtaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    estimated_minutes: Optional[int] = None
    order: Optional[int] = None
    status: Optional[str] = None


class SubtaskCreate(BaseModel):
    title: str
    description: str = ""
    estimated_minutes: int = 30
    task_id: str


class ReorderRequest(BaseModel):
    task_id: str
    subtask_ids: List[str]
