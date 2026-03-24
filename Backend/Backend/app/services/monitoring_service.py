# app/services/monitoring_service.py
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from ..database import get_db, User, Trip, UserFlight
from .notification_service import notification_service
from .external_apis import weather_service

logger = logging.getLogger(__name__)

class TravelMonitoringService:
    def __init__(self):
        self.monitoring_active = False
        self.check_interval = 300  # 5 minutes
        self.user_locations = {}  # user_id -> last_known_location
        
    async def start_monitoring(self):
        """Start background monitoring for all travel alerts"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        logger.info("🔍 Travel monitoring service started")
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_weather())
        asyncio.create_task(self._monitor_flights())
        asyncio.create_task(self._monitor_schedules()) 
        asyncio.create_task(self._monitor_traffic())

    async def stop_monitoring(self):
        """Stop monitoring service"""
        self.monitoring_active = False
        logger.info("🔍 Travel monitoring service stopped")

    async def _monitor_weather(self):
        """Monitor weather changes for active trips"""
        while self.monitoring_active:
            try:
                # Get active trips
                db = next(get_db())
                active_trips = db.query(Trip).filter(
                    Trip.start_date <= datetime.now(),
                    Trip.end_date >= datetime.now()
                ).all()
                
                for trip in active_trips:
                    try:
                        # Get weather for destination
                        if weather_service:
                            weather_data = await weather_service.get_current_weather(
                                trip.destination
                            )
                            
                            if weather_data and self._is_weather_alert_worthy(weather_data):
                                # Create weather alert
                                notification = await notification_service.create_weather_alert(
                                    user_id=trip.user_id,
                                    location=trip.destination,
                                    weather_data=weather_data
                                )
                                
                                # Send notification
                                await notification_service.send_push_notification(
                                    trip.user_id, notification
                                )
                                
                    except Exception as e:
                        logger.error(f"Weather monitoring failed for trip {trip.id}: {e}")
                
                db.close()
                
            except Exception as e:
                logger.error(f"Weather monitoring error: {e}")
            
            # Wait before next check
            await asyncio.sleep(self.check_interval)

    async def _monitor_flights(self):
        """Monitor flight status changes"""
        while self.monitoring_active:
            try:
                # Get tracked flights
                db = next(get_db())
                tracked_flights = db.query(UserFlight).filter(
                    UserFlight.is_tracking == True,
                    UserFlight.flight_date >= datetime.now() - timedelta(hours=2),
                    UserFlight.flight_date <= datetime.now() + timedelta(hours=24)
                ).all()
                
                for flight in tracked_flights:
                    try:
                        # Check flight status (implement flight API call)
                        flight_status = await self._get_flight_status(flight.flight_number)
                        
                        if flight_status and self._has_flight_status_changed(flight, flight_status):
                            # Update flight record
                            flight.current_status = flight_status.get("status", "unknown")
                            flight.delay_minutes = flight_status.get("delay_minutes", 0)
                            flight.last_checked = datetime.now()
                            
                            # Create flight notification
                            notification = await notification_service.create_flight_update(
                                user_id=flight.user_id,
                                flight_data={
                                    "flight_number": flight.flight_number,
                                    "status": flight.current_status,
                                    "delay_minutes": flight.delay_minutes,
                                    **flight_status
                                }
                            )
                            
                            # Send notification
                            await notification_service.send_push_notification(
                                flight.user_id, notification
                            )
                            
                    except Exception as e:
                        logger.error(f"Flight monitoring failed for {flight.flight_number}: {e}")
                
                db.commit()
                db.close()
                
            except Exception as e:
                logger.error(f"Flight monitoring error: {e}")
            
            await asyncio.sleep(self.check_interval)

    async def _monitor_schedules(self):
        """Monitor user schedules and detect delays"""
        while self.monitoring_active:
            try:
                # Get active trips with itineraries
                db = next(get_db())
                current_time = datetime.now()
                
                # Check for schedule delays (simplified logic)
                # In a real app, you'd track user location and compare with planned schedule
                
                # Simulate schedule check for demo
                for user_id in [1, 2, 3]:  # Replace with actual active users
                    if user_id in self.user_locations:
                        user_location = self.user_locations[user_id]
                        
                        # Check if user is behind schedule (mock implementation)
                        delay_minutes = await self._calculate_schedule_delay(user_id, user_location)
                        
                        if delay_minutes > 10:  # More than 10 minutes late
                            notification = await notification_service.create_schedule_delay_alert(
                                user_id=user_id,
                                activity="Next scheduled activity",
                                delay_minutes=delay_minutes,
                                current_location=user_location
                            )
                            
                            await notification_service.send_push_notification(
                                user_id, notification
                            )
                
                db.close()
                
            except Exception as e:
                logger.error(f"Schedule monitoring error: {e}")
            
            await asyncio.sleep(self.check_interval)

    async def _monitor_traffic(self):
        """Monitor traffic conditions for active routes"""
        while self.monitoring_active:
            try:
                # Monitor traffic for users with active navigation
                for user_id, location in self.user_locations.items():
                    try:
                        # Get traffic data (implement with Google Maps/traffic API)
                        traffic_data = await self._get_traffic_data(location)
                        
                        if traffic_data and traffic_data.get("delay_minutes", 0) > 15:
                            notification = await notification_service.create_traffic_alert(
                                user_id=user_id,
                                route=traffic_data.get("route", "Current route"),
                                delay_minutes=traffic_data["delay_minutes"],
                                alternative_route=traffic_data.get("alternative")
                            )
                            
                            await notification_service.send_push_notification(
                                user_id, notification
                            )
                            
                    except Exception as e:
                        logger.error(f"Traffic monitoring failed for user {user_id}: {e}")
                
            except Exception as e:
                logger.error(f"Traffic monitoring error: {e}")
            
            await asyncio.sleep(self.check_interval)

    # Helper methods
    def _is_weather_alert_worthy(self, weather_data: Dict) -> bool:
        """Check if weather conditions warrant an alert"""
        condition = weather_data.get("condition", "").lower()
        temp = weather_data.get("temperature", 20)
        
        # Alert conditions
        if any(keyword in condition for keyword in ["rain", "storm", "snow", "thunderstorm"]):
            return True
        if temp < 5 or temp > 35:  # Extreme temperatures
            return True
        if weather_data.get("wind_speed", 0) > 25:  # High wind
            return True
            
        return False

    def _has_flight_status_changed(self, flight: UserFlight, new_status: Dict) -> bool:
        """Check if flight status has meaningfully changed"""
        old_status = flight.current_status
        new_status_str = new_status.get("status", "unknown")
        
        old_delay = flight.delay_minutes
        new_delay = new_status.get("delay_minutes", 0)
        
        # Status change
        if old_status != new_status_str:
            return True
        
        # Significant delay change (more than 10 minutes)
        if abs(old_delay - new_delay) > 10:
            return True
            
        return False

    async def _get_flight_status(self, flight_number: str) -> Dict:
        """Get current flight status (implement with aviation API)"""
        # Mock implementation - replace with real API call
        return {
            "status": "on_time",
            "delay_minutes": 0,
            "gate": "A12",
            "terminal": "1"
        }

    async def _calculate_schedule_delay(self, user_id: int, location: Dict) -> int:
        """Calculate how late user is for their schedule"""
        # Mock implementation - replace with real calculation
        # This would compare user's current location with scheduled location
        return 0

    async def _get_traffic_data(self, location: Dict) -> Dict:
        """Get traffic data for location"""
        # Mock implementation - replace with real traffic API
        return {
            "route": "Main route",
            "delay_minutes": 5,
            "alternative": "Highway route"
        }

    # Location tracking
    def update_user_location(self, user_id: int, latitude: float, longitude: float):
        """Update user's current location for monitoring"""
        self.user_locations[user_id] = {
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": datetime.now()
        }

# Global monitoring service instance
monitoring_service = TravelMonitoringService()
