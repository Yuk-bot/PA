// src/components/landing/Footer.jsx

export function Footer() {
  const links = [
    { label: 'Privacy', href: '#' },
    { label: 'Terms', href: '#' },
    { label: 'Contact', href: '#' },
  ];

  return (
    <footer className="relative border-t border-slate-200/30 bg-[#FAFAF8]/50 backdrop-blur-sm">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
          {/* Left: Copyright */}
          <p className="text-sm text-slate-600 font-light">
            © 2026 PA. All rights reserved.
          </p>

          {/* Right: Links */}
          <div className="flex items-center gap-6">
            {links.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-sm text-slate-600 hover:text-slate-900 transition-colors font-light"
              >
                {link.label}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}