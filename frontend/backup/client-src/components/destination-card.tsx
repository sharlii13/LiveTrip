import { Link } from "wouter";
import { MapPin, Calendar } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import StarRating from "./star-rating";
import type { Destination } from "@shared/schema";

interface DestinationCardProps {
  destination: Destination;
  variant?: "default" | "search";
  onPlanTrip?: (destination: string) => void;
}

export default function DestinationCard({ destination, variant = "default", onPlanTrip }: DestinationCardProps) {
  const categoryColors = {
    hotel: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    restaurant: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200", 
    attraction: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    experience: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200"
  };

  if (variant === "search") {
    return (
      <Link href={`/destinations/${destination.id}`} data-testid={`link-destination-${destination.id}`}>
        <Card className="overflow-hidden hover:shadow-xl transition-shadow cursor-pointer" data-testid={`card-destination-${destination.id}`}>
          <div className="md:flex">
            <img 
              src={destination.images?.[0] || "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=600&h=300"}
              alt={destination.name}
              className="w-full md:w-1/3 h-48 md:h-auto object-cover"
              data-testid={`img-destination-${destination.id}`}
            />
            <CardContent className="p-6 flex-1">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-xl font-semibold" data-testid={`text-destination-name-${destination.id}`}>
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
                <span className="text-sm text-muted-foreground" data-testid={`text-review-count-${destination.id}`}>
                  {(destination.reviewCount || 0).toLocaleString()} reviews
                </span>
                <div className="flex items-center">
                  {destination.priceRange && (
                    <span className="text-lg font-semibold text-primary" data-testid={`text-price-${destination.id}`}>
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
                  className="w-full bg-green-600 hover:bg-green-700"
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
    <Link href={`/destinations/${destination.id}`} data-testid={`link-destination-${destination.id}`}>
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
