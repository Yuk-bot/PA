from fastapi import APIRouter, Depends, HTTPException
from middleware.auth import verify_token
from agents.planning.plan_store import get_latest_plan
from agent_runtime.execution.engine import ExecutionEngine
from agents.planning.engagement_agent import EngagementPlanningAgent

router = APIRouter(prefix="/api/schedule", tags=["Schedule"])

@router.get("")
async def get_schedule(user=Depends(verify_token)):
    uid = user["uid"]
    plan = get_latest_plan(uid)
    if not plan:
        raise HTTPException(status_code=404, detail="No plan found")
    if not plan.mixed_task_plans and plan.task_plans:
        engine = ExecutionEngine()
        agent = EngagementPlanningAgent()
        res = await engine.execute_agent(
            agent=agent,
            user_id=uid,
            session_id=plan.plan_id,
            input_data={"plan_id": plan.plan_id},
            state_data={},
            working_memory={},
            session_memory={},
            long_term_memory={}
        )
        if res.success:
            plan = get_latest_plan(uid)
    return {
        "sequential_schedule": [tp.model_dump() for tp in plan.task_plans] if plan else [],
        "mixed_schedule": [tp.model_dump() for tp in plan.mixed_task_plans] if plan and plan.mixed_task_plans else None
    }

@router.get("/mixed")
async def get_mixed_schedule(user=Depends(verify_token)):
    uid = user["uid"]
    plan = get_latest_plan(uid)
    if not plan:
        raise HTTPException(status_code=404, detail="No plan found")
    if not plan.mixed_task_plans and plan.task_plans:
        engine = ExecutionEngine()
        agent = EngagementPlanningAgent()
        res = await engine.execute_agent(
            agent=agent,
            user_id=uid,
            session_id=plan.plan_id,
            input_data={"plan_id": plan.plan_id},
            state_data={},
            working_memory={},
            session_memory={},
            long_term_memory={}
        )
        if res.success:
            plan = get_latest_plan(uid)
    return {
        "mixed_schedule": [tp.model_dump() for tp in plan.mixed_task_plans] if plan and plan.mixed_task_plans else None
    }

@router.post("/generate-mixed")
async def generate_mixed_schedule(user=Depends(verify_token)):
    uid = user["uid"]
    plan = get_latest_plan(uid)
    if not plan:
        raise HTTPException(status_code=404, detail="No plan found")
    engine = ExecutionEngine()
    agent = EngagementPlanningAgent()
    res = await engine.execute_agent(
        agent=agent,
        user_id=uid,
        session_id=plan.plan_id,
        input_data={"plan_id": plan.plan_id},
        state_data={},
        working_memory={},
        session_memory={},
        long_term_memory={}
    )
    if not res.success:
        raise HTTPException(status_code=500, detail=res.error or "Failed to generate mixed schedule")
    updated_plan = get_latest_plan(uid)
    return {
        "plan_id": updated_plan.plan_id if updated_plan else plan.plan_id,
        "mixed_schedule": [tp.model_dump() for tp in updated_plan.mixed_task_plans] if updated_plan and updated_plan.mixed_task_plans else []
    }
