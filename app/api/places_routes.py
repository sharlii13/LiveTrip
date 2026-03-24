"""
Places API routes for frontend compatibility
"""
import logging
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from app.models.schemas import PlanRequest, HotelLocation
from app.api.itinerary_routes import plan_one_day

logger = logging.getLogger(__name__)

# Create places router with both /api and root prefixes for compatibility
router = APIRouter(
    prefix="/api",
    tags=["places"],
)

# Also create a root-level router for frontend compatibility
root_router = APIRouter(
    prefix="",
    tags=["places"],
)

@router.get("/places/search")
async def search_places(query: str = "", limit: int = 8) -> Dict[str, Any]:
    """
    Search for places/POIs in a city using real-time Google Places API.
    """
    try:
        # Use real Google Places API
        from app.services.google_places import GooglePlacesService
        
        places_service = GooglePlacesService()
        
        # If no specific query, search for tourist attractions in the city
        search_query = query if query else "tourist attractions"
        
        # Search for places
        places = await places_service.search_places(search_query, limit=limit)
        
        # Convert to expected format
        items = []
        for place in places:
            items.append({
                "name": place.name,
                "location": {"lat": place.lat, "lng": place.lng},
                "geometry": {"location": {"lat": place.lat, "lng": place.lng}},
                "rating": place.rating,
                "formatted_address": place.formatted_address,
                "types": place.types,
                "place_id": place.place_id
            })
        
        logger.info(f"Found {len(items)} places for query: {search_query}")
        return {"items": items}
        
    except Exception as e:
        logger.error(f"Google Places API error: {e}")
        # If Google Places API fails, return empty result (no fallback to mock data)
        return {"items": []}
        

# Add the same endpoint to root router for frontend compatibility
@root_router.get("/places/search")
async def search_places_root(query: str = "", limit: int = 8) -> Dict[str, Any]:
    """
    Search for places/POIs in a city using real-time Google Places API (root-level endpoint).
    """
    # Delegate to the main search function
    return await search_places(query, limit)

@router.post("/api/itinerary/plan-multi-day-simple")
async def plan_multi_day_simple(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple multi-day planning endpoint that accepts frontend's simple request format.
    """
    try:
        city = request.get("city", "Pune")
        days = int(request.get("days", 3))
        start_time = request.get("start_time", "10:00")
        end_time = request.get("end_time", "18:00")
        mode = request.get("mode", "driving")
        pace = request.get("pace", "normal")
        hotel = request.get("hotel", {"lat": 18.5204, "lng": 73.8567})
        
        # Create multiple single-day plans
        results = []
        for day in range(days):
            plan_request = PlanRequest(
                city=city,
                start_time=start_time,
                end_time=end_time,
                mode=mode,
                pace=pace,
                hotel=HotelLocation(lat=hotel["lat"], lng=hotel["lng"]),
                date=f"2024-01-{day+1:02d}"  # Simple date generation
            )
            
            day_plan = await plan_one_day(plan_request)
            
            # Convert to simple format
            day_result = {
                "date": day_plan.date,
                "items": [
                    {
                        "name": item.name,
                        "arrive_at": item.arrive_at,
                        "depart_at": item.depart_at,
                        "duration_min": item.duration_min,
                        "category": item.category
                    }
                    for item in day_plan.items
                ],
                "stats": {
                    "total_travel_min": day_plan.stats.total_travel_min,
                    "total_duration": day_plan.stats.total_duration
                }
            }
            results.append(day_result)
        
        return {
            "days": results,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Simple multi-day planning failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/itinerary/create-complete-itinerary") 
async def create_complete_itinerary_fix(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a complete itinerary from a list of destinations.
    This endpoint handles the double /api/api path issue.
    """
    try:
        # Extract destinations and convert to plan-one-day format
        destinations = request.get("destinations", [])
        title = request.get("title", "Trip")
        start_lat = request.get("start_latitude", 18.5204)
        start_lng = request.get("start_longitude", 73.8567)
        
        if not destinations:
            raise HTTPException(status_code=400, detail="No destinations provided")
        
        # Use first destination to determine city
        city = "Pune"  # Default fallback
        if destinations:
            first_dest = destinations[0]
            dest_name = first_dest.get("name", "")
            if any(pune_place in dest_name.lower() for pune_place in ["pune", "shaniwar", "aga khan"]):
                city = "Pune"
        
        # Convert to plan-one-day request
        plan_request = PlanRequest(
            city=city,
            start_time="09:00",
            end_time="18:00", 
            mode="driving",
            pace="normal",
            hotel=HotelLocation(lat=start_lat, lng=start_lng)
        )
        
        # Call our existing plan-one-day endpoint
        day_plan = await plan_one_day(plan_request)
        
        # Convert response to expected format
        return {
            "itinerary_id": f"itinerary_{int(time.time())}",
            "title": title,
            "optimized_route": [
                {
                    "name": item.name,
                    "arrival_time_formatted": item.arrive_at,
                    "departure_time_formatted": item.depart_at,
                    "category": item.category,
                    "stay_duration_hours": item.duration_min / 60.0,
                    "lat": item.lat,
                    "lng": item.lng
                }
                for item in day_plan.items
            ],
            "stats": day_plan.stats.model_dump(),
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Create complete itinerary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))