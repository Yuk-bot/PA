import os
import json
import time
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from agent_runtime.base.agent import BaseRuntimeAgent
from agent_runtime.orchestrator.registry import register_agent
from agent_runtime.schemas.models import AgentResponse, ExecutionContext, Event
from agent_runtime.events.bus import InMemoryEventBus
from agents.planning.schemas import GlobalPlan, TaskPlanSchema, SubtaskSchema
from agents.planning.plan_store import get_plan, save_plan

logger = logging.getLogger("agents.planning.engagement")

def _get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception:
        return None

def _parse_dt(iso_str: Optional[str]) -> Optional[datetime]:
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None

@register_agent("EngagementPlanner")
class EngagementPlanningAgent(BaseRuntimeAgent):
    def __init__(self) -> None:
        super().__init__(
            name="EngagementPlanner",
            description="Generates an alternative schedule optimized for engagement and reduced cognitive fatigue.",
            state_permissions={
                "mixed_schedule": "rw",
                "dependency_groups": "rw",
                "difficulty_levels": "rw",
                "engagement_score": "rw",
                "schedule_metrics": "rw",
                "*": "r",
            },
            memory_permissions={
                "working": "*",
                "session": "*",
                "long_term": "*",
            },
        )
        self.event_bus = InMemoryEventBus()

    async def run(self, context: ExecutionContext, input_data: Dict[str, Any]) -> AgentResponse:
        uid = context.user_id
        session_id = context.session_id
        plan_id = input_data.get("plan_id")
        if not plan_id:
            return AgentResponse(success=False, error="Missing plan_id in input_data")

        await self.event_bus.publish(Event(
            event_id=str(random.randint(100000, 999999)),
            event_name="MixedSchedulePlanningStarted",
            payload={"plan_id": plan_id, "user_id": uid},
            session_id=session_id,
            user_id=uid
        ))

        plan = get_plan(uid, plan_id)
        if not plan or not plan.task_plans:
            return AgentResponse(success=False, error="Plan or sequential schedule not found")

        all_subtasks = []
        for tp in plan.task_plans:
            for s in tp.subtasks:
                all_subtasks.append(s)

        if not all_subtasks:
            return AgentResponse(success=False, error="No subtasks found in the plan")

        difficulty_levels = {}
        dependency_groups = []
        client = _get_client()

        if client:
            try:
                task_data_list = []
                for tp in plan.task_plans:
                    task_data_list.append({
                        "task_id": tp.task_id,
                        "title": tp.task_title,
                        "priority": tp.task_priority,
                        "subtasks": [{"id": s.subtask_id, "title": s.title, "minutes": s.estimated_minutes} for s in tp.subtasks]
                    })

                prompt = (
                    "You are a task analysis assistant. Classify the difficulty level of each subtask into 'hard', 'medium', or 'easy' "
                    "based on estimated effort, complexity, and type. Also identify dependency chains/groups of subtasks that MUST be scheduled "
                    "consecutively without breaks or interleaving (e.g. backend implementation -> testing).\n\n"
                    f"Tasks Data: {json.dumps(task_data_list)}\n\n"
                    "Return ONLY a JSON object with this structure (no markdown formatting, no backticks, no extra text):\n"
                    "{\n"
                    "  \"difficulty_levels\": {\n"
                    "    \"subtask_id_here\": \"hard/medium/easy\"\n"
                    "  },\n"
                    "  \"dependency_groups\": [\n"
                    "    [\"subtask_id_1\", \"subtask_id_2\"]\n"
                    "  ]\n"
                    "}"
                )

                response = client.models.generate_content(
                    model=os.getenv("PLANNING_DECOMP_MODEL", "gemini-2.5-flash"),
                    contents=prompt,
                )
                raw = response.text.strip()
                if raw.startswith("```"):
                    lines = raw.split("\n")
                    raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
                parsed = json.loads(raw)
                difficulty_levels = parsed.get("difficulty_levels", {})
                dependency_groups = parsed.get("dependency_groups", [])
            except Exception as e:
                logger.error(f"LLM categorization failed: {e}")

        for s in all_subtasks:
            if s.subtask_id not in difficulty_levels:
                if s.estimated_minutes > 60:
                    difficulty_levels[s.subtask_id] = "hard"
                elif s.estimated_minutes > 30:
                    difficulty_levels[s.subtask_id] = "medium"
                else:
                    difficulty_levels[s.subtask_id] = "easy"

        await self.event_bus.publish(Event(
            event_id=str(random.randint(100000, 999999)),
            event_name="DifficultyCategorized",
            payload={"difficulty_levels": difficulty_levels},
            session_id=session_id,
            user_id=uid
        ))

        await self.event_bus.publish(Event(
            event_id=str(random.randint(100000, 999999)),
            event_name="DependencyGroupsCreated",
            payload={"dependency_groups": dependency_groups},
            session_id=session_id,
            user_id=uid
        ))

        subtask_map = {s.subtask_id: s for s in all_subtasks}
        task_plans_map = {tp.task_id: tp for tp in plan.task_plans}

        flat_scheduled = []
        for tp in plan.task_plans:
            for s in tp.subtasks:
                if s.scheduled_start and s.scheduled_end:
                    flat_scheduled.append((_parse_dt(s.scheduled_start), _parse_dt(s.scheduled_end)))

        flat_scheduled.sort(key=lambda x: x[0])
        time_slots = []
        for start, end in flat_scheduled:
            time_slots.append([start, end, int((end - start).total_seconds() / 60)])

        retry_count = 0
        success = False
        mixed_task_plans = []
        metrics = {}
        engagement_score = 0.0

        while retry_count < 3 and not success:
            await self.event_bus.publish(Event(
                event_id=str(random.randint(100000, 999999)),
                event_name="EvaluationStarted",
                payload={"retry_count": retry_count},
                session_id=session_id,
                user_id=uid
            ))

            slot_state = [[ts[0], ts[1], ts[2]] for ts in time_slots]
            task_blocks = {}
            for tp in plan.task_plans:
                task_blocks[tp.task_id] = []
                grouped_ids = set()
                for group in dependency_groups:
                    valid_group = [sid for sid in group if sid in subtask_map and subtask_map[sid].task_id == tp.task_id]
                    if valid_group:
                        task_blocks[tp.task_id].append(valid_group)
                        for sid in valid_group:
                            grouped_ids.add(sid)
                for s in tp.subtasks:
                    if s.subtask_id not in grouped_ids:
                        task_blocks[tp.task_id].append([s.subtask_id])

            scheduled_blocks = []
            last_difficulty = None
            last_task_id = None
            consecutive_same_task_minutes = 0

            random_factor = 0.1 * retry_count

            while any(task_blocks.values()):
                eligible_candidates = []
                for tid, blocks in task_blocks.items():
                    if blocks:
                        eligible_candidates.append((tid, blocks[0]))

                if not eligible_candidates:
                    break

                best_candidate = None
                best_score = -999999.0

                for tid, block in eligible_candidates:
                    tp = task_plans_map[tid]
                    base_score = tp.priority_score

                    block_difficulties = [difficulty_levels.get(sid, "medium") for sid in block]
                    max_diff = "easy"
                    if "hard" in block_difficulties:
                        max_diff = "hard"
                    elif "medium" in block_difficulties:
                        max_diff = "medium"

                    diff_mod = 0.0
                    if last_difficulty == "hard":
                        if max_diff == "easy":
                            diff_mod = 3.0
                        elif max_diff == "medium":
                            diff_mod = 1.5
                        elif max_diff == "hard":
                            diff_mod = -3.0
                    elif last_difficulty == "easy":
                        if max_diff == "hard":
                            diff_mod = 1.0

                    switch_mod = 0.0
                    block_minutes = sum(subtask_map[sid].estimated_minutes for sid in block)
                    if tid == last_task_id:
                        if consecutive_same_task_minutes + block_minutes <= 90:
                            switch_mod = 0.8
                        else:
                            switch_mod = -2.5
                    else:
                        if last_task_id is not None:
                            switch_mod = 0.2

                    urgency_mod = 0.0
                    deadline_dt = _parse_dt(tp.task_deadline)
                    if deadline_dt:
                        current_sched_time = datetime.now()
                        for slot in slot_state:
                            if slot[2] > 0:
                                current_sched_time = slot[0]
                                break
                        time_left = (deadline_dt - current_sched_time).total_seconds() / 60
                        remaining_task_minutes = sum(subtask_map[sid].estimated_minutes for b in task_blocks[tid] for sid in b)
                        if time_left <= remaining_task_minutes * 1.5:
                            urgency_mod = 25.0
                        elif time_left <= remaining_task_minutes * 3.0:
                            urgency_mod = 10.0

                    score = base_score + diff_mod + switch_mod + urgency_mod
                    score += random.uniform(-random_factor, random_factor)

                    if score > best_score:
                        best_score = score
                        best_candidate = (tid, block, max_diff, block_minutes)

                if not best_candidate:
                    break

                tid, block, block_diff, block_mins = best_candidate
                task_blocks[tid].pop(0)

                for sid in block:
                    subtask = subtask_map[sid]
                    needed = subtask.estimated_minutes
                    placed = False

                    for slot in slot_state:
                        slot_start, slot_end, slot_dur = slot
                        if slot_dur >= needed:
                            subtask.scheduled_start = slot_start.isoformat()
                            subtask.scheduled_end = (slot_start + timedelta(minutes=needed)).isoformat()
                            slot[0] = slot_start + timedelta(minutes=needed)
                            slot[2] = slot_dur - needed
                            placed = True
                            break

                    if not placed:
                        subtask.scheduled_start = None
                        subtask.scheduled_end = None

                scheduled_blocks.append((tid, block, block_diff, block_mins))
                last_difficulty = block_diff
                if tid == last_task_id:
                    consecutive_same_task_minutes += block_mins
                else:
                    last_task_id = tid
                    consecutive_same_task_minutes = block_mins

            mixed_task_plans = []
            for tp in plan.task_plans:
                tp_subtasks = [subtask_map[s.subtask_id] for s in tp.subtasks]
                mixed_task_plans.append(tp.model_copy(update={
                    "subtasks": tp_subtasks
                }))

            errors = []
            for tp in mixed_task_plans:
                deadline_dt = _parse_dt(tp.task_deadline)
                for s in tp.subtasks:
                    if s.scheduled_end and deadline_dt:
                        end_dt = _parse_dt(s.scheduled_end)
                        if end_dt > deadline_dt:
                            errors.append(f"Subtask {s.subtask_id} scheduled after task deadline")

            hard_streak = 0
            max_hard_streak = 0
            for tid, block, diff, mins in scheduled_blocks:
                if diff == "hard":
                    hard_streak += 1
                    max_hard_streak = max(max_hard_streak, hard_streak)
                else:
                    hard_streak = 0

            if max_hard_streak >= 3:
                errors.append(f"Hard workload streak of {max_hard_streak} detected")

            all_ids = {s.subtask_id for s in all_subtasks}
            scheduled_ids = {sid for b in scheduled_blocks for sid in b[1]}
            if all_ids != scheduled_ids:
                errors.append("Mismatch in subtask sets between schedules")

            if not errors:
                success = True
                total_switches = 0
                prev_tid = None
                for tid, block, diff, mins in scheduled_blocks:
                    if prev_tid and tid != prev_tid:
                        total_switches += 1
                    prev_tid = tid

                metrics = {
                    "max_hard_streak": max_hard_streak,
                    "context_switches": total_switches,
                    "difficulty_distribution": {
                        "hard": sum(1 for d in difficulty_levels.values() if d == "hard"),
                        "medium": sum(1 for d in difficulty_levels.values() if d == "medium"),
                        "easy": sum(1 for d in difficulty_levels.values() if d == "easy")
                    }
                }
                engagement_score = round(100.0 - (max_hard_streak * 15.0) - (total_switches * 2.0), 1)
                engagement_score = max(10.0, min(100.0, engagement_score))
            else:
                retry_count += 1
                await self.event_bus.publish(Event(
                    event_id=str(random.randint(100000, 999999)),
                    event_name="EvaluationFailed",
                    payload={"errors": errors},
                    session_id=session_id,
                    user_id=uid
                ))

        if success:
            await self.event_bus.publish(Event(
                event_id=str(random.randint(100000, 999999)),
                event_name="EvaluationPassed",
                payload={"engagement_score": engagement_score},
                session_id=session_id,
                user_id=uid
            ))

            plan.mixed_task_plans = mixed_task_plans
            plan.difficulty_levels = difficulty_levels
            plan.dependency_groups = dependency_groups
            plan.engagement_score = engagement_score
            plan.schedule_metrics = metrics
            save_plan(plan)

            await self.event_bus.publish(Event(
                event_id=str(random.randint(100000, 999999)),
                event_name="MixedScheduleStored",
                payload={"plan_id": plan_id},
                session_id=session_id,
                user_id=uid
            ))

            await self.event_bus.publish(Event(
                event_id=str(random.randint(100000, 999999)),
                event_name="MixedScheduleGenerated",
                payload={"plan_id": plan_id},
                session_id=session_id,
                user_id=uid
            ))

            return AgentResponse(
                success=True,
                output_data={
                    "mixed_schedule": [tp.model_dump() for tp in mixed_task_plans],
                    "difficulty_levels": difficulty_levels,
                    "dependency_groups": dependency_groups,
                    "engagement_score": engagement_score,
                    "schedule_metrics": metrics
                }
            )
        else:
            return AgentResponse(success=False, error="Failed to generate a valid engagement schedule after 3 retries")
