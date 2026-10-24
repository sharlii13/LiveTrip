import { sql } from "drizzle-orm";
import { pgTable, text, varchar, integer, numeric, timestamp, doublePrecision } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  username: text("username").unique(),
  email: text("email").notNull().unique(),
  name: text("name").notNull(),
  bio: text("bio"),
  location: text("location"),
  avatar: text("avatar"),
  googleId: text("google_id").unique(),
  provider: text("provider").default("local"), // 'local' or 'google'
  createdAt: timestamp("created_at").defaultNow(),
});

export const destinations = pgTable("destinations", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  name: text("name").notNull(),
  location: text("location").notNull(),
  country: text("country").notNull(),
  category: text("category").notNull(), // hotel, restaurant, attraction, experience
  description: text("description").notNull(),
  shortDescription: text("short_description"),
  images: text("images").array(),
  rating: numeric("rating", { precision: 3, scale: 2 }).default("0"),
  reviewCount: integer("review_count").default(0),
  priceRange: text("price_range"), // $, $$, $$$
  openingHours: text("opening_hours"),
  website: text("website"),
  phone: text("phone"),
  address: text("address"),
  features: text("features").array(),
  lat: doublePrecision("lat"),  // the API sends coordinates for the map
  lng: doublePrecision("lng"),
  createdAt: timestamp("created_at").defaultNow(),
});

export const reviews = pgTable("reviews", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").notNull().references(() => users.id),
  destinationId: varchar("destination_id").notNull().references(() => destinations.id),
  rating: integer("rating").notNull(),
  title: text("title"),
  content: text("content").notNull(),
  images: text("images").array(),
  helpful: integer("helpful").default(0),
  createdAt: timestamp("created_at").defaultNow(),
});

export const insertUserSchema = createInsertSchema(users).omit({
  id: true,
  createdAt: true,
});

export const insertDestinationSchema = createInsertSchema(destinations).omit({
  id: true,
  rating: true,
  reviewCount: true,
  createdAt: true,
});

export const insertReviewSchema = createInsertSchema(reviews).omit({
  id: true,
  helpful: true,
  createdAt: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;
export type InsertDestination = z.infer<typeof insertDestinationSchema>;
export type Destination = typeof destinations.$inferSelect;
export type InsertReview = z.infer<typeof insertReviewSchema>;
export type Review = typeof reviews.$inferSelect;

export type ReviewWithUser = Review & {
  user: User;
};

export type DestinationWithReviews = Destination & {
  reviews: ReviewWithUser[];
};
