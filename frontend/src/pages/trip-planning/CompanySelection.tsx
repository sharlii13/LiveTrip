import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { User, Heart, Users, Home, PawPrint, Check } from 'lucide-react';
import { useTripPlanning } from '@/contexts/TripPlanningContext';
import ProgressIndicator from '@/components/ProgressIndicator';

const CompanySelection: React.FC = () => {
  const navigate = useNavigate();
  const { tripData, updateTripData, currentStep, totalSteps } = useTripPlanning();
  const [selectedCompany, setSelectedCompany] = useState<string | null>(tripData.companyType);
  const [withPets, setWithPets] = useState<boolean | null>(tripData.withPets);

  const companyOptions = [
    {
      id: 'solo',
      title: 'Solo Trip',
      icon: User,
      description: 'Traveling alone',
      color: 'bg-blue-50 border-blue-200 text-blue-800',
      selectedColor: 'bg-blue-600 border-blue-600 text-white',
    },
    {
      id: 'partner',
      title: 'Partner Trip',
      icon: Heart,
      description: 'Traveling with your partner',
      color: 'bg-pink-50 border-pink-200 text-pink-800',
      selectedColor: 'bg-pink-600 border-pink-600 text-white',
    },
    {
      id: 'friends',
      title: 'Friends Trip',
      icon: Users,
      description: 'Traveling with friends',
      color: 'bg-blue-50 border-blue-200 text-blue-800',
      selectedColor: 'bg-blue-600 border-blue-600 text-white',
    },
    {
      id: 'family',
      title: 'Family Trip',
      icon: Home,
      description: 'Traveling with family',
      color: 'bg-purple-50 border-purple-200 text-purple-800',
      selectedColor: 'bg-purple-600 border-purple-600 text-white',
    },
  ];

  const handleCompanySelect = (companyId: string) => {
    setSelectedCompany(companyId);
  };

  const handlePetToggle = (hasPets: boolean) => {
    setWithPets(hasPets);
  };

  const handleNext = () => {
    if (selectedCompany) {
      updateTripData({
        companyType: selectedCompany as any,
        withPets: withPets,
      });
      navigate('/trip-planning/food-preferences');
    }
  };

  const handleBack = () => {
    navigate('/trip-planning/dates');
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
              What kind of trip are you planning?
            </CardTitle>
            <CardDescription className="text-lg text-gray-600">
              Select one
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-8">
            {/* Company Type Selection */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {companyOptions.map((option) => {
                const Icon = option.icon;
                const isSelected = selectedCompany === option.id;
                
                return (
                  <div
                    key={option.id}
                    onClick={() => handleCompanySelect(option.id)}
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

            {/* Pet Question */}
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-semibold text-gray-800">
                  Are you traveling with pets?
                </h3>
                <div className="w-4 h-4 bg-gray-300 rounded-full flex items-center justify-center">
                  <span className="text-xs text-gray-600">i</span>
                </div>
              </div>
              
              <div className="flex space-x-4">
                <Button
                  variant={withPets === true ? "default" : "outline"}
                  onClick={() => handlePetToggle(true)}
                  className={`flex items-center space-x-2 ${
                    withPets === true 
                      ? 'bg-blue-600 hover:bg-blue-700 text-white' 
                      : 'border-gray-300 text-gray-700'
                  }`}
                >
                  <PawPrint className="w-4 h-4" />
                  <span>Yes</span>
                  {withPets === true && <Check className="w-4 h-4" />}
                </Button>
                
                <Button
                  variant={withPets === false ? "default" : "outline"}
                  onClick={() => handlePetToggle(false)}
                  className={`flex items-center space-x-2 ${
                    withPets === false 
                      ? 'bg-blue-600 hover:bg-blue-700 text-white' 
                      : 'border-gray-300 text-gray-700'
                  }`}
                >
                  <span>No</span>
                  {withPets === false && <Check className="w-4 h-4" />}
                </Button>
              </div>
            </div>

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
                {selectedCompany && (
                  <div className="flex justify-between">
                    <span>Company:</span>
                    <Badge variant="outline">
                      {companyOptions.find(opt => opt.id === selectedCompany)?.title}
                    </Badge>
                  </div>
                )}
                {withPets !== null && (
                  <div className="flex justify-between">
                    <span>Pets:</span>
                    <span>{withPets ? 'Yes' : 'No'}</span>
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
                disabled={!selectedCompany || withPets === null}
                className="bg-blue-600 hover:bg-blue-700"
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

export default CompanySelection;

