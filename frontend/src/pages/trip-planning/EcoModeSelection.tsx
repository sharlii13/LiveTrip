import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Leaf, Car, Plane, Train, Bus, Bike, Check } from 'lucide-react';
import { useTripPlanning } from '@/contexts/TripPlanningContext';
import ProgressIndicator from '@/components/ProgressIndicator';

const EcoModeSelection: React.FC = () => {
  const navigate = useNavigate();
  const { tripData, updateTripData, currentStep, totalSteps } = useTripPlanning();
  const [ecoMode, setEcoMode] = useState<boolean>(tripData.ecoMode);
  const [selectedTransport, setSelectedTransport] = useState<string>('');

  const transportOptions = [
    {
      id: 'walking',
      title: 'Walking',
      icon: Bike,
      description: 'Explore on foot',
      ecoScore: 10,
      color: 'bg-blue-50 border-blue-200 text-blue-800',
    },
    {
      id: 'bicycle',
      title: 'Bicycle',
      icon: Bike,
      description: 'Rent a bike',
      ecoScore: 9,
      color: 'bg-blue-50 border-blue-200 text-blue-800',
    },
    {
      id: 'public-transport',
      title: 'Public Transport',
      icon: Bus,
      description: 'Buses, trams, metro',
      ecoScore: 8,
      color: 'bg-blue-50 border-blue-200 text-blue-800',
    },
    {
      id: 'train',
      title: 'Train',
      icon: Train,
      description: 'Intercity trains',
      ecoScore: 7,
      color: 'bg-blue-50 border-blue-200 text-blue-800',
    },
    {
      id: 'car',
      title: 'Car',
      icon: Car,
      description: 'Rental or taxi',
      ecoScore: 4,
      color: 'bg-orange-50 border-orange-200 text-orange-800',
    },
    {
      id: 'plane',
      title: 'Plane',
      icon: Plane,
      description: 'Domestic flights',
      ecoScore: 2,
      color: 'bg-red-50 border-red-200 text-red-800',
    },
  ];

  const handleEcoModeToggle = (enabled: boolean) => {
    setEcoMode(enabled);
  };

  const handleTransportSelect = (transportId: string) => {
    setSelectedTransport(transportId);
  };

  const handleNext = async () => {
    updateTripData({
      ecoMode: ecoMode,
    });

    // Submit trip data to backend
    try {
      const response = await fetch('/api/trips', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          ...tripData,
          ecoMode: ecoMode,
          transportPreference: selectedTransport,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Trip created successfully:', result);
        navigate('/trip-planning/summary');
      } else {
        console.error('Failed to create trip');
      }
    } catch (error) {
      console.error('Error creating trip:', error);
    }
  };

  const handleBack = () => {
    navigate('/trip-planning/interests');
  };

  const getEcoScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600';
    if (score >= 6) return 'text-blue-600';
    if (score >= 4) return 'text-orange-600';
    return 'text-red-600';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <ProgressIndicator 
        currentStep={currentStep} 
        totalSteps={totalSteps} 
        tripName={`${tripData.destination} trip`}
      />
      
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Card className="w-full">
          <CardHeader className="text-center">
            <CardTitle className="text-3xl font-bold text-blue-800 mb-2">
              Choose your eco-friendly options
            </CardTitle>
            <CardDescription className="text-lg text-gray-600">
              Help us make your trip more sustainable
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-8">
            {/* Eco Mode Toggle */}
            <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Leaf className="w-6 h-6 text-blue-600" />
                  <div>
                    <h3 className="text-lg font-semibold text-blue-800">Eco Mode</h3>
                    <p className="text-sm text-blue-700">
                      Enable eco-friendly recommendations and sustainable travel options
                    </p>
                  </div>
                </div>
                <Switch
                  checked={ecoMode}
                  onCheckedChange={handleEcoModeToggle}
                  className="data-[state=checked]:bg-blue-600"
                />
              </div>
            </div>

            {/* Transport Preferences */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-800">
                Preferred Transportation
              </h3>
              <p className="text-sm text-gray-600">
                Select your preferred way to get around (optional)
              </p>
              
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {transportOptions.map((option) => {
                  const Icon = option.icon;
                  const isSelected = selectedTransport === option.id;
                  
                  return (
                    <div
                      key={option.id}
                      onClick={() => handleTransportSelect(option.id)}
                      className={`p-4 rounded-lg border-2 cursor-pointer transition-all duration-200 hover:shadow-md ${
                        isSelected 
                          ? 'border-blue-500 bg-blue-50' 
                          : `${option.color} hover:shadow-sm`
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <Icon className={`w-5 h-5 ${isSelected ? 'text-blue-600' : ''}`} />
                        {isSelected && <Check className="w-4 h-4 text-blue-600" />}
                      </div>
                      <h4 className={`font-medium text-sm ${isSelected ? 'text-blue-800' : ''}`}>
                        {option.title}
                      </h4>
                      <p className={`text-xs ${isSelected ? 'text-blue-600' : 'text-gray-600'}`}>
                        {option.description}
                      </p>
                      <div className="mt-2">
                        <span className={`text-xs font-medium ${getEcoScoreColor(option.ecoScore)}`}>
                          Eco Score: {option.ecoScore}/10
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Eco Mode Benefits */}
            {ecoMode && (
              <div className="bg-blue-50 p-4 rounded-lg">
                <h4 className="font-semibold text-blue-800 mb-2">🌱 Eco Mode Benefits</h4>
                <ul className="text-sm text-blue-700 space-y-1">
                  <li>• Sustainable accommodation recommendations</li>
                  <li>• Eco-friendly restaurant suggestions</li>
                  <li>• Carbon footprint tracking</li>
                  <li>• Green transportation options</li>
                  <li>• Local environmental initiatives</li>
                </ul>
              </div>
            )}

            {/* Trip Summary */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="font-semibold text-gray-800 mb-2">Trip Summary</h4>
              <div className="space-y-1 text-sm text-gray-600">
                <div className="flex justify-between">
                  <span>Destination:</span>
                  <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                    {tripData.destination}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>Dates:</span>
                  <span>
                    {tripData.startDate?.toLocaleDateString()} - {tripData.endDate?.toLocaleDateString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Company:</span>
                  <Badge variant="outline">
                    {tripData.companyType ? tripData.companyType.charAt(0).toUpperCase() + tripData.companyType.slice(1) : 'Unknown'} Trip
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>Food:</span>
                  <Badge variant="outline">
                    {tripData.foodPreference ? tripData.foodPreference.charAt(0).toUpperCase() + tripData.foodPreference.slice(1) : 'Unknown'}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>Interests:</span>
                  <span className="text-blue-600 font-medium">
                    {tripData.interests.length} selected
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Eco Mode:</span>
                  <Badge variant={ecoMode ? "default" : "outline"} className={ecoMode ? "bg-blue-600" : ""}>
                    {ecoMode ? 'Enabled' : 'Disabled'}
                  </Badge>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <div className="flex justify-between pt-6">
              <Button variant="outline" onClick={handleBack}>
                Back
              </Button>
              
              <Button 
                onClick={handleNext}
                className="bg-blue-600 hover:bg-blue-700"
              >
                Create Trip Plan
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default EcoModeSelection;
