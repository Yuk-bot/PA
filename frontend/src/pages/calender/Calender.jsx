

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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
} from 'lucide-react';
import {
  connectCalendar,
  checkCalendarStatus,
  getEvents,
  getFreeSlots,
  disconnectCalendar,
} from '@/services/calendarService';


function formatTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
}

function formatDuration(startStr, endStr) {
  if (!startStr || !endStr) return '';
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


function groupEventsByDate(events) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);

  const groups = {};

  for (const event of events) {
    const d = new Date(event.start);
    d.setHours(0, 0, 0, 0);
    const key = d.toISOString();

    if (!groups[key]) {
      let label;
      if (d.getTime() === today.getTime()) {
        label = 'Today';
      } else if (d.getTime() === tomorrow.getTime()) {
        label = 'Tomorrow';
      } else {
        label = d.toLocaleDateString('en-US', {
          weekday: 'long',
          month: 'long',
          day: 'numeric',
        });
      }
      groups[key] = { label, dateKey: key, events: [] };
    }

    groups[key].events.push(event);
  }

  return Object.values(groups).sort((a, b) => a.dateKey.localeCompare(b.dateKey));
}

function hasMeetingLink(event) {
  const desc = (event.description || '').toLowerCase();
  return (
    desc.includes('meet.google.com') ||
    desc.includes('zoom.us') ||
    desc.includes('teams.microsoft')
  );
}

function getMeetingLink(event) {
  const desc = event.description || '';
  const match = desc.match(/https?:\/\/[^\s<"]+/);
  return match ? match[0] : null;
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

function EventCard({ event }) {
  const [expanded, setExpanded] = useState(false);
  const meetingLink = getMeetingLink(event);

  return (
    <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm hover:bg-white/90 transition-all duration-200 cursor-pointer overflow-hidden">
      <div className="p-4" onClick={() => setExpanded((p) => !p)}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-semibold text-slate-900 truncate">{event.title}</h4>
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
                  {event.attendees.length} attendee{event.attendees.length !== 1 ? 's' : ''}
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
              {expanded ? 'Less' : 'Details'}
            </Button>
          </div>
        </div>

        {/* Expanded details */}
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
  const token = localStorage.getItem('token');
  const [searchParams, setSearchParams] = useSearchParams();

  // State
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(true);         // initial load
  const [syncing, setSyncing] = useState(false);         // sync/refresh button
  const [events, setEvents] = useState([]);
  const [freeSlots, setFreeSlots] = useState(null);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Read URL params after OAuth redirect
  const oauthConnected = searchParams.get('calendar_connected');
  const oauthError = searchParams.get('error');
  const oauthEmail = searchParams.get('email');

  // ── Data fetching ────────────────────────────────────────────────────────

  const loadCalendarData = useCallback(async () => {
    if (!token) return;
    setError(null);

    try {
      // Check connection + fetch events in parallel
      const [eventsResult, slotsResult] = await Promise.all([
        getEvents(token, 30, 30),
        getFreeSlots(token),
      ]);

      if (!eventsResult.connected) {
        setIsConnected(false);
        setEvents([]);
        setFreeSlots(null);
        return;
      }

      setIsConnected(true);
      setEvents(eventsResult.events);
      setFreeSlots(slotsResult.connected ? slotsResult : null);
    } catch (err) {
      setError(err.message || 'Failed to load calendar data');
    }
  }, [token]);

  // Initial load
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await loadCalendarData();
      setLoading(false);
    };
    init();
  }, [loadCalendarData]);

  // Handle OAuth redirect params
  useEffect(() => {
    if (oauthConnected === 'true') {
      setSuccessMessage(
        oauthEmail
          ? `Connected as ${oauthEmail}`
          : 'Google Calendar connected successfully!'
      );
      // Remove query params and reload data
      setSearchParams({}, { replace: true });
      setIsConnected(true);
      loadCalendarData();

      const t = setTimeout(() => setSuccessMessage(null), 5000);
      return () => clearTimeout(t);
    }

    if (oauthError) {
      const readable =
        oauthError === 'missing_code'
          ? 'OAuth was cancelled or the code was missing.'
          : oauthError === 'missing_state'
          ? 'OAuth state was invalid. Please try again.'
          : `OAuth error: ${oauthError}`;
      setError(readable);
      setSearchParams({}, { replace: true });
    }
  }, [oauthConnected, oauthError, oauthEmail, setSearchParams, loadCalendarData]);

  

  const handleSync = async () => {
    if (!token) return;

    if (!isConnected) {
      // Not connected → initiate OAuth
      setSyncing(true);
      setError(null);
      try {
        const { authorization_url } = await connectCalendar(token);
        // Redirect the browser to Google's consent screen
        window.location.href = authorization_url;
      } catch (err) {
        setError(err.message || 'Failed to start Google Calendar connection');
        setSyncing(false);
      }
    } else {
      // Already connected → refresh data
      setSyncing(true);
      setError(null);
      try {
        await loadCalendarData();
        setSuccessMessage('Calendar refreshed');
        setTimeout(() => setSuccessMessage(null), 3000);
      } catch (err) {
        setError(err.message || 'Failed to refresh calendar');
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
      setSuccessMessage('Calendar disconnected');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err.message || 'Failed to disconnect calendar');
    } finally {
      setSyncing(false);
    }
  };

  

  const groupedEvents = groupEventsByDate(events);
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="p-6 md:p-8 space-y-6">

        {/* ── Header ── */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold text-slate-900">Calendar</h2>
            <p className="text-sm text-slate-600 mt-1">
              {loading
                ? 'Loading…'
                : isConnected
                ? `${events.length} upcoming event${events.length !== 1 ? 's' : ''}`
                : 'Connect your Google Calendar to get started'}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Disconnect button (only when connected) */}
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

            {/* Sync / Connect button */}
            <Button
              variant={isConnected ? 'outline' : 'default'}
              onClick={handleSync}
              disabled={syncing || loading}
              className={
                isConnected
                  ? 'gap-2 border-slate-300 hover:bg-slate-50'
                  : 'gap-2 bg-slate-900 text-white hover:bg-slate-800'
              }
            >
              {syncing ? (
                <Loader className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              {syncing
                ? isConnected
                  ? 'Refreshing…'
                  : 'Connecting…'
                : isConnected
                ? 'Refresh'
                : 'Sync Google Calendar'}
            </Button>
          </div>
        </div>

        {/* ── Feedback banners ── */}
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

        {/* ── Not connected empty state ── */}
        {!loading && !isConnected && (
          <Card className="border-slate-200/50 bg-gradient-to-br from-slate-50 to-slate-100/50 p-10">
            <div className="flex flex-col items-center justify-center text-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center">
                <Calendar className="w-8 h-8 text-slate-400" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 text-lg">No calendar connected</h3>
                <p className="text-slate-500 text-sm mt-1 max-w-xs">
                  Click <span className="font-medium text-slate-700">Sync Google Calendar</span> to
                  connect your account and see your events here.
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
                {syncing ? 'Connecting…' : 'Connect Google Calendar'}
              </Button>
            </div>
          </Card>
        )}

        {/* ── Loading skeletons ── */}
        {loading && (
          <div className="space-y-6">
            <SkeletonSection />
            <SkeletonSection />
          </div>
        )}

        {/* ── Connected: show events + free slots ── */}
        {!loading && isConnected && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Events (left, 2/3 width on large screens) */}
            <div className="lg:col-span-2 space-y-6">
              {groupedEvents.length === 0 ? (
                <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm p-8">
                  <div className="flex flex-col items-center text-center gap-3">
                    <CalendarX className="w-10 h-10 text-slate-300" />
                    <div>
                      <p className="font-medium text-slate-700">No upcoming events</p>
                      <p className="text-sm text-slate-400 mt-0.5">
                        Your next 30 days look free.
                      </p>
                    </div>
                  </div>
                </Card>
              ) : (
                groupedEvents.map(({ label, dateKey, events: dayEvents }) => (
                  <div key={dateKey} className="space-y-3">
                    {/* Date header */}
                    <div>
                      <h3 className="text-lg font-semibold text-slate-900">{label}</h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {dayEvents.length} event{dayEvents.length !== 1 ? 's' : ''}
                      </p>
                    </div>

                    <div className="space-y-2">
                      {dayEvents.map((event) => (
                        <EventCard key={event.event_id} event={event} />
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Free Slots sidebar (right, 1/3 width on large screens) */}
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

                {/* Slots list */}
                {!freeSlots ? (
                  // Skeleton for slots
                  <div className="space-y-2 animate-pulse">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-10 bg-slate-100 rounded-lg" />
                    ))}
                  </div>
                ) : freeSlots.free_slots.length === 0 ? (
                  <div className="text-center py-6">
                    <p className="text-sm text-slate-500">No free slots today</p>
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

              {/* Connection status card */}
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