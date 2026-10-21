"""
Google Distance Matrix API service for calculating travel times and distances.
Supports multiple transportation modes and provides real-time traffic data.
"""
import asyncio
import logging
import os
import json
from contextvars import ContextVar
from typing import List, Dict, Any, Optional, Tuple
import aiohttp
from enum import Enum

logger = logging.getLogger(__name__)

# Per-request state; the endpoint sets it, fallbacks mark it when travel times are estimated
distance_source: ContextVar[dict] = ContextVar("distance_source")


def mark_distance_estimate() -> None:
    state = distance_source.get(None)
    if state is not None:
        state["estimated"] = True


ROUTES_MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
ROUTES_TRAVEL_MODE = {"driving": "DRIVE", "walking": "WALK", "bicycling": "BICYCLE", "transit": "TRANSIT"}


class TravelMode(str, Enum):
    """Travel modes supported by Google Distance Matrix API"""
    DRIVING = "driving"
    WALKING = "walking"
    BICYCLING = "bicycling"
    TRANSIT = "transit"


class TrafficModel(str, Enum):
    """Traffic models for driving mode"""
    BEST_GUESS = "best_guess"
    PESSIMISTIC = "pessimistic"
    OPTIMISTIC = "optimistic"


class DistanceMatrixResult:
    """Result from Distance Matrix API call"""
    
    def __init__(self, origins: List[str], destinations: List[str], results: Dict[str, Any]):
        self.origins = origins
        self.destinations = destinations
        self.results = results
        self.rows = results.get("rows", [])
        self.status = results.get("status", "UNKNOWN")
    
    def get_duration(self, origin_idx: int, dest_idx: int, use_traffic: bool = True) -> Optional[int]:
        """
        Get travel duration in seconds between origin and destination
        
        Args:
            origin_idx: Index of origin in the origins list
            dest_idx: Index of destination in the destinations list
            use_traffic: Whether to use traffic-aware duration (if available)
            
        Returns:
            Duration in seconds, or None if not available
        """
        try:
            if origin_idx >= len(self.rows) or dest_idx >= len(self.rows[origin_idx].get("elements", [])):
                return None
            
            element = self.rows[origin_idx]["elements"][dest_idx]
            if element.get("status") != "OK":
                return None
            
            # Try traffic-aware duration first (only available for driving mode)
            if use_traffic and "duration_in_traffic" in element:
                return element["duration_in_traffic"]["value"]
            
            # Fallback to regular duration
            if "duration" in element:
                return element["duration"]["value"]
            
            return None
            
        except (KeyError, IndexError, TypeError):
            return None
    
    def get_distance(self, origin_idx: int, dest_idx: int) -> Optional[int]:
        """
        Get travel distance in meters between origin and destination
        
        Args:
            origin_idx: Index of origin in the origins list
            dest_idx: Index of destination in the destinations list
            
        Returns:
            Distance in meters, or None if not available
        """
        try:
            if origin_idx >= len(self.rows) or dest_idx >= len(self.rows[origin_idx].get("elements", [])):
                return None
            
            element = self.rows[origin_idx]["elements"][dest_idx]
            if element.get("status") != "OK":
                return None
            
            if "distance" in element:
                return element["distance"]["value"]
            
            return None
            
        except (KeyError, IndexError, TypeError):
            return None


class GoogleDistanceService:
    """Service for Google Distance Matrix API"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_DISTANCE_MATRIX_API_KEY") or os.getenv("GOOGLE_PLACES_API_KEY")
        self.session: Optional[aiohttp.ClientSession] = None
        
        if not self.api_key or self.api_key in ["your_google_distance_matrix_api_key_here", "your_google_places_api_key_here"]:
            raise ValueError("❌ GOOGLE DISTANCE MATRIX API KEY REQUIRED! Please set GOOGLE_PLACES_API_KEY in .env file. No mock data allowed - real-time data only!")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]],
        mode: TravelMode = TravelMode.DRIVING,
        traffic_model: TrafficModel = TrafficModel.BEST_GUESS,
        departure_time: Optional[str] = "now"
    ) -> DistanceMatrixResult:
        """
        Get distance matrix between multiple origins and destinations
        
        Args:
            origins: List of (lat, lng) tuples for starting points
            destinations: List of (lat, lng) tuples for destinations
            mode: Travel mode (driving, walking, bicycling, transit)
            traffic_model: Traffic model for driving mode
            departure_time: Departure time for traffic calculations ("now" or epoch timestamp)
            
        Returns:
            DistanceMatrixResult object
        """
        if not self.api_key:
            raise ValueError("Google Distance Matrix API key required. No mock data allowed.")

        def waypoint(lat: float, lng: float) -> Dict[str, Any]:
            return {"waypoint": {"location": {"latLng": {"latitude": lat, "longitude": lng}}}}

        # Routes API computeRouteMatrix (replaces the legacy Distance Matrix API)
        body: Dict[str, Any] = {
            "origins": [waypoint(lat, lng) for lat, lng in origins],
            "destinations": [waypoint(lat, lng) for lat, lng in destinations],
            "travelMode": ROUTES_TRAVEL_MODE[mode.value],
        }
        if mode == TravelMode.DRIVING:
            body["routingPreference"] = "TRAFFIC_AWARE"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,condition",
        }

        session = await self._get_session()
        async with session.post(ROUTES_MATRIX_URL, json=body, headers=headers) as response:
            data = await response.json(content_type=None)
            if response.status != 200:
                err = data[0] if isinstance(data, list) and data else data
                message = err.get("error", {}).get("message", f"HTTP {response.status}")
                raise ValueError(f"Routes API error: {message}")

        # Reshape into the legacy rows/elements layout that DistanceMatrixResult reads
        elements = [[{"status": "ZERO_RESULTS"} for _ in destinations] for _ in origins]
        for item in data:
            i, j = item.get("originIndex", 0), item.get("destinationIndex", 0)
            if item.get("condition") == "ROUTE_EXISTS":
                seconds = int(item.get("duration", "0s").rstrip("s"))
                element = {"status": "OK", "distance": {"value": item.get("distanceMeters", 0)}, "duration": {"value": seconds}}
                if mode == TravelMode.DRIVING:
                    element["duration_in_traffic"] = {"value": seconds}
                elements[i][j] = element
        rows = [{"elements": row} for row in elements]

        origin_strings = [f"{lat},{lng}" for lat, lng in origins]
        dest_strings = [f"{lat},{lng}" for lat, lng in destinations]
        logger.info(f"Route matrix calculated for {len(origins)} origins and {len(destinations)} destinations")
        return DistanceMatrixResult(origin_strings, dest_strings, {"status": "OK", "rows": rows})


# Global instance
_distance_service: Optional[GoogleDistanceService] = None


async def get_distance_service() -> GoogleDistanceService:
    """Get or create the Google Distance service instance"""
    global _distance_service
    if _distance_service is None:
        _distance_service = GoogleDistanceService()
    return _distance_service


async def cleanup_distance_service():
    """Cleanup the Google Distance service"""
    global _distance_service
    if _distance_service:
        await _distance_service.close()
        _distance_service = None