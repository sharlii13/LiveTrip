import { formatDistanceToNow } from "date-fns";
import { ThumbsUp, Edit, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import StarRating from "./star-rating";
import type { ReviewWithUser, Destination } from "@shared/schema";

interface ReviewCardProps {
  review: ReviewWithUser;
  destination?: Destination;
  showDestination?: boolean;
  showActions?: boolean;
  onEdit?: (reviewId: string) => void;
  onDelete?: (reviewId: string) => void;
}

export default function ReviewCard({ 
  review, 
  destination,
  showDestination = false, 
  showActions = false,
  onEdit,
  onDelete 
}: ReviewCardProps) {
  const categoryColors = {
    hotel: "bg-brand-100 text-brand-800 dark:bg-brand-900 dark:text-brand-200",
    restaurant: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
    attraction: "bg-brand-100 text-brand-800 dark:bg-brand-900 dark:text-brand-200",
    experience: "bg-brand-100 text-brand-800 dark:bg-brand-900 dark:text-brand-200",
    default: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200"
  };

  return (
    <Card className="p-6" data-testid={`card-review-${review.id}`}>
      <CardContent className="p-0">
        <div className="flex items-start space-x-4">
          {showDestination && destination?.images?.[0] && (
            <img 
              src={destination.images[0]}
              alt={destination.name}
              className="w-20 h-20 object-cover rounded-lg flex-shrink-0"
              data-testid={`img-destination-${review.id}`}
            />
          )}
          
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              {showDestination && destination ? (
                <h3 className="text-lg font-semibold" data-testid={`text-destination-name-${review.id}`}>
                  {destination.name}
                </h3>
              ) : (
                <h4 className="font-semibold" data-testid={`text-reviewer-name-${review.id}`}>
                  {review.user.name}
                </h4>
              )}
              <span className="text-sm text-muted-foreground" data-testid={`text-review-date-${review.id}`}>
                {formatDistanceToNow(new Date(review.createdAt || new Date()), { addSuffix: true })}
              </span>
            </div>
            
            <div className="flex items-center mb-3">
              <StarRating rating={review.rating} size="sm" />
              <span className="text-sm text-muted-foreground ml-2" data-testid={`text-rating-${review.id}`}>
                {review.rating}/5
              </span>
              {destination && (
                <>
                  <span className="mx-2 text-muted-foreground">•</span>
                  <Badge 
                    variant="secondary" 
                    className={categoryColors[destination.category as keyof typeof categoryColors] || categoryColors.default}
                    data-testid={`badge-category-${review.id}`}
                  >
                    {destination.category}
                  </Badge>
                </>
              )}
            </div>
            
            {review.title && (
              <h5 className="font-medium mb-2" data-testid={`text-review-title-${review.id}`}>
                {review.title}
              </h5>
            )}
            
            <p className="text-muted-foreground mb-4" data-testid={`text-review-content-${review.id}`}>
              {review.content}
            </p>
            
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <div className="flex items-center space-x-4">
                {showDestination && destination && (
                  <span data-testid={`text-destination-location-${review.id}`}>
                    {destination.location}, {destination.country}
                  </span>
                )}
                {!showDestination && (
                  <span data-testid={`text-helpful-${review.id}`}>
                    {review.helpful} helpful votes
                  </span>
                )}
                {!showDestination && (
                  <button 
                    className="flex items-center hover:text-foreground transition-colors"
                    data-testid={`button-helpful-${review.id}`}
                  >
                    <ThumbsUp className="w-3 h-3 mr-1" />
                    Helpful
                  </button>
                )}
              </div>
              
              {showActions && (
                <div className="flex items-center space-x-2">
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => onEdit?.(review.id)}
                    data-testid={`button-edit-${review.id}`}
                  >
                    <Edit className="w-3 h-3 mr-1" />
                    Edit
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => onDelete?.(review.id)}
                    data-testid={`button-delete-${review.id}`}
                  >
                    <Trash2 className="w-3 h-3 mr-1" />
                    Delete
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
