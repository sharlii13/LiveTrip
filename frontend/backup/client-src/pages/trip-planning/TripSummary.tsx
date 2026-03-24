import React from 'react';
import { useLocation } from 'wouter';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, Calendar, Users, Utensils, Leaf, MapPin } from 'lucide-react';
import { useTripPlanning } from '@/contexts/TripPlanningContext';
import LiveTripLogo from '@/components/LiveTripLogo';

const TripSummary: React.FC = () => {
  const [, setLocation] = useLocation();
  const { tripData, resetTripData } = useTripPlanning();

  const handleStartOver = () => {
    resetTripData();
    setLocation('/search');
  };

  const handleViewRecommendations = () => {
    setLocation('/');
  };

  const getDuration = () => {
    if (tripData.startDate && tripData.endDate) {
      const diffTime = Math.abs(tripData.endDate.getTime() - tripData.startDate.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
      return diffDays;
    }
    return 0;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-100">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Card className="w-full">
          <CardHeader className="text-center">
            <div className="flex items-center justify-center mb-4">
              <CheckCircle className="w-12 h-12 text-green-600 mr-3" />
              <LiveTripLogo size="lg" />
            </div>
            <CardTitle className="text-3xl font-bold text-green-800 mb-2">
              Trip Plan Created Successfully!
            </CardTitle>
            <CardDescription className="text-lg text-gray-600">
              Your personalized trip plan is ready
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-8">
            {/* Trip Overview */}
            <div className="bg-gradient-to-r from-green-50 to-blue-50 p-6 rounded-lg">
              <h3 className="text-xl font-semibold text-gray-800 mb-4">Trip Overview</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <div className="flex items-center space-x-3">
                    <MapPin className="w-5 h-5 text-green-600" />
                    <div>
                      <span className="text-sm text-gray-600">Destination</span>
                      <p className="font-semibold text-gray-800">{tripData.destination}</p>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-3">
                    <Calendar className="w-5 h-5 text-green-600" />
                    <div>
                      <span className="text-sm text-gray-600">Duration</span>
                      <p className="font-semibold text-gray-800">
                        {getDuration()} day{getDuration() > 1 ? 's' : ''}
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <div className="flex items-center space-x-3">
                    <Users className="w-5 h-5 text-green-600" />
                    <div>
                      <span className="text-sm text-gray-600">Travel Type</span>
                      <p className="font-semibold text-gray-800">
                        {tripData.companyType?.charAt(0).toUpperCase() + tripData.companyType?.slice(1)} Trip
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-3">
                    <Utensils className="w-5 h-5 text-green-600" />
                    <div>
                      <span className="text-sm text-gray-600">Food Preference</span>
                      <p className="font-semibold text-gray-800">
                        {tripData.foodPreference?.charAt(0).toUpperCase() + tripData.foodPreference?.slice(1)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Detailed Preferences */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Travel Details */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Travel Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Start Date:</span>
                    <span className="font-medium">{tripData.startDate?.toLocaleDateString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">End Date:</span>
                    <span className="font-medium">{tripData.endDate?.toLocaleDateString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Pets:</span>
                    <Badge variant="outline">
                      {tripData.withPets ? 'Yes' : 'No'}
                    </Badge>
                  </div>
                </CardContent>
              </Card>

              {/* Preferences */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Preferences</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Eco Mode:</span>
                    <Badge variant={tripData.ecoMode ? "default" : "outline"} className={tripData.ecoMode ? "bg-green-600" : ""}>
                      {tripData.ecoMode ? 'Enabled' : 'Disabled'}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Interests:</span>
                    <span className="font-medium text-green-600">
                      {tripData.interests.length} selected
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Selected Interests */}
            {tripData.interests.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Your Interests</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {tripData.interests.map((interest) => (
                      <Badge key={interest} variant="secondary" className="bg-green-100 text-green-800">
                        {interest}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Eco Mode Benefits */}
            {tripData.ecoMode && (
              <Card className="border-green-200 bg-green-50">
                <CardHeader>
                  <CardTitle className="text-lg text-green-800 flex items-center">
                    <Leaf className="w-5 h-5 mr-2" />
                    Eco-Friendly Features
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="text-sm text-green-700 space-y-1">
                    <li>• Sustainable accommodation recommendations</li>
                    <li>• Eco-friendly restaurant suggestions</li>
                    <li>• Carbon footprint tracking</li>
                    <li>• Green transportation options</li>
                    <li>• Local environmental initiatives</li>
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 pt-6">
              <Button 
                onClick={handleViewRecommendations}
                className="flex-1 bg-green-600 hover:bg-green-700"
              >
                View Recommendations
              </Button>
              
              <Button 
                variant="outline" 
                onClick={handleStartOver}
                className="flex-1"
              >
                Plan Another Trip
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default TripSummary;
