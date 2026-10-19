"""
Multi-day POI scoring system that combines POI scores with user preference weights and distance penalties.
"""
import math
import logging
from typing import List, Dict, Tuple
from collections import Counter

from app.rootplan.models.multiday_schemas import (
    MultiDayPOI, Location, UserPreferences, PlanningConstraints,
    ScoredPOIForMultiDay, MultiDayPlanRequest
)


logger = logging.getLogger(__name__)


class MultiDayPOIScorer:
    """POI scoring system for multi-day itinerary planning."""
    
    def __init__(self):
        """Initialize the scorer."""
        self.haversine_cache = {}  # Cache for distance calculations
    
    def calculate_distance_km(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two coordinates using Haversine formula.
        Uses caching for performance optimization.
        
        Args:
            lat1, lng1: First location coordinates
            lat2, lng2: Second location coordinates
            
        Returns:
            Distance in kilometers
        """
        # Create cache key
        cache_key = (round(lat1, 6), round(lng1, 6), round(lat2, 6), round(lng2, 6))
        
        if cache_key in self.haversine_cache:
            return self.haversine_cache[cache_key]
        
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
        distance = earth_radius * c
        
        # Cache the result
        self.haversine_cache[cache_key] = distance
        
        return distance
    
    def calculate_preference_score(self, poi: MultiDayPOI, preferences: UserPreferences) -> float:
        """
        Calculate preference score based on user preferences for POI categories.
        
        Args:
            poi: POI to score
            preferences: User preferences
            
        Returns:
            Preference score (0.0 to 1.0)
        """
        return preferences.get_preference(poi.category)
    
    def calculate_distance_penalty(self, poi: MultiDayPOI, start_location: Location, 
                                  max_distance_km: float = 50) -> float:
        """
        Calculate distance penalty based on distance from start location.
        
        Args:
            poi: POI to evaluate
            start_location: Starting location
            max_distance_km: Maximum reasonable distance
            
        Returns:
            Distance penalty (0.0 to 1.0, where 0 is no penalty)
        """
        distance = self.calculate_distance_km(
            start_location.lat, start_location.lng,
            poi.lat, poi.lng
        )
        
        # Normalize distance penalty (0 to max_distance_km range)
        # Closer POIs get lower penalty
        penalty = min(distance / max_distance_km, 1.0)
        
        # Apply logarithmic scaling to reduce penalty impact for moderate distances
        penalty = math.log(1 + penalty) / math.log(2)  # Normalize to 0-1 range
        
        return penalty
    
    def calculate_category_diversity_bonus(self, poi: MultiDayPOI, 
                                         existing_categories: List[str]) -> float:
        """
        Calculate bonus for category diversity.
        
        Args:
            poi: POI to evaluate
            existing_categories: Categories already selected
            
        Returns:
            Diversity bonus (0.0 to 0.2)
        """
        if not existing_categories:
            return 0.1  # Small bonus for first POI
        
        category_counts = Counter(existing_categories)
        current_count = category_counts.get(poi.category, 0)
        
        # Bonus decreases with repetition
        if current_count == 0:
            return 0.2  # New category bonus
        elif current_count == 1:
            return 0.05  # Small bonus for second occurrence
        else:
            return 0.0  # No bonus for third+ occurrence
    
    def calculate_time_feasibility_score(self, poi: MultiDayPOI, available_hours: float) -> float:
        """
        Calculate score based on time feasibility.
        
        Args:
            poi: POI to evaluate
            available_hours: Available hours in the day
            
        Returns:
            Feasibility score (0.0 to 1.0)
        """
        if poi.duration > available_hours:
            return 0.0  # Cannot fit
        
        # Prefer POIs that utilize time well but don't dominate the day
        ideal_duration = available_hours * 0.2  # 20% of available time is ideal
        
        if poi.duration <= ideal_duration:
            return 1.0
        elif poi.duration <= available_hours * 0.5:  # Up to 50% is acceptable
            return 0.8
        else:  # More than 50% gets lower score
            return 0.5
    
    def calculate_opening_hours_compatibility(self, poi: MultiDayPOI, start_time: str) -> float:
        """
        Calculate compatibility with daily schedule based on opening hours.
        
        Args:
            poi: POI to evaluate
            start_time: Daily start time in HH:MM format
            
        Returns:
            Compatibility score (0.0 to 1.0)
        """
        from app.rootplan.models.multiday_schemas import time_str_to_minutes
        
        poi_open = time_str_to_minutes(poi.open)
        poi_close = time_str_to_minutes(poi.close)
        day_start = time_str_to_minutes(start_time)
        
        # Calculate available time window
        available_start = max(poi_open, day_start)
        available_duration = poi_close - available_start
        
        if available_duration <= 0:
            return 0.0  # No available time
        
        # Check if POI duration fits in available window
        if poi.duration * 60 > available_duration:  # Convert hours to minutes
            return 0.3  # Partial compatibility
        
        # Prefer POIs with longer availability windows
        total_possible = poi_close - poi_open
        availability_ratio = available_duration / total_possible
        
        return min(availability_ratio + 0.3, 1.0)
    
    async def score_pois(self, request: MultiDayPlanRequest) -> List[ScoredPOIForMultiDay]:
        """
        Score all POIs based on multiple factors.
        
        Args:
            request: Multi-day planning request
            
        Returns:
            List of scored POIs sorted by final score (descending)
        """
        logger.info(f"Scoring {len(request.poi_list)} POIs for multi-day planning")
        
        scored_pois = []
        existing_categories = []  # For diversity bonus calculation
        
        for poi in request.poi_list:
            # Calculate individual score components
            base_score = poi.score / 10.0  # Normalize to 0-1
            
            preference_score = self.calculate_preference_score(poi, request.user_preferences)
            
            distance_penalty = self.calculate_distance_penalty(
                poi, request.start_location, request.constraints.max_daily_distance_km
            )
            
            category_bonus = self.calculate_category_diversity_bonus(
                poi, existing_categories
            )
            
            time_feasibility = self.calculate_time_feasibility_score(
                poi, request.available_hours_per_day
            )
            
            opening_hours_compatibility = self.calculate_opening_hours_compatibility(
                poi, request.start_time
            )
            
            # Combine scores with weights
            final_score = (
                base_score * 0.3 +  # 30% base POI score
                preference_score * 0.35 +  # 35% user preferences
                category_bonus +  # Up to 20% category diversity bonus
                time_feasibility * 0.15 +  # 15% time feasibility
                opening_hours_compatibility * 0.2 -  # 20% opening hours compatibility
                distance_penalty * 0.25  # 25% distance penalty
            )
            
            # Ensure score is within valid range
            final_score = max(0.0, min(1.0, final_score))
            
            scored_poi = ScoredPOIForMultiDay(
                poi=poi,
                final_score=final_score,
                preference_score=preference_score,
                distance_penalty=distance_penalty,
                category_bonus=category_bonus
            )
            
            scored_pois.append(scored_poi)
            
            logger.debug(f"POI: {poi.name}, Final Score: {final_score:.3f} "
                        f"(base: {base_score:.2f}, pref: {preference_score:.2f}, "
                        f"dist_penalty: {distance_penalty:.2f}, bonus: {category_bonus:.2f})")
        
        # Sort by final score (descending)
        scored_pois.sort(key=lambda x: x.final_score, reverse=True)
        
        logger.info(f"POI scoring completed. Top POI: {scored_pois[0].poi.name} "
                   f"(score: {scored_pois[0].final_score:.3f})")
        
        return scored_pois
    
    def get_category_distribution(self, scored_pois: List[ScoredPOIForMultiDay]) -> Dict[str, int]:
        """Get distribution of categories in scored POIs."""
        categories = [poi.poi.category for poi in scored_pois]
        return dict(Counter(categories))
    
    def filter_by_constraints(self, scored_pois: List[ScoredPOIForMultiDay], 
                             constraints: PlanningConstraints) -> List[ScoredPOIForMultiDay]:
        """Filter POIs based on planning constraints."""
        filtered_pois = []
        
        for scored_poi in scored_pois:
            poi = scored_poi.poi
            
            # Check duration constraints
            if poi.duration > constraints.max_pois_per_day * 2:  # Arbitrary max duration check
                logger.debug(f"Filtering out {poi.name}: duration too long ({poi.duration}h)")
                continue
            
            # Add other constraint checks here as needed
            
            filtered_pois.append(scored_poi)
        
        logger.info(f"Applied constraints: {len(scored_pois)} -> {len(filtered_pois)} POIs")
        return filtered_pois


# Global scorer instance
_scorer_instance = None


def get_multiday_scorer() -> MultiDayPOIScorer:
    """Get or create the global multi-day scorer instance."""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = MultiDayPOIScorer()
    return _scorer_instance


async def score_pois_for_multiday(request: MultiDayPlanRequest) -> List[ScoredPOIForMultiDay]:
    """
    Score POIs for multi-day planning using the global scorer.
    
    Args:
        request: Multi-day planning request
        
    Returns:
        List of scored POIs sorted by score
    """
    scorer = get_multiday_scorer()
    scored_pois = await scorer.score_pois(request)
    return scorer.filter_by_constraints(scored_pois, request.constraints)
