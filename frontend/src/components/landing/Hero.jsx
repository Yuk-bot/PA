// src/components/landing/Hero.jsx

import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, Sparkles } from 'lucide-react';

export function Hero() {
  const navigate = useNavigate();

  return (
    <section className="relative min-h-screen pt-32 pb-16 px-4 sm:px-6 lg:px-8 flex items-center">
      <div className="max-w-3xl mx-auto text-center">
        {/* Badge */}
        <div className="mb-6 inline-block">
          <Badge variant="outline" className="border-slate-300 bg-white/50 text-slate-700">
            <Sparkles className="w-3.5 h-3.5 mr-1.5" />
            AI Powered Productivity
          </Badge>
        </div>

        {/* Heading */}
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-900 mb-6 leading-[1.15]">
          Plan Better.
          <br />
          Work Smarter.
          <br />
          Stay Consistent.
        </h1>

        {/* Description */}
        <p className="text-lg sm:text-xl text-slate-600 mb-10 leading-relaxed max-w-2xl mx-auto font-light">
          PA is your personal AI productivity assistant. Organize tasks, intelligently plan schedules, prioritize work, and maintain long-term productivity—all powered by advanced AI agents working together.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Button
            size="lg"
            onClick={() => navigate('/signup')}
            className="bg-slate-900 text-white hover:bg-slate-800 px-8 h-12 text-base"
          >
            Get Started
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
          <Button
            size="lg"
            variant="outline"
            onClick={() => navigate('/login')}
            className="border-slate-300 text-slate-900 hover:bg-slate-50 px-8 h-12 text-base"
          >
            Login
          </Button>
        </div>
      </div>
    </section>
  );
}