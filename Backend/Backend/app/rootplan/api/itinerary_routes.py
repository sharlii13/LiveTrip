"""
FastAPI routes for the itinerary planning API.
Implements the main endpoint for one-day itinerary planning.
"""
import logging
import time
import traceback
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.rootplan.models.schemas import PlanRequest, DayPlan, ErrorResponse, HotelLocation
from app.rootplan.models.multiday_schemas import MultiDayPlanRequest, MultiDayItinerary, MultiDayPOI, Location, UserPreferences, PlanningConstraints
from app.rootplan.planner import greedy_selector, route_optimizer
from app.rootplan.planner.multiday_planner import plan_multiday_itinerary
from app.rootplan.utils.cache_utils import cleanup_cache


def create_universal_response(status: str, message: str, response_city: str = None, data: dict = None) -> dict:
    """
    Create a consistent JSON response format for all endpoints.
    
    Args:
        status: "success" or "error"
        message: Human-readable message
        response_city: The actual city name processed by backend
        data: Response data (for success) or None (for error)
    
    Returns:
        Consistent JSON response format
    """
    response = {
        "status": status,
        "message": message,
        "responseCity": response_city
    }
    
    if data is not None:
        response["data"] = data
    
    return response


logger = logging.getLogger(__name__)

# Create the router
router = APIRouter(
    prefix="/api/itinerary",
    tags=["itinerary"],
    responses={404: {"description": "Not found"}},
)


@router.post("/plan-one-day", 
            response_model=DayPlan,
            summary="Plan One-Day Itinerary",
            description="Create an optimal one-day travel itinerary using greedy POI selection and OR-Tools route optimization.")
async def plan_one_day(request: PlanRequest) -> DayPlan:
    """
    Plan a one-day itinerary with optimal POI selection and route optimization.
    
    This endpoint combines:
    - Greedy algorithm for intelligent POI selection based on ratings, reviews, weather compatibility, etc.
    - OR-Tools VRPTW solver for optimal visit ordering while respecting time windows
    - Caching for improved performance
    
    Args:
        request: Planning request with city, times, transportation mode, and hotel location
        
    Returns:
        Optimized day plan with scheduled POIs and travel statistics
        
    Raises:
        HTTPException: For various error conditions (validation, no POIs found, etc.)
    """
    try:
        logger.info(f"Planning one-day itinerary for {request.city} from {request.start_time} to {request.end_time}")
        
        # Set default date if not provided
        if not request.date:
            request.date = datetime.now().strftime("%Y-%m-%d")
        
        # Step 1: Select best POIs using greedy algorithm
        logger.info("Step 1: Selecting POIs with greedy algorithm")
        selected_pois = await greedy_selector.select_best_pois(request, max_pois=6)
        
        if not selected_pois:
            logger.warning(f"No feasible POIs found for {request.city}")
            raise HTTPException(
                status_code=404,
                detail=f"No suitable POIs found for {request.city} within the specified time constraints"
            )
        
        logger.info(f"Selected {len(selected_pois)} POIs for optimization")
        
        # Step 2: Optimize route using OR-Tools
        logger.info("Step 2: Optimizing route with OR-Tools")
        hotel_location = {"lat": request.hotel.lat, "lng": request.hotel.lng}
        
        optimized_plan = await route_optimizer.optimize_day(
            selected_pois=selected_pois,
            hotel_location=hotel_location,
            request=request
        )
        
        logger.info(f"Successfully created itinerary with {len(optimized_plan.items)} POIs, "
                   f"total travel time: {optimized_plan.stats.total_travel_min} minutes")
        
        return optimized_plan
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        logger.error(f"Validation error in plan_one_day: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in plan_one_day: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="Internal server error occurred while planning itinerary"
        )


@router.get("/health", 
           summary="Health Check",
           description="Check API health and component status.")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint to verify API status and component health.
    
    Returns:
        Dictionary with health status and component information
    """
    try:
        # Check cache health
        cache_stats = await cleanup_cache()
        
        # Check if OR-Tools is available
        ortools_available = True
        try:
            from ortools.constraint_solver import pywrapcp
        except ImportError:
            ortools_available = False
        
        # Get POI selector status
        selector = greedy_selector.get_selector()
        selector_ready = selector is not None
        
        # Get route optimizer status  
        optimizer = route_optimizer.get_optimizer()
        optimizer_ready = optimizer is not None
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "greedy_selector": {
                    "status": "ready" if selector_ready else "unavailable",
                    "weights": selector.weights.model_dump() if selector_ready else None
                },
                "route_optimizer": {
                    "status": "ready" if optimizer_ready else "unavailable",
                    "ortools_available": ortools_available
                },
                "cache": {
                    "status": "ready",
                    "stats": cache_stats
                }
            },
            "version": "1.0.0"
        }
        
        # Determine overall status
        if not (selector_ready and optimizer_ready and ortools_available):
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/cache/stats",
           summary="Cache Statistics", 
           description="Get current cache statistics and performance metrics.")
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get detailed cache statistics.
    
    Returns:
        Dictionary with cache statistics and metrics
    """
    try:
        stats = await cleanup_cache()
        
        return {
            "cache_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cache statistics")


@router.delete("/cache",
              summary="Clear Cache",
              description="Clear all cached data (POIs, distance matrices, etc.).")
async def clear_cache() -> Dict[str, str]:
    """
    Clear all cached data.
    
    Returns:
        Confirmation message
    """
    try:
        from app.rootplan.utils.cache_utils import get_cache
        
        cache = get_cache()
        await cache.clear()
        
        logger.info("Cache cleared successfully")
        
        return {
            "message": "Cache cleared successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@router.post("/debug/score-pois",
            summary="Debug: Score POIs",
            description="Debug endpoint to see POI scoring without full optimization (development only).")
async def debug_score_pois(request: PlanRequest) -> Dict[str, Any]:
    """
    Debug endpoint to examine POI scoring without running full optimization.
    Useful for development and testing the scoring algorithm.
    
    Args:
        request: Planning request
        
    Returns:
        Dictionary with scored POIs and selection details
    """
    try:
        logger.info(f"Debug: Scoring POIs for {request.city}")
        
        # Get the selector and run POI selection
        selected_pois = await greedy_selector.select_best_pois(request, max_pois=10)
        
        # Prepare debug response
        scored_poi_details = []
        for scored_poi in selected_pois:
            poi = scored_poi.poi
            scored_poi_details.append({
                "name": poi.name,
                "category": poi.category,
                "score": round(scored_poi.score, 3),
                "rating": poi.rating,
                "reviews": poi.reviews,
                "open_time": poi.open_time,
                "close_time": poi.close_time,
                "travel_time_min": scored_poi.travel_time_min,
                "feasible": scored_poi.feasible,
                "coordinates": {"lat": poi.lat, "lng": poi.lng}
            })
        
        # Get category distribution
        selector = greedy_selector.get_selector()
        category_distribution = selector.get_category_distribution(selected_pois)
        
        return {
            "request_summary": {
                "city": request.city,
                "time_window": f"{request.start_time} - {request.end_time}",
                "mode": request.mode,
                "hotel": {"lat": request.hotel.lat, "lng": request.hotel.lng}
            },
            "selection_results": {
                "total_selected": len(selected_pois),
                "scored_pois": scored_poi_details,
                "category_distribution": category_distribution
            },
            "scoring_weights": selector.weights.model_dump(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Debug scoring failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Debug scoring failed: {str(e)}")




@router.post("/plan-multi-day",
            summary="Plan Multi-Day Itinerary",
            description="Create an optimal multi-day travel itinerary. Accepts both simple and complex request formats.")
async def plan_multi_day(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Plan a multi-day itinerary. Handles both simple and complex request formats.
    
    Simple format (from frontend):
    {
        "city": "Mumbai",
        "days": 3,
        "start_time": "10:00",
        "end_time": "18:00",
        "mode": "driving",
        "pace": "normal",
        "hotel": {"lat": 19.0760, "lng": 72.8777}
    }
    
    Complex format (advanced planning):
    {
        "start_location": {"lat": 19.0760, "lng": 72.8777},
        "days": 3,
        "available_hours_per_day": 8.0,
        "poi_list": [...],
        "user_preferences": {...},
        "constraints": {...}
    }
    """
    try:
        # Check if this is a simple request format (from frontend)
        if "city" in request and "hotel" in request:
            logger.info(f"Simple multi-day request for {request.get('city')} - {request.get('days', 3)} days")
            
            # Convert simple request to enhanced multi-day planning
            city = (request.get("city") or "").strip()
            days = int(request.get("days", 3))
            start_time = request.get("start_time", "10:00")
            end_time = request.get("end_time", "18:00")
            mode = request.get("mode", "driving")
            pace = request.get("pace", "normal")
            hotel = request.get("hotel", {"lat": 18.5204, "lng": 73.8567})
            response_city = city or None
            
            # For multi-day trips, use our enhanced algorithm
            if days > 1:
                logger.info(f"Using ENHANCED multi-day planning for {city} - {days} days")
                
                # Get all available POIs for the city using Google Places
                from app.rootplan.services.google_places import GooglePlacesService
                places_service = GooglePlacesService()
                google_places = []
                if city:
                    try:
                        google_places = await places_service.search_places(f"{city} tourist attractions", limit=50)
                    except Exception as e:
                        logger.error(f"Google Places search failed for {city}: {e}", exc_info=True)
                
                logger.info(f"Found {len(google_places)} places from Google Places API")
                
                if not google_places:
                    # Universal safe error response
                    return create_universal_response(
                        status="error",
                        message=f"No POIs found for '{city or 'unknown city'}'",
                        response_city=None
                    )
                
                # Convert Google Places to MultiDayPOI format
                from app.rootplan.models.multiday_schemas import MultiDayPOI, MultiDayPlanRequest, Location, UserPreferences, PlanningConstraints
                from app.rootplan.models.schemas import get_category_duration
                
                poi_list = []
                for i, place in enumerate(google_places, 1):
                    # Map Google Place types to our categories
                    category = "historic"
                    if any(t in place.types for t in ["restaurant", "meal_takeaway", "food"]):
                        category = "food"
                    elif any(t in place.types for t in ["park", "zoo", "aquarium"]):
                        category = "nature"
                    elif any(t in place.types for t in ["museum"]):
                        category = "museum"
                    elif any(t in place.types for t in ["hindu_temple", "place_of_worship"]):
                        category = "religious"
                    elif any(t in place.types for t in ["shopping_mall", "store"]):
                        category = "shopping"
                    elif any(t in place.types for t in ["tourist_attraction"]):
                        category = "historic"
                    
                    # Get category duration and opening hours
                    duration_hr = get_category_duration(category) / 60.0  # Convert minutes to hours
                    
                    # Parse opening hours from Google Places
                    open_time = "09:00"
                    close_time = "18:00"
                    if place.opening_hours and place.opening_hours.get("weekday_text"):
                        try:
                            # Simple parsing of first opening hours entry
                            first_day = place.opening_hours["weekday_text"][0]
                            if "–" in first_day:
                                time_part = first_day.split(": ")[1] if ": " in first_day else first_day
                                if "–" in time_part:
                                    open_str, close_str = time_part.split("–")
                                    # Convert 12-hour to 24-hour format (simplified)
                                    if "AM" in open_str or "PM" in open_str:
                                        open_time = open_str.strip().replace(" AM", "").replace(" PM", "")
                                        close_time = close_str.strip().replace(" AM", "").replace(" PM", "")
                                        if "PM" in close_str and not close_time.startswith("12"):
                                            hour = int(close_time.split(":")[0]) + 12
                                            close_time = f"{hour:02d}:{close_time.split(':')[1]}"
                        except:
                            pass  # Use defaults
                    
                    poi_list.append(MultiDayPOI(
                        id=i,
                        name=place.name,
                        lat=place.lat,
                        lng=place.lng,
                        duration=duration_hr,
                        open=open_time,
                        close=close_time,
                        category=category,
                        score=place.rating or 4.0
                    ))
                
                # Create enhanced multi-day request
                multiday_request = MultiDayPlanRequest(
                    start_location=Location(lat=hotel["lat"], lng=hotel["lng"]),
                    days=days,
                    available_hours_per_day=8.0,  # 8 hours per day
                    poi_list=poi_list,
                    user_preferences=UserPreferences(),  # Default preferences
                    constraints=PlanningConstraints(
                        max_daily_distance_km=50,
                        avoid_repetition=True,
                        max_pois_per_day=6,
                        min_pois_per_day=2
                    ),
                    start_time=start_time,
                    transportation_mode=mode
                )
                
                # Use our enhanced multi-day planner!
                from app.rootplan.planner.multiday_planner import plan_multiday_itinerary
                enhanced_itinerary = await plan_multiday_itinerary(multiday_request)
                
                logger.info(f"Enhanced planning complete: {enhanced_itinerary.summary.total_pois_covered} POIs, "
                           f"{enhanced_itinerary.summary.avg_daily_diversity} diversity")
                
                # Convert enhanced response to simple format for frontend compatibility
                results = []
                for day_itinerary in enhanced_itinerary.itinerary:
                    day_result = {
                        "date": f"2024-01-{day_itinerary.day:02d}",
                        "day": day_itinerary.day,
                        "total_distance_km": day_itinerary.total_distance_km,
                        "total_duration_hr": day_itinerary.total_duration_hr,
                        "utilization_percent": day_itinerary.utilization_percent,
                        "category_mix": day_itinerary.category_mix,
                        "diversity_score": day_itinerary.diversity_score,
                        "items": [
                            {
                                "name": poi.poi,
                                "arrive_at": poi.start,
                                "depart_at": poi.end,
                                "duration_min": int(poi.duration_hr * 60),
                                "category": poi.category,
                                "coordinates": {
                                    "lat": poi.coordinates.lat,
                                    "lng": poi.coordinates.lng
                                }
                            }
                            for poi in day_itinerary.schedule
                        ],
                        "stats": {
                            "total_travel_min": int((day_itinerary.total_duration_hr - day_itinerary.visit_duration_hr) * 60),
                            "total_duration": day_itinerary.total_duration_hr
                        }
                    }
                    results.append(day_result)
            else:
                # Single day - use normal planning
                plan_request = PlanRequest(
                    city=city,
                    start_time=start_time,
                    end_time=end_time,
                    mode=mode,
                    pace=pace,
                    hotel=HotelLocation(lat=hotel["lat"], lng=hotel["lng"]),
                    date="2024-01-01"
                )
                
                try:
                    day_plan = await plan_one_day(plan_request)
                except HTTPException as http_err:
                    # Return standardized error with responseCity always present
                    detail = str(http_err.detail)
                    if http_err.status_code == 404:
                        return create_universal_response(
                            status="error",
                            message=f"No POIs found for '{city or 'unknown city'}'",
                            response_city=None
                        )
                    traceback.print_exc()
                    return create_universal_response(
                        status="error",
                        message=detail,
                        response_city=response_city
                    )
                except Exception as e:
                    logger.error(f"Unexpected error in single-day path: {e}", exc_info=True)
                    traceback.print_exc()
                    return create_universal_response(
                        status="error",
                        message="Internal server error occurred while planning multi-day itinerary",
                        response_city=response_city
                    )
                
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
            
            return create_universal_response(
                status="success",
                message="Multi-day itinerary planned successfully",
                response_city=response_city,
                data={
                    "days": results,
                    "last_updated": datetime.now().isoformat()
                }
            )
        
        else:
            # Complex request format - use enhanced multi-day planning
            logger.info(f"Complex multi-day request: {request.get('days', 0)} days, {len(request.get('poi_list', []))} POIs")
            
            # Convert dict to MultiDayPlanRequest
            multi_day_request = MultiDayPlanRequest(**request)
            
            # Plan the multi-day itinerary with enhanced algorithm
            try:
                itinerary = await plan_multiday_itinerary(multi_day_request)
            except HTTPException as http_err:
                traceback.print_exc()
                return create_universal_response(
                    status="error",
                    message=str(http_err.detail),
                    response_city=None
                )
            except Exception as e:
                logger.error(f"Unexpected error in complex multi-day: {e}", exc_info=True)
                traceback.print_exc()
                return create_universal_response(
                    status="error",
                    message="Internal server error occurred while planning multi-day itinerary",
                    response_city=None
                )
            
            logger.info(f"Enhanced multi-day planning successful: {itinerary.summary.total_pois_covered} POIs assigned, "
                       f"{itinerary.summary.avg_daily_utilization} utilization, {itinerary.summary.avg_daily_diversity} diversity")
            
            # Transform to the required response format
            enhanced_response = {
                "itinerary": [
                    {
                        "day": day_itinerary.day,
                        "total_distance_km": day_itinerary.total_distance_km,
                        "total_duration_hr": day_itinerary.total_duration_hr,
                        "utilization_percent": day_itinerary.utilization_percent,
                        "category_mix": day_itinerary.category_mix,
                        "diversity_score": day_itinerary.diversity_score,
                        "schedule": [
                            {
                                "poi": poi.poi,
                                "category": poi.category,
                                "start": poi.start,
                                "end": poi.end,
                                "duration_hr": poi.duration_hr,
                                "coordinates": {
                                    "lat": poi.coordinates.lat,
                                    "lng": poi.coordinates.lng
                                }
                            }
                            for poi in day_itinerary.schedule
                        ]
                    }
                    for day_itinerary in itinerary.itinerary
                ],
                "summary": {
                    "total_days": itinerary.summary.total_days,
                    "total_pois_covered": itinerary.summary.total_pois_covered,
                    "avg_daily_diversity": itinerary.summary.avg_daily_diversity,
                    "avg_daily_utilization": itinerary.summary.avg_daily_utilization,
                    "categories_distribution": itinerary.summary.categories_distribution,
                    "unassigned_pois": itinerary.summary.unassigned_pois
                },
                "metadata": itinerary.metadata
            }
            
            return create_universal_response(
                status="success",
                message="Multi-day itinerary planned successfully",
                response_city=None,
                data=enhanced_response
            )
        
    except ValueError as e:
        logger.error(f"Validation error in plan_multi_day: {e}")
        traceback.print_exc()
        return create_universal_response(
            status="error",
            message=str(e),
            response_city=None
        )
    except Exception as e:
        logger.error(f"Unexpected error in plan_multi_day: {e}", exc_info=True)
        traceback.print_exc()
        return create_universal_response(
            status="error",
            message="Internal server error occurred while planning multi-day itinerary",
            response_city=None
        )


async def create_custom_day_plan(plan_request: PlanRequest, selected_pois: list):
    """
    Create a custom day plan with pre-selected POIs
    """
    try:
        # Convert POIs to ScoredPOI format
        from app.rootplan.models.schemas import ScoredPOI
        
        scored_pois = []
        for poi in selected_pois:
            scored_poi = ScoredPOI(
                name=poi.name,
                lat=poi.location.get('lat', 0),
                lng=poi.location.get('lng', 0),
                category=poi.category,
                rating=poi.rating,
                formatted_address=poi.formatted_address,
                score=1.0  # Default score
            )
            scored_pois.append(scored_poi)
        
        # Use route optimizer to create the day plan
        optimizer = route_optimizer.RouteOptimizer()
        day_plan = await optimizer.optimize_day(
            scored_pois, 
            {"lat": plan_request.hotel.lat, "lng": plan_request.hotel.lng},
            plan_request
        )
        
        return day_plan
        
    except Exception as e:
        logger.error(f"Error creating custom day plan: {e}")
        # Fallback to regular planning
        return await plan_one_day(plan_request)


# Places search endpoint moved to places_routes.py to avoid conflicts


@router.post("/create-complete-itinerary",
            summary="Create Complete Itinerary", 
            description="Create a complete itinerary from city name or destinations list using Google Places API.")
async def create_complete_itinerary(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a complete itinerary from a city name or list of destinations.
    Uses Google Places API to find POIs and create optimal itinerary.
    
    Returns:
        Success: {"message": "Itinerary created successfully", "data": {...}}
        Error: {"status": "error", "message": "reason here", "code": 500}
    """
    try:
        logger.info(f"Creating complete itinerary with request: {request}")
        
        # Extract request parameters
        destinations = request.get("destinations", [])
        title = request.get("title", "Trip")
        start_lat = request.get("start_latitude")
        start_lng = request.get("start_longitude")
        start_time = request.get("start_time", "09:00:00")
        
        logger.info(f"Request parameters - title: '{title}', destinations: {len(destinations)}, coords: ({start_lat}, {start_lng})")
        
        # Determine city name from title or coordinates
        city = None
        
        # Try to extract city from title
        if title and title != "Trip":
            city_from_title = title.replace(" Trip", "").strip()
            if city_from_title:
                city = city_from_title
                logger.info(f"Extracted city from title: {city}")
        
        # If still no city, try to infer from coordinates using geocoding service (universal, no hardcodes)
        if not city and start_lat and start_lng:
            try:
                from app.rootplan.services.google_places import get_places_service
                places_service = await get_places_service()
                # Attempt reverse geocoding if available; if not, fall back to nearest city name via search
                try:
                    # Some implementations may expose reverse geocoding; if not, this will raise
                    city_guess = await places_service.reverse_geocode_city(float(start_lat), float(start_lng))
                except Exception:
                    # Fallback: use a nearby search term to extract locality
                    nearby = await places_service.search_places("locality", location={"lat": float(start_lat), "lng": float(start_lng)}, limit=1)
                    city_guess = nearby[0].name if nearby else None
                if city_guess:
                    city = city_guess
            except Exception as e:
                logger.warning(f"City inference from coordinates failed: {e}")
                traceback.print_exc()
                # leave city as None
        
        # If still no city determined, use a neutral placeholder for responseCity and proceed to POI check
        response_city = city if city else None
        
        logger.info(f"Final city determination: {city}")
            
        # Use provided coordinates or, if missing, attempt to geocode the city generically
        if (start_lat is None or start_lng is None) and city:
            try:
                from app.rootplan.services.google_places import get_places_service
                places_service = await get_places_service()
                coords = await places_service.geocode_city(city)
                start_lat = coords["lat"] if isinstance(coords, dict) else coords[0]
                start_lng = coords["lng"] if isinstance(coords, dict) else coords[1]
            except Exception as e:
                logger.warning(f"Failed to geocode city '{city}': {e}")
                traceback.print_exc()
                # If we cannot determine coordinates, we cannot plan; we will return no POIs found below
        
        logger.info(f"Creating itinerary for {city} at coordinates ({start_lat}, {start_lng})")
        
        # Convert to plan-one-day request
        plan_request = PlanRequest(
            city=city or "",
            start_time=start_time.split(":")[0] + ":" + start_time.split(":")[1] if ":" in start_time else "09:00",
            end_time="18:00", 
            mode="driving",
            pace="normal",
            hotel=HotelLocation(lat=float(start_lat) if start_lat is not None else 0.0, lng=float(start_lng) if start_lng is not None else 0.0)
        )
        
        # Call our existing plan-one-day endpoint with enhanced error handling
        try:
            day_plan = await plan_one_day(plan_request)
        except HTTPException as http_err:
            # Re-raise HTTP exceptions from plan_one_day with proper formatting
            if http_err.status_code == 404:
                # No POIs found for the city
                logger.warning(f"No POIs found for city {city}")
                traceback.print_exc()
                return create_universal_response(
                    status="error",
                    message=f"No POIs found for '{city or 'unknown city'}'",
                    response_city=None
                )
            else:
                # Other HTTP errors from plan_one_day
                logger.error(f"HTTP error in plan_one_day: {http_err.detail}")
                traceback.print_exc()
                return create_universal_response(
                    status="error",
                    message=str(http_err.detail),
                    response_city=response_city
                )
        except Exception as plan_err:
            # Handle OR-Tools or other optimization errors
            logger.error(f"Error in plan_one_day optimization: {plan_err}")
            traceback.print_exc()
            return create_universal_response(
                status="error",
                message=f"Route optimization failed: {str(plan_err)}",
                response_city=response_city
            )
        
        # Convert response to expected format
        itinerary_data = {
            "itinerary_id": f"itinerary_{int(time.time())}",
            "title": f"{city} Trip" if title == "Trip" else title,
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
        
        return create_universal_response(
            status="success",
            message="Itinerary created successfully",
            response_city=response_city,
            data=itinerary_data
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is (they already have proper formatting)
        traceback.print_exc()
        return create_universal_response(
            status="error",
            message="Request failed",
            response_city=None
        )
    except ValueError as e:
        # Handle validation errors
        logger.error(f"Validation error in create_complete_itinerary: {e}")
        traceback.print_exc()
        return create_universal_response(
            status="error",
            message=f"Invalid request parameters: {str(e)}",
            response_city=None
        )
    except Exception as e:
        # Handle any other unexpected errors
        logger.error(f"Unexpected error in create_complete_itinerary: {e}")
        traceback.print_exc()
        return create_universal_response(
            status="error",
            message=f"Internal server error: {str(e)}",
            response_city=None
        )


@router.get("/multi-day/sample",
           summary="Get Sample Multi-Day Request",
           description="Get a sample multi-day planning request for testing purposes.")
async def get_multiday_sample() -> Dict[str, Any]:
    """
    Get a sample multi-day planning request for testing.
    
    Returns:
        Sample multi-day request JSON
    """
    sample_request = {
        "start_location": {"lat": 18.5204, "lng": 73.8567},
        "days": 3,
        "available_hours_per_day": 8,
        "poi_list": [
            {
                "id": 1,
                "name": "Aga Khan Palace",
                "lat": 18.5521,
                "lng": 73.8891,
                "duration": 1.5,
                "open": "09:00",
                "close": "17:30",
                "category": "historical",
                "score": 8.7
            },
            {
                "id": 2,
                "name": "Shaniwar Wada",
                "lat": 18.5196,
                "lng": 73.8553,
                "duration": 1.0,
                "open": "08:00",
                "close": "18:30",
                "category": "fort",
                "score": 9.1
            },
            {
                "id": 3,
                "name": "Dagadusheth Temple",
                "lat": 18.5158,
                "lng": 73.8567,
                "duration": 0.75,
                "open": "06:00",
                "close": "22:00",
                "category": "religious",
                "score": 9.3
            },
            {
                "id": 4,
                "name": "Pune University",
                "lat": 18.5089,
                "lng": 73.8067,
                "duration": 1.75,
                "open": "08:00",
                "close": "17:00",
                "category": "culture",
                "score": 7.8
            },
            {
                "id": 5,
                "name": "Osho Ashram",
                "lat": 18.5292,
                "lng": 73.8674,
                "duration": 2.0,
                "open": "06:00",
                "close": "21:00",
                "category": "culture",
                "score": 8.2
            },
            {
                "id": 6,
                "name": "Sinhagad Fort",
                "lat": 18.3668,
                "lng": 73.7555,
                "duration": 2.5,
                "open": "06:00",
                "close": "18:00",
                "category": "fort",
                "score": 8.9
            },
            {
                "id": 7,
                "name": "Empress Garden",
                "lat": 18.5314,
                "lng": 73.8446,
                "duration": 1.5,
                "open": "06:00",
                "close": "20:00",
                "category": "nature",
                "score": 7.5
            },
            {
                "id": 8,
                "name": "Phoenix Mall",
                "lat": 18.5626,
                "lng": 73.9143,
                "duration": 2.0,
                "open": "10:00",
                "close": "22:00",
                "category": "shopping",
                "score": 6.8
            }
        ],
        "user_preferences": {
            "nature": 0.8,
            "history": 0.9,
            "shopping": 0.2,
            "religious": 0.7,
            "culture": 0.8,
            "fort": 0.9
        },
        "constraints": {
            "max_daily_distance_km": 50,
            "avoid_repetition": True,
            "max_pois_per_day": 4,
            "min_pois_per_day": 2
        }
    }
    
    return {
        "sample_request": sample_request,
        "description": "Sample 3-day itinerary request for Pune with 8 POIs",
        "usage": "POST this JSON to /api/itinerary/plan-multi-day"
    }


# Exception handlers are now in main.py since APIRouter doesn't support exception_handler decorator


@router.post("/plan-multi-day-by-city",
            response_model=MultiDayItinerary,
            summary="Plan Multi-Day Itinerary by City",
            description="Fetch real-time POIs for a city using Google Places and generate a multi-day itinerary.")
async def plan_multi_day_by_city(request: Dict[str, Any]) -> MultiDayItinerary:
    """
    Plan a multi-day itinerary by city name using real-time Google Places data.

    Expected body:
      {
        "city": "Mumbai",
        "days": 3,
        "start_location": {"lat": 19.0760, "lng": 72.8777},
        "available_hours_per_day": 8,
        "start_time": "09:00",                # optional, default 09:00
        "transportation_mode": "driving",      # optional, driving|walking|transit|bicycling
        "user_preferences": { ... },            # optional per existing schema
        "constraints": { ... }                  # optional per existing schema
      }
    """
    import math
    from fastapi import HTTPException

    try:
        city = (request.get("city") or "").strip()
        days = int(request.get("days") or 0)
        start_loc = request.get("start_location") or {}
        available_hours = float(request.get("available_hours_per_day") or 0)
        start_time = request.get("start_time") or "09:00"
        transport = request.get("transportation_mode") or "driving"

        if not city:
            raise HTTPException(status_code=400, detail="'city' is required")
        if days < 1:
            raise HTTPException(status_code=400, detail="'days' must be >= 1")
        if not (isinstance(start_loc, dict) and "lat" in start_loc and "lng" in start_loc):
            raise HTTPException(status_code=400, detail="'start_location' with lat,lng is required")
        if available_hours <= 0:
            raise HTTPException(status_code=400, detail="'available_hours_per_day' must be > 0")

        # Fetch real-time places for the city
        from app.rootplan.services.google_places import get_places_service
        places_service = await get_places_service()
        city_coords = await places_service.geocode_city(city)

        # Aggregate queries for richer POI coverage
        queries = [
            f"tourist attractions in {city}",
            f"museums in {city}",
            f"parks in {city}",
            f"restaurants in {city}",
            f"shopping in {city}",
            f"temples in {city}",
            f"historical sites in {city}"
        ]

        all_places = []
        seen_ids = set()
        for q in queries:
            try:
                results = await places_service.search_places(query=q, location=city_coords, limit=15)
                for p in results:
                    if p.place_id not in seen_ids:
                        seen_ids.add(p.place_id)
                        all_places.append(p)
            except Exception as e:
                logger.warning(f"Places query failed '{q}': {e}")

        if not all_places:
            raise HTTPException(status_code=404, detail=f"No POIs found for {city} from Google Places")

        # Helpers: type->category and opening hours parsing
        def map_types_to_category(types: list[str]) -> str:
            type_mapping = {
                "tourist_attraction": "historic",
                "museum": "museum",
                "amusement_park": "entertainment",
                "zoo": "nature",
                "aquarium": "nature",
                "park": "nature",
                "natural_feature": "nature",
                "place_of_worship": "temple",
                "hindu_temple": "temple",
                "church": "temple",
                "mosque": "temple",
                "synagogue": "temple",
                "buddhist_temple": "temple",
                "shopping_mall": "shopping",
                "store": "shopping",
                "clothing_store": "shopping",
                "book_store": "shopping",
                "restaurant": "food",
                "food": "food",
                "meal_takeaway": "food",
                "cafe": "food",
                "bakery": "food",
                "night_club": "entertainment",
                "bar": "entertainment",
                "movie_theater": "entertainment",
                "casino": "entertainment",
                "art_gallery": "cultural",
                "library": "cultural",
                "university": "cultural",
                "school": "cultural",
            }
            for t in types or []:
                if t in type_mapping:
                    return type_mapping[t]
            return "historic"

        def parse_12h_time(s: str) -> str:
            try:
                s = s.strip()
                # expected like '9:00 AM' or '10:30 PM'
                parts = s.split()
                if len(parts) != 2:
                    return s
                tm, ampm = parts
                hh_mm = tm.split(":")
                hh = int(hh_mm[0])
                mm = int(hh_mm[1]) if len(hh_mm) > 1 else 0
                ampm = ampm.upper()
                if ampm == "AM":
                    hh = 0 if hh == 12 else hh
                else:  # PM
                    hh = 12 if hh == 12 else hh + 12
                return f"{hh:02d}:{mm:02d}"
            except Exception:
                return s

        def extract_open_close(weekday_text: list[str]) -> tuple[str, str]:
            # Default
            open_time, close_time = "08:00", "18:00"
            if not weekday_text:
                return open_time, close_time
            line = weekday_text[0]
            # Try to split on ': ' then on dash variants
            try:
                time_part = line.split(": ")[-1] if ": " in line else line
                if "–" in time_part:
                    a, b = time_part.split("–", 1)
                elif "-" in time_part:
                    a, b = time_part.split("-", 1)
                else:
                    return open_time, close_time
                a = a.strip(); b = b.strip()
                if ("AM" in a or "PM" in a) and ("AM" in b or "PM" in b):
                    open_time = parse_12h_time(a)
                    close_time = parse_12h_time(b)
            except Exception:
                pass
            return open_time, close_time

        from app.rootplan.models.schemas import get_category_duration

        # Convert places -> MultiDayPOI list
        md_pois: list[MultiDayPOI] = []
        next_id = 1
        for p in all_places:
            category = map_types_to_category(p.types)
            # derive duration in hours from category default minutes
            dur_min = get_category_duration(category)
            duration_hr = max(0.5, round(dur_min / 60.0, 2))

            open_time, close_time = "08:00", "18:00"
            if p.opening_hours and isinstance(p.opening_hours.get("weekday_text"), list):
                open_time, close_time = extract_open_close(p.opening_hours["weekday_text"])

            # base score 0..10 using rating and reviews
            rating = p.rating or 4.0
            reviews = p.user_ratings_total or 0
            base_score = (rating / 5.0) * 7.0 + min(3.0, math.log10(1 + reviews))
            base_score = max(0.0, min(10.0, round(base_score, 2)))

            try:
                md_pois.append(MultiDayPOI(
                    id=next_id,
                    name=p.name,
                    lat=p.lat,
                    lng=p.lng,
                    duration=duration_hr,
                    open=open_time,
                    close=close_time,
                    category=category,
                    score=base_score
                ))
                next_id += 1
            except Exception as e:
                logger.warning(f"Skipping POI due to validation: {p.name} ({e})")

        if not md_pois:
            raise HTTPException(status_code=404, detail=f"No usable POIs produced for {city}")

        # Build MultiDayPlanRequest
        md_request = MultiDayPlanRequest(
            start_location=Location(lat=float(start_loc["lat"]), lng=float(start_loc["lng"])),
            days=days,
            available_hours_per_day=available_hours,
            poi_list=md_pois,
            user_preferences=UserPreferences(**request.get("user_preferences", {})) if isinstance(request.get("user_preferences"), dict) else UserPreferences(),
            constraints=PlanningConstraints(**request.get("constraints", {})) if isinstance(request.get("constraints"), dict) else PlanningConstraints(),
            start_time=start_time,
            transportation_mode=transport
        )

        # Delegate to existing planner
        itinerary = await plan_multiday_itinerary(md_request)
        return itinerary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"plan-multi-day-by-city failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to plan multi-day itinerary for {request.get('city', '')}: {str(e)}")
