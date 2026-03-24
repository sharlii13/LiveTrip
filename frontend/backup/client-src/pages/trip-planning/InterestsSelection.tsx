import React, { useState } from 'react';
import { useLocation } from 'wouter';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Plus, Check } from 'lucide-react';
import { useTripPlanning } from '@/contexts/TripPlanningContext';
import ProgressIndicator from '@/components/ProgressIndicator';

const InterestsSelection: React.FC = () => {
  const [, setLocation] = useLocation();
  const { tripData, updateTripData, currentStep, totalSteps } = useTripPlanning();
  const [selectedInterests, setSelectedInterests] = useState<string[]>(tripData.interests);

  const interestOptions = [
    'Must-see Attractions',
    'Great Food',
    'Hidden Gems',
    'Tours & Experiences',
    'Historical Landmarks',
    'Authentic Local Cuisine',
    'Eco-Tourism and Wildlife',
    'Art and Culture',
    'Adventure Sports',
    'Luxury Shopping',
    'Wellness and Spa',
    'Nightlife',
  ];

  const handleInterestToggle = (interest: string) => {
    setSelectedInterests(prev => {
      if (prev.includes(interest)) {
        return prev.filter(item => item !== interest);
      } else {
        return [...prev, interest];
      }
    });
  };

  const handleNext = () => {
    updateTripData({
      interests: selectedInterests,
    });
    setLocation('/trip-planning/eco-mode');
  };

  const handleBack = () => {
    setLocation('/trip-planning/food-preferences');
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
            <CardTitle className="text-3xl font-bold text-green-800 mb-2">
              Tell us what you're interested in
            </CardTitle>
            <CardDescription className="text-lg text-gray-600">
              Select all that apply
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-8">
            {/* Interest Options */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {interestOptions.map((interest) => {
                const isSelected = selectedInterests.includes(interest);
                
                return (
                  <Button
                    key={interest}
                    variant={isSelected ? "default" : "outline"}
                    onClick={() => handleInterestToggle(interest)}
                    className={`h-auto p-3 text-left justify-start ${
                      isSelected 
                        ? 'bg-green-600 hover:bg-green-700 text-white border-green-600' 
                        : 'border-green-200 text-green-800 hover:bg-green-50'
                    }`}
                  >
                    <div className="flex items-center space-x-2 w-full">
                      <span className="text-sm font-medium flex-1">{interest}</span>
                      {isSelected && <Check className="w-4 h-4 flex-shrink-0" />}
                    </div>
                  </Button>
                );
              })}
              
              {/* Add Custom Interest */}
              <Button
                variant="outline"
                className="h-auto p-3 text-left justify-start border-dashed border-green-300 text-green-600 hover:bg-green-50"
              >
                <div className="flex items-center space-x-2 w-full">
                  <Plus className="w-4 h-4 flex-shrink-0" />
                  <span className="text-sm font-medium">Add interest</span>
                </div>
              </Button>
            </div>

            {/* Selected Interests Summary */}
            {selectedInterests.length > 0 && (
              <div className="bg-green-50 p-4 rounded-lg">
                <h4 className="font-semibold text-green-800 mb-2">
                  Selected Interests ({selectedInterests.length})
                </h4>
                <div className="flex flex-wrap gap-2">
                  {selectedInterests.map((interest) => (
                    <Badge key={interest} variant="secondary" className="bg-green-100 text-green-800">
                      {interest}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Trip Summary */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="font-semibold text-gray-800 mb-2">Trip Summary</h4>
              <div className="space-y-1 text-sm text-gray-600">
                <div className="flex justify-between">
                  <span>Destination:</span>
                  <Badge variant="secondary" className="bg-green-100 text-green-800">
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
                    {tripData.companyType?.charAt(0).toUpperCase() + tripData.companyType?.slice(1)} Trip
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>Food:</span>
                  <Badge variant="outline">
                    {tripData.foodPreference?.charAt(0).toUpperCase() + tripData.foodPreference?.slice(1)}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>Interests:</span>
                  <span className="text-green-600 font-medium">
                    {selectedInterests.length} selected
                  </span>
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
                className="bg-green-600 hover:bg-green-700"
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

export default InterestsSelection;
