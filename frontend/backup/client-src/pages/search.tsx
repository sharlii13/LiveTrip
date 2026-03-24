import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Search, MapPin } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import DestinationCard from "@/components/destination-card";
import SearchFilters from "@/components/search-filters";
import { Card, CardContent } from "@/components/ui/card";
import { useTripPlanning } from "@/contexts/TripPlanningContext";
import type { Destination } from "@shared/schema";

export default function SearchPage() {
  const [, setLocation] = useLocation();
  const { updateTripData } = useTripPlanning();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchParams, setSearchParams] = useState({
    search: "",
    category: "",
    rating: null as number | null,
    priceRange: "",
    sort: "popularity"
  });

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
  };

  const handlePlanTrip = (destination: string) => {
    updateTripData({ destination });
    setLocation('/trip-planning/dates');
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

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Search Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-4" data-testid="text-page-title">
          Search Destinations
        </h1>
        <div className="flex flex-col md:flex-row gap-4 items-center">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <Input 
              type="text" 
              placeholder="Where do you want to go?" 
              className="pl-10 pr-4 py-3"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              data-testid="input-search"
            />
          </div>
          <Button 
            onClick={handleSearch}
            className="bg-primary text-primary-foreground hover:bg-primary/90"
            data-testid="button-search"
          >
            Search
          </Button>
        </div>
      </div>

      {/* Filters and Results */}
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
          
          {/* Pagination */}
          {destinations && destinations.length > 0 && (
            <div className="flex justify-center mt-12">
              <div className="flex items-center space-x-2">
                <Button variant="ghost" disabled data-testid="button-prev">
                  Previous
                </Button>
                <Button className="bg-primary text-primary-foreground" data-testid="button-page-1">
                  1
                </Button>
                <Button variant="ghost" data-testid="button-page-2">
                  2
                </Button>
                <Button variant="ghost" data-testid="button-page-3">
                  3
                </Button>
                <span className="px-3 py-2 text-muted-foreground">...</span>
                <Button variant="ghost" data-testid="button-last-page">
                  15
                </Button>
                <Button variant="ghost" data-testid="button-next">
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
