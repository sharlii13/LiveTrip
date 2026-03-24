from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import math
import random
import sys
import os

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
    def __init__(self, expire_minutes: int = 5):
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

cache5m = SimpleCache(5)

# ✅ Settings functions
def get_openweather_api_key():
    return os.getenv("OPENWEATHER_API_KEY", "d021025aed18cf0d44575b63a855baea")

def get_openweather_base_url():
    return "http://api.openweathermap.org/data/2.5"

# ✅ Create router
router = APIRouter(prefix="/weather", tags=["🌤️ Weather Service"])

# ✅ Enums
class WeatherCondition(str, Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    PARTLY_CLOUDY = "partly_cloudy"
    OVERCAST = "overcast"
    LIGHT_RAIN = "light_rain"
    MODERATE_RAIN = "moderate_rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    SNOW = "snow"
    FOG = "fog"
    MIST = "mist"

class AlertSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"
    EXTREME = "extreme"

# ✅ Pydantic Models
class WeatherLocation(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    city: Optional[str] = Field(None, description="City name")
    country: Optional[str] = Field(None, description="Country name")

class CurrentWeather(BaseModel):
    location: WeatherLocation
    temperature: float = Field(..., description="Temperature in Celsius")
    feels_like: float = Field(..., description="Feels like temperature")
    humidity: int = Field(..., ge=0, le=100, description="Humidity percentage")
    condition: str = Field(..., description="Weather condition")
    wind_speed: float = Field(..., ge=0, description="Wind speed in km/h")
    wind_direction: Optional[int] = Field(None, ge=0, le=360, description="Wind direction in degrees")
    pressure: Optional[float] = Field(None, description="Atmospheric pressure in hPa")
    visibility: Optional[float] = Field(None, description="Visibility in km")
    uv_index: Optional[int] = Field(None, ge=0, le=11, description="UV index")

class WeatherAlert(BaseModel):
    alert_type: str
    severity: AlertSeverity
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    areas_affected: List[str]

class ForecastDay(BaseModel):
    date: str
    temp_min: float
    temp_max: float
    condition: str
    condition_icon: str
    humidity: int
    wind_speed: float
    precipitation_chance: int
    sunrise: Optional[str] = None
    sunset: Optional[str] = None

# ✅ Mock Weather Data
MOCK_WEATHER_DATA = {
    # Mumbai
    (19.0760, 72.8777): {
        "temp_c": 28.5,
        "feels_like_c": 32.1,
        "humidity": 78,
        "condition": "partly cloudy",
        "wind_kph": 12.5,
        "wind_direction": 240,
        "pressure": 1013.2,
        "visibility": 8.5,
        "uv_index": 7,
        "city": "Mumbai",
        "country": "India"
    },
    # Delhi  
    (28.6139, 77.2090): {
        "temp_c": 32.1,
        "feels_like_c": 36.8,
        "humidity": 65,
        "condition": "clear sky",
        "wind_kph": 8.3,
        "wind_direction": 180,
        "pressure": 1010.5,
        "visibility": 12.0,
        "uv_index": 9,
        "city": "Delhi",
        "country": "India"
    },
    # Bangalore
    (12.9716, 77.5946): {
        "temp_c": 24.2,
        "feels_like_c": 26.1,
        "humidity": 82,
        "condition": "light rain",
        "wind_kph": 15.8,
        "wind_direction": 270,
        "pressure": 1008.7,
        "visibility": 6.2,
        "uv_index": 4,
        "city": "Bangalore",
        "country": "India"
    },
    # Paris
    (48.8566, 2.3522): {
        "temp_c": 18.3,
        "feels_like_c": 16.9,
        "humidity": 71,
        "condition": "overcast clouds",
        "wind_kph": 22.1,
        "wind_direction": 320,
        "pressure": 1018.3,
        "visibility": 10.0,
        "uv_index": 3,
        "city": "Paris",
        "country": "France"
    },
    # New York
    (40.7128, -74.0060): {
        "temp_c": 22.7,
        "feels_like_c": 24.1,
        "humidity": 68,
        "condition": "scattered clouds",
        "wind_kph": 18.5,
        "wind_direction": 200,
        "pressure": 1015.8,
        "visibility": 16.0,
        "uv_index": 6,
        "city": "New York",
        "country": "USA"
    }
}

# ✅ Helper Functions
def find_nearest_mock_weather(lat: float, lon: float) -> Dict:
    """Find nearest mock weather data"""
    
    min_distance = float('inf')
    nearest_data = None
    nearest_location = None
    
    for (mock_lat, mock_lon), weather_data in MOCK_WEATHER_DATA.items():
        # Calculate distance using Haversine formula
        distance = calculate_distance(lat, lon, mock_lat, mock_lon)
        if distance < min_distance:
            min_distance = distance
            nearest_data = weather_data
            nearest_location = (mock_lat, mock_lon)
    
    if nearest_data:
        # Add some variation based on distance
        variation_factor = min(min_distance / 100, 0.3)  # Max 30% variation
        temp_variation = random.uniform(-5, 5) * variation_factor
        humidity_variation = random.randint(-10, 10) * int(variation_factor * 10)
        
        adjusted_data = nearest_data.copy()
        adjusted_data["temp_c"] = round(nearest_data["temp_c"] + temp_variation, 1)
        adjusted_data["feels_like_c"] = round(nearest_data["feels_like_c"] + temp_variation, 1)
        adjusted_data["humidity"] = max(0, min(100, nearest_data["humidity"] + humidity_variation))
        
        return adjusted_data
    
    # Fallback to generic data
    return {
        "temp_c": 25.0,
        "feels_like_c": 27.5,
        "humidity": 70,
        "condition": "partly cloudy",
        "wind_kph": 10.0,
        "wind_direction": 180,
        "pressure": 1013.25,
        "visibility": 10.0,
        "uv_index": 5,
        "city": "Unknown",
        "country": "Unknown"
    }

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in km"""
    R = 6371  # Earth's radius in kilometers
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lon/2) * math.sin(delta_lon/2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def get_weather_icon(condition: str) -> str:
    """Get weather icon based on condition"""
    
    condition_lower = condition.lower()
    
    icon_mapping = {
        "clear": "☀️",
        "sunny": "☀️",
        "partly cloudy": "⛅",
        "scattered clouds": "⛅",
        "cloudy": "☁️",
        "overcast": "☁️",
        "light rain": "🌦️",
        "moderate rain": "🌧️",
        "heavy rain": "⛈️",
        "thunderstorm": "⛈️",
        "snow": "❄️",
        "fog": "🌫️",
        "mist": "🌫️"
    }
    
    for key, icon in icon_mapping.items():
        if key in condition_lower:
            return icon
    
    return "🌤️"  # Default icon

def get_travel_recommendation(weather_data: Dict) -> Dict:
    """Get travel recommendations based on weather"""
    
    temp = weather_data.get("temp_c", 25)
    humidity = weather_data.get("humidity", 70)
    condition = weather_data.get("condition", "").lower()
    wind_kph = weather_data.get("wind_kph", 10)
    
    recommendations = {
        "clothing": [],
        "activities": [],
        "precautions": [],
        "travel_conditions": "good"
    }
    
    # Temperature-based recommendations
    if temp < 10:
        recommendations["clothing"].extend(["Heavy jacket", "Warm layers", "Gloves and hat"])
        recommendations["travel_conditions"] = "challenging"
    elif temp < 20:
        recommendations["clothing"].extend(["Light jacket", "Long pants", "Comfortable shoes"])
    elif temp < 30:
        recommendations["clothing"].extend(["Light clothing", "Comfortable walking shoes"])
    else:
        recommendations["clothing"].extend(["Light, breathable clothes", "Sun hat", "Sunscreen"])
        recommendations["precautions"].append("Stay hydrated")
    
    # Condition-based recommendations
    if "rain" in condition:
        recommendations["clothing"].append("Umbrella or raincoat")
        recommendations["precautions"].append("Watch for slippery surfaces")
        if "heavy" in condition:
            recommendations["travel_conditions"] = "poor"
            recommendations["precautions"].append("Avoid outdoor activities")
    
    if "thunderstorm" in condition:
        recommendations["travel_conditions"] = "dangerous"
        recommendations["precautions"].extend(["Seek shelter indoors", "Avoid high ground"])
    
    if "snow" in condition:
        recommendations["clothing"].extend(["Warm boots", "Snow gear"])
        recommendations["precautions"].append("Watch for icy conditions")
        recommendations["travel_conditions"] = "challenging"
    
    if "fog" in condition or "mist" in condition:
        recommendations["precautions"].extend(["Reduced visibility", "Drive carefully"])
    
    # Wind-based recommendations  
    if wind_kph > 30:
        recommendations["precautions"].append("Strong winds - secure loose items")
    
    # Humidity-based recommendations
    if humidity > 80:
        recommendations["precautions"].append("High humidity - take breaks")
    
    # Activity recommendations
    if temp > 20 and temp < 30 and "rain" not in condition:
        recommendations["activities"].extend(["Outdoor sightseeing", "Walking tours", "Photography"])
    elif "rain" in condition:
        recommendations["activities"].extend(["Museums", "Indoor attractions", "Covered markets"])
    elif temp > 30:
        recommendations["activities"].extend(["Early morning activities", "Air-conditioned venues"])
    
    return recommendations

async def fetch_openweather_data(lat: float, lon: float) -> Optional[Dict]:
    """Fetch weather data from OpenWeatherMap API"""
    
    if not HTTP_CLIENT_AVAILABLE:
        logger.info("HTTP client not available, using mock data")
        return find_nearest_mock_weather(lat, lon)
    
    api_key = get_openweather_api_key()
    base_url = get_openweather_base_url()
    
    if not api_key or api_key == "your_api_key_here":
        logger.info("OpenWeather API key not configured, using mock data")
        return find_nearest_mock_weather(lat, lon)
    
    try:
        url = f"{base_url}/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": "metric"
        }
        
        response = requests.get(url, params=params, timeout=10.0)
        
        if response.status_code == 200:
            data = response.json()
            
            # Normalize OpenWeather data
            weather_data = data.get("weather", [{}])[0]
            main_data = data.get("main", {})
            wind_data = data.get("wind", {})
            sys_data = data.get("sys", {})
            
            normalized = {
                "temp_c": main_data.get("temp"),
                "feels_like_c": main_data.get("feels_like"),
                "humidity": main_data.get("humidity"),
                "condition": weather_data.get("description", "unknown"),
                "wind_kph": round((wind_data.get("speed", 0) * 3.6), 1),
                "wind_direction": wind_data.get("deg"),
                "pressure": main_data.get("pressure"),
                "visibility": data.get("visibility", 0) / 1000 if data.get("visibility") else None,
                "city": data.get("name", "Unknown"),
                "country": sys_data.get("country", "Unknown")
            }
            
            return normalized
        else:
            logger.warning(f"OpenWeather API error: {response.status_code}")
            return find_nearest_mock_weather(lat, lon)
            
    except Exception as e:
        logger.error(f"Error fetching OpenWeather data: {e}")
        return find_nearest_mock_weather(lat, lon)

def generate_mock_forecast(lat: float, lon: float, days: int = 5) -> List[Dict]:
    """Generate mock weather forecast"""
    
    base_weather = find_nearest_mock_weather(lat, lon)
    base_temp = base_weather.get("temp_c", 25)
    
    forecast = []
    current_date = datetime.now()
    
    for i in range(days):
        date = current_date + timedelta(days=i)
        
        # Add some variation to temperature
        temp_variation = random.uniform(-3, 3)
        temp_max = base_temp + temp_variation + random.uniform(2, 6)
        temp_min = base_temp + temp_variation - random.uniform(2, 6)
        
        conditions = ["clear sky", "partly cloudy", "cloudy", "light rain", "scattered clouds"]
        condition = random.choice(conditions)
        
        forecast_day = {
            "date": date.strftime("%Y-%m-%d"),
            "day_name": date.strftime("%A"),
            "temp_min": round(temp_min, 1),
            "temp_max": round(temp_max, 1),
            "condition": condition,
            "condition_icon": get_weather_icon(condition),
            "humidity": random.randint(50, 90),
            "wind_speed": round(random.uniform(5, 25), 1),
            "precipitation_chance": random.randint(0, 80),
            "sunrise": "06:30",
            "sunset": "18:45"
        }
        
        forecast.append(forecast_day)
    
    return forecast

# ✅ API Endpoints
@router.get("/current",
            summary="Get Current Weather",
            description="Get current weather conditions for a specific location")
async def current_weather(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude")
):
    """Get current weather conditions"""
    
    try:
        # Check cache first
        cache_key = f"weather_current:{lat:.3f},{lon:.3f}"
        cached_result = cache5m.get(cache_key)
        
        if cached_result:
            cached_result["cached"] = True
            return cached_result
        
        # Fetch weather data
        weather_data = await fetch_openweather_data(lat, lon)
        
        if not weather_data:
            raise HTTPException(status_code=502, detail="Weather data not available")
        
        # Build response
        location = WeatherLocation(
            lat=lat,
            lon=lon,
            city=weather_data.get("city", "Unknown"),
            country=weather_data.get("country", "Unknown")
        )
        
        result = {
            "success": True,
            "location": location.dict(),
            "current_weather": {
                "temperature": weather_data["temp_c"],
                "feels_like": weather_data["feels_like_c"],
                "humidity": weather_data["humidity"],
                "condition": weather_data["condition"],
                "condition_icon": get_weather_icon(weather_data["condition"]),
                "wind_speed_kph": weather_data["wind_kph"],
                "wind_direction": weather_data.get("wind_direction"),
                "pressure_hpa": weather_data.get("pressure"),
                "visibility_km": weather_data.get("visibility"),
                "uv_index": weather_data.get("uv_index")
            },
            "travel_recommendations": get_travel_recommendation(weather_data),
            "last_updated": datetime.now().isoformat(),
            "cached": False,
            "data_source": "OpenWeatherMap API" if HTTP_CLIENT_AVAILABLE else "Mock Data"
        }
        
        # Cache the result
        cache5m.set(cache_key, result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current weather: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting current weather: {str(e)}")

@router.get("/forecast",
            summary="Get Weather Forecast",
            description="Get multi-day weather forecast for a location")
async def weather_forecast(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    days: int = Query(5, ge=1, le=14, description="Number of forecast days")
):
    """Get weather forecast for multiple days"""
    
    try:
        # Check cache first
        cache_key = f"weather_forecast:{lat:.3f},{lon:.3f}:{days}"
        cached_result = cache5m.get(cache_key)
        
        if cached_result:
            cached_result["cached"] = True
            return cached_result
        
        # Generate forecast (using mock data for now)
        forecast_data = generate_mock_forecast(lat, lon, days)
        
        # Get current weather for additional context
        current_data = await fetch_openweather_data(lat, lon)
        
        location = WeatherLocation(
            lat=lat,
            lon=lon,
            city=current_data.get("city", "Unknown") if current_data else "Unknown",
            country=current_data.get("country", "Unknown") if current_data else "Unknown"
        )
        
        result = {
            "success": True,
            "location": location.dict(),
            "forecast": forecast_data,
            "forecast_period": {
                "start_date": forecast_data[0]["date"],
                "end_date": forecast_data[-1]["date"],
                "total_days": len(forecast_data)
            },
            "summary": {
                "avg_temp_min": round(sum(day["temp_min"] for day in forecast_data) / len(forecast_data), 1),
                "avg_temp_max": round(sum(day["temp_max"] for day in forecast_data) / len(forecast_data), 1),
                "rainy_days": len([day for day in forecast_data if "rain" in day["condition"]]),
                "sunny_days": len([day for day in forecast_data if "clear" in day["condition"] or "sunny" in day["condition"]])
            },
            "last_updated": datetime.now().isoformat(),
            "cached": False,
            "data_source": "Mock Forecast Data"
        }
        
        # Cache the result
        cache5m.set(cache_key, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting weather forecast: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting weather forecast: {str(e)}")

@router.get("/alerts",
            summary="Get Weather Alerts",
            description="Get weather alerts and warnings for a location")
async def weather_alerts(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude")
):
    """Get weather alerts for a location"""
    
    try:
        # Mock weather alerts based on current conditions
        current_data = await fetch_openweather_data(lat, lon)
        alerts = []
        
        if current_data:
            condition = current_data.get("condition", "").lower()
            temp = current_data.get("temp_c", 25)
            wind_kph = current_data.get("wind_kph", 10)
            
            # Generate alerts based on conditions
            if "thunderstorm" in condition or "heavy rain" in condition:
                alerts.append({
                    "alert_type": "severe_weather",
                    "severity": AlertSeverity.HIGH,
                    "title": "Severe Weather Warning",
                    "description": "Thunderstorms with heavy rain expected. Avoid outdoor activities.",
                    "start_time": datetime.now(),
                    "end_time": datetime.now() + timedelta(hours=6),
                    "areas_affected": [current_data.get("city", "Local area")],
                    "icon": "⛈️"
                })
            
            if temp > 40:
                alerts.append({
                    "alert_type": "extreme_heat",
                    "severity": AlertSeverity.SEVERE,
                    "title": "Extreme Heat Warning",
                    "description": f"Temperature {temp}°C. Stay indoors, drink water, avoid sun exposure.",
                    "start_time": datetime.now(),
                    "end_time": datetime.now() + timedelta(hours=12),
                    "areas_affected": [current_data.get("city", "Local area")],
                    "icon": "🔥"
                })
            
            if temp < 0:
                alerts.append({
                    "alert_type": "extreme_cold",
                    "severity": AlertSeverity.HIGH,
                    "title": "Extreme Cold Warning",
                    "description": f"Temperature {temp}°C. Dress warmly, watch for frostbite.",
                    "start_time": datetime.now(),
                    "end_time": datetime.now() + timedelta(hours=24),
                    "areas_affected": [current_data.get("city", "Local area")],
                    "icon": "🥶"
                })
            
            if wind_kph > 50:
                alerts.append({
                    "alert_type": "high_wind",
                    "severity": AlertSeverity.MODERATE,
                    "title": "High Wind Warning",
                    "description": f"Wind speeds {wind_kph} km/h. Secure loose objects.",
                    "start_time": datetime.now(),
                    "end_time": datetime.now() + timedelta(hours=8),
                    "areas_affected": [current_data.get("city", "Local area")],
                    "icon": "💨"
                })
        
        # If no alerts, create a safe travel message
        if not alerts:
            alerts.append({
                "alert_type": "all_clear",
                "severity": AlertSeverity.LOW,
                "title": "No Weather Alerts",
                "description": "Current weather conditions are safe for travel.",
                "start_time": datetime.now(),
                "end_time": datetime.now() + timedelta(hours=24),
                "areas_affected": [current_data.get("city", "Local area") if current_data else "Local area"],
                "icon": "✅"
            })
        
        return {
            "success": True,
            "location": {
                "lat": lat,
                "lon": lon,
                "city": current_data.get("city", "Unknown") if current_data else "Unknown",
                "country": current_data.get("country", "Unknown") if current_data else "Unknown"
            },
            "alerts": alerts,
            "alert_count": len(alerts),
            "highest_severity": max((alert["severity"] for alert in alerts), default=AlertSeverity.LOW),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting weather alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting weather alerts: {str(e)}")

@router.get("/travel-conditions",
            summary="Get Travel Conditions",
            description="Get travel suitability based on weather conditions")
async def travel_conditions(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    activity_type: str = Query("sightseeing", description="Type of travel activity")
):
    """Get travel conditions and recommendations"""
    
    try:
        # Get current weather
        current_data = await fetch_openweather_data(lat, lon)
        
        if not current_data:
            raise HTTPException(status_code=502, detail="Weather data not available")
        
        # Calculate travel suitability score (0-100)
        score = 100
        factors = []
        
        temp = current_data.get("temp_c", 25)
        condition = current_data.get("condition", "").lower()
        humidity = current_data.get("humidity", 70)
        wind_kph = current_data.get("wind_kph", 10)
        
        # Temperature scoring
        if 20 <= temp <= 28:
            factors.append({"factor": "temperature", "impact": 0, "note": "Ideal temperature"})
        elif 15 <= temp < 20 or 28 < temp <= 35:
            score -= 10
            factors.append({"factor": "temperature", "impact": -10, "note": "Slightly uncomfortable temperature"})
        elif 10 <= temp < 15 or 35 < temp <= 40:
            score -= 20
            factors.append({"factor": "temperature", "impact": -20, "note": "Uncomfortable temperature"})
        else:
            score -= 40
            factors.append({"factor": "temperature", "impact": -40, "note": "Extreme temperature"})
        
        # Condition scoring
        if "clear" in condition or "sunny" in condition:
            factors.append({"factor": "weather", "impact": 0, "note": "Clear skies"})
        elif "partly cloudy" in condition or "scattered clouds" in condition:
            score -= 5
            factors.append({"factor": "weather", "impact": -5, "note": "Partly cloudy"})
        elif "cloudy" in condition or "overcast" in condition:
            score -= 10
            factors.append({"factor": "weather", "impact": -10, "note": "Cloudy skies"})
        elif "light rain" in condition or "drizzle" in condition:
            score -= 20
            factors.append({"factor": "weather", "impact": -20, "note": "Light rain"})
        elif "rain" in condition:
            score -= 30
            factors.append({"factor": "weather", "impact": -30, "note": "Rainy conditions"})
        elif "thunderstorm" in condition or "severe" in condition:
            score -= 50
            factors.append({"factor": "weather", "impact": -50, "note": "Severe weather"})
        
        # Wind scoring
        if wind_kph > 30:
            score -= 15
            factors.append({"factor": "wind", "impact": -15, "note": "Strong winds"})
        elif wind_kph > 20:
            score -= 5
            factors.append({"factor": "wind", "impact": -5, "note": "Moderate winds"})
        
        # Activity-specific adjustments
        activity_adjustments = {
            "beach": {"rain": -20, "cold": -30, "wind": -10},
            "hiking": {"rain": -25, "extreme_temp": -35, "wind": -5},
            "photography": {"rain": -30, "overcast": 10, "wind": -15},
            "sightseeing": {"rain": -15, "extreme_temp": -20},
            "shopping": {"rain": -5, "extreme_temp": -10}  # Indoor activities less affected
        }
        
        score = max(0, score)  # Don't go below 0
        
        # Determine travel recommendation
        if score >= 80:
            recommendation = "excellent"
            recommendation_text = "Perfect conditions for travel!"
        elif score >= 60:
            recommendation = "good"
            recommendation_text = "Good conditions with minor considerations."
        elif score >= 40:
            recommendation = "fair"
            recommendation_text = "Fair conditions, some activities may be affected."
        elif score >= 20:
            recommendation = "poor"
            recommendation_text = "Poor conditions, consider indoor activities."
        else:
            recommendation = "avoid"
            recommendation_text = "Avoid outdoor activities if possible."
        
        # Get detailed recommendations
        travel_rec = get_travel_recommendation(current_data)
        
        return {
            "success": True,
            "location": {
                "lat": lat,
                "lon": lon,
                "city": current_data.get("city", "Unknown"),
                "country": current_data.get("country", "Unknown")
            },
            "travel_conditions": {
                "overall_score": score,
                "recommendation": recommendation,
                "recommendation_text": recommendation_text,
                "activity_type": activity_type,
                "factors_affecting_score": factors
            },
            "current_weather": {
                "temperature": current_data["temp_c"],
                "condition": current_data["condition"],
                "condition_icon": get_weather_icon(current_data["condition"]),
                "humidity": current_data["humidity"],
                "wind_speed_kph": current_data["wind_kph"]
            },
            "recommendations": travel_rec,
            "best_times_today": [
                "10:00-12:00",
                "14:00-17:00"
            ] if score > 50 else ["Indoor activities recommended"],
            "last_updated": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting travel conditions: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting travel conditions: {str(e)}")

@router.get("/compare-locations",
            summary="Compare Weather at Multiple Locations",
            description="Compare weather conditions across multiple destinations")
async def compare_locations(
    locations: str = Query(..., description="Comma-separated lat,lon pairs (e.g., '19.0760,72.8777;28.6139,77.2090')")
):
    """Compare weather at multiple locations"""
    
    try:
        # Parse locations
        location_pairs = []
        for location_str in locations.split(';'):
            try:
                lat_str, lon_str = location_str.strip().split(',')
                lat = float(lat_str.strip())
                lon = float(lon_str.strip())
                
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    location_pairs.append((lat, lon))
            except (ValueError, IndexError):
                continue
        
        if not location_pairs:
            raise HTTPException(status_code=400, detail="No valid locations provided")
        
        if len(location_pairs) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 locations allowed")
        
        # Get weather for each location
        comparisons = []
        for i, (lat, lon) in enumerate(location_pairs):
            weather_data = await fetch_openweather_data(lat, lon)
            
            if weather_data:
                travel_rec = get_travel_recommendation(weather_data)
                
                comparisons.append({
                    "location_id": i + 1,
                    "coordinates": {"lat": lat, "lon": lon},
                    "city": weather_data.get("city", "Unknown"),
                    "country": weather_data.get("country", "Unknown"),
                    "weather": {
                        "temperature": weather_data["temp_c"],
                        "feels_like": weather_data["feels_like_c"],
                        "condition": weather_data["condition"],
                        "condition_icon": get_weather_icon(weather_data["condition"]),
                        "humidity": weather_data["humidity"],
                        "wind_speed_kph": weather_data["wind_kph"]
                    },
                    "travel_suitability": travel_rec["travel_conditions"],
                    "clothing_recommendations": travel_rec["clothing"]
                })
        
        if not comparisons:
            raise HTTPException(status_code=502, detail="Could not fetch weather for any location")
        
        # Find best and worst conditions
        best_location = max(comparisons, key=lambda x: x["weather"]["temperature"] if "rain" not in x["weather"]["condition"].lower() else 0)
        worst_conditions = min(comparisons, key=lambda x: x["weather"]["temperature"] if "rain" not in x["weather"]["condition"].lower() else 100)
        
        return {
            "success": True,
            "comparison": comparisons,
            "summary": {
                "total_locations": len(comparisons),
                "best_weather_location": {
                    "city": best_location["city"],
                    "temperature": best_location["weather"]["temperature"],
                    "condition": best_location["weather"]["condition"]
                },
                "average_temperature": round(sum(loc["weather"]["temperature"] for loc in comparisons) / len(comparisons), 1),
                "locations_with_rain": len([loc for loc in comparisons if "rain" in loc["weather"]["condition"].lower()]),
                "warmest_location": max(comparisons, key=lambda x: x["weather"]["temperature"]),
                "coolest_location": min(comparisons, key=lambda x: x["weather"]["temperature"])
            },
            "last_updated": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing locations: {e}")
        raise HTTPException(status_code=500, detail=f"Error comparing locations: {str(e)}")

@router.get("/historical",
            summary="Get Historical Weather",
            description="Get historical weather data for a location (mock data)")
async def historical_weather(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    days_back: int = Query(7, ge=1, le=30, description="Days of historical data")
):
    """Get historical weather data (mock implementation)"""
    
    try:
        # Generate mock historical data
        historical_data = []
        base_weather = find_nearest_mock_weather(lat, lon)
        base_temp = base_weather.get("temp_c", 25)
        
        for i in range(days_back, 0, -1):
            date = datetime.now() - timedelta(days=i)
            
            # Add variation to simulate historical data
            temp_variation = random.uniform(-5, 5)
            temp = base_temp + temp_variation
            
            conditions = ["clear sky", "partly cloudy", "cloudy", "light rain", "overcast"]
            condition = random.choice(conditions)
            
            historical_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "temperature_avg": round(temp, 1),
                "temperature_max": round(temp + random.uniform(2, 8), 1),
                "temperature_min": round(temp - random.uniform(2, 8), 1),
                "condition": condition,
                "condition_icon": get_weather_icon(condition),
                "humidity": random.randint(40, 90),
                "precipitation_mm": round(random.uniform(0, 15), 1) if "rain" in condition else 0,
                "wind_speed_kph": round(random.uniform(5, 30), 1)
            })
        
        # Calculate statistics
        temperatures = [day["temperature_avg"] for day in historical_data]
        precipitations = [day["precipitation_mm"] for day in historical_data]
        
        return {
            "success": True,
            "location": {
                "lat": lat,
                "lon": lon,
                "city": base_weather.get("city", "Unknown"),
                "country": base_weather.get("country", "Unknown")
            },
            "historical_data": historical_data,
            "period": {
                "start_date": historical_data[0]["date"],
                "end_date": historical_data[-1]["date"],
                "total_days": len(historical_data)
            },
            "statistics": {
                "avg_temperature": round(sum(temperatures) / len(temperatures), 1),
                "max_temperature": max(temperatures),
                "min_temperature": min(temperatures),
                "total_precipitation": round(sum(precipitations), 1),
                "rainy_days": len([day for day in historical_data if day["precipitation_mm"] > 0])
            },
            "last_updated": datetime.now().isoformat(),
            "data_source": "Mock Historical Data"
        }
        
    except Exception as e:
        logger.error(f"Error getting historical weather: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting historical weather: {str(e)}")

@router.get("/health",
            summary="Weather Service Health",
            description="Check weather service health and capabilities")
async def weather_service_health():
    """Weather service health check"""
    
    api_key_configured = bool(get_openweather_api_key() and get_openweather_api_key() != "your_api_key_here")
    
    return {
        "service": "weather",
        "status": "healthy",
        "features": {
            "current_weather": True,
            "weather_forecast": True,
            "weather_alerts": True,
            "travel_conditions": True,
            "location_comparison": True,
            "historical_data": True,
            "travel_recommendations": True,
            "caching": True
        },
        "external_services": {
            "openweathermap_api": "configured" if api_key_configured else "using_mock_data",
            "http_client": "available" if HTTP_CLIENT_AVAILABLE else "mock_mode"
        },
        "capabilities": {
            "supported_locations": "worldwide",
            "forecast_days": "up to 14 days",
            "historical_days": "up to 30 days",
            "location_comparison": "up to 10 locations",
            "alert_types": ["severe_weather", "extreme_heat", "extreme_cold", "high_wind"],
            "travel_activities": ["sightseeing", "hiking", "beach", "photography", "shopping"]
        },
        "mock_cities": len(MOCK_WEATHER_DATA),
        "cache_entries": len(CACHE_STORAGE),
        "version": "2.0.0"
    }
