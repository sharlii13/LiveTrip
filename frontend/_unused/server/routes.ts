import type { Express } from "express";
import { createServer, type Server } from "http";
import passport from "passport";
import { storage } from "./storage";
import { insertDestinationSchema, insertReviewSchema, insertUserSchema } from "@shared/schema";
import { isAuthenticated, optionalAuth } from "./auth";
import { z } from "zod";

export async function registerRoutes(app: Express): Promise<Server> {
  // Authentication routes
  app.get("/api/auth/google", (req, res) => {
    if (!process.env.GOOGLE_CLIENT_ID || !process.env.GOOGLE_CLIENT_SECRET) {
      return res.status(503).json({ 
        message: "Google OAuth not configured. Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your .env file." 
      });
    }
    passport.authenticate("google", { scope: ["profile", "email"] })(req, res);
  });

  app.get("/api/auth/google/callback", (req, res) => {
    if (!process.env.GOOGLE_CLIENT_ID || !process.env.GOOGLE_CLIENT_SECRET) {
      return res.status(503).json({ 
        message: "Google OAuth not configured. Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your .env file." 
      });
    }
    passport.authenticate("google", { failureRedirect: "/login?error=google_auth_failed" })(req, res, (err: any) => {
      if (err) {
        return res.redirect("/login?error=google_auth_failed");
      }
      // Successful authentication, redirect to home page
      res.redirect("/");
    });
  });

  app.post("/api/auth/logout", (req, res) => {
    req.logout((err) => {
      if (err) {
        return res.status(500).json({ message: "Error during logout" });
      }
      res.json({ message: "Logged out successfully" });
    });
  });

  app.get("/api/auth/me", optionalAuth, (req, res) => {
    if (req.isAuthenticated()) {
      res.json({ user: req.user });
    } else {
      res.json({ user: null });
    }
  });

  // Trip Planning Routes
  app.post("/api/trips", isAuthenticated, async (req, res) => {
    try {
      const tripData = req.body;
      const userId = (req.user as any)?.id;

      if (!userId) {
        return res.status(401).json({ message: "User not authenticated" });
      }

      // Create trip in storage
      const trip = await storage.createTrip({
        ...tripData,
        userId,
        createdAt: new Date(),
      });

      res.status(201).json({ 
        message: "Trip created successfully", 
        trip 
      });
    } catch (error) {
      console.error("Error creating trip:", error);
      res.status(500).json({ message: "Failed to create trip" });
    }
  });

  app.get("/api/trips", isAuthenticated, async (req, res) => {
    try {
      const userId = (req.user as any)?.id;

      if (!userId) {
        return res.status(401).json({ message: "User not authenticated" });
      }

      const trips = await storage.getUserTrips(userId);
      res.json({ trips });
    } catch (error) {
      console.error("Error fetching trips:", error);
      res.status(500).json({ message: "Failed to fetch trips" });
    }
  });

  // Users
  app.get("/api/users/:id", async (req, res) => {
    try {
      const user = await storage.getUser(req.params.id);
      if (!user) {
        return res.status(404).json({ message: "User not found" });
      }
      res.json(user);
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });

  app.post("/api/users", async (req, res) => {
    try {
      const userData = insertUserSchema.parse(req.body);
      const user = await storage.createUser(userData);
      res.status(201).json(user);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid user data", errors: error.errors });
      }
      res.status(500).json({ message: "Internal server error" });
    }
  });

  // Destinations
  app.get("/api/destinations", async (req, res) => {
    try {
      const { search, category, rating, priceRange, limit, offset } = req.query;
      
      const params = {
        search: search as string,
        category: category as string,
        rating: rating ? parseFloat(rating as string) : undefined,
        priceRange: priceRange as string,
        limit: limit ? parseInt(limit as string) : undefined,
        offset: offset ? parseInt(offset as string) : undefined,
      };

      const destinations = await storage.getDestinations(params);
      res.json(destinations);
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });

  app.get("/api/destinations/:id", async (req, res) => {
    try {
      const destination = await storage.getDestination(req.params.id);
      if (!destination) {
        return res.status(404).json({ message: "Destination not found" });
      }
      res.json(destination);
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });

  app.post("/api/destinations", async (req, res) => {
    try {
      const destinationData = insertDestinationSchema.parse(req.body);
      const destination = await storage.createDestination(destinationData);
      res.status(201).json(destination);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid destination data", errors: error.errors });
      }
      res.status(500).json({ message: "Internal server error" });
    }
  });

  // Reviews
  app.get("/api/destinations/:destinationId/reviews", async (req, res) => {
    try {
      const reviews = await storage.getReviewsByDestination(req.params.destinationId);
      res.json(reviews);
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });

  app.get("/api/users/:userId/reviews", async (req, res) => {
    try {
      const reviews = await storage.getReviewsByUser(req.params.userId);
      res.json(reviews);
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });

  app.post("/api/reviews", async (req, res) => {
    try {
      const reviewData = insertReviewSchema.parse(req.body);
      const review = await storage.createReview(reviewData);
      res.status(201).json(review);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid review data", errors: error.errors });
      }
      res.status(500).json({ message: "Internal server error" });
    }
  });

  app.put("/api/reviews/:id", async (req, res) => {
    try {
      const reviewData = insertReviewSchema.partial().parse(req.body);
      const review = await storage.updateReview(req.params.id, reviewData);
      if (!review) {
        return res.status(404).json({ message: "Review not found" });
      }
      res.json(review);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid review data", errors: error.errors });
      }
      res.status(500).json({ message: "Internal server error" });
    }
  });

  app.delete("/api/reviews/:id", async (req, res) => {
    try {
      const deleted = await storage.deleteReview(req.params.id);
      if (!deleted) {
        return res.status(404).json({ message: "Review not found" });
      }
      res.status(204).send();
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });

  // Featured destinations endpoint
  app.get("/api/destinations/featured", async (req, res) => {
    try {
      const destinations = await storage.getDestinations({ limit: 6 });
      res.json(destinations);
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}
