import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { MapPin, Globe, Edit, Medal } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/livetrip";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import StarRating from "@/components/star-rating";
import ReviewCard from "@/components/review-card";
import type { User, ReviewWithUser, Destination } from "@shared/schema";

export default function ProfilePage() {
  const { userId } = useParams();
  const { user: me, refresh } = useAuth();
  const queryClient = useQueryClient();
  const isOwn = !!me && me.id === userId;
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ name: "", bio: "", location: "" });

  // trips, visited places and badges: your own always, other travellers only if they made their history public
  const { data: history } = useQuery<History | null>({
    queryKey: ["/api/history", userId, isOwn],
    queryFn: () => api<History>(isOwn ? "/api/history" : `/api/users/${userId}/history`).catch(() => null),
  });
  const { data: wishlist } = useQuery<{ id: number; name: string; city: string }[]>({
    queryKey: ["/api/wishlist", isOwn],
    queryFn: () => (isOwn ? api("/api/wishlist") : Promise.resolve([])),
  });

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
                {history && (
                  <div className="flex items-center">
                    <Globe className="w-4 h-4 mr-1" />
                    <span data-testid="text-countries-visited">
                      {plural(new Set(history.trips.map((t) => t.destination.toLowerCase())).size, "destination")} ·{" "}
                      {plural(history.trips.reduce((n, t) => n + t.visited.length, 0), "place")} visited
                    </span>
                  </div>
                )}
                {averageRating > 0 && (
                  <div className="flex items-center">
                    <StarRating rating={averageRating} size="sm" showNumber />
                    <span className="ml-2">reviewer rating</span>
                  </div>
                )}
              </div>
            </div>
            {isOwn && <Button className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="button-edit-profile"
                    onClick={() => { setForm({ name: user.name || "", bio: user.bio || "", location: user.location || "" }); setEditing(true); }}>
              <Edit className="w-4 h-4 mr-2" />
              Edit Profile
            </Button>}
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
            Saved Places{isOwn ? ` (${wishlist?.length ?? 0})` : ""}
          </TabsTrigger>
          <TabsTrigger value="maps" data-testid="tab-maps">
            Trips ({history?.trips.length ?? 0})
          </TabsTrigger>
          <TabsTrigger value="badges" data-testid="tab-badges">
            Badges ({history?.badges.length ?? 0})
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
          {!isOwn ? <p className="text-center py-12 text-muted-foreground">Saved places are private.</p>
            : wishlist?.length ? (
              <div className="grid gap-2 sm:grid-cols-2">
                {wishlist.map((w) => <Card key={w.id}><CardContent className="py-3"><p className="font-medium">{w.name}</p><p className="text-sm text-muted-foreground">{w.city || "Anywhere"}</p></CardContent></Card>)}
              </div>
            ) : <p className="text-center py-12 text-muted-foreground">No saved places yet. Save them from the photo feed or <Link className="text-primary underline" to="/wishlist">your wishlist</Link>.</p>}
        </TabsContent>

        <TabsContent value="maps" className="mt-8">
          {history?.trips.length ? (
            <div className="space-y-2">
              {history.trips.map((t) => (
                <Card key={t.id}>
                  <CardContent className="py-3 flex justify-between gap-2">
                    <div>
                      <p className="font-medium capitalize">{isOwn ? <Link className="hover:underline" to={`/trips/${t.id}`}>{t.destination}</Link> : t.destination}</p>
                      <p className="text-sm text-muted-foreground">{t.start_date} → {t.end_date} · {t.visited.length} places visited · {t.photos} photos</p>
                    </div>
                    <Badge variant="secondary" className="capitalize h-fit">{t.status}</Badge>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : <p className="text-center py-12 text-muted-foreground">{history ? "No trips yet." : "This traveler's trips are private."}</p>}
        </TabsContent>

        <TabsContent value="badges" className="mt-8">
          {history?.badges.length ? (
            <div className="flex flex-wrap gap-2">{history.badges.map((b) => <Badge key={b.code} className="text-sm py-1"><Medal className="w-4 h-4 mr-1" />{b.title}</Badge>)}</div>
          ) : <p className="text-center py-12 text-muted-foreground">No badges yet. Check in at places on your trips to earn them.</p>}
        </TabsContent>
      </Tabs>

      <Dialog open={editing} onOpenChange={setEditing}>
        <DialogContent>
          <DialogHeader><DialogTitle>Edit profile</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1"><Label htmlFor="p-name">Name</Label><Input id="p-name" value={form.name} maxLength={80} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div className="space-y-1"><Label htmlFor="p-loc">Location</Label><Input id="p-loc" value={form.location} maxLength={120} onChange={(e) => setForm({ ...form, location: e.target.value })} /></div>
            <div className="space-y-1"><Label htmlFor="p-bio">Bio</Label><Textarea id="p-bio" value={form.bio} maxLength={500} onChange={(e) => setForm({ ...form, bio: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
            <Button disabled={!form.name.trim()} onClick={async () => {
              await api("/api/users/me", { method: "PATCH", json: form });
              await queryClient.invalidateQueries({ queryKey: ["/api/users", userId] });
              await refresh();
              setEditing(false);
            }}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

interface History {
  trips: { id: number; destination: string; start_date: string; end_date: string; status: string;
           visited: { name: string }[]; photos: number }[];
  badges: { code: string; title: string }[];
}
