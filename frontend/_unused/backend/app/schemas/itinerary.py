from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, time
from enum import Enum


class ActivityType(str, Enum):
    SIGHTSEEING = "sightseeing"
    RESTAURANT = "restaurant"
    HOTEL = "hotel"
    TRANSPORT = "transport"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    OUTDOOR = "outdoor"
    INDOOR = "indoor"
    CULTURAL = "cultural"
    ADVENTURE = "adventure"


class WeatherCondition(str, Enum):
    SUNNY = "sunny"
    RAINY = "rainy"
    CLOUDY = "cloudy"
    SNOWY = "snowy"
    STORMY = "stormy"


class TrafficLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SEVERE = "severe"


class FlightStatus(str, Enum):
    ON_TIME = "on_time"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class Location(BaseModel):
    latitude: float
    longitude: float
    address: str
    city: str
    country: str


class Activity(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    location: Location
    activity_type: ActivityType
    estimated_duration: int  # in minutes
    cost: Optional[float] = None
    rating: Optional[float] = None
    weather_dependent: bool = False
    indoor_alternative: Optional[str] = None
    opening_hours: Optional[Dict[str, str]] = None
    booking_required: bool = False
    difficulty_level: Optional[str] = None
    accessibility_info: Optional[str] = None


class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    activity: Activity
    priority: int = Field(ge=1, le=10)  # 1 = lowest, 10 = highest
    flexibility: int = Field(ge=1, le=5)  # 1 = fixed, 5 = very flexible


class UserPreferences(BaseModel):
    food_preference: str  # "vegetarian", "vegan", "non_vegetarian", "any"
    budget_range: str  # "low", "medium", "high"
    travel_style: str  # "solo", "family", "friends", "business"
    mobility_requirements: Optional[str] = None
    language_preference: str = "english"
    interests: List[str] = []
    avoid_activities: List[str] = []
    eco_mode: bool = False
    preferred_transport: List[str] = ["walking", "public_transport", "taxi"]


class WeatherData(BaseModel):
    temperature: float
    condition: WeatherCondition
    humidity: int
    wind_speed: float
    precipitation_probability: int
    timestamp: datetime


class TrafficData(BaseModel):
    route: str
    current_duration: int  # in minutes
    typical_duration: int  # in minutes
    traffic_level: TrafficLevel
    alternative_routes: List[Dict[str, Any]] = []
    timestamp: datetime


class FlightData(BaseModel):
    flight_number: str
    airline: str
    departure_time: datetime
    arrival_time: datetime
    status: FlightStatus
    delay_minutes: Optional[int] = None
    gate: Optional[str] = None
    terminal: Optional[str] = None


class ItineraryDay(BaseModel):
    date: datetime
    time_slots: List[TimeSlot]
    total_budget: float = 0.0
    total_travel_time: int = 0  # in minutes
    weather_forecast: Optional[WeatherData] = None


class Itinerary(BaseModel):
    id: str
    user_id: str
    destination: str
    start_date: datetime
    end_date: datetime
    days: List[ItineraryDay]
    user_preferences: UserPreferences
    total_budget: float = 0.0
    created_at: datetime
    updated_at: datetime
    version: int = 1


class ItineraryUpdate(BaseModel):
    itinerary_id: str
    update_type: str  # "weather_change", "traffic_delay", "flight_delay", "user_preference"
    changes_made: List[Dict[str, Any]]
    reason: str
    timestamp: datetime


class CreateItineraryRequest(BaseModel):
    user_id: str
    destination: str
    start_date: datetime
    end_date: datetime
    user_preferences: UserPreferences
    must_visit_places: List[str] = []
    budget_limit: Optional[float] = None
    flight_details: Optional[FlightData] = None


class UpdatePreferencesRequest(BaseModel):
    itinerary_id: str
    preferences: Dict[str, Any]
    apply_immediately: bool = True


class EmergencyContact(BaseModel):
    name: str
    phone: str
    relationship: str
    email: Optional[str] = None


class TravelDocuments(BaseModel):
    passport_number: Optional[str] = None
    visa_details: Optional[str] = None
    travel_insurance: Optional[str] = None
    emergency_contacts: List[EmergencyContact] = []


class RealTimeAlert(BaseModel):
    id: str
    itinerary_id: str
    alert_type: str  # "weather", "traffic", "flight", "emergency", "suggestion"
    severity: str  # "low", "medium", "high", "critical"
    message: str
    suggested_actions: List[str] = []
    timestamp: datetime
    acknowledged: bool = False