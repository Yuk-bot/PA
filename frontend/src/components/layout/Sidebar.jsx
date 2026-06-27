// src/components/layout/Sidebar.jsx

import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import {
  LayoutDashboard,
  CheckSquare2,
  Calendar,
  Settings,
  LogOut,
  Menu,
  X,
} from 'lucide-react';

export function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);

  const navItems = [
    { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { label: 'Tasks', path: '/tasks', icon: CheckSquare2 },
    { label: 'Calendar', path: '/calendar', icon: Calendar },
    { label: 'Settings', path: '/settings', icon: Settings },
  ];

  const isActive = (path) => location.pathname === path;

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/');
  };

  const SidebarContent = () => (
    <div className="h-full flex flex-col">
      {/* Top Section */}
      <div className="p-6 space-y-8">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <span className="text-2xl font-bold text-slate-900 tracking-tight">PA</span>
          <span className="text-xs text-slate-500 font-medium">v0.1</span>
        </div>

        {/* Navigation */}
        <nav className="space-y-2">
          {navItems.map(({ label, path, icon: Icon }) => (
            <Button
              key={path}
              onClick={() => {
                navigate(path);
                setIsOpen(false);
              }}
              variant={isActive(path) ? 'default' : 'ghost'}
              className={`w-full justify-start gap-3 ${
                isActive(path)
                  ? 'bg-slate-900 text-white hover:bg-slate-800'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Button>
          ))}
        </nav>
      </div>

      {/* Bottom Section */}
      <div className="mt-auto p-6 space-y-4 border-t border-slate-200">
        {/* User Profile Card */}
        <div className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 transition-colors">
          <Avatar className="w-10 h-10">
            <AvatarFallback className="bg-slate-200 text-slate-700 font-semibold">
              YK
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-900 truncate">Yukta</p>
            <p className="text-xs text-slate-500 truncate">you@example.com</p>
          </div>
        </div>

        {/* Logout Button */}
        <Button
          onClick={handleLogout}
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2 text-slate-600 hover:text-red-600 hover:bg-red-50"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </Button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex fixed left-0 top-0 h-screen w-64 bg-[#FAFAF8] border-r border-slate-200/50 flex-col z-40">
        <SidebarContent />
      </aside>

      {/* Mobile Header with Menu */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-16 bg-[#FAFAF8] border-b border-slate-200/50 flex items-center px-4 z-40">
        <Button
          onClick={() => setIsOpen(!isOpen)}
          variant="ghost"
          size="icon"
          className="text-slate-900"
        >
          {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </Button>
        <span className="ml-3 text-lg font-bold text-slate-900">PA</span>
      </div>

      {/* Mobile Sidebar Sheet */}
      {isOpen && (
        <div className="md:hidden fixed inset-0 z-30 bg-black/50">
          <div className="absolute left-0 top-0 h-full w-64 bg-[#FAFAF8] border-r border-slate-200/50">
            <div className="pt-16">
              <SidebarContent />
            </div>
          </div>
        </div>
      )}
    </>
  );
}