import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { Search, Bed, Utensils, Camera, Ticket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import DestinationCard from "@/components/destination-card";
import ReviewCard from "@/components/review-card";
import LiveTripLogo from "@/components/LiveTripLogo";
import { useTripPlanning } from "@/contexts/TripPlanningContext";
import JourneyStory from "@/components/home/JourneyStory";
import VideoCategoryCard from "@/components/home/VideoCategoryCard";
import DestinationTicker from "@/components/home/DestinationTicker";
import Reveal from "@/components/home/Reveal";
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


      {/* Tagline + destination ticker */}
      <section className="relative py-12 bg-gradient-to-r from-blue-600 via-indigo-600 to-emerald-500 overflow-hidden">
        <Reveal className="max-w-4xl mx-auto px-4 text-center mb-6">
          <p className="text-2xl md:text-3xl font-semibold text-white tracking-wide">
            ✈️ your trip, your mood, your way - all live 🌍
          </p>
          <p className="text-white/80 mt-2">Tap a destination to start planning</p>
        </Reveal>
        <DestinationTicker onPick={(place) => { updateTripData({ destination: place }); navigate('/trip-planning'); }} />
      </section>

      {/* How it works: scroll story */}
      <JourneyStory />

      {/* Categories: video cards */}
      <section className="py-20 bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 relative z-10">
          <Reveal className="text-center mb-14">
            <h2 className="text-4xl md:text-5xl font-black text-white mb-4" data-testid="text-categories-title">
              Explore by <span className="bg-gradient-to-r from-sky-400 to-emerald-400 bg-clip-text text-transparent">category</span>
            </h2>
            <p className="text-lg text-white/70 max-w-2xl mx-auto">Hover a card to take a peek.</p>
          </Reveal>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <VideoCategoryCard to="/search" clip="stays" title="Stays" subtitle="Houseboats to hill-top hotels" count={12000}
                               unit="options" note="From luxury resorts to cozy homestays" accent="from-sky-500 to-blue-600"
                               icon={<Bed className="w-6 h-6 text-white" />} />
            <VideoCategoryCard to="/search" clip="food" title="Food" subtitle="Eat like a local" count={8500} unit="places"
                               note="From street food to sunset dinners" accent="from-orange-400 to-rose-500"
                               icon={<Utensils className="w-6 h-6 text-white" />} delay={0.1} />
            <VideoCategoryCard to="/map" clip="sights" title="Sights" subtitle="Must-see places" count={15000} unit="sites"
                               note="Iconic landmarks and hidden gems" accent="from-emerald-400 to-teal-600"
                               icon={<Camera className="w-6 h-6 text-white" />} delay={0.2} />
            <VideoCategoryCard to="/search" clip="experiences" title="Experiences" subtitle="Treks, cruises and more" count={3200}
                               unit="activities" note="Adventure, culture and local experiences" accent="from-violet-500 to-fuchsia-500"
                               icon={<Ticket className="w-6 h-6 text-white" />} delay={0.3} />
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
              {destinations?.map((destination, i) => (
                <Reveal key={destination.id} delay={i * 0.12}>
                  <DestinationCard destination={destination} />
                </Reveal>
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
              {recentReviews.map((review, i) => (
                <Reveal key={review.id} delay={i * 0.12}>
                  <ReviewCard review={review} />
                </Reveal>
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
