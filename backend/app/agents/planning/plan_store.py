from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import uuid4
import logging

from firebase_admin import firestore

from agents.planning.schemas import (
    GlobalPlan,
    SubtaskCreate,
    SubtaskSchema,
    SubtaskUpdate,
)

logger = logging.getLogger("agents.planning.plan_store")
db = firestore.client()


def _plans_ref(uid: str):
    return db.collection("users").document(uid).collection("plans")


def save_plan(plan: GlobalPlan) -> str:
    _plans_ref(plan.user_id).document(plan.plan_id).set(plan.model_dump())
    return plan.plan_id


def get_latest_plan(uid: str) -> Optional[GlobalPlan]:
    docs = list(
        _plans_ref(uid)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(1)
        .stream()
    )
    if not docs:
        return None
    try:
        return GlobalPlan(**docs[0].to_dict())
    except Exception as exc:
        logger.error(f"Failed to parse latest plan: {exc}")
        return None


def get_plan(uid: str, plan_id: str) -> Optional[GlobalPlan]:
    doc = _plans_ref(uid).document(plan_id).get()
    if not doc.exists:
        return None
    try:
        return GlobalPlan(**doc.to_dict())
    except Exception as exc:
        logger.error(f"Failed to parse plan {plan_id}: {exc}")
        return None


def _save_plan_obj(plan: GlobalPlan) -> None:
    plan.updated_at = datetime.utcnow().timestamp()
    _plans_ref(plan.user_id).document(plan.plan_id).set(plan.model_dump())


def update_subtask_in_plan(
    uid: str, plan_id: str, task_id: str, subtask_id: str, update: SubtaskUpdate
) -> bool:
    plan = get_plan(uid, plan_id)
    if not plan:
        return False

    updated = False
    for tp in plan.task_plans:
        if tp.task_id != task_id:
            continue
        new_subtasks = []
        for s in tp.subtasks:
            if s.subtask_id == subtask_id:
                new_subtasks.append(s.model_copy(update=update.model_dump(exclude_none=True)))
                updated = True
            else:
                new_subtasks.append(s)
        tp.subtasks = new_subtasks

    if updated:
        _save_plan_obj(plan)
    return updated


def add_subtask_to_plan(uid: str, plan_id: str, subtask: SubtaskCreate) -> Optional[str]:
    plan = get_plan(uid, plan_id)
    if not plan:
        return None

    new_subtask = SubtaskSchema(
        subtask_id=str(uuid4()),
        task_id=subtask.task_id,
        title=subtask.title,
        description=subtask.description,
        estimated_minutes=subtask.estimated_minutes,
        order=999,
    )

    for tp in plan.task_plans:
        if tp.task_id == subtask.task_id:
            tp.subtasks.append(new_subtask)
            for i, s in enumerate(tp.subtasks):
                s.order = i
            break

    _save_plan_obj(plan)
    return new_subtask.subtask_id


def delete_subtask_from_plan(uid: str, plan_id: str, task_id: str, subtask_id: str) -> bool:
    plan = get_plan(uid, plan_id)
    if not plan:
        return False

    deleted = False
    for tp in plan.task_plans:
        if tp.task_id != task_id:
            continue
        before = len(tp.subtasks)
        tp.subtasks = [s for s in tp.subtasks if s.subtask_id != subtask_id]
        if len(tp.subtasks) < before:
            deleted = True
            for i, s in enumerate(tp.subtasks):
                s.order = i

    if deleted:
        _save_plan_obj(plan)
    return deleted


def reorder_subtasks_in_plan(
    uid: str, plan_id: str, task_id: str, subtask_ids: list
) -> bool:
    plan = get_plan(uid, plan_id)
    if not plan:
        return False

    for tp in plan.task_plans:
        if tp.task_id != task_id:
            continue
        id_map = {s.subtask_id: s for s in tp.subtasks}
        reordered = []
        for i, sid in enumerate(subtask_ids):
            if sid in id_map:
                s = id_map[sid].model_copy(update={"order": i})
                reordered.append(s)
        tp.subtasks = reordered

    _save_plan_obj(plan)
    return True
