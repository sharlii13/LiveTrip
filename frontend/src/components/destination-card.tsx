import { Link } from "react-router-dom";
import { MapPin, Calendar, Heart, Share2, Bookmark, Eye, Users, TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import StarRating from "./star-rating";
import type { Destination } from "@shared/schema";
import { useState } from "react";

interface DestinationCardProps {
  destination: Destination;
  variant?: "default" | "search";
  onPlanTrip?: (destination: string) => void;
}

export default function DestinationCard({ destination, variant = "default", onPlanTrip }: DestinationCardProps) {
  const [isLiked, setIsLiked] = useState(false);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [showShareMenu, setShowShareMenu] = useState(false);

  const categoryColors = {
    hotel: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    restaurant: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200", 
    attraction: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    experience: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200"
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: destination.name,
        text: `Check out ${destination.name} on LiveTrip!`,
        url: window.location.href
      });
    } else {
      navigator.clipboard.writeText(window.location.href);
      setShowShareMenu(false);
    }
  };

  if (variant === "search") {
    return (
<Link to={`/destinations/${destination.id}`} data-testid={`link-destination-${destination.id}`}>
        <Card className="group overflow-hidden hover:shadow-2xl transition-all duration-300 cursor-pointer transform hover:-translate-y-1" data-testid={`card-destination-${destination.id}`}>
          <div className="md:flex">
            <div className="relative w-full md:w-1/3 h-48 md:h-auto overflow-hidden">
              <img 
                src={destination.images?.[0] || "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=600&h=300"}
                alt={destination.name}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                data-testid={`img-destination-${destination.id}`}
              />
              {/* Overlay with action buttons */}
              <div className="absolute top-3 right-3 flex space-x-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                <Button
                  size="sm"
                  variant="secondary"
                  className="h-8 w-8 p-0 bg-white/90 hover:bg-white"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setIsLiked(!isLiked);
                  }}
                >
                  <Heart className={`w-4 h-4 ${isLiked ? 'fill-red-500 text-red-500' : 'text-gray-600'}`} />
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  className="h-8 w-8 p-0 bg-white/90 hover:bg-white"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setIsBookmarked(!isBookmarked);
                  }}
                >
                  <Bookmark className={`w-4 h-4 ${isBookmarked ? 'fill-blue-500 text-blue-500' : 'text-gray-600'}`} />
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  className="h-8 w-8 p-0 bg-white/90 hover:bg-white"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleShare();
                  }}
                >
                  <Share2 className="w-4 h-4 text-gray-600" />
                </Button>
              </div>
              {/* Trending badge */}
              <div className="absolute top-3 left-3">
                <Badge className="bg-red-500 text-white text-xs">
                  <TrendingUp className="w-3 h-3 mr-1" />
                  Trending
                </Badge>
              </div>
            </div>
            <CardContent className="p-6 flex-1">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-xl font-semibold group-hover:text-blue-600 transition-colors duration-300" data-testid={`text-destination-name-${destination.id}`}>
                  {destination.name}
                </h3>
                <div className="flex items-center">
                  <StarRating rating={parseFloat(destination.rating || "0")} size="sm" showNumber />
                </div>
              </div>
              <div className="flex items-center mb-3">
                <MapPin className="w-4 h-4 text-muted-foreground mr-1" />
                <span className="text-sm text-muted-foreground" data-testid={`text-location-${destination.id}`}>
                  {destination.location}, {destination.country}
                </span>
                <span className="mx-2 text-muted-foreground">•</span>
                <Badge variant="secondary" className={categoryColors[destination.category as keyof typeof categoryColors]} data-testid={`badge-category-${destination.id}`}>
                  {destination.category}
                </Badge>
              </div>
              <p className="text-muted-foreground mb-4" data-testid={`text-description-${destination.id}`}>
                {destination.shortDescription || destination.description.slice(0, 150) + "..."}
              </p>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-4">
                  <span className="text-sm text-muted-foreground flex items-center" data-testid={`text-review-count-${destination.id}`}>
                    <Users className="w-4 h-4 mr-1" />
                    {(destination.reviewCount || 0).toLocaleString()} reviews
                  </span>
                  <span className="text-sm text-muted-foreground flex items-center">
                    <Eye className="w-4 h-4 mr-1" />
                    {Math.floor(Math.random() * 1000) + 100} views
                  </span>
                </div>
                <div className="flex items-center">
                  {destination.priceRange && (
                    <span className="text-lg font-semibold text-blue-600" data-testid={`text-price-${destination.id}`}>
                      {destination.priceRange}
                    </span>
                  )}
                </div>
              </div>
              {onPlanTrip && (
                <Button 
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onPlanTrip(destination.name);
                  }}
                  className="w-full bg-blue-600 hover:bg-blue-700 transition-all duration-300 hover:scale-105"
                >
                  <Calendar className="w-4 h-4 mr-2" />
                  Plan Trip
                </Button>
              )}
            </CardContent>
          </div>
        </Card>
      </Link>
    );
  }

  return (
<Link to={`/destinations/${destination.id}`} data-testid={`link-destination-${destination.id}`}>
      <Card className="overflow-hidden hover:shadow-xl transition-shadow cursor-pointer" data-testid={`card-destination-${destination.id}`}>
        <img 
          src={destination.images?.[0] || "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800&h=400"}
          alt={destination.name}
          className="w-full h-48 object-cover"
          data-testid={`img-destination-${destination.id}`}
        />
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xl font-semibold" data-testid={`text-destination-name-${destination.id}`}>
              {destination.name}
            </h3>
            <div className="flex items-center">
              <StarRating rating={parseFloat(destination.rating || "0")} size="sm" showNumber />
            </div>
          </div>
          <p className="text-muted-foreground text-sm mb-4" data-testid={`text-description-${destination.id}`}>
            {destination.shortDescription || destination.description.slice(0, 100) + "..."}
          </p>
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span data-testid={`text-review-count-${destination.id}`}>
              {(destination.reviewCount || 0).toLocaleString()} reviews
            </span>
            <span data-testid={`text-location-${destination.id}`}>
              {destination.location}, {destination.country}
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
