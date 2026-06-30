from __future__ import annotations
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from firebase_admin import firestore
from middleware.auth import verify_token
from services.task_service import get_all_tasks

from agents.planning.schemas import ReorderRequest, SubtaskCreate, SubtaskUpdate
from agents.planning.decomposition_agent import decompose_all_tasks
from agents.planning.priority_agent import prioritize_tasks
from agents.planning.planner_agent import generate_global_plan
from agents.planning.free_slot_service import get_multi_day_free_slots
from agents.planning.plan_store import (
    save_plan,
    get_latest_plan,
    get_plan,
    update_subtask_in_plan,
    add_subtask_to_plan,
    delete_subtask_from_plan,
    reorder_subtasks_in_plan,
)

logger = logging.getLogger("api.planning")
router = APIRouter(prefix="/api/planning", tags=["Planning"])
db = firestore.client()


def _get_profile(uid: str) -> dict:
    doc = db.collection("users").document(uid).get()
    return doc.to_dict().get("profile", {}) if doc.exists else {}


@router.post("/generate")
async def generate_plan(user=Depends(verify_token)):
    uid = user["uid"]
    try:
        tasks = await get_all_tasks(uid)
        pending = [t for t in tasks if t.get("status") != "completed" and t.get("title")]
        if not pending:
            raise HTTPException(status_code=400, detail="No pending tasks found to plan.")

        profile = _get_profile(uid)
        wh_start = profile.get("working_hours_start", "09:00")
        wh_end = profile.get("working_hours_end", "18:00")
        prod_hours = profile.get("productive_hours", [])
        session_dur = int(profile.get("preferred_session_duration") or 60)

        subtasks_map = decompose_all_tasks(pending)

        free_slots = get_multi_day_free_slots(
            uid=uid,
            working_hours_start=wh_start,
            working_hours_end=wh_end,
            productive_hours_raw=prod_hours,
            days_ahead=14,
        )
        total_free_minutes = sum(s.duration_minutes for s in free_slots)

        task_plans = prioritize_tasks(pending, subtasks_map, total_free_minutes)
        plan = generate_global_plan(uid, task_plans, free_slots, session_dur)
        plan_id = save_plan(plan)

        for task in pending:
            task_id = task.get("id")
            if task_id:
                try:
                    db.collection("tasks").document(task_id).update({"plan_id": plan_id})
                except Exception:
                    pass

        return {"plan_id": plan_id, "plan": plan.model_dump()}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Plan generation failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {str(exc)}")


@router.get("/latest")
async def get_latest(user=Depends(verify_token)):
    uid = user["uid"]
    plan = get_latest_plan(uid)
    if not plan:
        raise HTTPException(status_code=404, detail="No plan found.")
    return plan.model_dump()


@router.get("/plans/{plan_id}")
async def get_single_plan(plan_id: str, user=Depends(verify_token)):
    uid = user["uid"]
    plan = get_plan(uid, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return plan.model_dump()


@router.post("/plans/{plan_id}/reorder")
async def reorder(plan_id: str, req: ReorderRequest, user=Depends(verify_token)):
    uid = user["uid"]
    ok = reorder_subtasks_in_plan(uid, plan_id, req.task_id, req.subtask_ids)
    if not ok:
        raise HTTPException(status_code=404, detail="Plan or task not found.")
    return {"success": True}


@router.patch("/plans/{plan_id}/subtasks/{subtask_id}")
async def patch_subtask(
    plan_id: str,
    subtask_id: str,
    update: SubtaskUpdate,
    task_id: str = Query(...),
    user=Depends(verify_token),
):
    uid = user["uid"]
    ok = update_subtask_in_plan(uid, plan_id, task_id, subtask_id, update)
    if not ok:
        raise HTTPException(status_code=404, detail="Subtask not found.")
    return {"success": True}


@router.post("/plans/{plan_id}/subtasks")
async def post_subtask(plan_id: str, subtask: SubtaskCreate, user=Depends(verify_token)):
    uid = user["uid"]
    subtask_id = add_subtask_to_plan(uid, plan_id, subtask)
    if not subtask_id:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return {"subtask_id": subtask_id}


@router.delete("/plans/{plan_id}/subtasks/{subtask_id}")
async def del_subtask(
    plan_id: str,
    subtask_id: str,
    task_id: str = Query(...),
    user=Depends(verify_token),
):
    uid = user["uid"]
    ok = delete_subtask_from_plan(uid, plan_id, task_id, subtask_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Subtask not found.")
    return {"success": True}


@router.post("/plans/{plan_id}/regenerate")
async def regenerate(plan_id: str, user=Depends(verify_token)):
    uid = user["uid"]
    existing = get_plan(uid, plan_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Plan not found.")

    profile = _get_profile(uid)
    wh_start = profile.get("working_hours_start", "09:00")
    wh_end = profile.get("working_hours_end", "18:00")
    prod_hours = profile.get("productive_hours", [])
    session_dur = int(profile.get("preferred_session_duration") or 60)

    cleared_plans = [
        tp.model_copy(update={
            "subtasks": [
                s.model_copy(update={"scheduled_start": None, "scheduled_end": None})
                for s in tp.subtasks
            ]
        })
        for tp in existing.task_plans
    ]

    free_slots = get_multi_day_free_slots(
        uid=uid,
        working_hours_start=wh_start,
        working_hours_end=wh_end,
        productive_hours_raw=prod_hours,
        days_ahead=14,
    )

    new_plan = generate_global_plan(uid, cleared_plans, free_slots, session_dur)
    new_plan.plan_id = plan_id
    save_plan(new_plan)
    return {"plan_id": plan_id, "plan": new_plan.model_dump()}
