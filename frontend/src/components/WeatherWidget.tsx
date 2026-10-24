import React from 'react';
import { Cloud, Sun, CloudRain, Snowflake, Wind } from 'lucide-react';

interface WeatherWidgetProps {
  temperature: number;
  condition: 'sunny' | 'cloudy' | 'rainy' | 'snowy' | 'windy';
  location: string;
  className?: string;
}

const WeatherWidget: React.FC<WeatherWidgetProps> = ({ 
  temperature, 
  condition, 
  location, 
  className = '' 
}) => {
  const getWeatherIcon = () => {
    switch (condition) {
      case 'sunny':
        return <Sun className="w-4 h-4 text-yellow-500" />;
      case 'cloudy':
        return <Cloud className="w-4 h-4 text-gray-500" />;
      case 'rainy':
        return <CloudRain className="w-4 h-4 text-brand-700" />;
      case 'snowy':
        return <Snowflake className="w-4 h-4 text-brand-200" />;
      case 'windy':
        return <Wind className="w-4 h-4 text-gray-600" />;
      default:
        return <Sun className="w-4 h-4 text-yellow-500" />;
    }
  };

  const getConditionText = () => {
    switch (condition) {
      case 'sunny':
        return 'Sunny';
      case 'cloudy':
        return 'Cloudy';
      case 'rainy':
        return 'Rainy';
      case 'snowy':
        return 'Snowy';
      case 'windy':
        return 'Windy';
      default:
        return 'Sunny';
    }
  };

  return (
    <div className={`bg-gradient-to-r from-brand-50 to-brand-100 rounded-lg p-3 border border-brand-200 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {getWeatherIcon()}
          <div>
            <div className="text-sm font-medium text-brand-800">{temperature}°C</div>
            <div className="text-xs text-brand-700">{getConditionText()}</div>
          </div>
        </div>
        <div className="text-xs text-brand-700 text-right">
          <div className="font-medium">{location}</div>
          <div>Perfect for travel</div>
        </div>
      </div>
    </div>
  );
};

export default WeatherWidget;


