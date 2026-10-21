"""
Google Places API service for retrieving real-time POI data.
Provides places search, details, and geocoding functionality.
"""
import asyncio
import logging
import os
from typing import List, Dict, Any, Optional, Tuple
import aiohttp
from pydantic import BaseModel

logger = logging.getLogger(__name__)

PLACES_NEW_BASE_URL = "https://places.googleapis.com/v1"
PLACES_FIELD_MASK = ",".join([
    "places.id", "places.displayName", "places.formattedAddress", "places.location",
    "places.rating", "places.userRatingCount", "places.types", "places.regularOpeningHours",
    "places.websiteUri", "places.nationalPhoneNumber",
])


class PlaceDetails(BaseModel):
    """Place details from Google Places API"""
    place_id: str
    name: str
    formatted_address: str
    lat: float
    lng: float
    rating: float
    user_ratings_total: int
    price_level: Optional[int] = None
    types: List[str]
    opening_hours: Optional[Dict[str, Any]] = None
    photos: List[str] = []
    website: Optional[str] = None
    phone_number: Optional[str] = None


class GooglePlacesService:
    """Service for interacting with Google Places API"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        self.session: Optional[aiohttp.ClientSession] = None  # deprecated; using per-call sessions to avoid loop issues
        
        if not self.api_key or self.api_key == "your_google_places_api_key_here":
            raise ValueError("❌ GOOGLE PLACES API KEY REQUIRED! Please set GOOGLE_PLACES_API_KEY in .env file. No mock data allowed - real-time data only!")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Deprecated: maintained for backward compatibility. Returns a new session each call."""
        # Always return a fresh session bound to the current event loop
        return aiohttp.ClientSession()
    
    async def close(self):
        """No-op with per-call sessions (kept for compatibility)."""
        # Nothing to close because we use per-call sessions with context managers
        self.session = None
    
    async def geocode_city(self, city_name: str) -> Optional[Tuple[float, float]]:
        """
        Get coordinates for a city name using Google Geocoding API
        
        Args:
            city_name: Name of the city to geocode
            
        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        if not self.api_key:
            raise ValueError("Google Places API key required for geocoding. No mock data allowed.")
        
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": city_name,
                "key": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("results"):
                            location = data["results"][0]["geometry"]["location"]
                            return (location["lat"], location["lng"])
                    
                    logger.error(f"Geocoding failed for {city_name}: {response.status}")
                    return None
                
        except Exception as e:
            logger.error(f"Error geocoding {city_name}: {e}")
            return None
    
    
    async def search_places(
        self, 
        query: str, 
        location: Optional[Tuple[float, float]] = None,
        radius: int = 10000,
        limit: int = 20
    ) -> List[PlaceDetails]:
        """
        Search for places using Google Places API
        
        Args:
            query: Search query (e.g., "tourist attractions in Paris")
            location: Optional (lat, lng) tuple to center search
            radius: Search radius in meters
            limit: Maximum number of results
            
        Returns:
            List of PlaceDetails objects
        """
        if not self.api_key:
            raise ValueError("Google Places API key required for places search. No mock data allowed.")
        
        try:
            # First, try text search
            places = await self._text_search(query, location)
            
            # If we have a location, also do a nearby search for more variety
            if location and len(places) < limit:
                nearby_places = await self._nearby_search(location, radius)
                places.extend(nearby_places)
            
            # Remove duplicates and limit results
            seen_ids = set()
            unique_places = []
            for place in places:
                if place.place_id not in seen_ids and len(unique_places) < limit:
                    seen_ids.add(place.place_id)
                    unique_places.append(place)
            
            logger.info(f"Found {len(unique_places)} places for query: {query}")
            return unique_places
            
        except Exception as e:
            logger.error(f"Error searching places for '{query}': {e}")
            raise ValueError(f"Failed to search places using Google Places API: {e}. Real-time Google Places API key required.")
    
    async def _text_search(self, query: str, location: Optional[Tuple[float, float]]) -> List[PlaceDetails]:
        """Places API (New) text search"""
        body: Dict[str, Any] = {"textQuery": query, "maxResultCount": 20}
        if location:
            body["locationBias"] = {"circle": {"center": {"latitude": location[0], "longitude": location[1]}, "radius": 10000.0}}
        return await self._search("places:searchText", body)

    async def _nearby_search(self, location: Tuple[float, float], radius: int) -> List[PlaceDetails]:
        """Places API (New) nearby search"""
        body = {
            "includedTypes": ["tourist_attraction", "museum", "park", "restaurant", "shopping_mall"],
            "maxResultCount": 20,
            "locationRestriction": {"circle": {"center": {"latitude": location[0], "longitude": location[1]}, "radius": float(radius)}},
        }
        return await self._search("places:searchNearby", body)

    async def _search(self, endpoint: str, body: Dict[str, Any]) -> List[PlaceDetails]:
        """POST to Places API (New); raises with Google's message so the caller can show it"""
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": PLACES_FIELD_MASK,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{PLACES_NEW_BASE_URL}/{endpoint}", json=body, headers=headers) as response:
                data = await response.json(content_type=None)
                if response.status != 200:
                    message = data.get("error", {}).get("message", f"HTTP {response.status}")
                    raise ValueError(f"Google Places API error: {message}")
        return [p for p in (self._parse_place_result(r) for r in data.get("places", [])) if p]

    def _parse_place_result(self, result: Dict[str, Any]) -> Optional[PlaceDetails]:
        """Parse a Places API (New) place"""
        try:
            location = result.get("location") or {}
            if location.get("latitude") is None or location.get("longitude") is None:
                return None

            hours = result.get("regularOpeningHours")
            opening_hours = None
            if hours:
                opening_hours = {
                    "open_now": hours.get("openNow"),
                    "periods": hours.get("periods", []),
                    # New API uses narrow no-break spaces before AM/PM; the planner parses plain spaces
                    "weekday_text": [d.replace(" ", " ").replace(" ", " ") for d in hours.get("weekdayDescriptions", [])],
                }

            return PlaceDetails(
                place_id=result.get("id", ""),
                name=(result.get("displayName") or {}).get("text", "Unknown"),
                formatted_address=result.get("formattedAddress", ""),
                lat=float(location["latitude"]),
                lng=float(location["longitude"]),
                rating=float(result.get("rating", 4.0)),
                user_ratings_total=int(result.get("userRatingCount", 0)),
                price_level=None,  # shortcut: New API returns price as an enum string, not 0-4; not used by the planner, upgrade if price filtering is added
                types=result.get("types", []),
                opening_hours=opening_hours,
                photos=[],  # shortcut: photo URLs need the New photo media endpoint; not used by the planner yet
                website=result.get("websiteUri"),
                phone_number=result.get("nationalPhoneNumber"),
            )

        except Exception as e:
            logger.error(f"Error parsing place result: {e}")
            return None


# Global instance
_places_service: Optional[GooglePlacesService] = None


async def get_places_service() -> GooglePlacesService:
    """Get or create the Google Places service instance"""
    global _places_service
    if _places_service is None:
        _places_service = GooglePlacesService()
    return _places_service


async def cleanup_places_service():
    """Cleanup the Google Places service"""
    global _places_service
    if _places_service:
        await _places_service.close()
        _places_service = None