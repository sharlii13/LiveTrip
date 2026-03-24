from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from sqlalchemy.orm import Session
from datetime import datetime
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

# ✅ SIMPLE IMPORTS - Fixed
try:
    from database import get_db
except ImportError:
    try:
        from ..database import get_db
    except ImportError:
        def get_db():
            return None

# ✅ Create router
router = APIRouter(prefix="/discovery", tags=["discovery"])

# ✅ Simple Enums
class ActionType(str, Enum):
    PUBLIC_TRANSPORT = "public_transport"
    BIKE_USAGE = "bike_usage" 
    WALKING = "walking"
    ECO_HOTEL = "eco_hotel"
    LOCAL_FOOD = "local_food"
    HIDDEN_GEM_DISCOVERY = "hidden_gem_discovery"
    CONTENT_SUBMISSION = "content_submission"

class GemCategory(str, Enum):
    CAFE = "cafe"
    VIEWPOINT = "viewpoint"
    LOCAL_ART = "local_art"
    PARK = "park"
    TEMPLE = "temple"
    MARKET = "market"
    STREET_FOOD = "street_food"
    BEACH = "beach"

# ✅ Simple Pydantic Models
class HiddenGemSubmission(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    category: str = "viewpoint"
    address: Optional[str] = None
    photos: Optional[List[str]] = []

class GemDiscovery(BaseModel):
    gem_id: int
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    discovery_notes: Optional[str] = None

# ✅ Simple Mock User Function
async def get_current_user_id() -> int:
    """Get current user ID"""
    return 1

# ✅ Simple Helper Functions
def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between coordinates in meters"""
    try:
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
    except Exception:
        return 0.0

# ✅ Mock Data for Testing
MOCK_GEMS = [
    {
        "id": 1,
        "name": "Hidden Rooftop Cafe",
        "description": "Cozy cafe with city views",
        "category": "cafe",
        "lat": 19.0760,
        "lng": 72.8777,
        "discovery_points": 50,
        "address": "Mumbai, India",
        "is_verified": True,
        "created_at": "2025-01-15T10:00:00"
    },
    {
        "id": 2,
        "name": "Secret Beach Viewpoint", 
        "description": "Stunning ocean views",
        "category": "viewpoint",
        "lat": 19.0800,
        "lng": 72.8800,
        "discovery_points": 75,
        "address": "Mumbai Coast",
        "is_verified": True,
        "created_at": "2025-01-16T15:30:00"
    },
    {
        "id": 3,
        "name": "Local Art Gallery",
        "description": "Contemporary Indian art space",
        "category": "local_art",
        "lat": 19.0720,
        "lng": 72.8750,
        "discovery_points": 60,
        "address": "Colaba, Mumbai",
        "is_verified": True,
        "created_at": "2025-01-17T12:00:00"
    }
]

USER_DISCOVERIES = {}  # Store user discoveries in memory

# ✅ API Endpoints
@router.post("/submit-gem")
async def submit_hidden_gem(
    gem: HiddenGemSubmission,
    db: Session = Depends(get_db)
):
    """Submit a new hidden gem"""
    
    try:
        user_id = await get_current_user_id()
        
        # Create new gem
        new_gem = {
            "id": len(MOCK_GEMS) + 1,
            "name": gem.name,
            "description": gem.description,
            "category": gem.category,
            "lat": gem.lat,
            "lng": gem.lng,
            "address": gem.address,
            "discovery_points": 50,
            "is_verified": False,
            "created_by_user_id": user_id,
            "created_at": datetime.now().isoformat()
        }
        
        # Add to mock data
        MOCK_GEMS.append(new_gem)
        
        return {
            "success": True,
            "gem_id": new_gem["id"],
            "points_awarded": 50,
            "status": "pending_verification",
            "message": "Thank you for contributing! Your gem will be verified soon."
        }
        
    except Exception as e:
        logger.error(f"Error submitting gem: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit gem")

@router.get("/nearby-gems")
async def get_nearby_gems(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: int = Query(1000, ge=100, le=10000),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get nearby hidden gems"""
    
    try:
        user_id = await get_current_user_id()
        user_discoveries = USER_DISCOVERIES.get(user_id, [])
        
        # Filter gems within radius
        nearby_gems = []
        for gem in MOCK_GEMS:
            if not gem.get("is_verified", False):
                continue
                
            distance = calculate_distance(lat, lng, gem["lat"], gem["lng"])
            if distance <= radius:
                # Skip if already discovered
                if gem["id"] in user_discoveries:
                    continue
                    
                # Filter by category
                if category and gem["category"] != category:
                    continue
                
                gem_data = gem.copy()
                gem_data["distance_meters"] = int(distance)
                gem_data["is_discovered"] = False
                nearby_gems.append(gem_data)
        
        # Sort by distance
        nearby_gems.sort(key=lambda x: x["distance_meters"])
        
        return {
            "success": True,
            "gems": nearby_gems,
            "total_discoverable": len(nearby_gems),
            "search_radius": radius,
            "user_location": {"lat": lat, "lng": lng}
        }
        
    except Exception as e:
        logger.error(f"Error getting nearby gems: {e}")
        raise HTTPException(status_code=500, detail="Failed to get nearby gems")

@router.post("/discover-gem")
async def discover_gem(
    discovery: GemDiscovery,
    db: Session = Depends(get_db)
):
    """Discover a hidden gem"""
    
    try:
        user_id = await get_current_user_id()
        
        # Find the gem
        gem = None
        for g in MOCK_GEMS:
            if g["id"] == discovery.gem_id:
                gem = g
                break
        
        if not gem:
            raise HTTPException(status_code=404, detail="Hidden gem not found")
        
        # Check if already discovered
        if user_id not in USER_DISCOVERIES:
            USER_DISCOVERIES[user_id] = []
            
        if discovery.gem_id in USER_DISCOVERIES[user_id]:
            raise HTTPException(status_code=400, detail="Already discovered this gem")
        
        # Check proximity (within 100 meters)
        distance = calculate_distance(discovery.lat, discovery.lng, gem["lat"], gem["lng"])
        if distance > 100:
            raise HTTPException(
                status_code=400,
                detail=f"Too far from gem. Distance: {int(distance)}m (max: 100m)"
            )
        
        # Mark as discovered
        USER_DISCOVERIES[user_id].append(discovery.gem_id)
        
        points_awarded = gem.get("discovery_points", 50)
        
        return {
            "success": True,
            "message": f"Congratulations! You discovered '{gem['name']}'",
            "points_awarded": points_awarded,
            "gem_name": gem["name"],
            "total_discoveries": len(USER_DISCOVERIES[user_id])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error discovering gem: {e}")
        raise HTTPException(status_code=500, detail="Failed to discover gem")

@router.get("/my-discoveries")
async def get_my_discoveries(db: Session = Depends(get_db)):
    """Get user's discovered gems"""
    
    try:
        user_id = await get_current_user_id()
        discovery_ids = USER_DISCOVERIES.get(user_id, [])
        
        discoveries = []
        total_points = 0
        
        for gem in MOCK_GEMS:
            if gem["id"] in discovery_ids:
                points = gem.get("discovery_points", 50)
                discoveries.append({
                    "id": gem["id"],
                    "name": gem["name"],
                    "description": gem["description"],
                    "category": gem["category"],
                    "lat": gem["lat"],
                    "lng": gem["lng"],
                    "points_earned": points,
                    "discovered_at": datetime.now().isoformat()
                })
                total_points += points
        
        return {
            "success": True,
            "discoveries": discoveries,
            "total_discovered": len(discoveries),
            "total_points_from_discoveries": total_points
        }
        
    except Exception as e:
        logger.error(f"Error getting discoveries: {e}")
        raise HTTPException(status_code=500, detail="Failed to get discoveries")

@router.get("/categories")
async def get_gem_categories():
    """Get available gem categories"""
    
    categories = [
        {"value": "cafe", "name": "Cafe", "description": "Local cafes and coffee shops"},
        {"value": "viewpoint", "name": "Viewpoint", "description": "Scenic views and photo spots"},
        {"value": "local_art", "name": "Local Art", "description": "Art galleries and street art"},
        {"value": "park", "name": "Park", "description": "Parks and green spaces"},
        {"value": "temple", "name": "Temple", "description": "Temples and spiritual places"},
        {"value": "market", "name": "Market", "description": "Local markets and bazaars"},
        {"value": "street_food", "name": "Street Food", "description": "Street food and local eateries"},
        {"value": "beach", "name": "Beach", "description": "Beaches and coastal areas"}
    ]
    
    return {
        "success": True,
        "categories": categories,
        "total_categories": len(categories)
    }

@router.get("/leaderboard")
async def get_discovery_leaderboard(
    limit: int = Query(10, ge=1, le=50)
):
    """Get discovery leaderboard"""
    
    # Calculate leaderboard from USER_DISCOVERIES
    leaderboard = []
    for user_id, discoveries in USER_DISCOVERIES.items():
        total_points = 0
        for gem in MOCK_GEMS:
            if gem["id"] in discoveries:
                total_points += gem.get("discovery_points", 50)
        
        leaderboard.append({
            "rank": 0,  # Will be set after sorting
            "user_name": f"User {user_id}",
            "discoveries": len(discoveries),
            "points": total_points,
            "level": min(5, len(discoveries) // 2 + 1)
        })
    
    # Sort by points and set ranks
    leaderboard.sort(key=lambda x: x["points"], reverse=True)
    for i, entry in enumerate(leaderboard[:limit]):
        entry["rank"] = i + 1
    
    # Add mock data if empty
    if not leaderboard:
        leaderboard = [
            {"rank": 1, "user_name": "Explorer", "discoveries": 5, "points": 250, "level": 3},
            {"rank": 2, "user_name": "Adventurer", "discoveries": 3, "points": 150, "level": 2}
        ]
    
    return {
        "success": True,
        "leaderboard": leaderboard[:limit],
        "last_updated": datetime.now().isoformat()
    }

@router.get("/stats")
async def get_discovery_stats():
    """Get overall discovery statistics"""
    
    total_gems = len(MOCK_GEMS)
    verified_gems = len([g for g in MOCK_GEMS if g.get("is_verified", False)])
    total_discoveries = sum(len(discoveries) for discoveries in USER_DISCOVERIES.values())
    
    return {
        "success": True,
        "stats": {
            "total_gems": total_gems,
            "verified_gems": verified_gems,
            "pending_verification": total_gems - verified_gems,
            "total_discoveries": total_discoveries,
            "active_users": len(USER_DISCOVERIES),
            "average_discoveries_per_user": total_discoveries / max(1, len(USER_DISCOVERIES))
        }
    }

@router.get("/health")
async def discovery_health():
    """Discovery service health check"""
    return {
        "service": "discovery",
        "status": "healthy",
        "features": {
            "gem_submission": True,
            "gem_discovery": True,
            "proximity_verification": True,
            "leaderboard": True,
            "categories": True
        },
        "mock_data_count": len(MOCK_GEMS),
        "version": "1.0.0"
    }
