from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENWEATHER_API_KEY: str
    EVENTBRITE_API_KEY: str
    AVIATIONSTACK_API_KEY: str
    GOOGLE_MAPS_API_KEY: str
    ACCUWEATHER_API_KEY: str
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    OPENWEATHER_BASE: str = "https://api.openweathermap.org/data/2.5"
    EVENTBRITE_BASE: str = "https://www.eventbriteapi.com/v3"
    AVIATIONSTACK_BASE: str = "http://api.aviationstack.com/v1"
    GOOGLE_PLACES_BASE: str = "https://maps.googleapis.com/maps/api/place"

@lru_cache
def get_settings() -> Settings:
    return Settings()  # reads from environment/.env automatically
