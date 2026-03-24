import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import uuid
import heapq
from dataclasses import dataclass, field

from ..schemas.itinerary import (
    Itinerary, ItineraryDay, TimeSlot, Activity, UserPreferences,
    WeatherData, TrafficData, FlightData, ItineraryUpdate, RealTimeAlert,
    ActivityType, WeatherCondition, TrafficLevel, FlightStatus, Location
)
from ..services.weather_service import WeatherService
from ..services.maps_service import MapsService
from ..services.flight_service import FlightService
from ..services.events_service import EventsService


@dataclass
class OptimizationScore:
    total_score: float = 0.0
    preference_match: float = 0.0
    travel_efficiency: float = 0.0
    weather_suitability: float = 0.0
    time_utilization: float = 0.0
    cost_efficiency: float = 0.0
    factors: Dict[str, float] = field(default_factory=dict)


class ItineraryOptimizer:
    """
    Greedy algorithm-based itinerary optimizer that adapts to real-time conditions.
    Uses a multi-criteria scoring system to make optimal decisions.
    """
    
    def __init__(self, weather_service: WeatherService, maps_service: MapsService,
                 flight_service: FlightService, events_service: EventsService):
        self.weather_service = weather_service
        self.maps_service = maps_service
        self.flight_service = flight_service
        self.events_service = events_service
        
        # Scoring weights for different factors
        self.weights = {
            'preference_match': 0.25,
            'travel_efficiency': 0.20,
            'weather_suitability': 0.20,
            'time_utilization': 0.15,
            'cost_efficiency': 0.10,
            'flexibility': 0.10
        }

    async def create_optimal_itinerary(self, 
                                     activities: List[Activity],
                                     preferences: UserPreferences,
                                     start_date: datetime,
                                     end_date: datetime,
                                     flight_data: Optional[FlightData] = None) -> Itinerary:
        """Create an optimal itinerary using greedy algorithm"""
        
        # Initialize itinerary
        itinerary_id = str(uuid.uuid4())
        days = []
        current_date = start_date
        
        # Get weather forecast for the entire period
        location = activities[0].location if activities else None
        weather_forecast = []
        if location:
            weather_forecast = await self.weather_service.get_forecast(location, 
                                                                      days=(end_date - start_date).days + 1)
        
        # Process each day
        while current_date.date() <= end_date.date():
            day_weather = self._get_weather_for_date(weather_forecast, current_date)
            day_activities = self._filter_activities_for_date(activities, current_date)
            
            # Adjust first day if flight arrival affects it
            if flight_data and current_date.date() == start_date.date():
                day_activities = self._adjust_for_flight_arrival(day_activities, flight_data)
            
            # Create optimal day schedule
            day_schedule = await self._create_optimal_day(
                day_activities, preferences, current_date, day_weather
            )
            
            days.append(day_schedule)
            current_date += timedelta(days=1)
        
        itinerary = Itinerary(
            id=itinerary_id,
            user_id="",  # Will be set by API
            destination=location.city if location else "",
            start_date=start_date,
            end_date=end_date,
            days=days,
            user_preferences=preferences,
            total_budget=sum(day.total_budget for day in days),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            version=1
        )
        
        return itinerary

    async def _create_optimal_day(self, 
                                activities: List[Activity],
                                preferences: UserPreferences,
                                date: datetime,
                                weather: Optional[WeatherData]) -> ItineraryDay:
        """Create optimal schedule for a single day using greedy approach"""
        
        # Filter activities based on weather
        suitable_activities = self._filter_by_weather(activities, weather)
        
        # Score each activity
        scored_activities = []
        for activity in suitable_activities:
            score = await self._score_activity(activity, preferences, weather, date)
            scored_activities.append((score, activity))
        
        # Sort by score (greedy choice)
        scored_activities.sort(key=lambda x: x[0].total_score, reverse=True)
        
        # Build schedule using greedy algorithm
        time_slots = []
        current_time = date.replace(hour=9, minute=0, second=0)  # Start at 9 AM
        end_of_day = date.replace(hour=22, minute=0, second=0)   # End at 10 PM
        used_activities = set()
        total_budget = 0.0
        total_travel_time = 0
        
        while current_time < end_of_day and scored_activities:
            best_activity = None
            best_score = None
            best_index = -1
            
            # Find the best activity that can fit in remaining time
            for i, (score, activity) in enumerate(scored_activities):
                if activity.id in used_activities:
                    continue
                
                activity_end_time = current_time + timedelta(minutes=activity.estimated_duration)
                
                # Check if activity fits in the day
                if activity_end_time <= end_of_day:
                    # Check if we can afford it
                    if activity.cost is None or total_budget + (activity.cost or 0) <= self._get_daily_budget(preferences):
                        best_activity = activity
                        best_score = score
                        best_index = i
                        break
            
            if not best_activity:
                break
            
            # Add travel time if not the first activity
            if time_slots:
                travel_time = await self._estimate_travel_time(
                    time_slots[-1].activity.location, 
                    best_activity.location
                )
                current_time += timedelta(minutes=travel_time)
                total_travel_time += travel_time
                
                # Check if we still have time after travel
                if current_time + timedelta(minutes=best_activity.estimated_duration) > end_of_day:
                    break
            
            # Create time slot
            time_slot = TimeSlot(
                start_time=current_time,
                end_time=current_time + timedelta(minutes=best_activity.estimated_duration),
                activity=best_activity,
                priority=self._calculate_priority(best_score),
                flexibility=self._determine_flexibility(best_activity, preferences)
            )
            
            time_slots.append(time_slot)
            used_activities.add(best_activity.id)
            total_budget += (best_activity.cost or 0)
            current_time = time_slot.end_time
            
            # Add buffer time between activities
            current_time += timedelta(minutes=15)
            
            # Remove used activity from consideration
            scored_activities.pop(best_index)
        
        return ItineraryDay(
            date=date,
            time_slots=time_slots,
            total_budget=total_budget,
            total_travel_time=total_travel_time,
            weather_forecast=weather
        )

    async def adapt_to_weather_change(self, itinerary: Itinerary, 
                                    weather_update: WeatherData) -> Tuple[Itinerary, List[RealTimeAlert]]:
        """Adapt itinerary to weather changes using greedy re-optimization"""
        alerts = []
        changes_made = []
        
        # Find the day affected by weather change
        affected_day = None
        day_index = -1
        
        for i, day in enumerate(itinerary.days):
            if day.date.date() == weather_update.timestamp.date():
                affected_day = day
                day_index = i
                break
        
        if not affected_day:
            return itinerary, alerts
        
        # Check if current weather is suitable for outdoor activities
        outdoor_activities = [slot for slot in affected_day.time_slots 
                            if slot.activity.weather_dependent]
        
        if not self.weather_service.is_outdoor_weather_suitable(weather_update, "outdoor"):
            # Need to find indoor alternatives
            for slot in outdoor_activities:
                if slot.flexibility >= 3:  # Only reschedule flexible activities
                    # Find indoor alternative
                    indoor_alternative = await self._find_indoor_alternative(
                        slot.activity, itinerary.user_preferences
                    )
                    
                    if indoor_alternative:
                        old_activity = slot.activity
                        slot.activity = indoor_alternative
                        changes_made.append({
                            "type": "activity_replaced",
                            "original_activity": old_activity.name,
                            "new_activity": indoor_alternative.name,
                            "reason": "weather_unsuitable"
                        })
                        
                        alerts.append(RealTimeAlert(
                            id=str(uuid.uuid4()),
                            itinerary_id=itinerary.id,
                            alert_type="weather",
                            severity="medium",
                            message=f"Replaced {old_activity.name} with indoor alternative due to {weather_update.condition.value} weather",
                            suggested_actions=[f"Head to {indoor_alternative.name} instead"],
                            timestamp=datetime.now()
                        ))
        
        # Update the affected day
        if changes_made:
            itinerary.days[day_index] = affected_day
            itinerary.updated_at = datetime.now()
            itinerary.version += 1
        
        return itinerary, alerts

    async def adapt_to_traffic_delay(self, itinerary: Itinerary, 
                                   traffic_data: TrafficData) -> Tuple[Itinerary, List[RealTimeAlert]]:
        """Adapt itinerary to traffic delays"""
        alerts = []
        changes_made = []
        
        if traffic_data.traffic_level in [TrafficLevel.HIGH, TrafficLevel.SEVERE]:
            delay_minutes = traffic_data.current_duration - traffic_data.typical_duration
            
            # Find affected activities (activities scheduled after the traffic delay)
            current_time = datetime.now()
            
            for day in itinerary.days:
                if day.date.date() == current_time.date():
                    affected_slots = [slot for slot in day.time_slots 
                                    if slot.start_time > current_time]
                    
                    if affected_slots and delay_minutes > 30:  # Significant delay
                        # Shift flexible activities
                        for slot in affected_slots:
                            if slot.flexibility >= 2:
                                slot.start_time += timedelta(minutes=delay_minutes)
                                slot.end_time += timedelta(minutes=delay_minutes)
                                changes_made.append({
                                    "type": "time_shifted",
                                    "activity": slot.activity.name,
                                    "delay_minutes": delay_minutes,
                                    "reason": "traffic_delay"
                                })
                        
                        # Create alert
                        alerts.append(RealTimeAlert(
                            id=str(uuid.uuid4()),
                            itinerary_id=itinerary.id,
                            alert_type="traffic",
                            severity="high" if traffic_data.traffic_level == TrafficLevel.SEVERE else "medium",
                            message=f"Heavy traffic detected. Activities delayed by {delay_minutes} minutes.",
                            suggested_actions=self._get_traffic_alternatives(traffic_data),
                            timestamp=datetime.now()
                        ))
                    break
        
        if changes_made:
            itinerary.updated_at = datetime.now()
            itinerary.version += 1
        
        return itinerary, alerts

    async def adapt_to_flight_delay(self, itinerary: Itinerary, 
                                  flight_data: FlightData) -> Tuple[Itinerary, List[RealTimeAlert]]:
        """Adapt itinerary to flight delays"""
        alerts = []
        changes_made = []
        
        if flight_data.status in [FlightStatus.DELAYED, FlightStatus.CANCELLED] and flight_data.delay_minutes:
            delay_minutes = flight_data.delay_minutes
            arrival_date = flight_data.arrival_time.date()
            
            # Find the day affected by flight delay
            for i, day in enumerate(itinerary.days):
                if day.date.date() == arrival_date:
                    # Calculate new available time after delay
                    original_arrival = flight_data.arrival_time - timedelta(minutes=delay_minutes)
                    new_arrival = flight_data.arrival_time
                    
                    # Find activities that need to be rescheduled
                    affected_slots = [slot for slot in day.time_slots 
                                    if slot.start_time < new_arrival + timedelta(hours=2)]
                    
                    for slot in affected_slots:
                        if slot.flexibility >= 3:
                            # Reschedule to later in the day or next day
                            if slot.start_time + timedelta(minutes=delay_minutes) < day.date.replace(hour=20):
                                slot.start_time += timedelta(minutes=delay_minutes)
                                slot.end_time += timedelta(minutes=delay_minutes)
                                changes_made.append({
                                    "type": "rescheduled",
                                    "activity": slot.activity.name,
                                    "new_time": slot.start_time.isoformat()
                                })
                            else:
                                # Move to next day if possible
                                if i + 1 < len(itinerary.days):
                                    next_day = itinerary.days[i + 1]
                                    # Find suitable time slot in next day
                                    suitable_time = self._find_suitable_time_slot(next_day, slot.activity)
                                    if suitable_time:
                                        new_slot = TimeSlot(
                                            start_time=suitable_time,
                                            end_time=suitable_time + timedelta(minutes=slot.activity.estimated_duration),
                                            activity=slot.activity,
                                            priority=slot.priority,
                                            flexibility=slot.flexibility
                                        )
                                        next_day.time_slots.append(new_slot)
                                        day.time_slots.remove(slot)
                                        changes_made.append({
                                            "type": "moved_to_next_day",
                                            "activity": slot.activity.name
                                        })
                        else:
                            # Cancel inflexible activities if they can't be moved
                            day.time_slots.remove(slot)
                            changes_made.append({
                                "type": "cancelled",
                                "activity": slot.activity.name,
                                "reason": "flight_delay_conflict"
                            })
                    
                    # Create alert
                    severity = "high" if delay_minutes > 120 else "medium"
                    alerts.append(RealTimeAlert(
                        id=str(uuid.uuid4()),
                        itinerary_id=itinerary.id,
                        alert_type="flight",
                        severity=severity,
                        message=f"Flight {flight_data.flight_number} delayed by {delay_minutes} minutes. Itinerary updated.",
                        suggested_actions=[
                            "Check updated activity times",
                            "Consider hotel early check-in if needed",
                            "Review first day plans"
                        ],
                        timestamp=datetime.now()
                    ))
                    break
        
        elif flight_data.status == FlightStatus.CANCELLED:
            # Handle flight cancellation
            alerts.append(RealTimeAlert(
                id=str(uuid.uuid4()),
                itinerary_id=itinerary.id,
                alert_type="flight",
                severity="critical",
                message=f"Flight {flight_data.flight_number} has been cancelled. Immediate action required.",
                suggested_actions=[
                    "Contact airline for rebooking",
                    "Check alternative flights",
                    "Consider adjusting trip dates",
                    "Contact accommodations for date changes"
                ],
                timestamp=datetime.now()
            ))
        
        if changes_made:
            itinerary.updated_at = datetime.now()
            itinerary.version += 1
        
        return itinerary, alerts

    async def _score_activity(self, activity: Activity, preferences: UserPreferences,
                            weather: Optional[WeatherData], date: datetime) -> OptimizationScore:
        """Score an activity based on multiple criteria"""
        score = OptimizationScore()
        
        # Preference matching
        preference_score = self._score_preference_match(activity, preferences)
        score.preference_match = preference_score
        score.factors['preference_match'] = preference_score
        
        # Weather suitability
        if weather:
            weather_score = self._score_weather_suitability(activity, weather)
            score.weather_suitability = weather_score
            score.factors['weather_suitability'] = weather_score
        
        # Cost efficiency
        cost_score = self._score_cost_efficiency(activity, preferences)
        score.cost_efficiency = cost_score
        score.factors['cost_efficiency'] = cost_score
        
        # Calculate total score
        score.total_score = (
            self.weights['preference_match'] * score.preference_match +
            self.weights['weather_suitability'] * score.weather_suitability +
            self.weights['cost_efficiency'] * score.cost_efficiency
        )
        
        return score

    def _score_preference_match(self, activity: Activity, preferences: UserPreferences) -> float:
        """Score how well activity matches user preferences"""
        score = 0.5  # Base score
        
        # Interest matching
        if preferences.interests:
            activity_text = f"{activity.name} {activity.description or ''} {activity.activity_type.value}".lower()
            matching_interests = sum(1 for interest in preferences.interests 
                                   if interest.lower() in activity_text)
            score += min(0.4, matching_interests * 0.1)
        
        # Activity type preferences
        if activity.activity_type.value in preferences.avoid_activities:
            score -= 0.3
        
        # Travel style matching
        if preferences.travel_style == "family" and activity.difficulty_level in ["easy", "moderate"]:
            score += 0.1
        elif preferences.travel_style == "adventure" and activity.activity_type in [ActivityType.ADVENTURE, ActivityType.OUTDOOR]:
            score += 0.2
        
        return max(0.0, min(1.0, score))

    def _score_weather_suitability(self, activity: Activity, weather: WeatherData) -> float:
        """Score activity suitability for current weather"""
        if not activity.weather_dependent:
            return 1.0  # Indoor activities are always suitable
        
        if weather.condition in [WeatherCondition.RAINY, WeatherCondition.STORMY]:
            return 0.1  # Very low score for outdoor activities in bad weather
        elif weather.condition == WeatherCondition.SNOWY:
            # Good for winter activities, bad for others
            if activity.activity_type == ActivityType.ADVENTURE:
                return 0.8
            else:
                return 0.2
        elif weather.condition == WeatherCondition.SUNNY:
            return 1.0  # Perfect for outdoor activities
        else:
            return 0.7  # Cloudy is okay for most activities

    def _score_cost_efficiency(self, activity: Activity, preferences: UserPreferences) -> float:
        """Score activity based on cost efficiency"""
        if activity.cost is None or activity.cost == 0:
            return 1.0  # Free activities always get high cost score
        
        # Budget-based scoring
        budget_multipliers = {
            "low": {"threshold": 50, "multiplier": 0.8},
            "medium": {"threshold": 150, "multiplier": 1.0},
            "high": {"threshold": 500, "multiplier": 1.2}
        }
        
        budget_info = budget_multipliers.get(preferences.budget_range, budget_multipliers["medium"])
        
        if activity.cost <= budget_info["threshold"]:
            return 1.0 * budget_info["multiplier"]
        else:
            # Exponential decay for expensive activities
            excess_ratio = activity.cost / budget_info["threshold"]
            return max(0.1, 1.0 / excess_ratio) * budget_info["multiplier"]

    async def _estimate_travel_time(self, origin: Location, destination: Location) -> int:
        """Estimate travel time between two locations"""
        try:
            traffic_data = await self.maps_service.get_traffic_data(origin, destination)
            return traffic_data.current_duration
        except:
            # Fallback: simple distance-based estimation
            # This is a rough approximation
            return 30  # Default 30 minutes

    def _get_daily_budget(self, preferences: UserPreferences) -> float:
        """Get daily budget based on user preferences"""
        budget_limits = {
            "low": 100.0,
            "medium": 250.0,
            "high": 500.0
        }
        return budget_limits.get(preferences.budget_range, 250.0)

    def _calculate_priority(self, score: OptimizationScore) -> int:
        """Convert optimization score to priority (1-10)"""
        return max(1, min(10, int(score.total_score * 10)))

    def _determine_flexibility(self, activity: Activity, preferences: UserPreferences) -> int:
        """Determine activity flexibility (1-5)"""
        flexibility = 3  # Default moderate flexibility
        
        if activity.booking_required:
            flexibility -= 1  # Less flexible if booking required
        
        if activity.activity_type == ActivityType.RESTAURANT:
            flexibility += 1  # Restaurants are usually flexible
        elif activity.activity_type == ActivityType.ENTERTAINMENT:
            flexibility -= 1  # Shows have fixed times
        
        if preferences.travel_style == "business":
            flexibility -= 1  # Business travelers need more structure
        
        return max(1, min(5, flexibility))

    def _filter_by_weather(self, activities: List[Activity], weather: Optional[WeatherData]) -> List[Activity]:
        """Filter activities based on weather conditions"""
        if not weather:
            return activities
        
        suitable_activities = []
        for activity in activities:
            if not activity.weather_dependent:
                suitable_activities.append(activity)
            elif self.weather_service.is_outdoor_weather_suitable(weather, activity.activity_type.value):
                suitable_activities.append(activity)
            # Skip unsuitable outdoor activities
        
        return suitable_activities

    def _get_weather_for_date(self, weather_forecast: List[WeatherData], date: datetime) -> Optional[WeatherData]:
        """Get weather data for specific date"""
        for weather in weather_forecast:
            if weather.timestamp.date() == date.date():
                return weather
        return None

    def _filter_activities_for_date(self, activities: List[Activity], date: datetime) -> List[Activity]:
        """Filter activities that are available on the given date"""
        # For now, return all activities
        # In a real implementation, you'd check opening hours, availability, etc.
        return activities

    def _adjust_for_flight_arrival(self, activities: List[Activity], flight_data: FlightData) -> List[Activity]:
        """Adjust first day activities based on flight arrival"""
        # Remove activities that are too early for flight arrival
        arrival_time = flight_data.arrival_time
        if flight_data.delay_minutes:
            arrival_time += timedelta(minutes=flight_data.delay_minutes)
        
        # Allow 2 hours for airport exit and hotel check-in
        earliest_activity_time = arrival_time + timedelta(hours=2)
        
        # For now, return all activities - real implementation would filter by time
        return activities

    async def _find_indoor_alternative(self, outdoor_activity: Activity, 
                                     preferences: UserPreferences) -> Optional[Activity]:
        """Find indoor alternative for outdoor activity"""
        # This would typically search for indoor alternatives
        # For now, return a simple indoor alternative
        if outdoor_activity.indoor_alternative:
            # Return a basic indoor activity
            return Activity(
                id=f"indoor_alt_{outdoor_activity.id}",
                name=outdoor_activity.indoor_alternative,
                description=f"Indoor alternative to {outdoor_activity.name}",
                location=outdoor_activity.location,
                activity_type=ActivityType.INDOOR,
                estimated_duration=outdoor_activity.estimated_duration,
                cost=outdoor_activity.cost,
                weather_dependent=False,
                booking_required=False
            )
        return None

    def _get_traffic_alternatives(self, traffic_data: TrafficData) -> List[str]:
        """Get alternative suggestions for traffic delays"""
        suggestions = ["Consider alternative routes"]
        
        if traffic_data.alternative_routes:
            for route in traffic_data.alternative_routes[:2]:  # Top 2 alternatives
                suggestions.append(f"Alternative route: {route.get('summary', 'Via different path')} "
                                 f"({route.get('duration_minutes', 0)} min)")
        
        suggestions.append("Allow extra travel time for remaining activities")
        return suggestions

    def _find_suitable_time_slot(self, day: ItineraryDay, activity: Activity) -> Optional[datetime]:
        """Find suitable time slot for activity in given day"""
        # Sort existing slots by start time
        day.time_slots.sort(key=lambda x: x.start_time)
        
        day_start = day.date.replace(hour=9, minute=0, second=0)
        day_end = day.date.replace(hour=22, minute=0, second=0)
        
        # Try to fit activity at the beginning
        if not day.time_slots:
            return day_start
        
        # Check if fits at the start
        first_slot = day.time_slots[0]
        if day_start + timedelta(minutes=activity.estimated_duration) <= first_slot.start_time:
            return day_start
        
        # Check gaps between activities
        for i in range(len(day.time_slots) - 1):
            current_end = day.time_slots[i].end_time + timedelta(minutes=15)  # Buffer
            next_start = day.time_slots[i + 1].start_time
            
            if current_end + timedelta(minutes=activity.estimated_duration) <= next_start:
                return current_end
        
        # Check if fits at the end
        last_slot = day.time_slots[-1]
        last_end = last_slot.end_time + timedelta(minutes=15)  # Buffer
        
        if last_end + timedelta(minutes=activity.estimated_duration) <= day_end:
            return last_end
        
        return None  # No suitable slot found