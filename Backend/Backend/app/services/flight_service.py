# services/flight_service.py
import httpx  
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class FlightService:
    def __init__(self):
        self.api_key = os.getenv("AVIATIONSTACK_API_KEY")
        self.base_url = os.getenv("AVIATIONSTACK_BASE_URL", "http://api.aviationstack.com/v1")
        
    async def track_flight(self, flight_number: str, airline_code: str = None) -> Optional[Dict]:
        """Track a specific flight by flight number"""
        try:
            params = {
                "access_key": self.api_key,
                "flight_iata": flight_number
            }
            
            if airline_code:
                params["airline_iata"] = airline_code
            
            # ✅ Fixed: Using httpx instead of aiohttp
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/flights", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    flights = data.get("data", [])
                    
                    if flights:
                        flight = flights[0]  # Get the first matching flight
                        return self._parse_flight_data(flight)
                    else:
                        logger.warning(f"No flight found for {flight_number}")
                        return None
                else:
                    logger.error(f"API request failed: {response.status_code}")
                    return None
                        
        except Exception as e:
            logger.error(f"Error tracking flight {flight_number}: {e}")
            return None
    
    async def get_flight_by_route(self, departure_iata: str, arrival_iata: str, 
                                 flight_date: str = None) -> List[Dict]:
        """Get flights by route (departure and arrival airports)"""
        try:
            params = {
                "access_key": self.api_key,
                "dep_iata": departure_iata,
                "arr_iata": arrival_iata
            }
            
            if flight_date:
                params["flight_date"] = flight_date
            
            # ✅ Fixed: Using httpx instead of aiohttp
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/flights", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    flights = data.get("data", [])
                    return [self._parse_flight_data(flight) for flight in flights]
                else:
                    logger.error(f"API request failed: {response.status_code}")
                    return []
                        
        except Exception as e:
            logger.error(f"Error getting flights for route {departure_iata}-{arrival_iata}: {e}")
            return []
    
    async def search_flights(self, departure: str, arrival: str, date: str = None) -> List[Dict]:
        """Search for flights between airports"""
        try:
            params = {
                "access_key": self.api_key,
                "dep_iata": departure,
                "arr_iata": arrival,
                "limit": 20  # Limit results for better performance
            }
            
            if date:
                params["flight_date"] = date
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/flights", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    flights = data.get("data", [])
                    
                    # Parse and sort by departure time
                    parsed_flights = [self._parse_flight_data(flight) for flight in flights]
                    
                    # Sort by scheduled departure time
                    parsed_flights.sort(key=lambda x: x["departure"].get("scheduled", ""))
                    
                    return parsed_flights
                else:
                    logger.error(f"Flight search failed: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching flights {departure}-{arrival}: {e}")
            return []
    
    async def get_flight_status(self, flight_number: str, date: str = None) -> Optional[Dict]:
        """Get current status of a specific flight"""
        try:
            params = {
                "access_key": self.api_key,
                "flight_iata": flight_number
            }
            
            if date:
                params["flight_date"] = date
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(f"{self.base_url}/flights", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    flights = data.get("data", [])
                    
                    if flights:
                        # Get the most recent flight
                        flight = flights[0]
                        parsed_data = self._parse_flight_data(flight)
                        
                        # Add real-time status information
                        status_info = {
                            "real_time_status": self._get_real_time_status(parsed_data),
                            "next_update": datetime.utcnow() + timedelta(minutes=5),
                            "tracking_active": True
                        }
                        
                        parsed_data.update(status_info)
                        return parsed_data
                    else:
                        return None
                else:
                    logger.error(f"Status check failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting flight status {flight_number}: {e}")
            return None
    
    def _parse_flight_data(self, flight_data: Dict) -> Dict:
        """Parse raw flight data from API"""
        departure = flight_data.get("departure", {})
        arrival = flight_data.get("arrival", {})
        flight_info = flight_data.get("flight", {})
        airline = flight_data.get("airline", {})
        
        # Calculate delay information
        scheduled_departure = departure.get("scheduled")
        estimated_departure = departure.get("estimated")
        actual_departure = departure.get("actual")
        
        scheduled_arrival = arrival.get("scheduled")
        estimated_arrival = arrival.get("estimated")
        actual_arrival = arrival.get("actual")
        
        # Determine delay status
        delay_minutes = self._calculate_delay(
            scheduled_departure, estimated_departure, actual_departure
        )
        
        return {
            "flight_number": flight_info.get("iata", ""),
            "airline": {
                "name": airline.get("name", ""),
                "iata": airline.get("iata", ""),
                "icao": airline.get("icao", "")
            },
            "status": flight_data.get("flight_status", "unknown"),
            "departure": {
                "airport": departure.get("airport", ""),
                "iata": departure.get("iata", ""),
                "terminal": departure.get("terminal"),
                "gate": departure.get("gate"),
                "scheduled": scheduled_departure,
                "estimated": estimated_departure,
                "actual": actual_departure,
                "delay_minutes": delay_minutes
            },
            "arrival": {
                "airport": arrival.get("airport", ""),
                "iata": arrival.get("iata", ""),
                "terminal": arrival.get("terminal"),
                "gate": arrival.get("gate"),
                "scheduled": scheduled_arrival,
                "estimated": estimated_arrival,
                "actual": actual_arrival
            },
            "aircraft": flight_data.get("aircraft", {}),
            "is_delayed": delay_minutes > 15,  # Consider delayed if >15 minutes
            "delay_minutes": delay_minutes,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _calculate_delay(self, scheduled: str, estimated: str, actual: str) -> int:
        """Calculate delay in minutes"""
        try:
            scheduled_dt = datetime.fromisoformat(scheduled.replace('Z', '+00:00')) if scheduled else None
            
            # Use actual if available, otherwise estimated
            current_dt = None
            if actual:
                current_dt = datetime.fromisoformat(actual.replace('Z', '+00:00'))
            elif estimated:
                current_dt = datetime.fromisoformat(estimated.replace('Z', '+00:00'))
            
            if scheduled_dt and current_dt:
                delay = (current_dt - scheduled_dt).total_seconds() / 60
                return max(0, int(delay))  # Return 0 if early
            
            return 0
        except Exception:
            return 0
    
    def _get_real_time_status(self, flight_data: Dict) -> Dict:
        """Determine real-time flight status"""
        status = flight_data.get("status", "unknown")
        delay_minutes = flight_data.get("delay_minutes", 0)
        
        # Enhanced status messages
        status_messages = {
            "scheduled": "✈️ Flight Scheduled",
            "active": "🛫 In Flight",
            "landed": "🛬 Landed",
            "cancelled": "❌ Cancelled",
            "delayed": f"⏰ Delayed by {delay_minutes} minutes",
            "unknown": "❓ Status Unknown"
        }
        
        return {
            "display_status": status_messages.get(status, status.title()),
            "color_code": self._get_status_color(status, delay_minutes),
            "is_critical": delay_minutes > 60 or status in ["cancelled"],
            "recommendations": self._get_status_recommendations(status, delay_minutes)
        }
    
    def _get_status_color(self, status: str, delay_minutes: int) -> str:
        """Get color code for flight status"""
        if status == "cancelled":
            return "red"
        elif status == "landed":
            return "green"
        elif delay_minutes > 60:
            return "red"
        elif delay_minutes > 15:
            return "orange"
        elif status == "active":
            return "blue"
        else:
            return "gray"
    
    def _get_status_recommendations(self, status: str, delay_minutes: int) -> List[str]:
        """Get recommendations based on flight status"""
        recommendations = []
        
        if delay_minutes > 30:
            recommendations.append("Consider adjusting your itinerary")
            recommendations.append("Contact ground transportation")
        
        if delay_minutes > 60:
            recommendations.append("Check with airline for meal vouchers")
            recommendations.append("Consider rebooking if possible")
        
        if status == "active":
            recommendations.append("Flight is airborne - prepare for arrival")
        
        if status == "landed":
            recommendations.append("Welcome to your destination!")
            recommendations.append("Check baggage claim information")
        
        return recommendations

# ✅ Enhanced flight service with better error handling
class FlightServiceWrapper:
    """Wrapper class with additional functionality"""
    
    def __init__(self):
        self.flight_service = FlightService()
        self.cache = {}  # Simple in-memory cache
        self.cache_duration = 300  # 5 minutes
    
    async def get_cached_flight_status(self, flight_number: str) -> Optional[Dict]:
        """Get flight status with caching"""
        cache_key = f"status_{flight_number}"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.utcnow() - timestamp < timedelta(seconds=self.cache_duration):
                logger.info(f"Returning cached data for {flight_number}")
                return cached_data
        
        # Fetch new data
        flight_data = await self.flight_service.get_flight_status(flight_number)
        
        if flight_data:
            # Cache the result
            self.cache[cache_key] = (flight_data, datetime.utcnow())
            
        return flight_data
    
    def clear_cache(self):
        """Clear flight status cache"""
        self.cache.clear()
        logger.info("Flight status cache cleared")

# Global flight service instance
flight_service = FlightService()
flight_service_cached = FlightServiceWrapper()
