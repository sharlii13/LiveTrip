"""
Greedy POI selector for the itinerary planning system.
Implements intelligent scoring algorithm to select the best POIs for a one-day itinerary.
"""
import math
import logging
from typing import List, Dict, Optional
from collections import Counter
from fastapi import HTTPException

from app.rootplan.models.schemas import (
    PlanRequest, RawPOI, ScoredPOI, ScoringWeights,
    get_category_duration, time_str_to_minutes
)
from app.rootplan.utils.mock_data import get_mock_pois, get_weather_compatibility
from app.rootplan.utils.cache_utils import get_cached, set_cached, generate_poi_cache_key
from app.rootplan.services.google_places import get_places_service, PlaceDetails
from app.rootplan.services.google_distance import get_distance_service, TravelMode


logger = logging.getLogger(__name__)


class GreedyPOISelector:
    """Greedy algorithm for selecting optimal POIs for a day trip."""
    
    def __init__(self, weights: Optional[ScoringWeights] = None):
        """
        Initialize the selector with scoring weights.
        
        Args:
            weights: Scoring weights for the algorithm
        """
        self.weights = weights or ScoringWeights()
        
    def calculate_distance_km(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two coordinates using Haversine formula.
        
        Args:
            lat1, lng1: First location coordinates
            lat2, lng2: Second location coordinates
            
        Returns:
            Distance in kilometers
        """
        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        # Haversine formula
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        # Earth radius in kilometers
        earth_radius = 6371
        return earth_radius * c
    
    def calculate_travel_time(self, distance_km: float, mode: str = "driving") -> int:
        """
        Calculate travel time based on distance and transportation mode.
        
        Args:
            distance_km: Distance in kilometers
            mode: Transportation mode
            
        Returns:
            Travel time in minutes
        """
        # Average speeds (km/h) for different modes in city conditions
        speed_mapping = {
            "driving": 25,      # City driving with traffic
            "walking": 5,       # Walking speed
            "bicycling": 15,    # Cycling speed
            "transit": 20       # Public transport
        }
        
        avg_speed = speed_mapping.get(mode, 25)
        travel_time_hours = distance_km / avg_speed
        travel_time_minutes = int(travel_time_hours * 60)
        
        # Minimum travel time for very short distances
        return max(travel_time_minutes, 3)
    
    def score_poi(self, poi: RawPOI, hotel_location: Dict[str, float], 
                  selected_categories: List[str], request: PlanRequest) -> float:
        """
        Calculate score for a POI using the weighted scoring algorithm.
        
        Args:
            poi: POI to score
            hotel_location: Hotel coordinates {lat, lng}
            selected_categories: List of already selected categories
            request: Planning request
            
        Returns:
            POI score (higher is better)
        """
        # Component 1: Rating score (0-5 normalized to 0-1)
        rating_score = poi.rating / 5.0
        
        # Component 2: Reviews score (log-based to handle wide range)
        reviews_score = math.log(1 + poi.reviews) / math.log(100000)  # Normalize against large review counts
        reviews_score = min(reviews_score, 1.0)  # Cap at 1.0
        
        # Component 3: Weather compatibility
        weather_score = get_weather_compatibility(poi.category)
        
        # Component 4: Travel penalty (distance from hotel)
        distance_km = self.calculate_distance_km(
            hotel_location["lat"], hotel_location["lng"],
            poi.lat, poi.lng
        )
        # Normalize distance penalty (0-50km range)
        travel_penalty = min(distance_km / 50.0, 1.0)
        
        # Component 5: Category repetition penalty
        category_count = selected_categories.count(poi.category)
        category_repetition = min(category_count * 0.3, 1.0)  # Penalty increases with repetition
        
        # Calculate weighted score
        score = (
            self.weights.rating * rating_score +
            self.weights.reviews * reviews_score +
            self.weights.weather * weather_score -
            self.weights.travel_penalty * travel_penalty -
            self.weights.category_repetition * category_repetition
        )
        
        logger.debug(f"POI: {poi.name}, Score: {score:.3f} "
                    f"(rating: {rating_score:.2f}, reviews: {reviews_score:.2f}, "
                    f"weather: {weather_score:.2f}, travel: {travel_penalty:.2f}, "
                    f"category: {category_repetition:.2f})")
        
        return score
    
    def is_poi_feasible(self, poi: RawPOI, current_time_min: int, 
                       end_time_min: int, travel_time_min: int) -> bool:
        """
        Check if POI can be visited within the time constraints.
        
        Args:
            poi: POI to check
            current_time_min: Current time in minutes from midnight
            end_time_min: End time in minutes from midnight
            travel_time_min: Travel time to reach POI
            
        Returns:
            True if POI is feasible to visit
        """
        # Calculate arrival time
        arrival_time = current_time_min + travel_time_min
        
        # Get POI's opening/closing times
        open_time_min = time_str_to_minutes(poi.open_time)
        close_time_min = time_str_to_minutes(poi.close_time)
        
        # Ensure arrival is after opening time
        actual_arrival = max(arrival_time, open_time_min)
        
        # Get visit duration (use category default if not specified)
        visit_duration = poi.duration_min or get_category_duration(poi.category)
        
        # Calculate departure time
        departure_time = actual_arrival + visit_duration
        
        # Check constraints
        if departure_time > close_time_min:
            return False  # Would exceed POI closing time
        
        if departure_time > end_time_min:
            return False  # Would exceed day's end time
        
        return True
    
    async def get_pois_for_city(self, city: str) -> List[RawPOI]:
        """
        Get POIs for a city from Google Places API or cache.
        
        Args:
            city: City name
            
        Returns:
            List of available POIs
        """
        # Try to get from cache first
        cache_key = generate_poi_cache_key(city)
        cached_pois = await get_cached(cache_key)
        
        if cached_pois:
            logger.info(f"Using cached POIs for {city}")
            return [RawPOI(**poi) for poi in cached_pois]
        
        # Get POIs from Google Places API
        logger.info(f"Fetching POIs for {city} from Google Places API")
        places_service = await get_places_service()
        
        try:
            # First, get city coordinates
            city_coords = await places_service.geocode_city(city)
            
            # Search for various types of POIs
            all_places = []
            search_queries = [
                f"tourist attractions in {city}",
                f"museums in {city}",
                f"parks in {city}",
                f"restaurants in {city}",
                f"shopping in {city}",
                f"temples in {city}",
                f"historical sites in {city}"
            ]
            
            for query in search_queries:
                try:
                    places = await places_service.search_places(
                        query=query,
                        location=city_coords,
                        limit=10
                    )
                    all_places.extend(places)
                except Exception as e:
                    logger.warning(f"Failed to search for '{query}': {e}")
            
            # Remove duplicates based on place_id
            unique_places = {}
            for place in all_places:
                if place.place_id not in unique_places:
                    unique_places[place.place_id] = place
            
            # Convert to RawPOI format
            pois = []
            for place in unique_places.values():
                try:
                    poi = self._convert_place_to_poi(place)
                    if poi:
                        pois.append(poi)
                except Exception as e:
                    logger.warning(f"Failed to convert place {place.name}: {e}")
            
            logger.info(f"Found {len(pois)} POIs for {city}")
            
        except Exception as e:
            logger.error(f"Error fetching POIs for {city}: {e}")
            # No fallback - require real API data only
            raise HTTPException(status_code=500, detail=f"Failed to fetch POIs for {city}: {e}. Real-time API required.")
        
        # Cache for future use
        poi_dicts = [poi.model_dump() for poi in pois]
        await set_cached(cache_key, poi_dicts, ttl=86400)  # Cache for 24 hours
        
        return pois
    
    def _convert_place_to_poi(self, place: PlaceDetails) -> Optional[RawPOI]:
        """
        Convert a Google Places PlaceDetails to RawPOI format.
        
        Args:
            place: PlaceDetails from Google Places API
            
        Returns:
            RawPOI object or None if conversion fails
        """
        try:
            # Map Google place types to our category system
            category = self._map_place_type_to_category(place.types)
            
            # Get opening hours (default if not available)
            open_time = "08:00"
            close_time = "18:00"
            
            if place.opening_hours and place.opening_hours.get("weekday_text"):
                # Try to extract hours from weekday_text
                # This is a simplified extraction - in production you'd want more robust parsing
                weekday_text = place.opening_hours["weekday_text"]
                if weekday_text:
                    first_day = weekday_text[0] if weekday_text else ""
                    if "–" in first_day or "-" in first_day:
                        # Extract time range
                        time_part = first_day.split(": ")[-1] if ": " in first_day else first_day
                        if "–" in time_part:
                            times = time_part.split("–")
                        elif "-" in time_part:
                            times = time_part.split("-")
                        else:
                            times = []
                        
                        if len(times) >= 2:
                            try:
                                # Simple time parsing - assumes format like "9:00 AM"
                                open_str = times[0].strip()
                                close_str = times[1].strip()
                                
                                # Convert to 24-hour format (simplified)
                                if "AM" in open_str or "PM" in open_str:
                                    open_time = self._parse_12hour_time(open_str)
                                if "AM" in close_str or "PM" in close_str:
                                    close_time = self._parse_12hour_time(close_str)
                            except:
                                pass  # Keep defaults
            
            # Create RawPOI
            return RawPOI(
                name=place.name,
                lat=place.lat,
                lng=place.lng,
                category=category,
                rating=place.rating,
                reviews=place.user_ratings_total,
                duration_min=get_category_duration(category),
                open_time=open_time,
                close_time=close_time,
                price_level=place.price_level or 2,
                address=place.formatted_address,
                website=place.website,
                phone=place.phone_number
            )
            
        except Exception as e:
            logger.error(f"Error converting place {place.name}: {e}")
            return None
    
    def _map_place_type_to_category(self, types: List[str]) -> str:
        """
        Map Google Place types to our category system.
        
        Args:
            types: List of Google Place types
            
        Returns:
            Mapped category string
        """
        # Priority mapping - check in order of preference
        type_mapping = {
            # High priority attractions
            "tourist_attraction": "historic",
            "museum": "museum",
            "amusement_park": "entertainment",
            "zoo": "nature",
            "aquarium": "nature",
            "park": "nature",
            "natural_feature": "nature",
            
            # Religious/Cultural
            "place_of_worship": "temple",
            "hindu_temple": "temple",
            "church": "temple",
            "mosque": "temple",
            "synagogue": "temple",
            "buddhist_temple": "temple",
            
            # Shopping/Commerce
            "shopping_mall": "shopping",
            "store": "shopping",
            "clothing_store": "shopping",
            "book_store": "shopping",
            
            # Food
            "restaurant": "food",
            "food": "food",
            "meal_takeaway": "food",
            "cafe": "food",
            "bakery": "food",
            
            # Entertainment
            "night_club": "entertainment",
            "bar": "entertainment",
            "movie_theater": "entertainment",
            "casino": "entertainment",
            
            # Cultural
            "art_gallery": "cultural",
            "library": "cultural",
            "university": "cultural",
            "school": "cultural",
        }
        
        # Check types in order and return first match
        for place_type in types:
            if place_type in type_mapping:
                return type_mapping[place_type]
        
        # Default fallback
        return "historic"
    
    def _parse_12hour_time(self, time_str: str) -> str:
        """
        Parse 12-hour time format to 24-hour format.
        
        Args:
            time_str: Time string like "9:00 AM" or "2:30 PM"
            
        Returns:
            24-hour format time string like "09:00" or "14:30"
        """
        try:
            import re
            # Extract time components
            match = re.match(r'(\d{1,2})(?::(\d{2}))? *(AM|PM)', time_str.upper())
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0
                period = match.group(3)
                
                # Convert to 24-hour format
                if period == "PM" and hour != 12:
                    hour += 12
                elif period == "AM" and hour == 12:
                    hour = 0
                
                return f"{hour:02d}:{minute:02d}"
        except:
            pass
        
        # Default fallback
        return "09:00" if "AM" in time_str.upper() else "18:00"
    
    async def select_best_pois(self, request: PlanRequest,
                              max_pois: int = 6) -> List[ScoredPOI]:
        """
        Select the best POIs for the itinerary using greedy algorithm.
        
        Args:
            request: Planning request
            max_pois: Maximum number of POIs to select (default: 6)
            
        Returns:
            List of selected POIs with scores
        """
        logger.info(f"Starting POI selection for {request.city}")
        
        # Get available POIs
        available_pois = await self.get_pois_for_city(request.city)
        logger.info(f"Found {len(available_pois)} POIs for {request.city}")
        
        # Convert time strings to minutes
        start_time_min = time_str_to_minutes(request.start_time)
        end_time_min = time_str_to_minutes(request.end_time)
        
        # Initialize selection
        selected_pois: List[ScoredPOI] = []
        selected_categories: List[str] = []
        current_time = start_time_min
        hotel_coords = {"lat": request.hotel.lat, "lng": request.hotel.lng}
        
        # Greedy selection loop
        for iteration in range(max_pois):
            logger.debug(f"Selection iteration {iteration + 1}")
            
            best_poi = None
            best_score = -float('inf')
            best_travel_time = 0
            
            # Evaluate all remaining POIs
            for poi in available_pois:
                if any(selected.poi.name == poi.name for selected in selected_pois):
                    continue  # Already selected
                
                # Calculate travel time from current location
                if selected_pois:
                    # Travel from last selected POI
                    last_poi = selected_pois[-1].poi
                    distance_km = self.calculate_distance_km(
                        last_poi.lat, last_poi.lng, poi.lat, poi.lng
                    )
                else:
                    # Travel from hotel
                    distance_km = self.calculate_distance_km(
                        hotel_coords["lat"], hotel_coords["lng"],
                        poi.lat, poi.lng
                    )
                
                travel_time = self.calculate_travel_time(distance_km, request.mode)
                
                # Check feasibility
                if not self.is_poi_feasible(poi, current_time, end_time_min, travel_time):
                    logger.debug(f"POI {poi.name} is not feasible at current time")
                    continue
                
                # Calculate score
                score = self.score_poi(poi, hotel_coords, selected_categories, request)
                
                # Update best if this is better
                if score > best_score:
                    best_score = score
                    best_poi = poi
                    best_travel_time = travel_time
            
            # Break if no feasible POI found
            if best_poi is None:
                logger.info(f"No more feasible POIs found after {len(selected_pois)} selections")
                break
            
            # Add best POI to selection
            scored_poi = ScoredPOI(
                poi=best_poi,
                score=best_score,
                travel_time_min=best_travel_time,
                feasible=True
            )
            selected_pois.append(scored_poi)
            selected_categories.append(best_poi.category)
            
            # Update current time
            arrival_time = current_time + best_travel_time
            open_time_min = time_str_to_minutes(best_poi.open_time)
            actual_arrival = max(arrival_time, open_time_min)
            visit_duration = best_poi.duration_min or get_category_duration(best_poi.category)
            current_time = actual_arrival + visit_duration
            
            logger.info(f"Selected POI {iteration + 1}: {best_poi.name} "
                       f"(score: {best_score:.3f}, category: {best_poi.category})")
        
        # Ensure we have at least 5 POIs if possible
        if len(selected_pois) < 5 and len(available_pois) >= 5:
            logger.warning(f"Only selected {len(selected_pois)} POIs, fewer than recommended minimum of 5")
        
        logger.info(f"Final selection: {len(selected_pois)} POIs")
        return selected_pois
    
    def get_category_distribution(self, selected_pois: List[ScoredPOI]) -> Dict[str, int]:
        """
        Get distribution of categories in selected POIs.
        
        Args:
            selected_pois: List of selected POIs
            
        Returns:
            Dictionary with category counts
        """
        categories = [poi.poi.category for poi in selected_pois]
        return dict(Counter(categories))


# Global selector instance
_selector_instance = None


def get_selector() -> GreedyPOISelector:
    """Get or create the global selector instance."""
    global _selector_instance
    if _selector_instance is None:
        _selector_instance = GreedyPOISelector()
    return _selector_instance


async def select_best_pois(request: PlanRequest, max_pois: int = 6) -> List[ScoredPOI]:
    """
    Select the best POIs for the given request.
    
    Args:
        request: Planning request
        max_pois: Maximum number of POIs to select
        
    Returns:
        List of selected POIs with scores
    """
    selector = get_selector()
    return await selector.select_best_pois(request, max_pois)