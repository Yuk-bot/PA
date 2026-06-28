// src/App.jsx

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
// src/App.jsx

import Dashboard from '@/pages/Dashboard/Dashboard';
import Tasks from '@/pages/Tasks/Tasks';
import Calendar from '@/pages/Calender/Calender';
import Settings from '@/pages/Settings/Settings';
import Landing from '@/pages/Landing/Landing';
import Signup from '@/pages/Signup/Signup';   
import Login from '@/pages/Login/Login';
import Profile from '@/pages/Profile/Profile';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

// Protected Route Wrapper
function ProtectedRoute({ children }) {
  const token = localStorage.getItem('token');
  
  if (!token) {
    return <Navigate to="/" replace />;
  }
  
  return <DashboardLayout>{children}</DashboardLayout>;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<Landing />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/login" element={<Login />} />

        {/* Protected Dashboard Routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/tasks"
          element={
            <ProtectedRoute>
              <Tasks />
            </ProtectedRoute>
          }
        />
        <Route
          path="/calendar"
          element={
            <ProtectedRoute>
              <Calendar />
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Settings />
            </ProtectedRoute>
          }
        />

        {/* Catch all - redirect to landing */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;