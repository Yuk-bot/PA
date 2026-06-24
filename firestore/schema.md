users/
  {uid}/
    - profile (interests, timezone, etc.)
    - preferences

tasks/
  {taskId}/
    - title, description, deadline
    - userId
    - status (active, completed, missed)
    - priority_score
    - risk_score

schedules/
  {scheduleId}/
    - userId, startDate, endDate
    - subtasks (array of task slices + timing)
    - completion_probability

checkpoints/
  {checkpointId}/
    - taskId, dueTime
    - status (pending, reminded, evidence_submitted)