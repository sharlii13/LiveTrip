from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, time
import json

Base = declarative_base()

class Itinerary(Base):
    __tablename__ = "itineraries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    title = Column(String, default="My Trip")
    destination_city = Column(String, nullable=True)  # Main destination city
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    start_time = Column(String, default="09:00:00")  # Daily start time
    timezone = Column(String, default="Asia/Kolkata")
    
    # Scoring and optimization
    total_score = Column(Float, default=0.0)
    total_distance = Column(Float, default=0.0)
    estimated_cost = Column(Float, default=0.0)
    total_duration = Column(Float, default=0.0)  # Total trip duration in hours
    
    # Time scheduling features
    daily_start_time = Column(String, default="09:00:00")
    daily_end_time = Column(String, default="20:00:00")
    break_duration = Column(Float, default=1.0)  # Break between activities in hours
    lunch_break_duration = Column(Float, default=1.5)  # Lunch break duration
    
    # Algorithm settings
    algorithm_used = Column(String, default="greedy_with_time_scheduling")
    optimization_weights = Column(JSON, nullable=True)  # Store weights as JSON
    
    # Trip preferences
    mood = Column(String, default="happy")  # happy, adventurous, romantic, cultural, etc.
    budget_range = Column(String, default="medium")  # low, medium, high, luxury
    transport_preference = Column(String, default="mixed")  # walking, public, private, mixed
    eco_mode_enabled = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_optimized = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Weather and external factors
    weather_preference = Column(String, default="any")  # sunny, cloudy, rainy, any
    crowd_preference = Column(String, default="moderate")  # low, moderate, high
    
    # Relationships
    destinations = relationship("Destination", back_populates="itinerary", cascade="all, delete-orphan")
    time_schedules = relationship("TimeSchedule", back_populates="itinerary", cascade="all, delete-orphan")
    daily_plans = relationship("DailyPlan", back_populates="itinerary", cascade="all, delete-orphan")

class Destination(Base):
    __tablename__ = "destinations"
    
    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id"))
    
    # Basic destination info
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(Text)
    city = Column(String, nullable=True)
    country = Column(String, default="India")
    
    # Visit details
    rating = Column(Float, default=4.0)
    visit_order = Column(Integer, default=0)
    stay_duration = Column(Float, default=2.0)  # hours
    category = Column(String, default="tourist_attraction")
    subcategory = Column(String, nullable=True)  # museum, temple, beach, etc.
    
    # Cost and timing
    estimated_cost = Column(Float, default=0.0)
    entry_fee = Column(Float, default=0.0)
    best_time_to_visit = Column(String, nullable=True)  # morning, afternoon, evening
    
    # Algorithm factors
    distance_from_previous = Column(Float, default=0.0)
    travel_time_to_next = Column(Float, default=0.0)  # Travel time in hours
    traffic_score = Column(Float, default=5.0)  # 1-10 scale (1=heavy traffic, 10=no traffic)
    weather_match = Column(Float, default=8.0)  # 1-10 scale
    crowd_level = Column(Float, default=5.0)  # 1-10 scale (1=very crowded, 10=empty)
    calculated_score = Column(Float, default=0.0)
    
    # Time scheduling
    scheduled_arrival_time = Column(String, nullable=True)  # "HH:MM:SS"
    scheduled_departure_time = Column(String, nullable=True)  # "HH:MM:SS"
    day_number = Column(Integer, default=1)  # Which day of the trip
    
    # Additional details
    description = Column(Text, nullable=True)
    tips = Column(Text, nullable=True)
    opening_hours = Column(String, nullable=True)  # "09:00-18:00"
    closing_days = Column(String, nullable=True)  # "Monday,Tuesday"
    
    # Accessibility and preferences
    accessibility_friendly = Column(Boolean, default=True)
    family_friendly = Column(Boolean, default=True)
    eco_friendly = Column(Boolean, default=False)
    
    # External references
    google_place_id = Column(String, nullable=True)
    trip_advisor_id = Column(String, nullable=True)
    
    # Relationships
    itinerary = relationship("Itinerary", back_populates="destinations")

class TimeSchedule(Base):
    __tablename__ = "time_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id"))
    destination_id = Column(Integer, ForeignKey("destinations.id"))
    
    # Time details
    day_number = Column(Integer, nullable=False)
    arrival_time = Column(String, nullable=False)  # "HH:MM:SS"
    departure_time = Column(String, nullable=False)  # "HH:MM:SS"
    visit_duration = Column(Float, nullable=False)  # hours
    
    # Travel details
    travel_time_from_previous = Column(Float, default=0.0)  # hours
    travel_mode = Column(String, default="walking")  # walking, driving, public_transport
    travel_distance = Column(Float, default=0.0)  # km
    
    # Breaks and buffers
    break_before = Column(Float, default=0.0)  # Break time before this activity
    break_after = Column(Float, default=0.0)  # Break time after this activity
    buffer_time = Column(Float, default=0.25)  # Extra buffer time (15 min default)
    
    # Status
    is_flexible = Column(Boolean, default=True)  # Can this timing be adjusted?
    priority = Column(Integer, default=5)  # 1-10 priority for scheduling
    
    # Relationships
    itinerary = relationship("Itinerary", back_populates="time_schedules")

class DailyPlan(Base):
    __tablename__ = "daily_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id"))
    
    # Day details
    day_number = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)
    day_title = Column(String, default="Day")  # "Day 1", "Mumbai Exploration", etc.
    
    # Timing
    start_time = Column(String, default="09:00:00")
    end_time = Column(String, default="20:00:00")
    total_duration = Column(Float, default=0.0)  # Total active hours
    
    # Activities summary
    total_destinations = Column(Integer, default=0)
    total_travel_time = Column(Float, default=0.0)
    total_activity_time = Column(Float, default=0.0)
    total_break_time = Column(Float, default=0.0)
    
    # Cost and distance
    estimated_daily_cost = Column(Float, default=0.0)
    total_daily_distance = Column(Float, default=0.0)
    
    # Schedule flexibility
    has_buffer_time = Column(Boolean, default=True)
    is_packed_schedule = Column(Boolean, default=False)
    flexibility_score = Column(Float, default=7.0)  # 1-10 scale
    
    # Weather and conditions
    weather_dependent_activities = Column(Integer, default=0)
    indoor_activities = Column(Integer, default=0)
    outdoor_activities = Column(Integer, default=0)
    
    # Recommendations
    suggested_meal_times = Column(JSON, nullable=True)  # Store as JSON array
    suggested_rest_times = Column(JSON, nullable=True)
    alternative_activities = Column(JSON, nullable=True)
    
    # Relationships
    itinerary = relationship("Itinerary", back_populates="daily_plans")

class OptimizationWeights(Base):
    __tablename__ = "optimization_weights"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id"), nullable=True)
    
    # Core algorithm weights
    w1_rating = Column(Float, default=0.4)      # Weight for rating/popularity
    w2_distance = Column(Float, default=0.3)    # Weight for distance optimization
    w3_traffic = Column(Float, default=0.2)     # Weight for traffic conditions
    w4_weather = Column(Float, default=0.1)     # Weight for weather matching
    
    # Additional optimization factors
    w5_cost = Column(Float, default=0.0)        # Weight for cost optimization
    w6_time = Column(Float, default=0.0)        # Weight for time constraints
    w7_crowd = Column(Float, default=0.0)       # Weight for crowd avoidance
    w8_eco = Column(Float, default=0.0)         # Weight for eco-friendliness
    
    # User preferences
    preference_profile = Column(String, default="balanced")  # balanced, time_optimized, cost_optimized, etc.
    is_default = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, default=datetime.utcnow)
    usage_count = Column(Integer, default=0)

class ItineraryFeedback(Base):
    __tablename__ = "itinerary_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id"))
    user_id = Column(Integer, index=True)
    
    # Overall feedback
    overall_rating = Column(Float, nullable=False)  # 1-5 scale
    time_schedule_rating = Column(Float, nullable=True)  # 1-5 scale
    route_optimization_rating = Column(Float, nullable=True)
    cost_accuracy_rating = Column(Float, nullable=True)
    
    # Specific feedback
    was_schedule_followed = Column(Boolean, default=True)
    was_timing_accurate = Column(Boolean, default=True)
    was_cost_accurate = Column(Boolean, default=True)
    
    # Comments
    feedback_comments = Column(Text, nullable=True)
    suggested_improvements = Column(Text, nullable=True)
    
    # Usage data
    actual_start_time = Column(String, nullable=True)
    actual_end_time = Column(String, nullable=True)
    destinations_visited = Column(Integer, default=0)
    destinations_skipped = Column(Integer, default=0)
    
    # Algorithm learning
    preferred_pace = Column(String, nullable=True)  # slow, moderate, fast
    preferred_break_duration = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class AlternativeRoute(Base):
    __tablename__ = "alternative_routes"
    
    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id"))
    
    # Alternative details
    route_name = Column(String, default="Alternative Route")
    route_description = Column(Text, nullable=True)
    total_score = Column(Float, default=0.0)
    total_distance = Column(Float, default=0.0)
    total_duration = Column(Float, default=0.0)
    estimated_cost = Column(Float, default=0.0)
    
    # Route characteristics
    optimization_focus = Column(String, default="balanced")  # time, cost, distance, rating
    difficulty_level = Column(String, default="moderate")  # easy, moderate, challenging
    
    # Route data (stored as JSON)
    route_data = Column(JSON, nullable=True)  # Complete route with destinations and timing
    
    # Comparison metrics
    time_difference = Column(Float, default=0.0)  # vs main route
    cost_difference = Column(Float, default=0.0)
    distance_difference = Column(Float, default=0.0)
    
    # Status
    is_recommended = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.0)  # Algorithm confidence in this route
    
    created_at = Column(DateTime, default=datetime.utcnow)

# Helper function to serialize models to dict
def model_to_dict(instance):
    """Convert SQLAlchemy model instance to dictionary"""
    result = {}
    for column in instance.__table__.columns:
        value = getattr(instance, column.name)
        if isinstance(value, datetime):
            result[column.name] = value.isoformat()
        elif isinstance(value, (list, dict)):
            result[column.name] = value
        else:
            result[column.name] = value
    return result

# Helper function to get model relationships
def get_itinerary_with_details(db, itinerary_id: int):
    """Get complete itinerary with all related data"""
    from sqlalchemy.orm import Session
    
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    if not itinerary:
        return None
    
    # Convert to dict and add relationships
    result = model_to_dict(itinerary)
    result['destinations'] = [model_to_dict(dest) for dest in itinerary.destinations]
    result['time_schedules'] = [model_to_dict(schedule) for schedule in itinerary.time_schedules]
    result['daily_plans'] = [model_to_dict(plan) for plan in itinerary.daily_plans]
    
    return result
