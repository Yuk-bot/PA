// src/components/landing/BackgroundGrid.jsx

export function BackgroundGrid() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden">
      {/* Off-white background */}
      <div className="absolute inset-0 bg-[#FAFAF8]" />

      {/* Subtle square grid */}
      <svg
        className="absolute inset-0 w-full h-full opacity-[0.10]"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="none"
      >
        <defs>
          <pattern
            id="grid"
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
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>

      {/* Radial gradient fade at edges (subtle) */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#FAFAF8]/30" />
    </div>
  );
}