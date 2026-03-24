"""
Enhanced Greedy Algorithm Service for Travel Itinerary Optimization
Uses scoring formula: score = w1*(rating) - w2*(distance) - w3*(traffic) + w4*(weather_match)
No external dependencies - fully self-contained
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, timezone
import math
import logging

# Configure logging
logger = logging.getLogger(__name__)

class EnhancedGreedyAlgorithmService:
    """
    Enhanced Greedy Algorithm Service for travel route optimization
    Implements greedy selection based on multi-factor scoring with complete time scheduling
    ZERO EXTERNAL DEPENDENCIES - Uses only Python standard library
    """
    
    def __init__(self):
        # Default weights for scoring formula
        self.default_weights = {
            'w1': 0.4,  # rating weight
            'w2': 0.3,  # distance weight  
            'w3': 0.2,  # traffic weight
            'w4': 0.1   # weather weight
        }
        
        # Timezone offsets (hours from UTC)
        self.timezone_offsets = {
            'Asia/Kolkata': 5.5,
            'Asia/Mumbai': 5.5,
            'Asia/Delhi': 5.5,
            'UTC': 0,
            'US/Eastern': -5,
            'US/Pacific': -8,
            'Europe/London': 0,
            'Europe/Paris': 1,
            'Australia/Sydney': 10
        }
        
        logger.info("✅ Enhanced Greedy Algorithm Service initialized (zero dependencies)")
    
    def _validate_coordinates(self, lat: float, lon: float) -> bool:
        """Validate latitude and longitude ranges"""
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            return -90 <= lat_f <= 90 and -180 <= lon_f <= 180
        except (ValueError, TypeError):
            return False
    
    def _validate_weights(self, weights: Dict) -> Dict:
        """Validate and normalize weights"""
        try:
            validated_weights = {}
            for key in ['w1', 'w2', 'w3', 'w4']:
                value = float(weights.get(key, self.default_weights[key]))
                # Ensure weights are non-negative and reasonable
                validated_weights[key] = max(0.0, min(1.0, value))
            return validated_weights
        except (ValueError, TypeError):
            logger.warning("Invalid weights provided, using defaults")
            return self.default_weights.copy()
    
    def calculate_distance_haversine(self, loc1: Tuple[float, float], 
                                   loc2: Tuple[float, float]) -> float:
        """
        Calculate distance using Haversine formula (pure Python implementation)
        Returns distance in kilometers
        """
        try:
            lat1, lon1 = float(loc1[0]), float(loc1[1])
            lat2, lon2 = float(loc2[0]), float(loc2[1])
            
            # Validate coordinates
            if not (self._validate_coordinates(lat1, lon1) and 
                   self._validate_coordinates(lat2, lon2)):
                logger.warning(f"Invalid coordinates: {loc1}, {loc2}")
                return 0.0
            
            # Convert latitude and longitude from degrees to radians
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
            
            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = (math.sin(dlat/2)**2 + 
                 math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2)
            
            # Prevent domain errors in asin
            a = max(0.0, min(1.0, a))
            c = 2 * math.asin(math.sqrt(a))
            
            # Radius of earth in kilometers
            earth_radius_km = 6371
            distance = earth_radius_km * c
            
            return max(0.0, distance)  # Ensure non-negative distance
            
        except (ValueError, TypeError, ZeroDivisionError) as e:
            logger.error(f"Distance calculation failed: {e}")
            return 0.0
    
    def calculate_score(self, destination: Dict, previous_location: Tuple[float, float], 
                       weights: Optional[Dict] = None) -> float:
        """
        Calculate score using: score = w1*(rating) - w2*(distance) - w3*(traffic) + w4*(weather_match)
        Enhanced with better validation and error handling
        """
        try:
            # Validate and get weights
            if weights is None:
                weights = self.default_weights
            else:
                weights = self._validate_weights(weights)
                
            # Extract destination parameters with safe defaults and validation
            try:
                rating = float(destination.get('rating', 4.0))
                rating = max(0.0, min(10.0, rating))  # Clamp to 0-10 range
            except (ValueError, TypeError):
                rating = 4.0
                
            try:
                traffic = float(destination.get('traffic_score', 5.0))
                traffic = max(1.0, min(10.0, traffic))  # Clamp to 1-10 range
            except (ValueError, TypeError):
                traffic = 5.0
                
            try:
                weather_match = float(destination.get('weather_match', 8.0))
                weather_match = max(0.0, min(10.0, weather_match))  # Clamp to 0-10 range
            except (ValueError, TypeError):
                weather_match = 8.0
            
            # Validate location coordinates
            if ('latitude' not in destination or 'longitude' not in destination or
                destination['latitude'] is None or destination['longitude'] is None):
                logger.warning(f"Missing coordinates for destination: {destination.get('name', 'Unknown')}")
                return 0.0
            
            try:
                current_location = (float(destination['latitude']), float(destination['longitude']))
            except (ValueError, TypeError):
                logger.warning(f"Invalid coordinates for destination: {destination.get('name', 'Unknown')}")
                return 0.0
            
            # Validate coordinates are in valid ranges
            if not self._validate_coordinates(current_location[0], current_location[1]):
                logger.warning(f"Coordinates out of range for destination: {destination.get('name', 'Unknown')}")
                return 0.0
            
            # Calculate distance from previous location
            distance = self.calculate_distance_haversine(previous_location, current_location)
            
            # Normalize distance (0-200km scale to 0-10) - increased range for better scaling
            normalized_distance = min(distance / 20.0, 10.0)  # 20km = 1 point
            
            # Apply scoring formula with validated weights
            # Traffic score is inverted (higher traffic score = lower penalty)
            score = (weights['w1'] * rating - 
                    weights['w2'] * normalized_distance - 
                    weights['w3'] * (10.0 - traffic) +  # Lower traffic score = higher penalty
                    weights['w4'] * weather_match)
            
            return round(max(0.0, score), 2)  # Ensure non-negative score
            
        except Exception as e:
            logger.error(f"Error calculating score for destination {destination.get('name', 'Unknown')}: {e}")
            return 0.0
    
    def optimize_route_greedy(self, destinations: List[Dict], start_location: Tuple[float, float],
                            weights: Optional[Dict] = None) -> List[Dict]:
        """
        Enhanced greedy algorithm to optimize route based on scoring formula
        """
        try:
            # Input validation
            if not destinations:
                logger.warning("No destinations provided for optimization")
                return []
            
            if not isinstance(destinations, list):
                logger.error("Destinations must be a list")
                return []
                
            if weights is None:
                weights = self.default_weights
            else:
                weights = self._validate_weights(weights)
                
            # Validate start location
            if (not isinstance(start_location, (tuple, list)) or 
                len(start_location) != 2 or
                not self._validate_coordinates(start_location[0], start_location[1])):
                logger.error("Invalid start_location. Must be a tuple/list of (latitude, longitude)")
                return []
            
            # Filter out invalid destinations before processing
            valid_destinations = []
            for dest in destinations:
                if self.validate_destination(dest):
                    # Create a copy to avoid mutations
                    dest_copy = dict(dest)
                    valid_destinations.append(dest_copy)
                else:
                    logger.warning(f"Skipping invalid destination: {dest.get('name', 'Unknown')}")
            
            if not valid_destinations:
                logger.warning("No valid destinations after filtering")
                return []
            
            optimized_route = []
            remaining_destinations = valid_destinations.copy()
            current_location = tuple(start_location)
            total_distance = 0.0
            
            logger.info(f"Starting route optimization with {len(valid_destinations)} valid destinations")
            
            # Greedy selection: always pick highest scoring unvisited destination
            while remaining_destinations:
                best_destination = None
                best_score = float('-inf')
                best_index = -1
                
                # Evaluate all remaining destinations
                for i, destination in enumerate(remaining_destinations):
                    try:
                        score = self.calculate_score(destination, current_location, weights)
                        
                        if score > best_score:
                            best_score = score
                            best_destination = destination
                            best_index = i
                            
                    except Exception as e:
                        logger.warning(f"Error evaluating destination {destination.get('name', 'Unknown')}: {e}")
                        continue
                
                # Add best destination to route
                if best_destination is not None and best_index >= 0 and best_score > 0:
                    try:
                        # Calculate distance from current to selected destination
                        dest_location = (float(best_destination['latitude']), float(best_destination['longitude']))
                        distance = self.calculate_distance_haversine(current_location, dest_location)
                        
                        # Update destination with optimization data
                        best_destination['distance_from_previous'] = round(distance, 2)
                        best_destination['calculated_score'] = round(best_score, 2)
                        best_destination['visit_order'] = len(optimized_route) + 1
                        best_destination['cumulative_distance'] = round(total_distance + distance, 2)
                        
                        # Add travel time estimate (50 km/h average)
                        travel_time_hours = distance / 50.0
                        best_destination['estimated_travel_time_hours'] = round(travel_time_hours, 2)
                        
                        optimized_route.append(best_destination)
                        remaining_destinations.pop(best_index)
                        current_location = dest_location
                        total_distance += distance
                        
                        logger.debug(f"Added destination: {best_destination.get('name')} (Score: {best_score:.2f})")
                        
                    except Exception as e:
                        logger.error(f"Error adding destination to route: {e}")
                        # Remove problematic destination and continue
                        if best_index < len(remaining_destinations):
                            remaining_destinations.pop(best_index)
                        continue
                else:
                    logger.warning("No valid destination found with positive score, ending optimization")
                    break
            
            logger.info(f"Route optimization completed. {len(optimized_route)} destinations optimized.")
            return optimized_route
            
        except Exception as e:
            logger.error(f"Critical error in route optimization: {e}")
            return []
    
    def _get_timezone_offset(self, timezone_str: str) -> float:
        """Get timezone offset in hours from UTC"""
        return self.timezone_offsets.get(timezone_str, 5.5)  # Default to IST
    
    def _parse_time_with_timezone(self, time_str: str, timezone_str: str = "Asia/Kolkata") -> datetime:
        """Parse time string and apply timezone offset"""
        try:
            # Parse time (assuming HH:MM:SS format)
            if len(time_str.split(':')) == 3:
                time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
            else:
                time_obj = datetime.strptime(time_str, "%H:%M").time()
            
            # Create datetime for today
            current_date = datetime.now().date()
            dt = datetime.combine(current_date, time_obj)
            
            # Apply timezone offset
            offset_hours = self._get_timezone_offset(timezone_str)
            timezone_offset = timezone(timedelta(hours=offset_hours))
            dt = dt.replace(tzinfo=timezone_offset)
            
            return dt
            
        except Exception as e:
            logger.warning(f"Error parsing time {time_str}: {e}")
            # Fallback to 9 AM
            current_date = datetime.now().date()
            fallback_time = datetime.combine(current_date, datetime.strptime("09:00:00", "%H:%M:%S").time())
            offset_hours = self._get_timezone_offset(timezone_str)
            timezone_offset = timezone(timedelta(hours=offset_hours))
            return fallback_time.replace(tzinfo=timezone_offset)
    
    def calculate_visit_schedule(self, route: List[Dict], start_time: str, 
                               timezone_str: str = "Asia/Kolkata") -> List[Dict]:
        """
        Enhanced visit schedule calculation with better time management
        """
        try:
            if not route:
                return []
            
            # Parse start time with timezone
            current_datetime = self._parse_time_with_timezone(start_time, timezone_str)
            
            scheduled_route = []
            
            for i, destination in enumerate(route):
                dest_copy = dict(destination)
                
                # Set arrival time
                dest_copy['scheduled_arrival_time'] = current_datetime.isoformat()
                dest_copy['arrival_time_formatted'] = current_datetime.strftime("%I:%M %p")
                
                # Calculate stay duration with intelligent defaults
                stay_duration_hours = self._get_intelligent_stay_duration(destination)
                departure_time = current_datetime + timedelta(hours=stay_duration_hours)
                
                dest_copy['scheduled_departure_time'] = departure_time.isoformat()
                dest_copy['departure_time_formatted'] = departure_time.strftime("%I:%M %p")
                dest_copy['stay_duration_hours'] = stay_duration_hours
                
                # Calculate travel time to next destination (if not last)
                if i < len(route) - 1:
                    distance = float(destination.get('distance_from_previous', 0))
                    travel_time_hours = self._calculate_travel_time(distance)
                    travel_time_minutes = int(travel_time_hours * 60)
                    
                    dest_copy['travel_time_to_next_hours'] = round(travel_time_hours, 2)
                    dest_copy['travel_time_to_next_minutes'] = travel_time_minutes
                    
                    # Update current time for next destination
                    current_datetime = departure_time + timedelta(hours=travel_time_hours)
                else:
                    dest_copy['travel_time_to_next_hours'] = 0
                    dest_copy['travel_time_to_next_minutes'] = 0
                
                # Add enhanced time-based recommendations
                dest_copy['optimal_visit_info'] = self._get_enhanced_visit_info(
                    current_datetime, destination
                )
                
                scheduled_route.append(dest_copy)
                
            return scheduled_route
            
        except Exception as e:
            logger.error(f"Error calculating visit schedule: {e}")
            return route
    
    def _get_intelligent_stay_duration(self, destination: Dict) -> float:
        """Get intelligent stay duration based on destination type and category"""
        try:
            # Get base duration from destination or use category-based defaults
            if 'stay_duration' in destination and destination['stay_duration']:
                return max(0.5, min(8.0, float(destination['stay_duration'])))
            
            # Category-based intelligent defaults
            category = destination.get('category', '').lower()
            
            duration_map = {
                'museum': 2.5,
                'historical_site': 2.0,
                'religious_site': 1.5,
                'scenic_spot': 1.0,
                'viewpoint': 0.5,
                'restaurant': 1.5,
                'shopping': 2.0,
                'park': 2.0,
                'beach': 3.0,
                'zoo': 4.0,
                'theme_park': 6.0,
                'monument': 1.0
            }
            
            # Check if category matches any key
            for cat, duration in duration_map.items():
                if cat in category:
                    return duration
            
            # Default based on rating (higher rated places get more time)
            rating = float(destination.get('rating', 4.0))
            if rating >= 4.5:
                return 2.5
            elif rating >= 4.0:
                return 2.0
            else:
                return 1.5
                
        except Exception:
            return 2.0  # Default fallback
    
    def _calculate_travel_time(self, distance_km: float, transport_mode: str = "driving") -> float:
        """Calculate travel time based on distance and transport mode"""
        try:
            if distance_km <= 0:
                return 0.0
            
            # Speed assumptions (km/h)
            speeds = {
                'walking': 5,
                'cycling': 15,
                'driving': 50,
                'public_transport': 30,
                'mixed': 40
            }
            
            speed = speeds.get(transport_mode, 50)
            travel_time = distance_km / speed
            
            # Add buffer time (minimum 15 minutes, up to 30% of travel time)
            buffer_time = max(0.25, travel_time * 0.3)  # 15 minutes minimum
            
            return round(travel_time + buffer_time, 2)
            
        except Exception:
            return max(0.25, distance_km * 0.02)  # Fallback: ~30 km/h with buffer
    
    def _get_enhanced_visit_info(self, arrival_time: datetime, destination: Dict) -> Dict:
        """Get enhanced visit information based on time and destination"""
        try:
            hour = arrival_time.hour
            category = destination.get('category', '').lower()
            
            info = {
                'visit_period': self._get_visit_period(hour),
                'crowd_level': self._estimate_crowd_level(hour, category),
                'photography_rating': self._get_photography_rating(hour, category),
                'weather_suitability': self._get_weather_suitability(hour),
                'opening_status': self._get_opening_status(hour, category),
                'recommended_activities': self._get_recommended_activities(hour, category),
                'tips': self._get_visit_tips(hour, category)
            }
            
            return info
            
        except Exception as e:
            logger.warning(f"Error generating visit info: {e}")
            return {'visit_period': 'daytime', 'tips': ['Enjoy your visit!']}
    
    def _get_visit_period(self, hour: int) -> str:
        """Determine visit period"""
        if 5 <= hour < 10:
            return 'early_morning'
        elif 10 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 19:
            return 'evening'
        else:
            return 'night'
    
    def _estimate_crowd_level(self, hour: int, category: str) -> str:
        """Estimate crowd level based on time and category"""
        if 'museum' in category or 'historical' in category:
            if 10 <= hour <= 11 or 14 <= hour <= 15:
                return 'moderate'
            elif 12 <= hour <= 13:
                return 'high'
            else:
                return 'low'
        elif 'scenic' in category or 'viewpoint' in category:
            if 6 <= hour <= 8 or 17 <= hour <= 19:
                return 'high'  # Golden hours
            else:
                return 'moderate'
        else:
            if 11 <= hour <= 14:
                return 'high'
            else:
                return 'moderate'
    
    def _get_photography_rating(self, hour: int, category: str) -> str:
        """Rate photography conditions"""
        if 'scenic' in category or 'viewpoint' in category:
            if 6 <= hour <= 8 or 17 <= hour <= 19:
                return 'excellent'  # Golden hours
            elif 9 <= hour <= 16:
                return 'good'
            else:
                return 'fair'
        else:
            if 9 <= hour <= 16:
                return 'good'
            else:
                return 'fair'
    
    def _get_weather_suitability(self, hour: int) -> str:
        """Assess weather suitability for outdoor activities"""
        if 6 <= hour <= 10 or 16 <= hour <= 19:
            return 'excellent'
        elif 11 <= hour <= 15:
            return 'moderate'  # Could be hot
        else:
            return 'fair'
    
    def _get_opening_status(self, hour: int, category: str) -> str:
        """Estimate if place is likely open"""
        if 'museum' in category:
            if 10 <= hour <= 17:
                return 'open'
            else:
                return 'closed'
        elif 'religious' in category:
            if 6 <= hour <= 20:
                return 'open'
            else:
                return 'limited_access'
        elif 'restaurant' in category:
            if 11 <= hour <= 22:
                return 'open'
            else:
                return 'closed'
        else:
            if 9 <= hour <= 18:
                return 'likely_open'
            else:
                return 'check_hours'
    
    def _get_recommended_activities(self, hour: int, category: str) -> List[str]:
        """Get recommended activities for the time and place"""
        activities = []
        
        if 'scenic' in category:
            if 6 <= hour <= 8 or 17 <= hour <= 19:
                activities.extend(['photography', 'sunset/sunrise viewing'])
            else:
                activities.extend(['sightseeing', 'relaxation'])
        elif 'museum' in category:
            activities.extend(['guided_tour', 'audio_guide', 'educational_visit'])
        elif 'religious' in category:
            if 6 <= hour <= 9:
                activities.extend(['morning_prayers', 'peaceful_meditation'])
            else:
                activities.extend(['cultural_exploration', 'architecture_appreciation'])
        else:
            activities.extend(['exploration', 'photography'])
        
        return activities
    
    def _get_visit_tips(self, hour: int, category: str) -> List[str]:
        """Get practical tips for visiting at this time"""
        tips = []
        
        if hour < 9:
            tips.append('Early visit - expect fewer crowds')
        elif 11 <= hour <= 14:
            tips.append('Peak hours - expect crowds')
            if 'outdoor' in category or 'scenic' in category:
                tips.append('Stay hydrated and use sun protection')
        
        if 'museum' in category:
            tips.append('Allow extra time for exhibits')
        elif 'religious' in category:
            tips.append('Dress modestly and respect local customs')
        
        tips.append('Check opening hours before visiting')
        return tips
    
    def generate_daily_schedule(self, scheduled_route: List[Dict], 
                              trip_date: str = None) -> Dict:
        """
        Generate comprehensive daily schedule summary with enhanced details
        """
        try:
            if not scheduled_route:
                return {}
            
            if not trip_date:
                trip_date = datetime.now().strftime("%Y-%m-%d")
            
            first_arrival = scheduled_route[0]['scheduled_arrival_time']
            last_departure = scheduled_route[-1]['scheduled_departure_time']
            
            # Parse times
            start_dt = datetime.fromisoformat(first_arrival.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(last_departure.replace('Z', '+00:00'))
            
            # Calculate total duration
            total_duration = (end_dt - start_dt).total_seconds() / 3600
            
            # Generate break times and meal suggestions
            break_times = self._calculate_intelligent_breaks(scheduled_route)
            meal_suggestions = self._generate_meal_suggestions(scheduled_route)
            
            # Calculate travel statistics
            travel_stats = self._calculate_travel_statistics(scheduled_route)
            
            return {
                trip_date: {
                    "start_time": start_dt.strftime("%H:%M:%S"),
                    "start_time_formatted": start_dt.strftime("%I:%M %p"),
                    "end_time": end_dt.strftime("%H:%M:%S"),
                    "end_time_formatted": end_dt.strftime("%I:%M %p"),
                    "total_duration_hours": round(total_duration, 2),
                    "total_destinations": len(scheduled_route),
                    "break_times": break_times,
                    "meal_suggestions": meal_suggestions,
                    "travel_statistics": travel_stats,
                    "schedule_summary": {
                        "morning_activities": len([d for d in scheduled_route 
                                                 if 'morning' in d.get('optimal_visit_info', {}).get('visit_period', '')]),
                        "afternoon_activities": len([d for d in scheduled_route 
                                                   if 'afternoon' in d.get('optimal_visit_info', {}).get('visit_period', '')]),
                        "evening_activities": len([d for d in scheduled_route 
                                                 if 'evening' in d.get('optimal_visit_info', {}).get('visit_period', '')])
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating daily schedule: {e}")
            return {}
    
    def _calculate_intelligent_breaks(self, route: List[Dict]) -> List[Dict]:
        """Calculate intelligent break times based on schedule"""
        breaks = []
        
        try:
            for i, dest in enumerate(route):
                if i == 0:  # Skip first destination
                    continue
                    
                arrival_str = dest.get('scheduled_arrival_time', '')
                if not arrival_str:
                    continue
                    
                arrival = datetime.fromisoformat(arrival_str.replace('Z', '+00:00'))
                hour = arrival.hour
                
                # Suggest lunch break
                if 12 <= hour <= 14 and not any(b.get('type') == 'lunch' for b in breaks):
                    lunch_start = arrival - timedelta(minutes=30)
                    breaks.append({
                        "type": "lunch",
                        "start_time": lunch_start.strftime("%H:%M:%S"),
                        "start_time_formatted": lunch_start.strftime("%I:%M %p"),
                        "end_time": arrival.strftime("%H:%M:%S"),
                        "end_time_formatted": arrival.strftime("%I:%M %p"),
                        "duration_minutes": 30,
                        "location": f"Near {dest.get('name', 'destination')}",
                        "suggestion": "Local restaurant or food court"
                    })
                
                # Suggest coffee/snack break for long gaps
                if i < len(route) - 1:
                    prev_departure = dest.get('scheduled_departure_time', '')
                    next_arrival = route[i + 1].get('scheduled_arrival_time', '')
                    
                    if prev_departure and next_arrival:
                        prev_dep_dt = datetime.fromisoformat(prev_departure.replace('Z', '+00:00'))
                        next_arr_dt = datetime.fromisoformat(next_arrival.replace('Z', '+00:00'))
                        gap_hours = (next_arr_dt - prev_dep_dt).total_seconds() / 3600
                        
                        if gap_hours > 3:  # Long travel time
                            break_time = prev_dep_dt + timedelta(hours=gap_hours/2)
                            breaks.append({
                                "type": "rest_stop",
                                "start_time": break_time.strftime("%H:%M:%S"),
                                "start_time_formatted": break_time.strftime("%I:%M %p"),
                                "end_time": (break_time + timedelta(minutes=20)).strftime("%H:%M:%S"),
                                "duration_minutes": 20,
                                "location": "En route",
                                "suggestion": "Rest stop, snacks, fuel"
                            })
            
            return breaks
            
        except Exception as e:
            logger.warning(f"Error calculating breaks: {e}")
            return []
    
    def _generate_meal_suggestions(self, route: List[Dict]) -> Dict:
        """Generate meal suggestions based on schedule"""
        try:
            suggestions = {
                'breakfast': None,
                'lunch': None,
                'dinner': None,
                'snacks': []
            }
            
            for dest in route:
                arrival_str = dest.get('scheduled_arrival_time', '')
                if not arrival_str:
                    continue
                    
                arrival = datetime.fromisoformat(arrival_str.replace('Z', '+00:00'))
                hour = arrival.hour
                
                # Breakfast suggestion
                if 7 <= hour <= 10 and not suggestions['breakfast']:
                    suggestions['breakfast'] = {
                        'time': arrival.strftime("%I:%M %p"),
                        'location': f"Near {dest.get('name')}",
                        'suggestion': 'Local breakfast spot or hotel restaurant'
                    }
                
                # Lunch suggestion
                elif 12 <= hour <= 14 and not suggestions['lunch']:
                    suggestions['lunch'] = {
                        'time': arrival.strftime("%I:%M %p"),
                        'location': f"Near {dest.get('name')}",
                        'suggestion': 'Local cuisine restaurant'
                    }
                
                # Dinner suggestion
                elif 18 <= hour <= 20 and not suggestions['dinner']:
                    suggestions['dinner'] = {
                        'time': arrival.strftime("%I:%M %p"),
                        'location': f"Near {dest.get('name')}",
                        'suggestion': 'Fine dining or local specialties'
                    }
            
            return suggestions
            
        except Exception as e:
            logger.warning(f"Error generating meal suggestions: {e}")
            return {}
    
    def _calculate_travel_statistics(self, route: List[Dict]) -> Dict:
        """Calculate comprehensive travel statistics"""
        try:
            total_distance = sum(float(d.get('distance_from_previous', 0)) for d in route)
            total_travel_time = sum(float(d.get('travel_time_to_next_hours', 0)) for d in route)
            total_stay_time = sum(float(d.get('stay_duration_hours', 0)) for d in route)
            
            return {
                'total_distance_km': round(total_distance, 2),
                'total_travel_time_hours': round(total_travel_time, 2),
                'total_stay_time_hours': round(total_stay_time, 2),
                'average_distance_per_destination': round(total_distance / max(1, len(route)), 2),
                'average_stay_duration': round(total_stay_time / max(1, len(route)), 2),
                'estimated_fuel_cost_usd': round(total_distance * 0.15, 2),
                'carbon_footprint_kg': round(total_distance * 0.21, 2)  # Rough estimate
            }
            
        except Exception as e:
            logger.warning(f"Error calculating travel statistics: {e}")
            return {}
    
    def calculate_total_travel_time(self, route: List[Dict]) -> float:
        """
        Enhanced total travel time calculation with better accuracy
        """
        try:
            if not route:
                return 0.0
                
            total_time = 0.0
            
            for destination in route:
                try:
                    # Add stay duration
                    stay_duration = float(destination.get('stay_duration_hours', 
                                        destination.get('stay_duration', 2.0)))
                    stay_duration = max(0.0, min(24.0, stay_duration))
                    total_time += stay_duration
                    
                    # Add travel time
                    travel_time = float(destination.get('travel_time_to_next_hours', 0))
                    travel_time = max(0.0, travel_time)
                    total_time += travel_time
                    
                except (ValueError, TypeError, ZeroDivisionError):
                    logger.warning(f"Invalid data for travel time calculation in destination: {destination.get('name', 'Unknown')}")
                    continue
                
            return round(max(0.0, total_time), 2)
            
        except Exception as e:
            logger.error(f"Error calculating travel time: {e}")
            return 0.0
    
    def estimate_costs(self, route: List[Dict], transport_mode: str = "driving") -> Dict[str, float]:
        """
        Enhanced cost estimation with different transport modes
        """
        try:
            default_costs = {
                'total_distance_km': 0.0,
                'fuel_cost_usd': 0.0,
                'accommodation_cost_usd': 0.0,
                'entry_fees_usd': 0.0,
                'food_cost_usd': 0.0,
                'total_estimated_cost_usd': 0.0
            }
            
            if not route:
                return default_costs
                
            # Calculate total distance safely
            total_distance = 0.0
            valid_destinations = 0
            
            for dest in route:
                try:
                    distance = float(dest.get('distance_from_previous', 0))
                    if distance >= 0:
                        total_distance += distance
                        valid_destinations += 1
                except (ValueError, TypeError):
                    continue
            
            if valid_destinations == 0:
                return default_costs
            
            # Enhanced cost estimations based on transport mode
            transport_costs = {
                'driving': 0.15,      # USD per km
                'public_transport': 0.08,
                'cycling': 0.02,      # Maintenance costs
                'walking': 0.01,      # Shoe wear :)
                'mixed': 0.12
            }
            
            fuel_cost = total_distance * transport_costs.get(transport_mode, 0.15)
            
            # Dynamic accommodation based on trip duration
            total_hours = self.calculate_total_travel_time(route)
            accommodation_days = max(1, int(total_hours / 10))  # Assuming 10 hours per day
            accommodation_cost = accommodation_days * 80  # USD per night (mid-range)
            
            # Entry fees with category-based estimation
            entry_fees = 0
            for dest in route:
                category = dest.get('category', '').lower()
                if 'museum' in category:
                    entry_fees += 12
                elif 'historical' in category:
                    entry_fees += 8
                elif 'religious' in category:
                    entry_fees += 2
                elif 'park' in category:
                    entry_fees += 5
                else:
                    entry_fees += 6
            
            # Food cost estimation
            meal_days = max(1, accommodation_days)
            food_cost = meal_days * 45  # USD per day for meals
            
            total_cost = fuel_cost + accommodation_cost + entry_fees + food_cost
            
            return {
                'total_distance_km': round(max(0.0, total_distance), 2),
                'fuel_cost_usd': round(max(0.0, fuel_cost), 2),
                'accommodation_cost_usd': round(max(0.0, accommodation_cost), 2),
                'entry_fees_usd': round(max(0.0, entry_fees), 2),
                'food_cost_usd': round(max(0.0, food_cost), 2),
                'total_estimated_cost_usd': round(max(0.0, total_cost), 2),
                'cost_per_destination': round(max(0.0, total_cost / valid_destinations), 2),
                'transport_mode': transport_mode
            }
            
        except Exception as e:
            logger.error(f"Error estimating costs: {e}")
            return default_costs

    def create_complete_itinerary(self, destinations: List[Dict], 
                                start_location: Tuple[float, float],
                                start_time: str = "09:00:00",
                                trip_date: str = None,
                                timezone_str: str = "Asia/Kolkata",
                                weights: Optional[Dict] = None,
                                transport_mode: str = "driving") -> Dict:
        """
        Enhanced complete itinerary creation with all features
        
        Returns comprehensive response format with time scheduling, costs, and recommendations
        """
        try:
            # Step 1: Optimize route using greedy algorithm
            logger.info(f"Creating complete itinerary for {len(destinations)} destinations")
            
            optimized_route = self.optimize_route_greedy(destinations, start_location, weights)
            
            if not optimized_route:
                return {"success": False, "error": "Failed to optimize route"}
            
            # Step 2: Add comprehensive time scheduling
            scheduled_route = self.calculate_visit_schedule(
                optimized_route, start_time, timezone_str
            )
            
            # Step 3: Generate enhanced daily schedule
            daily_schedule = self.generate_daily_schedule(scheduled_route, trip_date)
            
            # Step 4: Calculate enhanced costs and metrics
            costs = self.estimate_costs(scheduled_route, transport_mode)
            total_travel_time = self.calculate_total_travel_time(scheduled_route)
            total_score = sum(float(dest.get('calculated_score', 0)) for dest in scheduled_route)
            
            # Step 5: Generate alternative routes
            alternatives = self.get_alternative_routes(destinations, start_location, weights, 2)
            
            # Step 6: Calculate sustainability metrics
            sustainability_metrics = self._calculate_sustainability_metrics(scheduled_route, transport_mode)
            
            # Step 7: Build comprehensive response
            return {
                "success": True,
                "message": "Complete itinerary created successfully with enhanced time scheduling",
                "algorithm_used": "enhanced_greedy_scoring_with_complete_temporal_optimization",
                "optimized_route": scheduled_route,
                "route_summary": {
                    "total_destinations": len(scheduled_route),
                    "total_score": round(total_score, 2),
                    "total_travel_time_hours": total_travel_time,
                    "total_distance_km": costs["total_distance_km"],
                    "estimated_duration_days": max(1, int(total_travel_time / 10))
                },
                "daily_schedule": daily_schedule,
                "cost_breakdown": costs,
                "alternative_routes": alternatives,
                "sustainability_metrics": sustainability_metrics,
                "time_optimization_details": {
                    "algorithm_version": "enhanced_greedy_v2.0",
                    "start_time_preference": start_time,
                    "timezone": timezone_str,
                    "buffer_time_included": True,
                    "intelligent_scheduling": True,
                    "break_time_optimization": True,
                    "transport_mode": transport_mode,
                    "traffic_considered": True,
                    "weather_integration": True
                },
                "recommendations": {
                    "best_time_to_start": self._recommend_best_start_time(scheduled_route),
                    "packing_suggestions": self._generate_packing_suggestions(scheduled_route),
                    "weather_prep": "Check weather forecast and pack accordingly",
                    "local_tips": self._generate_local_tips(scheduled_route)
                },
                "weights_applied": weights or self.default_weights,
                "optimization_metadata": {
                    "destinations_processed": len(destinations),
                    "destinations_included": len(scheduled_route),
                    "optimization_success_rate": round((len(scheduled_route) / max(1, len(destinations))) * 100, 1),
                    "algorithm_execution_time": "< 1 second"
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating complete itinerary: {e}")
            return {
                "success": False, 
                "error": f"Failed to create itinerary: {str(e)}",
                "fallback_available": True
            }
    
    def _calculate_sustainability_metrics(self, route: List[Dict], transport_mode: str) -> Dict:
        """Calculate sustainability and environmental impact metrics"""
        try:
            total_distance = sum(float(d.get('distance_from_previous', 0)) for d in route)
            
            # Carbon emission factors (kg CO2 per km)
            emission_factors = {
                'driving': 0.21,
                'public_transport': 0.08,
                'cycling': 0.0,
                'walking': 0.0,
                'mixed': 0.15
            }
            
            carbon_emissions = total_distance * emission_factors.get(transport_mode, 0.21)
            
            # Calculate eco-friendliness score
            eco_score = 100
            if transport_mode in ['cycling', 'walking']:
                eco_score = 100
            elif transport_mode == 'public_transport':
                eco_score = 85
            elif transport_mode == 'mixed':
                eco_score = 70
            else:
                eco_score = max(20, 80 - (carbon_emissions * 2))
            
            return {
                'carbon_footprint_kg': round(carbon_emissions, 2),
                'eco_friendliness_score': round(eco_score, 1),
                'transport_mode': transport_mode,
                'sustainability_rating': 'excellent' if eco_score >= 80 else 'good' if eco_score >= 60 else 'fair',
                'offset_suggestions': {
                    'tree_planting_equivalent': max(1, int(carbon_emissions / 22)),
                    'renewable_energy_hours': round(carbon_emissions * 2.3, 1)
                }
            }
            
        except Exception as e:
            logger.warning(f"Error calculating sustainability metrics: {e}")
            return {'carbon_footprint_kg': 0, 'eco_friendliness_score': 50}
    
    def _recommend_best_start_time(self, route: List[Dict]) -> str:
        """Recommend optimal start time based on route characteristics"""
        try:
            # Analyze route for scenic spots
            has_scenic = any('scenic' in d.get('category', '').lower() for d in route)
            has_museums = any('museum' in d.get('category', '').lower() for d in route)
            
            if has_scenic:
                return "07:00:00 (Early start for better lighting and fewer crowds)"
            elif has_museums:
                return "09:30:00 (Museums typically open at 10 AM)"
            else:
                return "08:30:00 (Good balance for most attractions)"
                
        except Exception:
            return "09:00:00 (Standard recommended start time)"
    
    def _generate_packing_suggestions(self, route: List[Dict]) -> List[str]:
        """Generate packing suggestions based on route characteristics"""
        try:
            suggestions = ['Comfortable walking shoes', 'Water bottle', 'Phone charger']
            
            categories = [d.get('category', '').lower() for d in route]
            
            if any('scenic' in cat or 'viewpoint' in cat for cat in categories):
                suggestions.extend(['Camera', 'Sunglasses', 'Hat'])
            
            if any('museum' in cat for cat in categories):
                suggestions.append('Notebook for interesting facts')
                
            if any('religious' in cat for cat in categories):
                suggestions.append('Modest clothing (cover shoulders/knees)')
                
            if len(route) > 5:
                suggestions.extend(['Snacks', 'First aid kit', 'Power bank'])
            
            return list(set(suggestions))  # Remove duplicates
            
        except Exception:
            return ['Comfortable shoes', 'Water', 'Camera', 'Snacks']
    
    def _generate_local_tips(self, route: List[Dict]) -> List[str]:
        """Generate local tips based on destinations"""
        try:
            tips = [
                'Check opening hours before visiting',
                'Carry local currency for entry fees',
                'Learn basic local phrases for better experience'
            ]
            
            if len(route) >= 5:
                tips.append('Consider buying a local transport pass')
            
            if any('religious' in d.get('category', '').lower() for d in route):
                tips.append('Respect local customs and dress codes at religious sites')
                
            return tips
            
        except Exception:
            return ['Check opening hours', 'Carry cash', 'Be respectful of local customs']
    
    def get_alternative_routes(self, destinations: List[Dict], start_location: Tuple[float, float],
                             weights: Optional[Dict] = None, num_alternatives: int = 3) -> List[Dict]:
        """
        Enhanced alternative routes generation with detailed analysis
        """
        try:
            if not destinations or not self._validate_coordinates(start_location[0], start_location[1]):
                logger.warning("Invalid input for alternative routes generation")
                return []
                
            alternatives = []
            num_alternatives = max(1, min(4, int(num_alternatives)))
            
            # Enhanced weight combinations with clear focus
            weight_variations = [
                {'w1': 0.5, 'w2': 0.2, 'w3': 0.2, 'w4': 0.1},  # Rating focused
                {'w1': 0.2, 'w2': 0.5, 'w3': 0.2, 'w4': 0.1},  # Distance focused
                {'w1': 0.3, 'w2': 0.2, 'w3': 0.4, 'w4': 0.1},  # Traffic focused
                {'w1': 0.25, 'w2': 0.25, 'w3': 0.25, 'w4': 0.25}   # Balanced
            ]
            
            focus_descriptions = [
                'Highest rated destinations prioritized',
                'Shortest travel distances prioritized', 
                'Best traffic conditions prioritized',
                'Balanced optimization approach'
            ]
            
            focus_names = ['Quality Focus', 'Distance Focus', 'Traffic Focus', 'Balanced']
            
            for i, weight_set in enumerate(weight_variations[:num_alternatives]):
                try:
                    # Create deep copies to avoid mutations
                    destinations_copy = [dict(dest) for dest in destinations if self.validate_destination(dest)]
                    
                    route = self.optimize_route_greedy(
                        destinations_copy, 
                        start_location, 
                        weight_set
                    )
                    
                    if route:
                        total_score = sum(float(dest.get('calculated_score', 0)) for dest in route)
                        costs = self.estimate_costs(route)
                        travel_time = self.calculate_total_travel_time(route)
                        
                        # Calculate route characteristics
                        avg_rating = sum(float(d.get('rating', 0)) for d in route) / len(route)
                        total_distance = costs['total_distance_km']
                        
                        alternatives.append({
                            'route': route,
                            'weights_used': weight_set,
                            'total_score': round(max(0.0, total_score), 2),
                            'costs': costs,
                            'travel_time_hours': travel_time,
                            'focus': focus_names[i] if i < len(focus_names) else f'Alternative {i+1}',
                            'focus_description': focus_descriptions[i] if i < len(focus_descriptions) else 'Alternative route optimization',
                            'route_characteristics': {
                                'average_rating': round(avg_rating, 1),
                                'total_destinations': len(route),
                                'total_distance_km': total_distance,
                                'estimated_cost_usd': costs['total_estimated_cost_usd'],
                                'time_efficiency': round(len(route) / max(1, travel_time), 2)
                            }
                        })
                        
                except Exception as e:
                    logger.warning(f"Error generating alternative route {i+1}: {e}")
                    continue
            
            # Sort alternatives by total score
            alternatives.sort(key=lambda x: x['total_score'], reverse=True)
            
            logger.info(f"Generated {len(alternatives)} alternative routes")
            return alternatives
            
        except Exception as e:
            logger.error(f"Error generating alternative routes: {e}")
            return []

    def validate_destination(self, destination: Dict) -> bool:
        """
        Enhanced destination validation with better error handling
        """
        try:
            if not isinstance(destination, dict):
                logger.warning("Destination must be a dictionary")
                return False
                
            required_fields = ['name', 'latitude', 'longitude']
            
            for field in required_fields:
                if field not in destination or destination[field] is None:
                    logger.warning(f"Missing required field '{field}' in destination")
                    return False
            
            # Validate name is not empty
            if not str(destination['name']).strip():
                logger.warning("Destination name cannot be empty")
                return False
                
            # Validate coordinates
            try:
                lat = float(destination['latitude'])
                lon = float(destination['longitude'])
                
                if not self._validate_coordinates(lat, lon):
                    logger.warning(f"Invalid coordinate values in destination: {destination.get('name', 'Unknown')}")
                    return False
                    
            except (ValueError, TypeError):
                logger.warning(f"Invalid coordinate values in destination: {destination.get('name', 'Unknown')}")
                return False
            
            # Validate and sanitize optional fields
            optional_fields = {
                'rating': (0.0, 10.0, 4.0),
                'traffic_score': (1.0, 10.0, 5.0),
                'weather_match': (0.0, 10.0, 8.0),
                'stay_duration': (0.0, 48.0, 2.0)
            }
            
            for field, (min_val, max_val, default_val) in optional_fields.items():
                if field in destination and destination[field] is not None:
                    try:
                        value = float(destination[field])
                        if not (min_val <= value <= max_val):
                            logger.warning(f"Field '{field}' value {value} out of range [{min_val}, {max_val}]. Using default.")
                            destination[field] = default_val
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid value for field '{field}'. Using default.")
                        destination[field] = default_val
                else:
                    # Set default if not present
                    destination[field] = default_val
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating destination: {e}")
            return False


# ✅ Global service instance with enhanced error handling
try:
    algorithm_service = EnhancedGreedyAlgorithmService()
    logger.info("✅ Enhanced Greedy Algorithm Service initialized successfully (zero dependencies)")
except Exception as e:
    logger.error(f"❌ Failed to initialize Enhanced Greedy Algorithm Service: {e}")
    algorithm_service = None

# Export for compatibility
if algorithm_service:
    logger.info("🧠 Algorithm service ready for complete itinerary optimization with time scheduling")
else:
    logger.warning("⚠️ Algorithm service not available - itinerary features will be limited")
