import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from ..schemas.itinerary import WeatherData, WeatherCondition, Location
import os


class WeatherService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    def _map_weather_condition(self, weather_main: str, weather_description: str) -> WeatherCondition:
        """Map OpenWeather conditions to our enum"""
        weather_main = weather_main.lower()
        weather_description = weather_description.lower()
        
        if "rain" in weather_main or "drizzle" in weather_main:
            return WeatherCondition.RAINY
        elif "snow" in weather_main:
            return WeatherCondition.SNOWY
        elif "thunderstorm" in weather_main:
            return WeatherCondition.STORMY
        elif "clear" in weather_main:
            return WeatherCondition.SUNNY
        else:
            return WeatherCondition.CLOUDY

    async def get_current_weather(self, location: Location) -> WeatherData:
        """Get current weather for a specific location"""
        session = await self._get_session()
        
        params = {
            "lat": location.latitude,
            "lon": location.longitude,
            "appid": self.api_key,
            "units": "metric"
        }
        
        async with session.get(f"{self.base_url}/weather", params=params) as response:
            if response.status == 200:
                data = await response.json()
                return WeatherData(
                    temperature=data["main"]["temp"],
                    condition=self._map_weather_condition(
                        data["weather"][0]["main"],
                        data["weather"][0]["description"]
                    ),
                    humidity=data["main"]["humidity"],
                    wind_speed=data["wind"]["speed"],
                    precipitation_probability=0,  # Current weather doesn't have probability
                    timestamp=datetime.now()
                )
            else:
                raise Exception(f"Weather API error: {response.status}")

    async def get_forecast(self, location: Location, days: int = 5) -> List[WeatherData]:
        """Get weather forecast for next few days"""
        session = await self._get_session()
        
        params = {
            "lat": location.latitude,
            "lon": location.longitude,
            "appid": self.api_key,
            "units": "metric"
        }
        
        async with session.get(f"{self.base_url}/forecast", params=params) as response:
            if response.status == 200:
                data = await response.json()
                forecasts = []
                
                for item in data["list"][:days * 8]:  # 8 forecasts per day (3-hour intervals)
                    forecasts.append(WeatherData(
                        temperature=item["main"]["temp"],
                        condition=self._map_weather_condition(
                            item["weather"][0]["main"],
                            item["weather"][0]["description"]
                        ),
                        humidity=item["main"]["humidity"],
                        wind_speed=item["wind"]["speed"],
                        precipitation_probability=item.get("pop", 0) * 100,
                        timestamp=datetime.fromtimestamp(item["dt"])
                    ))
                
                return forecasts
            else:
                raise Exception(f"Forecast API error: {response.status}")

    async def check_weather_alerts(self, location: Location) -> List[Dict[str, Any]]:
        """Check for weather alerts/warnings"""
        session = await self._get_session()
        
        params = {
            "lat": location.latitude,
            "lon": location.longitude,
            "appid": self.api_key
        }
        
        try:
            async with session.get(f"{self.base_url}/onecall", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("alerts", [])
                else:
                    return []
        except Exception:
            return []

    def is_outdoor_weather_suitable(self, weather: WeatherData, activity_type: str) -> bool:
        """Check if weather is suitable for outdoor activities"""
        if activity_type not in ["outdoor", "sightseeing", "adventure"]:
            return True  # Indoor activities aren't weather dependent
        
        # Check for unsuitable conditions
        if weather.condition in [WeatherCondition.RAINY, WeatherCondition.STORMY]:
            return False
        
        if weather.precipitation_probability > 70:
            return False
        
        if weather.temperature < 0 or weather.temperature > 40:
            return False
        
        if weather.wind_speed > 15:  # Very windy
            return False
        
        return True

    async def get_hourly_forecast(self, location: Location, hours: int = 24) -> List[WeatherData]:
        """Get hourly weather forecast"""
        session = await self._get_session()
        
        params = {
            "lat": location.latitude,
            "lon": location.longitude,
            "appid": self.api_key,
            "units": "metric"
        }
        
        try:
            async with session.get(f"{self.base_url}/onecall", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    forecasts = []
                    
                    for item in data.get("hourly", [])[:hours]:
                        forecasts.append(WeatherData(
                            temperature=item["temp"],
                            condition=self._map_weather_condition(
                                item["weather"][0]["main"],
                                item["weather"][0]["description"]
                            ),
                            humidity=item["humidity"],
                            wind_speed=item["wind_speed"],
                            precipitation_probability=item.get("pop", 0) * 100,
                            timestamp=datetime.fromtimestamp(item["dt"])
                        ))
                    
                    return forecasts
                else:
                    # Fallback to 5-day forecast if one call API is not available
                    return await self.get_forecast(location, days=2)
        except Exception:
            # Fallback to 5-day forecast
            return await self.get_forecast(location, days=2)


# AccuWeather service as backup
class AccuWeatherService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://dataservice.accuweather.com"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_location_key(self, location: Location) -> Optional[str]:
        """Get AccuWeather location key for coordinates"""
        session = await self._get_session()
        
        params = {
            "apikey": self.api_key,
            "q": f"{location.latitude},{location.longitude}"
        }
        
        try:
            async with session.get(f"{self.base_url}/locations/v1/cities/geoposition/search", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["Key"]
                else:
                    return None
        except Exception:
            return None

    async def get_current_weather(self, location: Location) -> Optional[WeatherData]:
        """Get current weather using AccuWeather API"""
        location_key = await self.get_location_key(location)
        if not location_key:
            return None
        
        session = await self._get_session()
        
        params = {
            "apikey": self.api_key,
            "details": "true"
        }
        
        try:
            async with session.get(f"{self.base_url}/currentconditions/v1/{location_key}", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        weather_data = data[0]
                        return WeatherData(
                            temperature=weather_data["Temperature"]["Metric"]["Value"],
                            condition=self._map_accu_weather_condition(weather_data["WeatherText"]),
                            humidity=weather_data.get("RelativeHumidity", 50),
                            wind_speed=weather_data["Wind"]["Speed"]["Metric"]["Value"],
                            precipitation_probability=weather_data.get("PrecipitationProbability", 0),
                            timestamp=datetime.now()
                        )
                else:
                    return None
        except Exception:
            return None

    def _map_accu_weather_condition(self, weather_text: str) -> WeatherCondition:
        """Map AccuWeather conditions to our enum"""
        weather_text = weather_text.lower()
        
        if any(word in weather_text for word in ["rain", "shower", "drizzle"]):
            return WeatherCondition.RAINY
        elif any(word in weather_text for word in ["snow", "flurries", "sleet"]):
            return WeatherCondition.SNOWY
        elif any(word in weather_text for word in ["storm", "thunder"]):
            return WeatherCondition.STORMY
        elif any(word in weather_text for word in ["sunny", "clear"]):
            return WeatherCondition.SUNNY
        else:
            return WeatherCondition.CLOUDY