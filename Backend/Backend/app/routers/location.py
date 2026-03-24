from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import logging
import math
import sys
import os

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

logger = logging.getLogger(__name__)

# ✅ FIXED IMPORTS - Handle both relative and absolute
try:
    from database import get_db
    DATABASE_AVAILABLE = True
except ImportError:
    try:
        from ..database import get_db
        DATABASE_AVAILABLE = True
    except ImportError:
        def get_db():
            return None
        DATABASE_AVAILABLE = False

# ✅ Create router
router = APIRouter(prefix="/location", tags=["📍 Location & Eco Tracking"])

# ✅ Action Types (define locally to avoid import issues)
class ActionType(str, Enum):
    WALKING = "walking"
    BIKE_USAGE = "bike_usage"
    PUBLIC_TRANSPORT = "public_transport"
    ECO_HOTEL = "eco_hotel"
    LOCAL_FOOD = "local_food"
    HIDDEN_GEM_DISCOVERY = "hidden_gem_discovery"

# ✅ Pydantic Models
class LocationUpdate(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    transport_mode: Optional[str] = Field(None, description="Transport mode: walking, cycling, public_transport, driving")
    timestamp: Optional[str] = Field(None, description="Timestamp (ISO format)")
    accuracy: Optional[float] = Field(None, ge=0, description="GPS accuracy in meters")
    speed: Optional[float] = Field(None, ge=0, description="Speed in km/h")

class GeofenceEvent(BaseModel):
    user_id: int = Field(..., gt=0)
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    event_type: str = Field(..., regex="^(enter|exit)$")
    poi_id: Optional[int] = Field(None, description="Point of Interest ID")
    poi_name: Optional[str] = Field(None, description="POI name")

class EcoTrackingSession(BaseModel):
    transport_mode: str = Field(..., regex="^(walking|cycling|public_transport)$")
    start_location: Optional[Dict[str, float]] = None
    target_destination: Optional[Dict[str, float]] = None

# ✅ Mock Data Storage
USER_LOCATIONS = {}  # Store user locations
USER_ECO_SESSIONS = {}  # Store eco tracking sessions
DISCOVERED_GEMS = {}  # Track discovered gems per user
USER_POINTS = {}  # Store user eco points

# ✅ Mock Hidden Gems (Points of Interest)
MOCK_HIDDEN_GEMS = [
    {
        "id": 1,
        "name": "Secret Rooftop Garden",
        "lat": 19.0760,
        "lng": 72.8777,
        "category": "park",
        "discovery_points": 50,
        "eco_friendly": True
    },
    {
        "id": 2,
        "name": "Local Organic Cafe",
        "lat": 19.0650,
        "lng": 72.8680,
        "category": "local_food",
        "discovery_points": 30,
        "eco_friendly": True
    },
    {
        "id": 3,
        "name": "Heritage Walking Trail",
        "lat": 18.9220,
        "lng": 72.8347,
        "category": "heritage_site",
        "discovery_points": 40,
        "eco_friendly": False
    }
]

# ✅ Helper Functions
def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two coordinates in meters"""
    R = 6371000  # Earth's radius in meters
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lng/2) * math.sin(delta_lng/2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

async def get_current_user_id() -> int:
    """Mock function to get current user - replace with your auth"""
    return 1

def get_eco_points_for_action(action_type: ActionType, distance_km: float = 0) -> int:
    """Calculate eco points based on action type and distance"""
    base_points = {
        ActionType.WALKING: 15,
        ActionType.BIKE_USAGE: 25,
        ActionType.PUBLIC_TRANSPORT: 20,
        ActionType.ECO_HOTEL: 40,
        ActionType.LOCAL_FOOD: 30,
        ActionType.HIDDEN_GEM_DISCOVERY: 50
    }
    
    points = base_points.get(action_type, 10)
    
    # Add distance bonus for walking/cycling
    if action_type in [ActionType.WALKING, ActionType.BIKE_USAGE] and distance_km > 0:
        distance_bonus = min(int(distance_km * 5), 50)  # Max 50 bonus points
        points += distance_bonus
    
    return points

def check_nearby_gems(lat: float, lng: float, radius_meters: float = 100) -> List[Dict]:
    """Check for hidden gems within radius"""
    nearby_gems = []
    
    for gem in MOCK_HIDDEN_GEMS:
        distance = calculate_distance(lat, lng, gem["lat"], gem["lng"])
        if distance <= radius_meters:
            gem_copy = gem.copy()
            gem_copy["distance"] = round(distance, 1)
            nearby_gems.append(gem_copy)
    
    # Sort by distance
    nearby_gems.sort(key=lambda x: x["distance"])
    return nearby_gems

# ✅ Service Classes
class GamificationService:
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    async def award_eco_points(self, action_type: ActionType, location: tuple, distance_km: float = 0) -> int:
        """Award eco points for sustainable actions"""
        
        points = get_eco_points_for_action(action_type, distance_km)
        
        # Update user points in mock storage
        if self.user_id not in USER_POINTS:
            USER_POINTS[self.user_id] = 0
        
        USER_POINTS[self.user_id] += points
        
        # Log the action
        logger.info(f"User {self.user_id} earned {points} points for {action_type.value}")
        
        return points
    
    async def check_gem_discovery(self, lat: float, lng: float) -> Optional[Dict]:
        """Check if user discovered a new hidden gem"""
        
        nearby_gems = check_nearby_gems(lat, lng, 50)  # 50m radius
        
        if self.user_id not in DISCOVERED_GEMS:
            DISCOVERED_GEMS[self.user_id] = set()
        
        for gem in nearby_gems:
            if gem["id"] not in DISCOVERED_GEMS[self.user_id]:
                # New discovery!
                DISCOVERED_GEMS[self.user_id].add(gem["id"])
                
                # Award discovery points
                discovery_points = await self.award_eco_points(
                    ActionType.HIDDEN_GEM_DISCOVERY, 
                    (lat, lng)
                )
                
                return {
                    "gem_id": gem["id"],
                    "gem_name": gem["name"],
                    "category": gem["category"],
                    "discovery_points": discovery_points,
                    "location": {"lat": lat, "lng": lng},
                    "distance": gem["distance"]
                }
        
        return None

class LocationService:
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    async def store_location(self, location_data: LocationUpdate):
        """Store user location update"""
        
        if self.user_id not in USER_LOCATIONS:
            USER_LOCATIONS[self.user_id] = []
        
        location_record = {
            "lat": location_data.lat,
            "lng": location_data.lng,
            "transport_mode": location_data.transport_mode,
            "timestamp": location_data.timestamp or datetime.now().isoformat(),
            "accuracy": location_data.accuracy,
            "speed": location_data.speed,
            "eco_mode": location_data.transport_mode in ["walking", "cycling", "public_transport"]
        }
        
        USER_LOCATIONS[self.user_id].append(location_record)
        
        # Keep only last 100 locations per user
        if len(USER_LOCATIONS[self.user_id]) > 100:
            USER_LOCATIONS[self.user_id] = USER_LOCATIONS[self.user_id][-100:]
        
        return location_record

# ✅ Background Tasks
async def process_gem_discovery(discovery_data: Dict):
    """Process hidden gem discovery in background"""
    logger.info(f"🎉 New gem discovered: {discovery_data['gem_name']} - {discovery_data['discovery_points']} points!")

async def calculate_route_carbon_savings(user_id: int, transport_mode: str, distance_km: float):
    """Calculate carbon savings for eco-friendly transport"""
    
    # Carbon emission factors (kg CO2 per km)
    emission_factors = {
        "driving": 0.2,
        "walking": 0.0,
        "cycling": 0.0,
        "public_transport": 0.05
    }
    
    car_emissions = distance_km * emission_factors["driving"]
    eco_emissions = distance_km * emission_factors.get(transport_mode, 0.1)
    
    carbon_saved = max(0, car_emissions - eco_emissions)
    
    logger.info(f"User {user_id} saved {carbon_saved:.2f} kg CO2 by using {transport_mode}")
    return carbon_saved

# ✅ API Endpoints
@router.post("/update",
             summary="Update User Location",
             description="Update user location and track eco-friendly transport modes")
async def update_location(
    location: LocationUpdate,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id)
):
    """Update user location and award eco points for sustainable transport"""
    
    try:
        # Store location
        location_service = LocationService(user_id)
        location_record = await location_service.store_location(location)
        
        # Initialize gamification service
        gamification_service = GamificationService(user_id)
        
        points_awarded = 0
        carbon_saved = 0
        discovery = None
        
        # Check for eco-friendly transport and award points
        if location.transport_mode in ["walking", "cycling", "public_transport"]:
            transport_mapping = {
                "walking": ActionType.WALKING,
                "cycling": ActionType.BIKE_USAGE,
                "public_transport": ActionType.PUBLIC_TRANSPORT
            }
            
            action_type = transport_mapping.get(location.transport_mode)
            
            if action_type:
                # Calculate distance from previous location if available
                distance_km = 0
                if user_id in USER_LOCATIONS and len(USER_LOCATIONS[user_id]) > 1:
                    prev_location = USER_LOCATIONS[user_id][-2]
                    distance_m = calculate_distance(
                        prev_location["lat"], prev_location["lng"],
                        location.lat, location.lng
                    )
                    distance_km = distance_m / 1000
                
                # Award points
                points_awarded = await gamification_service.award_eco_points(
                    action_type, (location.lat, location.lng), distance_km
                )
                
                # Calculate carbon savings in background
                if distance_km > 0.1:  # Only for meaningful distances
                    background_tasks.add_task(
                        calculate_route_carbon_savings, 
                        user_id, location.transport_mode, distance_km
                    )
                    carbon_saved = distance_km * 0.15  # Rough estimate
        
        # Check for hidden gem discovery
        discovery = await gamification_service.check_gem_discovery(location.lat, location.lng)
        
        if discovery:
            background_tasks.add_task(process_gem_discovery, discovery)
            points_awarded += discovery["discovery_points"]
        
        return {
            "success": True,
            "status": "location_updated",
            "eco_points_awarded": points_awarded,
            "transport_mode": location.transport_mode,
            "carbon_saved_kg": round(carbon_saved, 3) if carbon_saved > 0 else 0,
            "discovery": discovery,
            "total_user_points": USER_POINTS.get(user_id, 0),
            "location_stored": True
        }
        
    except Exception as e:
        logger.error(f"Error updating location: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating location: {str(e)}")

@router.post("/geofence-event",
             summary="Handle Geofence Event", 
             description="Process geofence entry/exit events for POIs")
async def handle_geofence_event(event: GeofenceEvent):
    """Handle geofence entry/exit events for points of interest"""
    
    try:
        gamification_service = GamificationService(event.user_id)
        points_awarded = 0
        
        if event.event_type == "enter":
            # Check what type of POI this is
            nearby_gems = check_nearby_gems(event.lat, event.lng, 100)
            
            if nearby_gems:
                gem = nearby_gems[0]  # Closest gem
                
                # Award points based on POI type
                if gem["category"] == "local_food":
                    points_awarded = await gamification_service.award_eco_points(
                        ActionType.LOCAL_FOOD, (event.lat, event.lng)
                    )
                elif gem["category"] == "eco_hotel":
                    points_awarded = await gamification_service.award_eco_points(
                        ActionType.ECO_HOTEL, (event.lat, event.lng)
                    )
                
                return {
                    "success": True,
                    "event_type": event.event_type,
                    "poi_name": gem["name"],
                    "poi_category": gem["category"],
                    "points_awarded": points_awarded,
                    "message": f"Entered {gem['name']} - sustainable choice!"
                }
        
        return {
            "success": True,
            "event_type": event.event_type,
            "points_awarded": points_awarded,
            "message": "Geofence event processed"
        }
        
    except Exception as e:
        logger.error(f"Error handling geofence event: {e}")
        raise HTTPException(status_code=500, detail=f"Error handling geofence event: {str(e)}")

@router.get("/user-tracking/{user_id}",
            summary="Get User Location History",
            description="Retrieve user's location tracking history")
async def get_user_location_history(
    user_id: int,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of locations to return")
):
    """Get user's recent location tracking data"""
    
    try:
        user_locations = USER_LOCATIONS.get(user_id, [])
        
        # Sort by timestamp (newest first)
        sorted_locations = sorted(
            user_locations, 
            key=lambda x: x["timestamp"], 
            reverse=True
        )
        
        limited_locations = sorted_locations[:limit]
        
        # Calculate statistics
        eco_friendly_count = sum(1 for loc in limited_locations if loc.get("eco_mode", False))
        total_distance = 0
        
        # Calculate total distance
        for i in range(1, len(limited_locations)):
            curr = limited_locations[i]
            prev = limited_locations[i-1]
            distance_m = calculate_distance(
                curr["lat"], curr["lng"],
                prev["lat"], prev["lng"]
            )
            total_distance += distance_m
        
        return {
            "success": True,
            "user_id": user_id,
            "location_count": len(limited_locations),
            "total_tracked": len(user_locations),
            "statistics": {
                "eco_friendly_locations": eco_friendly_count,
                "eco_percentage": round((eco_friendly_count / max(1, len(limited_locations))) * 100, 1),
                "total_distance_km": round(total_distance / 1000, 2),
                "total_points": USER_POINTS.get(user_id, 0)
            },
            "locations": limited_locations
        }
        
    except Exception as e:
        logger.error(f"Error getting location history: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting location history: {str(e)}")

@router.post("/start-eco-tracking",
             summary="Start Eco Tracking Session",
             description="Start an eco-friendly transportation tracking session")
async def start_eco_tracking(
    session: EcoTrackingSession,
    user_id: int = Depends(get_current_user_id)
):
    """Start eco-mode tracking session"""
    
    try:
        if session.transport_mode not in ["walking", "cycling", "public_transport"]:
            raise HTTPException(
                status_code=400, 
                detail="Invalid transport mode for eco tracking"
            )
        
        # Create eco tracking session
        session_id = f"{user_id}_{datetime.now().timestamp()}"
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "transport_mode": session.transport_mode,
            "start_time": datetime.now().isoformat(),
            "start_location": session.start_location,
            "target_destination": session.target_destination,
            "points_earned": 0,
            "distance_km": 0,
            "active": True
        }
        
        USER_ECO_SESSIONS[session_id] = session_data
        
        # Award starting bonus points
        gamification_service = GamificationService(user_id)
        bonus_points = 5  # Starting bonus
        
        if user_id not in USER_POINTS:
            USER_POINTS[user_id] = 0
        USER_POINTS[user_id] += bonus_points
        
        return {
            "success": True,
            "session_id": session_id,
            "status": "eco_tracking_started",
            "transport_mode": session.transport_mode,
            "bonus_points": bonus_points,
            "total_user_points": USER_POINTS[user_id],
            "message": f"Started eco-friendly {session.transport_mode} tracking! 🌱"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting eco tracking: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting eco tracking: {str(e)}")

@router.post("/stop-eco-tracking/{session_id}",
             summary="Stop Eco Tracking Session",
             description="Stop an active eco tracking session and calculate final rewards")
async def stop_eco_tracking(
    session_id: str,
    final_location: Optional[LocationUpdate] = None,
    user_id: int = Depends(get_current_user_id)
):
    """Stop eco-mode tracking session and calculate final rewards"""
    
    try:
        if session_id not in USER_ECO_SESSIONS:
            raise HTTPException(status_code=404, detail="Eco tracking session not found")
        
        session_data = USER_ECO_SESSIONS[session_id]
        
        if session_data["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to stop this session")
        
        if not session_data.get("active", False):
            raise HTTPException(status_code=400, detail="Session already stopped")
        
        # Calculate session duration
        start_time = datetime.fromisoformat(session_data["start_time"])
        end_time = datetime.now()
        duration_hours = (end_time - start_time).total_seconds() / 3600
        
        # Calculate distance if final location provided
        total_distance_km = 0
        if final_location and session_data.get("start_location"):
            start_loc = session_data["start_location"]
            distance_m = calculate_distance(
                start_loc["lat"], start_loc["lng"],
                final_location.lat, final_location.lng
            )
            total_distance_km = distance_m / 1000
        
        # Calculate bonus points based on duration and distance
        time_bonus = min(int(duration_hours * 10), 100)  # Max 100 points for time
        distance_bonus = min(int(total_distance_km * 15), 150)  # Max 150 points for distance
        total_bonus = time_bonus + distance_bonus
        
        # Award bonus points
        USER_POINTS[user_id] += total_bonus
        
        # Update session
        session_data["active"] = False
        session_data["end_time"] = end_time.isoformat()
        session_data["duration_hours"] = round(duration_hours, 2)
        session_data["distance_km"] = round(total_distance_km, 2)
        session_data["final_bonus_points"] = total_bonus
        session_data["carbon_saved_kg"] = round(total_distance_km * 0.2, 2)  # Estimated
        
        return {
            "success": True,
            "session_id": session_id,
            "status": "eco_tracking_completed",
            "session_summary": {
                "transport_mode": session_data["transport_mode"],
                "duration_hours": session_data["duration_hours"],
                "distance_km": session_data["distance_km"],
                "final_bonus_points": total_bonus,
                "carbon_saved_kg": session_data["carbon_saved_kg"],
                "total_user_points": USER_POINTS[user_id]
            },
            "achievements": {
                "time_bonus": time_bonus,
                "distance_bonus": distance_bonus,
                "eco_warrior": duration_hours >= 2,
                "long_distance": total_distance_km >= 5
            },
            "message": f"Great job! You completed {total_distance_km:.1f}km of eco-friendly travel! 🌍"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping eco tracking: {e}")
        raise HTTPException(status_code=500, detail=f"Error stopping eco tracking: {str(e)}")

@router.get("/nearby-gems",
            summary="Get Nearby Hidden Gems",
            description="Find hidden gems and POIs near current location")
async def get_nearby_gems(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: int = Query(500, ge=50, le=5000, description="Search radius in meters"),
    user_id: int = Depends(get_current_user_id)
):
    """Get hidden gems near the specified location"""
    
    try:
        nearby_gems = check_nearby_gems(lat, lng, radius)
        
        # Check which gems have been discovered by this user
        user_discovered = DISCOVERED_GEMS.get(user_id, set())
        
        for gem in nearby_gems:
            gem["discovered"] = gem["id"] in user_discovered
            gem["potential_points"] = gem["discovery_points"] if not gem["discovered"] else 0
        
        # Separate discovered and undiscovered
        undiscovered = [gem for gem in nearby_gems if not gem["discovered"]]
        discovered = [gem for gem in nearby_gems if gem["discovered"]]
        
        return {
            "success": True,
            "search_location": {"lat": lat, "lng": lng},
            "search_radius_m": radius,
            "total_gems_found": len(nearby_gems),
            "undiscovered_gems": undiscovered,
            "discovered_gems": discovered,
            "potential_points": sum(gem["potential_points"] for gem in nearby_gems),
            "user_discovery_count": len(user_discovered)
        }
        
    except Exception as e:
        logger.error(f"Error getting nearby gems: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting nearby gems: {str(e)}")

@router.get("/user-stats/{user_id}",
            summary="Get User Location & Eco Stats",
            description="Get comprehensive user statistics for location and eco tracking")
async def get_user_stats(user_id: int):
    """Get comprehensive user location and eco statistics"""
    
    try:
        locations = USER_LOCATIONS.get(user_id, [])
        discovered_gems = DISCOVERED_GEMS.get(user_id, set())
        total_points = USER_POINTS.get(user_id, 0)
        
        # Calculate eco-friendly percentage
        eco_locations = [loc for loc in locations if loc.get("eco_mode", False)]
        eco_percentage = (len(eco_locations) / max(1, len(locations))) * 100
        
        # Calculate total distance
        total_distance_km = 0
        for i in range(1, len(locations)):
            distance_m = calculate_distance(
                locations[i-1]["lat"], locations[i-1]["lng"],
                locations[i]["lat"], locations[i]["lng"]
            )
            total_distance_km += distance_m / 1000
        
        # Get active eco sessions
        active_sessions = [
            session for session in USER_ECO_SESSIONS.values()
            if session["user_id"] == user_id and session.get("active", False)
        ]
        
        return {
            "success": True,
            "user_id": user_id,
            "statistics": {
                "total_eco_points": total_points,
                "locations_tracked": len(locations),
                "eco_friendly_percentage": round(eco_percentage, 1),
                "total_distance_km": round(total_distance_km, 2),
                "gems_discovered": len(discovered_gems),
                "active_eco_sessions": len(active_sessions)
            },
            "achievements": {
                "eco_warrior": eco_percentage >= 70,
                "explorer": len(discovered_gems) >= 5,
                "distance_champion": total_distance_km >= 50,
                "point_collector": total_points >= 500
            },
            "recent_activity": locations[-10:] if locations else [],
            "active_sessions": active_sessions
        }
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting user stats: {str(e)}")

@router.get("/health",
            summary="Location Service Health",
            description="Check location service health and statistics")
async def location_service_health():
    """Location service health check"""
    
    return {
        "service": "location_tracking",
        "status": "healthy",
        "features": {
            "location_updates": True,
            "eco_tracking": True,
            "geofence_events": True,
            "hidden_gem_discovery": True,
            "carbon_tracking": True,
            "points_system": True
        },
        "statistics": {
            "total_users_tracked": len(USER_LOCATIONS),
            "total_locations_stored": sum(len(locs) for locs in USER_LOCATIONS.values()),
            "active_eco_sessions": sum(1 for session in USER_ECO_SESSIONS.values() if session.get("active")),
            "total_gems_available": len(MOCK_HIDDEN_GEMS),
            "total_discoveries": sum(len(gems) for gems in DISCOVERED_GEMS.values())
        },
        "mock_data": {
            "hidden_gems_available": len(MOCK_HIDDEN_GEMS),
            "sample_gem_locations": [
                {"name": gem["name"], "category": gem["category"]} 
                for gem in MOCK_HIDDEN_GEMS[:3]
            ]
        },
        "database_mode": "mock_storage",
        "version": "1.0.0"
    }
