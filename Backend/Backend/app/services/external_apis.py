# services/external_apis.py
import httpx
import os
import json
from datetime import datetime
from typing import Dict, List, Optional

class WeatherService:
    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
    async def get_current_weather(self, location: str) -> Dict:
        """Get current weather for a location"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/weather",
                params={
                    "q": location,
                    "appid": self.api_key,
                    "units": "metric"
                }
            )
            return response.json() if response.status_code == 200 else {}
    
    async def get_forecast(self, location: str, days: int = 5) -> Dict:
        """Get weather forecast for a location"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/forecast",
                params={
                    "q": location,
                    "appid": self.api_key,
                    "units": "metric",
                    "cnt": days * 8  # 8 forecasts per day (3-hour intervals)
                }
            )
            return response.json() if response.status_code == 200 else {}

class FlightService:
    def __init__(self):
        self.api_key = os.getenv("AVIATIONSTACK_API_KEY")
        self.base_url = "http://api.aviationstack.com/v1"
    
    async def get_flights(self, departure: str, arrival: str) -> Dict:
        """Get flight information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/flights",
                params={
                    "access_key": self.api_key,
                    "dep_iata": departure,
                    "arr_iata": arrival,
                    "limit": 10
                }
            )
            return response.json() if response.status_code == 200 else {}

class EventService:
    def __init__(self):
        self.api_key = os.getenv("EVENTBRITE_API_KEY")
        self.base_url = "https://www.eventbriteapi.com/v3"
    
    async def get_events(self, location: str, start_date: str = None) -> Dict:
        """Get events for a location"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/events/search/",
                headers=headers,
                params={
                    "location.address": location,
                    "start_date.range_start": start_date or datetime.now().isoformat(),
                    "expand": "venue",
                    "page_size": 20
                }
            )
            return response.json() if response.status_code == 200 else {}

class GoogleMapsService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        self.base_url = "https://maps.googleapis.com/maps/api"
    
    async def get_places(self, location: str, place_type: str = "tourist_attraction") -> Dict:
        """Get places of interest"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/place/nearbysearch/json",
                params={
                    "location": location,
                    "radius": 5000,
                    "type": place_type,
                    "key": self.api_key
                }
            )
            return response.json() if response.status_code == 200 else {}
    
    async def geocode_location(self, address: str) -> Dict:
        """Convert address to coordinates"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/geocode/json",
                params={
                    "address": address,
                    "key": self.api_key
                }
            )
            return response.json() if response.status_code == 200 else {}

# Service instances
weather_service = WeatherService()
flight_service = FlightService()
event_service = EventService()
maps_service = GoogleMapsService()