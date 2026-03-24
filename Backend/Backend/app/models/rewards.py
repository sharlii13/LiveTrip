from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import enum
import json

Base = declarative_base()

# ✅ Enhanced Action Types with more eco-friendly actions
class ActionType(str, enum.Enum):
    PUBLIC_TRANSPORT = "public_transport"
    BIKE_USAGE = "bike_usage" 
    WALKING = "walking"
    ECO_HOTEL = "eco_hotel"
    LOCAL_FOOD = "local_food"
    HIDDEN_GEM_DISCOVERY = "hidden_gem_discovery"
    CONTENT_SUBMISSION = "content_submission"
    PLASTIC_FREE_SHOPPING = "plastic_free_shopping"
    WATER_REFILL = "water_refill"
    CARBON_OFFSET = "carbon_offset"
    SUSTAINABLE_TOUR = "sustainable_tour"
    WASTE_CLEANUP = "waste_cleanup"
    ENERGY_CONSERVATION = "energy_conservation"
    LOCAL_TRANSPORT = "local_transport"

class BadgeType(str, enum.Enum):
    GREEN_COMMUTER = "green_commuter"
    ECO_EXPLORER = "eco_explorer"
    SUSTAINABLE_TRAVELER = "sustainable_traveler"
    HIDDEN_GEM_HUNTER = "hidden_gem_hunter"
    CARBON_SAVER = "carbon_saver"
    LOCAL_HERO = "local_hero"
    WASTE_WARRIOR = "waste_warrior"
    ENERGY_EFFICIENT = "energy_efficient"
    PLASTIC_FREE = "plastic_free"
    COMMUNITY_CONTRIBUTOR = "community_contributor"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Enhanced gamification fields
    total_eco_points = Column(Integer, default=0)
    lifetime_eco_points = Column(Integer, default=0)  # Never decreases
    level = Column(Integer, default=1)
    experience_points = Column(Integer, default=0)  # XP separate from eco points
    carbon_footprint_saved = Column(Float, default=0.0)  # in kg CO2
    
    # User profile and preferences
    profile_image_url = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    preferred_eco_activities = Column(JSON, nullable=True)  # List of preferred actions
    sustainability_goals = Column(JSON, nullable=True)  # Personal goals
    
    # Streaks and achievements
    current_streak = Column(Integer, default=0)  # Days of consecutive eco actions
    longest_streak = Column(Integer, default=0)
    last_action_date = Column(DateTime, nullable=True)
    
    # Statistics
    total_distance_walked = Column(Float, default=0.0)  # km
    total_distance_cycled = Column(Float, default=0.0)  # km
    total_public_transport_usage = Column(Float, default=0.0)  # km
    total_gems_discovered = Column(Integer, default=0)
    total_content_submitted = Column(Integer, default=0)
    
    # Social features
    is_public_profile = Column(Boolean, default=True)
    allow_leaderboard = Column(Boolean, default=True)
    eco_mentor = Column(Boolean, default=False)  # Experienced user who can guide others
    
    # Relationships
    eco_rewards = relationship("EcoReward", back_populates="user")
    eco_actions = relationship("EcoAction", back_populates="user") 
    hidden_gems = relationship("HiddenGem", back_populates="discoverer")
    user_badges = relationship("UserBadge", back_populates="user")
    achievements = relationship("Achievement", back_populates="user")
    challenges_completed = relationship("ChallengeCompletion", back_populates="user")

class EcoReward(Base):
    __tablename__ = "eco_rewards"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Points and rewards
    points = Column(Integer)
    bonus_points = Column(Integer, default=0)  # Extra points for special conditions
    multiplier_applied = Column(Float, default=1.0)  # Event multipliers
    
    # Action details
    action_type = Column(String(50))  # Using String for SQLite compatibility
    action_category = Column(String(30), default="transport")  # transport, accommodation, food, discovery
    
    # Location data
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    location_name = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    
    # Transport specific
    transport_mode = Column(String(30), nullable=True)
    distance_km = Column(Float, nullable=True)
    co2_saved = Column(Float, default=0.0)  # kg of CO2 saved
    cost_saved = Column(Float, default=0.0)  # Money saved by eco choice
    
    # Verification and proof
    is_verified = Column(Boolean, default=True)
    verification_method = Column(String(50), default="auto")  # auto, manual, gps, photo
    proof_image_url = Column(String(500), nullable=True)
    verification_notes = Column(Text, nullable=True)
    
    # Timing and context
    timestamp = Column(DateTime, default=datetime.utcnow)
    action_duration = Column(Float, nullable=True)  # Duration of action in hours
    weather_condition = Column(String(50), nullable=True)
    
    # Gamification context
    is_challenge_completion = Column(Boolean, default=False)
    challenge_id = Column(Integer, nullable=True)
    is_streak_bonus = Column(Boolean, default=False)
    is_first_time_bonus = Column(Boolean, default=False)
    
    # Social impact
    inspired_others_count = Column(Integer, default=0)  # How many others were inspired
    social_share_count = Column(Integer, default=0)
    
    user = relationship("User", back_populates="eco_rewards")

class HiddenGem(Base):
    __tablename__ = "hidden_gems"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic information
    name = Column(String(100))
    description = Column(Text)
    detailed_description = Column(Text, nullable=True)
    category = Column(String(50))  # cafe, viewpoint, local_art, park, temple, market
    subcategory = Column(String(50), nullable=True)  # street_food, hiking_trail, etc.
    
    # Location
    lat = Column(Float)
    lng = Column(Float)
    address = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    
    # Discovery and verification
    discovery_points = Column(Integer, default=50)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    is_verified = Column(Boolean, default=False)
    verified_by_admin = Column(Boolean, default=False)
    verification_score = Column(Float, default=0.0)  # Community verification score
    
    # Media and content
    photo_urls = Column(JSON, nullable=True)  # JSON array of photo URLs
    video_urls = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)  # Array of tags
    
    # Visit information
    best_time_to_visit = Column(String(100), nullable=True)
    opening_hours = Column(String(100), nullable=True)
    entry_fee = Column(Float, default=0.0)
    estimated_duration = Column(Float, nullable=True)  # hours
    
    # Ratings and reviews
    average_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    total_visits = Column(Integer, default=0)
    total_likes = Column(Integer, default=0)
    
    # Accessibility and features
    is_family_friendly = Column(Boolean, default=True)
    is_eco_friendly = Column(Boolean, default=False)
    is_accessible = Column(Boolean, default=False)
    has_parking = Column(Boolean, default=False)
    has_wifi = Column(Boolean, default=False)
    accepts_cards = Column(Boolean, default=False)
    
    # Community features
    difficulty_level = Column(String(20), default="easy")  # easy, moderate, difficult
    crowdedness = Column(String(20), default="moderate")  # low, moderate, high
    safety_rating = Column(Float, default=5.0)  # 1-5 scale
    
    # Administrative
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
    last_visited_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    is_seasonal = Column(Boolean, default=False)
    seasonal_months = Column(JSON, nullable=True)  # Array of month numbers
    
    discoverer = relationship("User", back_populates="hidden_gems")

class EcoAction(Base):
    __tablename__ = "eco_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Action details
    action_type = Column(String(50))
    action_category = Column(String(30), default="general")
    points_earned = Column(Integer)
    
    # Context and location
    location_data = Column(String(200))  # lat,lng format
    location_name = Column(String(200), nullable=True)
    context = Column(Text, nullable=True)  # What was the situation
    
    # Proof and verification
    proof_image_url = Column(String(500), nullable=True)
    proof_video_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    
    # Impact measurement
    co2_impact = Column(Float, default=0.0)  # kg CO2 saved/reduced
    financial_impact = Column(Float, default=0.0)  # Money saved
    time_impact = Column(Float, nullable=True)  # Time spent on action
    
    # Social and sharing
    is_shared = Column(Boolean, default=False)
    share_platforms = Column(JSON, nullable=True)  # Which platforms shared to
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    
    # Administrative
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_verified = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="eco_actions")

class UserBadge(Base):
    __tablename__ = "user_badges"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Badge details
    badge_name = Column(String(50))
    badge_type = Column(String(50))  # achievement, milestone, special
    badge_level = Column(Integer, default=1)
    badge_tier = Column(String(20), default="bronze")  # bronze, silver, gold, platinum
    
    # Description and display
    badge_description = Column(String(200), nullable=True)
    badge_icon_url = Column(String(500), nullable=True)
    badge_color = Column(String(7), default="#4CAF50")  # Hex color
    
    # Requirements and progress
    requirements_met = Column(JSON, nullable=True)  # What requirements were met
    progress_data = Column(JSON, nullable=True)  # Progress towards next level
    
    # Earning details
    earned_at = Column(DateTime, default=datetime.utcnow)
    points_when_earned = Column(Integer, nullable=True)  # User's points when earned
    level_when_earned = Column(Integer, nullable=True)
    
    # Display preferences
    is_displayed = Column(Boolean, default=True)  # Show on profile
    is_favorite = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    
    user = relationship("User", back_populates="user_badges")

class Achievement(Base):
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Achievement details
    achievement_type = Column(String(50))  # distance_walked, gems_found, etc.
    achievement_name = Column(String(100))
    achievement_description = Column(Text)
    
    # Achievement data
    target_value = Column(Float)  # Target to achieve
    current_value = Column(Float, default=0.0)  # Current progress
    is_completed = Column(Boolean, default=False)
    completion_percentage = Column(Float, default=0.0)
    
    # Rewards
    points_reward = Column(Integer, default=0)
    badge_reward = Column(String(50), nullable=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)
    
    # Categories
    category = Column(String(50), default="general")
    difficulty = Column(String(20), default="medium")
    
    user = relationship("User", back_populates="achievements")

class Challenge(Base):
    __tablename__ = "challenges"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Challenge details
    title = Column(String(100))
    description = Column(Text)
    challenge_type = Column(String(50))  # daily, weekly, monthly, special
    category = Column(String(50), default="eco_action")
    
    # Requirements
    target_value = Column(Float)
    target_unit = Column(String(30))  # points, km, count, etc.
    required_actions = Column(JSON, nullable=True)  # Specific actions required
    
    # Rewards
    points_reward = Column(Integer)
    badge_reward = Column(String(50), nullable=True)
    special_reward = Column(String(200), nullable=True)
    
    # Timing
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Participation
    max_participants = Column(Integer, nullable=True)
    current_participants = Column(Integer, default=0)
    completion_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_admin = Column(Boolean, default=True)
    difficulty_level = Column(String(20), default="medium")

class ChallengeCompletion(Base):
    __tablename__ = "challenge_completions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    challenge_id = Column(Integer, ForeignKey("challenges.id"))
    
    # Completion details
    completed_at = Column(DateTime, default=datetime.utcnow)
    final_value = Column(Float)  # Final achievement value
    points_earned = Column(Integer)
    
    # Performance
    completion_time = Column(Float, nullable=True)  # Days taken to complete
    ranking = Column(Integer, nullable=True)  # Rank among participants
    
    # Social
    is_shared = Column(Boolean, default=False)
    celebration_message = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="challenges_completed")

class Leaderboard(Base):
    __tablename__ = "leaderboards"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Leaderboard categories
    category = Column(String(50))  # overall, weekly, monthly, city, challenge
    time_period = Column(String(20))  # all_time, weekly, monthly
    city = Column(String(100), nullable=True)
    
    # Rankings
    current_rank = Column(Integer)
    previous_rank = Column(Integer, nullable=True)
    points = Column(Integer)
    
    # Additional metrics
    co2_saved = Column(Float, default=0.0)
    distance_covered = Column(Float, default=0.0)
    gems_discovered = Column(Integer, default=0)
    
    # Timing
    updated_at = Column(DateTime, default=datetime.utcnow)
    period_start = Column(DateTime)
    period_end = Column(DateTime)

# ✅ Helper functions for gamification logic
def calculate_level_from_xp(experience_points: int) -> int:
    """Calculate user level based on experience points"""
    if experience_points < 100:
        return 1
    elif experience_points < 500:
        return 2
    elif experience_points < 1200:
        return 3
    elif experience_points < 2500:
        return 4
    elif experience_points < 5000:
        return 5
    else:
        return min(50, 5 + (experience_points - 5000) // 2000)

def get_next_level_xp(current_level: int) -> int:
    """Get XP required for next level"""
    level_thresholds = [0, 100, 500, 1200, 2500, 5000]
    if current_level <= 5:
        return level_thresholds[current_level]
    else:
        return 5000 + (current_level - 5) * 2000

def calculate_streak_bonus(streak_days: int) -> float:
    """Calculate streak bonus multiplier"""
    if streak_days >= 30:
        return 2.0
    elif streak_days >= 14:
        return 1.5
    elif streak_days >= 7:
        return 1.3
    elif streak_days >= 3:
        return 1.1
    else:
        return 1.0

# ✅ Export all models
__all__ = [
    'ActionType',
    'BadgeType', 
    'User',
    'EcoReward',
    'HiddenGem', 
    'EcoAction',
    'UserBadge',
    'Achievement',
    'Challenge',
    'ChallengeCompletion',
    'Leaderboard',
    'calculate_level_from_xp',
    'get_next_level_xp',
    'calculate_streak_bonus'
]
