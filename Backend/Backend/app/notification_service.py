# app/notification_service.py
import json
import logging
from datetime import datetime
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class SimpleNotificationService:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.offline_notifications: Dict[int, List[Dict]] = {}
        
    async def send_notification(self, user_id: int, notification: Dict):
        """Send notification to user"""
        notification_data = {
            **notification,
            "timestamp": datetime.now().isoformat(),
            "id": f"notif_{user_id}_{datetime.now().timestamp()}"
        }
        
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(notification_data))
                except:
                    pass
        else:
            # Store offline
            if user_id not in self.offline_notifications:
                self.offline_notifications[user_id] = []
            self.offline_notifications[user_id].append(notification_data)

    async def send_weather_alert(self, user_id: int, location: str, condition: str):
        notification = {
            "type": "weather",
            "title": "🌦️ Weather Alert",
            "message": f"Weather update for {location}: {condition}",
            "priority": "medium"
        }
        await self.send_notification(user_id, notification)

    async def send_flight_update(self, user_id: int, flight_no: str, status: str, delay: int = 0):
        message = f"Flight {flight_no} delayed by {delay} minutes" if delay > 0 else f"Flight {flight_no}: {status}"
        notification = {
            "type": "flight",
            "title": "✈️ Flight Update",
            "message": message,
            "priority": "high" if delay > 0 else "medium"
        }
        await self.send_notification(user_id, notification)

    async def send_schedule_alert(self, user_id: int, activity: str, delay_minutes: int):
        title = "⏰ Running Very Late!" if delay_minutes > 30 else "⏰ Running Late"
        notification = {
            "type": "schedule",
            "title": title,
            "message": f"{activity} - {delay_minutes} min delay",
            "priority": "high" if delay_minutes > 30 else "medium"
        }
        await self.send_notification(user_id, notification)

    async def send_traffic_alert(self, user_id: int, route: str, delay: int):
        notification = {
            "type": "traffic",
            "title": "🚗 Traffic Alert",
            "message": f"Traffic on {route}: +{delay} min delay",
            "priority": "medium"
        }
        await self.send_notification(user_id, notification)

# Global service
simple_notification_service = SimpleNotificationService()
class NotificationType:
    WEATHER = "weather"
    FLIGHT = "flight"
    SCHEDULE = "schedule"
    TRAFFIC = "traffic"
    ITINERARY_CHANGE = "itinerary_change"