from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
import logging
import json
import sys
import os

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

logger = logging.getLogger(__name__)

# ✅ FIXED IMPORTS - Handle both relative and absolute
DATABASE_AVAILABLE = False
algorithm_service = None

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

try:
    from services.algorithm_service import algorithm_service
    if algorithm_service:
        logger.info("Algorithm service imported successfully")
except ImportError:
    try:
        from ..services.algorithm_service import algorithm_service
        if algorithm_service:
            logger.info("Algorithm service imported successfully (relative)")
    except ImportError:
        logger.warning("Algorithm service not available")
        algorithm_service = None

# ✅ Create router
router = APIRouter(
    prefix="/itinerary",
    tags=["🧠 Itinerary Optimization"],
    responses={404: {"description": "Not found"}}
)

# ✅ Enhanced Pydantic models with validation (Pydantic v2 compatible)
class DestinationInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Destination name")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude between -90 and 90")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude between -180 and 180")
    rating: Optional[float] = Field(4.0, ge=0, le=10, description="Rating from 0 to 10")
    stay_duration: Optional[float] = Field(2.0, ge=0.5, le=48, description="Stay duration in hours")
    category: Optional[str] = Field("tourist_attraction", description="Destination category")
    address: Optional[str] = Field("", max_length=500, description="Full address")
    traffic_score: Optional[float] = Field(5.0, ge=1, le=10, description="Traffic score 1-10")
    weather_match: Optional[float] = Field(8.0, ge=0, le=10, description="Weather compatibility 0-10")

class ItineraryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Trip title")
    user_id: int = Field(..., gt=0, description="User ID")
    destinations: List[DestinationInput] = Field(..., min_length=1, max_length=50)
    start_latitude: float = Field(..., ge=-90, le=90)
    start_longitude: float = Field(..., ge=-180, le=180)
    start_date: Optional[str] = Field(None, description="Trip start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Trip end date (YYYY-MM-DD)")
    start_time: Optional[str] = Field("09:00:00", pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$")
    timezone: Optional[str] = Field("Asia/Kolkata", description="Timezone for scheduling")

class WeightsUpdate(BaseModel):
    w1_rating: float = Field(0.4, ge=0, le=1, description="Rating weight")
    w2_distance: float = Field(0.3, ge=0, le=1, description="Distance weight")
    w3_traffic: float = Field(0.2, ge=0, le=1, description="Traffic weight")
    w4_weather: float = Field(0.1, ge=0, le=1, description="Weather weight")
    
    @validator('w4_weather')
    def weights_sum_reasonable(cls, v, values):
        # Ensure weights sum to approximately 1.0 (allow some flexibility)
        if len(values) == 3:  # All weights are set
            total = sum(values.values()) + v
            if not 0.8 <= total <= 1.2:
                raise ValueError('Weights should sum to approximately 1.0')
        return v

# ✅ Mock Data for Testing
MOCK_ITINERARIES = {}
MOCK_WEIGHTS = {}

def create_mock_result(destinations_list, start_location, start_time="09:00:00"):
    """Create mock optimization result"""
    
    # Sort destinations by rating (simple greedy approach)
    sorted_dests = sorted(destinations_list, key=lambda x: x.get('rating', 0), reverse=True)
    
    optimized_route = []
    total_score = 0
    total_distance = 0
    
    for i, dest in enumerate(sorted_dests):
        dest_copy = dest.copy()
        dest_copy['visit_order'] = i + 1
        dest_copy['calculated_score'] = dest.get('rating', 4.0) * 2.5
        dest_copy['distance_from_previous'] = i * 5.2  # Mock distance
        
        # Add time scheduling
        hour = int(start_time[:2]) + (i * 3)  # 3 hours per destination
        dest_copy['arrival_time'] = f"{hour:02d}:00:00"
        dest_copy['departure_time'] = f"{hour + int(dest.get('stay_duration', 2)):02d}:00:00"
        
        optimized_route.append(dest_copy)
        total_score += dest_copy['calculated_score']
        total_distance += dest_copy['distance_from_previous']
    
    return {
        "success": True,
        "optimized_route": optimized_route,
        "total_score": round(total_score, 2),
        "total_distance_km": round(total_distance, 2),
        "algorithm_used": "greedy_with_mock_time_scheduling",
        "time_scheduling": {
            "daily_start_time": start_time,
            "total_duration_hours": len(optimized_route) * 3,
            "break_time_included": True,
            "arrival_departure_calculated": True
        },
        "costs": {
            "total_distance_km": round(total_distance, 2),
            "total_estimated_cost": total_distance * 15,  # ₹15 per km
            "fuel_cost": total_distance * 8,
            "food_cost": len(optimized_route) * 500,
            "activity_cost": len(optimized_route) * 300
        },
        "message": "Itinerary optimized successfully with complete time scheduling!"
    }

# ✅ API Endpoints
@router.post("/create-complete-itinerary", 
            summary="🧠 Create Complete Itinerary with Time Scheduling",
            description="Create optimized itinerary with complete time scheduling using enhanced greedy algorithm")
async def create_complete_itinerary(
    itinerary_data: ItineraryCreate,
    db: Session = Depends(get_db) if DATABASE_AVAILABLE else None
):
    """Create complete itinerary with route optimization and time scheduling"""
    
    try:
        # Convert destinations to dict format
        destinations_list = []
        for dest in itinerary_data.destinations:
            destinations_list.append({
                "name": dest.name,
                "latitude": dest.latitude,
                "longitude": dest.longitude,
                "rating": dest.rating,
                "stay_duration": dest.stay_duration,
                "category": dest.category,
                "address": dest.address,
                "traffic_score": dest.traffic_score,
                "weather_match": dest.weather_match
            })
        
        start_location = (itinerary_data.start_latitude, itinerary_data.start_longitude)
        start_time = itinerary_data.start_time or "09:00:00"
        timezone_str = itinerary_data.timezone or "Asia/Kolkata"
        
        # Require algorithm service (no mock fallback)
        if not algorithm_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Algorithm service unavailable. Live itinerary generation requires the algorithm service."
            )
        result = algorithm_service.create_complete_itinerary(
            destinations=destinations_list,
            start_location=start_location,
            start_time=start_time,
            trip_date=itinerary_data.start_date,
            timezone_str=timezone_str,
            weights=None
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to create itinerary")
            )
        
        # If multi-day trip requested, split intelligently across days (3–4 stops/day, balanced)
        try:
            # Perform day-wise split whenever multi-day range is provided and we have a route
            if itinerary_data.start_date and itinerary_data.end_date and result.get("optimized_route"):
                from datetime import date as _date, timedelta as _timedelta, datetime as _dt
                sd = str(itinerary_data.start_date)
                ed = str(itinerary_data.end_date)
                d0 = _date.fromisoformat(sd)
                d1 = _date.fromisoformat(ed)
                num_days = max(1, (d1 - d0).days + 1)
                route = result["optimized_route"]

                # Framework targets
                base_per_day_cap = 8.0   # ~8 hours target per day
                base_per_day_max = 4     # up to 4 attractions per day (3 main + 1 optional)

                # Ensure one lighter day on longer trips
                per_day_max_by_day = [base_per_day_max] * num_days
                per_day_cap_by_day = [base_per_day_cap] * num_days
                if num_days >= 4:
                    light_idx = num_days // 2
                    per_day_max_by_day[light_idx] = 3
                    per_day_cap_by_day[light_idx] = 6.0

                day_chunks = []
                current_chunk = []
                current_hours = 0.0
                recent_categories = []

                def _cat(d):
                    return str(d.get('category', '')).lower()

                def _current_limits():
                    idx = len(day_chunks)
                    return per_day_cap_by_day[min(idx, num_days-1)], per_day_max_by_day[min(idx, num_days-1)]

                for dest in route:
                    stay = float(dest.get('stay_duration_hours', dest.get('stay_duration', 2.0)) or 2.0)
                    travel = float(dest.get('travel_time_to_next_hours', 0.0) or 0.0)
                    add_h = max(0.0, stay) + max(0.0, travel)
                    new_cat = _cat(dest)

                    per_day_cap, per_day_max = _current_limits()
                    would_exceed_time = current_chunk and (current_hours + add_h) > per_day_cap
                    would_exceed_count = len(current_chunk) >= per_day_max
                    would_create_triple = False
                    if len(recent_categories) >= 2 and new_cat:
                        if recent_categories[-1] == recent_categories[-2] == new_cat:
                            would_create_triple = True

                    start_new_day = (
                        current_chunk and (would_exceed_time or would_exceed_count or would_create_triple)
                        and len(day_chunks) < num_days - 1
                    )

                    if start_new_day:
                        day_chunks.append(current_chunk)
                        current_chunk = [dest]
                        current_hours = add_h
                        recent_categories = [new_cat]
                    else:
                        current_chunk.append(dest)
                        current_hours += add_h
                        recent_categories.append(new_cat)
                        recent_categories = recent_categories[-2:]
                if current_chunk:
                    day_chunks.append(current_chunk)

                # If we still have fewer chunks than days requested, spread remaining by splitting largest chunks
                while len(day_chunks) < num_days and any(len(c) > 1 for c in day_chunks):
                    largest_idx = max(range(len(day_chunks)), key=lambda i: len(day_chunks[i]))
                    chunk = day_chunks.pop(largest_idx)
                    mid = max(1, len(chunk)//2)
                    day_chunks.insert(largest_idx, chunk[:mid])
                    day_chunks.insert(largest_idx+1, chunk[mid:])

                # Rebuild schedule per day and adjust dates
                combined = []
                combined_daily = {}
                for day_index, chunk in enumerate(day_chunks):
                    # Compute per-day schedule (includes travel buffers and lunch/rest suggestions)
                    scheduled = algorithm_service.calculate_visit_schedule(chunk, start_time, timezone_str) if algorithm_service else chunk
                    day_date = d0 + _timedelta(days=day_index)
                    adjusted = []
                    for item in scheduled:
                        try:
                            def _shift(iso_s: str) -> str:
                                dt = _dt.fromisoformat(iso_s.replace('Z', '+00:00')) if iso_s else None
                                if not dt:
                                    return ''
                                dt = dt.replace(year=day_date.year, month=day_date.month, day=day_date.day)
                                return dt.isoformat()
                            if item.get('scheduled_arrival_time'):
                                item['scheduled_arrival_time'] = _shift(item.get('scheduled_arrival_time'))
                            if item.get('scheduled_departure_time'):
                                item['scheduled_departure_time'] = _shift(item.get('scheduled_departure_time'))
                        except Exception:
                            pass
                        adjusted.append(item)
                    combined.extend(adjusted)
                    # Daily summary keyed by date (YYYY-MM-DD)
                    day_key = day_date.strftime('%Y-%m-%d')
                    if algorithm_service:
                        day_summary = algorithm_service.generate_daily_schedule(adjusted, day_key)
                        if day_summary:
                            combined_daily.update(day_summary)

                # Update result with combined multi-day plan
                if algorithm_service:
                    total_time = algorithm_service.calculate_total_travel_time(combined)
                    costs = algorithm_service.estimate_costs(combined)
                else:
                    total_time = sum(float(d.get('stay_duration_hours', d.get('stay_duration', 2.0)) or 2.0) for d in combined)
                    costs = {"total_distance_km": sum(float(d.get('distance_from_previous', 0.0) or 0.0) for d in combined)}
                total_score = sum(float(d.get('calculated_score', 0)) for d in combined)
                result["optimized_route"] = combined
                if combined_daily:
                    result["daily_schedule"] = combined_daily
                if "route_summary" not in result:
                    result["route_summary"] = {}
                result["route_summary"].update({
                    "total_destinations": len(combined),
                    "total_score": round(total_score, 2),
                    "total_travel_time_hours": total_time,
                    "total_distance_km": costs.get("total_distance_km", 0.0),
                    "estimated_duration_days": len(day_chunks)
                })
        except Exception as split_err:
            logger.warning(f"Multi-day smart split skipped: {split_err}")
        
        # Store in mock storage for retrieval
        itinerary_id = len(MOCK_ITINERARIES) + 1
        MOCK_ITINERARIES[itinerary_id] = {
            "id": itinerary_id,
            "title": itinerary_data.title,
            "user_id": itinerary_data.user_id,
            "start_date": itinerary_data.start_date,
            "end_date": itinerary_data.end_date,
            "result": result,
            "created_at": datetime.now().isoformat()
        }
        
        result["itinerary_id"] = itinerary_id
        result["service_mode"] = "algorithm_service"
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating complete itinerary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating complete itinerary: {str(e)}"
        )

@router.post("/create-optimized", 
            summary="⚡ Create Basic Optimized Itinerary",
            description="Create optimized itinerary using greedy algorithm (without time scheduling)")
async def create_optimized_itinerary(
    itinerary_data: ItineraryCreate,
    db: Session = Depends(get_db) if DATABASE_AVAILABLE else None
):
    """Create and optimize an itinerary using greedy algorithm (legacy endpoint)"""
    
    try:
        # Convert destinations to dict format
        destinations_list = []
        for dest in itinerary_data.destinations:
            destinations_list.append({
                "name": dest.name,
                "latitude": dest.latitude,
                "longitude": dest.longitude,
                "rating": dest.rating,
                "stay_duration": dest.stay_duration,
                "category": dest.category,
                "address": dest.address,
                "traffic_score": dest.traffic_score,
                "weather_match": dest.weather_match
            })
        
        start_location = (itinerary_data.start_latitude, itinerary_data.start_longitude)
        
        # Require algorithm service (no mock fallback)
        if not (algorithm_service and hasattr(algorithm_service, 'optimize_route_greedy')):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Algorithm service unavailable. Live optimization requires the algorithm service."
            )

        optimized_route = algorithm_service.optimize_route_greedy(
            destinations_list, start_location, None
        )
        
        if not optimized_route:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to optimize route. Please check destination data."
            )
        
        # Calculate metrics
        total_score = sum(dest.get('calculated_score', 0) for dest in optimized_route)
        total_time = sum(dest.get('stay_duration', 2) for dest in optimized_route)
        
        costs = {
            "total_distance_km": sum(dest.get('distance_from_previous', 0) for dest in optimized_route),
            "total_estimated_cost": len(optimized_route) * 800,
            "fuel_cost": sum(dest.get('distance_from_previous', 0) for dest in optimized_route) * 8,
            "food_cost": len(optimized_route) * 500
        }
        
        response_data = {
            "success": True,
            "optimized_route": optimized_route,
            "total_score": round(total_score, 2),
            "total_travel_time_hours": total_time,
            "costs": costs,
            "message": "Itinerary optimized successfully using greedy algorithm",
            "algorithm_used": "greedy_scoring_formula",
            "service_mode": "algorithm_service"
        }
        
        # Store in mock storage
        itinerary_id = len(MOCK_ITINERARIES) + 1
        MOCK_ITINERARIES[itinerary_id] = {
            "id": itinerary_id,
            "title": itinerary_data.title,
            "user_id": itinerary_data.user_id,
            "result": response_data,
            "created_at": datetime.now().isoformat()
        }
        
        response_data["itinerary_id"] = itinerary_id
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating optimized itinerary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating optimized itinerary: {str(e)}"
        )

@router.get("/alternatives/{itinerary_id}",
           summary="🔄 Get Alternative Routes", 
           description="Generate alternative optimized routes using different weight combinations")
async def get_alternative_routes(
    itinerary_id: int,
    db: Session = Depends(get_db) if DATABASE_AVAILABLE else None
):
    """Get alternative optimized routes for an existing itinerary"""
    
    try:
        # Get itinerary from mock storage
        if itinerary_id not in MOCK_ITINERARIES:
            raise HTTPException(status_code=404, detail="Itinerary not found")
        
        itinerary = MOCK_ITINERARIES[itinerary_id]
        original_route = itinerary["result"]["optimized_route"]
        
        # Generate alternatives with different weights
        alternatives = []
        weight_combinations = [
            {"focus": "Rating Priority", "w1": 0.6, "w2": 0.2, "w3": 0.1, "w4": 0.1},
            {"focus": "Distance Priority", "w1": 0.2, "w2": 0.6, "w3": 0.1, "w4": 0.1},
            {"focus": "Traffic Priority", "w1": 0.2, "w2": 0.2, "w3": 0.5, "w4": 0.1},
            {"focus": "Balanced Route", "w1": 0.25, "w2": 0.25, "w3": 0.25, "w4": 0.25}
        ]
        
        for i, weights in enumerate(weight_combinations):
            # Create alternative by shuffling and re-scoring
            alt_route = original_route.copy()
            if i % 2 == 0:
                alt_route.reverse()  # Simple alternative generation
            
            # Recalculate scores with new weights
            for dest in alt_route:
                new_score = (
                    weights["w1"] * dest.get("rating", 4.0) +
                    weights["w2"] * (10 - dest.get("distance_from_previous", 5) / 10) +
                    weights["w3"] * dest.get("traffic_score", 5) +
                    weights["w4"] * dest.get("weather_match", 8)
                )
                dest["calculated_score"] = round(new_score, 2)
            
            alternatives.append({
                "alternative_id": i + 1,
                "focus": weights["focus"],
                "weights_used": weights,
                "route": alt_route,
                "total_score": sum(dest["calculated_score"] for dest in alt_route),
                "total_destinations": len(alt_route),
                "estimated_time": sum(dest.get("stay_duration", 2) for dest in alt_route)
            })
        
        return {
            "success": True,
            "original_itinerary_id": itinerary_id,
            "alternatives": alternatives,
            "total_alternatives": len(alternatives),
            "message": "Alternative routes generated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating alternatives: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating alternatives: {str(e)}"
        )

@router.put("/weights/{user_id}",
           summary="⚖️ Update Optimization Weights",
           description="Update user's optimization weights for the greedy algorithm scoring formula")
async def update_optimization_weights(
    user_id: int,
    weights: WeightsUpdate,
    db: Session = Depends(get_db) if DATABASE_AVAILABLE else None
):
    """Update user's optimization weights for the scoring algorithm"""
    
    try:
        # Store in mock storage
        MOCK_WEIGHTS[user_id] = weights.dict()
        
        return {
            "success": True,
            "user_id": user_id,
            "weights": weights.dict(),
            "message": "Optimization weights updated successfully",
            "storage_mode": "database" if DATABASE_AVAILABLE else "in_memory"
        }
        
    except Exception as e:
        logger.error(f"Error updating weights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating weights: {str(e)}"
        )

@router.get("/{itinerary_id}",
           summary="📋 Get Itinerary Details",
           description="Retrieve complete itinerary with optimized route and calculated scores")
async def get_itinerary(
    itinerary_id: int,
    db: Session = Depends(get_db) if DATABASE_AVAILABLE else None
):
    """Get complete itinerary with optimized route"""
    
    try:
        if itinerary_id not in MOCK_ITINERARIES:
            raise HTTPException(status_code=404, detail="Itinerary not found")
        
        itinerary = MOCK_ITINERARIES[itinerary_id]
        
        return {
            "success": True,
            "itinerary": {
                "id": itinerary["id"],
                "title": itinerary["title"],
                "user_id": itinerary["user_id"],
                "start_date": itinerary.get("start_date"),
                "end_date": itinerary.get("end_date"),
                "created_at": itinerary["created_at"],
                "optimization_result": itinerary["result"],
                "storage_mode": "database" if DATABASE_AVAILABLE else "in_memory"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving itinerary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving itinerary: {str(e)}"
        )

@router.get("/list/{user_id}",
           summary="📝 List User Itineraries",
           description="Get all itineraries for a specific user")
async def get_user_itineraries(
    user_id: int,
    limit: int = Query(10, ge=1, le=50, description="Maximum number of itineraries to return")
):
    """Get all itineraries for a user"""
    
    try:
        user_itineraries = []
        for itinerary_id, itinerary in MOCK_ITINERARIES.items():
            if itinerary["user_id"] == user_id:
                user_itineraries.append({
                    "id": itinerary_id,
                    "title": itinerary["title"],
                    "created_at": itinerary["created_at"],
                    "total_destinations": len(itinerary["result"]["optimized_route"]),
                    "total_score": itinerary["result"]["total_score"],
                    "algorithm_used": itinerary["result"].get("algorithm_used", "unknown")
                })
        
        # Sort by creation date (newest first)
        user_itineraries.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "success": True,
            "user_id": user_id,
            "itineraries": user_itineraries[:limit],
            "total_count": len(user_itineraries),
            "returned_count": min(len(user_itineraries), limit)
        }
        
    except Exception as e:
        logger.error(f"Error getting user itineraries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user itineraries: {str(e)}"
        )

@router.get("/weights/{user_id}",
           summary="⚖️ Get User Weights",
           description="Get current optimization weights for user")  
async def get_user_weights(
    user_id: int,
    db: Session = Depends(get_db) if DATABASE_AVAILABLE else None
):
    """Get current optimization weights for user"""
    
    try:
        weights = MOCK_WEIGHTS.get(user_id, {
            "w1_rating": 0.4,
            "w2_distance": 0.3,
            "w3_traffic": 0.2,
            "w4_weather": 0.1
        })
        
        return {
            "success": True,
            "user_id": user_id,
            "weights": weights,
            "storage_mode": "database" if DATABASE_AVAILABLE else "in_memory"
        }
        
    except Exception as e:
        logger.error(f"Error getting user weights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user weights: {str(e)}"
        )

@router.get("/health",
           summary="🏥 Itinerary Service Health",
           description="Check health status of itinerary optimization service")
async def itinerary_service_health():
    """Health check for itinerary service"""
    
    return {
        "service": "itinerary_optimization",
        "status": "healthy",
        "algorithm_service": algorithm_service is not None,
        "database_available": DATABASE_AVAILABLE,
        "enhanced_features": {
            "complete_time_scheduling": "active" if algorithm_service else "mock_mode",
            "daily_schedule_generation": "active" if algorithm_service else "mock_mode",
            "break_time_planning": "active" if algorithm_service else "mock_mode",
            "arrival_departure_times": "active" if algorithm_service else "mock_mode"
        },
        "features": {
            "greedy_algorithm": "active",
            "time_scheduling": "active",
            "alternative_routes": "active",
            "cost_estimation": "active",
            "weight_customization": "active"
        },
        "endpoints": {
            "create_complete_itinerary": "/create-complete-itinerary",
            "create_basic_optimized": "/create-optimized",
            "get_alternatives": "/alternatives/{itinerary_id}",
            "update_weights": "/weights/{user_id}",
            "get_itinerary": "/{itinerary_id}",
            "list_user_itineraries": "/list/{user_id}",
            "get_user_weights": "/weights/{user_id}"
        },
        "statistics": {
            "total_itineraries": len(MOCK_ITINERARIES),
            "total_users_with_weights": len(MOCK_WEIGHTS)
        },
        "scoring_formula": "w1×(rating) - w2×(distance) - w3×(traffic) + w4×(weather_match)",
        "pydantic_version": "v2_compatible",
        "service_mode": "algorithm_service" if algorithm_service else "mock_mode"
    }
