import React from 'react';

interface LiveTripLogoProps {
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  className?: string;
}

const LiveTripLogo: React.FC<LiveTripLogoProps> = ({ 
  size = 'md', 
  showText = true, 
  className = '' 
}) => {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  };

  const textSizeClasses = {
    sm: 'text-lg',
    md: 'text-xl',
    lg: 'text-2xl'
  };

  return (
    <div className={`flex items-center ${className}`}>
      <div className={sizeClasses[size]}>
        <svg viewBox="0 0 100 100" className="w-full h-full">
          <defs>
            <linearGradient id="pinGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#1e40af" />
              <stop offset="100%" stopColor="#06b6d4" />
            </linearGradient>
          </defs>
          {/* Pin head with hole */}
          <circle cx="50" cy="30" r="15" fill="url(#pinGradient)" />
          <circle cx="50" cy="30" r="8" fill="white" />
          {/* Pin body with flowing curve */}
          <path d="M50 45 Q70 60 50 75 Q30 60 50 45" fill="url(#pinGradient)" />
        </svg>
      </div>
      {showText && (
        <span className={`${textSizeClasses[size]} font-bold bg-gradient-to-r from-gray-800 to-blue-500 bg-clip-text text-transparent ml-3`}>
          LiveTrip
        </span>
      )}
    </div>
  );
};

export default LiveTripLogo;
