import { type User, type InsertUser, type Destination, type InsertDestination, type Review, type InsertReview, type ReviewWithUser, type DestinationWithReviews } from "@shared/schema";
import { randomUUID } from "crypto";

export interface Trip {
  id: string;
  userId: string;
  destination: string;
  startDate: Date;
  endDate: Date;
  companyType: 'solo' | 'partner' | 'friends' | 'family';
  withPets: boolean;
  foodPreference: 'vegetarian' | 'non-vegetarian' | 'both';
  ecoMode: boolean;
  interests: string[];
  budget?: number;
  transportPreference?: string;
  createdAt: Date;
}

export interface InsertTrip {
  userId: string;
  destination: string;
  startDate: Date;
  endDate: Date;
  companyType: 'solo' | 'partner' | 'friends' | 'family';
  withPets: boolean;
  foodPreference: 'vegetarian' | 'non-vegetarian' | 'both';
  ecoMode: boolean;
  interests: string[];
  budget?: number;
  transportPreference?: string;
}

export interface IStorage {
  // Users
  getUser(id: string): Promise<User | undefined>;
  getUserByEmail(email: string): Promise<User | undefined>;
  getUserByGoogleId(googleId: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  createOrUpdateGoogleUser(profile: any): Promise<User>;
  updateUser(id: string, user: Partial<InsertUser>): Promise<User | undefined>;

  // Destinations
  getDestination(id: string): Promise<DestinationWithReviews | undefined>;
  getDestinations(params?: {
    search?: string;
    category?: string;
    rating?: number;
    priceRange?: string;
    limit?: number;
    offset?: number;
  }): Promise<Destination[]>;
  createDestination(destination: InsertDestination): Promise<Destination>;
  updateDestinationRating(id: string): Promise<void>;

  // Reviews
  getReview(id: string): Promise<ReviewWithUser | undefined>;
  getReviewsByDestination(destinationId: string): Promise<ReviewWithUser[]>;
  getReviewsByUser(userId: string): Promise<ReviewWithUser[]>;
  createReview(review: InsertReview): Promise<Review>;
  updateReview(id: string, review: Partial<InsertReview>): Promise<Review | undefined>;
  deleteReview(id: string): Promise<boolean>;

  // Trips
  createTrip(insertTrip: InsertTrip): Promise<Trip>;
  getUserTrips(userId: string): Promise<Trip[]>;
  getTrip(id: string): Promise<Trip | undefined>;
  updateTrip(id: string, updates: Partial<InsertTrip>): Promise<Trip | undefined>;
  deleteTrip(id: string): Promise<boolean>;
}

export class MemStorage implements IStorage {
  private users: Map<string, User>;
  private destinations: Map<string, Destination>;
  private reviews: Map<string, Review>;
  private trips: Map<string, Trip>;

  constructor() {
    this.users = new Map();
    this.destinations = new Map();
    this.reviews = new Map();
    this.trips = new Map();
    this.seedData();
  }

  private seedData() {
    // Create sample users
    const user1: User = {
      id: "user1",
      username: "sarahj",
      email: "sarah@example.com",
      name: "Sarah Johnson",
      bio: "Travel enthusiast exploring the world one destination at a time",
      location: "New York, USA",
      avatar: null,
      googleId: null,
      provider: "local",
      createdAt: new Date("2019-01-01"),
    };

    const user2: User = {
      id: "user2",
      username: "mikeadventures",
      email: "mike@example.com",
      name: "Mike Robinson",
      bio: "Adventure seeker and food lover",
      location: "London, UK",
      avatar: null,
      googleId: null,
      provider: "local",
      createdAt: new Date("2020-03-15"),
    };

    this.users.set(user1.id, user1);
    this.users.set(user2.id, user2);

    // Create sample destinations
    const paris: Destination = {
      id: "dest1",
      name: "Eiffel Tower",
      location: "Paris",
      country: "France",
      category: "attraction",
      description: "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. It is named after the engineer Gustave Eiffel, whose company designed and built the tower. Constructed from 1887 to 1889 as the entrance to the 1889 World's Fair, it was initially criticized by some of France's leading artists and intellectuals for its design. Standing at 324 meters (1,063 ft) tall, it was the tallest man-made structure in the world until the Chrysler Building was built in 1930.",
      shortDescription: "Iconic iron lattice tower and symbol of Paris with breathtaking city views",
      images: [
        "https://images.unsplash.com/photo-1511739001486-6bfe10ce785f?auto=format&fit=crop&w=800",
        "https://images.unsplash.com/photo-1549144511-f099e773c147?auto=format&fit=crop&w=800",
        "https://images.unsplash.com/photo-1502602898536-47ad22581b52?auto=format&fit=crop&w=800"
      ],
      rating: "4.8",
      reviewCount: 15234,
      priceRange: "$$",
      openingHours: "9:30 AM - 11:45 PM",
      website: "https://www.toureiffel.paris",
      phone: "+33 892 70 12 39",
      address: "Champ de Mars, 5 Avenue Anatole France, 75007 Paris, France",
      features: ["Elevator access", "Restaurant", "Gift shop", "Night illumination"],
      createdAt: new Date("2020-01-01"),
    };

    const tokyo: Destination = {
      id: "dest2",
      name: "Shibuya Crossing",
      location: "Tokyo",
      country: "Japan",
      category: "attraction",
      description: "Shibuya Crossing is often called the world's busiest pedestrian crossing. The large intersection gets hundreds of thousands of pedestrians each day, coming from the crowded Shibuya Station. When the traffic lights turn red, pedestrians flood the intersection from all directions.",
      shortDescription: "World's busiest pedestrian crossing in the heart of Tokyo",
      images: [
        "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=800",
        "https://images.unsplash.com/photo-1513407030348-c983a97b98d8?auto=format&fit=crop&w=800"
      ],
      rating: "4.7",
      reviewCount: 12891,
      priceRange: "$",
      openingHours: "24/7",
      website: null,
      phone: null,
      address: "Shibuya City, Tokyo, Japan",
      features: ["24/7 access", "Shopping nearby", "Photo opportunities", "Observation deck"],
      createdAt: new Date("2020-02-01"),
    };

    const santorini: Destination = {
      id: "dest3",
      name: "Oia Village",
      location: "Santorini",
      country: "Greece",
      category: "attraction",
      description: "Oia is a coastal town on the northwest tip of Santorini, a Greek Aegean island. The town has whitewashed houses carved into the rugged clifftops, and overlooks a vast caldera filled with water. In a 19th-century mansion, the Naval Maritime Museum has exhibits on local seafaring history.",
      shortDescription: "Picturesque village famous for stunning sunsets and traditional architecture",
      images: [
        "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?auto=format&fit=crop&w=800",
        "https://images.unsplash.com/photo-1613395877344-13d4a8e0d49e?auto=format&fit=crop&w=800"
      ],
      rating: "4.9",
      reviewCount: 8756,
      priceRange: "$$$",
      openingHours: "24/7",
      website: null,
      phone: null,
      address: "Oia, Santorini, Greece",
      features: ["Sunset views", "Traditional architecture", "Art galleries", "Fine dining"],
      createdAt: new Date("2020-03-01"),
    };

    const barcelona: Destination = {
      id: "dest4",
      name: "Park Güell",
      location: "Barcelona",
      country: "Spain",
      category: "attraction",
      description: "Park Güell is a public park system composed of gardens and architectural elements located on Carmel Hill, in Barcelona, Catalonia, Spain. Carmel Hill belongs to the mountain range of Collserola – the Parc del Carmel is located on the northern face.",
      shortDescription: "Gaudí's whimsical park featuring colorful mosaics and unique architecture",
      images: [
        "https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?auto=format&fit=crop&w=800"
      ],
      rating: "4.6",
      reviewCount: 8432,
      priceRange: "$$",
      openingHours: "8:00 AM - 9:30 PM",
      website: "https://www.parkguell.cat",
      phone: "+34 934 09 18 31",
      address: "08024 Barcelona, Spain",
      features: ["Guided tours", "Audio guides", "Photography allowed", "Gaudí architecture"],
      createdAt: new Date("2020-04-01"),
    };

    this.destinations.set(paris.id, paris);
    this.destinations.set(tokyo.id, tokyo);
    this.destinations.set(santorini.id, santorini);
    this.destinations.set(barcelona.id, barcelona);

    // Create sample reviews
    const reviews: Review[] = [
      {
        id: "review1",
        userId: "user1",
        destinationId: "dest1",
        rating: 5,
        title: "Absolutely breathtaking!",
        content: "The view from the top is spectacular, especially at sunset. Yes, it's touristy and crowded, but it's a must-see for a reason. Book tickets in advance to avoid long lines.",
        images: [],
        helpful: 23,
        createdAt: new Date("2024-09-20"),
      },
      {
        id: "review2",
        userId: "user2",
        destinationId: "dest1",
        rating: 4,
        title: "Iconic landmark that lives up to the hype",
        content: "The engineering is impressive up close. The restaurant on the second floor was expensive but the experience was worth it. Go at night for the light show!",
        images: [],
        helpful: 15,
        createdAt: new Date("2024-09-16"),
      },
      {
        id: "review3",
        userId: "user1",
        destinationId: "dest2",
        rating: 4,
        title: "Amazing experience!",
        content: "Tokyo exceeded all expectations. The blend of modern and traditional culture is fascinating. The energy of Shibuya Crossing is unmatched!",
        images: [],
        helpful: 18,
        createdAt: new Date("2024-09-18"),
      },
      {
        id: "review4",
        userId: "user2",
        destinationId: "dest3",
        rating: 5,
        title: "Pure magic",
        content: "Santorini is breathtaking. The sunsets from Oia are incredible and the local wine is exceptional. Perfect for a romantic getaway.",
        images: [],
        helpful: 25,
        createdAt: new Date("2024-09-15"),
      },
    ];

    reviews.forEach(review => this.reviews.set(review.id, review));
  }

  async getUser(id: string): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByEmail(email: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(user => user.email === email);
  }

  async getUserByGoogleId(googleId: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(user => user.googleId === googleId);
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = randomUUID();
    const user: User = { 
      ...insertUser, 
      id, 
      avatar: insertUser.avatar || null,
      bio: insertUser.bio || null,
      location: insertUser.location || null,
      googleId: insertUser.googleId || null,
      provider: insertUser.provider || "local",
      createdAt: new Date(),
      username: insertUser.username || null
    };
    this.users.set(id, user);
    return user;
  }

  async createOrUpdateGoogleUser(profile: any): Promise<User> {
    const existingUser = await this.getUserByGoogleId(profile.id);
    
    if (existingUser) {
      // Update existing user with latest profile info
      const updatedUser = {
        ...existingUser,
        name: profile.displayName || existingUser.name,
        avatar: profile.photos?.[0]?.value || existingUser.avatar,
        email: profile.emails?.[0]?.value || existingUser.email,
      };
      this.users.set(existingUser.id, updatedUser);
      return updatedUser;
    }

    // Check if user exists with same email
    const existingEmailUser = await this.getUserByEmail(profile.emails?.[0]?.value);
    if (existingEmailUser) {
      // Link Google account to existing user
      const updatedUser = {
        ...existingEmailUser,
        googleId: profile.id,
        provider: "google",
        avatar: profile.photos?.[0]?.value || existingEmailUser.avatar,
      };
      this.users.set(existingEmailUser.id, updatedUser);
      return updatedUser;
    }

    // Create new user
    const newUser: InsertUser = {
      username: profile.emails?.[0]?.value?.split('@')[0] || `user_${profile.id}`,
      email: profile.emails?.[0]?.value || '',
      name: profile.displayName || 'Google User',
      avatar: profile.photos?.[0]?.value || null,
      googleId: profile.id,
      provider: "google",
    };

    return this.createUser(newUser);
  }

  async updateUser(id: string, userData: Partial<InsertUser>): Promise<User | undefined> {
    const existingUser = this.users.get(id);
    if (!existingUser) return undefined;

    const updatedUser = { ...existingUser, ...userData };
    this.users.set(id, updatedUser);
    return updatedUser;
  }

  async getDestination(id: string): Promise<DestinationWithReviews | undefined> {
    const destination = this.destinations.get(id);
    if (!destination) return undefined;

    const reviews = await this.getReviewsByDestination(id);
    return { ...destination, reviews };
  }

  async getDestinations(params: {
    search?: string;
    category?: string;
    rating?: number;
    priceRange?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<Destination[]> {
    let destinations = Array.from(this.destinations.values());

    // Apply filters
    if (params.search) {
      const searchLower = params.search.toLowerCase();
      destinations = destinations.filter(d => 
        d.name.toLowerCase().includes(searchLower) ||
        d.location.toLowerCase().includes(searchLower) ||
        d.country.toLowerCase().includes(searchLower) ||
        d.description.toLowerCase().includes(searchLower)
      );
    }

    if (params.category) {
      destinations = destinations.filter(d => d.category === params.category);
    }

    if (params.rating) {
      destinations = destinations.filter(d => parseFloat(d.rating || "0") >= params.rating!);
    }

    if (params.priceRange) {
      destinations = destinations.filter(d => d.priceRange === params.priceRange);
    }

    // Sort by rating (highest first)
    destinations.sort((a, b) => parseFloat(b.rating || "0") - parseFloat(a.rating || "0"));

    // Apply pagination
    const offset = params.offset || 0;
    const limit = params.limit || 20;
    return destinations.slice(offset, offset + limit);
  }

  async createDestination(insertDestination: InsertDestination): Promise<Destination> {
    const id = randomUUID();
    const destination: Destination = { 
      ...insertDestination, 
      id,
      rating: "0",
      reviewCount: 0,
      shortDescription: insertDestination.shortDescription || null,
      images: insertDestination.images || null,
      priceRange: insertDestination.priceRange || null,
      openingHours: insertDestination.openingHours || null,
      website: insertDestination.website || null,
      phone: insertDestination.phone || null,
      address: insertDestination.address || null,
      features: insertDestination.features || null,
      createdAt: new Date()
    };
    this.destinations.set(id, destination);
    return destination;
  }

  async updateDestinationRating(id: string): Promise<void> {
    const destination = this.destinations.get(id);
    if (!destination) return;

    const reviews = Array.from(this.reviews.values()).filter(r => r.destinationId === id);
    if (reviews.length === 0) return;

    const avgRating = reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length;
    destination.rating = avgRating.toFixed(1);
    destination.reviewCount = reviews.length;
    this.destinations.set(id, destination);
  }

  async getReview(id: string): Promise<ReviewWithUser | undefined> {
    const review = this.reviews.get(id);
    if (!review) return undefined;

    const user = this.users.get(review.userId);
    if (!user) return undefined;

    return { ...review, user };
  }

  async getReviewsByDestination(destinationId: string): Promise<ReviewWithUser[]> {
    const reviews = Array.from(this.reviews.values())
      .filter(r => r.destinationId === destinationId)
      .sort((a, b) => (b.createdAt?.getTime() || 0) - (a.createdAt?.getTime() || 0));

    const reviewsWithUsers: ReviewWithUser[] = [];
    for (const review of reviews) {
      const user = this.users.get(review.userId);
      if (user) {
        reviewsWithUsers.push({ ...review, user });
      }
    }

    return reviewsWithUsers;
  }

  async getReviewsByUser(userId: string): Promise<ReviewWithUser[]> {
    const reviews = Array.from(this.reviews.values())
      .filter(r => r.userId === userId)
      .sort((a, b) => (b.createdAt?.getTime() || 0) - (a.createdAt?.getTime() || 0));

    const user = this.users.get(userId);
    if (!user) return [];

    return reviews.map(review => ({ ...review, user }));
  }

  async createReview(insertReview: InsertReview): Promise<Review> {
    const id = randomUUID();
    const review: Review = { 
      ...insertReview, 
      id,
      title: insertReview.title || null,
      images: insertReview.images || null,
      helpful: 0,
      createdAt: new Date()
    };
    this.reviews.set(id, review);
    
    // Update destination rating
    await this.updateDestinationRating(insertReview.destinationId);
    
    return review;
  }

  async updateReview(id: string, reviewData: Partial<InsertReview>): Promise<Review | undefined> {
    const existingReview = this.reviews.get(id);
    if (!existingReview) return undefined;

    const updatedReview = { ...existingReview, ...reviewData };
    this.reviews.set(id, updatedReview);
    
    // Update destination rating
    await this.updateDestinationRating(existingReview.destinationId);
    
    return updatedReview;
  }

  async deleteReview(id: string): Promise<boolean> {
    const review = this.reviews.get(id);
    if (!review) return false;

    const deleted = this.reviews.delete(id);
    if (deleted) {
      // Update destination rating
      await this.updateDestinationRating(review.destinationId);
    }
    
    return deleted;
  }

  // Trip methods
  async createTrip(insertTrip: InsertTrip): Promise<Trip> {
    const id = randomUUID();
    const trip: Trip = {
      ...insertTrip,
      id,
      createdAt: new Date()
    };
    this.trips.set(id, trip);
    return trip;
  }

  async getUserTrips(userId: string): Promise<Trip[]> {
    return Array.from(this.trips.values())
      .filter(trip => trip.userId === userId)
      .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
  }

  async getTrip(id: string): Promise<Trip | undefined> {
    return this.trips.get(id);
  }

  async updateTrip(id: string, updates: Partial<InsertTrip>): Promise<Trip | undefined> {
    const existingTrip = this.trips.get(id);
    if (!existingTrip) return undefined;

    const updatedTrip = { ...existingTrip, ...updates };
    this.trips.set(id, updatedTrip);
    return updatedTrip;
  }

  async deleteTrip(id: string): Promise<boolean> {
    return this.trips.delete(id);
  }
}

export const storage = new MemStorage();
