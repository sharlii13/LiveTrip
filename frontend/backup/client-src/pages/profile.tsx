import { useParams } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { MapPin, Globe, Edit } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import StarRating from "@/components/star-rating";
import ReviewCard from "@/components/review-card";
import type { User, ReviewWithUser, Destination } from "@shared/schema";

export default function ProfilePage() {
  const { userId } = useParams();

  const { data: user, isLoading: userLoading } = useQuery<User>({
    queryKey: ["/api/users", userId],
    enabled: !!userId,
    queryFn: async () => {
      const response = await fetch(`/api/users/${userId}`);
      if (!response.ok) throw new Error("Failed to fetch user");
      return response.json();
    }
  });

  const { data: userReviews, isLoading: reviewsLoading } = useQuery<ReviewWithUser[]>({
    queryKey: ["/api/users", userId, "reviews"],
    enabled: !!userId,
    queryFn: async () => {
      const response = await fetch(`/api/users/${userId}/reviews`);
      if (!response.ok) throw new Error("Failed to fetch reviews");
      return response.json();
    }
  });

  // Get destinations for reviews (simplified - in real app would batch this)
  const { data: destinations } = useQuery<Destination[]>({
    queryKey: ["/api/destinations"],
    queryFn: async () => {
      const response = await fetch("/api/destinations");
      if (!response.ok) return [];
      return response.json();
    }
  });

  if (userLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Card className="p-8 mb-8 animate-pulse">
          <div className="flex items-center space-x-6">
            <div className="w-24 h-24 bg-muted rounded-full"></div>
            <div className="flex-1">
              <div className="h-6 bg-muted rounded w-1/3 mb-2"></div>
              <div className="h-4 bg-muted rounded w-2/3 mb-4"></div>
              <div className="h-4 bg-muted rounded w-1/2"></div>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 text-center">
        <h1 className="text-2xl font-bold mb-4">User not found</h1>
        <p className="text-muted-foreground">The user profile you're looking for doesn't exist.</p>
      </div>
    );
  }

  const averageRating = userReviews && userReviews.length > 0 
    ? userReviews.reduce((sum, review) => sum + review.rating, 0) / userReviews.length 
    : 0;

  const getDestinationForReview = (destinationId: string) => {
    return destinations?.find(d => d.id === destinationId);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Profile Header */}
      <Card className="p-8 mb-8">
        <CardContent className="p-0">
          <div className="flex flex-col md:flex-row items-center md:items-start space-y-4 md:space-y-0 md:space-x-6">
            <div className="w-24 h-24 bg-gray-300 rounded-full flex-shrink-0 flex items-center justify-center">
              <span className="text-2xl font-bold text-gray-600" data-testid="text-user-avatar">
                {user.name.charAt(0)}
              </span>
            </div>
            <div className="text-center md:text-left flex-1">
              <h1 className="text-2xl font-bold mb-2" data-testid="text-user-name">
                {user.name}
              </h1>
              <p className="text-muted-foreground mb-4" data-testid="text-user-bio">
                {user.bio || "Travel enthusiast"} • {userReviews?.length || 0} reviews • Member since {new Date(user.createdAt || new Date()).getFullYear()}
              </p>
              <div className="flex flex-col md:flex-row items-center space-y-2 md:space-y-0 md:space-x-6 text-sm text-muted-foreground">
                {user.location && (
                  <div className="flex items-center">
                    <MapPin className="w-4 h-4 mr-1" />
                    <span data-testid="text-user-location">{user.location}</span>
                  </div>
                )}
                <div className="flex items-center">
                  <Globe className="w-4 h-4 mr-1" />
                  <span data-testid="text-countries-visited">15 countries visited</span>
                </div>
                {averageRating > 0 && (
                  <div className="flex items-center">
                    <StarRating rating={averageRating} size="sm" showNumber />
                    <span className="ml-2">reviewer rating</span>
                  </div>
                )}
              </div>
            </div>
            <Button className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="button-edit-profile">
              <Edit className="w-4 h-4 mr-2" />
              Edit Profile
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Profile Tabs */}
      <Tabs defaultValue="reviews" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="reviews" data-testid="tab-reviews">
            My Reviews ({userReviews?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="saved" data-testid="tab-saved">
            Saved Places (23)
          </TabsTrigger>
          <TabsTrigger value="maps" data-testid="tab-maps">
            Travel Maps (3)
          </TabsTrigger>
          <TabsTrigger value="badges" data-testid="tab-badges">
            Badges (8)
          </TabsTrigger>
        </TabsList>

        <TabsContent value="reviews" className="mt-8">
          {reviewsLoading ? (
            <div className="space-y-6">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="p-6 animate-pulse">
                  <div className="flex space-x-4">
                    <div className="w-20 h-20 bg-muted rounded-lg"></div>
                    <div className="flex-1">
                      <div className="h-4 bg-muted rounded w-1/3 mb-2"></div>
                      <div className="h-3 bg-muted rounded w-1/4 mb-3"></div>
                      <div className="h-3 bg-muted rounded mb-2"></div>
                      <div className="h-3 bg-muted rounded w-2/3"></div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : userReviews && userReviews.length > 0 ? (
            <div className="space-y-6">
              {userReviews.map((review) => {
                const destination = getDestinationForReview(review.destinationId);
                return (
                  <ReviewCard 
                    key={review.id} 
                    review={review} 
                    destination={destination}
                    showDestination={true}
                    showActions={true}
                    onEdit={(id) => console.log("Edit review:", id)}
                    onDelete={(id) => console.log("Delete review:", id)}
                  />
                );
              })}
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-muted-foreground text-lg">No reviews yet</p>
              <p className="text-muted-foreground">Start exploring and share your experiences!</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="saved" className="mt-8">
          <div className="text-center py-12">
            <p className="text-muted-foreground text-lg">Saved places feature coming soon!</p>
            <p className="text-muted-foreground">Save your favorite destinations to plan future trips.</p>
          </div>
        </TabsContent>

        <TabsContent value="maps" className="mt-8">
          <div className="text-center py-12">
            <p className="text-muted-foreground text-lg">Travel maps feature coming soon!</p>
            <p className="text-muted-foreground">Create custom maps of your adventures.</p>
          </div>
        </TabsContent>

        <TabsContent value="badges" className="mt-8">
          <div className="text-center py-12">
            <p className="text-muted-foreground text-lg">Badges feature coming soon!</p>
            <p className="text-muted-foreground">Earn badges for your travel achievements.</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
