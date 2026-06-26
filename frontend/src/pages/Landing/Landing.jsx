// src/pages/Landing/Landing.jsx

import { BackgroundGrid } from '@/components/landing/Background';
import { Navbar } from '@/components/landing/Navbar';
import { Hero } from '@/components/landing/Hero';
import { About } from '@/components/landing/About';
import { Footer } from '@/components/landing/Footer';

export default function Landing() {
  return (
    <div className="relative w-full overflow-x-hidden">
      {/* Background Grid */}
      <BackgroundGrid />

      {/* Navbar */}
      <Navbar />

      {/* Main Content */}
      <main>
        {/* Hero Section */}
        <Hero />

        {/* About Section */}
        <About />
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}