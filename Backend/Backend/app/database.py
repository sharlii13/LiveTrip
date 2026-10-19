# app/database.py
import os
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, create_engine
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from datetime import datetime, timedelta
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

# SQLite for quick hackathon setup
DATABASE_URL = "sqlite:///./hackathon_travel.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# CORE MODELS
# ==========================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Gamification fields
    total_eco_points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    carbon_footprint_saved = Column(Float, default=0.0)
    
    # Relationships
    trips = relationship("Trip", back_populates="user")
    eco_rewards = relationship("EcoReward", back_populates="user")
    eco_actions = relationship("EcoAction", back_populates="user") 
    hidden_gems = relationship("HiddenGem", back_populates="discoverer")
    user_badges = relationship("UserBadge", back_populates="user")
    emergency_contacts = relationship("EmergencyContact", back_populates="user")
    sos_alerts = relationship("SOSAlert", back_populates="user")

class Trip(Base):
    __tablename__ = "trips"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    destination = Column(String, index=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    budget = Column(Float)
    preferences = Column(Text)
    mood = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Eco fields
    eco_mode_enabled = Column(Boolean, default=False)
    transport_preference = Column(String, default="mixed")
    
    # Relationships
    user = relationship("User", back_populates="trips")
    itineraries = relationship("Itinerary", back_populates="trip")
    feedback = relationship("Feedback", back_populates="trip")
    sos_alerts = relationship("SOSAlert", back_populates="trip")

class Itinerary(Base):
    __tablename__ = "itineraries"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"))
    day = Column(Integer)
    activities = Column(Text)
    locations = Column(Text)
    weather_data = Column(Text)
    events = Column(Text)
    eco_suggestions = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trip = relationship("Trip", back_populates="itineraries")

class SavedItinerary(Base):
    __tablename__ = "saved_itineraries"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    full_itinerary_json = Column(Text)
    cached_at = Column(DateTime, default=datetime.utcnow)
    is_offline_cached = Column(Boolean, default=True)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trip = relationship("Trip")
    user = relationship("User")

class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"))
    feedback_type = Column(String)
    rating = Column(Integer)
    comments = Column(Text)
    location_name = Column(String)
    activity_name = Column(String)
    eco_rating = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trip = relationship("Trip", back_populates="feedback")

class WeatherCache(Base):
    __tablename__ = "weather_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    location = Column(String, index=True)
    weather_data = Column(Text)
    cached_at = Column(DateTime, default=datetime.utcnow)

# ==========================================
# FLIGHT TRACKING MODELS
# ==========================================

class UserFlight(Base):
    __tablename__ = "user_flights"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=True)
    
    # Flight details
    flight_number = Column(String(10))
    airline_iata = Column(String(3))
    departure_iata = Column(String(3))
    arrival_iata = Column(String(3))
    flight_date = Column(DateTime)
    
    # Tracking status
    is_tracking = Column(Boolean, default=True)
    notification_enabled = Column(Boolean, default=True)
    
    # Current status
    current_status = Column(String(20), default="scheduled")
    delay_minutes = Column(Integer, default=0)
    last_checked = Column(DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    trip = relationship("Trip")
    notifications = relationship("FlightNotification", back_populates="flight")

class FlightNotification(Base):
    __tablename__ = "flight_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    flight_id = Column(Integer, ForeignKey("user_flights.id"))
    
    notification_type = Column(String(30))
    message = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    flight = relationship("UserFlight", back_populates="notifications")

# ==========================================
# SOS EMERGENCY MODELS
# ==========================================

class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    contact_relationship = Column(String)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="emergency_contacts")

class SOSAlert(Base):
    __tablename__ = "sos_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=True)
    alert_type = Column(String, default="emergency")
    latitude = Column(Float)
    longitude = Column(Float)
    location_address = Column(String)
    message = Column(String)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="sos_alerts")
    trip = relationship("Trip", back_populates="sos_alerts")

# ==========================================
# GAMIFICATION MODELS
# ==========================================

class EcoReward(Base):
    __tablename__ = "eco_rewards"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    points = Column(Integer)
    action_type = Column(String(50))
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True) 
    transport_mode = Column(String(30), nullable=True)
    distance_km = Column(Float, nullable=True)
    co2_saved = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_verified = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="eco_rewards")

class HiddenGem(Base):
    __tablename__ = "hidden_gems"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    description = Column(Text)
    category = Column(String(50))
    lat = Column(Float)
    lng = Column(Float)
    discovery_points = Column(Integer, default=50)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    is_verified = Column(Boolean, default=False)
    photo_urls = Column(Text)
    address = Column(String(200), nullable=True)
    opening_hours = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
    
    discoverer = relationship("User", back_populates="hidden_gems")

class EcoAction(Base):
    __tablename__ = "eco_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action_type = Column(String(50))
    points_earned = Column(Integer)
    location_data = Column(String(200))
    proof_image_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="eco_actions")

class UserBadge(Base):
    __tablename__ = "user_badges"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    badge_name = Column(String(50))
    badge_level = Column(Integer, default=1)
    earned_at = Column(DateTime, default=datetime.utcnow)
    badge_description = Column(String(200), nullable=True)
    
    user = relationship("User", back_populates="user_badges")

# ✅ ADD THESE MISSING MODELS:

class LocationTracking(Base):
    __tablename__ = "location_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    lat = Column(Float)
    lng = Column(Float)
    accuracy_meters = Column(Float, nullable=True)
    speed_kmh = Column(Float, nullable=True)
    detected_transport_mode = Column(String(30), nullable=True)
    manual_transport_mode = Column(String(30), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # For eco-mode tracking
    eco_mode_active = Column(Boolean, default=False)
    trip_session_id = Column(String(50), nullable=True)

class EcoChallenge(Base):
    __tablename__ = "eco_challenges"
    
    id = Column(Integer, primary_key=True, index=True)
    challenge_name = Column(String(100))
    challenge_type = Column(String(30))  # weekly, monthly, seasonal
    target_value = Column(Float)  # Target distance, points, etc.
    target_metric = Column(String(30))  # km, points, actions
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    reward_points = Column(Integer)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserChallengeProgress(Base):
    __tablename__ = "user_challenge_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    challenge_id = Column(Integer, ForeignKey("eco_challenges.id"))
    current_progress = Column(Float, default=0.0)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)

class ItineraryAdjustment(Base):
    __tablename__ = "itinerary_adjustments"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"))
    flight_id = Column(Integer, ForeignKey("user_flights.id"), nullable=True)
    
    original_schedule = Column(Text)  # JSON of original itinerary
    adjusted_schedule = Column(Text)  # JSON of adjusted itinerary
    adjustment_reason = Column(String(100))  # flight_delay, cancellation, etc.
    delay_minutes = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    applied_at = Column(DateTime, nullable=True)
    
    # Relationships
    trip = relationship("Trip")
    flight = relationship("UserFlight")

# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)

create_tables()

print("✅ Database initialized with complete gamification, SOS system, and flight tracking!")
