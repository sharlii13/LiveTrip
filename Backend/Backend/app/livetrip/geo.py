"""Places search, live weather, distances and travel-time estimates."""
import asyncio
import math
import re
import time
from datetime import date
from typing import Dict, List, Optional, Tuple

import aiohttp
import httpx
from fastapi import HTTPException

# Google place types -> planner categories (the planner's UserPreferences knows these names)
_TYPE_CATEGORY = [
    ({"museum", "art_gallery"}, "museum"),
    ({"park", "garden", "city_park", "zoo", "botanical_garden", "dog_park"}, "park"),
    ({"beach", "natural_feature", "hiking_area", "national_park", "lake", "waterfall", "campground"}, "nature"),
    ({"hindu_temple", "church", "mosque", "synagogue", "place_of_worship", "buddhist_temple"}, "religious"),
    ({"historical_landmark", "monument", "historical_place", "castle", "fortress"}, "history"),
    ({"shopping_mall", "market", "store", "clothing_store", "department_store"}, "shopping"),
    ({"restaurant", "cafe", "food", "bakery", "meal_takeaway", "vegetarian_restaurant", "coffee_shop"}, "food"),
    ({"night_club", "bar", "pub", "amusement_park", "movie_theater", "bowling_alley", "casino"}, "entertainment"),
    ({"lodging", "hotel", "hostel", "resort_hotel", "guest_house", "bed_and_breakfast"}, "lodging"),
]
OUTDOOR_CATEGORIES = {"park", "nature", "history", "fort", "adventure"}
VISIT_MINUTES = {"museum": 90, "park": 60, "nature": 120, "religious": 45, "history": 75, "shopping": 90,
                 "food": 60, "entertainment": 120, "culture": 75, "lodging": 0}
SPEED_KMH = {"walking": 4.5, "bicycle": 14, "public-transport": 20, "transit": 20, "train": 30, "driving": 25, "car": 25}
ROAD_FACTOR = 1.3  # straight line -> road distance


SERVICE_TYPES = {"tour_agency", "travel_agency", "tourist_information_center", "taxi_service",
                 "transportation_service", "real_estate_agency", "car_rental"}
SERVICE_NAME = re.compile(r"^things to do\b|sightseeing (tour|package)|\btours? (and|&) travels?\b|\btour packages?\b|"
                          r"\btours?$|\btours? (company|operator|agency)\b|\bexcursions?$", re.IGNORECASE)


def is_service(types: List[str], name: str) -> bool:
    """Tour operators, taxis and info desks show up in 'attractions' searches but are not places to visit."""
    return bool(SERVICE_TYPES & set(types or [])) or bool(SERVICE_NAME.search(name or ""))


def categorize(types: List[str]) -> str:
    found = set(types or [])
    for type_set, category in _TYPE_CATEGORY:
        if found & type_set:
            return category
    return "culture"


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def road_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    # shortcut: road distance is straight-line x1.3 while the Routes API needs billing; upgrade by calling computeRouteMatrix
    return haversine_km(a, b) * ROAD_FACTOR


def travel_minutes(a: Tuple[float, float], b: Tuple[float, float], mode: str = "driving") -> int:
    km = road_km(a, b)
    if km < 0.05:
        return 0
    return max(5, round(km / SPEED_KMH.get(mode, 25) * 60))


QUOTA_MESSAGE = ("Google Places has hit this API key's daily limit. Enable billing on the Google Cloud "
                 "project (it includes a free monthly allowance) or try again after the quota resets.")
_SEARCH_TTL_S = 6 * 3600
# shortcut: in-process cache (lost on restart, not shared between workers); move to Redis if you run several workers
_search_cache: Dict[Tuple, Tuple[float, "asyncio.Task"]] = {}


async def search_places(query: str, near: Optional[Tuple[float, float]] = None, limit: int = 20) -> List[Dict]:
    """Google Places API (New) text search, as plain dicts, cached for a few hours.
    Points are rounded to ~1 km so nearby lookups (e.g. meal stops) share one Google call."""
    near = (round(near[0], 2), round(near[1], 2)) if near else None
    key = (query.strip().lower(), near)
    hit = _search_cache.get(key)
    if hit and hit[0] > time.monotonic():
        task = hit[1]
    else:
        task = asyncio.ensure_future(_text_search_any(query, near))
        _search_cache[key] = (time.monotonic() + _SEARCH_TTL_S, task)
    try:
        return [dict(p) for p in (await asyncio.shield(task))[:limit]]  # copies: callers may annotate them
    except Exception:
        _search_cache.pop(key, None)  # never cache failures
        raise


GOOGLE_RETRY_AFTER_S = 30 * 60
_google_down_until = 0.0


async def _text_search_any(query: str, near: Optional[Tuple[float, float]]) -> List[Dict]:
    """Google first; when it is out of quota or has no key, OpenStreetMap (and skip Google for a while)."""
    global _google_down_until
    if time.monotonic() >= _google_down_until:
        try:
            return await _google_text_search(query, near)
        except HTTPException as e:
            if e.status_code not in (429, 503):
                raise
            # quota or a missing key lasts: pause Google for a while; a network blip only for a minute
            lasting = e.status_code == 429 or "KEY" in str(e.detail).upper()
            _google_down_until = time.monotonic() + (GOOGLE_RETRY_AFTER_S if lasting else 60)
    from . import osm
    return await osm.search(query, near)


def google_available() -> bool:
    return time.monotonic() >= _google_down_until


async def _google_text_search(query: str, near: Optional[Tuple[float, float]]) -> List[Dict]:
    from app.rootplan.services.google_places import GooglePlacesService
    try:
        service = GooglePlacesService()
        places = await service.text_search(query, near)
    except ValueError as e:
        if "quota" in str(e).lower():
            raise HTTPException(status_code=429, detail=QUOTA_MESSAGE)
        raise HTTPException(status_code=503, detail=str(e))
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
        # network trouble reaching Google counts as "unavailable", so the open-data fallback takes over
        raise HTTPException(status_code=503, detail=f"Google Places unreachable ({e.__class__.__name__})")
    out = []
    for p in places:
        if is_service(p.types, p.name):
            continue
        category = categorize(p.types)
        out.append({
            "name": p.name, "place_id": p.place_id, "address": p.formatted_address,
            "lat": p.lat, "lng": p.lng, "rating": p.rating, "rating_count": p.user_ratings_total,
            "types": p.types, "category": category, "outdoor": category in OUTDOOR_CATEGORIES,
            "hours": (p.opening_hours or {}).get("weekday_text", []), "source": "google",
        })
    return out


async def geocode(place: str) -> Tuple[float, float]:
    results = await search_places(place, limit=1)
    if not results:
        raise HTTPException(status_code=404, detail=f"Could not find '{place}'")
    return results[0]["lat"], results[0]["lng"]


# WMO weather codes used by Open-Meteo
_WMO = {0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "fog",
        51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
        66: "freezing rain", 67: "freezing rain", 71: "light snow", 73: "snow", 75: "heavy snow",
        80: "rain showers", 81: "rain showers", 82: "violent rain showers", 95: "thunderstorm",
        96: "thunderstorm with hail", 99: "thunderstorm with hail"}
WET_CODES = {51, 53, 55, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}


async def weather(lat: float, lng: float) -> Dict:
    """Current conditions and 16-day forecast from Open-Meteo (free, no API key)."""
    params = {
        "latitude": lat, "longitude": lng, "timezone": "auto", "forecast_days": 16,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Weather service unavailable: {e}")
    cur, daily = data.get("current", {}), data.get("daily", {})
    days = {}
    for i, d in enumerate(daily.get("time", [])):
        code = daily["weather_code"][i]
        days[d] = {
            "date": d, "condition": _WMO.get(code, "unknown"), "code": code,
            "temp_max": daily["temperature_2m_max"][i], "temp_min": daily["temperature_2m_min"][i],
            "precipitation_probability": daily["precipitation_probability_max"][i] or 0,
            "wet": code in WET_CODES or (daily["precipitation_probability_max"][i] or 0) >= 60,
        }
    return {
        "source": "open-meteo",
        "current": {
            "temperature": cur.get("temperature_2m"), "humidity": cur.get("relative_humidity_2m"),
            "wind_speed": cur.get("wind_speed_10m"), "precipitation": cur.get("precipitation"),
            "condition": _WMO.get(cur.get("weather_code"), "unknown"), "timestamp": cur.get("time"),
        },
        "days": days,
    }


def hhmm_to_min(t: str) -> int:
    h, m = t.split(":")[:2]
    return int(h) * 60 + int(m)


def min_to_hhmm(m: int) -> str:
    m = max(0, min(m, 23 * 60 + 59))
    return f"{m // 60:02d}:{m % 60:02d}"


def today() -> str:
    return date.today().isoformat()
