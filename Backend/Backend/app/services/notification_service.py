# app/services/notification_service.py
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import asyncio
from enum import Enum

# ✅ Remove httpx import - causes issues with Python 3.13
# import httpx

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    WEATHER_ALERT = "weather_alert"
    TRAFFIC_DELAY = "traffic_delay"
    FLIGHT_UPDATE = "flight_update"
    SCHEDULE_DELAY = "schedule_delay"
    ITINERARY_CHANGE = "itinerary_change"

@dataclass
class Notification:
    id: str
    user_id: int
    type: NotificationType
    title: str
    message: str
    data: Dict
    priority: str  # high, medium, low
    created_at: datetime
    sent_at: Optional[datetime] = None

class NotificationService:
    def __init__(self):
        # ✅ Simplified for hackathon - no external APIs needed
        self.development_mode = True
        
        # In-memory storage (perfect for demo)
        self.notification_queue = []
        self.user_subscriptions = {}  # user_id -> device_tokens
        self.sent_notifications = []  # Store sent notifications for demo
        
        logger.info("🔔 Simple Notification service initialized")

    async def send_push_notification(
        self, 
        user_id: int, 
        notification: Notification
    ) -> Dict:
        """Send push notification - simplified for hackathon"""
        try:
            # ✅ Store notification for demo purposes
            notification_data = {
                "id": notification.id,
                "user_id": user_id,
                "type": notification.type.value,
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority,
                "data": notification.data,
                "created_at": notification.created_at.isoformat(),
                "sent_at": datetime.now().isoformat()
            }
            
            # Add to sent notifications for tracking
            self.sent_notifications.append(notification_data)
            
            # Keep only last 50 notifications for demo
            if len(self.sent_notifications) > 50:
                self.sent_notifications = self.sent_notifications[-50:]
            
            # Update notification status
            notification.sent_at = datetime.now()
            
            logger.info(f"📱 Notification sent to user {user_id}: {notification.title}")
            
            return {
                "notification_id": notification.id,
                "status": "sent",
                "success": True,
                "user_id": user_id,
                "title": notification.title,
                "message": notification.message,
                "timestamp": notification.sent_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Push notification failed: {e}")
            return {
                "notification_id": notification.id,
                "status": "failed",
                "success": False,
                "error": str(e)
            }

    # ✅ Simplified notification creators for hackathon
    async def create_weather_alert(
        self, 
        user_id: int, 
        location: str, 
        weather_data: Dict
    ) -> Notification:
        """Create weather alert notification"""
        condition = weather_data.get("condition", "Unknown")
        temp = weather_data.get("temperature", "N/A")
        
        if "rain" in condition.lower() or "storm" in condition.lower():
            title = "⛈️ Weather Alert!"
            message = f"Rain expected in {location}. Consider indoor activities."
            priority = "high"
        elif "snow" in condition.lower():
            title = "❄️ Snow Alert!"
            message = f"Snow forecast for {location}. Plan for delays."
            priority = "high"
        else:
            title = "🌤️ Weather Update"
            message = f"{location}: {condition}, {temp}°C"
            priority = "medium"
        
        return Notification(
            id=f"weather_{user_id}_{int(datetime.now().timestamp())}",
            user_id=user_id,
            type=NotificationType.WEATHER_ALERT,
            title=title,
            message=message,
            data={
                "location": location,
                "weather": weather_data,
                "action": "check_itinerary"
            },
            priority=priority,
            created_at=datetime.now()
        )

    async def create_flight_update(
        self, 
        user_id: int, 
        flight_data: Dict
    ) -> Notification:
        """Create flight update notification"""
        flight_no = flight_data.get("flight_number", "Unknown")
        status = flight_data.get("status", "unknown")
        delay_minutes = flight_data.get("delay_minutes", 0)
        
        if status == "delayed":
            title = "✈️ Flight Delayed"
            message = f"Flight {flight_no} delayed by {delay_minutes} minutes"
            priority = "high"
        elif status == "cancelled":
            title = "❌ Flight Cancelled"
            message = f"Flight {flight_no} has been cancelled"
            priority = "high"
        elif status == "boarding":
            title = "🛫 Flight Boarding"
            message = f"Flight {flight_no} is now boarding"
            priority = "high"
        else:
            title = "✈️ Flight Update"
            message = f"Flight {flight_no}: {status}"
            priority = "medium"
        
        return Notification(
            id=f"flight_{user_id}_{flight_no}_{int(datetime.now().timestamp())}",
            user_id=user_id,
            type=NotificationType.FLIGHT_UPDATE,
            title=title,
            message=message,
            data={
                "flight": flight_data,
                "action": "view_flight_details"
            },
            priority=priority,
            created_at=datetime.now()
        )

    async def create_schedule_delay_alert(
        self, 
        user_id: int, 
        activity: str, 
        delay_minutes: int,
        current_location: Optional[Dict] = None
    ) -> Notification:
        """Create schedule delay notification"""
        if delay_minutes > 30:
            title = "⏰ Running Very Late!"
            message = f"You're {delay_minutes} min late for {activity}. Consider rescheduling."
            priority = "high"
        elif delay_minutes > 15:
            title = "⏰ Running Late"
            message = f"You're {delay_minutes} min behind schedule for {activity}"
            priority = "medium"
        else:
            title = "⏰ Schedule Alert"
            message = f"Upcoming: {activity} in {15-delay_minutes} minutes"
            priority = "low"
        
        return Notification(
            id=f"schedule_{user_id}_{int(datetime.now().timestamp())}",
            user_id=user_id,
            type=NotificationType.SCHEDULE_DELAY,
            title=title,
            message=message,
            data={
                "activity": activity,
                "delay_minutes": delay_minutes,
                "current_location": current_location or {},
                "action": "view_itinerary"
            },
            priority=priority,
            created_at=datetime.now()
        )

    async def create_traffic_alert(
        self, 
        user_id: int, 
        route: str, 
        delay_minutes: int,
        alternative_route: Optional[str] = None
    ) -> Notification:
        """Create traffic delay notification"""
        if delay_minutes > 20:
            title = "🚗 Heavy Traffic Alert!"
            message = f"Expect {delay_minutes} min delay on {route}"
            priority = "high"
        else:
            title = "🚗 Traffic Update"
            message = f"Light traffic on {route} (+{delay_minutes} min)"
            priority = "medium"
        
        if alternative_route:
            message += f"\nSuggested: {alternative_route}"
        
        return Notification(
            id=f"traffic_{user_id}_{int(datetime.now().timestamp())}",
            user_id=user_id,
            type=NotificationType.TRAFFIC_DELAY,
            title=title,
            message=message,
            data={
                "route": route,
                "delay_minutes": delay_minutes,
                "alternative_route": alternative_route,
                "action": "view_navigation"
            },
            priority=priority,
            created_at=datetime.now()
        )

    # ✅ Simple subscription management for demo
    def subscribe_user(self, user_id: int, device_token: str, platform: str = "web"):
        """Subscribe user for push notifications"""
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = []
        
        if device_token not in self.user_subscriptions[user_id]:
            self.user_subscriptions[user_id].append(device_token)
            logger.info(f"User {user_id} subscribed for notifications")

    def unsubscribe_user(self, user_id: int, device_token: Optional[str] = None):
        """Unsubscribe user from push notifications"""
        if user_id in self.user_subscriptions:
            if device_token:
                if device_token in self.user_subscriptions[user_id]:
                    self.user_subscriptions[user_id].remove(device_token)
            else:
                del self.user_subscriptions[user_id]
            logger.info(f"User {user_id} unsubscribed from notifications")

    # ✅ Demo helper methods
    def get_user_notifications(self, user_id: int) -> List[Dict]:
        """Get notifications for a user - useful for demo"""
        return [
            notif for notif in self.sent_notifications 
            if notif["user_id"] == user_id
        ]

    def get_notification_stats(self) -> Dict:
        """Get notification statistics - useful for demo"""
        return {
            "total_sent": len(self.sent_notifications),
            "active_subscriptions": len(self.user_subscriptions),
            "notification_types": list(set(notif["type"] for notif in self.sent_notifications)),
            "recent_notifications": self.sent_notifications[-5:] if self.sent_notifications else []
        }

    # ✅ Quick demo methods
    async def send_demo_weather(self, user_id: int = 1):
        """Send demo weather notification"""
        weather_data = {"condition": "Heavy Rain", "temperature": 15}
        notification = await self.create_weather_alert(user_id, "Paris", weather_data)
        return await self.send_push_notification(user_id, notification)

    async def send_demo_flight(self, user_id: int = 1):
        """Send demo flight notification"""
        flight_data = {"flight_number": "AI101", "status": "delayed", "delay_minutes": 30}
        notification = await self.create_flight_update(user_id, flight_data)
        return await self.send_push_notification(user_id, notification)

    async def send_demo_schedule(self, user_id: int = 1):
        """Send demo schedule notification"""
        notification = await self.create_schedule_delay_alert(user_id, "Museum Visit", 15)
        return await self.send_push_notification(user_id, notification)

    async def send_demo_traffic(self, user_id: int = 1):
        """Send demo traffic notification"""
        notification = await self.create_traffic_alert(user_id, "Highway A1", 20, "Local Route")
        return await self.send_push_notification(user_id, notification)

# Global notification service instance
notification_service = NotificationService()
