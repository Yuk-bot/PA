// src/components/layout/DashboardLayout.jsx

import { useState } from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { RightPanel } from './RightPanel';

export function DashboardLayout({ children }) {
  const [rightPanelOpen, setRightPanelOpen] = useState(false);

  return (
    <div className="flex h-screen bg-[#FAFAF8] overflow-hidden">
      {/* Background Grid */}
      <svg
        className="fixed inset-0 -z-10 w-full h-full opacity-[0.08] pointer-events-none"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="none"
      >
        <defs>
          <pattern
            id="dashboard-grid"
            width="40"
            height="40"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 40 0 L 0 0 0 40"
              fill="none"
              stroke="currentColor"
              strokeWidth="0.5"
              className="text-slate-900"
            />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#dashboard-grid)" />
      </svg>

      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 md:ml-64 overflow-hidden">
        {/* Mobile Header */}
        <div className="md:hidden h-16 border-b border-slate-200/50" />

        {/* Topbar */}
        <Topbar />

        {/* Page Content */}
        <div className="flex flex-1 overflow-hidden">
          <div className="flex-1 overflow-y-auto">{children}</div>
        </div>
      </div>
    </div>
  );
}