import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { Search, Bed, Utensils, Camera, Ticket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import DestinationCard from "@/components/destination-card";
import ReviewCard from "@/components/review-card";
import LiveTripLogo from "@/components/LiveTripLogo";
import type { Destination, ReviewWithUser } from "@shared/schema";

export default function Home() {
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

  return (
    <div>
      {/* Hero Section */}
      <section className="relative">
        <div 
          className="h-96 bg-cover bg-center relative"
          style={{
            backgroundImage: "url('https://images.unsplash.com/photo-1506905925346-21bda4d32df4?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&h=600')"
          }}
        >
          <div className="absolute inset-0 bg-black bg-opacity-40"></div>
          <div className="relative max-w-4xl mx-auto px-4 h-full flex flex-col justify-center items-center text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-4" data-testid="text-hero-title">
              Discover Your Next Adventure
            </h1>
            <p className="text-xl text-white/90 mb-8 max-w-2xl" data-testid="text-hero-subtitle">
              Find the perfect destination with millions of reviews from travelers like you
            </p>
            
            {/* Search Bar */}
            <div className="w-full max-w-2xl bg-white rounded-full search-shadow p-2">
              <div className="flex items-center">
                <div className="flex-1 flex items-center">
                  <Search className="text-muted-foreground ml-4 mr-3" />
                  <Input 
                    type="text" 
                    placeholder="Where do you want to go?" 
                    className="flex-1 border-0 outline-none focus:ring-0 focus:border-transparent"
                    data-testid="input-search-hero"
                  />
                </div>
                <Link href="/search">
                  <Button className="bg-primary text-primary-foreground px-6 py-3 rounded-full font-medium hover:bg-primary/90" data-testid="button-search-hero">
                    Search
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Popular Categories */}
      <section className="py-16 bg-secondary/30">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12" data-testid="text-categories-title">
            Explore by Category
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {/* Hotels Category */}
            <div className="text-center category-icon cursor-pointer" data-testid="category-hotels">
              <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Bed className="text-primary text-2xl" />
              </div>
              <h3 className="font-semibold text-foreground">Hotels</h3>
              <p className="text-muted-foreground text-sm">Find the perfect stay</p>
            </div>
            
            {/* Restaurants Category */}
            <div className="text-center category-icon cursor-pointer" data-testid="category-restaurants">
              <div className="w-16 h-16 bg-accent/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Utensils className="text-accent text-2xl" />
              </div>
              <h3 className="font-semibold text-foreground">Restaurants</h3>
              <p className="text-muted-foreground text-sm">Discover local cuisine</p>
            </div>
            
            {/* Attractions Category */}
            <div className="text-center category-icon cursor-pointer" data-testid="category-attractions">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Camera className="text-blue-600 text-2xl" />
              </div>
              <h3 className="font-semibold text-foreground">Attractions</h3>
              <p className="text-muted-foreground text-sm">Must-see places</p>
            </div>
            
            {/* Experiences Category */}
            <div className="text-center category-icon cursor-pointer" data-testid="category-experiences">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Ticket className="text-purple-600 text-2xl" />
              </div>
              <h3 className="font-semibold text-foreground">Experiences</h3>
              <p className="text-muted-foreground text-sm">Book unique activities</p>
            </div>
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
            <Link href="/search">
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
                <li><a href="#" className="hover:text-foreground">About Us</a></li>
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
