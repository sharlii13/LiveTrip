import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from ..schemas.itinerary import Location, Activity, ActivityType
import json


class EventsService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.eventbriteapi.com/v3"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    def _map_to_activity_type(self, category: str, subcategory: str = "") -> ActivityType:
        """Map Eventbrite categories to our activity types"""
        category = category.lower()
        subcategory = subcategory.lower()
        
        if any(word in category for word in ["music", "performing", "arts", "entertainment"]):
            return ActivityType.ENTERTAINMENT
        elif any(word in category for word in ["food", "drink", "culinary"]):
            return ActivityType.RESTAURANT
        elif any(word in category for word in ["business", "professional"]):
            return ActivityType.CULTURAL
        elif any(word in category for word in ["sports", "fitness", "outdoor"]):
            return ActivityType.ADVENTURE
        elif any(word in category for word in ["education", "science", "tech"]):
            return ActivityType.CULTURAL
        elif any(word in category for word in ["charity", "community"]):
            return ActivityType.CULTURAL
        else:
            return ActivityType.ENTERTAINMENT

    async def search_events(self, location: Location, date_range: tuple = None, 
                           category: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for events in a specific location"""
        session = await self._get_session()
        
        params = {
            "location.latitude": location.latitude,
            "location.longitude": location.longitude,
            "location.within": "25km",  # Search within 25km radius
            "expand": "venue,category,subcategory,organizer",
            "sort_by": "date",
            "page_size": min(limit, 50)  # Eventbrite max is 50 per page
        }
        
        if date_range:
            start_date, end_date = date_range
            params["start_date.range_start"] = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            params["start_date.range_end"] = end_date.strftime("%Y-%m-%dT%H:%M:%S")
        
        if category:
            params["categories"] = category

        async with session.get(f"{self.base_url}/events/search/", params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("events", [])
            else:
                raise Exception(f"Events API error: {response.status}")

    async def get_events_for_itinerary(self, location: Location, start_date: datetime, 
                                     end_date: datetime, preferences: Dict[str, Any]) -> List[Activity]:
        """Get events that can be integrated into an itinerary"""
        events = await self.search_events(
            location=location,
            date_range=(start_date, end_date),
            limit=100
        )
        
        activities = []
        user_interests = preferences.get("interests", [])
        budget_range = preferences.get("budget_range", "medium")
        
        for event in events:
            # Filter based on user preferences
            if not self._matches_user_preferences(event, user_interests, budget_range):
                continue
            
            venue = event.get("venue")
            if not venue:
                continue
            
            # Extract location information
            event_location = Location(
                latitude=float(venue.get("latitude", 0)),
                longitude=float(venue.get("longitude", 0)),
                address=venue.get("address", {}).get("localized_address_display", ""),
                city=location.city,  # Use the search location's city
                country=location.country
            )
            
            # Calculate estimated duration
            start_time = datetime.fromisoformat(event["start"]["utc"].replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(event["end"]["utc"].replace("Z", "+00:00"))
            duration = int((end_time - start_time).total_seconds() / 60)
            
            # Determine if it's weather dependent
            venue_name = venue.get("name", "").lower()
            is_outdoor = any(word in venue_name for word in ["park", "outdoor", "stadium", "field", "beach"])
            
            activity = Activity(
                id=f"event_{event['id']}",
                name=event["name"]["text"],
                description=event.get("description", {}).get("text", "")[:500],  # Limit description
                location=event_location,
                activity_type=self._map_to_activity_type(
                    event.get("category", {}).get("name", ""),
                    event.get("subcategory", {}).get("name", "")
                ),
                estimated_duration=max(60, min(duration, 480)),  # Between 1-8 hours
                cost=self._extract_cost(event),
                rating=None,  # Eventbrite doesn't provide ratings
                weather_dependent=is_outdoor,
                indoor_alternative=None,
                opening_hours=None,
                booking_required=not event.get("is_free", False),
                difficulty_level="easy",
                accessibility_info=None
            )
            
            activities.append(activity)
        
        return activities

    async def get_event_details(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific event"""
        session = await self._get_session()
        
        params = {
            "expand": "venue,organizer,ticket_availability,category,subcategory"
        }

        async with session.get(f"{self.base_url}/events/{event_id}/", params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None

    async def get_trending_events(self, location: Location, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Get trending/popular events in the area"""
        end_date = datetime.now() + timedelta(days=days_ahead)
        
        events = await self.search_events(
            location=location,
            date_range=(datetime.now(), end_date),
            limit=50
        )
        
        # Sort by popularity (number of attendees going)
        trending = sorted(
            events, 
            key=lambda e: int(e.get("capacity", 0)) - int(e.get("capacity_is_custom", 0)),
            reverse=True
        )
        
        return trending[:20]  # Return top 20 trending events

    async def get_free_events(self, location: Location, date_range: tuple = None) -> List[Dict[str, Any]]:
        """Get free events in the area"""
        events = await self.search_events(location, date_range, limit=100)
        return [event for event in events if event.get("is_free", False)]

    async def get_events_by_category(self, location: Location, category_name: str, 
                                   date_range: tuple = None) -> List[Dict[str, Any]]:
        """Get events by specific category"""
        # First get category ID
        categories = await self.get_categories()
        category_id = None
        
        for cat in categories:
            if category_name.lower() in cat.get("name", "").lower():
                category_id = cat.get("id")
                break
        
        if not category_id:
            return []
        
        return await self.search_events(location, date_range, category_id, limit=50)

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all available event categories"""
        session = await self._get_session()

        async with session.get(f"{self.base_url}/categories/") as response:
            if response.status == 200:
                data = await response.json()
                return data.get("categories", [])
            else:
                return []

    async def get_organizer_events(self, organizer_id: str) -> List[Dict[str, Any]]:
        """Get all events by a specific organizer"""
        session = await self._get_session()

        async with session.get(f"{self.base_url}/organizers/{organizer_id}/events/") as response:
            if response.status == 200:
                data = await response.json()
                return data.get("events", [])
            else:
                return []

    def _matches_user_preferences(self, event: Dict[str, Any], interests: List[str], 
                                 budget_range: str) -> bool:
        """Check if event matches user preferences"""
        # Check budget
        if not self._matches_budget(event, budget_range):
            return False
        
        # Check interests
        if interests:
            event_category = event.get("category", {}).get("name", "").lower()
            event_subcategory = event.get("subcategory", {}).get("name", "").lower()
            event_name = event.get("name", {}).get("text", "").lower()
            event_description = event.get("description", {}).get("text", "").lower()
            
            # Check if any interest matches
            matches_interest = False
            for interest in interests:
                interest_lower = interest.lower()
                if (interest_lower in event_category or 
                    interest_lower in event_subcategory or 
                    interest_lower in event_name or 
                    interest_lower in event_description):
                    matches_interest = True
                    break
            
            if not matches_interest:
                return False
        
        return True

    def _matches_budget(self, event: Dict[str, Any], budget_range: str) -> bool:
        """Check if event matches budget range"""
        if event.get("is_free", False):
            return True  # Free events match all budgets
        
        # For paid events, we'd need to check ticket prices
        # Since Eventbrite API requires additional calls for ticket info,
        # we'll assume paid events match medium and high budgets
        return budget_range in ["medium", "high"]

    def _extract_cost(self, event: Dict[str, Any]) -> Optional[float]:
        """Extract cost information from event"""
        if event.get("is_free", False):
            return 0.0
        
        # For paid events, we'd need to make additional API calls to get ticket prices
        # For now, return None to indicate unknown cost
        return None

    async def get_venue_info(self, venue_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed venue information"""
        session = await self._get_session()

        async with session.get(f"{self.base_url}/venues/{venue_id}/") as response:
            if response.status == 200:
                return await response.json()
            else:
                return None

    async def suggest_events_for_weather(self, location: Location, weather_condition: str, 
                                       date: datetime) -> List[Activity]:
        """Suggest events based on weather conditions"""
        end_date = date + timedelta(days=1)
        events = await self.search_events(location, (date, end_date), limit=50)
        
        suitable_events = []
        
        for event in events:
            venue = event.get("venue", {})
            venue_name = venue.get("name", "").lower()
            
            # Determine if event is suitable for weather
            is_outdoor = any(word in venue_name for word in ["park", "outdoor", "stadium", "field", "beach"])
            
            if weather_condition in ["rainy", "stormy"] and is_outdoor:
                continue  # Skip outdoor events in bad weather
            
            if weather_condition in ["sunny", "clear"] and not is_outdoor:
                # Prefer outdoor events in good weather, but include indoor too
                pass
            
            # Convert to Activity object
            event_location = Location(
                latitude=float(venue.get("latitude", 0)),
                longitude=float(venue.get("longitude", 0)),
                address=venue.get("address", {}).get("localized_address_display", ""),
                city=location.city,
                country=location.country
            )
            
            start_time = datetime.fromisoformat(event["start"]["utc"].replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(event["end"]["utc"].replace("Z", "+00:00"))
            duration = int((end_time - start_time).total_seconds() / 60)
            
            activity = Activity(
                id=f"event_{event['id']}",
                name=event["name"]["text"],
                description=event.get("description", {}).get("text", "")[:500],
                location=event_location,
                activity_type=self._map_to_activity_type(
                    event.get("category", {}).get("name", ""),
                    event.get("subcategory", {}).get("name", "")
                ),
                estimated_duration=max(60, min(duration, 480)),
                cost=self._extract_cost(event),
                rating=None,
                weather_dependent=is_outdoor,
                indoor_alternative=None,
                opening_hours=None,
                booking_required=not event.get("is_free", False),
                difficulty_level="easy"
            )
            
            suitable_events.append(activity)
        
        return suitable_events[:10]  # Return top 10 suitable events