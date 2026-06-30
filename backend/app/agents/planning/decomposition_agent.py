from __future__ import annotations
import json
import logging
import os
from typing import Dict, List
from uuid import uuid4

from agents.planning.schemas import SubtaskSchema

logger = logging.getLogger("agents.planning.decomposition")

MAX_SUBTASKS = 8
_MODEL = os.getenv("PLANNING_DECOMP_MODEL", "gemini-2.5-flash")
_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        _client = genai.Client(api_key=api_key)
        return _client
    except Exception as exc:
        logger.error(f"Gemini init failed: {exc}")
        return None


def _build_prompt(task: Dict) -> str:
    deadline_line = f"Deadline: {task.get('deadline', 'None')}"
    return (
        f"You are a task planning assistant. Decompose this task into concrete, ordered, actionable subtasks.\n\n"
        f"Task: {task.get('title', 'Untitled')}\n"
        f"Description: {task.get('description', '')}\n"
        f"{deadline_line}\n"
        f"Priority: {task.get('priority', 'medium')}\n"
        f"Estimated total hours: {task.get('estimated_hours', 1.0)}\n\n"
        f"Return ONLY a JSON object with this exact structure (no markdown, no extra text):\n"
        f'{{"subtasks": [{{"title": "...", "description": "...", "estimated_minutes": 30}}]}}\n\n'
        f"Rules:\n"
        f"- Maximum {MAX_SUBTASKS} subtasks\n"
        f"- Each subtask completable in 15–120 minutes\n"
        f"- estimated_minutes must be an integer between 15 and 120\n"
        f"- Subtasks must be logically ordered (earlier ones enable later ones)\n"
        f"- Be specific and actionable"
    )


def _fallback(task: Dict) -> List[SubtaskSchema]:
    total_min = int((task.get("estimated_hours") or 1.0) * 60)
    session_min = max(30, min(90, total_min))
    return [SubtaskSchema(
        subtask_id=str(uuid4()),
        task_id=task.get("id", ""),
        title=f"Work on: {task.get('title', 'Task')}",
        description=task.get("description", ""),
        estimated_minutes=session_min,
        order=0,
    )]


def decompose_task(task: Dict) -> List[SubtaskSchema]:
    client = _get_client()
    if not client:
        return _fallback(task)
    try:
        response = client.models.generate_content(model=_MODEL, contents=_build_prompt(task))
        raw = response.text.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        data = json.loads(raw)
        subtasks_raw = data.get("subtasks", [])
        result = []
        for i, s in enumerate(subtasks_raw[:MAX_SUBTASKS]):
            result.append(SubtaskSchema(
                subtask_id=str(uuid4()),
                task_id=task.get("id", ""),
                title=str(s.get("title", "Subtask"))[:200],
                description=str(s.get("description", ""))[:500],
                estimated_minutes=max(15, min(120, int(s.get("estimated_minutes", 30)))),
                order=i,
            ))
        return result if result else _fallback(task)
    except Exception as exc:
        logger.error(f"Decomposition failed for task {task.get('id')}: {exc}")
        return _fallback(task)


def decompose_all_tasks(tasks: List[Dict]) -> Dict[str, List[SubtaskSchema]]:
    return {(task.get("id") or task.get("task_id", "")): decompose_task(task) for task in tasks}
