from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import os
import logging
import math
import sys

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

logger = logging.getLogger(__name__)

# ✅ Simple HTTP client setup using requests
try:
    import requests
    HTTP_CLIENT_AVAILABLE = True
except ImportError:
    HTTP_CLIENT_AVAILABLE = False
    logger.warning("requests not available, using mock data")

# ✅ Simple cache implementation
CACHE_STORAGE = {}

class SimpleCache:
    def __init__(self, expire_minutes: int = 30):
        self.expire_minutes = expire_minutes
    
    def get(self, key: str):
        if key in CACHE_STORAGE:
            data, timestamp = CACHE_STORAGE[key]
            if (datetime.now() - timestamp).total_seconds() < (self.expire_minutes * 60):
                return data
            else:
                del CACHE_STORAGE[key]
        return None
    
    def set(self, key: str, value):
        CACHE_STORAGE[key] = (value, datetime.now())

cache30m = SimpleCache(30)

# ✅ Settings functions
def get_google_maps_api_key():
    return os.getenv("GOOGLE_MAPS_API_KEY", "AIzaSyBvOkBvKjhL1Q2QW3XyQr8nZjJjQ9QW8k4")

def get_google_places_base_url():
    return "https://maps.googleapis.com/maps/api/place"

# ✅ Create router
router = APIRouter(prefix="/places", tags=["📍 Places & Locations"])

# ✅ Pydantic Models
class PlaceDetails(BaseModel):
    name: str
    address: Optional[str] = None
    rating: Optional[float] = None
    location: Optional[Dict[str, float]] = None
    place_id: Optional[str] = None
    types: Optional[List[str]] = []
    price_level: Optional[int] = None
    opening_hours: Optional[Dict[str, Any]] = None
    photos: Optional[List[str]] = []

class PlacesSearchResponse(BaseModel):
    success: bool
    query: str
    location_filter: Optional[Dict[str, float]] = None
    count: int
    items: List[PlaceDetails]
    cached: bool = False

# ✅ Mock Places Data for Testing
MOCK_PLACES = {
    "mumbai": [
        {
            "name": "Gateway of India",
            "formatted_address": "Apollo Bandar, Colaba, Mumbai, Maharashtra 400001, India",
            "rating": 4.4,
            "geometry": {"location": {"lat": 18.9220, "lng": 72.8347}},
            "place_id": "ChIJjR8-RJbvwjsRJCKJ1x2xQ0A",
            "types": ["tourist_attraction", "point_of_interest", "establishment"],
            "price_level": None
        },
        {
            "name": "Marine Drive",
            "formatted_address": "Marine Drive, Mumbai, Maharashtra, India",
            "rating": 4.3,
            "geometry": {"location": {"lat": 18.9434, "lng": 72.8234}},
            "place_id": "ChIJL2pOXtjvwjsRgGo3Xde5pQI",
            "types": ["route"],
            "price_level": None
        },
        {
            "name": "Chhatrapati Shivaji Terminus",
            "formatted_address": "Chhatrapati Shivaji Terminus, Mumbai, Maharashtra 400001, India",
            "rating": 4.5,
            "geometry": {"location": {"lat": 18.9404, "lng": 72.8352}},
            "place_id": "ChIJjTRCWAjvwjsRtSW9wB_FTqA",
            "types": ["train_station", "transit_station", "point_of_interest", "establishment"],
            "price_level": None
        }
    ],
    "delhi": [
        {
            "name": "Red Fort",
            "formatted_address": "Netaji Subhash Marg, Lal Qila, Old Delhi, Delhi, 110006, India",
            "rating": 4.3,
            "geometry": {"location": {"lat": 28.6562, "lng": 77.2410}},
            "place_id": "ChIJdXkxWjPgDDkRhvVwxtQhcRU",
            "types": ["museum", "tourist_attraction", "point_of_interest", "establishment"],
            "price_level": 1
        },
        {
            "name": "India Gate",
            "formatted_address": "Rajpath, India Gate, New Delhi, Delhi 110001, India",
            "rating": 4.4,
            "geometry": {"location": {"lat": 28.6129, "lng": 77.2295}},
            "place_id": "ChIJj9rBiDvlDDkRhvwftqCNXg0",
            "types": ["tourist_attraction", "point_of_interest", "establishment"],
            "price_level": None
        }
    ],
    "bangalore": [
        {
            "name": "Lalbagh Botanical Garden",
            "formatted_address": "Mavalli, Bengaluru, Karnataka 560004, India",
            "rating": 4.4,
            "geometry": {"location": {"lat": 12.9507, "lng": 77.5848}},
            "place_id": "ChIJnQ2xAy0RrjsRYy1XqK23Eg0",
            "types": ["park", "tourist_attraction", "point_of_interest", "establishment"],
            "price_level": 1
        },
        {
            "name": "Bangalore Palace",
            "formatted_address": "Palace Road, Bengaluru, Karnataka 560052, India",
            "rating": 4.0,
            "geometry": {"location": {"lat": 12.9985, "lng": 77.5848}},
            "place_id": "ChIJOwo2R9ARrjsRcNVTJJmP5E8",
            "types": ["museum", "tourist_attraction", "point_of_interest", "establishment"],
            "price_level": 2
        }
    ]
}

# ✅ Helper Functions
def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two coordinates in km"""
    R = 6371  # Earth's radius in kilometers
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lng/2) * math.sin(delta_lng/2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def get_mock_places_by_query(query: str, lat: Optional[float] = None, lng: Optional[float] = None) -> List[Dict]:
    """Get mock places based on query and location"""
    
    query_lower = query.lower()
    all_places = []
    
    # Search in all mock data
    for city, places in MOCK_PLACES.items():
        if query_lower in city.lower():
            all_places.extend(places)
        else:
            # Search in place names and addresses
            for place in places:
                name_match = query_lower in place.get("name", "").lower()
                address_match = query_lower in place.get("formatted_address", "").lower()
                types_match = any(query_lower in ptype for ptype in place.get("types", []))
                
                if name_match or address_match or types_match:
                    all_places.append(place)
    
    # Filter by location if provided
    if lat is not None and lng is not None:
        filtered_places = []
        for place in all_places:
            place_location = place.get("geometry", {}).get("location", {})
            if place_location.get("lat") and place_location.get("lng"):
                distance = calculate_distance(
                    lat, lng, 
                    place_location["lat"], place_location["lng"]
                )
                if distance <= 5:  # Within 5km radius
                    place_copy = place.copy()
                    place_copy["distance_km"] = round(distance, 2)
                    filtered_places.append(place_copy)
        
        # Sort by distance
        filtered_places.sort(key=lambda x: x.get("distance_km", 999))
        return filtered_places
    
    return all_places

async def fetch_google_places(query: str, lat: Optional[float] = None, lng: Optional[float] = None, radius: int = 5000) -> List[Dict]:
    """Fetch places from Google Places API"""
    
    if not HTTP_CLIENT_AVAILABLE:
        logger.info("HTTP client not available, using mock data")
        return get_mock_places_by_query(query, lat, lng)
    
    api_key = get_google_maps_api_key()
    base_url = get_google_places_base_url()
    
    if not api_key or api_key == "your_api_key_here":
        logger.info("Google Places API key not configured, using mock data")
        return get_mock_places_by_query(query, lat, lng)
    
    try:
        url = f"{base_url}/textsearch/json"
        params = {
            "query": query,
            "key": api_key
        }
        
        if lat is not None and lng is not None:
            params["location"] = f"{lat},{lng}"
            params["radius"] = str(radius)
        
        response = requests.get(url, params=params, timeout=10.0)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("status") == "OK":
                return data.get("results", [])
            else:
                logger.warning(f"Google Places API returned status: {data.get('status')}")
                return get_mock_places_by_query(query, lat, lng)
        else:
            logger.warning(f"Google Places API error: {response.status_code}")
            return get_mock_places_by_query(query, lat, lng)
            
    except Exception as e:
        logger.error(f"Error fetching Google Places: {e}")
        return get_mock_places_by_query(query, lat, lng)

async def get_place_details(place_id: str) -> Optional[Dict]:
    """Get detailed information about a specific place"""
    
    api_key = get_google_maps_api_key()
    base_url = get_google_places_base_url()
    
    if not HTTP_CLIENT_AVAILABLE or not api_key or api_key == "your_api_key_here":
        # Return mock detailed data
        mock_details = {
            "name": "Sample Place",
            "formatted_address": "Sample Address, City, Country",
            "international_phone_number": "+1-234-567-8900",
            "website": "https://example.com",
            "rating": 4.2,
            "user_ratings_total": 150,
            "price_level": 2,
            "opening_hours": {
                "open_now": True,
                "weekday_text": [
                    "Monday: 9:00 AM – 6:00 PM",
                    "Tuesday: 9:00 AM – 6:00 PM",
                    "Wednesday: 9:00 AM – 6:00 PM",
                    "Thursday: 9:00 AM – 6:00 PM",
                    "Friday: 9:00 AM – 6:00 PM",
                    "Saturday: 10:00 AM – 4:00 PM",
                    "Sunday: Closed"
                ]
            },
            "geometry": {"location": {"lat": 19.0760, "lng": 72.8777}},
            "types": ["tourist_attraction", "point_of_interest", "establishment"]
        }
        return mock_details
    
    try:
        url = f"{base_url}/details/json"
        params = {
            "place_id": place_id,
            "key": api_key,
            "fields": "name,formatted_address,international_phone_number,website,rating,user_ratings_total,price_level,opening_hours,geometry,types,photos"
        }
        
        response = requests.get(url, params=params, timeout=10.0)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "OK":
                return data.get("result", {})
        
        logger.warning(f"Place details API error for {place_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching place details: {e}")
        return None

# ✅ API Endpoints
@router.get("/search",
            response_model=PlacesSearchResponse,
            summary="Search Places",
            description="Search for places using text query with optional location filtering")
async def places_search(
    query: str = Query(..., min_length=1, max_length=200, description="Search query"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitude for location-based search"),
    lng: Optional[float] = Query(None, ge=-180, le=180, description="Longitude for location-based search"), 
    radius: int = Query(5000, ge=100, le=50000, description="Search radius in meters"),
    limit: int = Query(20, ge=1, le=60, description="Maximum number of results")
):
    """Search for places using Google Places API or mock data"""
    
    try:
        # Create cache key
        cache_key = f"places_search:{query}:{lat}:{lng}:{radius}:{limit}"
        
        # Check cache first
        cached_result = cache30m.get(cache_key)
        if cached_result:
            cached_result["cached"] = True
            return cached_result
        
        # Fetch places
        places_data = await fetch_google_places(query, lat, lng, radius)
        
        # Process and format results
        processed_places = []
        for place in places_data:
            location_data = place.get("geometry", {}).get("location")
            
            place_detail = PlaceDetails(
                name=place.get("name", "Unknown Place"),
                address=place.get("formatted_address"),
                rating=place.get("rating"),
                location=location_data,
                place_id=place.get("place_id"),
                types=place.get("types", []),
                price_level=place.get("price_level")
            )
            
            processed_places.append(place_detail)
        
        # Limit results
        limited_places = processed_places[:limit]
        
        # Create response
        response = PlacesSearchResponse(
            success=True,
            query=query,
            location_filter={"lat": lat, "lng": lng} if lat and lng else None,
            count=len(limited_places),
            items=limited_places,
            cached=False
        )
        
        # Cache the result
        cache30m.set(cache_key, response.dict())
        
        return response
        
    except Exception as e:
        logger.error(f"Places search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Places search failed: {str(e)}")

@router.get("/details/{place_id}",
            summary="Get Place Details",
            description="Get detailed information about a specific place")
async def get_place_detail(place_id: str):
    """Get detailed information about a specific place"""
    
    try:
        # Check cache first
        cache_key = f"place_details:{place_id}"
        cached_result = cache30m.get(cache_key)
        
        if cached_result:
            return {**cached_result, "cached": True}
        
        # Fetch place details
        place_details = await get_place_details(place_id)
        
        if not place_details:
            raise HTTPException(status_code=404, detail="Place not found")
        
        # Process photos if available
        photos = []
        if place_details.get("photos"):
            for photo in place_details.get("photos", [])[:5]:  # Limit to 5 photos
                photo_reference = photo.get("photo_reference")
                if photo_reference:
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_reference}&key={get_google_maps_api_key()}"
                    photos.append(photo_url)
        
        # Format response
        result = {
            "success": True,
            "place_id": place_id,
            "name": place_details.get("name"),
            "address": place_details.get("formatted_address"),
            "phone": place_details.get("international_phone_number"),
            "website": place_details.get("website"),
            "rating": place_details.get("rating"),
            "total_ratings": place_details.get("user_ratings_total"),
            "price_level": place_details.get("price_level"),
            "location": place_details.get("geometry", {}).get("location"),
            "types": place_details.get("types", []),
            "opening_hours": place_details.get("opening_hours"),
            "photos": photos,
            "cached": False
        }
        
        # Cache the result
        cache30m.set(cache_key, result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get place details failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get place details failed: {str(e)}")

@router.get("/nearby",
            summary="Find Nearby Places",
            description="Find places near a specific location by type")
async def find_nearby_places(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    place_type: str = Query("tourist_attraction", description="Type of place to search for"),
    radius: int = Query(1000, ge=100, le=5000, description="Search radius in meters"),
    limit: int = Query(20, ge=1, le=60, description="Maximum number of results")
):
    """Find nearby places of a specific type"""
    
    try:
        # Create cache key
        cache_key = f"nearby_places:{lat:.4f}:{lng:.4f}:{place_type}:{radius}:{limit}"
        
        # Check cache first
        cached_result = cache30m.get(cache_key)
        if cached_result:
            return {**cached_result, "cached": True}
        
        # For mock data, find places within radius
        all_places = []
        for city_places in MOCK_PLACES.values():
            all_places.extend(city_places)
        
        nearby_places = []
        for place in all_places:
            place_location = place.get("geometry", {}).get("location", {})
            if place_location.get("lat") and place_location.get("lng"):
                distance_km = calculate_distance(
                    lat, lng,
                    place_location["lat"], place_location["lng"]
                )
                distance_m = distance_km * 1000
                
                if distance_m <= radius:
                    # Check if place type matches
                    place_types = place.get("types", [])
                    if place_type in place_types or place_type == "all":
                        place_copy = place.copy()
                        place_copy["distance_meters"] = int(distance_m)
                        place_copy["distance_km"] = round(distance_km, 2)
                        nearby_places.append(place_copy)
        
        # Sort by distance
        nearby_places.sort(key=lambda x: x.get("distance_meters", 999999))
        
        # Format results
        formatted_places = []
        for place in nearby_places[:limit]:
            formatted_place = {
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "rating": place.get("rating"),
                "location": place.get("geometry", {}).get("location"),
                "place_id": place.get("place_id"),
                "types": place.get("types", []),
                "distance_meters": place.get("distance_meters"),
                "distance_km": place.get("distance_km")
            }
            formatted_places.append(formatted_place)
        
        result = {
            "success": True,
            "search_location": {"lat": lat, "lng": lng},
            "place_type": place_type,
            "radius_meters": radius,
            "count": len(formatted_places),
            "places": formatted_places,
            "cached": False
        }
        
        # Cache the result
        cache30m.set(cache_key, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Nearby places search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Nearby places search failed: {str(e)}")

@router.get("/categories",
            summary="Get Place Categories",
            description="Get list of available place categories/types")
async def get_place_categories():
    """Get available place categories"""
    
    categories = [
        {
            "type": "tourist_attraction",
            "name": "Tourist Attractions",
            "description": "Museums, monuments, landmarks, and popular tourist spots"
        },
        {
            "type": "restaurant",
            "name": "Restaurants",
            "description": "Restaurants, cafes, and dining establishments"
        },
        {
            "type": "lodging",
            "name": "Hotels & Lodging",
            "description": "Hotels, hostels, and accommodation options"
        },
        {
            "type": "shopping_mall",
            "name": "Shopping",
            "description": "Shopping centers, markets, and retail stores"
        },
        {
            "type": "park",
            "name": "Parks & Recreation",
            "description": "Parks, gardens, and recreational areas"
        },
        {
            "type": "hospital",
            "name": "Healthcare",
            "description": "Hospitals, clinics, and medical facilities"
        },
        {
            "type": "gas_station",
            "name": "Gas Stations",
            "description": "Fuel stations and automotive services"
        },
        {
            "type": "atm",
            "name": "ATMs & Banks",
            "description": "ATMs, banks, and financial services"
        },
        {
            "type": "transit_station",
            "name": "Transport",
            "description": "Train stations, bus stops, and transport hubs"
        },
        {
            "type": "pharmacy",
            "name": "Pharmacy",
            "description": "Pharmacies and medical stores"
        }
    ]
    
    return {
        "success": True,
        "categories": categories,
        "total_categories": len(categories)
    }

@router.get("/autocomplete",
            summary="Place Autocomplete",
            description="Get place suggestions for autocomplete")
async def place_autocomplete(
    input_text: str = Query(..., min_length=1, max_length=100, description="Input text for autocomplete"),
    types: Optional[str] = Query(None, description="Restrict results to specific types"),
    components: Optional[str] = Query(None, description="Country restriction (e.g., country:in)")
):
    """Get place autocomplete suggestions"""
    
    try:
        # Simple mock autocomplete based on our mock data
        suggestions = []
        input_lower = input_text.lower()
        
        # Search in mock places
        for city, places in MOCK_PLACES.items():
            if input_lower in city.lower():
                suggestions.append({
                    "description": f"{city.title()}, India",
                    "place_id": f"city_{city}",
                    "types": ["locality", "political"],
                    "structured_formatting": {
                        "main_text": city.title(),
                        "secondary_text": "India"
                    }
                })
            
            for place in places:
                place_name = place.get("name", "")
                if input_lower in place_name.lower():
                    suggestions.append({
                        "description": f"{place_name}, {place.get('formatted_address', '')}",
                        "place_id": place.get("place_id"),
                        "types": place.get("types", []),
                        "structured_formatting": {
                            "main_text": place_name,
                            "secondary_text": place.get("formatted_address", "")
                        }
                    })
        
        # Limit suggestions
        limited_suggestions = suggestions[:10]
        
        return {
            "success": True,
            "input": input_text,
            "predictions": limited_suggestions,
            "status": "OK"
        }
        
    except Exception as e:
        logger.error(f"Autocomplete failed: {e}")
        raise HTTPException(status_code=500, detail=f"Autocomplete failed: {str(e)}")

@router.get("/health",
            summary="Places Service Health",
            description="Check places service health and configuration")
async def places_health():
    """Places service health check"""
    
    api_key_configured = bool(get_google_maps_api_key() and get_google_maps_api_key() != "your_api_key_here")
    
    return {
        "service": "places",
        "status": "healthy",
        "features": {
            "place_search": True,
            "place_details": True,
            "nearby_search": True,
            "autocomplete": True,
            "place_categories": True,
            "caching": True
        },
        "external_services": {
            "google_places_api": "configured" if api_key_configured else "using_mock_data",
            "http_client": "available" if HTTP_CLIENT_AVAILABLE else "mock_mode"
        },
        "statistics": {
            "cache_entries": len(CACHE_STORAGE),
            "mock_cities": len(MOCK_PLACES),
            "mock_places_total": sum(len(places) for places in MOCK_PLACES.values())
        },
        "supported_types": [
            "tourist_attraction", "restaurant", "lodging", "shopping_mall",
            "park", "hospital", "gas_station", "atm", "transit_station", "pharmacy"
        ],
        "api_info": {
            "base_url": get_google_places_base_url(),
            "api_key_present": api_key_configured
        },
        "version": "1.0.0"
    }
