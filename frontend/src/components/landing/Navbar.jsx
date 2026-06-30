

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Menu, X } from 'lucide-react';

export function Navbar() {
  const [sheetOpen, setSheetOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogin = () => navigate('/login');
  const handleSignup = () => navigate('/signup');

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#FAFAF8]/80 backdrop-blur-md border-b border-slate-200/20">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center">
          <span className="text-2xl font-bold text-slate-900 tracking-tight">Momentum- PlanMind AI</span>
        </div>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogin}
            className="text-slate-600 hover:text-slate-900 hover:bg-slate-100/50"
          >
            Login
          </Button>
          <Button
            size="sm"
            onClick={handleSignup}
            className="bg-slate-900 text-white hover:bg-slate-800"
          >
            Sign Up
          </Button>
        </div>

        {/* Mobile Navigation */}
        <div className="md:hidden">
          <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="h-10 w-10">
                <Menu className="h-5 w-5 text-slate-900" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-56 bg-[#FAFAF8]">
              <div className="flex flex-col gap-4 mt-8">
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => {
                    handleLogin();
                    setSheetOpen(false);
                  }}
                >
                  Login
                </Button>
                <Button
                  className="w-full justify-start bg-slate-900 text-white hover:bg-slate-800"
                  onClick={() => {
                    handleSignup();
                    setSheetOpen(false);
                  }}
                >
                  Sign Up
                </Button>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </nav>
  );
}