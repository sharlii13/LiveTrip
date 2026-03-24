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
        self.base_url = "https://maps.googleapis.com/maps/api/place"
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
        """Perform Google Places text search"""
        url = f"{self.base_url}/textsearch/json"
        
        params = {
            "query": query,
            "key": self.api_key
        }
        
        if location:
            params["location"] = f"{location[0]},{location[1]}"
            params["radius"] = "10000"
        
        places = []
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for result in data.get("results", []):
                        place = self._parse_place_result(result)
                        if place:
                            places.append(place)
        
        return places
    
    async def _nearby_search(self, location: Tuple[float, float], radius: int) -> List[PlaceDetails]:
        """Perform Google Places nearby search"""
        url = f"{self.base_url}/nearbysearch/json"
        
        params = {
            "location": f"{location[0]},{location[1]}",
            "radius": str(radius),
            "type": "tourist_attraction|museum|park|restaurant|shopping_mall",
            "key": self.api_key
        }
        
        places = []
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for result in data.get("results", []):
                        place = self._parse_place_result(result)
                        if place:
                            places.append(place)
        
        return places
    
    def _parse_place_result(self, result: Dict[str, Any]) -> Optional[PlaceDetails]:
        """Parse a place result from Google Places API"""
        try:
            geometry = result.get("geometry", {})
            location = geometry.get("location", {})
            
            if not location.get("lat") or not location.get("lng"):
                return None
            
            # Get opening hours
            opening_hours = None
            if result.get("opening_hours"):
                opening_hours = {
                    "open_now": result["opening_hours"].get("open_now"),
                    "periods": result["opening_hours"].get("periods", []),
                    "weekday_text": result["opening_hours"].get("weekday_text", [])
                }
            
            # Get photos
            photos = []
            if result.get("photos"):
                for photo in result["photos"][:3]:  # Limit to 3 photos
                    if photo.get("photo_reference"):
                        photo_url = f"{self.base_url}/photo?maxwidth=400&photoreference={photo['photo_reference']}&key={self.api_key}"
                        photos.append(photo_url)
            
            return PlaceDetails(
                place_id=result.get("place_id", ""),
                name=result.get("name", "Unknown"),
                formatted_address=result.get("formatted_address", ""),
                lat=float(location["lat"]),
                lng=float(location["lng"]),
                rating=float(result.get("rating", 4.0)),
                user_ratings_total=int(result.get("user_ratings_total", 0)),
                price_level=result.get("price_level"),
                types=result.get("types", []),
                opening_hours=opening_hours,
                photos=photos,
                website=result.get("website"),
                phone_number=result.get("formatted_phone_number")
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