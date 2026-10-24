import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Filter, List, Map as MapIcon, Navigation, Globe } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import DestinationsMap from '@/components/DestinationsMap';
import { useNavigate } from 'react-router-dom';
import { useTripPlanning } from '@/contexts/TripPlanningContext';
import DestinationCard from '@/components/destination-card';
import PageHero from '@/components/PageHero';
import type { Destination } from '@shared/schema';

export default function MapPage() {
  const [viewMode, setViewMode] = useState<'map' | 'list' | 'split'>('split');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedDestination, setSelectedDestination] = useState<Destination | null>(null);
  const navigate = useNavigate();
  const { updateTripData } = useTripPlanning();

  const { data: destinations, isLoading } = useQuery<Destination[]>({
    queryKey: ['/api/destinations'],
    queryFn: async () => {
      const response = await fetch('/api/destinations');
      if (!response.ok) throw new Error('Failed to fetch destinations');
      return response.json();
    }
  });

  const filteredDestinations = destinations?.filter(dest => {
    const matchesSearch = dest.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         dest.location.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || dest.category === selectedCategory;
    return matchesSearch && matchesCategory;
  }) || [];

  const handleDestinationSelect = (destination: Destination) => {
    setSelectedDestination(destination);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 to-brand-100">
      <PageHero title="Explore destinations" clip="map" icon={<Globe className="w-6 h-6" />}
                subtitle="Every destination on a live map. Tap a pin to see it and plan a trip there.">
        {/* View Mode Toggle */}
        <div className="flex items-center space-x-2">
          <Button
            variant={viewMode === 'map' ? 'default' : 'secondary'}
            size="sm"
            onClick={() => setViewMode('map')}
            className="flex items-center space-x-2"
          >
            <MapIcon className="w-4 h-4" />
            <span>Map</span>
          </Button>
          <Button
            variant={viewMode === 'list' ? 'default' : 'secondary'}
            size="sm"
            onClick={() => setViewMode('list')}
            className="flex items-center space-x-2"
          >
            <List className="w-4 h-4" />
            <span>List</span>
          </Button>
          <Button
            variant={viewMode === 'split' ? 'default' : 'secondary'}
            size="sm"
            onClick={() => setViewMode('split')}
            className="flex items-center space-x-2"
          >
            <Navigation className="w-4 h-4" />
            <span>Split</span>
          </Button>
        </div>
      </PageHero>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Search and Filters */}
        <div className="mb-6">
          <div className="flex flex-col md:flex-row gap-4 items-center">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
              <Input
                type="text"
                placeholder="Search destinations..."
                className="pl-10 pr-4 py-3 border-brand-300 focus:border-brand-500 focus:ring-brand-500"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                <SelectItem value="attraction">Attractions</SelectItem>
                <SelectItem value="hotel">Hotels</SelectItem>
                <SelectItem value="restaurant">Restaurants</SelectItem>
                <SelectItem value="experience">Experiences</SelectItem>
              </SelectContent>
            </Select>

            <Button className="bg-brand-700 hover:bg-brand-800">
              <Filter className="w-4 h-4 mr-2" />
              Filters
            </Button>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Map Section */}
          {(viewMode === 'map' || viewMode === 'split') && (
            <div className={`${viewMode === 'split' ? 'lg:col-span-1' : 'col-span-2'}`}>
              <Card className="h-[600px]">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Globe className="w-5 h-5 text-brand-700" />
                    <span>Interactive Map</span>
                    <Badge variant="outline" className="ml-auto">
                      {filteredDestinations.length} destinations
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0 h-[calc(100%-80px)]">
                  <DestinationsMap
                    destinations={filteredDestinations}
                    selectedId={selectedDestination?.id}
                    onSelect={handleDestinationSelect}
                    onPlan={(d) => { updateTripData({ destination: d.location }); navigate('/trip-planning'); }}
                    className="h-full rounded-none border-0 shadow-none"
                  />
                </CardContent>
              </Card>
            </div>
          )}

          {/* List Section */}
          {(viewMode === 'list' || viewMode === 'split') && (
            <div className={`${viewMode === 'split' ? 'lg:col-span-1' : 'col-span-2'}`}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>Destinations</span>
                    <Badge variant="outline">
                      {filteredDestinations.length} found
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="max-h-[600px] overflow-y-auto">
                  {isLoading ? (
                    <div className="space-y-4">
                      {[1, 2, 3].map((i) => (
                        <div key={i} className="animate-pulse">
                          <div className="h-32 bg-gray-200 rounded-lg"></div>
                        </div>
                      ))}
                    </div>
                  ) : filteredDestinations.length > 0 ? (
                    <div className="space-y-4">
                      {filteredDestinations.map((destination) => (
                        <div
                          key={destination.id}
                          className={`p-4 rounded-lg border-2 cursor-pointer transition-all duration-200 hover:shadow-md ${
                            selectedDestination?.id === destination.id
                              ? 'border-brand-500 bg-brand-50'
                              : 'border-gray-200 hover:border-brand-300'
                          }`}
                          onClick={() => handleDestinationSelect(destination)}
                        >
                          <div className="flex items-start space-x-3">
                            <img
                              src={destination.images?.[0] || 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=100&h=100&fit=crop'}
                              alt={destination.name}
                              className="w-16 h-16 rounded-lg object-cover"
                            />
                            <div className="flex-1">
                              <h3 className="font-semibold text-gray-800">{destination.name}</h3>
                              <p className="text-sm text-gray-600">{destination.location}, {destination.country}</p>
                              <div className="flex items-center space-x-2 mt-2">
                                <Badge variant="secondary" className="text-xs">
                                  {destination.category}
                                </Badge>
                                <div className="flex items-center space-x-1">
                                  <span className="text-yellow-500 text-sm">★</span>
                                  <span className="text-sm text-gray-600">{destination.rating}</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12">
                      <Globe className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <p className="text-gray-600">No destinations found</p>
                      <p className="text-sm text-gray-500">Try adjusting your search criteria</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </div>

        {/* Selected Destination Details */}
        {selectedDestination && (
          <Card className="mt-6 animate-slide-up">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Selected Destination</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedDestination(null)}
                >
                  Close
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DestinationCard
                destination={selectedDestination}
                variant="search"
                onPlanTrip={(name) => {
                  // Handle trip planning
                  console.log('Plan trip for:', name);
                }}
              />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
