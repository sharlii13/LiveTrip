import passport from "passport";
import { Strategy as GoogleStrategy } from "passport-google-oauth20";
import { storage } from "./storage";
import { type User } from "@shared/schema";

// Configure Passport
export function configurePassport() {
  // Serialize user for session
  passport.serializeUser((user: any, done) => {
    done(null, user.id);
  });

  // Deserialize user from session
  passport.deserializeUser(async (id: string, done) => {
    try {
      const user = await storage.getUser(id);
      done(null, user);
    } catch (error) {
      done(error, null);
    }
  });

  // Google OAuth Strategy (only if credentials are provided)
  if (process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET) {
    passport.use(new GoogleStrategy({
      clientID: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      callbackURL: "http://localhost:5000/api/auth/google/callback"
    }, async (accessToken, refreshToken, profile, done) => {
      try {
        const user = await storage.createOrUpdateGoogleUser(profile);
        return done(null, user);
      } catch (error) {
        return done(error, undefined);
      }
    }));
  } else {
    console.log("⚠️  Google OAuth credentials not configured. OAuth login will not work.");
    console.log("   Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your .env file.");
  }
}

// Authentication middleware
export function isAuthenticated(req: any, res: any, next: any) {
  if (req.isAuthenticated()) {
    return next();
  }
  res.status(401).json({ message: "Authentication required" });
}

// Optional authentication middleware (doesn't fail if not authenticated)
export function optionalAuth(req: any, res: any, next: any) {
  if (req.isAuthenticated()) {
    req.user = req.user;
  }
  next();
}
