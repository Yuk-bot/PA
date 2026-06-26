// src/components/landing/About.jsx

import { Card } from '@/components/ui/card';
import {
  CheckCircle2,
  ListTodo,
  Calendar,
  Target,
  Zap,
  AlertTriangle,
} from 'lucide-react';

export function About() {
  const features = [
    { icon: ListTodo, text: 'Manage Tasks' },
    { icon: Calendar, text: 'Plan Schedules' },
    { icon: Target, text: 'Prioritize Work' },
    { icon: Zap, text: 'Maintain Productivity' },
    { icon: AlertTriangle, text: 'Prevent Missed Deadlines' },
  ];

  return (
    <section className="relative py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto">
        <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm shadow-sm">
          <div className="p-8 sm:p-10 lg:p-12">
            {/* Title */}
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-6">
              What is PA?
            </h2>

            {/* Description */}
            <p className="text-lg text-slate-700 mb-8 leading-relaxed font-light">
              PA combines intelligent AI agents to work together seamlessly, giving you a productivity system that learns your habits, understands your priorities, and adapts to your unique working style. No more juggling tools or missing deadlines—PA handles the complexity while you focus on what matters.
            </p>

            {/* Features List */}
            <div className="space-y-3">
              {features.map(({ icon: Icon, text }, index) => (
                <div key={index} className="flex items-center gap-3">
                  <Icon className="w-5 h-5 text-slate-900 flex-shrink-0" />
                  <span className="text-slate-700 font-medium">{text}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>
    </section>
  );
}