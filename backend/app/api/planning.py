from __future__ import annotations
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from firebase_admin import firestore
from middleware.auth import verify_token
from services.task_service import get_all_tasks

from agents.planning.schemas import ReorderRequest, SubtaskCreate, SubtaskUpdate, GlobalPlan, TaskPlanSchema, SubtaskSchema
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


@router.post("/generate-subtasks")
async def generate_subtasks(user=Depends(verify_token)):
    uid = user["uid"]
    try:
        tasks = await get_all_tasks(uid)
        pending = [t for t in tasks if t.get("status") != "completed" and t.get("title")]
        calendar_items = []
        from calender.oauth_handler import get_stored_credentials
        from calender.calender_client import GoogleCalendarClient
        creds = get_stored_credentials(uid)
        if creds and creds.connected:
            try:
                client = GoogleCalendarClient(creds, uid)
                events = client.get_events(max_results=50, days_ahead=14)
                for e in events:
                    calendar_items.append({
                        "id": f"event_{e.event_id}",
                        "title": e.title,
                        "description": e.description or "",
                        "priority": "medium",
                        "deadline": e.start.isoformat() if e.start else None,
                        "estimated_hours": 1.0
                    })
            except Exception as e_exc:
                logger.error(f"Failed to fetch calendar events for subtasks: {e_exc}")
        all_items = pending + calendar_items
        if not all_items:
            raise HTTPException(status_code=400, detail="No pending tasks or calendar events found to plan.")
        subtasks_map = decompose_all_tasks(all_items)
        from uuid import uuid4
        task_plans = []
        for item in all_items:
            item_id = item.get("id") or item.get("task_id", "")
            subtasks = subtasks_map.get(item_id, [])
            task_plans.append(TaskPlanSchema(
                task_id=item_id,
                task_title=item.get("title", "Untitled"),
                task_deadline=item.get("deadline"),
                task_priority=item.get("priority", "medium"),
                priority_score=0.0,
                can_complete_on_time=True,
                warning=None,
                subtasks=subtasks
            ))
        plan = GlobalPlan(
            plan_id=str(uuid4()),
            user_id=uid,
            status="draft",
            task_plans=task_plans
        )
        save_plan(plan)
        return {"plan_id": plan.plan_id, "plan": plan.model_dump()}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Subtask generation failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Subtask generation failed: {str(exc)}")


@router.post("/plans/{plan_id}/schedule")
async def schedule_draft_plan(plan_id: str, user=Depends(verify_token)):
    uid = user["uid"]
    try:
        plan = get_plan(uid, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found.")
        profile = _get_profile(uid)
        wh_start = profile.get("working_hours_start", "09:00")
        wh_end = profile.get("working_hours_end", "18:00")
        prod_hours = profile.get("productive_hours", [])
        session_dur = int(profile.get("preferred_session_duration") or 60)
        free_slots = get_multi_day_free_slots(
            uid=uid,
            working_hours_start=wh_start,
            working_hours_end=wh_end,
            productive_hours_raw=prod_hours,
            days_ahead=14,
        )
        total_free_minutes = sum(s.duration_minutes for s in free_slots)
        items_for_priority = []
        for tp in plan.task_plans:
            items_for_priority.append({
                "id": tp.task_id,
                "title": tp.task_title,
                "deadline": tp.task_deadline,
                "priority": tp.task_priority
            })
        subtasks_map = {tp.task_id: tp.subtasks for tp in plan.task_plans}
        try:
            sh, sm = int(wh_start.split(":")[0]), int(wh_start.split(":")[1])
            eh, em = int(wh_end.split(":")[0]), int(wh_end.split(":")[1])
            wh_duration = (eh * 60 + em) - (sh * 60 + sm)
            working_hours_per_day = max(1.0, wh_duration / 60.0)
        except Exception:
            working_hours_per_day = 8.0

        timezone_str = profile.get("timezone", "UTC")
        task_plans = prioritize_tasks(items_for_priority, subtasks_map, total_free_minutes, working_hours_per_day, timezone_str)
        scheduled_plan = generate_global_plan(uid, task_plans, free_slots, session_dur, timezone_str)
        scheduled_plan.plan_id = plan_id
        scheduled_plan.status = "active"
        save_plan(scheduled_plan)
        for tp in scheduled_plan.task_plans:
            if not tp.task_id.startswith("event_"):
                try:
                    db.collection("tasks").document(tp.task_id).update({"plan_id": plan_id})
                except Exception:
                    pass
        return {"plan_id": plan_id, "plan": scheduled_plan.model_dump()}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Scheduling failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(exc)}")


@router.post("/generate")
async def generate_plan(user=Depends(verify_token)):
    uid = user["uid"]
    try:
        subtasks_res = await generate_subtasks(user)
        plan_id = subtasks_res["plan_id"]
        scheduled_res = await schedule_draft_plan(plan_id, user)
        return scheduled_res
    except Exception as exc:
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

    timezone_str = profile.get("timezone", "UTC")
    new_plan = generate_global_plan(uid, cleared_plans, free_slots, session_dur, timezone_str)
    new_plan.plan_id = plan_id
    save_plan(new_plan)
    return {"plan_id": plan_id, "plan": new_plan.model_dump()}
