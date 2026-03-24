import { Star } from "lucide-react";

interface StarRatingProps {
  rating: number;
  maxRating?: number;
  size?: "sm" | "md" | "lg";
  showNumber?: boolean;
  className?: string;
}

export default function StarRating({ 
  rating, 
  maxRating = 5, 
  size = "md", 
  showNumber = false,
  className = ""
}: StarRatingProps) {
  const sizeClasses = {
    sm: "w-3 h-3",
    md: "w-4 h-4", 
    lg: "w-5 h-5"
  };

  const stars = [];
  
  for (let i = 0; i < maxRating; i++) {
    const filled = i < Math.floor(rating);
    const halfFilled = i === Math.floor(rating) && rating % 1 >= 0.5;
    
    stars.push(
      <Star
        key={i}
        className={`${sizeClasses[size]} ${filled || halfFilled ? 'fill-current text-yellow-400' : 'text-gray-300'} ${className}`}
        data-testid={`star-${i + 1}`}
      />
    );
  }

  return (
    <div className="flex items-center" data-testid="star-rating">
      {stars}
      {showNumber && (
        <span className="ml-1 text-sm text-muted-foreground" data-testid="text-rating-number">
          {rating.toFixed(1)}
        </span>
      )}
    </div>
  );
}
