import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { Search, Bed, Utensils, Camera, Ticket, MapPin, Users, Star, TrendingUp, Globe, Heart, Share2, Bookmark, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import DestinationCard from "@/components/destination-card";
import ReviewCard from "@/components/review-card";
import LiveTripLogo from "@/components/LiveTripLogo";
import InteractiveMap from "@/components/InteractiveMap";
import { useTripPlanning } from "@/contexts/TripPlanningContext";
import type { Destination, ReviewWithUser } from "@shared/schema";

export default function Home() {
  const { updateTripData } = useTripPlanning();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");

  const { data: destinations, isLoading } = useQuery<Destination[]>({
    queryKey: ["/api/destinations"],
    queryFn: async () => {
      const response = await fetch("/api/destinations?limit=3");
      if (!response.ok) throw new Error("Failed to fetch destinations");
      return response.json();
    }
  });

  const { data: recentReviews } = useQuery<ReviewWithUser[]>({
    queryKey: ["/api/destinations", "recent-reviews"],
    queryFn: async () => {
      // Get reviews from first few destinations
      const response = await fetch("/api/destinations/dest1/reviews");
      if (!response.ok) return [];
      const reviews = await response.json();
      return reviews.slice(0, 3);
    }
  });

  // Trip planning handlers
  const handleSearch = () => {
    if (searchQuery.trim()) {
      updateTripData({ destination: searchQuery.trim() });
      navigate('/trip-planning');
    }
  };

  return (
    <div>
          {/* Hero Section with Video */}
          <section className="relative">
            <div className="h-[700px] relative overflow-hidden">
              {/* Video Background */}
              <video
                autoPlay
                muted
                loop
                playsInline
                className="absolute inset-0 w-full h-full object-cover"
              >
                <source src="/videos/hero-video.mp4" type="video/mp4" />
                <source src="/videos/hero-video.webm" type="video/webm" />
                {/* Fallback image if video doesn't load */}
                <div
                  className="w-full h-full bg-cover bg-center"
                  style={{
                    backgroundImage: "url('https://images.unsplash.com/photo-1506905925346-21bda4d32df4?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&h=700')"
                  }}
                />
              </video>

              {/* Floating Elements */}
              <div className="absolute inset-0 overflow-hidden">
                <div className="absolute top-20 left-10 w-16 h-16 bg-blue-500/20 rounded-full animate-bounce" style={{ animationDelay: '0s', animationDuration: '3s' }}></div>
                <div className="absolute top-40 right-20 w-12 h-12 bg-white/20 rounded-full animate-bounce" style={{ animationDelay: '1s', animationDuration: '4s' }}></div>
                <div className="absolute bottom-40 left-20 w-20 h-20 bg-blue-400/20 rounded-full animate-bounce" style={{ animationDelay: '2s', animationDuration: '3.5s' }}></div>
                <div className="absolute bottom-20 right-10 w-14 h-14 bg-white/30 rounded-full animate-bounce" style={{ animationDelay: '0.5s', animationDuration: '4.5s' }}></div>
              </div>

              {/* Overlay */}
              <div className="absolute inset-0 bg-black bg-opacity-40"></div>
              <div className="relative max-w-4xl mx-auto px-4 h-full flex flex-col justify-center items-center text-center">
                <h1 className="text-4xl md:text-6xl font-bold text-white mb-6 animate-slide-up" data-testid="text-hero-title">
                  Discover Your Next Adventure
                </h1>
                <p className="text-xl text-white/90 mb-8 max-w-2xl animate-slide-up" data-testid="text-hero-subtitle" style={{ animationDelay: '0.2s' }}>
                  Find the perfect destination with millions of reviews from travelers like you
                </p>
            
                    {/* Search Bar */}
                    <div className="w-full max-w-2xl bg-white rounded-full search-shadow p-2 animate-slide-up" style={{ animationDelay: '0.4s' }}>
                      <div className="flex items-center">
                        <div className="flex-1 flex items-center">
                          <Search className="text-muted-foreground ml-4 mr-3" />
                          <Input 
                            type="text" 
                            placeholder="Where do you want to go?" 
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                            className="flex-1 border-0 outline-none focus:ring-0 focus:border-transparent"
                            data-testid="input-search-hero"
                          />
                        </div>
                        <Button 
                          onClick={handleSearch}
                          className="bg-blue-600 text-white px-6 py-3 rounded-full font-medium hover:bg-blue-700 transition-all duration-300 hover:scale-105" 
                          data-testid="button-search-hero"
                        >
                          Search
                        </Button>
                      </div>
                    </div>

              </div>
            </div>
          </section>


      {/* Tagline Section */}
      <section className="py-12 bg-gradient-to-r from-blue-50 to-indigo-100">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <div className="flex justify-center mb-6">
            <LiveTripLogo size="lg" />
          </div>
          <p className="text-2xl md:text-3xl font-semibold text-gray-800 tracking-wide">
            ✈️ your trip, your mood, your way - all live 🌍
          </p>
        </div>
      </section>

      {/* Popular Categories */}
      <section className="py-20 bg-gradient-to-br from-indigo-50 via-white to-purple-50 relative overflow-hidden">
        {/* Background decorative elements */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-10 -right-10 w-40 h-40 bg-blue-200 rounded-full opacity-20 animate-pulse"></div>
          <div className="absolute top-1/2 -left-20 w-32 h-32 bg-purple-200 rounded-full opacity-20 animate-pulse delay-1000"></div>
          <div className="absolute bottom-10 right-1/4 w-24 h-24 bg-pink-200 rounded-full opacity-20 animate-pulse delay-500"></div>
        </div>
        
        <div className="max-w-7xl mx-auto px-4 relative z-10">
          <div className="text-center mb-16">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full mb-6">
              <Target className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent mb-6" data-testid="text-categories-title">
              Explore by Category
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
              Discover amazing places and experiences tailored to your interests. 
              <span className="text-blue-600 font-semibold"> Start your journey today!</span>
            </p>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {/* Hotels Category */}
            <div className="group relative" data-testid="category-hotels">
              <div className="bg-white rounded-3xl p-8 shadow-lg hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-4 hover:scale-105 border border-gray-100 group-hover:border-blue-200">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-blue-600/10 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                <div className="relative z-10">
                  <div className="w-20 h-20 bg-gradient-to-br from-blue-400 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:shadow-lg group-hover:shadow-blue-200 transition-all duration-500 group-hover:scale-110">
                    <Bed className="text-white text-3xl" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-800 mb-3 group-hover:text-blue-600 transition-colors duration-300">Hotels</h3>
                  <p className="text-gray-600 mb-4 group-hover:text-blue-500 transition-colors duration-300">Find the perfect stay</p>
                  <div className="flex items-center justify-center space-x-2 text-sm text-blue-500 font-semibold">
                    <Star className="w-4 h-4 fill-current" />
                    <span>12,000+ options</span>
                  </div>
                  <div className="mt-4 text-xs text-gray-400 group-hover:text-blue-400 transition-colors duration-300">
                    From luxury resorts to cozy B&Bs
                  </div>
                </div>
              </div>
            </div>
            
            {/* Restaurants Category */}
            <div className="group relative" data-testid="category-restaurants">
              <div className="bg-white rounded-3xl p-8 shadow-lg hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-4 hover:scale-105 border border-gray-100 group-hover:border-orange-200">
                <div className="absolute inset-0 bg-gradient-to-br from-orange-500/5 to-orange-600/10 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                <div className="relative z-10">
                  <div className="w-20 h-20 bg-gradient-to-br from-orange-400 to-orange-600 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:shadow-lg group-hover:shadow-orange-200 transition-all duration-500 group-hover:scale-110">
                    <Utensils className="text-white text-3xl" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-800 mb-3 group-hover:text-orange-600 transition-colors duration-300">Restaurants</h3>
                  <p className="text-gray-600 mb-4 group-hover:text-orange-500 transition-colors duration-300">Discover local cuisine</p>
                  <div className="flex items-center justify-center space-x-2 text-sm text-orange-500 font-semibold">
                    <Heart className="w-4 h-4 fill-current" />
                    <span>8,500+ places</span>
                  </div>
                  <div className="mt-4 text-xs text-gray-400 group-hover:text-orange-400 transition-colors duration-300">
                    From street food to fine dining
                  </div>
                </div>
              </div>
            </div>
            
            {/* Attractions Category */}
            <div className="group relative" data-testid="category-attractions">
              <div className="bg-white rounded-3xl p-8 shadow-lg hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-4 hover:scale-105 border border-gray-100 group-hover:border-green-200">
                <div className="absolute inset-0 bg-gradient-to-br from-green-500/5 to-green-600/10 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                <div className="relative z-10">
                  <div className="w-20 h-20 bg-gradient-to-br from-green-400 to-green-600 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:shadow-lg group-hover:shadow-green-200 transition-all duration-500 group-hover:scale-110">
                    <Camera className="text-white text-3xl" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-800 mb-3 group-hover:text-green-600 transition-colors duration-300">Attractions</h3>
                  <p className="text-gray-600 mb-4 group-hover:text-green-500 transition-colors duration-300">Must-see places</p>
                  <div className="flex items-center justify-center space-x-2 text-sm text-green-500 font-semibold">
                    <Globe className="w-4 h-4" />
                    <span>15,000+ sites</span>
                  </div>
                  <div className="mt-4 text-xs text-gray-400 group-hover:text-green-400 transition-colors duration-300">
                    Iconic landmarks and hidden gems
                  </div>
                </div>
              </div>
            </div>
            
            {/* Experiences Category */}
            <div className="group relative" data-testid="category-experiences">
              <div className="bg-white rounded-3xl p-8 shadow-lg hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-4 hover:scale-105 border border-gray-100 group-hover:border-purple-200">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-purple-600/10 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                <div className="relative z-10">
                  <div className="w-20 h-20 bg-gradient-to-br from-purple-400 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:shadow-lg group-hover:shadow-purple-200 transition-all duration-500 group-hover:scale-110">
                    <Ticket className="text-white text-3xl" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-800 mb-3 group-hover:text-purple-600 transition-colors duration-300">Experiences</h3>
                  <p className="text-gray-600 mb-4 group-hover:text-purple-500 transition-colors duration-300">Book unique activities</p>
                  <div className="flex items-center justify-center space-x-2 text-sm text-purple-500 font-semibold">
                    <TrendingUp className="w-4 h-4" />
                    <span>3,200+ activities</span>
                  </div>
                  <div className="mt-4 text-xs text-gray-400 group-hover:text-purple-400 transition-colors duration-300">
                    Adventure, culture, and local experiences
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          {/* Call to Action */}
          <div className="text-center mt-16">
            <div className="inline-flex items-center space-x-4 bg-gradient-to-r from-blue-500 to-purple-500 text-white px-8 py-4 rounded-full shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 cursor-pointer">
              <Search className="w-5 h-5" />
              <span className="font-semibold">Explore All Categories</span>
              <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
            </div>
          </div>
        </div>
      </section>

          {/* Interactive Map Section */}
      <section className="py-16 bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4" data-testid="text-map-title">
              🌍 Explore the World
            </h2>
            <p className="text-gray-600 max-w-2xl mx-auto mb-8">
              Discover amazing destinations around the globe with our interactive map
            </p>
<Link to="/map">
              <Button className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-full font-medium hover:scale-105 transition-all duration-300">
                <Globe className="w-5 h-5 mr-2" />
                Open Interactive Map
              </Button>
            </Link>
          </div>
          
          <div className="max-w-4xl mx-auto">
            <InteractiveMap 
              destinations={destinations}
              className="h-96 rounded-lg shadow-xl"
            />
          </div>
        </div>
      </section>

      {/* Featured Destinations */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex justify-between items-center mb-12">
            <h2 className="text-3xl font-bold" data-testid="text-featured-title">
              Featured Destinations
            </h2>
<Link to="/search">
              <Button variant="ghost" className="text-primary font-medium hover:underline" data-testid="button-view-all">
                View all destinations
              </Button>
            </Link>
          </div>
          
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="animate-pulse">
                  <div className="w-full h-48 bg-muted"></div>
                  <CardContent className="p-6">
                    <div className="h-4 bg-muted rounded mb-2"></div>
                    <div className="h-3 bg-muted rounded w-2/3 mb-4"></div>
                    <div className="h-3 bg-muted rounded w-1/2"></div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {destinations?.map((destination) => (
                <DestinationCard key={destination.id} destination={destination} />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Popular Reviews Section */}
      <section className="py-16 bg-secondary/30">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12" data-testid="text-reviews-title">
            Recent Traveler Reviews
          </h2>
          {recentReviews && recentReviews.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {recentReviews.map((review) => (
                <ReviewCard key={review.id} review={review} />
              ))}
            </div>
          ) : (
            <div className="text-center text-muted-foreground">
              <p>No recent reviews available</p>
            </div>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-secondary/30 py-12 mt-16">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center mb-4">
                <Search className="text-primary text-xl mr-2" />
                <LiveTripLogo size="sm" showText={false} />
              </div>
              <p className="text-muted-foreground text-sm">
                Discover amazing places and plan your perfect trip with millions of reviews from travelers worldwide.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Explore</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground">Destinations</a></li>
                <li><a href="#" className="hover:text-foreground">Hotels</a></li>
                <li><a href="#" className="hover:text-foreground">Restaurants</a></li>
                <li><a href="#" className="hover:text-foreground">Attractions</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Company</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
<Link to="/about" className="hover:text-foreground">About Us</Link>
                <li><a href="#" className="hover:text-foreground">Careers</a></li>
                <li><a href="#" className="hover:text-foreground">Press</a></li>
                <li><a href="#" className="hover:text-foreground">Contact</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Support</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground">Help Center</a></li>
                <li><a href="#" className="hover:text-foreground">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-foreground">Terms of Service</a></li>
                <li><a href="#" className="hover:text-foreground">Community Guidelines</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-border mt-8 pt-8 text-center text-sm text-muted-foreground">
            <p>&copy; 2024 LiveTrip. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
