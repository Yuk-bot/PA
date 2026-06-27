// src/pages/Tasks.jsx

import { useState } from 'react';
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
import { CheckSquare2, Plus, Filter, Trash2 } from 'lucide-react';

const SAMPLE_TASKS = [
  { id: 1, title: 'Complete project report', priority: 'high', completed: false, dueDate: 'Today' },
  { id: 2, title: 'Review pull requests', priority: 'medium', completed: false, dueDate: 'Today' },
  { id: 3, title: 'Update documentation', priority: 'low', completed: true, dueDate: 'Yesterday' },
  { id: 4, title: 'Team meeting prep', priority: 'high', completed: false, dueDate: 'Tomorrow' },
  { id: 5, title: 'Email client feedback', priority: 'medium', completed: false, dueDate: 'Tomorrow' },
];

export default function Tasks() {
  const [tasks, setTasks] = useState(SAMPLE_TASKS);
  const [filter, setFilter] = useState('all');
  const [newTask, setNewTask] = useState('');

  const filteredTasks = tasks.filter((task) => {
    if (filter === 'completed') return task.completed;
    if (filter === 'pending') return !task.completed;
    return true;
  });

  const handleToggleTask = (id) => {
    setTasks(tasks.map((task) =>
      task.id === id ? { ...task, completed: !task.completed } : task
    ));
  };

  const handleDeleteTask = (id) => {
    setTasks(tasks.filter((task) => task.id !== id));
  };

  const handleAddTask = () => {
    if (newTask.trim()) {
      setTasks([
        ...tasks,
        {
          id: Math.max(...tasks.map((t) => t.id), 0) + 1,
          title: newTask,
          priority: 'medium',
          completed: false,
          dueDate: 'Today',
        },
      ]);
      setNewTask('');
    }
  };

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
              {tasks.length} total • {tasks.filter((t) => !t.completed).length} pending
            </p>
          </div>

          {/* Add Task Dialog */}
          <Dialog>
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
              <div className="space-y-4">
                <Input
                  placeholder="Task title"
                  value={newTask}
                  onChange={(e) => setNewTask(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddTask()}
                />
                <Button
                  onClick={handleAddTask}
                  className="w-full bg-slate-900 text-white hover:bg-slate-800"
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

        {/* Task List */}
        <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm overflow-hidden">
          {filteredTasks.length === 0 ? (
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
                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={task.completed}
                    onChange={() => handleToggleTask(task.id)}
                    className="w-5 h-5 rounded border-slate-300 cursor-pointer"
                  />

                  {/* Task Content */}
                  <div className="flex-1 min-w-0">
                    <p
                      className={`font-medium ${
                        task.completed
                          ? 'text-slate-400 line-through'
                          : 'text-slate-900'
                      }`}
                    >
                      {task.title}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">{task.dueDate}</p>
                  </div>

                  {/* Priority Badge */}
                  <span
                    className={`text-xs font-medium px-2.5 py-1 rounded whitespace-nowrap ${getPriorityColor(
                      task.priority
                    )}`}
                  >
                    {task.priority}
                  </span>

                  {/* Delete Button */}
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