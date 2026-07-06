import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  GripVertical,
  Loader,
  Plus,
  RefreshCw,
  Trash2,
  Pencil,
  Check,
  X,
  CalendarDays,
  Zap,
  Coffee,
} from "lucide-react";
import {
  generatePlan,
  getLatestPlan,
  reorderSubtasks,
  updateSubtask,
  addSubtask,
  deleteSubtask,
  regeneratePlan,
  generateSubtasks,
  schedulePlan,
  generateMixedSchedule,
} from "@/services/planningService";

function fmt(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function fmtDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function fmtMins(mins) {
  if (mins < 60) return `${mins}m`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

const PRIORITY_STYLES = {
  high: "bg-red-100 text-red-700 border-red-200",
  medium: "bg-amber-100 text-amber-700 border-amber-200",
  low: "bg-emerald-100 text-emerald-700 border-emerald-200",
};

function SummaryCard({ summary, planId }) {
  if (!summary) return null;
  const { total_tasks, tasks_scheduled, tasks_cannot_complete, total_subtasks, scheduled_subtasks, unscheduled_subtasks, total_scheduled_hours, breaks_inserted, schedule_days_span, warnings } = summary;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Total Tasks Planned", value: total_tasks, icon: Zap, color: "text-violet-600" },
          { label: "Tasks scheduled completely", value: tasks_scheduled, icon: CheckCircle2, color: "text-emerald-600" },
          { label: "Hours Scheduled", value: `${total_scheduled_hours}h`, icon: Clock, color: "text-blue-600" },
          { label: "Days Span", value: schedule_days_span || 1, icon: CalendarDays, color: "text-slate-600" },
        ].map(({ label, value, icon: Icon, color }) => (
          <Card key={label} className="p-4 border-slate-200/60 bg-white/80 backdrop-blur-sm">
            <div className="flex items-center gap-2 mb-1">
              <Icon className={`w-4 h-4 ${color}`} />
              <span className="text-xs text-slate-500 font-medium">{label}</span>
            </div>
            <p className="text-2xl font-bold text-slate-900">{value}</p>
          </Card>
        ))}
      </div>

      <div className="flex flex-wrap gap-3 text-sm">
        <span className="flex items-center gap-1.5 text-slate-600">
          <Zap className="w-3.5 h-3.5 text-violet-500" />
          {scheduled_subtasks} of {total_subtasks} subtasks scheduled
        </span>
        {breaks_inserted > 0 && (
          <span className="flex items-center gap-1.5 text-slate-600">
            <Coffee className="w-3.5 h-3.5 text-amber-500" />
            {breaks_inserted} breaks auto-inserted
          </span>
        )}
        {unscheduled_subtasks > 0 && (
          <span className="flex items-center gap-1.5 text-red-600 font-medium">
            <AlertCircle className="w-3.5 h-3.5" />
            {unscheduled_subtasks} subtasks couldn't be scheduled
          </span>
        )}
      </div>

      {warnings.length > 0 && (
        <div className="space-y-2">
          {tasks_cannot_complete > 0 && (
            <div className="flex items-start gap-3 p-3 rounded-lg bg-red-50 border border-red-200">
              <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-semibold text-red-800">
                  {tasks_cannot_complete} task{tasks_cannot_complete !== 1 ? "s" : ""} cannot be completed on time
                </p>
                <p className="text-xs text-red-600 mt-0.5">
                  Lower-priority tasks were deferred. See task cards below for details.
                </p>
              </div>
            </div>
          )}
          {warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-50 border border-amber-200">
              <AlertCircle className="w-3.5 h-3.5 text-amber-600 mt-0.5 shrink-0" />
              <p className="text-xs text-amber-800">{w}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const DIFFICULTY_COLORS = {
  hard: "bg-red-50 text-red-700 border-red-100",
  medium: "bg-amber-50 text-amber-700 border-amber-100",
  easy: "bg-emerald-50 text-emerald-700 border-emerald-100"
};

function SortableSubtaskCard({ subtask, planId, taskId, token, onDeleted, onUpdated, difficulty, isGrouped, parentTaskTitle, hideGrip }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: subtask.subtask_id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(subtask.title);
  const [editMins, setEditMins] = useState(subtask.estimated_minutes);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const saveEdit = async () => {
    setSaving(true);
    try {
      await updateSubtask(token, planId, subtask.subtask_id, taskId, {
        title: editTitle.trim() || subtask.title,
        estimated_minutes: Math.max(15, Math.min(180, parseInt(editMins) || 30)),
      });
      onUpdated();
      setEditing(false);
    } catch {
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteSubtask(token, planId, subtask.subtask_id, taskId);
      onDeleted(subtask.subtask_id);
    } catch {
      setDeleting(false);
    }
  };

  const isScheduled = !!subtask.scheduled_start;

  return (
    <div ref={hideGrip ? null : setNodeRef} style={hideGrip ? {} : style} className="group">
      <div className={`flex items-start gap-2 p-3 rounded-lg border transition-all duration-150 ${isDragging
        ? "border-violet-300 bg-violet-50 shadow-lg"
        : isScheduled
          ? "border-slate-200/60 bg-white hover:border-slate-300 hover:shadow-sm"
          : "border-dashed border-slate-300/60 bg-slate-50/50"
        }`}>
        {!hideGrip && (
          <button
            {...attributes}
            {...listeners}
            className="mt-0.5 p-0.5 text-slate-300 hover:text-slate-500 cursor-grab active:cursor-grabbing touch-none shrink-0"
          >
            <GripVertical className="w-4 h-4" />
          </button>
        )}

        <div className="flex-1 min-w-0">
          {parentTaskTitle && (
            <p className="text-[10px] uppercase font-bold tracking-wider text-violet-600 mb-0.5">{parentTaskTitle}</p>
          )}
          {editing ? (
            <div className="space-y-1.5">
              <Input
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="h-7 text-sm border-slate-300"
                autoFocus
              />
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Duration (min):</span>
                <Input
                  type="number"
                  value={editMins}
                  onChange={(e) => setEditMins(e.target.value)}
                  className="h-6 w-20 text-xs border-slate-300"
                  min={15}
                  max={180}
                />
              </div>
            </div>
          ) : (
            <p className="text-sm font-medium text-slate-800 leading-snug">{subtask.title}</p>
          )}

          <div className="flex items-center gap-3 mt-1 flex-wrap">
            {isScheduled ? (
              <span className="text-[11px] text-violet-600 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {fmt(subtask.scheduled_start)} – {new Date(subtask.scheduled_end).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true })}
              </span>
            ) : (
              <span className="text-[11px] text-slate-400 italic">Not yet scheduled</span>
            )}
            <span className="text-[11px] text-slate-400">{fmtMins(subtask.estimated_minutes)}</span>
            {difficulty && (
              <Badge variant="outline" className={`text-[9px] px-1.5 py-0 h-4 uppercase ${DIFFICULTY_COLORS[difficulty] || ""}`}>
                {difficulty}
              </Badge>
            )}
            {isGrouped && (
              <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 bg-blue-50 text-blue-700 border-blue-100">
                Group
              </Badge>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {editing ? (
            <>
              <Button size="icon-xs" variant="ghost" onClick={saveEdit} disabled={saving} className="w-6 h-6 text-emerald-600 hover:bg-emerald-50">
                {saving ? <Loader className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
              </Button>
              <Button size="icon-xs" variant="ghost" onClick={() => { setEditing(false); setEditTitle(subtask.title); setEditMins(subtask.estimated_minutes); }} className="w-6 h-6 text-slate-400 hover:bg-slate-100">
                <X className="w-3 h-3" />
              </Button>
            </>
          ) : (
            <Button
              size="icon-xs"
              variant="ghost"
              onClick={() => setEditing(true)}
              className="w-6 h-6 text-slate-300 hover:text-slate-600 hover:bg-slate-100 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <Pencil className="w-3 h-3" />
            </Button>
          )}
          <Button
            size="icon-xs"
            variant="ghost"
            onClick={handleDelete}
            disabled={deleting}
            className="w-6 h-6 text-slate-300 hover:text-red-600 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            {deleting ? <Loader className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
          </Button>
        </div>
      </div>
    </div>
  );
}

function AddSubtaskForm({ planId, taskId, token, onAdded }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [mins, setMins] = useState(30);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!title.trim()) return;
    setLoading(true);
    try {
      await addSubtask(token, planId, {
        title: title.trim(),
        estimated_minutes: Math.max(15, parseInt(mins) || 30),
        task_id: taskId,
      });
      setTitle("");
      setMins(30);
      setOpen(false);
      onAdded();
    } catch {
    } finally {
      setLoading(false);
    }
  };

  if (!open) {
    return (
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen(true)}
        className="w-full text-xs text-slate-400 hover:text-violet-600 hover:bg-violet-50 border border-dashed border-slate-200 hover:border-violet-200 mt-1"
      >
        <Plus className="w-3.5 h-3.5 mr-1" />
        Add subtask
      </Button>
    );
  }

  return (
    <div className="mt-2 p-3 rounded-lg border border-violet-200 bg-violet-50/50 space-y-2">
      <Input
        placeholder="Subtask title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        className="h-8 text-sm border-slate-300"
        autoFocus
      />
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-500 whitespace-nowrap">Duration (min):</span>
        <Input
          type="number"
          value={mins}
          onChange={(e) => setMins(e.target.value)}
          className="h-7 w-20 text-xs border-slate-300"
          min={15}
          max={180}
        />
        <div className="flex gap-1 ml-auto">
          <Button size="xs" onClick={submit} disabled={loading || !title.trim()} className="h-7 text-xs bg-violet-600 hover:bg-violet-700 text-white">
            {loading ? <Loader className="w-3 h-3 animate-spin" /> : "Add"}
          </Button>
          <Button size="xs" variant="ghost" onClick={() => setOpen(false)} className="h-7 text-xs">
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

function TaskPlanCard({ taskPlan, planId, token, onReorder, onMutate, plan }) {
  const [collapsed, setCollapsed] = useState(false);
  const [subtasks, setSubtasks] = useState(taskPlan.subtasks ?? []);

  useEffect(() => {
    setSubtasks(taskPlan.subtasks ?? []);
  }, [taskPlan]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = async ({ active, over }) => {
    if (!over || active.id === over.id) return;
    const oldIdx = subtasks.findIndex((s) => s.subtask_id === active.id);
    const newIdx = subtasks.findIndex((s) => s.subtask_id === over.id);
    const reordered = arrayMove(subtasks, oldIdx, newIdx);
    setSubtasks(reordered);
    try {
      await reorderSubtasks(token, planId, taskPlan.task_id, reordered.map((s) => s.subtask_id));
    } catch {
      setSubtasks(subtasks);
    }
    onReorder();
  };

  const handleDeleted = (subtaskId) => {
    setSubtasks((prev) => prev.filter((s) => s.subtask_id !== subtaskId));
  };

  const priorityStyle = PRIORITY_STYLES[taskPlan.task_priority] || PRIORITY_STYLES.medium;

  return (
    <Card className={`border-slate-200/60 overflow-hidden transition-all ${!taskPlan.can_complete_on_time ? "border-l-4 border-l-red-400" : "border-l-4 border-l-violet-400"
      }`}>
      <div
        className="p-4 flex items-start justify-between gap-3 cursor-pointer select-none hover:bg-slate-50/60 transition-colors"
        onClick={() => setCollapsed((p) => !p)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-slate-900 text-sm">{taskPlan.task_title}</h3>
            <Badge className={`text-[10px] px-1.5 py-0.5 border ${priorityStyle}`}>
              {taskPlan.task_priority}
            </Badge>
            {taskPlan.can_complete_on_time ? (
              <span className="flex items-center gap-1 text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-100 px-1.5 py-0.5 rounded">
                <CheckCircle2 className="w-3 h-3" /> On time
              </span>
            ) : (
              <span className="flex items-center gap-1 text-[10px] text-red-700 bg-red-50 border border-red-100 px-1.5 py-0.5 rounded">
                <AlertTriangle className="w-3 h-3" /> At risk
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
            {taskPlan.task_deadline && (
              <span className="flex items-center gap-1">
                <CalendarDays className="w-3 h-3" />
                Due {fmtDate(taskPlan.task_deadline)}
              </span>
            )}
            <span>{subtasks.length} subtasks</span>
            <span>Score {taskPlan.priority_score.toFixed(2)}</span>
          </div>
          {taskPlan.warning && (
            <p className="text-[11px] text-red-600 mt-1 flex items-start gap-1">
              <AlertCircle className="w-3 h-3 mt-0.5 shrink-0" />
              {taskPlan.warning}
            </p>
          )}
        </div>
        <button className="text-slate-400 hover:text-slate-600 shrink-0 mt-0.5">
          {collapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
        </button>
      </div>

      {!collapsed && (
        <div className="px-4 pb-4 space-y-1.5 border-t border-slate-100 pt-3">
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={subtasks.map((s) => s.subtask_id)} strategy={verticalListSortingStrategy}>
              {subtasks.map((subtask) => (
                <SortableSubtaskCard
                  key={subtask.subtask_id}
                  subtask={subtask}
                  planId={planId}
                  taskId={taskPlan.task_id}
                  token={token}
                  onDeleted={handleDeleted}
                  onUpdated={onMutate}
                  difficulty={plan?.difficulty_levels?.[subtask.subtask_id]}
                  isGrouped={plan?.dependency_groups?.some(groupStr => groupStr.split(",").includes(subtask.subtask_id))}
                />
              ))}
            </SortableContext>
          </DndContext>
          <AddSubtaskForm planId={planId} taskId={taskPlan.task_id} token={token} onAdded={onMutate} />
        </div>
      )}
    </Card>
  );
}

export default function PlanPage() {
  const token = localStorage.getItem("token");
  const navigate = useNavigate();

  const [plan, setPlan] = useState(null);
  const [scheduleMode, setScheduleMode] = useState("sequential");
  const [generatingMixed, setGeneratingMixed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generatingSubtasks, setGeneratingSubtasks] = useState(false);
  const [schedulingPlan, setSchedulingPlan] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [reorderNotice, setReorderNotice] = useState(false);

  const flash = (msg) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(null), 4000);
  };

  const loadPlan = useCallback(async () => {
    if (!token) return;
    try {
      const p = await getLatestPlan(token);
      setPlan(p);
    } catch {
      setPlan(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadPlan();
  }, [loadPlan]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const result = await generatePlan(token);
      setPlan(result.plan);
      flash("Plan generated successfully!");
    } catch (err) {
      setError(err.message || "Failed to generate plan");
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateSubtasks = async () => {
    setGeneratingSubtasks(true);
    setError(null);
    try {
      const result = await generateSubtasks(token);
      setPlan(result.plan);
      flash("Subtasks generated! Now generate your plan to schedule them.");
    } catch (err) {
      setError(err.message || "Failed to generate subtasks");
    } finally {
      setGeneratingSubtasks(false);
    }
  };

  const handleSchedulePlan = async () => {
    if (!plan) return;
    setSchedulingPlan(true);
    setError(null);
    try {
      const result = await schedulePlan(token, plan.plan_id);
      setPlan(result.plan);
      flash("Plan scheduled successfully!");
    } catch (err) {
      setError(err.message || "Failed to schedule plan");
    } finally {
      setSchedulingPlan(false);
    }
  };

  const handleRegenerate = async () => {
    if (!plan) return;
    setRegenerating(true);
    setError(null);
    setReorderNotice(false);
    try {
      const result = await regeneratePlan(token, plan.plan_id);
      setPlan(result.plan);
      flash("Schedule regenerated!");
    } catch (err) {
      setError(err.message || "Failed to regenerate");
    } finally {
      setRegenerating(false);
    }
  };

  const handleMutate = () => {
    setReorderNotice(true);
  };

  const handleReorder = () => {
    setReorderNotice(true);
  };

  const handleGenerateMixed = async () => {
    if (!plan) return;
    setGeneratingMixed(true);
    setError(null);
    try {
      await generateMixedSchedule(token);
      await loadPlan();
      flash("Engagement schedule generated successfully!");
    } catch (err) {
      setError(err.message || "Failed to generate mixed schedule");
    } finally {
      setGeneratingMixed(false);
    }
  };

  const getMixedFlatSchedule = () => {
    const scheduled = [];
    const unscheduled = [];
    (plan?.mixed_task_plans ?? []).forEach((tp) => {
      (tp.subtasks ?? []).forEach((sub) => {
        const item = {
          ...sub,
          taskId: tp.task_id,
          parentTaskTitle: tp.task_title,
          priority: tp.task_priority,
        };
        if (sub.scheduled_start) {
          scheduled.push(item);
        } else {
          unscheduled.push(item);
        }
      });
    });
    scheduled.sort((a, b) => new Date(a.scheduled_start) - new Date(b.scheduled_start));
    return { scheduled, unscheduled };
  };

  if (loading) {
    return (
      <main className="flex-1 overflow-y-auto">
        <div className="p-6 md:p-8 flex items-center justify-center min-h-[60vh]">
          <div className="flex flex-col items-center gap-3 text-slate-400">
            <Loader className="w-8 h-8 animate-spin" />
            <p className="text-sm">Loading your plan…</p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="p-6 md:p-8 space-y-6 max-w-4xl mx-auto">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold text-slate-900 flex items-center gap-2">
              <Zap className="w-7 h-7 text-violet-600" />
              Generated Plan
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              {plan
                ? `${plan.task_plans?.length ?? 0} tasks · Generated ${new Date(plan.created_at * 1000).toLocaleDateString()}`
                : "No plan yet — generate one from your pending tasks"}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {plan && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleRegenerate}
                disabled={regenerating}
                className="gap-2 border-slate-300"
              >
                {regenerating ? <Loader className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                Regenerate
              </Button>
            )}
            {plan && plan.status === "draft" && (
              <Button
                size="sm"
                onClick={handleSchedulePlan}
                disabled={schedulingPlan}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                {schedulingPlan ? "Saving Plan..." : "Save Plan"}
              </Button>
            )}
            {plan && plan.status === "active" && (
              <Button
                size="sm"
                disabled
                className="bg-slate-100 text-slate-500 border border-slate-200 cursor-not-allowed gap-1.5"
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                Saved & Active
              </Button>
            )}
            <Button
              size="sm"
              onClick={handleGenerateSubtasks}
              disabled={generatingSubtasks}
              className="gap-2 bg-violet-600 hover:bg-violet-700 text-white"
            >
              {generatingSubtasks ? <Loader className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              {generatingSubtasks ? "Generating..." : plan ? "Regenerate Subtasks" : "Generate Subtasks"}
            </Button>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {success && (
          <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-700 text-sm">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            {success}
          </div>
        )}

        {reorderNotice && (
          <div className="flex items-center justify-between p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-center gap-2 text-amber-800 text-sm">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              You've made edits — regenerate to update the schedule timing.
            </div>
            <Button size="xs" variant="outline" onClick={handleRegenerate} disabled={regenerating} className="text-xs border-amber-300 text-amber-800 hover:bg-amber-100">
              {regenerating ? <Loader className="w-3 h-3 animate-spin" /> : "Regenerate now"}
            </Button>
          </div>
        )}

        {!plan && !generating && (
          <Card className="border-slate-200/50 bg-gradient-to-br from-violet-50 to-slate-50 p-12">
            <div className="flex flex-col items-center text-center gap-5">
              <div className="w-20 h-20 rounded-2xl bg-violet-100 border border-violet-200 flex items-center justify-center">
                <Zap className="w-10 h-10 text-violet-500" />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-slate-900">No plan yet</h3>
                <p className="text-slate-500 text-sm mt-2 max-w-sm">
                  Click "Generate Subtasks" to let the AI analyze all your pending tasks and calendar events, break them down into actionable subtasks, and prepare your schedule.
                </p>
              </div>
              <Button onClick={handleGenerateSubtasks} disabled={generatingSubtasks} className="gap-2 bg-violet-600 hover:bg-violet-700 text-white px-6">
                {generatingSubtasks ? <Loader className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                {generatingSubtasks ? "Generating..." : "Generate Subtasks"}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => navigate("/tasks")} className="text-slate-500 hover:text-slate-900 text-xs">
                Go to Tasks →
              </Button>
            </div>
          </Card>
        )}

        {plan && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-2 border rounded-lg p-1 bg-slate-100/80 w-fit">
                <Button
                  size="sm"
                  onClick={() => setScheduleMode("sequential")}
                  className={`text-xs h-7 px-3 font-medium ${scheduleMode === "sequential" ? "bg-white text-slate-900 shadow-sm hover:bg-white" : "bg-transparent text-slate-600 hover:bg-slate-200/50"}`}
                >
                  Sequential View
                </Button>
                <Button
                  size="sm"
                  onClick={() => setScheduleMode("mixed")}
                  className={`text-xs h-7 px-3 font-medium ${scheduleMode === "mixed" ? "bg-white text-slate-900 shadow-sm hover:bg-white" : "bg-transparent text-slate-600 hover:bg-slate-200/50"}`}
                >
                  Mixed (Engagement)
                </Button>
              </div>
              {scheduleMode === "mixed" && plan.engagement_score !== undefined && (
                <div className="text-xs text-slate-500 font-medium">
                  Engagement Score: <span className="text-violet-600 font-bold text-sm">{plan.engagement_score}%</span>
                </div>
              )}
            </div>
            <SummaryCard summary={plan.summary} planId={plan.plan_id} />
            <Separator />
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-slate-800">Task Plans</h3>
              <p className="text-xs text-slate-500">
                Sorted by priority · drag subtasks to reorder · hover to edit or delete
              </p>
            </div>
            {scheduleMode === "mixed" && (!plan.mixed_task_plans || plan.mixed_task_plans.length === 0) ? (
              <Card className="border-slate-200/50 bg-gradient-to-br from-violet-50 to-slate-50 p-12">
                <div className="flex flex-col items-center text-center gap-5">
                  <div className="w-20 h-20 rounded-2xl bg-violet-100 border border-violet-200 flex items-center justify-center">
                    <Zap className="w-10 h-10 text-violet-500" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-slate-900">No mixed schedule yet</h3>
                    <p className="text-slate-500 text-sm mt-2 max-w-sm">
                      Generate an alternative schedule optimized for engagement and reduced cognitive fatigue.
                    </p>
                  </div>
                  <Button onClick={handleGenerateMixed} disabled={generatingMixed} className="gap-2 bg-violet-600 hover:bg-violet-700 text-white px-6">
                    {generatingMixed ? <Loader className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    {generatingMixed ? "Generating..." : "Generate Mixed Schedule"}
                  </Button>
                </div>
              </Card>
            ) : generatingMixed ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <Card key={i} className="p-4 border-slate-200/60 bg-white/80 animate-pulse">
                    <div className="h-4 bg-slate-200 rounded w-1/3 mb-2"></div>
                    <div className="h-3 bg-slate-200 rounded w-1/4 mb-4"></div>
                    <div className="space-y-2">
                      <div className="h-8 bg-slate-100 rounded"></div>
                      <div className="h-8 bg-slate-100 rounded"></div>
                    </div>
                  </Card>
                ))}
              </div>
            ) : scheduleMode === "mixed" ? (
              <div className="space-y-6">
                {(() => {
                  const { scheduled, unscheduled } = getMixedFlatSchedule();
                  return (
                    <>
                      {scheduled.length > 0 && (
                        <div className="space-y-3">
                          <h4 className="text-sm font-semibold text-slate-700">Timeline</h4>
                          {scheduled.map((subtask) => (
                            <SortableSubtaskCard
                              key={subtask.subtask_id}
                              subtask={subtask}
                              planId={plan.plan_id}
                              taskId={subtask.taskId}
                              token={token}
                              onDeleted={handleMutate}
                              onUpdated={loadPlan}
                              difficulty={plan?.difficulty_levels?.[subtask.subtask_id]}
                              isGrouped={plan?.dependency_groups?.some(groupStr => groupStr.split(",").includes(subtask.subtask_id))}
                              parentTaskTitle={subtask.parentTaskTitle}
                              hideGrip={true}
                            />
                          ))}
                        </div>
                      )}
                      {unscheduled.length > 0 && (
                        <div className="space-y-3 pt-4 border-t border-slate-100">
                          <h4 className="text-sm font-semibold text-slate-500 italic">Unscheduled Subtasks</h4>
                          {unscheduled.map((subtask) => (
                            <SortableSubtaskCard
                              key={subtask.subtask_id}
                              subtask={subtask}
                              planId={plan.plan_id}
                              taskId={subtask.taskId}
                              token={token}
                              onDeleted={handleMutate}
                              onUpdated={loadPlan}
                              difficulty={plan?.difficulty_levels?.[subtask.subtask_id]}
                              isGrouped={plan?.dependency_groups?.some(groupStr => groupStr.split(",").includes(subtask.subtask_id))}
                              parentTaskTitle={subtask.parentTaskTitle}
                              hideGrip={true}
                            />
                          ))}
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>
            ) : (
              <div className="space-y-3">
                {(plan.task_plans ?? []).map((tp) => (
                  <TaskPlanCard
                    key={tp.task_id}
                    taskPlan={tp}
                    planId={plan.plan_id}
                    token={token}
                    onReorder={handleReorder}
                    onMutate={handleMutate}
                    plan={plan}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
