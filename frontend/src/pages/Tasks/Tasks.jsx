

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { CheckSquare2, Plus, Filter, Trash2, Loader, Zap, Pencil, ChevronDown, ChevronUp } from 'lucide-react';
import { generateSubtasks, getLatestPlan } from '@/services/planningService';

import { API_BASE } from '@/services/apiConfig';

export default function Tasks() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState('all');
  const [newTask, setNewTask] = useState('');
  const [newDeadline, setNewDeadline] = useState('');
  const [newPriority, setNewPriority] = useState('medium');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [planGenerating, setPlanGenerating] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [editDeadline, setEditDeadline] = useState('');
  const [editPriority, setEditPriority] = useState('medium');
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [latestPlan, setLatestPlan] = useState(null);
  const [expandedTasks, setExpandedTasks] = useState({});

  const handleStartEdit = (task) => {
    setEditingTask(task);
    setEditTitle(task.title);
    setEditDeadline(task.deadline ? new Date(task.deadline).toISOString().slice(0, 16) : '');
    setEditPriority(task.priority);
    setEditDialogOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!editTitle.trim()) return;
    try {
      const response = await fetch(`${API_BASE}/tasks/${editingTask.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: editTitle.trim(),
          deadline: editDeadline ? new Date(editDeadline).toISOString() : null,
          priority: editPriority,
        }),
      });
      if (response.ok) {
        setTasks(
          tasks.map((t) =>
            t.id === editingTask.id
              ? { ...t, title: editTitle.trim(), deadline: editDeadline ? new Date(editDeadline).toISOString() : '', priority: editPriority }
              : t
          )
        );
        setEditDialogOpen(false);
        setEditingTask(null);
      }
    } catch (err) {
      console.error('Error updating task:', err);
    }
  };

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

  // Get token from localStorage
  const token = localStorage.getItem('token');

//fetching from backend
  const fetchTasks = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/tasks`, {
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
      console.error('Error fetching tasks:', err);
    } finally {
      setLoading(false);
    }
  };
  const fetchLatestPlan = async () => {
    try {
      const p = await getLatestPlan(token);
      setLatestPlan(p);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchTasks();
    fetchLatestPlan();
  }, []);



  const handleToggleTask = async (id) => {
    const task = tasks.find((t) => t.id === id);
    const newStatus = task.status === 'completed' ? 'todo' : 'completed';

    try {
      const response = await fetch(`${API_BASE}/tasks/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (response.ok) {
        setTasks(
          tasks.map((t) =>
            t.id === id ? { ...t, status: newStatus } : t
          )
        );
      }
    } catch (err) {
      console.error('Error updating task:', err);
    }
  };

  const handleDeleteTask = async (id) => {
    try {
      const response = await fetch(`${API_BASE}/tasks/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setTasks(tasks.filter((t) => t.id !== id));
      }
    } catch (err) {
      console.error('Error deleting task:', err);
    }
  };

  const handleAddTask = async () => {
    if (!newTask.trim()) return;

    try {
      const body = {
        title: newTask.trim(),
        description: '',
        priority: newPriority,
        estimated_hours: 1,
        tags: [],
      };

      // Only include deadline if the user set one
      if (newDeadline) {
        body.deadline = new Date(newDeadline).toISOString();
      }

      const response = await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });

      if (response.ok) {
        setNewTask('');
        setNewDeadline('');
        setNewPriority('medium');
        setDialogOpen(false);
        fetchTasks(); // Refresh list
      } else {
        const err = await response.json().catch(() => ({}));
        console.error('Add task failed:', err);
      }
    } catch (err) {
      console.error('Error adding task:', err);
    }
  };

 //filter and display

  const filteredTasks = tasks.filter((task) => {
    if (filter === 'completed') return task.status === 'completed';
    if (filter === 'pending') return task.status !== 'completed';
    return true;
  });

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-700';
      case 'medium':
        return 'bg-yellow-100 text-yellow-700';
      case 'low':
        return 'bg-green-100 text-green-700';
      default:
        return 'bg-slate-100 text-slate-700';
    }
  };



  return (
    <main className="flex-1 overflow-y-auto">
      <div className="p-6 md:p-8 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold text-slate-900">My Tasks</h2>
            <p className="text-sm text-slate-600 mt-1">
              {tasks.length} total • {tasks.filter((t) => t.status !== 'completed').length} pending
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              onClick={handleGenerateSubtasks}
              disabled={planGenerating || tasks.filter((t) => t.status !== 'completed').length === 0}
              className="gap-2 bg-violet-600 hover:bg-violet-700 text-white"
            >
              {planGenerating ? (
                <Loader className="w-4 h-4 animate-spin" />
              ) : (
                <Zap className="w-4 h-4" />
              )}
              {planGenerating ? 'Generating Subtasks...' : 'Generate Subtasks'}
            </Button>

            {/* Add Task Dialog */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button className="gap-2 bg-slate-900 text-white hover:bg-slate-800">
                  <Plus className="w-4 h-4" />
                  Add Task
                </Button>
              </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Task</DialogTitle>
                <DialogDescription>Add a new task to your list</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 pt-1">
                {/* Title */}
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-slate-700">Title <span className="text-red-500">*</span></label>
                  <Input
                    placeholder="e.g. Finish project report"
                    value={newTask}
                    onChange={(e) => setNewTask(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAddTask()}
                    autoFocus
                  />
                </div>

                {/* Priority */}
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-slate-700">Priority</label>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        className={`w-full justify-between border-slate-300 font-normal ${
                          newPriority === 'high' ? 'text-red-600' :
                          newPriority === 'medium' ? 'text-yellow-600' : 'text-green-600'
                        }`}
                      >
                        {newPriority.charAt(0).toUpperCase() + newPriority.slice(1)}
                        <Filter className="w-3.5 h-3.5 opacity-50" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-full">
                      <DropdownMenuItem onClick={() => setNewPriority('high')} className="text-red-600">High</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setNewPriority('medium')} className="text-yellow-600">Medium</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setNewPriority('low')} className="text-green-600">Low</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                {/* Deadline (optional) */}
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-slate-700">
                    Deadline <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <Input
                    type="datetime-local"
                    value={newDeadline}
                    onChange={(e) => setNewDeadline(e.target.value)}
                    className="border-slate-300"
                    min={new Date(new Date() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16)}
                  />
                </div>

                <Button
                  onClick={handleAddTask}
                  className="w-full bg-slate-900 text-white hover:bg-slate-800"
                  disabled={!newTask.trim()}
                >
                  Add Task
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

        {/* Filters */}
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="gap-2 border-slate-300"
              >
                <Filter className="w-4 h-4" />
                Filter: {filter === 'all' ? 'All' : filter === 'completed' ? 'Completed' : 'Pending'}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => setFilter('all')}>
                All Tasks
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setFilter('pending')}>
                Pending
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setFilter('completed')}>
                Completed
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Task List */}
        <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm overflow-hidden">
          {loading ? (
            <div className="p-12 flex items-center justify-center">
              <Loader className="w-6 h-6 text-slate-400 animate-spin" />
            </div>
          ) : filteredTasks.length === 0 ? (
            <div className="p-12 text-center">
              <CheckSquare2 className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-600">
                {filter === 'completed'
                  ? 'No completed tasks yet'
                  : filter === 'pending'
                  ? 'No pending tasks. Great job!'
                  : 'No tasks yet. Create one to get started.'}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-200/50">
              {filteredTasks.map((task) => {
                const subtasks = latestPlan?.task_plans?.find((tp) => tp.task_id === task.id)?.subtasks || [];
                const isExpanded = !!expandedTasks[task.id];
                return (
                  <div
                    key={task.id}
                    className="p-4 hover:bg-slate-50/50 transition-colors flex items-start gap-4 group"
                  >
                  <input
                    type="checkbox"
                    checked={task.status === 'completed'}
                    onChange={() => handleToggleTask(task.id)}
                    className="w-5 h-5 rounded border-slate-300 cursor-pointer"
                  />

                  <div className="flex-1 min-w-0">
                    <p
                      className={`font-medium ${
                        task.status === 'completed'
                          ? 'text-slate-400 line-through'
                          : 'text-slate-900'
                      }`}
                    >
                      {task.title}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      {task.deadline
                        ? new Date(task.deadline).toLocaleString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                            hour: 'numeric',
                            minute: '2-digit',
                            hour12: true,
                          })
                        : 'No date'}
                    </p>
                    {subtasks.length > 0 && (
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedTasks(prev => ({ ...prev, [task.id]: !prev[task.id] }));
                        }}
                        className="text-xs text-violet-600 hover:text-violet-700 p-0 h-auto font-medium mt-1.5 select-none flex items-center gap-1"
                      >
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        {isExpanded ? 'Hide Subtasks' : `Show Subtasks (${subtasks.length})`}
                      </Button>
                    )}
                    {isExpanded && subtasks.length > 0 && (
                      <div className="mt-2 pl-3 border-l-2 border-violet-100 space-y-1.5 animate-fadeIn">
                        {subtasks.map((s) => (
                          <div key={s.subtask_id} className="flex items-center gap-2 text-xs text-slate-600">
                            <div className={`w-1 h-1 rounded-full ${s.status === 'completed' ? 'bg-slate-300' : 'bg-violet-400'}`} />
                            <span className={s.status === 'completed' ? 'line-through text-slate-400' : ''}>
                              {s.title}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <span
                    className={`text-xs font-medium px-2.5 py-1 rounded whitespace-nowrap ${getPriorityColor(
                      task.priority
                    )}`}
                  >
                    {task.priority}
                  </span>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleStartEdit(task)}
                    className="text-slate-400 hover:text-slate-600 hover:bg-slate-100 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Pencil className="w-4 h-4" />
                  </Button>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteTask(task.id)}
                    className="text-slate-400 hover:text-red-600 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>

      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Task</DialogTitle>
            <DialogDescription>Modify task details</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-1">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Title <span className="text-red-500">*</span></label>
              <Input
                placeholder="e.g. Finish project report"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSaveEdit()}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Priority</label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    className={`w-full justify-between border-slate-300 font-normal ${
                      editPriority === 'high' ? 'text-red-600' :
                      editPriority === 'medium' ? 'text-yellow-600' : 'text-green-600'
                    }`}
                  >
                    {editPriority.charAt(0).toUpperCase() + editPriority.slice(1)}
                    <Filter className="w-3.5 h-3.5 opacity-50" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-full">
                  <DropdownMenuItem onClick={() => setEditPriority('high')} className="text-red-600">High</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setEditPriority('medium')} className="text-yellow-600">Medium</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setEditPriority('low')} className="text-green-600">Low</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Deadline</label>
              <Input
                type="datetime-local"
                value={editDeadline}
                onChange={(e) => setEditDeadline(e.target.value)}
                className="border-slate-300"
              />
            </div>
            <Button
              onClick={handleSaveEdit}
              className="w-full bg-slate-900 text-white hover:bg-slate-800"
              disabled={!editTitle.trim()}
            >
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </main>
  );
}