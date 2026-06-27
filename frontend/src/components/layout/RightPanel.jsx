// src/components/layout/RightPanel.jsx

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Send, Lightbulb, X } from 'lucide-react';

export function RightPanel({ isOpen, onClose }) {
  const [suggestion] = useState(
    'Based on your tasks, I recommend prioritizing "Finish project report" before 5 PM.'
  );

  return (
    <>
      {/* Desktop Panel */}
      <aside className="hidden lg:flex fixed right-0 top-0 h-screen w-80 bg-[#FAFAF8] border-l border-slate-200/50 flex-col z-20">
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-6 space-y-1">
            <h2 className="text-lg font-bold text-slate-900">PA Assistant</h2>
            <p className="text-xs text-slate-500">AI-powered insights</p>
          </div>

          <Separator />

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {/* AI Suggestion Card */}
            <Card className="p-4 border-slate-200/50 bg-blue-50/50 border-blue-200">
              <div className="flex gap-3">
                <Lightbulb className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-blue-900 mb-1">
                    Smart Suggestion
                  </p>
                  <p className="text-xs text-blue-800 leading-relaxed">
                    {suggestion}
                  </p>
                </div>
              </div>
            </Card>

            {/* Recent Suggestions */}
            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                Recent Insights
              </p>
              <div className="space-y-2">
                {['Calendar sync', 'Focus mode ready', 'Task analysis'].map(
                  (item) => (
                    <Button
                      key={item}
                      variant="ghost"
                      size="sm"
                      className="w-full justify-start text-slate-700 hover:bg-slate-100 text-xs"
                    >
                      {item}
                    </Button>
                  )
                )}
              </div>
            </div>
          </div>

          <Separator />

          {/* Input Section */}
          <div className="p-6 space-y-3">
            <div className="flex gap-2">
              <Input
                type="text"
                placeholder="Ask PA anything..."
                className="h-9 bg-white border-slate-300 text-sm"
              />
              <Button
                size="icon"
                className="bg-slate-900 text-white hover:bg-slate-800 h-9 w-9"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
            <p className="text-xs text-slate-500 text-center">
              Ask about tasks, schedules, or productivity tips
            </p>
          </div>
        </div>
      </aside>

      {/* Mobile Panel (Sheet-like) */}
      {isOpen && (
        <div className="lg:hidden fixed inset-0 z-40 bg-black/50">
          <div className="absolute right-0 top-0 h-full w-80 bg-[#FAFAF8] border-l border-slate-200/50 flex flex-col">
            {/* Header with Close */}
            <div className="flex items-center justify-between p-6">
              <div>
                <h2 className="text-lg font-bold text-slate-900">PA Assistant</h2>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="text-slate-600"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>

            <Separator />

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <Card className="p-4 border-slate-200/50 bg-blue-50/50 border-blue-200">
                <div className="flex gap-3">
                  <Lightbulb className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-blue-900 mb-1">
                      Smart Suggestion
                    </p>
                    <p className="text-xs text-blue-800 leading-relaxed">
                      {suggestion}
                    </p>
                  </div>
                </div>
              </Card>
            </div>

            <Separator />

            {/* Input Section */}
            <div className="p-6 space-y-3">
              <div className="flex gap-2">
                <Input
                  type="text"
                  placeholder="Ask PA..."
                  className="h-9 bg-white border-slate-300 text-sm"
                />
                <Button
                  size="icon"
                  className="bg-slate-900 text-white hover:bg-slate-800 h-9 w-9"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}