import React, { useId } from 'react';

interface LiveTripLogoProps {
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  className?: string;
}

/** The LiveTrip mark (a location pin with a plane looping around it, on a blue-to-green badge) and wordmark. */
export function LiveTripMark({ className = 'w-10 h-10' }: { className?: string }) {
  const id = useId().replace(/:/g, '');  // unique gradient ids: several logos can share a page
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      <defs>
        <linearGradient id={`lt-bg-${id}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#2563eb" />
          <stop offset="55%" stopColor="#0891b2" />
          <stop offset="100%" stopColor="#10b981" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="16" fill={`url(#lt-bg-${id})`} />
      {/* the plane's loop around the pin */}
      <path d="M14 42 C 6 28, 20 12, 38 12 C 50 12, 56 20, 54 28" fill="none" stroke="white" strokeOpacity=".75"
            strokeWidth="2.4" strokeLinecap="round" strokeDasharray="0.5 5" />
      <path transform="translate(47 17) rotate(40) scale(0.62) translate(-12 -12)" fill="white"
            d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
      {/* the pin */}
      <path d="M32 53 C 32 53, 19 40.5, 19 31.5 a 13 13 0 0 1 26 0 C 45 40.5, 32 53, 32 53 Z" fill="white" />
      <circle cx="32" cy="31.5" r="5.2" fill={`url(#lt-bg-${id})`} />
    </svg>
  );
}

const LiveTripLogo: React.FC<LiveTripLogoProps> = ({ size = 'md', showText = true, className = '' }) => {
  const markSize = { sm: 'w-7 h-7', md: 'w-9 h-9', lg: 'w-11 h-11' }[size];
  const textSize = { sm: 'text-lg', md: 'text-2xl', lg: 'text-3xl' }[size];

  return (
    <div className={`flex items-center gap-2.5 ${className}`} translate="no">
      <LiveTripMark className={`${markSize} shrink-0 drop-shadow-sm`} />
      {showText && (
        <span className={`${textSize} font-black tracking-tight leading-none`}>
          <span className="text-slate-900 dark:text-white">Live</span>
          <span className="bg-gradient-to-r from-blue-600 to-emerald-500 bg-clip-text text-transparent">Trip</span>
        </span>
      )}
    </div>
  );
};

export default LiveTripLogo;
