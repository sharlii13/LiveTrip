"""
Pydantic models and schemas for the travel itinerary planning API.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime, time
import re


class HotelLocation(BaseModel):
    """Hotel/starting location coordinates."""
    lat: float = Field(..., description="Latitude coordinate", ge=-90, le=90)
    lng: float = Field(..., description="Longitude coordinate", ge=-180, le=180)


class PlanRequest(BaseModel):
    """Request model for one-day itinerary planning."""
    city: str = Field(..., description="City name for planning")
    start_time: str = Field(..., description="Start time in HH:MM format")
    end_time: str = Field(..., description="End time in HH:MM format")
    mode: str = Field(default="driving", description="Transportation mode")
    pace: str = Field(default="normal", description="Travel pace preference")
    hotel: HotelLocation = Field(..., description="Starting location coordinates")
    date: Optional[str] = Field(default=None, description="Travel date (YYYY-MM-DD)")

    @validator("start_time", "end_time")
    def validate_time_format(cls, v):
        """Validate time format is HH:MM."""
        if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", v):
            raise ValueError("Time must be in HH:MM format")
        return v

    @validator("mode")
    def validate_mode(cls, v):
        """Validate transportation mode."""
        allowed_modes = ["driving", "walking", "transit", "bicycling"]
        if v not in allowed_modes:
            raise ValueError(f"Mode must be one of: {allowed_modes}")
        return v

    @validator("pace")
    def validate_pace(cls, v):
        """Validate travel pace."""
        allowed_paces = ["relaxed", "normal", "fast"]
        if v not in allowed_paces:
            raise ValueError(f"Pace must be one of: {allowed_paces}")
        return v

    @validator("end_time")
    def validate_time_order(cls, v, values):
        """Ensure end_time is after start_time."""
        if "start_time" in values:
            start_hour, start_min = map(int, values["start_time"].split(":"))
            end_hour, end_min = map(int, v.split(":"))
            
            start_minutes = start_hour * 60 + start_min
            end_minutes = end_hour * 60 + end_min
            
            if end_minutes <= start_minutes:
                raise ValueError("End time must be after start time")
        return v


class RawPOI(BaseModel):
    """Raw POI data from Places API or mock data."""
    name: str
    category: str
    lat: float
    lng: float
    rating: float = Field(default=4.0, ge=0, le=5)
    reviews: int = Field(default=100, ge=0)
    open_time: str = Field(default="09:00", description="Opening time in HH:MM")
    close_time: str = Field(default="18:00", description="Closing time in HH:MM")
    duration_min: Optional[int] = Field(default=None, description="Visit duration in minutes")


class POI(BaseModel):
    """Point of Interest in the itinerary."""
    name: str = Field(..., description="POI name")
    category: str = Field(..., description="POI category")
    arrive_at: str = Field(..., description="Arrival time in HH:MM format")
    depart_at: str = Field(..., description="Departure time in HH:MM format")
    duration_min: int = Field(..., description="Visit duration in minutes", gt=0)
    lat: Optional[float] = Field(default=None, description="Latitude")
    lng: Optional[float] = Field(default=None, description="Longitude")


class ItineraryStats(BaseModel):
    """Statistics about the planned itinerary."""
    total_travel_min: int = Field(..., description="Total travel time in minutes")
    total_duration: int = Field(..., description="Total itinerary duration in minutes")
    total_pois: int = Field(..., description="Total number of POIs visited")
    solver_time_ms: Optional[int] = Field(default=None, description="OR-Tools solver time")
    dropped_pois: Optional[int] = Field(default=0, description="Number of dropped POIs")


class DayPlan(BaseModel):
    """Complete one-day itinerary plan."""
    date: str = Field(..., description="Travel date")
    items: List[POI] = Field(..., description="Ordered list of POIs to visit")
    stats: ItineraryStats = Field(..., description="Itinerary statistics")
    
    @validator("date")
    def validate_date_format(cls, v):
        """Validate date format is YYYY-MM-DD."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class ScoredPOI(BaseModel):
    """POI with calculated score for selection."""
    poi: RawPOI
    score: float
    travel_time_min: int = Field(default=0, description="Travel time from hotel/previous POI")
    feasible: bool = Field(default=True, description="Whether POI can fit in schedule")


class DistanceMatrix(BaseModel):
    """Distance matrix between locations."""
    origins: List[Dict[str, float]]  # List of {lat, lng} dicts
    destinations: List[Dict[str, float]]  # List of {lat, lng} dicts
    durations: List[List[int]]  # Duration matrix in minutes
    distances: List[List[int]]  # Distance matrix in meters


class OptimizationConfig(BaseModel):
    """Configuration for OR-Tools optimization."""
    time_limit_ms: int = Field(default=1000, description="Solver time limit")
    drop_penalty: int = Field(default=300, description="Penalty for dropping POIs")
    start_time_min: int = Field(..., description="Start time in minutes from midnight")
    end_time_min: int = Field(..., description="End time in minutes from midnight")


class ScoringWeights(BaseModel):
    """Weights for POI scoring algorithm."""
    rating: float = Field(default=0.6, description="Weight for rating score")
    reviews: float = Field(default=0.25, description="Weight for reviews score")
    weather: float = Field(default=0.25, description="Weight for weather compatibility")
    travel_penalty: float = Field(default=0.15, description="Weight for travel penalty")
    category_repetition: float = Field(default=0.10, description="Weight for category repetition penalty")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
    code: Optional[str] = Field(default=None, description="Error code")


# Category duration mappings (in minutes)
CATEGORY_DURATIONS = {
    "museum": 120,
    "temple": 45,
    "park": 90,
    "shopping": 60,
    "food": 60,
    "historic": 90,
    "entertainment": 150,
    "market": 75,
    "scenic": 60,
    "cultural": 105,
    "default": 60
}


def get_category_duration(category: str) -> int:
    """Get default visit duration for a POI category."""
    return CATEGORY_DURATIONS.get(category.lower(), CATEGORY_DURATIONS["default"])


def time_str_to_minutes(time_str: str) -> int:
    """Convert time string (HH:MM) to minutes from midnight."""
    hours, minutes = map(int, time_str.split(":"))
    return hours * 60 + minutes


def minutes_to_time_str(minutes: int) -> str:
    """Convert minutes from midnight to time string (HH:MM)."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"