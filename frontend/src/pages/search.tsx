import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Search, MapPin, Calendar, User, Heart, Users, Home, PawPrint, Leaf, Utensils, Check, ChevronLeft, ChevronRight, Map, List, Shield, Globe, CheckCircle, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
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
import DestinationCard from "@/components/destination-card";
import SearchFilters from "@/components/search-filters";
import InteractiveMap from "@/components/InteractiveMap";
import { useTripPlanning } from "@/contexts/TripPlanningContext";
import type { Destination } from "@shared/schema";
import PlanningOverlay from "@/components/livetrip/PlanningOverlay";
import { rememberTrip } from "@/lib/livetrip";

export default function SearchPage() {
  const navigate = useNavigate();
  const { tripData, updateTripData } = useTripPlanning();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchParams, setSearchParams] = useState({
    search: "",
    category: "",
    rating: null as number | null,
    priceRange: "",
    sort: "popularity"
  });

  // Trip planning states
  const [selectedDestination, setSelectedDestination] = useState<string | null>(null);
  const [showTripPlanning, setShowTripPlanning] = useState(false);
  const [tripStep, setTripStep] = useState(1);
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
  const [viewMode, setViewMode] = useState<'list' | 'map'>('list');
  
  // Emergency contact states
  const [emergencyName, setEmergencyName] = useState('');
  const [emergencyPhone, setEmergencyPhone] = useState('');
  const [emergencyRelation, setEmergencyRelation] = useState('');
  
  // Language preference states
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [languageSearch, setLanguageSearch] = useState('');

  const { data: destinations, isLoading } = useQuery<Destination[]>({
    queryKey: ["/api/destinations", searchParams],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (searchParams.search) params.append("search", searchParams.search);
      if (searchParams.category) params.append("category", searchParams.category);
      if (searchParams.rating) params.append("rating", searchParams.rating.toString());
      if (searchParams.priceRange) params.append("priceRange", searchParams.priceRange);
      
      const response = await fetch(`/api/destinations?${params.toString()}`);
      if (!response.ok) throw new Error("Failed to fetch destinations");
      return response.json();
    }
  });

  const handleSearch = () => {
    setSearchParams(prev => ({ ...prev, search: searchQuery }));
    setShowTripPlanning(false);
    setTripStep(1);
  };

  const handlePlanTrip = (destination: string) => {
    setSelectedDestination(destination);
    updateTripData({ destination });
    setShowTripPlanning(true);
    setTripStep(1);
  };

  const handleFiltersChange = (filters: {
    categories: string[];
    rating: number | null;
    priceRanges: string[];
  }) => {
    setSearchParams(prev => ({
      ...prev,
      category: filters.categories[0] || "",
      rating: filters.rating,
      priceRange: filters.priceRanges[0] || "",
    }));
  };

  // Trip planning options
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
      color: 'bg-green-50 border-green-200 text-green-800',
      selectedColor: 'bg-green-600 border-green-600 text-white',
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

  const foodOptions = [
    {
      id: 'vegetarian',
      title: 'Vegetarian',
      icon: Leaf,
      description: 'Plant-based meals only',
      color: 'bg-green-50 border-green-200 text-green-800',
      selectedColor: 'bg-green-600 border-green-600 text-white',
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
      color: 'bg-blue-50 border-blue-200 text-blue-800',
      selectedColor: 'bg-blue-600 border-blue-600 text-white',
    },
  ];

  const interestOptions = [
    { id: 'attractions', label: 'Attractions', icon: '🏛️' },
    { id: 'food', label: 'Food & Dining', icon: '🍽️' },
    { id: 'culture', label: 'Culture & History', icon: '🎭' },
    { id: 'nature', label: 'Nature & Outdoors', icon: '🌲' },
    { id: 'adventure', label: 'Adventure Sports', icon: '🏄' },
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

  const handleNextStep = () => {
    if (tripStep < 8) {
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
      const response = await fetch('/api/trips', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          ...tripData,
          destination: selectedDestination,
          startDate: selectedDates.from,
          endDate: selectedDates.to,
          companyType: selectedCompany,
          withPets: withPets,
          foodPreference: selectedFoodPreference,
          interests: selectedInterests,
          ecoMode: ecoMode,
          transportPreference: selectedTransport,
          emergencyContact: {
            name: emergencyName,
            phone: emergencyPhone,
            relation: emergencyRelation,
          },
          languages: selectedLanguages,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setShowTripPlanning(false);
        setTripStep(1);
        rememberTrip(result.id);
        navigate(`/trips/${result.id}`);
      } else {
        console.error('Failed to create trip');
        const err = await response.json().catch(() => ({}));
        alert(err.detail || 'Failed to create trip plan. Please try again.');
      }
    } catch (error) {
      console.error('Error creating trip:', error);
      alert('Error creating trip plan. Please try again.');
    }
  };

  const getDuration = () => {
    if (selectedDates.from && selectedDates.to) {
      const diffTime = Math.abs(selectedDates.to.getTime() - selectedDates.from.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
      return diffDays;
    }
    return 0;
  };

  const isDateDisabled = (date: Date) => {
    return date < new Date();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
    <PlanningOverlay open={submitting} destination={selectedDestination ?? undefined} />
    <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Search Header with Video */}
      <div className="mb-8">
          <div className="relative h-64 rounded-lg overflow-hidden mb-6">
            <video
              autoPlay
              muted
              loop
              playsInline
              className="absolute inset-0 w-full h-full object-cover"
            >
                <source src="/videos/hero-video.mp4" type="video/mp4" />
                <source src="/videos/hero-video.webm" type="video/webm" />
            </video>
            <div className="absolute inset-0 bg-black bg-opacity-30"></div>
            <div className="relative h-full flex items-center justify-center">
              <h1 className="text-4xl md:text-5xl font-bold text-white text-center" data-testid="text-page-title">
          Search Destinations
        </h1>
            </div>
          </div>
        <div className="flex flex-col md:flex-row gap-4 items-center">
          <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-blue-600 w-4 h-4" />
            <Input 
              type="text" 
              placeholder="Where do you want to go?" 
                className="pl-10 pr-4 py-3 border-blue-300 focus:border-blue-500 focus:ring-blue-500"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              data-testid="input-search"
            />
          </div>
          <Button 
            onClick={handleSearch}
              className="bg-blue-600 text-white hover:bg-blue-700"
            data-testid="button-search"
          >
            Search
          </Button>
        </div>
      </div>

        {!showTripPlanning ? (
          /* Search Results */
      <div className="flex flex-col lg:flex-row gap-8">
        {/* Filters Sidebar */}
        <div className="lg:w-1/4">
          <SearchFilters onFiltersChange={handleFiltersChange} />
        </div>

        {/* Search Results */}
        <div className="lg:w-3/4">
          <div className="flex justify-between items-center mb-6">
            <p className="text-muted-foreground" data-testid="text-results-count">
              {destinations ? `Showing ${destinations.length} results` : "Loading..."}
            </p>
                <div className="flex items-center space-x-4">
                  {/* View Toggle */}
                  <div className="flex items-center space-x-2">
                    <Button
                      variant={viewMode === 'list' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setViewMode('list')}
                      className="flex items-center space-x-2"
                    >
                      <List className="w-4 h-4" />
                      <span>List</span>
                    </Button>
                    <Button
                      variant={viewMode === 'map' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setViewMode('map')}
                      className="flex items-center space-x-2"
                    >
                      <Map className="w-4 h-4" />
                      <span>Map</span>
                    </Button>
                  </div>
                  
            <Select defaultValue="popularity">
              <SelectTrigger className="w-48" data-testid="select-sort">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="popularity">Sort by: Popularity</SelectItem>
                <SelectItem value="rating">Highest Rated</SelectItem>
                <SelectItem value="price-low">Price: Low to High</SelectItem>
                <SelectItem value="price-high">Price: High to Low</SelectItem>
              </SelectContent>
            </Select>
                </div>
          </div>
          
              {viewMode === 'map' ? (
                /* Map View */
                <div className="h-[600px] rounded-lg overflow-hidden shadow-lg">
                  <InteractiveMap
                    destinations={destinations}
                    searchQuery={searchQuery}
                    className="h-full"
                  />
                </div>
              ) : (
                /* List View */
                <>
          {isLoading ? (
            <div className="space-y-6">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="animate-pulse">
                  <div className="md:flex">
                    <div className="w-full md:w-1/3 h-48 bg-muted"></div>
                    <CardContent className="p-6 flex-1">
                      <div className="h-6 bg-muted rounded mb-2"></div>
                      <div className="h-4 bg-muted rounded w-2/3 mb-3"></div>
                      <div className="h-4 bg-muted rounded mb-4"></div>
                      <div className="h-4 bg-muted rounded w-1/2"></div>
                    </CardContent>
                  </div>
                </Card>
              ))}
            </div>
          ) : destinations && destinations.length > 0 ? (
            <div className="space-y-6">
              {destinations.map((destination) => (
                <DestinationCard 
                  key={destination.id} 
                  destination={destination} 
                  variant="search"
                          onPlanTrip={handlePlanTrip}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-muted-foreground text-lg" data-testid="text-no-results">
                No destinations found. Try adjusting your search criteria.
              </p>
            </div>
          )}
                </>
              )}
            </div>
          </div>
        ) : (
          /* Trip Planning Flow */
          <div className="max-w-4xl mx-auto">
            <Card className="w-full">
              <CardHeader className="text-center">
                <div className="flex items-center justify-between mb-4">
                  <Button variant="outline" onClick={() => setShowTripPlanning(false)}>
                    <ChevronLeft className="w-4 h-4 mr-2" />
                    Back to Search
                  </Button>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-gray-600">Step {tripStep} of 8</span>
                      <div className="w-32 bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${(tripStep / 8) * 100}%` }}
                        ></div>
                      </div>
                  </div>
                </div>
                <CardTitle className="text-3xl font-bold text-blue-800 mb-2">
                  {tripStep === 1 && "When are you going?"}
                  {tripStep === 2 && "What kind of trip are you planning?"}
                  {tripStep === 3 && "What are your food preferences?"}
                  {tripStep === 4 && "What are your interests?"}
                  {tripStep === 5 && "Choose your eco-friendly options"}
                  {tripStep === 6 && "Emergency Contact Information"}
                  {tripStep === 7 && "Language Preferences"}
                  {tripStep === 8 && "Trip Summary"}
                </CardTitle>
                <CardDescription className="text-lg text-gray-600">
                  {tripStep === 1 && "Choose a date range, up to 7 days"}
                  {tripStep === 2 && "Select one"}
                  {tripStep === 3 && "This helps us recommend the best restaurants and dining experiences"}
                  {tripStep === 4 && "Select all that apply"}
                  {tripStep === 5 && "Help us make your trip more sustainable"}
                  {tripStep === 6 && "For your safety during the trip"}
                  {tripStep === 7 && "Select languages you're comfortable with"}
                  {tripStep === 8 && "Review your trip details"}
                </CardDescription>
              </CardHeader>
              
              <CardContent className="space-y-6">
                {/* Step 1: Date Selection */}
                {tripStep === 1 && (
                  <div className="flex justify-center">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <h3 className="text-lg font-semibold text-blue-800">Select Dates</h3>
                        </div>
                        <CalendarComponent
                          mode="range"
                          selected={selectedDates}
                          onSelect={(range) => {
                            if (range?.from) {
                              setSelectedDates(prev => ({ ...prev, from: range.from }));
                            }
                            if (range?.to) {
                              setSelectedDates(prev => ({ ...prev, to: range.to }));
                            }
                          }}
                          disabled={isDateDisabled}
                          className="rounded-md border"
                        />
                      </div>
                      <div className="space-y-4">
                        <h3 className="text-lg font-semibold text-blue-800">Trip Summary</h3>
                        <div className="space-y-3">
                          <div className="flex justify-between">
                            <span className="text-gray-600">Destination:</span>
                            <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                              {selectedDestination}
                            </Badge>
                          </div>
                          {selectedDates.from && (
                            <div className="flex justify-between">
                              <span className="text-gray-600">Start Date:</span>
                              <span className="font-medium">
                                {selectedDates.from.toLocaleDateString()}
                              </span>
                            </div>
                          )}
                          {selectedDates.to && (
                            <div className="flex justify-between">
                              <span className="text-gray-600">End Date:</span>
                              <span className="font-medium">
                                {selectedDates.to.toLocaleDateString()}
                              </span>
                            </div>
                          )}
                          {getDuration() > 0 && (
                            <div className="flex justify-between">
                              <span className="text-gray-600">Duration:</span>
                              <Badge variant="outline" className="bg-blue-50 text-blue-800">
                                {getDuration()} day{getDuration() > 1 ? 's' : ''}
                              </Badge>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Step 2: Company Selection */}
                {tripStep === 2 && (
                  <div className="space-y-8">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {companyOptions.map((option) => {
                        const Icon = option.icon;
                        const isSelected = selectedCompany === option.id;
                        
                        return (
                          <div
                            key={option.id}
                            onClick={() => setSelectedCompany(option.id)}
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

                    <div className="space-y-4">
              <div className="flex items-center space-x-2">
                        <h3 className="text-lg font-semibold text-gray-800">
                          Are you traveling with pets?
                        </h3>
                      </div>
                      
                      <div className="flex space-x-4">
                        <Button
                          variant={withPets === true ? "default" : "outline"}
                          onClick={() => setWithPets(true)}
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
                          onClick={() => setWithPets(false)}
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
                  </div>
                )}

                {/* Step 3: Food Preferences */}
                {tripStep === 3 && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {foodOptions.map((option) => {
                      const Icon = option.icon;
                      const isSelected = selectedFoodPreference === option.id;
                      
                      return (
                        <div
                          key={option.id}
                          onClick={() => setSelectedFoodPreference(option.id)}
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
                )}

                {/* Step 4: Interests */}
                {tripStep === 4 && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {interestOptions.map((option) => {
                      const isSelected = selectedInterests.includes(option.id);
                      
                      return (
                        <div
                          key={option.id}
                          onClick={() => {
                            if (isSelected) {
                              setSelectedInterests(prev => prev.filter(id => id !== option.id));
                            } else {
                              setSelectedInterests(prev => [...prev, option.id]);
                            }
                          }}
                          className={`p-4 rounded-lg border-2 cursor-pointer transition-all duration-200 hover:shadow-md ${
                            isSelected 
                              ? 'border-blue-500 bg-blue-50' 
                              : 'border-gray-200 bg-white hover:shadow-sm'
                          }`}
                        >
                          <div className="text-center">
                            <div className="text-2xl mb-2">{option.icon}</div>
                            <h4 className={`font-medium text-sm ${isSelected ? 'text-blue-800' : 'text-gray-800'}`}>
                              {option.label}
                            </h4>
                            {isSelected && <Check className="w-4 h-4 text-blue-600 mx-auto mt-2" />}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Step 5: Eco Mode */}
                {tripStep === 5 && (
                  <div className="space-y-8">
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
                          onCheckedChange={setEcoMode}
                          className="data-[state=checked]:bg-blue-600"
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
                                    ? 'border-blue-500 bg-blue-50' 
                                    : 'border-gray-200 bg-white hover:shadow-sm'
                                }`}
                              >
                                <div className="text-center">
                                  <div className="text-2xl mb-2">{option.icon}</div>
                                  <h4 className={`font-medium text-sm ${isSelected ? 'text-blue-800' : 'text-gray-800'}`}>
                                    {option.title}
                                  </h4>
                                  <p className={`text-xs ${isSelected ? 'text-blue-600' : 'text-gray-600'}`}>
                                    Eco Score: {option.ecoScore}/10
                                  </p>
                                  {isSelected && <Check className="w-4 h-4 text-blue-600 mx-auto mt-2" />}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Step 6: Emergency Contact */}
                {tripStep === 6 && (
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

                {/* Step 7: Language Preferences */}
                {tripStep === 7 && (
                  <div className="space-y-6">
                    <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                      <div className="flex items-center mb-4">
                        <Globe className="w-6 h-6 text-green-600 mr-2" />
                        <h3 className="text-lg font-semibold text-green-800">Language Preferences</h3>
                      </div>
                      <p className="text-green-700 mb-4">
                        Select the languages you're comfortable with for better recommendations
                      </p>
                      <div className="space-y-4">
                        <div>
                          <Label htmlFor="languageSearch" className="text-sm font-medium">
                            Search Languages
                          </Label>
                          <div className="relative mt-1">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                            <Input
                              id="languageSearch"
                              type="text"
                              placeholder="Search for languages..."
                              value={languageSearch}
                              onChange={(e) => setLanguageSearch(e.target.value)}
                              className="pl-10 border-green-300 focus:border-green-500 focus:ring-green-500"
                            />
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto border border-green-200 rounded-lg p-3">
                          {['English 🇺🇸', 'Spanish 🇪🇸', 'French 🇫🇷', 'German 🇩🇪', 'Italian 🇮🇹', 'Portuguese 🇵🇹', 'Russian 🇷🇺', 'Japanese 🇯🇵', 'Korean 🇰🇷', 'Chinese 🇨🇳', 'Arabic 🇸🇦', 'Hindi 🇮🇳'].map((lang) => {
                            const isSelected = selectedLanguages.includes(lang);
                            return (
                              <label key={lang} className="flex items-center space-x-2 p-2 hover:bg-green-100 rounded cursor-pointer">
                                <input 
                                  type="checkbox" 
                                  checked={isSelected}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setSelectedLanguages([...selectedLanguages, lang]);
                                    } else {
                                      setSelectedLanguages(selectedLanguages.filter(l => l !== lang));
                                    }
                                  }}
                                  className="border-green-500 text-green-600 focus:ring-green-500" 
                                />
                                <span className="text-sm">{lang}</span>
                              </label>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Step 8: Trip Summary */}
                {tripStep === 8 && (
                  <div className="space-y-6">
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                      <div className="flex items-center mb-4">
                        <CheckCircle className="w-6 h-6 text-blue-600 mr-2" />
                        <h3 className="text-lg font-semibold text-blue-800">Trip Summary</h3>
                      </div>
                      <p className="text-blue-700 mb-4">
                        Review your trip details and create your personalized travel plan
                      </p>
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Destination:</span>
                          <Badge className="bg-blue-100 text-blue-800">
                            {selectedDestination || "Not selected"}
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
                      (tripStep === 2 && (!selectedCompany || withPets === null)) ||
                      (tripStep === 3 && !selectedFoodPreference) ||
                      (tripStep === 4 && selectedInterests.length === 0) ||
                      (tripStep === 6 && (!emergencyName.trim() || !emergencyPhone.trim() || !emergencyRelation.trim())) ||
                      (tripStep === 7 && selectedLanguages.length === 0) ||
                      submitting
                    }
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    {submitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                    {tripStep === 8 ? (submitting ? 'Building your itinerary...' : 'Create Trip Plan') : 'Next'}
                    {tripStep < 8 && <ChevronRight className="w-4 h-4 ml-2" />}
                  </Button>
                </div>
              </CardContent>
            </Card>
        </div>
        )}
      </div>
    </div>
  );
}
