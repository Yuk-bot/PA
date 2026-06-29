

import { useState, useEffect } from 'react';
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
import { CheckSquare2, Plus, Filter, Trash2, Loader } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

export default function Tasks() {
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState('all');
  const [newTask, setNewTask] = useState('');
  const [newDeadline, setNewDeadline] = useState('');
  const [newPriority, setNewPriority] = useState('medium');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);

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


  useEffect(() => {
    fetchTasks();
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
                    type="date"
                    value={newDeadline}
                    onChange={(e) => setNewDeadline(e.target.value)}
                    className="border-slate-300"
                    min={new Date().toISOString().split('T')[0]}
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
              {filteredTasks.map((task) => (
                <div
                  key={task.id}
                  className="p-4 hover:bg-slate-50/50 transition-colors flex items-center gap-4 group"
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
                      {task.deadline ? new Date(task.deadline).toLocaleDateString() : 'No date'}
                    </p>
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
                    onClick={() => handleDeleteTask(task.id)}
                    className="text-slate-400 hover:text-red-600 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </main>
  );
}