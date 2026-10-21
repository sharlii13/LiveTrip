"""
Pydantic models and schemas for multi-day itinerary planning.
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, validator
from datetime import time, datetime
import re


class Location(BaseModel):
    """Geographic location coordinates."""
    lat: float = Field(..., description="Latitude coordinate", ge=-90, le=90)
    lng: float = Field(..., description="Longitude coordinate", ge=-180, le=180)


class MultiDayPOI(BaseModel):
    """Point of Interest for multi-day planning."""
    id: int = Field(..., description="Unique POI identifier")
    name: str = Field(..., description="POI name")
    lat: float = Field(..., description="Latitude coordinate", ge=-90, le=90)
    lng: float = Field(..., description="Longitude coordinate", ge=-180, le=180)
    duration: float = Field(..., description="Visit duration in hours", gt=0, le=12)
    open: str = Field(..., description="Opening time in HH:MM format")
    close: str = Field(..., description="Closing time in HH:MM format")
    category: str = Field(..., description="POI category")
    score: float = Field(..., description="POI base score", ge=0, le=10)

    @validator("open", "close")
    def validate_time_format(cls, v):
        """Validate time format is HH:MM."""
        if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", v):
            raise ValueError("Time must be in HH:MM format")
        return v

    @validator("close")
    def validate_time_order(cls, v, values):
        """Ensure close time is after open time."""
        if "open" in values:
            open_hour, open_min = map(int, values["open"].split(":"))
            close_hour, close_min = map(int, v.split(":"))
            
            open_minutes = open_hour * 60 + open_min
            close_minutes = close_hour * 60 + close_min
            
            if close_minutes <= open_minutes:
                raise ValueError("Closing time must be after opening time")
        return v


class UserPreferences(BaseModel):
    """User preferences for different POI categories."""
    nature: float = Field(default=0.5, description="Preference for nature attractions", ge=0, le=1)
    history: float = Field(default=0.5, description="Preference for historical sites", ge=0, le=1)
    shopping: float = Field(default=0.5, description="Preference for shopping areas", ge=0, le=1)
    food: float = Field(default=0.5, description="Preference for food/dining", ge=0, le=1)
    culture: float = Field(default=0.5, description="Preference for cultural sites", ge=0, le=1)
    entertainment: float = Field(default=0.5, description="Preference for entertainment", ge=0, le=1)
    religious: float = Field(default=0.5, description="Preference for religious sites", ge=0, le=1)
    fort: float = Field(default=0.5, description="Preference for forts/monuments", ge=0, le=1)
    museum: float = Field(default=0.5, description="Preference for museums", ge=0, le=1)
    park: float = Field(default=0.5, description="Preference for parks", ge=0, le=1)

    def get_preference(self, category: str) -> float:
        """Get preference score for a category, with fallback."""
        # Map common category variations
        category_mapping = {
            "historical": "history",
            "historic": "history",
            "temple": "religious",
            "spiritual": "religious",
            "market": "shopping",
            "dining": "food",
            "restaurant": "food",
            "cultural": "culture"
        }
        
        mapped_category = category_mapping.get(category.lower(), category.lower())
        return getattr(self, mapped_category, 0.5)


class PlanningConstraints(BaseModel):
    """Constraints for multi-day planning."""
    max_daily_distance_km: float = Field(default=50, description="Maximum daily travel distance", gt=0)
    avoid_repetition: bool = Field(default=True, description="Avoid similar categories on same day")
    min_category_gap: int = Field(default=1, description="Minimum gap between same categories (in hours)")
    max_pois_per_day: int = Field(default=6, description="Maximum POIs per day", gt=0, le=15)
    min_pois_per_day: int = Field(default=2, description="Minimum POIs per day", gt=0)
    travel_buffer_minutes: int = Field(default=15, description="Buffer time for travel", ge=0, le=60)

    @validator("min_pois_per_day")
    def validate_poi_limits(cls, v, values):
        """Ensure min POIs is less than max POIs."""
        if "max_pois_per_day" in values and v > values["max_pois_per_day"]:
            raise ValueError("Minimum POIs per day must be less than maximum")
        return v


class MultiDayPlanRequest(BaseModel):
    """Request model for multi-day itinerary planning."""
    start_location: Location = Field(..., description="Starting location coordinates")
    days: int = Field(..., description="Number of days for the trip", ge=1, le=14)
    available_hours_per_day: float = Field(..., description="Available hours per day", gt=0, le=16)
    poi_list: List[MultiDayPOI] = Field(..., description="List of POIs to consider", min_items=1)
    user_preferences: UserPreferences = Field(default_factory=UserPreferences, description="User preferences")
    constraints: PlanningConstraints = Field(default_factory=PlanningConstraints, description="Planning constraints")
    start_time: str = Field(default="09:00", description="Daily start time in HH:MM format")
    transportation_mode: str = Field(default="driving", description="Transportation mode")

    @validator("start_time")
    def validate_start_time_format(cls, v):
        """Validate start time format."""
        if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", v):
            raise ValueError("Start time must be in HH:MM format")
        return v

    @validator("transportation_mode")
    def validate_transport_mode(cls, v):
        """Validate transportation mode."""
        allowed_modes = ["driving", "walking", "transit", "bicycling"]
        if v not in allowed_modes:
            raise ValueError(f"Transportation mode must be one of: {allowed_modes}")
        return v

    @validator("poi_list")
    def validate_poi_list_size(cls, v, values):
        """Ensure sufficient POIs for the number of days."""
        if "days" in values:
            min_required = values["days"]  # At least 1 POI per day
            if len(v) < min_required:
                raise ValueError(f"Need at least {min_required} POIs for {values['days']} days")
        return v


class ScheduledPOI(BaseModel):
    """POI with scheduled visit times."""
    poi: str = Field(..., description="POI name")
    poi_id: int = Field(..., description="POI ID")
    start: str = Field(..., description="Visit start time in HH:MM format")
    end: str = Field(..., description="Visit end time in HH:MM format")
    duration_hr: float = Field(..., description="Visit duration in hours")
    travel_time_to_next: Optional[int] = Field(default=None, description="Travel time to next POI in minutes")
    category: str = Field(..., description="POI category")
    coordinates: Location = Field(..., description="POI coordinates")


class DayItinerary(BaseModel):
    """Single day itinerary."""
    day: int = Field(..., description="Day number")
    total_distance_km: float = Field(..., description="Total distance covered in km")
    total_duration_hr: float = Field(..., description="Total duration including travel in hours")
    visit_duration_hr: float = Field(..., description="Pure visit duration in hours")
    utilization_percent: float = Field(..., description="Day utilization percentage")
    schedule: List[ScheduledPOI] = Field(..., description="Ordered list of scheduled POIs")
    categories_covered: List[str] = Field(..., description="Categories covered on this day")
    category_mix: Dict[str, int] = Field(default_factory=dict, description="Category count distribution")
    diversity_score: float = Field(default=0.0, description="Category diversity score (0.0 to 1.0)")
    solver_time_ms: Optional[int] = Field(default=None, description="OR-Tools solver time in milliseconds")


class ItinerarySummary(BaseModel):
    """Summary of the complete itinerary."""
    total_days: int = Field(..., description="Total number of days")
    total_pois_covered: int = Field(..., description="Total POIs included in itinerary")
    total_distance_km: float = Field(..., description="Total distance across all days")
    avg_daily_utilization: str = Field(..., description="Average daily utilization percentage")
    avg_daily_diversity: str = Field(default="0.0", description="Average daily diversity score")
    categories_distribution: Dict[str, int] = Field(..., description="Distribution of categories across days")
    unassigned_pois: List[str] = Field(default_factory=list, description="POIs that couldn't be assigned")
    optimization_stats: Dict[str, Any] = Field(default_factory=dict, description="Optimization statistics")


class MultiDayItinerary(BaseModel):
    """Complete multi-day itinerary response."""
    itinerary: List[DayItinerary] = Field(..., description="Day-wise itinerary")
    summary: ItinerarySummary = Field(..., description="Itinerary summary")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ScoredPOIForMultiDay(BaseModel):
    """POI with calculated scores for multi-day planning."""
    poi: MultiDayPOI
    final_score: float = Field(..., description="Final calculated score")
    preference_score: float = Field(..., description="User preference score")
    distance_penalty: float = Field(..., description="Distance penalty from start location")
    category_bonus: float = Field(default=0, description="Category diversity bonus")
    assigned_day: Optional[int] = Field(default=None, description="Assigned day (if any)")


class DayAssignmentResult(BaseModel):
    """Result of day assignment process."""
    day_assignments: Dict[int, List[ScoredPOIForMultiDay]] = Field(..., description="POIs assigned to each day")
    unassigned_pois: List[ScoredPOIForMultiDay] = Field(..., description="POIs that couldn't be assigned")
    assignment_stats: Dict[str, Any] = Field(default_factory=dict, description="Assignment statistics")


class OptimizationConfig(BaseModel):
    """Configuration for OR-Tools optimization."""
    # guided local search always runs to the limit; a day has <10 stops, so 1 s is plenty
    time_limit_ms: int = Field(default=1000, description="Solver time limit per day")
    drop_penalty: int = Field(default=500, description="Penalty for dropping POIs")
    distance_weight: float = Field(default=1.0, description="Weight for distance optimization")
    time_weight: float = Field(default=1.5, description="Weight for time optimization")


def time_str_to_minutes(time_str: str) -> int:
    """Convert time string (HH:MM) to minutes from midnight."""
    hours, minutes = map(int, time_str.split(":"))
    return hours * 60 + minutes


def minutes_to_time_str(minutes: int) -> str:
    """Convert minutes from midnight to time string (HH:MM)."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def hours_to_time_str(hours: float) -> str:
    """Convert hours to HH:MM format."""
    total_minutes = int(hours * 60)
    return minutes_to_time_str(total_minutes)