import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Calendar, Clock, MapPin, Activity, TrendingUp, Star, Navigation } from 'lucide-react';
import { apiService, MultiDayPlanRequest, MultiDayResponse, MultiDayItinerary } from '@/services/apiService';
import LoadingSpinner from '@/components/LoadingSpinner';

// Category icons mapping
const categoryIcons: { [key: string]: React.ReactNode } = {
  historical: <Activity className="h-4 w-4" />,
  nature: <MapPin className="h-4 w-4" />,
  food: <Star className="h-4 w-4" />,
  shopping: <Navigation className="h-4 w-4" />,
  cultural: <Activity className="h-4 w-4" />,
  religious: <Star className="h-4 w-4" />,
  entertainment: <TrendingUp className="h-4 w-4" />,
  fort: <Activity className="h-4 w-4" />,
  museum: <Activity className="h-4 w-4" />,
  park: <MapPin className="h-4 w-4" />,
  temple: <Star className="h-4 w-4" />,
  historic: <Activity className="h-4 w-4" />,
};

// Category colors mapping
const categoryColors: { [key: string]: string } = {
  historical: 'bg-amber-100 text-amber-800 border-amber-200',
  nature: 'bg-brand-100 text-brand-800 border-brand-200',
  food: 'bg-red-100 text-red-800 border-red-200',
  shopping: 'bg-brand-100 text-brand-800 border-brand-200',
  cultural: 'bg-brand-100 text-brand-800 border-brand-200',
  religious: 'bg-orange-100 text-orange-800 border-orange-200',
  entertainment: 'bg-pink-100 text-pink-800 border-pink-200',
  fort: 'bg-gray-100 text-gray-800 border-gray-200',
  museum: 'bg-brand-100 text-brand-800 border-brand-200',
  park: 'bg-brand-100 text-brand-800 border-brand-200',
  temple: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  historic: 'bg-amber-100 text-amber-800 border-amber-200',
};

interface MultiDayPlannerProps {
  onItineraryGenerated?: (itinerary: MultiDayResponse) => void;
}

const MultiDayPlanner: React.FC<MultiDayPlannerProps> = ({ onItineraryGenerated }) => {
  const [planRequest, setPlanRequest] = useState<MultiDayPlanRequest>({
    city: 'Mumbai',
    days: 3,
    start_time: '10:00',
    end_time: '18:00',
    mode: 'driving',
    pace: 'normal',
    hotel: {
      lat: 19.0760,
      lng: 72.8777
    }
  });
  
  const [itinerary, setItinerary] = useState<MultiDayResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePlanTrip = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.planMultiDayTrip(planRequest);
      setItinerary(response);
      onItineraryGenerated?.(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to plan multi-day trip');
      console.error('Multi-day planning error:', err);
    } finally {
      setLoading(false);
    }
  };

  const updatePlanRequest = (updates: Partial<MultiDayPlanRequest>) => {
    setPlanRequest(prev => ({ ...prev, ...updates }));
  };

  const getDiversityColor = (score: number) => {
    if (score >= 0.8) return 'text-brand-700';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getUtilizationColor = (percent: number) => {
    if (percent >= 80) return 'text-brand-700';
    if (percent >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const renderDayItinerary = (dayItinerary: MultiDayItinerary) => {
    return (
      <Card key={dayItinerary.day} className="mb-6">
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Day {dayItinerary.day}
            </CardTitle>
            <div className="flex gap-4 text-sm">
              <div className="flex items-center gap-1">
                <TrendingUp className="h-4 w-4" />
                <span className={getUtilizationColor(dayItinerary.utilization_percent)}>
                  {dayItinerary.utilization_percent.toFixed(1)}% utilization
                </span>
              </div>
              <div className="flex items-center gap-1">
                <Star className="h-4 w-4" />
                <span className={getDiversityColor(dayItinerary.diversity_score)}>
                  {(dayItinerary.diversity_score * 100).toFixed(0)}% diversity
                </span>
              </div>
            </div>
          </div>
          
          {/* Category mix indicators */}
          <div className="flex flex-wrap gap-2 mt-2">
            {Object.entries(dayItinerary.category_mix).map(([category, count]) => (
              <Badge 
                key={category} 
                variant="outline" 
                className={`flex items-center gap-1 ${categoryColors[category] || 'bg-gray-100'}`}
              >
                {categoryIcons[category]}
                {category} ({count})
              </Badge>
            ))}
          </div>
          
          {/* Diversity progress bar */}
          <div className="mt-3">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs font-medium">Category Diversity</span>
              <span className="text-xs">{(dayItinerary.diversity_score * 100).toFixed(0)}%</span>
            </div>
            <Progress 
              value={dayItinerary.diversity_score * 100} 
              className="h-2"
            />
          </div>
        </CardHeader>
        
        <CardContent>
          <div className="grid gap-4">
            {/* Day statistics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
              <div className="text-center">
                <div className="text-lg font-semibold">{dayItinerary.schedule.length}</div>
                <div className="text-xs text-gray-600">POIs</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-semibold">{dayItinerary.total_distance_km}km</div>
                <div className="text-xs text-gray-600">Distance</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-semibold">{dayItinerary.total_duration_hr.toFixed(1)}h</div>
                <div className="text-xs text-gray-600">Duration</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-semibold">{Object.keys(dayItinerary.category_mix).length}</div>
                <div className="text-xs text-gray-600">Categories</div>
              </div>
            </div>
            
            {/* Schedule timeline */}
            <div className="space-y-3">
              {dayItinerary.schedule.map((poi, index) => (
                <div key={index} className="flex items-center gap-4 p-3 bg-white border rounded-lg hover:shadow-sm transition-shadow">
                  <div className="flex-shrink-0 w-2 h-2 bg-brand-700 rounded-full"></div>
                  
                  <div className="flex-grow">
                    <div className="flex items-center gap-2 mb-1">
                      {categoryIcons[poi.category]}
                      <h4 className="font-medium">{poi.poi}</h4>
                      <Badge 
                        variant="outline" 
                        className={`text-xs ${categoryColors[poi.category] || 'bg-gray-100'}`}
                      >
                        {poi.category}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {poi.start} - {poi.end}
                      </div>
                      <div className="flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {poi.coordinates.lat.toFixed(4)}, {poi.coordinates.lng.toFixed(4)}
                      </div>
                    </div>
                  </div>
                  
                  <div className="text-right text-sm">
                    <div className="font-medium">{poi.duration_hr}h</div>
                    <div className="text-gray-500">visit</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Planning Form */}
      <Card>
        <CardHeader>
          <CardTitle>Plan Multi-Day Trip</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">City</label>
              <Input
                value={planRequest.city}
                onChange={(e) => updatePlanRequest({ city: e.target.value })}
                placeholder="Enter city name"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Days</label>
              <Input
                type="number"
                min="1"
                max="14"
                value={planRequest.days}
                onChange={(e) => updatePlanRequest({ days: parseInt(e.target.value) })}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Start Time</label>
              <Input
                type="time"
                value={planRequest.start_time}
                onChange={(e) => updatePlanRequest({ start_time: e.target.value })}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">End Time</label>
              <Input
                type="time"
                value={planRequest.end_time}
                onChange={(e) => updatePlanRequest({ end_time: e.target.value })}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Transportation</label>
              <Select value={planRequest.mode} onValueChange={(value) => updatePlanRequest({ mode: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="driving">Driving</SelectItem>
                  <SelectItem value="walking">Walking</SelectItem>
                  <SelectItem value="transit">Public Transit</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Pace</label>
              <Select value={planRequest.pace} onValueChange={(value) => updatePlanRequest({ pace: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="slow">Slow</SelectItem>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="fast">Fast</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1">Hotel Location</label>
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="number"
                  step="0.0001"
                  placeholder="Latitude"
                  value={planRequest.hotel.lat}
                  onChange={(e) => updatePlanRequest({ 
                    hotel: { ...planRequest.hotel, lat: parseFloat(e.target.value) || 0 }
                  })}
                />
                <Input
                  type="number"
                  step="0.0001"
                  placeholder="Longitude"
                  value={planRequest.hotel.lng}
                  onChange={(e) => updatePlanRequest({ 
                    hotel: { ...planRequest.hotel, lng: parseFloat(e.target.value) || 0 }
                  })}
                />
              </div>
            </div>
          </div>
          
          <div className="mt-6">
            <Button 
              onClick={handlePlanTrip} 
              disabled={loading}
              className="w-full md:w-auto"
            >
              {loading ? (
                <>
                  <LoadingSpinner />
                  Planning Trip...
                </>
              ) : (
                'Plan Multi-Day Trip 🎯'
              )}
            </Button>
          </div>
          
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Itinerary Results */}
      {itinerary && (
        <div className="space-y-6">
          {/* Summary Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Trip Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold text-brand-700">{itinerary.summary.total_days}</div>
                  <div className="text-sm text-gray-600">Days</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-brand-700">{itinerary.summary.total_pois_covered}</div>
                  <div className="text-sm text-gray-600">POIs</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-brand-700">{itinerary.summary.avg_daily_diversity}</div>
                  <div className="text-sm text-gray-600">Avg Diversity</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-orange-600">{itinerary.summary.avg_daily_utilization}</div>
                  <div className="text-sm text-gray-600">Avg Utilization</div>
                </div>
              </div>
              
              {itinerary.summary.unassigned_pois.length > 0 && (
                <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                  <p className="text-yellow-800 text-sm">
                    <strong>Note:</strong> {itinerary.summary.unassigned_pois.length} POI(s) could not be scheduled: {itinerary.summary.unassigned_pois.join(', ')}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Daily Itineraries */}
          <div>
            <h2 className="text-2xl font-bold mb-4">Daily Itineraries</h2>
            {itinerary.itinerary.map(renderDayItinerary)}
          </div>
        </div>
      )}
    </div>
  );
};

export default MultiDayPlanner;