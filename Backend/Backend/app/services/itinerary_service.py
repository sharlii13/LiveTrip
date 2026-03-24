# services/itinerary_service.py
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
from .external_apis import weather_service, event_service, maps_service

class GreedyItineraryPlanner:
    def __init__(self, weights=(0.4, 0.3, 0.2, 0.1)):
        self.w1, self.w2, self.w3, self.w4 = weights

    def calculate_score(self, attraction):
        """
        Score = w1*rating - w2*distance - w3*traffic + w4*weather_match
        """
        return (
            self.w1 * attraction.get("rating", 0)
            - self.w2 * attraction.get("distance", 0)
            - self.w3 * attraction.get("traffic", 0)
            + self.w4 * attraction.get("weather_ok", 0)
        )

    def plan_itinerary(self, attractions: list, top_k: int = 5):
        scored = [(a, self.calculate_score(a)) for a in attractions]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [a for a, s in scored[:top_k]]


class ItineraryService:
    def __init__(self):
        self.templates_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'itinerary_templates.json')
        self.templates = self.load_templates()
        self.planner = GreedyItineraryPlanner()

    def load_templates(self) -> Dict:
        try:
            with open(self.templates_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return self.get_default_templates()

    def get_default_templates(self) -> Dict:
        return {
            "default": {
                "name": "Any City",
                "default_days": 3,
                "templates": {
                    "happy": {
                        "day_1": {
                            "morning": [{"time": "09:00", "activity": "Explore City Center", "location": "Downtown", "duration": "3 hours"}],
                            "afternoon": [{"time": "14:00", "activity": "Local Market Visit", "location": "Main Market", "duration": "2 hours"}],
                            "evening": [{"time": "18:00", "activity": "Sunset Viewpoint", "location": "Best Viewpoint", "duration": "2 hours"}]
                        }
                    }
                }
            }
        }

    async def generate_enhanced_itinerary(self, destination: str, start_date: datetime,
                                          end_date: datetime, mood: str = "happy",
                                          preferences: Dict = None) -> Dict:
        """Generate enhanced itinerary with API data + template + greedy planner"""
        days = (end_date - start_date).days + 1
        template = self.get_template_for_destination(destination.lower().replace(" ", "").replace(",", ""), mood)
        base_itinerary = self.generate_base_itinerary(template, days, destination, start_date)

        # Get API-enhanced data
        enhanced_itinerary = await self.enhance_with_api_data(base_itinerary, destination)

        # Distribute top attractions across days
        top_attractions = enhanced_itinerary.get("recommended_places", [])
        top_attractions = self.generate_greedy_itinerary(top_attractions, top_k=len(top_attractions))
        self.assign_attractions_to_days(enhanced_itinerary, top_attractions)

        return enhanced_itinerary

    def generate_greedy_itinerary(self, attractions: List[Dict], top_k: int = 5) -> List[Dict]:
        return self.planner.plan_itinerary(attractions, top_k)

    def assign_attractions_to_days(self, itinerary: Dict, attractions: List[Dict]):
        """Distribute attractions into morning/afternoon/evening slots"""
        day_keys = sorted([k for k in itinerary.keys() if k.startswith("day_")])
        slots = ["morning", "afternoon", "evening"]
        slot_index = 0
        day_index = 0

        for attraction in attractions:
            day_key = day_keys[day_index]
            slot = slots[slot_index]
            activity_entry = {
                "time": ["09:00", "14:00", "18:00"][slot_index],
                "activity": attraction.get("name"),
                "location": attraction.get("vicinity", "Unknown"),
                "duration": "2 hours",
                "type": "sightseeing",
                "description": f"Recommended based on rating {attraction.get('rating')}"
            }
            if slot not in itinerary[day_key]:
                itinerary[day_key][slot] = []
            itinerary[day_key][slot].append(activity_entry)

            # Move to next slot/day
            slot_index += 1
            if slot_index >= len(slots):
                slot_index = 0
                day_index += 1
                if day_index >= len(day_keys):
                    day_index = 0

    # Other helper methods remain unchanged
    def get_template_for_destination(self, destination_key: str, mood: str) -> Dict:
        if destination_key in self.templates:
            dest_template = self.templates[destination_key]
            if mood in dest_template["templates"]:
                return dest_template["templates"][mood]
        for key in self.templates:
            if destination_key in key or key in destination_key:
                dest_template = self.templates[key]
                if mood in dest_template["templates"]:
                    return dest_template["templates"][mood]
                return dest_template["templates"][list(dest_template["templates"].keys())[0]]
        return self.get_default_templates()["default"]["templates"]["happy"]

    def generate_base_itinerary(self, template: Dict, days: int, destination: str, start_date: datetime) -> Dict:
        itinerary = {}
        for day in range(1, days + 1):
            current_date = start_date + timedelta(days=day - 1)
            day_key = f"day_{day}"
            if day_key in template:
                day_template = template[day_key]
            else:
                available_days = [k for k in template.keys() if k.startswith("day_")]
                day_template = template[available_days[(day - 1) % len(available_days)]] if available_days else {}
            itinerary[day_key] = {"date": current_date.strftime("%Y-%m-%d"), "day_name": current_date.strftime("%A"), **day_template, "weather": {}, "events": []}
        return itinerary

    async def enhance_with_api_data(self, base_itinerary: Dict, destination: str) -> Dict:
        enhanced = base_itinerary.copy()
        try:
            weather_data = await weather_service.get_current_weather(destination)
            enhanced["weather_status"] = "success" if weather_data else "failed"
            enhanced["general_weather"] = {"temperature": weather_data.get("main", {}).get("temp"), "description": weather_data.get("weather", [{}])[0].get("description")} if weather_data else {}
        except Exception:
            enhanced["weather_status"] = "failed"
        try:
            events_data = await event_service.get_events(destination)
            enhanced["events_status"] = "success" if events_data else "failed"
            enhanced["local_events"] = events_data.get("events", [])[:5] if events_data else []
        except Exception:
            enhanced["events_status"] = "failed"
            enhanced["local_events"] = []
        try:
            places_data = await maps_service.get_places(destination, "tourist_attraction")
            enhanced["places_status"] = "success" if places_data else "failed"
            enhanced["recommended_places"] = [{"name": p.get("name"), "rating": p.get("rating"), "vicinity": p.get("vicinity")} for p in places_data.get("results", [])[:8]] if places_data else []
        except Exception:
            enhanced["places_status"] = "failed"
            enhanced["recommended_places"] = []
        return enhanced


# Service instance
itinerary_service = ItineraryService()
