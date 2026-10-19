from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from datetime import datetime, date, timedelta
from enum import Enum
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

# ✅ Simple HTTP client setup using requests instead of httpx
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
def get_eventbrite_api_key():
    return os.getenv("EVENTBRITE_API_KEY", "")

def get_eventbrite_base_url():
    return "https://www.eventbriteapi.com/v3"

# ✅ Create router
router = APIRouter(prefix="/events", tags=["🎉 Events & Activities"])

# ✅ Enums
class EventCategory(str, Enum):
    MUSIC = "music"
    FOOD_DRINK = "food-and-drink"
    ARTS_CULTURE = "arts-and-culture"
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    SPORTS_FITNESS = "sports-and-fitness"
    EDUCATION = "education"
    COMMUNITY = "community"
    NIGHTLIFE = "nightlife"
    TRAVEL_OUTDOOR = "travel-and-outdoor"

class EventType(str, Enum):
    CONFERENCE = "conference"
    WORKSHOP = "workshop"
    CONCERT = "concert"
    FESTIVAL = "festival"
    EXHIBITION = "exhibition"
    MEETUP = "meetup"
    PARTY = "party"
    TOUR = "tour"

# ✅ Enhanced Response Models
class EventVenue(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity: Optional[int] = None
    venue_type: Optional[str] = None

class EventOrganizer(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None

class EventPricing(BaseModel):
    is_free: bool = False
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    currency: str = "USD"
    price_display: Optional[str] = None

class EventDetails(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    venue: Optional[EventVenue] = None
    organizer: Optional[EventOrganizer] = None
    category: Optional[str] = None
    event_type: Optional[str] = None
    pricing: Optional[EventPricing] = None
    tags: Optional[List[str]] = []
    distance_km: Optional[float] = None
    popularity_score: Optional[float] = None

class EventsResponse(BaseModel):
    success: bool
    count: int
    events: List[EventDetails]
    location: Optional[Dict[str, float]] = None
    search_radius_km: Optional[int] = None
    filters_applied: Optional[Dict[str, Any]] = None
    cached: bool = False

# ✅ Enhanced Mock Events Data with Indian Context
MOCK_EVENTS = [
    {
        "id": "mumbai_food_fest_2025",
        "name": "Mumbai Street Food Festival 2025",
        "description": "Experience the authentic flavors of Mumbai's famous street food. From vada pav to pav bhaji, taste the best of local cuisine with over 50 food stalls and live cooking demonstrations.",
        "start_time": "2025-02-15T16:00:00",
        "end_time": "2025-02-15T23:00:00",
        "url": "https://mumbaistreetfood.com",
        "image_url": "https://example.com/food-festival.jpg",
        "venue": {
            "name": "Bandra Kurla Complex (BKC) Ground",
            "address": "Bandra Kurla Complex, Bandra East, Mumbai, Maharashtra 400051",
            "city": "Mumbai",
            "latitude": 19.0650,
            "longitude": 72.8680,
            "capacity": 5000,
            "venue_type": "outdoor"
        },
        "organizer": {
            "name": "Mumbai Food Events",
            "description": "Organizing food festivals across Mumbai",
            "website": "https://mumbaifoodeevents.com"
        },
        "category": "Food & Drink",
        "event_type": "festival",
        "pricing": {
            "is_free": False,
            "min_price": 500,
            "max_price": 2000,
            "currency": "INR",
            "price_display": "₹500-2000"
        },
        "tags": ["food", "street food", "mumbai", "festival", "culture"],
        "popularity_score": 9.2
    },
    {
        "id": "tech_mumbai_2025",
        "name": "TechMumbai Conference 2025",
        "description": "Leading technology conference featuring AI, blockchain, and startup innovations. Network with tech leaders and discover the latest industry trends.",
        "start_time": "2025-02-20T09:00:00",
        "end_time": "2025-02-20T18:00:00",
        "url": "https://techmumbai.in",
        "image_url": "https://example.com/tech-conf.jpg",
        "venue": {
            "name": "World Trade Centre",
            "address": "Cuffe Parade, Mumbai, Maharashtra 400005",
            "city": "Mumbai",
            "latitude": 18.9267,
            "longitude": 72.8233,
            "capacity": 1500,
            "venue_type": "conference_center"
        },
        "organizer": {
            "name": "Tech Mumbai Community",
            "description": "Building Mumbai's tech ecosystem",
            "website": "https://techmumbai.community"
        },
        "category": "Technology",
        "event_type": "conference",
        "pricing": {
            "is_free": False,
            "min_price": 1500,
            "max_price": 3500,
            "currency": "INR",
            "price_display": "₹1500-3500"
        },
        "tags": ["technology", "AI", "blockchain", "startups", "networking"],
        "popularity_score": 8.8
    },
    {
        "id": "weekend_art_market",
        "name": "Bandra Art Market Weekend",
        "description": "Discover local artists, handmade crafts, and unique artworks. Support local creators and find one-of-a-kind pieces at this vibrant weekend market.",
        "start_time": "2025-02-22T10:00:00",
        "end_time": "2025-02-22T20:00:00",
        "url": "https://bandraartmarket.com",
        "image_url": "https://example.com/art-market.jpg",
        "venue": {
            "name": "Linking Road Amphitheatre",
            "address": "Linking Road, Bandra West, Mumbai, Maharashtra 400050",
            "city": "Mumbai",
            "latitude": 19.0544,
            "longitude": 72.8286,
            "capacity": 2000,
            "venue_type": "outdoor"
        },
        "organizer": {
            "name": "Mumbai Artists Collective",
            "description": "Supporting local artists and craftspeople",
            "website": "https://mumbaiartists.org"
        },
        "category": "Arts & Culture",
        "event_type": "exhibition",
        "pricing": {
            "is_free": True,
            "min_price": 0,
            "max_price": 0,
            "currency": "INR",
            "price_display": "Free Entry"
        },
        "tags": ["art", "crafts", "local artists", "free", "weekend"],
        "popularity_score": 7.5
    },
    {
        "id": "indie_music_concert",
        "name": "Mumbai Indie Music Night",
        "description": "Experience the best of Mumbai's indie music scene with performances by upcoming bands and established artists. A night of soulful music and great vibes.",
        "start_time": "2025-02-25T19:00:00",
        "end_time": "2025-02-25T23:30:00",
        "url": "https://mumbaimusic.live",
        "image_url": "https://example.com/concert.jpg",
        "venue": {
            "name": "NSCI Stadium",
            "address": "Worli, Mumbai, Maharashtra 400018",
            "city": "Mumbai",
            "latitude": 19.0176,
            "longitude": 72.8177,
            "capacity": 3000,
            "venue_type": "stadium"
        },
        "organizer": {
            "name": "Mumbai Music Society",
            "description": "Promoting indie and local music talent",
            "website": "https://mumbaimusicsociety.com"
        },
        "category": "Music",
        "event_type": "concert",
        "pricing": {
            "is_free": False,
            "min_price": 800,
            "max_price": 3500,
            "currency": "INR",
            "price_display": "₹800-3500"
        },
        "tags": ["indie music", "live music", "bands", "concert", "nightlife"],
        "popularity_score": 8.1
    },
    {
        "id": "yoga_workshop_juhu",
        "name": "Sunrise Yoga Workshop at Juhu Beach",
        "description": "Start your day with a peaceful yoga session on Juhu Beach. Suitable for all levels, includes meditation and breathing exercises with ocean views.",
        "start_time": "2025-02-28T06:30:00",
        "end_time": "2025-02-28T08:00:00",
        "url": "https://juhuyoga.com",
        "image_url": "https://example.com/yoga.jpg",
        "venue": {
            "name": "Juhu Beach",
            "address": "Juhu Beach, Juhu, Mumbai, Maharashtra 400049",
            "city": "Mumbai",
            "latitude": 19.1075,
            "longitude": 72.8263,
            "capacity": 50,
            "venue_type": "beach"
        },
        "organizer": {
            "name": "Mumbai Wellness Community",
            "description": "Promoting health and wellness in Mumbai",
            "website": "https://mumbaiwellness.org"
        },
        "category": "Sports & Fitness",
        "event_type": "workshop",
        "pricing": {
            "is_free": False,
            "min_price": 300,
            "max_price": 500,
            "currency": "INR",
            "price_display": "₹300-500"
        },
        "tags": ["yoga", "wellness", "beach", "sunrise", "meditation"],
        "popularity_score": 7.8
    },
    {
        "id": "startup_networking",
        "name": "Mumbai Startup Networking Meetup",
        "description": "Connect with fellow entrepreneurs, investors, and startup enthusiasts. Share ideas, find co-founders, and explore collaboration opportunities.",
        "start_time": "2025-03-05T18:30:00",
        "end_time": "2025-03-05T21:00:00",
        "url": "https://mumbaistartups.net",
        "image_url": "https://example.com/networking.jpg",
        "venue": {
            "name": "WeWork BKC",
            "address": "G Block, Bandra Kurla Complex, Mumbai, Maharashtra 400051",
            "city": "Mumbai",
            "latitude": 19.0632,
            "longitude": 72.8697,
            "capacity": 200,
            "venue_type": "coworking_space"
        },
        "organizer": {
            "name": "Mumbai Entrepreneurs Network",
            "description": "Building Mumbai's startup ecosystem",
            "website": "https://mumbaienterpreurs.com"
        },
        "category": "Business",
        "event_type": "meetup",
        "pricing": {
            "is_free": True,
            "min_price": 0,
            "max_price": 0,
            "currency": "INR",
            "price_display": "Free"
        },
        "tags": ["startups", "networking", "entrepreneurs", "business", "free"],
        "popularity_score": 8.3
    }
]

# ✅ Helper Functions
def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between coordinates in km using Haversine formula"""
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

def get_event_icon(category: str) -> str:
    """Get emoji icon for event category"""
    icons = {
        "music": "🎵",
        "food & drink": "🍕",
        "arts & culture": "🎨",
        "technology": "💻",
        "business": "💼",
        "sports & fitness": "🏃",
        "education": "📚",
        "community": "👥",
        "nightlife": "🌙",
        "travel & outdoor": "🌲"
    }
    return icons.get(category.lower(), "🎉")

async def fetch_eventbrite_events(lat: float, lng: float, radius_km: int, 
                                category: Optional[str] = None) -> List[Dict]:
    """Fetch events from Eventbrite API using requests instead of httpx"""
    
    if not HTTP_CLIENT_AVAILABLE:
        logger.info("HTTP client not available, using mock data")
        return filter_mock_events_by_location(lat, lng, radius_km, category)
    
    api_key = get_eventbrite_api_key()
    base_url = get_eventbrite_base_url()
    
    if not api_key or api_key == "your_api_key_here":
        logger.info("Eventbrite API key not configured, using mock data")
        return filter_mock_events_by_location(lat, lng, radius_km, category)
    
    try:
        url = f"{base_url}/events/search/"
        params = {
            "location.latitude": lat,
            "location.longitude": lng,
            "location.within": f"{radius_km}km",
            "expand": "venue,organizer,ticket_availability",
            "sort_by": "date",
            "page_size": 20
        }
        
        if category:
            # Map category to Eventbrite category IDs (you'd need to implement this mapping)
            params["categories"] = category
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10.0)
        
        if response.status_code == 200:
            data = response.json()
            events = []
            
            for event in data.get("events", [])[:15]:  # Limit to 15 events
                try:
                    venue_data = event.get("venue", {}) or {}
                    organizer_data = event.get("organizer", {}) or {}
                    
                    # Extract pricing information
                    is_free = event.get("is_free", False)
                    ticket_availability = event.get("ticket_availability", {})
                    
                    event_details = {
                        "id": str(event.get("id", "")),
                        "name": event.get("name", {}).get("text", "Untitled Event"),
                        "description": (event.get("description", {}).get("text", "")[:300] + "...") if event.get("description", {}).get("text", "") else None,
                        "start_time": event.get("start", {}).get("local"),
                        "end_time": event.get("end", {}).get("local"),
                        "url": event.get("url"),
                        "image_url": event.get("logo", {}).get("url") if event.get("logo") else None,
                        "venue": {
                            "name": venue_data.get("name"),
                            "address": venue_data.get("address", {}).get("localized_address_display") if venue_data.get("address") else None,
                            "city": venue_data.get("address", {}).get("city") if venue_data.get("address") else None,
                            "latitude": float(venue_data.get("latitude", 0)) if venue_data.get("latitude") else None,
                            "longitude": float(venue_data.get("longitude", 0)) if venue_data.get("longitude") else None,
                            "capacity": venue_data.get("capacity"),
                            "venue_type": venue_data.get("resource_uri", "").split("/")[-1] if venue_data.get("resource_uri") else None
                        },
                        "organizer": {
                            "name": organizer_data.get("name"),
                            "description": organizer_data.get("description", {}).get("text") if organizer_data.get("description") else None,
                            "website": organizer_data.get("website")
                        },
                        "category": event.get("category", {}).get("name") if event.get("category") else "General",
                        "event_type": "event",
                        "pricing": {
                            "is_free": is_free,
                            "price_display": "Free" if is_free else "Check Event Page",
                            "currency": "USD"
                        },
                        "tags": [],
                        "popularity_score": 7.0  # Default score
                    }
                    events.append(event_details)
                    
                except Exception as e:
                    logger.warning(f"Error processing event: {e}")
                    continue
            
            return events
        else:
            logger.warning(f"Eventbrite API error: {response.status_code}")
            return filter_mock_events_by_location(lat, lng, radius_km, category)
            
    except Exception as e:
        logger.error(f"Error fetching Eventbrite events: {e}")
        return filter_mock_events_by_location(lat, lng, radius_km, category)

def filter_mock_events_by_location(lat: float, lng: float, radius_km: int, 
                                 category: Optional[str] = None) -> List[Dict]:
    """Filter mock events by location, radius, and category"""
    
    filtered_events = []
    for event in MOCK_EVENTS:
        venue = event.get("venue", {})
        if venue.get("latitude") and venue.get("longitude"):
            distance = calculate_distance(lat, lng, venue["latitude"], venue["longitude"])
            if distance <= radius_km:
                # Apply category filter if specified
                if category and event.get("category", "").lower() != category.lower():
                    continue
                    
                event_copy = event.copy()
                event_copy["distance_km"] = round(distance, 1)
                filtered_events.append(event_copy)
    
    # Sort by distance, then by popularity score
    filtered_events.sort(key=lambda x: (x.get("distance_km", 0), -x.get("popularity_score", 0)))
    return filtered_events

def convert_to_event_details(event_data: Dict) -> EventDetails:
    """Convert event data dictionary to EventDetails model"""
    
    venue_data = event_data.get("venue", {})
    venue = EventVenue(
        name=venue_data.get("name"),
        address=venue_data.get("address"),
        city=venue_data.get("city"),
        latitude=venue_data.get("latitude"),
        longitude=venue_data.get("longitude"),
        capacity=venue_data.get("capacity"),
        venue_type=venue_data.get("venue_type")
    ) if venue_data else None
    
    organizer_data = event_data.get("organizer", {})
    organizer = EventOrganizer(
        name=organizer_data.get("name"),
        description=organizer_data.get("description"),
        website=organizer_data.get("website")
    ) if organizer_data else None
    
    pricing_data = event_data.get("pricing", {})
    pricing = EventPricing(
        is_free=pricing_data.get("is_free", False),
        min_price=pricing_data.get("min_price"),
        max_price=pricing_data.get("max_price"),
        currency=pricing_data.get("currency", "USD"),
        price_display=pricing_data.get("price_display")
    ) if pricing_data else None
    
    return EventDetails(
        id=event_data["id"],
        name=event_data["name"],
        description=event_data.get("description"),
        start_time=event_data.get("start_time"),
        end_time=event_data.get("end_time"),
        url=event_data.get("url"),
        image_url=event_data.get("image_url"),
        venue=venue,
        organizer=organizer,
        category=event_data.get("category"),
        event_type=event_data.get("event_type"),
        pricing=pricing,
        tags=event_data.get("tags", []),
        distance_km=event_data.get("distance_km"),
        popularity_score=event_data.get("popularity_score")
    )

# ✅ Enhanced API Endpoints
@router.get("/nearby", 
            response_model=EventsResponse,
            summary="Get Nearby Events",
            description="Find events and activities near a specific location with advanced filtering")
async def events_nearby(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"), 
    radius_km: int = Query(10, ge=1, le=50, description="Search radius in kilometers"),
    category: Optional[str] = Query(None, description="Event category filter"),
    date: Optional[str] = Query(None, description="Date filter (YYYY-MM-DD)"),
    is_free: Optional[bool] = Query(None, description="Filter for free events only"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of events to return")
):
    """Get events near the specified location with comprehensive filtering"""
    
    try:
        # Create cache key
        cache_key = f"events_nearby:{lat:.3f},{lng:.3f}:{radius_km}:{category or 'all'}:{date or 'any'}:{is_free}:{limit}"
        
        # Check cache
        cached_result = cache30m.get(cache_key)
        if cached_result:
            cached_result["cached"] = True
            return cached_result
        
        # Fetch events
        events_data = await fetch_eventbrite_events(lat, lng, radius_km, category)
        
        # Apply additional filters
        filtered_events = events_data
        
        # Filter by date if specified
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
                date_filtered = []
                for event in filtered_events:
                    start_time = event.get("start_time")
                    if start_time:
                        try:
                            event_date = datetime.fromisoformat(start_time.replace('Z', '+00:00')).date()
                            if event_date == target_date:
                                date_filtered.append(event)
                        except Exception:
                            continue
                filtered_events = date_filtered
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        # Filter by free events if specified
        if is_free is not None:
            filtered_events = [
                event for event in filtered_events 
                if event.get("pricing", {}).get("is_free", False) == is_free
            ]
        
        # Convert to response format
        events = []
        for event_data in filtered_events[:limit]:
            try:
                event = convert_to_event_details(event_data)
                events.append(event)
            except Exception as e:
                logger.warning(f"Error converting event data: {e}")
                continue
        
        # Build filters applied summary
        filters_applied = {}
        if category:
            filters_applied["category"] = category
        if date:
            filters_applied["date"] = date
        if is_free is not None:
            filters_applied["is_free"] = is_free
        
        # Create response
        result = EventsResponse(
            success=True,
            count=len(events),
            events=events,
            location={"latitude": lat, "longitude": lng},
            search_radius_km=radius_km,
            filters_applied=filters_applied if filters_applied else None,
            cached=False
        )
        
        # Cache the result
        cache30m.set(cache_key, result.dict())
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting nearby events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve events: {str(e)}")

@router.get("/search",
            summary="Search Events",
            description="Search events by keywords with location and category filters")
async def search_events(
    q: str = Query(..., min_length=2, max_length=100, description="Search query"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitude for location-based results"),
    lng: Optional[float] = Query(None, ge=-180, le=180, description="Longitude for location-based results"),
    radius_km: int = Query(25, ge=1, le=100, description="Search radius in kilometers"),
    category: Optional[str] = Query(None, description="Event category filter"),
    limit: int = Query(15, ge=1, le=30, description="Maximum number of results")
):
    """Search events by keywords with advanced filtering"""
    
    try:
        query_lower = q.lower()
        matching_events = []
        
        # Search in all mock events
        for event in MOCK_EVENTS:
            # Check if query matches various fields
            matches = []
            matches.append(query_lower in event.get("name", "").lower())
            matches.append(query_lower in event.get("description", "").lower())
            matches.append(query_lower in event.get("category", "").lower())
            matches.append(any(query_lower in tag.lower() for tag in event.get("tags", [])))
            
            if any(matches):
                # Apply location filter if coordinates provided
                if lat is not None and lng is not None:
                    venue = event.get("venue", {})
                    if venue.get("latitude") and venue.get("longitude"):
                        distance = calculate_distance(lat, lng, venue["latitude"], venue["longitude"])
                        if distance <= radius_km:
                            event_copy = event.copy()
                            event_copy["distance_km"] = round(distance, 1)
                            matching_events.append(event_copy)
                else:
                    matching_events.append(event.copy())
        
        # Apply category filter
        if category:
            matching_events = [
                event for event in matching_events 
                if event.get("category", "").lower() == category.lower()
            ]
        
        # Sort by relevance (popularity score and distance)
        if lat is not None and lng is not None:
            matching_events.sort(key=lambda x: (x.get("distance_km", 0), -x.get("popularity_score", 0)))
        else:
            matching_events.sort(key=lambda x: -x.get("popularity_score", 0))
        
        # Convert to EventDetails
        events = []
        for event_data in matching_events[:limit]:
            try:
                event = convert_to_event_details(event_data)
                events.append(event)
            except Exception as e:
                logger.warning(f"Error converting search result: {e}")
                continue
        
        return {
            "success": True,
            "query": q,
            "count": len(events),
            "events": events,
            "search_location": {"latitude": lat, "longitude": lng} if lat and lng else None,
            "filters_applied": {
                "category": category,
                "radius_km": radius_km if lat and lng else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error searching events: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/categories",
            summary="Get Event Categories",
            description="Get list of available event categories with descriptions and icons")
async def get_event_categories():
    """Get available event categories with enhanced information"""
    
    categories = [
        {
            "value": EventCategory.MUSIC,
            "name": "Music",
            "description": "Concerts, festivals, live performances, and music events",
            "icon": "🎵",
            "example_events": ["Concerts", "Music Festivals", "DJ Nights"]
        },
        {
            "value": EventCategory.FOOD_DRINK,
            "name": "Food & Drink",
            "description": "Food festivals, wine tastings, culinary workshops, and dining events",
            "icon": "🍕",
            "example_events": ["Food Festivals", "Wine Tastings", "Cooking Classes"]
        },
        {
            "value": EventCategory.ARTS_CULTURE,
            "name": "Arts & Culture",
            "description": "Art exhibitions, theater, cultural festivals, and creative workshops",
            "icon": "🎨",
            "example_events": ["Art Exhibitions", "Theater Shows", "Cultural Programs"]
        },
        {
            "value": EventCategory.TECHNOLOGY,
            "name": "Technology",
            "description": "Tech conferences, hackathons, product launches, and workshops",
            "icon": "💻",
            "example_events": ["Tech Conferences", "Hackathons", "Product Demos"]
        },
        {
            "value": EventCategory.BUSINESS,
            "name": "Business",
            "description": "Networking events, seminars, startup meetups, and conferences",
            "icon": "💼",
            "example_events": ["Networking Events", "Business Seminars", "Startup Meetups"]
        },
        {
            "value": EventCategory.SPORTS_FITNESS,
            "name": "Sports & Fitness",
            "description": "Sports events, fitness classes, outdoor activities, and wellness workshops",
            "icon": "🏃",
            "example_events": ["Marathons", "Yoga Classes", "Sports Tournaments"]
        },
        {
            "value": EventCategory.EDUCATION,
            "name": "Education",
            "description": "Workshops, seminars, courses, and learning opportunities",
            "icon": "📚",
            "example_events": ["Workshops", "Training Sessions", "Educational Seminars"]
        },
        {
            "value": EventCategory.COMMUNITY,
            "name": "Community",
            "description": "Community gatherings, social events, volunteer activities, and meetups",
            "icon": "👥",
            "example_events": ["Community Meetups", "Social Gatherings", "Volunteer Events"]
        }
    ]
    
    return {
        "success": True,
        "categories": categories,
        "total_categories": len(categories),
        "note": "Categories help filter events by type and interest"
    }

@router.get("/popular",
            summary="Get Popular Events", 
            description="Get popular and trending events with sorting options")
async def get_popular_events(
    limit: int = Query(10, ge=1, le=30, description="Number of events to return"),
    timeframe: str = Query("upcoming", pattern="^(upcoming|this_week|this_month)$", 
                          description="Time filter: upcoming, this_week, this_month"),
    lat: Optional[float] = Query(None, description="Latitude for location-based results"),
    lng: Optional[float] = Query(None, description="Longitude for location-based results")
):
    """Get popular events with time and location filtering"""
    
    try:
        events_data = MOCK_EVENTS.copy()
        
        # Apply time filter
        now = datetime.now()
        if timeframe == "this_week":
            week_end = now + timedelta(days=7)
            events_data = [
                event for event in events_data
                if event.get("start_time") and 
                now <= datetime.fromisoformat(event["start_time"]) <= week_end
            ]
        elif timeframe == "this_month":
            month_end = now + timedelta(days=30)
            events_data = [
                event for event in events_data
                if event.get("start_time") and 
                now <= datetime.fromisoformat(event["start_time"]) <= month_end
            ]
        
        # Add distance if location provided
        if lat is not None and lng is not None:
            for event in events_data:
                venue = event.get("venue", {})
                if venue.get("latitude") and venue.get("longitude"):
                    distance = calculate_distance(lat, lng, venue["latitude"], venue["longitude"])
                    event["distance_km"] = round(distance, 1)
        
        # Sort by popularity score (and distance if location provided)
        if lat is not None and lng is not None:
            events_data.sort(key=lambda x: (x.get("distance_km", 999), -x.get("popularity_score", 0)))
        else:
            events_data.sort(key=lambda x: -x.get("popularity_score", 0))
        
        # Convert to EventDetails
        events = []
        for event_data in events_data[:limit]:
            try:
                event = convert_to_event_details(event_data)
                events.append(event)
            except Exception as e:
                logger.warning(f"Error converting popular event: {e}")
                continue
        
        return {
            "success": True,
            "events": events,
            "count": len(events),
            "timeframe": timeframe,
            "location_filter_applied": lat is not None and lng is not None,
            "note": f"Popular events for {timeframe} timeframe"
        }
        
    except Exception as e:
        logger.error(f"Error getting popular events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get popular events: {str(e)}")

@router.get("/trending",
            summary="Get Trending Events",
            description="Get currently trending events based on popularity and engagement")
async def get_trending_events(
    limit: int = Query(8, ge=1, le=20, description="Number of trending events"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """Get trending events with high engagement"""
    
    try:
        # Filter by category if specified
        events_data = MOCK_EVENTS
        if category:
            events_data = [
                event for event in events_data 
                if event.get("category", "").lower() == category.lower()
            ]
        
        # Sort by popularity score and add trending indicators
        trending_events = sorted(events_data, key=lambda x: -x.get("popularity_score", 0))
        
        results = []
        for i, event_data in enumerate(trending_events[:limit]):
            try:
                event = convert_to_event_details(event_data)
                # Add trending rank
                event_dict = event.dict()
                event_dict["trending_rank"] = i + 1
                event_dict["trending_indicator"] = "🔥" if i < 3 else "📈"
                results.append(event_dict)
            except Exception as e:
                logger.warning(f"Error processing trending event: {e}")
                continue
        
        return {
            "success": True,
            "trending_events": results,
            "count": len(results),
            "category_filter": category,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting trending events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get trending events: {str(e)}")

@router.get("/recommendations",
            summary="Get Personalized Event Recommendations",
            description="Get event recommendations based on location and preferences")
async def get_event_recommendations(
    lat: float = Query(..., ge=-90, le=90, description="User latitude"),
    lng: float = Query(..., ge=-180, le=180, description="User longitude"),
    interests: Optional[str] = Query(None, description="Comma-separated interests (e.g., 'music,food,technology')"),
    budget: Optional[str] = Query(None, pattern="^(free|low|medium|high)$", description="Budget preference"),
    limit: int = Query(6, ge=1, le=15, description="Number of recommendations")
):
    """Get personalized event recommendations"""
    
    try:
        # Parse interests
        user_interests = []
        if interests:
            user_interests = [interest.strip().lower() for interest in interests.split(',')]
        
        # Score events based on user preferences
        scored_events = []
        for event in MOCK_EVENTS:
            score = 0
            
            # Distance scoring (closer is better)
            venue = event.get("venue", {})
            if venue.get("latitude") and venue.get("longitude"):
                distance = calculate_distance(lat, lng, venue["latitude"], venue["longitude"])
                event_copy = event.copy()
                event_copy["distance_km"] = round(distance, 1)
                
                # Distance score (max 30 points)
                if distance <= 5:
                    score += 30
                elif distance <= 15:
                    score += 20
                elif distance <= 30:
                    score += 10
                
                # Interest matching (max 40 points)
                if user_interests:
                    event_tags = [tag.lower() for tag in event.get("tags", [])]
                    event_category = event.get("category", "").lower()
                    
                    for interest in user_interests:
                        if (interest in event_category or 
                            any(interest in tag for tag in event_tags)):
                            score += 10
                
                # Budget matching (max 20 points)
                if budget:
                    pricing = event.get("pricing", {})
                    is_free = pricing.get("is_free", False)
                    
                    if budget == "free" and is_free:
                        score += 20
                    elif budget == "low" and (is_free or pricing.get("max_price", 0) <= 1000):
                        score += 15
                    elif budget == "medium" and pricing.get("max_price", 0) <= 3000:
                        score += 10
                    elif budget == "high":
                        score += 5
                
                # Popularity bonus (max 10 points)
                popularity = event.get("popularity_score", 0)
                score += int(popularity)
                
                event_copy["recommendation_score"] = score
                scored_events.append(event_copy)
        
        # Sort by recommendation score
        scored_events.sort(key=lambda x: -x.get("recommendation_score", 0))
        
        # Convert to EventDetails
        recommendations = []
        for event_data in scored_events[:limit]:
            try:
                event = convert_to_event_details(event_data)
                event_dict = event.dict()
                event_dict["recommendation_score"] = event_data.get("recommendation_score", 0)
                event_dict["recommendation_reason"] = _get_recommendation_reason(event_data, user_interests, budget)
                recommendations.append(event_dict)
            except Exception as e:
                logger.warning(f"Error processing recommendation: {e}")
                continue
        
        return {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations),
            "user_location": {"latitude": lat, "longitude": lng},
            "user_preferences": {
                "interests": user_interests,
                "budget": budget
            },
            "personalization_note": "Recommendations based on location, interests, and budget preferences"
        }
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")

def _get_recommendation_reason(event_data: Dict, interests: List[str], budget: Optional[str]) -> str:
    """Generate explanation for why event was recommended"""
    reasons = []
    
    # Distance reason
    distance = event_data.get("distance_km", 0)
    if distance <= 5:
        reasons.append("Very close to you")
    elif distance <= 15:
        reasons.append("Nearby location")
    
    # Interest matching
    if interests:
        event_tags = [tag.lower() for tag in event_data.get("tags", [])]
        matching_interests = [interest for interest in interests 
                            if any(interest in tag for tag in event_tags)]
        if matching_interests:
            reasons.append(f"Matches your interest in {', '.join(matching_interests)}")
    
    # Budget matching
    if budget:
        pricing = event_data.get("pricing", {})
        if budget == "free" and pricing.get("is_free", False):
            reasons.append("Free event")
        elif budget in ["low", "medium"] and pricing.get("max_price", 0) <= 2000:
            reasons.append("Within your budget")
    
    # Popularity
    if event_data.get("popularity_score", 0) >= 8:
        reasons.append("Highly rated event")
    
    return "; ".join(reasons) if reasons else "Great event in your area"

@router.get("/health",
            summary="Events Service Health",
            description="Check events service health and configuration")
async def events_health():
    """Events service health check"""
    
    api_key_configured = bool(get_eventbrite_api_key() and get_eventbrite_api_key() != "your_api_key_here")
    
    return {
        "service": "events",
        "status": "healthy",
        "features": {
            "nearby_events": True,
            "event_search": True,
            "categories": True,
            "popular_events": True,
            "trending_events": True,
            "recommendations": True,
            "caching": True,
            "location_filtering": True,
            "budget_filtering": True
        },
        "external_services": {
            "eventbrite_api": "configured" if api_key_configured else "using_mock_data",
            "http_client": "available (requests)" if HTTP_CLIENT_AVAILABLE else "mock_mode"
        },
        "statistics": {
            "cache_entries": len(CACHE_STORAGE),
            "mock_events_count": len(MOCK_EVENTS),
            "supported_categories": len(EventCategory),
            "average_event_popularity": round(sum(event.get("popularity_score", 0) for event in MOCK_EVENTS) / len(MOCK_EVENTS), 2)
        },
        "api_info": {
            "base_url": get_eventbrite_base_url(),
            "api_key_present": api_key_configured,
            "http_client": "requests (instead of httpx)"
        },
        "version": "2.0.0"
    }
