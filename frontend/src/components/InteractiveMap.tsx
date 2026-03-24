import React, { useState, useEffect, useRef } from 'react';
import { MapPin, Navigation, ZoomIn, ZoomOut, RotateCcw, Layers, Search, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import type { Destination } from '@shared/schema';

interface MapMarker {
  id: string;
  name: string;
  lat: number;
  lng: number;
  category: string;
  rating: number;
  image?: string;
}

interface InteractiveMapProps {
  destinations?: Destination[];
  selectedDestination?: string | null;
  onDestinationSelect?: (destination: Destination) => void;
  searchQuery?: string;
  className?: string;
}

const InteractiveMap: React.FC<InteractiveMapProps> = ({
  destinations = [],
  selectedDestination,
  onDestinationSelect,
  searchQuery = '',
  className = ''
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [currentView, setCurrentView] = useState<'satellite' | 'terrain' | 'roadmap'>('roadmap');
  const [zoom, setZoom] = useState(2);
  const [center, setCenter] = useState({ lat: 20, lng: 0 });
  const [selectedMarker, setSelectedMarker] = useState<MapMarker | null>(null);
  const [searchResults, setSearchResults] = useState<MapMarker[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchInput, setSearchInput] = useState(searchQuery);

  // Sample map markers (in a real app, these would come from your API)
  const mapMarkers: MapMarker[] = [
    {
      id: 'dest1',
      name: 'Eiffel Tower',
      lat: 48.8584,
      lng: 2.2945,
      category: 'attraction',
      rating: 4.8,
      image: 'https://images.unsplash.com/photo-1511739001486-6bfe10ce785f?w=300&h=200&fit=crop'
    },
    {
      id: 'dest2',
      name: 'Santorini',
      lat: 36.3932,
      lng: 25.4615,
      category: 'attraction',
      rating: 4.9,
      image: 'https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?w=300&h=200&fit=crop'
    },
    {
      id: 'dest3',
      name: 'Tokyo',
      lat: 35.6762,
      lng: 139.6503,
      category: 'city',
      rating: 4.7,
      image: 'https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=300&h=200&fit=crop'
    },
    {
      id: 'dest4',
      name: 'New York',
      lat: 40.7128,
      lng: -74.0060,
      category: 'city',
      rating: 4.6,
      image: 'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=300&h=200&fit=crop'
    },
    {
      id: 'dest5',
      name: 'Sydney Opera House',
      lat: -33.8568,
      lng: 151.2153,
      category: 'attraction',
      rating: 4.8,
      image: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=300&h=200&fit=crop'
    },
    {
      id: 'dest6',
      name: 'Machu Picchu',
      lat: -13.1631,
      lng: -72.5450,
      category: 'attraction',
      rating: 4.9,
      image: 'https://images.unsplash.com/photo-1526392060635-9d6019884377?w=300&h=200&fit=crop'
    }
  ];

  // Geocoding function to convert search query to coordinates
  const geocodeLocation = async (query: string): Promise<{ lat: number; lng: number; name: string } | null> => {
    // In a real app, you would use a geocoding service like Google Maps Geocoding API
    // For now, we'll use a simple mapping of common locations
    const locationMap: { [key: string]: { lat: number; lng: number; name: string } } = {
      'paris': { lat: 48.8566, lng: 2.3522, name: 'Paris, France' },
      'london': { lat: 51.5074, lng: -0.1278, name: 'London, UK' },
      'tokyo': { lat: 35.6762, lng: 139.6503, name: 'Tokyo, Japan' },
      'new york': { lat: 40.7128, lng: -74.0060, name: 'New York, USA' },
      'sydney': { lat: -33.8688, lng: 151.2093, name: 'Sydney, Australia' },
      'rome': { lat: 41.9028, lng: 12.4964, name: 'Rome, Italy' },
      'barcelona': { lat: 41.3851, lng: 2.1734, name: 'Barcelona, Spain' },
      'dubai': { lat: 25.2048, lng: 55.2708, name: 'Dubai, UAE' },
      'singapore': { lat: 1.3521, lng: 103.8198, name: 'Singapore' },
      'bangkok': { lat: 13.7563, lng: 100.5018, name: 'Bangkok, Thailand' },
      'mumbai': { lat: 19.0760, lng: 72.8777, name: 'Mumbai, India' },
      'delhi': { lat: 28.7041, lng: 77.1025, name: 'Delhi, India' },
      'eiffel tower': { lat: 48.8584, lng: 2.2945, name: 'Eiffel Tower, Paris' },
      'santorini': { lat: 36.3932, lng: 25.4615, name: 'Santorini, Greece' },
      'machu picchu': { lat: -13.1631, lng: -72.5450, name: 'Machu Picchu, Peru' },
      'sydney opera house': { lat: -33.8568, lng: 151.2153, name: 'Sydney Opera House, Australia' },
      'taj mahal': { lat: 27.1751, lng: 78.0421, name: 'Taj Mahal, India' },
      'colosseum': { lat: 41.8902, lng: 12.4922, name: 'Colosseum, Rome' },
      'statue of liberty': { lat: 40.6892, lng: -74.0445, name: 'Statue of Liberty, New York' },
      'big ben': { lat: 51.4994, lng: -0.1245, name: 'Big Ben, London' },
      'amsterdam': { lat: 52.3676, lng: 4.9041, name: 'Amsterdam, Netherlands' },
      'berlin': { lat: 52.5200, lng: 13.4050, name: 'Berlin, Germany' },
      'madrid': { lat: 40.4168, lng: -3.7038, name: 'Madrid, Spain' },
      'vienna': { lat: 48.2082, lng: 16.3738, name: 'Vienna, Austria' },
      'prague': { lat: 50.0755, lng: 14.4378, name: 'Prague, Czech Republic' },
      'istanbul': { lat: 41.0082, lng: 28.9784, name: 'Istanbul, Turkey' },
      'cairo': { lat: 30.0444, lng: 31.2357, name: 'Cairo, Egypt' },
      'cape town': { lat: -33.9249, lng: 18.4241, name: 'Cape Town, South Africa' },
      'rio de janeiro': { lat: -22.9068, lng: -43.1729, name: 'Rio de Janeiro, Brazil' },
      'buenos aires': { lat: -34.6118, lng: -58.3960, name: 'Buenos Aires, Argentina' },
      'mexico city': { lat: 19.4326, lng: -99.1332, name: 'Mexico City, Mexico' },
      'toronto': { lat: 43.6532, lng: -79.3832, name: 'Toronto, Canada' },
      'vancouver': { lat: 49.2827, lng: -123.1207, name: 'Vancouver, Canada' },
      'seoul': { lat: 37.5665, lng: 126.9780, name: 'Seoul, South Korea' },
      'hong kong': { lat: 22.3193, lng: 114.1694, name: 'Hong Kong' },
      'shanghai': { lat: 31.2304, lng: 121.4737, name: 'Shanghai, China' },
      'beijing': { lat: 39.9042, lng: 116.4074, name: 'Beijing, China' },
      'moscow': { lat: 55.7558, lng: 37.6176, name: 'Moscow, Russia' },
      'st petersburg': { lat: 59.9311, lng: 30.3609, name: 'St. Petersburg, Russia' }
    };

    const normalizedQuery = query.toLowerCase().trim();
    
    // Try exact match first
    if (locationMap[normalizedQuery]) {
      return locationMap[normalizedQuery];
    }
    
    // Try partial matches
    for (const [key, value] of Object.entries(locationMap)) {
      if (key.includes(normalizedQuery) || normalizedQuery.includes(key)) {
        return value;
      }
    }
    
    return null;
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'attraction':
        return 'bg-blue-500';
      case 'city':
        return 'bg-green-500';
      case 'hotel':
        return 'bg-purple-500';
      case 'restaurant':
        return 'bg-orange-500';
      default:
        return 'bg-gray-500';
    }
  };

  const handleSearch = async () => {
    if (!searchInput.trim()) return;
    
    setIsSearching(true);
    try {
      const location = await geocodeLocation(searchInput);
      if (location) {
        // Create a search result marker
        const searchMarker: MapMarker = {
          id: `search-${Date.now()}`,
          name: location.name,
          lat: location.lat,
          lng: location.lng,
          category: 'search',
          rating: 4.5,
          image: `https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=300&h=200&fit=crop&q=${encodeURIComponent(location.name)}`
        };
        
        setSearchResults([searchMarker]);
        setCenter({ lat: location.lat, lng: location.lng });
        setZoom(10);
        setSelectedMarker(searchMarker);
      } else {
        // If location not found, show a message
        setSearchResults([]);
        alert(`Location "${searchInput}" not found. Try searching for: Paris, London, Tokyo, New York, Sydney, Rome, Barcelona, Dubai, Singapore, Bangkok, Mumbai, Delhi, Eiffel Tower, Santorini, Machu Picchu, Sydney Opera House, Taj Mahal, Colosseum, Statue of Liberty, Big Ben`);
      }
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setIsSearching(false);
    }
  };

  const handleMarkerClick = (marker: MapMarker) => {
    setSelectedMarker(marker);
    setCenter({ lat: marker.lat, lng: marker.lng });
    setZoom(8);
    
    // Find the corresponding destination and call the callback
    const destination = destinations.find(dest => dest.name === marker.name);
    if (destination && onDestinationSelect) {
      onDestinationSelect(destination);
    }
  };

  const resetView = () => {
    setCenter({ lat: 20, lng: 0 });
    setZoom(2);
    setSelectedMarker(null);
    setSearchResults([]);
    setSearchInput('');
  };

  const toggleView = () => {
    const views: Array<'satellite' | 'terrain' | 'roadmap'> = ['roadmap', 'satellite', 'terrain'];
    const currentIndex = views.indexOf(currentView);
    const nextIndex = (currentIndex + 1) % views.length;
    setCurrentView(views[nextIndex]);
  };

  useEffect(() => {
    // Simulate map loading
    const timer = setTimeout(() => {
      setMapLoaded(true);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  // Handle search query from props
  useEffect(() => {
    if (searchQuery && searchQuery !== searchInput) {
      setSearchInput(searchQuery);
      handleSearch();
    }
  }, [searchQuery]);

  // Auto-search when searchInput changes from props
  useEffect(() => {
    if (searchInput && searchInput !== searchQuery) {
      const timer = setTimeout(() => {
        handleSearch();
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [searchInput]);

  return (
    <div className={`relative ${className}`}>
      {/* Map Container */}
      <div 
        ref={mapRef}
        className="relative w-full h-96 bg-gradient-to-br from-blue-100 to-blue-200 rounded-lg overflow-hidden border border-blue-200"
      >
        {!mapLoaded ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-blue-600 font-medium">Loading Map...</p>
            </div>
          </div>
        ) : (
          <>
            {/* Map Background Pattern */}
            <div className="absolute inset-0 bg-gradient-to-br from-blue-50 to-green-50">
              <div className="absolute inset-0 opacity-20">
                <svg width="100%" height="100%" viewBox="0 0 100 100" className="text-blue-300">
                  <defs>
                    <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
                      <path d="M 10 0 L 0 0 0 10" fill="none" stroke="currentColor" strokeWidth="0.5"/>
                    </pattern>
                  </defs>
                  <rect width="100%" height="100%" fill="url(#grid)" />
                </svg>
              </div>
            </div>

            {/* Search Input */}
            <div className="absolute top-4 left-4 right-4 z-10">
              <div className="flex space-x-2">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 w-4 h-4" />
                  <Input
                    type="text"
                    placeholder="Search for a location..."
                    className="pl-10 pr-4 py-2 bg-white/90 border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  />
                </div>
                <Button
                  onClick={handleSearch}
                  disabled={isSearching || !searchInput.trim()}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4"
                >
                  {isSearching ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Search className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>

            {/* Map Markers */}
            {[...mapMarkers, ...searchResults].map((marker) => (
              <div
                key={marker.id}
                className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer group"
                style={{
                  left: `${((marker.lng + 180) / 360) * 100}%`,
                  top: `${((90 - marker.lat) / 180) * 100}%`,
                }}
                onClick={() => handleMarkerClick(marker)}
              >
                <div className={`w-6 h-6 rounded-full ${marker.category === 'search' ? 'bg-red-500 animate-pulse' : getCategoryColor(marker.category)} shadow-lg group-hover:scale-125 transition-transform duration-200 flex items-center justify-center`}>
                  <MapPin className="w-3 h-3 text-white" />
                </div>
                
                {/* Marker Label */}
                <div className="absolute top-8 left-1/2 transform -translate-x-1/2 bg-white rounded-lg px-2 py-1 shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 whitespace-nowrap">
                  <p className="text-xs font-medium text-gray-800">{marker.name}</p>
                  <div className="flex items-center space-x-1">
                    <span className="text-xs text-yellow-500">★</span>
                    <span className="text-xs text-gray-600">{marker.rating}</span>
                  </div>
                </div>
              </div>
            ))}

            {/* Map Controls */}
            <div className="absolute top-16 right-4 flex flex-col space-y-2">
              <Button
                size="sm"
                variant="secondary"
                className="w-8 h-8 p-0 bg-white/90 hover:bg-white shadow-lg"
                onClick={() => setZoom(Math.min(zoom + 1, 10))}
                title="Zoom In"
              >
                <ZoomIn className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                variant="secondary"
                className="w-8 h-8 p-0 bg-white/90 hover:bg-white shadow-lg"
                onClick={() => setZoom(Math.max(zoom - 1, 1))}
                title="Zoom Out"
              >
                <ZoomOut className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                variant="secondary"
                className="w-8 h-8 p-0 bg-white/90 hover:bg-white shadow-lg"
                onClick={resetView}
                title="Reset View"
              >
                <RotateCcw className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                variant="secondary"
                className="w-8 h-8 p-0 bg-white/90 hover:bg-white shadow-lg"
                onClick={toggleView}
                title="Change View"
              >
                <Layers className="w-4 h-4" />
              </Button>
            </div>

            {/* Map Info */}
            <div className="absolute bottom-4 left-4 bg-white/90 rounded-lg px-3 py-2 shadow-lg">
              <div className="flex items-center space-x-2">
                <Navigation className="w-4 h-4 text-blue-600" />
                <span className="text-sm font-medium text-gray-800">
                  {currentView.charAt(0).toUpperCase() + currentView.slice(1)} View
                </span>
                <Badge variant="outline" className="text-xs">
                  Zoom: {zoom}x
                </Badge>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Selected Marker Info */}
      {selectedMarker && (
        <Card className="absolute top-4 left-4 w-80 z-10 animate-slide-in-left">
          <CardContent className="p-4">
            <div className="flex items-start space-x-3">
              <img
                src={selectedMarker.image}
                alt={selectedMarker.name}
                className="w-16 h-16 rounded-lg object-cover"
              />
              <div className="flex-1">
                <h3 className="font-semibold text-gray-800">{selectedMarker.name}</h3>
                <div className="flex items-center space-x-2 mt-1">
                  <Badge className={`${getCategoryColor(selectedMarker.category)} text-white text-xs`}>
                    {selectedMarker.category}
                  </Badge>
                  <div className="flex items-center space-x-1">
                    <span className="text-yellow-500 text-sm">★</span>
                    <span className="text-sm text-gray-600">{selectedMarker.rating}</span>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {selectedMarker.lat.toFixed(4)}, {selectedMarker.lng.toFixed(4)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Map Legend */}
      <div className="absolute bottom-4 right-4 bg-white/90 rounded-lg px-3 py-2 shadow-lg">
        <h4 className="text-xs font-semibold text-gray-800 mb-2">Legend</h4>
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
            <span className="text-xs text-gray-600">Attractions</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span className="text-xs text-gray-600">Cities</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
            <span className="text-xs text-gray-600">Hotels</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InteractiveMap;
