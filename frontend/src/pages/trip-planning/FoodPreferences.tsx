import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Leaf, Utensils, Check } from 'lucide-react';
import { useTripPlanning } from '@/contexts/TripPlanningContext';
import ProgressIndicator from '@/components/ProgressIndicator';

const FoodPreferences: React.FC = () => {
  const navigate = useNavigate();
  const { tripData, updateTripData, currentStep, totalSteps } = useTripPlanning();
  const [selectedPreference, setSelectedPreference] = useState<string | null>(tripData.foodPreference);

  const foodOptions = [
    {
      id: 'vegetarian',
      title: 'Vegetarian',
      icon: Leaf,
      description: 'Plant-based meals only',
      color: 'bg-brand-50 border-brand-200 text-brand-800',
      selectedColor: 'bg-brand-700 border-brand-600 text-white',
    },
    {
      id: 'non-vegetarian',
      title: 'Non-Vegetarian',
      icon: Utensils,
      description: 'Include meat and seafood',
      color: 'bg-orange-50 border-orange-200 text-orange-800',
      selectedColor: 'bg-orange-600 border-orange-600 text-white',
    },
    {
      id: 'both',
      title: 'Both',
      icon: Utensils,
      description: 'Flexible with all food types',
      color: 'bg-brand-50 border-brand-200 text-brand-800',
      selectedColor: 'bg-brand-700 border-brand-600 text-white',
    },
  ];

  const handlePreferenceSelect = (preferenceId: string) => {
    setSelectedPreference(preferenceId);
  };

  const handleNext = () => {
    if (selectedPreference) {
      updateTripData({
        foodPreference: selectedPreference as any,
      });
      navigate('/trip-planning/eco-mode');
    }
  };

  const handleBack = () => {
    navigate('/trip-planning/company');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 to-brand-100">
      <ProgressIndicator 
        currentStep={currentStep} 
        totalSteps={totalSteps} 
        tripName={`${tripData.destination} trip`}
      />
      
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Card className="w-full">
          <CardHeader className="text-center">
            <CardTitle className="text-3xl font-bold text-brand-800 mb-2">
              What are your food preferences?
            </CardTitle>
            <CardDescription className="text-lg text-gray-600">
              This helps us recommend the best restaurants and dining experiences
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-8">
            {/* Food Preference Selection */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {foodOptions.map((option) => {
                const Icon = option.icon;
                const isSelected = selectedPreference === option.id;
                
                return (
                  <div
                    key={option.id}
                    onClick={() => handlePreferenceSelect(option.id)}
                    className={`p-6 rounded-lg border-2 cursor-pointer transition-all duration-200 hover:shadow-md ${
                      isSelected 
                        ? option.selectedColor 
                        : `${option.color} hover:shadow-sm`
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <Icon className={`w-6 h-6 ${isSelected ? 'text-white' : ''}`} />
                      {isSelected && <Check className="w-5 h-5 text-white" />}
                    </div>
                    <h3 className={`text-lg font-semibold mb-1 ${isSelected ? 'text-white' : ''}`}>
                      {option.title}
                    </h3>
                    <p className={`text-sm ${isSelected ? 'text-white/80' : 'text-gray-600'}`}>
                      {option.description}
                    </p>
                  </div>
                );
              })}
            </div>

            {/* Additional Information */}
            <div className="bg-brand-50 p-4 rounded-lg">
              <h4 className="font-semibold text-brand-800 mb-2">💡 Pro Tip</h4>
              <p className="text-sm text-brand-700">
                Your food preference helps us suggest restaurants that match your dietary needs and 
                cultural preferences. We'll also consider local specialties and hidden gems!
              </p>
            </div>

            {/* Trip Summary */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="font-semibold text-gray-800 mb-2">Trip Summary</h4>
              <div className="space-y-1 text-sm text-gray-600">
                <div className="flex justify-between">
                  <span>Destination:</span>
                  <Badge variant="secondary" className="bg-brand-100 text-brand-800">
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
                  <span>Pets:</span>
                  <span>{tripData.withPets ? 'Yes' : 'No'}</span>
                </div>
                {selectedPreference && (
                  <div className="flex justify-between">
                    <span>Food:</span>
                    <Badge variant="outline">
                      {foodOptions.find(opt => opt.id === selectedPreference)?.title}
                    </Badge>
                  </div>
                )}
              </div>
            </div>

            {/* Navigation */}
            <div className="flex justify-between pt-6">
              <Button variant="outline" onClick={handleBack}>
                Back
              </Button>
              
              <Button 
                onClick={handleNext}
                disabled={!selectedPreference}
                className="bg-brand-700 hover:bg-brand-800"
              >
                Next
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default FoodPreferences;
