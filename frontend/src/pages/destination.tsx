import { useParams } from "react-router-dom";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Heart, Share, Clock, Ticket, TrainFront, Users, Edit, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import StarRating from "@/components/star-rating";
import ReviewCard from "@/components/review-card";
import { apiRequest } from "@/lib/queryClient";
import { insertReviewSchema } from "@shared/schema";
import type { DestinationWithReviews } from "@shared/schema";

export default function DestinationPage() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [reviewForm, setReviewForm] = useState({
    rating: 5,
    title: "",
    content: "",
    userId: "user1" // Default user for demo
  });

  const { data: destination, isLoading } = useQuery<DestinationWithReviews>({
    queryKey: ["/api/destinations", id],
    enabled: !!id,
    queryFn: async () => {
      const response = await fetch(`/api/destinations/${id}`);
      if (!response.ok) throw new Error("Failed to fetch destination");
      return response.json();
    }
  });

  const createReviewMutation = useMutation({
    mutationFn: async (reviewData: any) => {
      return apiRequest("POST", "/api/reviews", reviewData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/destinations", id] });
      setReviewDialogOpen(false);
      setReviewForm({
        rating: 5,
        title: "",
        content: "",
        userId: "user1"
      });
    }
  });

  const handleSubmitReview = () => {
    const reviewData = {
      ...reviewForm,
      destinationId: id
    };

    try {
      insertReviewSchema.parse(reviewData);
      createReviewMutation.mutate(reviewData);
    } catch (error) {
      console.error("Invalid review data:", error);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="animate-pulse">
          <div className="h-8 bg-muted rounded w-1/3 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="md:col-span-2 md:row-span-2 h-96 bg-muted rounded-xl"></div>
            <div className="h-48 bg-muted rounded-xl"></div>
            <div className="h-48 bg-muted rounded-xl"></div>
            <div className="h-48 bg-muted rounded-xl"></div>
            <div className="h-48 bg-muted rounded-xl"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!destination) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8 text-center">
        <h1 className="text-2xl font-bold mb-4">Destination not found</h1>
        <p className="text-muted-foreground">The destination you're looking for doesn't exist.</p>
      </div>
    );
  }

  const avgRating = parseFloat(destination.rating || "0");

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Destination Header */}
      <div className="mb-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-4">
          <div>
            <h1 className="text-3xl font-bold mb-2" data-testid="text-destination-name">
              {destination.name}
            </h1>
            <div className="flex items-center space-x-4 text-muted-foreground">
              <div className="flex items-center">
                <span data-testid="text-destination-location">
                  {destination.location}, {destination.country}
                </span>
              </div>
              <div className="flex items-center">
                <StarRating rating={avgRating} size="sm" showNumber />
                <span className="ml-2" data-testid="text-review-count">
                  ({(destination.reviewCount || 0).toLocaleString()} reviews)
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-3 mt-4 md:mt-0">
            <Button variant="outline" data-testid="button-save">
              <Heart className="w-4 h-4 mr-2" />
              Save
            </Button>
            <Button variant="outline" data-testid="button-share">
              <Share className="w-4 h-4 mr-2" />
              Share
            </Button>
            <Button className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="button-book">
              Book Now
            </Button>
          </div>
        </div>
      </div>

      {/* Photo Gallery */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="md:col-span-2 md:row-span-2">
          <img 
            src={destination.images?.[0] || "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800"} 
            alt={destination.name}
            className="w-full h-full object-cover rounded-xl"
            data-testid="img-destination-main"
          />
        </div>
        {destination.images?.slice(1, 5).map((image, index) => (
          <img 
            key={index}
            src={image}
            alt={`${destination.name} ${index + 2}`}
            className="w-full h-48 object-cover rounded-xl"
            data-testid={`img-destination-gallery-${index}`}
          />
        )) || Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="w-full h-48 bg-muted rounded-xl flex items-center justify-center">
            <span className="text-muted-foreground">Image {index + 2}</span>
          </div>
        ))}
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2">
          {/* Description */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold mb-4">About This Place</h2>
            <p className="text-muted-foreground mb-4" data-testid="text-destination-description">
              {destination.description}
            </p>
          </div>

          {/* Key Information */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold mb-4">Key Information</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {destination.openingHours && (
                <div className="flex items-center p-4 bg-secondary/30 rounded-lg">
                  <Clock className="text-primary mr-3 w-5 h-5" />
                  <div>
                    <h4 className="font-medium">Opening Hours</h4>
                    <p className="text-sm text-muted-foreground" data-testid="text-opening-hours">
                      {destination.openingHours}
                    </p>
                  </div>
                </div>
              )}
              {destination.priceRange && (
                <div className="flex items-center p-4 bg-secondary/30 rounded-lg">
                  <Ticket className="text-primary mr-3 w-5 h-5" />
                  <div>
                    <h4 className="font-medium">Price Range</h4>
                    <p className="text-sm text-muted-foreground" data-testid="text-price-range">
                      {destination.priceRange}
                    </p>
                  </div>
                </div>
              )}
              {destination.address && (
                <div className="flex items-center p-4 bg-secondary/30 rounded-lg">
                  <TrainFront className="text-primary mr-3 w-5 h-5" />
                  <div>
                    <h4 className="font-medium">Address</h4>
                    <p className="text-sm text-muted-foreground" data-testid="text-address">
                      {destination.address}
                    </p>
                  </div>
                </div>
              )}
              <div className="flex items-center p-4 bg-secondary/30 rounded-lg">
                <Users className="text-primary mr-3 w-5 h-5" />
                <div>
                  <h4 className="font-medium">Reviews</h4>
                  <p className="text-sm text-muted-foreground" data-testid="text-total-reviews">
                    {(destination.reviewCount || 0).toLocaleString()} reviews
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Reviews Section */}
          <div className="mb-8">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold" data-testid="text-reviews-title">
                Reviews ({(destination.reviewCount || 0).toLocaleString()})
              </h2>
              <Dialog open={reviewDialogOpen} onOpenChange={setReviewDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="button-write-review">
                    <Edit className="w-4 h-4 mr-2" />
                    Write a Review
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl">
                  <DialogHeader>
                    <DialogTitle>Write a Review for {destination.name}</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="rating">Rating</Label>
                      <Select value={reviewForm.rating.toString()} onValueChange={(value) => setReviewForm(prev => ({ ...prev, rating: parseInt(value) }))}>
                        <SelectTrigger data-testid="select-review-rating">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="5">5 Stars - Excellent</SelectItem>
                          <SelectItem value="4">4 Stars - Very Good</SelectItem>
                          <SelectItem value="3">3 Stars - Average</SelectItem>
                          <SelectItem value="2">2 Stars - Poor</SelectItem>
                          <SelectItem value="1">1 Star - Terrible</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label htmlFor="title">Review Title (Optional)</Label>
                      <Input
                        id="title"
                        value={reviewForm.title}
                        onChange={(e) => setReviewForm(prev => ({ ...prev, title: e.target.value }))}
                        placeholder="Summarize your experience"
                        data-testid="input-review-title"
                      />
                    </div>
                    <div>
                      <Label htmlFor="content">Your Review</Label>
                      <Textarea
                        id="content"
                        value={reviewForm.content}
                        onChange={(e) => setReviewForm(prev => ({ ...prev, content: e.target.value }))}
                        placeholder="Share your experience with other travelers..."
                        rows={4}
                        data-testid="textarea-review-content"
                      />
                    </div>
                    <div className="flex justify-end space-x-2">
                      <Button variant="outline" onClick={() => setReviewDialogOpen(false)} data-testid="button-cancel-review">
                        Cancel
                      </Button>
                      <Button 
                        onClick={handleSubmitReview}
                        disabled={!reviewForm.content || createReviewMutation.isPending}
                        data-testid="button-submit-review"
                      >
                        {createReviewMutation.isPending ? "Submitting..." : "Submit Review"}
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            {/* Rating Summary */}
            <div className="bg-secondary/30 p-6 rounded-xl mb-6">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center mb-2">
                    <span className="text-4xl font-bold mr-2" data-testid="text-average-rating">
                      {avgRating.toFixed(1)}
                    </span>
                    <StarRating rating={avgRating} size="lg" />
                  </div>
                  <p className="text-muted-foreground">
                    Based on {(destination.reviewCount || 0).toLocaleString()} reviews
                  </p>
                </div>
              </div>
            </div>

            {/* Individual Reviews */}
            {destination.reviews && destination.reviews.length > 0 ? (
              <div className="space-y-6">
                {destination.reviews.map((review) => (
                  <ReviewCard key={review.id} review={review} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-muted-foreground">No reviews yet. Be the first to review!</p>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div>
          {/* Booking Card */}
          <Card className="p-6 mb-6 sticky top-24">
            <CardContent className="p-0">
              <h3 className="text-xl font-semibold mb-4">Quick Info</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Category</span>
                  <Badge variant="secondary" data-testid="badge-category">
                    {destination.category}
                  </Badge>
                </div>
                {destination.phone && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Phone</span>
                    <span className="font-medium" data-testid="text-phone">
                      {destination.phone}
                    </span>
                  </div>
                )}
                {destination.website && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Website</span>
                    <a 
                      href={destination.website} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="font-medium text-primary hover:underline"
                      data-testid="link-website"
                    >
                      Visit Website
                    </a>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Reviews</span>
                  <span className="font-medium" data-testid="text-sidebar-reviews">
                    {(destination.reviewCount || 0).toLocaleString()}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Features */}
          {destination.features && destination.features.length > 0 && (
            <Card className="p-6">
              <CardContent className="p-0">
                <h3 className="font-semibold mb-4">Features</h3>
                <div className="space-y-2">
                  {destination.features.map((feature, index) => (
                    <div key={index} className="flex items-center">
                      <span className="w-2 h-2 bg-primary rounded-full mr-3"></span>
                      <span className="text-sm" data-testid={`text-feature-${index}`}>
                        {feature}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
