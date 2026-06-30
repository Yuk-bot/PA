const BASE = "http://localhost:8000/api/planning";

function headers(token) {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

export async function generatePlan(token) {
  const res = await fetch(`${BASE}/generate`, { method: "POST", headers: headers(token) });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Plan generation failed (${res.status})`);
  }
  return res.json();
}

export async function generateSubtasks(token) {
  const res = await fetch(`${BASE}/generate-subtasks`, { method: "POST", headers: headers(token) });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Subtask generation failed (${res.status})`);
  }
  return res.json();
}

export async function schedulePlan(token, planId) {
  const res = await fetch(`${BASE}/plans/${planId}/schedule`, { method: "POST", headers: headers(token) });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Plan scheduling failed (${res.status})`);
  }
  return res.json();
}

export async function getLatestPlan(token) {
  const res = await fetch(`${BASE}/latest`, { headers: headers(token) });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch plan (${res.status})`);
  return res.json();
}

export async function getPlan(token, planId) {
  const res = await fetch(`${BASE}/plans/${planId}`, { headers: headers(token) });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch plan (${res.status})`);
  return res.json();
}

export async function reorderSubtasks(token, planId, taskId, subtaskIds) {
  const res = await fetch(`${BASE}/plans/${planId}/reorder`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify({ task_id: taskId, subtask_ids: subtaskIds }),
  });
  if (!res.ok) throw new Error(`Reorder failed (${res.status})`);
  return res.json();
}

export async function updateSubtask(token, planId, subtaskId, taskId, data) {
  const res = await fetch(
    `${BASE}/plans/${planId}/subtasks/${subtaskId}?task_id=${encodeURIComponent(taskId)}`,
    { method: "PATCH", headers: headers(token), body: JSON.stringify(data) }
  );
  if (!res.ok) throw new Error(`Update failed (${res.status})`);
  return res.json();
}

export async function addSubtask(token, planId, data) {
  const res = await fetch(`${BASE}/plans/${planId}/subtasks`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Add subtask failed (${res.status})`);
  return res.json();
}

export async function deleteSubtask(token, planId, subtaskId, taskId) {
  const res = await fetch(
    `${BASE}/plans/${planId}/subtasks/${subtaskId}?task_id=${encodeURIComponent(taskId)}`,
    { method: "DELETE", headers: headers(token) }
  );
  if (!res.ok) throw new Error(`Delete failed (${res.status})`);
  return res.json();
}

export async function regeneratePlan(token, planId) {
  const res = await fetch(`${BASE}/plans/${planId}/regenerate`, {
    method: "POST",
    headers: headers(token),
  });
  if (!res.ok) throw new Error(`Regenerate failed (${res.status})`);
  return res.json();
}
