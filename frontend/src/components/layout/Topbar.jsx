// src/components/layout/Topbar.jsx

import { useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Bell, Search, Settings, User } from 'lucide-react';

export function Topbar() {
  const location = useLocation();

  // Get page title based on route
  const getTitleFromPath = (path) => {
    const titles = {
      '/dashboard': 'Dashboard',
      '/tasks': 'Tasks',
      '/calendar': 'Calendar',
      '/settings': 'Settings',
    };
    return titles[path] || 'PA';
  };

  return (
    <header className="sticky top-0 z-30 w-full bg-[#FAFAF8]/80 backdrop-blur-md border-b border-slate-200/50">
      <div className="flex items-center justify-between h-16 px-4 md:px-6">
        {/* Left: Page Title */}
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-900">
            {getTitleFromPath(location.pathname)}
          </h1>
        </div>

        {/* Center: Search (hidden on mobile) */}
        <div className="hidden md:flex flex-1 justify-center px-4">
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              type="text"
              placeholder="Search tasks, calendar..."
              className="pl-10 h-9 bg-white border-slate-300 text-slate-900 placeholder:text-slate-400"
            />
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-3 ml-auto">
          {/* AI Status Indicator */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200">
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-xs font-medium text-blue-700">AI Active</span>
          </div>

          {/* Notifications */}
          <Button
            variant="ghost"
            size="icon"
            className="text-slate-600 hover:text-slate-900 hover:bg-slate-100"
          >
            <Bell className="w-5 h-5" />
          </Button>

          {/* Profile Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              >
                <User className="w-5 h-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <div className="px-2 py-1.5">
                <p className="text-sm font-semibold text-slate-900">Yukta</p>
                <p className="text-xs text-slate-500">you@example.com</p>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <User className="w-4 h-4 mr-2" />
                Profile Settings
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Settings className="w-4 h-4 mr-2" />
                Preferences
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-red-600">
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}