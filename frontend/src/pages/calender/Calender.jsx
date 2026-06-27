// src/pages/Calendar.jsx

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Calendar, RefreshCw, Clock } from 'lucide-react';

const SAMPLE_EVENTS = [
  { id: 1, title: 'Team Standup', time: '09:00 AM', date: 'Today', duration: '30 min' },
  { id: 2, title: 'Project Review', time: '02:00 PM', date: 'Today', duration: '1 hour' },
  { id: 3, title: 'Client Call', time: '03:30 PM', date: 'Today', duration: '45 min' },
  { id: 4, title: 'Weekly Planning', time: '10:00 AM', date: 'Tomorrow', duration: '1 hour' },
];

export default function CalendarPage() {
  const getDayName = (dayOffset) => {
    const date = new Date();
    date.setDate(date.getDate() + dayOffset);
    return date.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
  };

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="p-6 md:p-8 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold text-slate-900">Calendar</h2>
            <p className="text-sm text-slate-600 mt-1">
              {SAMPLE_EVENTS.length} events scheduled
            </p>
          </div>

          <Button
            variant="outline"
            className="gap-2 border-slate-300"
          >
            <RefreshCw className="w-4 h-4" />
            Sync Google Calendar
          </Button>
        </div>

        {/* Calendar Grid Placeholder */}
        <Card className="border-slate-200/50 bg-gradient-to-br from-slate-50 to-slate-100/50 p-8">
          <div className="aspect-video flex flex-col items-center justify-center">
            <Calendar className="w-16 h-16 text-slate-300 mb-4" />
            <p className="text-slate-600 text-center max-w-sm">
              Click "Sync Google Calendar" to connect your calendar and view events here.
            </p>
          </div>
        </Card>

        {/* Events List */}
        <div className="space-y-6">
          {/* Today's Events */}
          <div className="space-y-3">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">
                {getDayName(0)}
              </h3>
              <p className="text-sm text-slate-500">3 events</p>
            </div>

            <div className="space-y-2">
              {SAMPLE_EVENTS.filter((e) => e.date === 'Today').map((event) => (
                <Card
                  key={event.id}
                  className="border-slate-200/50 bg-white/70 backdrop-blur-sm p-4 hover:bg-white/90 transition-colors cursor-pointer"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-semibold text-slate-900">
                        {event.title}
                      </h4>
                      <div className="flex items-center gap-4 mt-2 text-sm text-slate-600">
                        <div className="flex items-center gap-1">
                          <Clock className="w-4 h-4" />
                          {event.time}
                        </div>
                        <div>{event.duration}</div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                    >
                      Details
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          {/* Tomorrow's Events */}
          <div className="space-y-3">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">
                {getDayName(1)}
              </h3>
              <p className="text-sm text-slate-500">1 event</p>
            </div>

            <div className="space-y-2">
              {SAMPLE_EVENTS.filter((e) => e.date === 'Tomorrow').map((event) => (
                <Card
                  key={event.id}
                  className="border-slate-200/50 bg-white/70 backdrop-blur-sm p-4 hover:bg-white/90 transition-colors cursor-pointer"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-semibold text-slate-900">
                        {event.title}
                      </h4>
                      <div className="flex items-center gap-4 mt-2 text-sm text-slate-600">
                        <div className="flex items-center gap-1">
                          <Clock className="w-4 h-4" />
                          {event.time}
                        </div>
                        <div>{event.duration}</div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                    >
                      Details
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}