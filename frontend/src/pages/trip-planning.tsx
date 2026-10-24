import { useState } from "react";
import LanguageChecklist from "@/components/LanguageChecklist";
import { useNavigate } from "react-router-dom";
import { Search, Bed, Utensils, Camera, Ticket, MapPin, Users, Star, TrendingUp, Globe, Heart, Share2, Bookmark, ChevronLeft, ChevronRight, Check, Shield, Leaf, PawPrint, Home as HomeIcon, CheckCircle, Calendar, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Calendar as CalendarComponent } from "@/components/ui/calendar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useTripPlanning } from "@/contexts/TripPlanningContext";
import LiveTripLogo from "@/components/LiveTripLogo";
import { api, localDate as toLocalDate, rememberTrip } from "@/lib/livetrip";
import PlanningOverlay from "@/components/livetrip/PlanningOverlay";

export default function TripPlanning() {
  const navigate = useNavigate();
  const { tripData, updateTripData } = useTripPlanning();
  const [tripStep, setTripStep] = useState(1);
  
  // Trip planning states
  const [selectedDates, setSelectedDates] = useState<{ from: Date | undefined; to: Date | undefined }>({
    from: tripData.startDate || undefined,
    to: tripData.endDate || undefined,
  });
  const [selectedCompany, setSelectedCompany] = useState<string | null>(tripData.companyType);
  const [withPets, setWithPets] = useState<boolean | null>(tripData.withPets);
  const [selectedFoodPreference, setSelectedFoodPreference] = useState<string | null>(tripData.foodPreference);
  const [selectedInterests, setSelectedInterests] = useState<string[]>(tripData.interests || []);
  const [ecoMode, setEcoMode] = useState<boolean>(tripData.ecoMode);
  const [selectedTransport, setSelectedTransport] = useState<string>('');
  
  // Emergency contact states
  const [emergencyName, setEmergencyName] = useState('');
  const [emergencyPhone, setEmergencyPhone] = useState('');
  const [emergencyRelation, setEmergencyRelation] = useState('');
  
  // Language preference states
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // Trip planning options
  const companyOptions = [
    { id: 'solo', label: 'Solo', icon: '🧑', description: 'Traveling alone' },
    { id: 'partner', label: 'Couple', icon: '👫', description: 'With my partner' },
    { id: 'friends', label: 'Friends', icon: '👥', description: 'With friends' },
    { id: 'family', label: 'Family', icon: '👨‍👩‍👧‍👦', description: 'With family' },
  ];

  const foodOptions = [
    { id: 'vegetarian', label: 'Vegetarian', icon: '🥗', description: 'Plant-based meals' },
    { id: 'non-vegetarian', label: 'Non-Vegetarian', icon: '🥩', description: 'All types of food' },
    { id: 'both', label: 'Both', icon: '🍽️', description: 'Open to everything' },
  ];

  const interestOptions = [
    { id: 'adventure', label: 'Adventure', icon: '🏔️' },
    { id: 'culture', label: 'Culture', icon: '🏛️' },
    { id: 'nature', label: 'Nature', icon: '🌿' },
    { id: 'food', label: 'Food', icon: '🍜' },
    { id: 'nightlife', label: 'Nightlife', icon: '🌃' },
    { id: 'shopping', label: 'Shopping', icon: '🛍️' },
    { id: 'relaxation', label: 'Relaxation', icon: '🧘' },
  ];

  const transportOptions = [
    { id: 'walking', title: 'Walking', icon: '🚶', ecoScore: 10 },
    { id: 'bicycle', title: 'Bicycle', icon: '🚴', ecoScore: 9 },
    { id: 'public-transport', title: 'Public Transport', icon: '🚌', ecoScore: 8 },
    { id: 'train', title: 'Train', icon: '🚂', ecoScore: 7 },
    { id: 'car', title: 'Car', icon: '🚗', ecoScore: 4 },
    { id: 'plane', title: 'Plane', icon: '✈️', ecoScore: 2 },
  ];

  // Trip planning handlers
  const handleNextStep = () => {
    if (tripStep < 7) {
      setTripStep(tripStep + 1);
    } else if (!submitting) {
      setSubmitting(true);
      handleSubmitTrip().finally(() => setSubmitting(false));
    }
  };

  const handlePrevStep = () => {
    if (tripStep > 1) {
      setTripStep(tripStep - 1);
    }
  };

  const handleSubmitTrip = async () => {
    try {
      // Update trip data with current form data
      const updatedTripData = {
        startDate: selectedDates.from,
        endDate: selectedDates.to,
        companyType: selectedCompany as any,
        withPets: !!withPets,
        foodPreference: selectedFoodPreference as any,
        interests: selectedInterests,
        ecoMode: ecoMode,
        transportPreference: selectedTransport,
        emergencyContact: {
          name: emergencyName,
          phone: emergencyPhone,
          relation: emergencyRelation,
        },
        languages: selectedLanguages,
      };

      updateTripData(updatedTripData);

      // Create and save a live itinerary on the backend, then open it
      try {
        if (!selectedDates.from || !selectedDates.to || !tripData.destination) {
          throw new Error('Missing required trip information');
        }
        const transport = selectedTransport || 'car';  // car/taxi unless chosen on the eco step
        const trip = await api<{ id: string }>('/api/trips', {
          method: 'POST',
          json: {
            destination: tripData.destination,
            startDate: toLocalDate(selectedDates.from),
            endDate: toLocalDate(selectedDates.to),
            companyType: selectedCompany,
            withPets: !!withPets,
            foodPreference: selectedFoodPreference,
            interests: selectedInterests,
            ecoMode,
            transportPreference: transport,
            pace: 'normal',
            budget: tripData.budget,
          },
        });
        updateTripData({ ...updatedTripData, itineraryId: trip.id, backendItinerary: trip } as any);
        rememberTrip(trip.id);
        navigate(`/trips/${trip.id}`);
      } catch (apiError) {
        alert(`Could not create the itinerary: ${(apiError as Error).message}`);
      }

    } catch (error) {
      console.error('Error creating trip:', error);
      // Still redirect to itinerary page even if there's an error
      navigate('/itinerary');
    }
  };

  const getDuration = () => {
    if (selectedDates.from && selectedDates.to) {
      const diffTime = Math.abs(selectedDates.to.getTime() - selectedDates.from.getTime());
      return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
    }
    return 0;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 to-brand-100 py-8">
      <PlanningOverlay open={submitting} destination={tripData.destination} />
      <div className="max-w-4xl mx-auto px-4">
        <Card className="w-full">
          <CardHeader>
            <div className="flex items-center justify-between mb-4">
<Button variant="outline" onClick={() => navigate('/')}>
                <ChevronLeft className="w-4 h-4 mr-2" />
                Back to Home
              </Button>
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600">Step {tripStep} of 7</span>
                <div className="w-32 bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-brand-700 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${(tripStep / 7) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
            <CardTitle className="text-3xl font-bold text-brand-800 mb-2">
              {tripStep === 1 && "When are you going?"}
              {tripStep === 2 && "What kind of trip are you planning?"}
              {tripStep === 3 && "What are your food preferences?"}
              {tripStep === 4 && "Choose your eco-friendly options"}
              {tripStep === 5 && "Emergency Contact Information"}
              {tripStep === 6 && "Language Preferences"}
              {tripStep === 7 && "Trip Summary"}
            </CardTitle>
            <CardDescription className="text-lg text-gray-600">
              {tripStep === 1 && "Choose a date range, up to 7 days"}
              {tripStep === 2 && "Select one"}
              {tripStep === 3 && "This helps us recommend the best restaurants and dining experiences"}
              {tripStep === 4 && "Help us make your trip more sustainable"}
              {tripStep === 5 && "For your safety during the trip"}
              {tripStep === 6 && "Select languages you're comfortable with"}
              {tripStep === 7 && "Review your trip details"}
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {/* Step 1: Date Selection */}
            {tripStep === 1 && (
              <div className="space-y-8">
                <div className="flex justify-center">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold text-brand-800">Start Date</h3>
                      <CalendarComponent
                        mode="single"
                        selected={selectedDates.from}
                        onSelect={(date) => setSelectedDates(prev => ({ ...prev, from: date }))}
                        className="rounded-md border"
                      />
                    </div>
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold text-brand-800">End Date</h3>
                      <CalendarComponent
                        mode="single"
                        selected={selectedDates.to}
                        onSelect={(date) => setSelectedDates(prev => ({ ...prev, to: date }))}
                        className="rounded-md border"
                      />
                    </div>
                  </div>
                </div>
                
              </div>
            )}

            {/* Step 2: Company Type */}
            {tripStep === 2 && (
              <div className="space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {companyOptions.map((option) => (
                    <div
                      key={option.id}
                      onClick={() => setSelectedCompany(option.id)}
                      className={`p-6 rounded-lg border-2 cursor-pointer transition-all duration-200 ${
                        selectedCompany === option.id
                          ? 'border-brand-500 bg-brand-50'
                          : 'border-gray-200 bg-white hover:border-brand-300'
                      }`}
                    >
                      <div className="text-center">
                        <div className="text-4xl mb-3">{option.icon}</div>
                        <h3 className="text-lg font-semibold mb-2">{option.label}</h3>
                        <p className="text-sm text-gray-600">{option.description}</p>
                        {selectedCompany === option.id && (
                          <Check className="w-6 h-6 text-brand-700 mx-auto mt-3" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                
                <div className="flex items-center justify-center space-x-4">
                  <span className="text-sm font-medium">Traveling with pets?</span>
                  <Switch
                    checked={withPets || false}
                    onCheckedChange={setWithPets}
                    className="data-[state=checked]:bg-brand-700"
                  />
                  <PawPrint className="w-5 h-5 text-gray-600" />
                </div>
              </div>
            )}

            {/* Step 3: Food Preferences */}
            {tripStep === 3 && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {foodOptions.map((option) => (
                  <div
                    key={option.id}
                    onClick={() => setSelectedFoodPreference(option.id)}
                    className={`p-6 rounded-lg border-2 cursor-pointer transition-all duration-200 ${
                      selectedFoodPreference === option.id
                        ? 'border-brand-500 bg-brand-50'
                        : 'border-gray-200 bg-white hover:border-brand-300'
                    }`}
                  >
                    <div className="text-center">
                      <div className="text-4xl mb-3">{option.icon}</div>
                      <h3 className="text-lg font-semibold mb-2">{option.label}</h3>
                      <p className="text-sm text-gray-600">{option.description}</p>
                      {selectedFoodPreference === option.id && (
                        <Check className="w-6 h-6 text-brand-700 mx-auto mt-3" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Step 4: Eco-friendly Options */}
            {tripStep === 4 && (
              <div className="space-y-8">
                <div className="bg-brand-50 p-6 rounded-lg border border-brand-200">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <Leaf className="w-6 h-6 text-brand-700" />
                      <div>
                        <h3 className="text-lg font-semibold text-brand-800">Eco Mode</h3>
                        <p className="text-sm text-brand-700">
                          Enable eco-friendly recommendations and sustainable travel options
                        </p>
                      </div>
                    </div>
                    <Switch
                      checked={ecoMode}
                      onCheckedChange={setEcoMode}
                      className="data-[state=checked]:bg-brand-700"
                    />
                  </div>
                </div>

                {ecoMode && (
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-gray-800">
                      Preferred Transportation
                    </h3>
                    <p className="text-sm text-gray-600">
                      Select your preferred way to get around (optional)
                    </p>
                    
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {transportOptions.map((option) => {
                        const isSelected = selectedTransport === option.id;
                        
                        return (
                          <div
                            key={option.id}
                            onClick={() => setSelectedTransport(option.id)}
                            className={`p-4 rounded-lg border-2 cursor-pointer transition-all duration-200 hover:shadow-md ${
                              isSelected 
                                ? 'border-brand-500 bg-brand-50' 
                                : 'border-gray-200 bg-white hover:shadow-sm'
                            }`}
                          >
                            <div className="text-center">
                              <div className="text-2xl mb-2">{option.icon}</div>
                              <h4 className={`font-medium text-sm ${isSelected ? 'text-brand-800' : 'text-gray-800'}`}>
                                {option.title}
                              </h4>
                              <p className={`text-xs ${isSelected ? 'text-brand-700' : 'text-gray-600'}`}>
                                Eco Score: {option.ecoScore}/10
                              </p>
                              {isSelected && <Check className="w-4 h-4 text-brand-700 mx-auto mt-2" />}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Step 5: Emergency Contact */}
            {tripStep === 5 && (
              <div className="space-y-6">
                <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                  <div className="flex items-center mb-4">
                    <Shield className="w-6 h-6 text-red-600 mr-2" />
                    <h3 className="text-lg font-semibold text-red-800">Emergency Contact</h3>
                  </div>
                  <p className="text-red-700 mb-4">
                    Please provide emergency contact details for your safety during the trip
                  </p>
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="emergencyName" className="text-sm font-medium">
                        Emergency Contact Name *
                      </Label>
                      <Input
                        id="emergencyName"
                        type="text"
                        placeholder="Enter full name"
                        value={emergencyName}
                        onChange={(e) => setEmergencyName(e.target.value)}
                        className="mt-1 border-red-300 focus:border-red-500 focus:ring-red-500"
                      />
                    </div>
                    <div>
                      <Label htmlFor="emergencyPhone" className="text-sm font-medium">
                        Emergency Contact Phone *
                      </Label>
                      <Input
                        id="emergencyPhone"
                        type="tel"
                        placeholder="+1 (555) 123-4567"
                        value={emergencyPhone}
                        onChange={(e) => setEmergencyPhone(e.target.value)}
                        className="mt-1 border-red-300 focus:border-red-500 focus:ring-red-500"
                      />
                    </div>
                    <div>
                      <Label htmlFor="emergencyRelation" className="text-sm font-medium">
                        Relationship *
                      </Label>
                      <Input
                        id="emergencyRelation"
                        type="text"
                        placeholder="e.g., Spouse, Parent, Sibling, Friend"
                        value={emergencyRelation}
                        onChange={(e) => setEmergencyRelation(e.target.value)}
                        className="mt-1 border-red-300 focus:border-red-500 focus:ring-red-500"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Step 6: Language Preferences */}
            {tripStep === 6 && (
              <div className="space-y-6">
                <div className="bg-brand-50 border border-brand-200 rounded-lg p-6">
                  <div className="flex items-center mb-4">
                    <Globe className="w-6 h-6 text-brand-700 mr-2" />
                    <h3 className="text-lg font-semibold text-brand-800">Language Preferences</h3>
                  </div>
                  <p className="text-brand-700 mb-4">
                    Select the languages you're comfortable with for better recommendations
                  </p>
                  <LanguageChecklist selected={selectedLanguages} onChange={setSelectedLanguages} />
                </div>
              </div>
            )}

            {/* Step 7: Trip Summary */}
            {tripStep === 7 && (
              <div className="space-y-6">
                <div className="bg-brand-50 border border-brand-200 rounded-lg p-6">
                  <div className="flex items-center mb-4">
                    <CheckCircle className="w-6 h-6 text-brand-700 mr-2" />
                    <h3 className="text-lg font-semibold text-brand-800">Trip Summary</h3>
                  </div>
                  <p className="text-brand-700 mb-4">
                    Review your trip details and create your personalized travel plan
                  </p>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Destination:</span>
                      <Badge className="bg-brand-100 text-brand-800">
                        {tripData.destination || "Not selected"}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Dates:</span>
                      <span className="text-sm font-medium">
                        {selectedDates.from ? selectedDates.from.toLocaleDateString() : "Not set"} - 
                        {selectedDates.to ? selectedDates.to.toLocaleDateString() : "Not set"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Company:</span>
                      <span className="text-sm font-medium">{selectedCompany || "Not selected"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Food:</span>
                      <span className="text-sm font-medium">{selectedFoodPreference || "Not selected"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Eco Mode:</span>
                      <span className="text-sm font-medium">{ecoMode ? "Enabled" : "Disabled"}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Navigation */}
            <div className="flex justify-between pt-6">
              <Button variant="outline" onClick={handlePrevStep} disabled={tripStep === 1}>
                <ChevronLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              
              <Button 
                onClick={handleNextStep}
                disabled={
                  (tripStep === 1 && (!selectedDates.from || !selectedDates.to || getDuration() > 7)) ||
                  (tripStep === 2 && !selectedCompany) ||
                  (tripStep === 3 && !selectedFoodPreference) ||
                  (tripStep === 5 && (!emergencyName.trim() || !emergencyPhone.trim() || !emergencyRelation.trim())) ||
                  (tripStep === 6 && selectedLanguages.length === 0) ||
                  submitting
                }
                className="bg-brand-700 hover:bg-brand-800"
              >
                {submitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                {tripStep === 7 ? (submitting ? 'Building your itinerary...' : 'Create Trip Plan') : 'Next'}
                {tripStep < 7 && <ChevronRight className="w-4 h-4 ml-2" />}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
