
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Calendar,
  CheckSquare2,
  Plus,
  Zap,
  Clock,
  Target,
  Loader
} from 'lucide-react';
import { generateSubtasks } from '@/services/planningService';

const backend_api='http://localhost:8000/api';

export default function Dashboard() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [planGenerating, setPlanGenerating] = useState(false);

  const handleGenerateSubtasks = async () => {
    setPlanGenerating(true);
    setError(null);
    try {
      await generateSubtasks(token);
      navigate('/plan');
    } catch (err) {
      setError(err.message || 'Failed to generate subtasks');
    } finally {
      setPlanGenerating(false);
    }
  };

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${backend_api}/tasks`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error('Failed to fetch tasks');
        }

        const data = await response.json();
        setTasks(data.tasks || []);
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error('Error:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchTasks();
  }, [token]);

  const completedCount = tasks.filter((t) => t.status === 'completed').length;
  const pendingCount = tasks.filter((t) => t.status !== 'completed').length;
  const todayTasks = tasks.slice(0, 10);  //first 10 tasks


  return (
    <main className="flex-1 overflow-y-auto">
      <div className="p-6 md:p-8 space-y-8">
        {/* Welcome Section */}
        <div>
          <h2 className="text-4xl font-bold text-slate-900 mb-2">
            Good Morning, Yukta
          </h2>
          <p className="text-slate-600">
            {pendingCount} tasks due. Let's make it productive.
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex justify-center py-12">
            <Loader className="w-8 h-8 text-slate-400 animate-spin" />
          </div>
        )}

        {!loading && (
          <>
            {/* Grid Layout */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Today Overview Card */}
              <Card className="md:col-span-2 border-slate-200/50 bg-white/70 backdrop-blur-sm p-6">
                <div className="space-y-6">
                  {/* Date Header */}
                  <div>
                    <p className="text-sm font-medium text-slate-500 uppercase tracking-wider">
                      Today
                    </p>
                    <h3 className="text-2xl font-bold text-slate-900 mt-1">
                      {today}
                    </h3>
                  </div>

                  {/* Task Summary */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/50">
                      <p className="text-2xl font-bold text-slate-900">{tasks.length}</p>
                      <p className="text-xs text-slate-600 mt-1">Total Tasks</p>
                    </div>
                    <div className="p-4 rounded-lg bg-green-50 border border-green-200/50">
                      <p className="text-2xl font-bold text-green-700">{completedCount}</p>
                      <p className="text-xs text-green-600 mt-1">Completed</p>
                    </div>
                    <div className="p-4 rounded-lg bg-blue-50 border border-blue-200/50">
                      <p className="text-2xl font-bold text-blue-700">{pendingCount}</p>
                      <p className="text-xs text-blue-600 mt-1">Pending</p>
                    </div>
                  </div>

                  {/* Next Event Preview */}
                  <div className="p-4 rounded-lg bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200/50">
                    <div className="flex items-start gap-3">
                      <Calendar className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-purple-900">
                          Next Event
                        </p>
                        <p className="text-xs text-purple-700 mt-1">
                          Sync Google Calendar to see your events
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Quick Actions Card */}
              <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm p-6">
                <div className="space-y-3">
                  <p className="text-sm font-medium text-slate-500 uppercase tracking-wider">
                    Quick Actions
                  </p>

                  <Button
                    onClick={() => navigate('/tasks')}
                    className="w-full justify-start gap-2 bg-slate-900 text-white hover:bg-slate-800"
                  >
                    <Plus className="w-4 h-4" />
                    Add Task
                  </Button>

                  <Button
                    onClick={() => navigate('/calendar')}
                    variant="outline"
                    className="w-full justify-start gap-2 border-slate-300"
                  >
                    <Calendar className="w-4 h-4" />
                    Open Calendar
                  </Button>

                  <Button
                    onClick={handleGenerateSubtasks}
                    disabled={planGenerating || tasks.filter((t) => t.status !== 'completed').length === 0}
                    variant="outline"
                    className="w-full justify-start gap-2 border-slate-300"
                  >
                    {planGenerating ? (
                      <Loader className="w-4 h-4 animate-spin text-violet-600" />
                    ) : (
                      <Zap className="w-4 h-4 text-violet-600" />
                    )}
                    {planGenerating ? 'Generating Subtasks...' : 'Generate Subtasks'}
                  </Button>
                </div>
              </Card>
            </div>


            {/* Upcoming Tasks Preview */}
            <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm p-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckSquare2 className="w-5 h-5 text-slate-600" />
                    <h3 className="font-semibold text-slate-900">Today's Tasks</h3>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate('/tasks')}
                    className="text-slate-600 hover:text-slate-900"
                  >
                    View All
                  </Button>
                </div>

                {/* Task List */}
                <div className="space-y-2">
                  {todayTasks.length === 0 ? (
                    <p className="text-sm text-slate-500 text-center py-4">
                      No tasks yet. Create one to get started!
                    </p>
                  ) : (
                    todayTasks.map((task) => (
                      <div
                        key={task.id}
                        className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={task.status === 'completed'}
                          className="w-4 h-4 rounded border-slate-300"
                        />
                        <span
                          className={`flex-1 text-sm ${
                            task.status === 'completed'
                              ? 'text-slate-400 line-through'
                              : 'text-slate-700'
                          }`}
                        >
                          {task.title}
                        </span>
                        <span
                          className={`text-xs font-medium px-2 py-1 rounded ${
                            task.priority === 'high'
                              ? 'bg-red-100 text-red-700'
                              : task.priority === 'medium'
                              ? 'bg-yellow-100 text-yellow-700'
                              : 'bg-green-100 text-green-700'
                          }`}
                        >
                          {task.priority}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </Card>
          </>
        )}
      </div>
    </main>
  );
}

