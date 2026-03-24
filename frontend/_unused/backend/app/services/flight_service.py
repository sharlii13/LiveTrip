import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from ..schemas.itinerary import FlightData, FlightStatus
import json


class FlightService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://api.aviationstack.com/v1"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    def _map_flight_status(self, status: str) -> FlightStatus:
        """Map AviationStack status to our enum"""
        status = status.lower()
        if "scheduled" in status or "active" in status:
            return FlightStatus.ON_TIME
        elif "delayed" in status:
            return FlightStatus.DELAYED
        elif "cancelled" in status or "canceled" in status:
            return FlightStatus.CANCELLED
        elif "diverted" in status or "redirected" in status:
            return FlightStatus.RESCHEDULED
        else:
            return FlightStatus.ON_TIME

    async def get_flight_status(self, flight_number: str, date: Optional[datetime] = None) -> Optional[FlightData]:
        """Get current status of a specific flight"""
        session = await self._get_session()
        
        params = {
            "access_key": self.api_key,
            "flight_iata": flight_number
        }
        
        if date:
            params["flight_date"] = date.strftime("%Y-%m-%d")

        async with session.get(f"{self.base_url}/flights", params=params) as response:
            if response.status == 200:
                data = await response.json()
                flights = data.get("data", [])
                
                if flights:
                    flight = flights[0]  # Get the most recent flight
                    
                    # Calculate delay in minutes
                    delay_minutes = None
                    if flight.get("departure") and flight["departure"].get("scheduled") and flight["departure"].get("actual"):
                        scheduled = datetime.fromisoformat(flight["departure"]["scheduled"].replace("Z", "+00:00"))
                        actual = datetime.fromisoformat(flight["departure"]["actual"].replace("Z", "+00:00"))
                        delay_minutes = int((actual - scheduled).total_seconds() / 60)
                    
                    return FlightData(
                        flight_number=flight["flight"]["iata"] or flight["flight"]["icao"],
                        airline=flight["airline"]["name"],
                        departure_time=datetime.fromisoformat(
                            (flight["departure"]["scheduled"] or flight["departure"]["estimated"]).replace("Z", "+00:00")
                        ),
                        arrival_time=datetime.fromisoformat(
                            (flight["arrival"]["scheduled"] or flight["arrival"]["estimated"]).replace("Z", "+00:00")
                        ),
                        status=self._map_flight_status(flight["flight_status"]),
                        delay_minutes=delay_minutes,
                        gate=flight["departure"].get("gate"),
                        terminal=flight["departure"].get("terminal")
                    )
                else:
                    return None
            else:
                raise Exception(f"Flight API error: {response.status}")

    async def track_multiple_flights(self, flight_numbers: List[str], date: Optional[datetime] = None) -> List[FlightData]:
        """Track multiple flights at once"""
        flights = []
        
        # Process flights in parallel
        tasks = [self.get_flight_status(flight_num, date) for flight_num in flight_numbers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, FlightData):
                flights.append(result)
        
        return flights

    async def get_airport_departures(self, airport_iata: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get departures from a specific airport"""
        session = await self._get_session()
        
        params = {
            "access_key": self.api_key,
            "dep_iata": airport_iata,
            "limit": limit
        }

        async with session.get(f"{self.base_url}/flights", params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", [])
            else:
                raise Exception(f"Airport departures API error: {response.status}")

    async def get_airport_arrivals(self, airport_iata: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get arrivals to a specific airport"""
        session = await self._get_session()
        
        params = {
            "access_key": self.api_key,
            "arr_iata": airport_iata,
            "limit": limit
        }

        async with session.get(f"{self.base_url}/flights", params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", [])
            else:
                raise Exception(f"Airport arrivals API error: {response.status}")

    async def search_flights(self, origin: str, destination: str, date: datetime) -> List[Dict[str, Any]]:
        """Search for flights between two airports on a specific date"""
        session = await self._get_session()
        
        params = {
            "access_key": self.api_key,
            "dep_iata": origin,
            "arr_iata": destination,
            "flight_date": date.strftime("%Y-%m-%d")
        }

        async with session.get(f"{self.base_url}/flights", params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", [])
            else:
                raise Exception(f"Flight search API error: {response.status}")

    async def get_airline_info(self, airline_iata: str) -> Optional[Dict[str, Any]]:
        """Get information about an airline"""
        session = await self._get_session()
        
        params = {
            "access_key": self.api_key,
            "airline_iata": airline_iata
        }

        async with session.get(f"{self.base_url}/airlines", params=params) as response:
            if response.status == 200:
                data = await response.json()
                airlines = data.get("data", [])
                return airlines[0] if airlines else None
            else:
                return None

    async def get_airport_info(self, airport_iata: str) -> Optional[Dict[str, Any]]:
        """Get information about an airport"""
        session = await self._get_session()
        
        params = {
            "access_key": self.api_key,
            "iata_code": airport_iata
        }

        async with session.get(f"{self.base_url}/airports", params=params) as response:
            if response.status == 200:
                data = await response.json()
                airports = data.get("data", [])
                return airports[0] if airports else None
            else:
                return None

    def calculate_impact_on_itinerary(self, flight_data: FlightData, scheduled_activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate how flight delays affect the itinerary"""
        impact = {
            "affected_activities": [],
            "total_delay_minutes": flight_data.delay_minutes or 0,
            "recommendations": []
        }
        
        if flight_data.status in [FlightStatus.DELAYED, FlightStatus.RESCHEDULED] and flight_data.delay_minutes:
            delay_minutes = flight_data.delay_minutes
            
            # Find activities that are affected by the delay
            arrival_time = flight_data.arrival_time
            if flight_data.delay_minutes:
                arrival_time = arrival_time + timedelta(minutes=flight_data.delay_minutes)
            
            for activity in scheduled_activities:
                activity_start = datetime.fromisoformat(activity.get("start_time", ""))
                
                # If activity is within 2 hours of delayed arrival, it's likely affected
                if activity_start < arrival_time + timedelta(hours=2):
                    impact["affected_activities"].append({
                        "activity_id": activity.get("id"),
                        "activity_name": activity.get("name"),
                        "original_start": activity.get("start_time"),
                        "suggested_action": "reschedule" if activity.get("flexibility", 1) > 2 else "cancel"
                    })
            
            # Generate recommendations
            if delay_minutes < 60:
                impact["recommendations"].append("Minor delay - consider rescheduling flexible activities")
            elif delay_minutes < 180:
                impact["recommendations"].append("Moderate delay - reschedule first day activities, consider backup indoor options")
            else:
                impact["recommendations"].append("Major delay - consider rescheduling entire first day, book later hotel check-in")
        
        elif flight_data.status == FlightStatus.CANCELLED:
            impact["recommendations"].extend([
                "Flight cancelled - check alternative flights",
                "Consider extending trip or shortening itinerary",
                "Contact accommodations and activities for rescheduling"
            ])
        
        return impact

    async def monitor_flights(self, flight_numbers: List[str], callback_url: Optional[str] = None) -> Dict[str, Any]:
        """Set up monitoring for flight status changes"""
        # This would typically involve setting up webhooks or polling
        # For now, we'll return monitoring setup info
        monitoring_info = {
            "flights": flight_numbers,
            "status": "monitoring_started",
            "callback_url": callback_url,
            "check_interval_minutes": 15,
            "notifications": {
                "delay_threshold_minutes": 30,
                "status_changes": True,
                "gate_changes": True
            }
        }
        
        return monitoring_info

    async def get_flight_history(self, flight_number: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get historical data for a flight (for reliability analysis)"""
        session = await self._get_session()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            "access_key": self.api_key,
            "flight_iata": flight_number,
            "date_from": start_date.strftime("%Y-%m-%d"),
            "date_to": end_date.strftime("%Y-%m-%d")
        }

        try:
            async with session.get(f"{self.base_url}/flights", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                else:
                    return []
        except Exception:
            return []

    def analyze_flight_reliability(self, flight_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze flight reliability based on historical data"""
        if not flight_history:
            return {"reliability_score": 0, "analysis": "No historical data available"}
        
        total_flights = len(flight_history)
        on_time = 0
        delayed = 0
        cancelled = 0
        total_delay_minutes = 0
        
        for flight in flight_history:
            status = flight.get("flight_status", "").lower()
            
            if "cancelled" in status:
                cancelled += 1
            elif "delayed" in status:
                delayed += 1
                # Try to calculate delay
                if flight.get("departure") and flight["departure"].get("scheduled") and flight["departure"].get("actual"):
                    scheduled = datetime.fromisoformat(flight["departure"]["scheduled"].replace("Z", "+00:00"))
                    actual = datetime.fromisoformat(flight["departure"]["actual"].replace("Z", "+00:00"))
                    delay = (actual - scheduled).total_seconds() / 60
                    total_delay_minutes += max(0, delay)
            else:
                on_time += 1
        
        on_time_percentage = (on_time / total_flights) * 100 if total_flights > 0 else 0
        avg_delay = total_delay_minutes / delayed if delayed > 0 else 0
        
        # Calculate reliability score (0-100)
        reliability_score = max(0, on_time_percentage - (cancelled / total_flights * 50))
        
        analysis = {
            "reliability_score": round(reliability_score, 1),
            "on_time_percentage": round(on_time_percentage, 1),
            "delay_percentage": round((delayed / total_flights) * 100, 1) if total_flights > 0 else 0,
            "cancellation_percentage": round((cancelled / total_flights) * 100, 1) if total_flights > 0 else 0,
            "average_delay_minutes": round(avg_delay, 1),
            "total_flights_analyzed": total_flights,
            "recommendation": self._get_reliability_recommendation(reliability_score)
        }
        
        return analysis

    def _get_reliability_recommendation(self, score: float) -> str:
        """Get recommendation based on reliability score"""
        if score >= 90:
            return "Highly reliable flight - low risk of delays"
        elif score >= 75:
            return "Generally reliable - consider minor backup plans"
        elif score >= 60:
            return "Moderate reliability - plan flexible itinerary"
        elif score >= 40:
            return "Below average reliability - have strong backup plans"
        else:
            return "Poor reliability - consider alternative flights"