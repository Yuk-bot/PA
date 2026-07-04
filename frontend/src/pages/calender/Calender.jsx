import { useState, useEffect, useCallback } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Calendar,
  RefreshCw,
  Clock,
  MapPin,
  Users,
  Link as LinkIcon,
  CalendarX,
  CheckCircle2,
  AlertCircle,
  Loader,
  Unplug,
  Mail,
  Zap,
  Trash2,
  CheckSquare,
} from "lucide-react";
import {
  connectCalendar,
  checkCalendarStatus,
  getEvents,
  getFreeSlots,
  disconnectCalendar,
} from "@/services/calendarService";
import {
  checkGmailStatus,
  getGmailSuggestions,
  dismissGmailSuggestion,
  syncGmail,
} from "@/services/gmailService";
import { Separator } from "@/components/ui/separator";
import { API_BASE } from "@/services/apiConfig";


function formatTime(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function formatDuration(startStr, endStr) {
  if (!startStr || !endStr) return "";
  const diff = (new Date(endStr) - new Date(startStr)) / 60000;
  if (diff < 60) return `${diff} min`;
  const h = Math.floor(diff / 60);
  const m = diff % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function formatFreeMinutes(mins) {
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function groupItemsByDate(events, tasks, latestPlan) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);

  const groups = {};

  const addToGroup = (dateMs, item) => {
    const d = new Date(dateMs);
    d.setHours(0, 0, 0, 0);
    const key = d.toISOString();
    if (!groups[key]) {
      let label;
      if (d.getTime() === today.getTime()) label = "Today";
      else if (d.getTime() === tomorrow.getTime()) label = "Tomorrow";
      else
        label = d.toLocaleDateString("en-US", {
          weekday: "long",
          month: "long",
          day: "numeric",
        });
      groups[key] = { label, dateKey: key, items: [] };
    }
    groups[key].items.push(item);
  };

  for (const event of events) {
    addToGroup(new Date(event.start).getTime(), { ...event, itemType: "event" });
  }

  for (const task of tasks) {
    if (!task.deadline) continue;
    const deadlineMs = new Date(task.deadline).getTime();
    if (isNaN(deadlineMs)) continue;
    addToGroup(deadlineMs, { ...task, itemType: "task" });
  }

  if (latestPlan && latestPlan.task_plans) {
    for (const tp of latestPlan.task_plans) {
      if (tp.task_id.startsWith("event_")) continue;
      
      for (const subtask of tp.subtasks) {
        if (!subtask.scheduled_start) continue;
        const startMs = new Date(subtask.scheduled_start).getTime();
        if (isNaN(startMs)) continue;
        
        addToGroup(startMs, {
          id: subtask.subtask_id,
          task_id: tp.task_id,
          title: `${tp.task_title}: ${subtask.title}`,
          description: subtask.description || "",
          start: subtask.scheduled_start,
          end: subtask.scheduled_end,
          priority: tp.task_priority,
          status: subtask.status,
          itemType: "scheduled_subtask",
        });
      }
    }
  }

  return Object.values(groups).sort((a, b) =>
    a.dateKey.localeCompare(b.dateKey)
  );
}


function getMeetingLink(event) {
  const desc = event.description || "";
  const match = desc.match(/https?:\/\/[^\s<"]+/);
  return match ? match[0] : null;
}

function TaskCard({ task, subtasks }) {
  const [expanded, setExpanded] = useState(false);
  const priorityColor =
    task.priority === "high"
      ? "text-red-600 bg-red-50 border-red-100"
      : task.priority === "low"
      ? "text-emerald-700 bg-emerald-50 border-emerald-100"
      : "text-amber-700 bg-amber-50 border-amber-100";

  return (
    <Card className="border-violet-200/60 bg-violet-50/60 backdrop-blur-sm hover:bg-violet-50/90 transition-all duration-200 overflow-hidden">
      <div className="p-4 flex items-start gap-3 cursor-pointer select-none" onClick={() => setExpanded(p => !p)}>
        <CheckSquare className="w-4 h-4 text-violet-500 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="font-semibold text-slate-900 truncate">{task.title}</h4>
            <Badge className="text-[10px] bg-violet-100 text-violet-700 border border-violet-200 shrink-0">
              Task
            </Badge>
            <span
              className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${priorityColor} shrink-0 uppercase`}
            >
              {task.priority}
            </span>
          </div>
          {task.description && (
            <p className="text-xs text-slate-500 mt-1 line-clamp-2">{task.description}</p>
          )}
          <div className="flex items-center gap-1 mt-1.5 text-xs text-violet-600">
            <Clock className="w-3 h-3" />
            Due:{" "}
            {new Date(task.deadline).toLocaleString("en-US", {
              hour: "numeric",
              minute: "2-digit",
              hour12: true,
            })}
          </div>
          {expanded && subtasks && subtasks.length > 0 && (
            <div className="mt-3 pt-3 border-t border-violet-200/40">
              <p className="text-[10px] font-semibold text-violet-700 uppercase tracking-wider mb-2">
                Subtasks
              </p>
              <div className="space-y-1.5 pl-3 border-l-2 border-violet-300">
                {subtasks.map((s) => (
                  <div key={s.subtask_id} className="flex items-center gap-2 text-xs text-slate-700">
                    <div className={`w-1 h-1 rounded-full ${s.status === 'completed' ? 'bg-slate-300' : 'bg-violet-400'}`} />
                    <span className={s.status === 'completed' ? 'line-through text-slate-400' : ''}>
                      {s.title}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      {expanded && (
        <div className="px-4 pb-3 border-t border-violet-100/50 pt-2 bg-violet-100/10 flex justify-end">
          <Link to="/plan" className="text-xs font-medium text-violet-700 hover:underline">
            View on Plan Page →
          </Link>
        </div>
      )}
    </Card>
  );
}

function SkeletonCard() {
  return (
    <div className="border border-slate-200/50 bg-white/70 backdrop-blur-sm rounded-lg p-4 animate-pulse">
      <div className="flex items-start justify-between">
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-slate-200 rounded w-3/5" />
          <div className="flex gap-3">
            <div className="h-3 bg-slate-100 rounded w-16" />
            <div className="h-3 bg-slate-100 rounded w-12" />
          </div>
        </div>
        <div className="h-8 bg-slate-100 rounded w-16 ml-4" />
      </div>
    </div>
  );
}

function SkeletonSection() {
  return (
    <div className="space-y-3">
      <div className="space-y-1 animate-pulse">
        <div className="h-5 bg-slate-200 rounded w-24" />
        <div className="h-3 bg-slate-100 rounded w-16" />
      </div>
      <div className="space-y-2">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    </div>
  );
}

function EventCard({ event, subtasks }) {
  const [expanded, setExpanded] = useState(false);
  const meetingLink = getMeetingLink(event);

  return (
    <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm hover:bg-white/90 transition-all duration-200 cursor-pointer overflow-hidden">
      <div className="p-4" onClick={() => setExpanded((p) => !p)}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-semibold text-slate-900 truncate">
                {event.title}
              </h4>
              {event.is_all_day && (
                <Badge variant="secondary" className="text-xs shrink-0">
                  All day
                </Badge>
              )}
            </div>

            <div className="flex items-center flex-wrap gap-3 mt-2 text-sm text-slate-600">
              {!event.is_all_day && (
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 shrink-0" />
                  {formatTime(event.start)} – {formatTime(event.end)}
                </span>
              )}
              {!event.is_all_day && (
                <span className="text-slate-400 text-xs">
                  {formatDuration(event.start, event.end)}
                </span>
              )}
              {event.location && (
                <span className="flex items-center gap-1 truncate max-w-xs">
                  <MapPin className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">{event.location}</span>
                </span>
              )}
              {event.attendees && event.attendees.length > 0 && (
                <span className="flex items-center gap-1">
                  <Users className="w-3.5 h-3.5 shrink-0" />
                  {event.attendees.length} attendee
                  {event.attendees.length !== 1 ? "s" : ""}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {meetingLink && (
              <a
                href={meetingLink}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-2 py-1.5 rounded-md transition-colors"
              >
                <LinkIcon className="w-3 h-3" />
                Join
              </a>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="text-slate-500 hover:text-slate-900 hover:bg-slate-100 text-xs"
            >
              {expanded ? "Less" : "Details"}
            </Button>
          </div>
        </div>

        {expanded && (
          <div className="mt-3 pt-3 border-t border-slate-100 space-y-2">
            {event.description && (
              <p className="text-sm text-slate-600 whitespace-pre-line line-clamp-4">
                {event.description}
              </p>
            )}
            {event.attendees && event.attendees.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {event.attendees.slice(0, 5).map((email) => (
                  <span
                    key={email}
                    className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full"
                  >
                    {email}
                  </span>
                ))}
                {event.attendees.length > 5 && (
                  <span className="text-xs text-slate-400 px-1 py-0.5">
                    +{event.attendees.length - 5} more
                  </span>
                )}
              </div>
            )}
            {subtasks && subtasks.length > 0 && (
              <div className="mt-3 pt-3 border-t border-slate-100">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  Generated Subtasks
                </p>
                <div className="space-y-1.5 pl-3 border-l-2 border-violet-100">
                  {subtasks.map((s) => (
                    <div key={s.subtask_id} className="flex items-center gap-2 text-xs text-slate-600">
                      <div className={`w-1 h-1 rounded-full ${s.status === 'completed' ? 'bg-slate-300' : 'bg-violet-400'}`} />
                      <span className={s.status === 'completed' ? 'line-through text-slate-400' : ''}>
                        {s.title}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}

function FreeSlotCard({ slot }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-emerald-50/70 border border-emerald-200/60 hover:bg-emerald-50 transition-colors">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
        <span className="text-sm font-medium text-emerald-900">
          {formatTime(slot.start)} – {formatTime(slot.end)}
        </span>
      </div>
      <span className="text-xs text-emerald-700 font-medium bg-emerald-100 px-2 py-1 rounded-full">
        {formatFreeMinutes(slot.duration_minutes)} free
      </span>
    </div>
  );
}

export default function CalendarPage() {
  const token = localStorage.getItem("token");
  const [searchParams, setSearchParams] = useSearchParams();

  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [events, setEvents] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [freeSlots, setFreeSlots] = useState(null);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [latestPlan, setLatestPlan] = useState(null);
  const [isGmailConnected, setIsGmailConnected] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [isGmailSyncing, setIsGmailSyncing] = useState(false);

  const oauthConnected = searchParams.get("calendar_connected");
  const oauthError = searchParams.get("error");
  const oauthEmail = searchParams.get("email");

  const loadCalendarData = useCallback(async () => {
    if (!token) return;
    setError(null);

    try {
      const [eventsResult, slotsResult, gmailStatus] = await Promise.all([
        getEvents(token, 30, 30),
        getFreeSlots(token),
        checkGmailStatus(token),
      ]);

      if (!eventsResult.connected) {
        setIsConnected(false);
        setEvents([]);
        setTasks([]);
        setFreeSlots(null);
        setIsGmailConnected(false);
        setSuggestions([]);
        return;
      }

      setIsConnected(true);
      setEvents(eventsResult.events);
      setFreeSlots(slotsResult.connected ? slotsResult : null);

      // Fetch Firestore tasks to overlay on calendar (non-critical)
      try {
        const tasksRes = await fetch(`${API_BASE}/tasks`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (tasksRes.ok) {
          const tasksData = await tasksRes.json();
          setTasks(
            (tasksData.tasks || []).filter(
              (t) => t.deadline && t.status !== "completed"
            )
          );
        }
      } catch {}
      try {
        const p = await getLatestPlan(token);
        setLatestPlan(p);
      } catch {}

      setIsGmailConnected(gmailStatus.connected);
      if (gmailStatus.connected) {
        const suggs = await getGmailSuggestions(token);
        setSuggestions(suggs.suggestions || []);
      } else {
        setSuggestions([]);
      }
    } catch (err) {
      setError(err.message || "Failed to load calendar data");
    }
  }, [token]);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await loadCalendarData();
      setLoading(false);
    };
    init();
  }, [loadCalendarData]);

  useEffect(() => {
    if (oauthConnected === "true") {
      setSuccessMessage(
        oauthEmail
          ? `Connected as ${oauthEmail}`
          : "Google Calendar connected successfully!"
      );
      setSearchParams({}, { replace: true });
      setIsConnected(true);
      loadCalendarData();

      const t = setTimeout(() => setSuccessMessage(null), 5000);
      return () => clearTimeout(t);
    }

    if (oauthError) {
      const readable =
        oauthError === "missing_code"
          ? "OAuth was cancelled or the code was missing."
          : oauthError === "missing_state"
            ? "OAuth state was invalid. Please try again."
            : `OAuth error: ${oauthError}`;
      setError(readable);
      setSearchParams({}, { replace: true });
    }
  }, [
    oauthConnected,
    oauthError,
    oauthEmail,
    setSearchParams,
    loadCalendarData,
  ]);

  const handleSync = async () => {
    if (!token) return;

    if (!isConnected) {
      setSyncing(true);
      setError(null);
      try {
        const { authorization_url } = await connectCalendar(token);
        window.location.href = authorization_url;
      } catch (err) {
        setError(err.message || "Failed to start Google Calendar connection");
        setSyncing(false);
      }
    } else {
      setSyncing(true);
      setError(null);
      try {
        await loadCalendarData();
        setSuccessMessage("Calendar refreshed");
        setTimeout(() => setSuccessMessage(null), 3000);
      } catch (err) {
        setError(err.message || "Failed to refresh calendar");
      } finally {
        setSyncing(false);
      }
    }
  };

  const handleDisconnect = async () => {
    if (!token) return;
    setSyncing(true);
    setError(null);
    try {
      await disconnectCalendar(token);
      setIsConnected(false);
      setEvents([]);
      setFreeSlots(null);
      setIsGmailConnected(false);
      setSuggestions([]);
      setSuccessMessage("Calendar disconnected");
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err.message || "Failed to disconnect calendar");
    } finally {
      setSyncing(false);
    }
  };

  const handleGmailSync = async (deep = false) => {
    if (!token) return;
    setIsGmailSyncing(true);
    setError(null);
    try {
      const res = await syncGmail(token, deep);
      if (res.success) {
        const suggs = await getGmailSuggestions(token);
        setSuggestions(suggs.suggestions || []);
        setSuccessMessage(deep ? "Gmail deep sync completed" : "Gmail suggestions synced");
        setTimeout(() => setSuccessMessage(null), 3000);
      } else {
        setError(res.error || "Gmail sync failed");
      }
    } catch (err) {
      setError(err.message || "Gmail sync failed");
    } finally {
      setIsGmailSyncing(false);
    }
  };

  const handleAddTask = async (sug) => {
    if (!token) return;
    try {
      const deadline = sug.due_date
        ? new Date(sug.due_date).toISOString()
        : null;
      const res = await fetch(`${API_BASE}/tasks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: sug.title,
          description: sug.description || "",
          priority: sug.urgency || "medium",
          deadline: deadline,
          estimated_hours: 1,
          tags: [],
        }),
      });

      if (!res.ok) throw new Error("Failed to create task");

      await dismissGmailSuggestion(token, sug.suggestion_id);
      setSuggestions((prev) =>
        prev.filter((s) => s.suggestion_id !== sug.suggestion_id)
      );
      setSuccessMessage("Task added successfully");
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err.message || "Failed to add task");
    }
  };

  const handleAddToCalendar = async (sug) => {
    if (!token) return;
    try {
      const deadline = sug.due_date
        ? new Date(sug.due_date).toISOString()
        : null;
      const res = await fetch(`${API_BASE}/tasks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: sug.title,
          description: sug.description || "",
          priority: sug.urgency || "medium",
          deadline: deadline,
          estimated_hours: 1,
          tags: ["calendar"],
        }),
      });

      if (!res.ok) throw new Error("Failed to schedule event");

      await dismissGmailSuggestion(token, sug.suggestion_id);
      setSuggestions((prev) =>
        prev.filter((s) => s.suggestion_id !== sug.suggestion_id)
      );
      setSuccessMessage("Event added to calendar successfully");
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err.message || "Failed to schedule event");
    }
  };

  const handleDismissSuggestion = async (suggestionId) => {
    if (!token) return;
    try {
      await dismissGmailSuggestion(token, suggestionId);
      setSuggestions((prev) =>
        prev.filter((s) => s.suggestion_id !== suggestionId)
      );
      setSuccessMessage("Suggestion dismissed");
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError("Failed to dismiss suggestion");
    }
  };

  const groupedItems = groupItemsByDate(events, tasks, latestPlan);
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="p-6 md:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold text-slate-900">Calendar</h2>
            <p className="text-sm text-slate-600 mt-1">
              {loading
                ? "Loading…"
                : isConnected
                  ? `${events.length} event${events.length !== 1 ? "s" : ""}${tasks.length > 0 ? `, ${tasks.length} task deadline${tasks.length !== 1 ? "s" : ""}` : ""}`
                  : "Connect your Google Calendar to get started"}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {isConnected && !loading && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleDisconnect}
                disabled={syncing}
                className="gap-1.5 border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 hover:border-red-300 transition-colors"
              >
                <Unplug className="w-3.5 h-3.5" />
                Disconnect
              </Button>
            )}

            <Button
              variant={isConnected ? "outline" : "default"}
              onClick={handleSync}
              disabled={syncing || loading}
              className={
                isConnected
                  ? "gap-2 border-slate-300 hover:bg-slate-50"
                  : "gap-2 bg-slate-900 text-white hover:bg-slate-800"
              }
            >
              {syncing ? (
                <Loader className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              {syncing
                ? isConnected
                  ? "Refreshing…"
                  : "Connecting…"
                : isConnected
                  ? "Refresh"
                  : "Sync Google Calendar"}
            </Button>
          </div>
        </div>

        {successMessage && (
          <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-sm">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            {successMessage}
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {!loading && !isConnected && (
          <Card className="border-slate-200/50 bg-gradient-to-br from-slate-50 to-slate-100/50 p-10">
            <div className="flex flex-col items-center justify-center text-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center">
                <Calendar className="w-8 h-8 text-slate-400" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 text-lg">
                  No calendar connected
                </h3>
                <p className="text-slate-500 text-sm mt-1 max-w-xs">
                  Click{" "}
                  <span className="font-medium text-slate-700">
                    Sync Google Calendar
                  </span>{" "}
                  to connect your account and see your events here.
                </p>
              </div>
              <Button
                onClick={handleSync}
                disabled={syncing}
                className="gap-2 bg-slate-900 text-white hover:bg-slate-800 mt-2"
              >
                {syncing ? (
                  <Loader className="w-4 h-4 animate-spin" />
                ) : (
                  <Calendar className="w-4 h-4" />
                )}
                {syncing ? "Connecting…" : "Connect Google Calendar"}
              </Button>
            </div>
          </Card>
        )}

        {loading && (
          <div className="space-y-6">
            <SkeletonSection />
            <SkeletonSection />
          </div>
        )}

        {!loading && isConnected && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              {groupedItems.length === 0 ? (
                <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm p-8">
                  <div className="flex flex-col items-center text-center gap-3">
                    <CalendarX className="w-10 h-10 text-slate-300" />
                    <div>
                      <p className="font-medium text-slate-700">
                        No upcoming events or task deadlines
                      </p>
                      <p className="text-sm text-slate-400 mt-0.5">
                        Your next 30 days look free.
                      </p>
                    </div>
                  </div>
                </Card>
              ) : (
                groupedItems.map(({ label, dateKey, items }) => (
                  <div key={dateKey} className="space-y-3">
                    <div>
                      <h3 className="text-lg font-semibold text-slate-900">
                        {label}
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {items.filter((i) => i.itemType === "event").length > 0 &&
                          `${items.filter((i) => i.itemType === "event").length} event${items.filter((i) => i.itemType === "event").length !== 1 ? "s" : ""}`}
                        {items.filter((i) => i.itemType === "event").length > 0 &&
                          (items.filter((i) => i.itemType === "task").length > 0 || items.filter((i) => i.itemType === "scheduled_subtask").length > 0) && " · "}
                        {items.filter((i) => i.itemType === "task").length > 0 &&
                          `${items.filter((i) => i.itemType === "task").length} task deadline${items.filter((i) => i.itemType === "task").length !== 1 ? "s" : ""}`}
                        {items.filter((i) => i.itemType === "task").length > 0 &&
                          items.filter((i) => i.itemType === "scheduled_subtask").length > 0 && " · "}
                        {items.filter((i) => i.itemType === "scheduled_subtask").length > 0 &&
                          `${items.filter((i) => i.itemType === "scheduled_subtask").length} work session${items.filter((i) => i.itemType === "scheduled_subtask").length !== 1 ? "s" : ""}`}
                      </p>
                    </div>

                    <div className="space-y-2">
                      {items.map((item) => {
                        if (item.itemType === "task") {
                          const taskSubtasks = latestPlan?.task_plans?.find((tp) => tp.task_id === item.id)?.subtasks || [];
                          return <TaskCard key={`task-${item.id}`} task={item} subtasks={taskSubtasks} />;
                        } else if (item.itemType === "scheduled_subtask") {
                          return (
                            <Card key={`subtask-${item.id}`} className="border-indigo-100 bg-indigo-50/40 hover:bg-indigo-50/70 transition-all duration-200 p-4">
                              <div className="flex items-start gap-3">
                                <CheckCircle2 className={`w-4 h-4 mt-0.5 shrink-0 ${item.status === 'completed' ? 'text-indigo-400' : 'text-indigo-600'}`} />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <h4 className={`font-semibold text-slate-900 truncate ${item.status === 'completed' ? 'line-through text-slate-400' : ''}`}>
                                      {item.title}
                                    </h4>
                                    <Badge className="text-[10px] bg-indigo-100 text-indigo-700 border border-indigo-200 shrink-0">
                                      Schedule Block
                                    </Badge>
                                    {item.priority && (
                                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded border border-indigo-100 bg-indigo-50 text-indigo-700 shrink-0 uppercase">
                                        {item.priority}
                                      </span>
                                    )}
                                  </div>
                                  {item.description && (
                                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">{item.description}</p>
                                  )}
                                  <div className="flex items-center gap-3 mt-2 text-sm text-slate-600">
                                    <span className="flex items-center gap-1">
                                      <Clock className="w-3.5 h-3.5 shrink-0" />
                                      {formatTime(item.start)} – {formatTime(item.end)}
                                    </span>
                                    <span className="text-slate-400 text-xs">
                                      {formatDuration(item.start, item.end)}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </Card>
                          );
                        } else {
                          const eventSubtasks = latestPlan?.task_plans?.find((tp) => tp.task_id === "event_" + item.event_id)?.subtasks || [];
                          return <EventCard key={item.event_id} event={item} subtasks={eventSubtasks} />;
                        }
                      })}
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="space-y-4">
              <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                      <Clock className="w-4 h-4 text-emerald-600" />
                      Free Time Today
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">{today}</p>
                  </div>
                  {freeSlots && freeSlots.total_free_minutes > 0 && (
                    <Badge
                      variant="outline"
                      className="text-emerald-700 border-emerald-200 bg-emerald-50 text-xs font-semibold"
                    >
                      {formatFreeMinutes(freeSlots.total_free_minutes)} total
                    </Badge>
                  )}
                </div>

                {!freeSlots ? (
                  <div className="space-y-2 animate-pulse">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-10 bg-slate-100 rounded-lg" />
                    ))}
                  </div>
                ) : freeSlots.free_slots.length === 0 ? (
                  <div className="text-center py-6">
                    <p className="text-sm text-slate-500">
                      No free slots today
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Looks like a fully packed day!
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {freeSlots.free_slots.map((slot, i) => (
                      <FreeSlotCard key={i} slot={slot} />
                    ))}
                  </div>
                )}
              </Card>

              {isGmailConnected && (
                <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4 text-blue-600" />
                      <h3 className="font-semibold text-slate-900">
                        Gmail Suggestions
                      </h3>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={() => handleGmailSync(false)}
                        disabled={isGmailSyncing}
                        className="text-slate-500 hover:text-slate-900"
                        title="Sync Gmail (Incremental)"
                      >
                        {isGmailSyncing ? (
                          <Loader className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="w-3.5 h-3.5" />
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="xs"
                        onClick={() => handleGmailSync(true)}
                        disabled={isGmailSyncing}
                        className="text-xs text-blue-600 border-blue-200 hover:bg-blue-50/50"
                      >
                        Deep Sync
                      </Button>
                    </div>
                  </div>

                  <Separator />

                  {suggestions.length > 0 ? (
                    <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                      {suggestions.map((s) => (
                        <div
                          key={s.suggestion_id}
                          className="p-3 rounded-lg border border-slate-200/50 bg-slate-50/50 space-y-2"
                        >
                          <div>
                            <p className="font-semibold text-slate-900 text-xs">
                              {s.title}
                            </p>
                            {s.description && (
                              <p className="text-[11px] text-slate-600 mt-0.5 leading-relaxed">
                                {s.description}
                              </p>
                            )}
                          </div>

                          <div className="flex flex-wrap gap-1">
                            {s.due_date && (
                              <span className="text-[9px] font-medium bg-white border border-slate-200 text-slate-700 px-1 rounded">
                                Due: {s.due_date}
                              </span>
                            )}
                            {s.urgency && (
                              <span
                                className={`text-[9px] font-semibold px-1 rounded uppercase ${s.urgency === "high"
                                  ? "bg-red-50 text-red-700 border border-red-100"
                                  : s.urgency === "medium"
                                    ? "bg-amber-50 text-amber-700 border border-amber-100"
                                    : "bg-emerald-50 text-emerald-700 border border-emerald-100"
                                  }`}
                              >
                                {s.urgency}
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-1.5 pt-1">
                            <Button
                              size="xs"
                              variant="default"
                              onClick={() => handleAddToCalendar(s)}
                              className="text-[10px] bg-slate-950 text-white hover:bg-slate-800"
                            >
                              Add to Calendar
                            </Button>
                            <Button
                              size="xs"
                              variant="outline"
                              onClick={() => handleAddTask(s)}
                              className="text-[10px] border-slate-300 text-slate-700 hover:bg-white"
                            >
                              Add to Task
                            </Button>
                            <Button
                              size="icon-xs"
                              variant="ghost"
                              onClick={() =>
                                handleDismissSuggestion(s.suggestion_id)
                              }
                              className="ml-auto text-slate-400 hover:text-red-600 hover:bg-red-50"
                            >
                              <Trash2 className="w-3 h-3" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-6 space-y-3">
                      <div className="space-y-1">
                        <CheckCircle2 className="w-6 h-6 text-emerald-500 mx-auto" />
                        <p className="text-xs font-semibold text-slate-800">
                          All caught up
                        </p>
                        <p className="text-[10px] text-slate-500">
                          No actionable tasks in emails.
                        </p>
                      </div>
                      <Button
                        size="xs"
                        onClick={() => handleGmailSync(false)}
                        disabled={isGmailSyncing}
                        className="mx-auto gap-1 bg-slate-900 text-white hover:bg-slate-800 text-[10px]"
                      >
                        {isGmailSyncing ? (
                          <Loader className="w-3 h-3 animate-spin" />
                        ) : (
                          <RefreshCw className="w-3 h-3" />
                        )}
                        Sync Gmail
                      </Button>
                    </div>
                  )}
                </Card>
              )}

              <Card className="border-slate-200/50 bg-gradient-to-br from-slate-50 to-slate-100/50 p-4">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs font-medium text-slate-700">
                    Google Calendar connected
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1 pl-4">
                  Events sync automatically on refresh
                </p>
              </Card>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}