from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
import asyncio
import uuid

logger = logging.getLogger(__name__)

# ✅ Enhanced Enums
class NotificationType(str, Enum):
    WEATHER = "weather"
    FLIGHT = "flight"
    SCHEDULE = "schedule"
    TRAFFIC = "traffic"
    ECO_ACHIEVEMENT = "eco_achievement"
    HIDDEN_GEM = "hidden_gem"
    ITINERARY_CHANGE = "itinerary_change"
    EMERGENCY = "emergency"
    REMINDER = "reminder"
    CUSTOM = "custom"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

# ✅ Enhanced Pydantic Models
class NotificationRequest(BaseModel):
    type: NotificationType = Field(NotificationType.CUSTOM, description="Notification type")
    title: str = Field(..., min_length=1, max_length=100, description="Notification title")
    message: str = Field(..., min_length=1, max_length=500, description="Notification message")
    priority: Priority = Field(Priority.MEDIUM, description="Notification priority")
    action_url: Optional[str] = Field(None, description="URL to navigate when clicked")
    icon: Optional[str] = Field(None, description="Custom icon for notification")
    expires_at: Optional[str] = Field(None, description="Expiration time (ISO format)")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")

class WeatherAlert(BaseModel):
    location: str = Field(..., min_length=1, max_length=100)
    condition: str = Field(..., min_length=1, max_length=200)
    temperature: Optional[int] = Field(None, description="Temperature in Celsius")
    humidity: Optional[int] = Field(None, ge=0, le=100, description="Humidity percentage")
    wind_speed: Optional[float] = Field(None, ge=0, description="Wind speed in km/h")

class FlightUpdate(BaseModel):
    flight_number: str = Field(..., min_length=2, max_length=10)
    status: str = Field(..., description="Flight status")
    delay_minutes: int = Field(0, ge=0, description="Delay in minutes")
    gate: Optional[str] = Field(None, description="Gate number")
    terminal: Optional[str] = Field(None, description="Terminal")
    estimated_time: Optional[str] = Field(None, description="New estimated time")

class ScheduleAlert(BaseModel):
    activity: str = Field(..., min_length=1, max_length=200)
    delay_minutes: int = Field(0, ge=0)
    location: Optional[str] = Field(None, description="Activity location")
    notes: Optional[str] = Field(None, max_length=300, description="Additional notes")

class TrafficAlert(BaseModel):
    route: str = Field(..., min_length=1, max_length=200)
    delay_minutes: int = Field(0, ge=0)
    congestion_level: Optional[str] = Field("medium", regex="^(light|medium|heavy|severe)$")
    alternative_route: Optional[str] = Field(None, description="Suggested alternative")

# ✅ ENHANCED SERVICE WITH MORE FEATURES
class EnhancedNotificationService:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.offline_notifications: Dict[int, List[Dict]] = {}
        self.notification_history: Dict[int, List[Dict]] = {}
        self.user_preferences: Dict[int, Dict[str, bool]] = {}
        self.notification_stats = {
            "total_sent": 0,
            "by_type": {},
            "by_priority": {}
        }
    
    async def connect_user(self, user_id: int, websocket: WebSocket):
        """Connect user to WebSocket"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Send welcome message
        welcome_msg = {
            "type": "system",
            "title": "🔔 Notifications Connected",
            "message": "You're now connected to real-time notifications!",
            "priority": "low",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            await websocket.send_text(json.dumps(welcome_msg))
        except:
            pass
        
        logger.info(f"User {user_id} connected for notifications")
        
        # Send any offline notifications
        await self.send_offline_notifications(user_id)
    
    def disconnect_user(self, user_id: int, websocket: WebSocket):
        """Disconnect user from WebSocket"""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from notifications")
    
    async def send_offline_notifications(self, user_id: int):
        """Send stored offline notifications when user reconnects"""
        if user_id in self.offline_notifications and self.offline_notifications[user_id]:
            for notification in self.offline_notifications[user_id]:
                if user_id in self.active_connections:
                    for websocket in self.active_connections[user_id]:
                        try:
                            await websocket.send_text(json.dumps(notification))
                        except:
                            continue
            
            # Clear offline notifications after sending
            self.offline_notifications[user_id] = []
    
    def should_send_notification(self, user_id: int, notification_type: str) -> bool:
        """Check if user wants to receive this type of notification"""
        preferences = self.user_preferences.get(user_id, {})
        return preferences.get(notification_type, True)  # Default to True
    
    async def send_notification(self, user_id: int, notification: Dict):
        """Send notification to user"""
        notification_id = str(uuid.uuid4())
        notification_data = {
            **notification,
            "id": notification_id,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id
        }
        
        # Check user preferences
        if not self.should_send_notification(user_id, notification.get("type", "custom")):
            logger.info(f"Notification blocked by user {user_id} preferences: {notification.get('type')}")
            return
        
        # Store in history
        if user_id not in self.notification_history:
            self.notification_history[user_id] = []
        self.notification_history[user_id].append(notification_data)
        
        # Keep only last 50 notifications per user
        if len(self.notification_history[user_id]) > 50:
            self.notification_history[user_id] = self.notification_history[user_id][-50:]
        
        # Update statistics
        self.notification_stats["total_sent"] += 1
        notif_type = notification.get("type", "unknown")
        notif_priority = notification.get("priority", "medium")
        
        self.notification_stats["by_type"][notif_type] = self.notification_stats["by_type"].get(notif_type, 0) + 1
        self.notification_stats["by_priority"][notif_priority] = self.notification_stats["by_priority"].get(notif_priority, 0) + 1
        
        # Send to active connections
        if user_id in self.active_connections:
            connections_to_remove = []
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(notification_data))
                    logger.info(f"Sent notification to user {user_id}: {notification.get('title', 'No title')}")
                except Exception as e:
                    logger.error(f"WebSocket send failed for user {user_id}: {e}")
                    connections_to_remove.append(websocket)
            
            # Remove dead connections
            for dead_connection in connections_to_remove:
                self.active_connections[user_id].remove(dead_connection)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        else:
            # Store for offline users
            if user_id not in self.offline_notifications:
                self.offline_notifications[user_id] = []
            self.offline_notifications[user_id].append(notification_data)
            
            # Keep only last 10 offline notifications
            if len(self.offline_notifications[user_id]) > 10:
                self.offline_notifications[user_id] = self.offline_notifications[user_id][-10:]
    
    async def send_weather_alert(self, user_id: int, weather_data: WeatherAlert):
        """Send enhanced weather notification"""
        severity_icons = {
            "sunny": "☀️",
            "cloudy": "☁️",
            "rainy": "🌧️",
            "stormy": "⛈️",
            "snowy": "❄️",
            "foggy": "🌫️"
        }
        
        condition_lower = weather_data.condition.lower()
        icon = "🌦️"  # default
        for weather_type, emoji in severity_icons.items():
            if weather_type in condition_lower:
                icon = emoji
                break
        
        priority = Priority.HIGH if any(word in condition_lower for word in ["storm", "severe", "heavy", "extreme"]) else Priority.MEDIUM
        
        message = f"Weather update for {weather_data.location}: {weather_data.condition}"
        if weather_data.temperature is not None:
            message += f" • {weather_data.temperature}°C"
        if weather_data.humidity is not None:
            message += f" • {weather_data.humidity}% humidity"
        
        notification = {
            "type": NotificationType.WEATHER,
            "title": f"{icon} Weather Alert",
            "message": message,
            "priority": priority,
            "icon": icon,
            "data": {
                "location": weather_data.location,
                "condition": weather_data.condition,
                "temperature": weather_data.temperature,
                "humidity": weather_data.humidity,
                "wind_speed": weather_data.wind_speed
            }
        }
        await self.send_notification(user_id, notification)
    
    async def send_flight_update(self, user_id: int, flight_data: FlightUpdate):
        """Send enhanced flight notification"""
        icon = "✈️"
        priority = Priority.MEDIUM
        
        if flight_data.delay_minutes > 60:
            priority = Priority.HIGH
            icon = "⏰"
        elif flight_data.delay_minutes > 30:
            priority = Priority.MEDIUM
            icon = "⚠️"
        
        if flight_data.delay_minutes > 0:
            message = f"Flight {flight_data.flight_number} delayed by {flight_data.delay_minutes} minutes"
            if flight_data.estimated_time:
                message += f" • New time: {flight_data.estimated_time}"
        else:
            message = f"Flight {flight_data.flight_number}: {flight_data.status}"
        
        if flight_data.gate:
            message += f" • Gate: {flight_data.gate}"
        if flight_data.terminal:
            message += f" • Terminal: {flight_data.terminal}"
            
        notification = {
            "type": NotificationType.FLIGHT,
            "title": f"{icon} Flight Update",
            "message": message,
            "priority": priority,
            "icon": icon,
            "data": flight_data.dict()
        }
        await self.send_notification(user_id, notification)
    
    async def send_schedule_alert(self, user_id: int, schedule_data: ScheduleAlert):
        """Send enhanced schedule notification"""
        if schedule_data.delay_minutes > 45:
            title = "🚨 Severely Delayed!"
            priority = Priority.URGENT
        elif schedule_data.delay_minutes > 30:
            title = "⏰ Running Very Late!"
            priority = Priority.HIGH
        elif schedule_data.delay_minutes > 15:
            title = "⏰ Running Late"
            priority = Priority.MEDIUM
        else:
            title = "📅 Upcoming Activity"
            priority = Priority.LOW
            
        message = f"{schedule_data.activity}"
        if schedule_data.delay_minutes > 0:
            message += f" • {schedule_data.delay_minutes} min delay"
        if schedule_data.location:
            message += f" • Location: {schedule_data.location}"
        if schedule_data.notes:
            message += f" • {schedule_data.notes}"
            
        notification = {
            "type": NotificationType.SCHEDULE,
            "title": title,
            "message": message,
            "priority": priority,
            "icon": "📅",
            "data": schedule_data.dict()
        }
        await self.send_notification(user_id, notification)
    
    async def send_traffic_alert(self, user_id: int, traffic_data: TrafficAlert):
        """Send enhanced traffic notification"""
        congestion_icons = {
            "light": "🟢",
            "medium": "🟡",
            "heavy": "🔴",
            "severe": "🚨"
        }
        
        icon = congestion_icons.get(traffic_data.congestion_level, "🚗")
        priority = Priority.HIGH if traffic_data.congestion_level in ["heavy", "severe"] else Priority.MEDIUM
        
        message = f"Traffic on {traffic_data.route}: +{traffic_data.delay_minutes} min delay"
        message += f" • {traffic_data.congestion_level.title()} congestion"
        
        if traffic_data.alternative_route:
            message += f" • Alternative: {traffic_data.alternative_route}"
            
        notification = {
            "type": NotificationType.TRAFFIC,
            "title": f"{icon} Traffic Alert",
            "message": message,
            "priority": priority,
            "icon": icon,
            "data": traffic_data.dict()
        }
        await self.send_notification(user_id, notification)
    
    async def send_eco_achievement(self, user_id: int, achievement: str, points: int):
        """Send eco achievement notification"""
        notification = {
            "type": NotificationType.ECO_ACHIEVEMENT,
            "title": "🌱 Eco Achievement Unlocked!",
            "message": f"{achievement} • +{points} eco points earned!",
            "priority": Priority.MEDIUM,
            "icon": "🏆",
            "data": {
                "achievement": achievement,
                "points": points,
                "category": "eco_achievement"
            }
        }
        await self.send_notification(user_id, notification)
    
    async def send_hidden_gem_alert(self, user_id: int, gem_name: str, distance: float):
        """Send hidden gem discovery notification"""
        notification = {
            "type": NotificationType.HIDDEN_GEM,
            "title": "💎 Hidden Gem Nearby!",
            "message": f"{gem_name} is just {distance:.0f}m away. Discover it for eco points!",
            "priority": Priority.MEDIUM,
            "icon": "💎",
            "data": {
                "gem_name": gem_name,
                "distance_meters": distance
            }
        }
        await self.send_notification(user_id, notification)
    
    def update_user_preferences(self, user_id: int, preferences: Dict[str, bool]):
        """Update user notification preferences"""
        self.user_preferences[user_id] = preferences
    
    def get_user_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get user notification history"""
        history = self.notification_history.get(user_id, [])
        return history[-limit:]
    
    def get_statistics(self) -> Dict:
        """Get notification service statistics"""
        return {
            "active_connections": len(self.active_connections),
            "total_connected_users": len(self.active_connections),
            "total_notifications_sent": self.notification_stats["total_sent"],
            "notifications_by_type": self.notification_stats["by_type"],
            "notifications_by_priority": self.notification_stats["by_priority"],
            "users_with_offline_notifications": len(self.offline_notifications)
        }

# ✅ Create enhanced service instance
notification_service = EnhancedNotificationService()

# ✅ Create router
router = APIRouter(prefix="/simple-notifications", tags=["📱 Smart Notifications"])

# ✅ WebSocket endpoint
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """🔌 WebSocket connection for real-time notifications"""
    try:
        await notification_service.connect_user(user_id, websocket)
        
        # Keep connection alive and handle ping/pong
        while True:
            try:
                message = await websocket.receive_text()
                
                # Handle ping/pong to keep connection alive
                if message == "ping":
                    await websocket.send_text("pong")
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket receive error for user {user_id}: {e}")
                break
                
    except WebSocketDisconnect:
        notification_service.disconnect_user(user_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        notification_service.disconnect_user(user_id, websocket)

# ✅ Enhanced API endpoints
@router.post("/send",
             summary="Send Custom Notification",
             description="Send a custom notification to a user")
async def send_custom_notification(
    notification: NotificationRequest,
    user_id: int = Query(1, description="User ID to send notification to")
):
    """📤 Send custom notification"""
    try:
        notification_data = notification.dict()
        await notification_service.send_notification(user_id, notification_data)
        
        return {
            "success": True,
            "status": "sent",
            "message": "Notification sent successfully",
            "user_id": user_id,
            "notification_id": f"custom_{user_id}_{datetime.now().timestamp()}"
        }
        
    except Exception as e:
        logger.error(f"Send notification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Send notification failed: {str(e)}")

@router.post("/weather",
             summary="Send Weather Alert",
             description="Send weather notification with detailed information")
async def send_weather_notification(
    weather: WeatherAlert,
    user_id: int = Query(1, description="User ID")
):
    """🌦️ Send enhanced weather notification"""
    try:
        await notification_service.send_weather_alert(user_id, weather)
        return {
            "success": True,
            "status": "sent",
            "type": "weather",
            "message": f"Weather alert sent for {weather.location}",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Weather notification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Weather notification failed: {str(e)}")

@router.post("/flight",
             summary="Send Flight Update",
             description="Send flight status notification with gate and terminal info")
async def send_flight_notification(
    flight: FlightUpdate,
    user_id: int = Query(1, description="User ID")
):
    """✈️ Send enhanced flight notification"""
    try:
        await notification_service.send_flight_update(user_id, flight)
        return {
            "success": True,
            "status": "sent",
            "type": "flight",
            "message": f"Flight {flight.flight_number} notification sent",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Flight notification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Flight notification failed: {str(e)}")

@router.post("/schedule",
             summary="Send Schedule Alert",
             description="Send schedule notification with location and notes")
async def send_schedule_notification(
    schedule: ScheduleAlert,
    user_id: int = Query(1, description="User ID")
):
    """⏰ Send enhanced schedule notification"""
    try:
        await notification_service.send_schedule_alert(user_id, schedule)
        return {
            "success": True,
            "status": "sent",
            "type": "schedule",
            "message": f"Schedule alert sent for {schedule.activity}",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Schedule notification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Schedule notification failed: {str(e)}")

@router.post("/traffic",
             summary="Send Traffic Alert",
             description="Send traffic notification with congestion level and alternatives")
async def send_traffic_notification(
    traffic: TrafficAlert,
    user_id: int = Query(1, description="User ID")
):
    """🚗 Send enhanced traffic notification"""
    try:
        await notification_service.send_traffic_alert(user_id, traffic)
        return {
            "success": True,
            "status": "sent",
            "type": "traffic",
            "message": f"Traffic alert sent for {traffic.route}",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Traffic notification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Traffic notification failed: {str(e)}")

@router.post("/eco-achievement",
             summary="Send Eco Achievement",
             description="Send eco achievement notification")
async def send_eco_achievement_notification(
    achievement: str = Query(..., description="Achievement name"),
    points: int = Query(..., ge=1, description="Points earned"),
    user_id: int = Query(1, description="User ID")
):
    """🌱 Send eco achievement notification"""
    try:
        await notification_service.send_eco_achievement(user_id, achievement, points)
        return {
            "success": True,
            "status": "sent",
            "type": "eco_achievement",
            "message": f"Eco achievement sent: {achievement} (+{points} points)",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Eco achievement notification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Eco achievement notification failed: {str(e)}")

@router.post("/hidden-gem",
             summary="Send Hidden Gem Alert",
             description="Send hidden gem discovery notification")
async def send_hidden_gem_notification(
    gem_name: str = Query(..., description="Hidden gem name"),
    distance: float = Query(..., ge=0, description="Distance in meters"),
    user_id: int = Query(1, description="User ID")
):
    """💎 Send hidden gem notification"""
    try:
        await notification_service.send_hidden_gem_alert(user_id, gem_name, distance)
        return {
            "success": True,
            "status": "sent",
            "type": "hidden_gem",
            "message": f"Hidden gem alert sent: {gem_name} ({distance}m away)",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Hidden gem notification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Hidden gem notification failed: {str(e)}")

@router.get("/history/{user_id}",
            summary="Get Notification History",
            description="Get user's notification history")
async def get_notification_history(
    user_id: int,
    limit: int = Query(20, ge=1, le=100, description="Number of notifications to return")
):
    """📜 Get user notification history"""
    try:
        history = notification_service.get_user_history(user_id, limit)
        
        return {
            "success": True,
            "user_id": user_id,
            "notifications": history,
            "count": len(history),
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Get notification history failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get notification history failed: {str(e)}")

@router.put("/preferences/{user_id}",
            summary="Update Notification Preferences",
            description="Update user's notification preferences")
async def update_notification_preferences(
    user_id: int,
    preferences: Dict[str, bool]
):
    """⚙️ Update user notification preferences"""
    try:
        notification_service.update_user_preferences(user_id, preferences)
        
        return {
            "success": True,
            "user_id": user_id,
            "preferences": preferences,
            "message": "Notification preferences updated successfully"
        }
    except Exception as e:
        logger.error(f"Update preferences failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update preferences failed: {str(e)}")

@router.get("/statistics",
            summary="Get Notification Statistics",
            description="Get notification service statistics")
async def get_notification_statistics():
    """📊 Get notification service statistics"""
    try:
        stats = notification_service.get_statistics()
        
        return {
            "success": True,
            "statistics": stats,
            "service_status": "healthy",
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Get statistics failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get statistics failed: {str(e)}")

@router.post("/demo",
             summary="Send Demo Notifications",
             description="Send demo notifications for hackathon presentation")
async def send_demo_notifications(user_id: int = Query(1, description="User ID")):
    """🎯 Send demo notifications for hackathon presentation"""
    try:
        # Demo notifications with realistic data
        demo_notifications = [
            WeatherAlert(location="Paris", condition="Heavy Rain Expected", temperature=15, humidity=85),
            FlightUpdate(flight_number="AI101", status="delayed", delay_minutes=30, gate="A12", terminal="T2"),
            ScheduleAlert(activity="Louvre Museum Visit", delay_minutes=15, location="Rue de Rivoli, Paris"),
            TrafficAlert(route="A1 Highway", delay_minutes=25, congestion_level="heavy", alternative_route="Ring Road")
        ]
        
        # Send weather alert
        await notification_service.send_weather_alert(user_id, demo_notifications[0])
        await asyncio.sleep(0.5)
        
        # Send flight update
        await notification_service.send_flight_update(user_id, demo_notifications[1])
        await asyncio.sleep(0.5)
        
        # Send schedule alert
        await notification_service.send_schedule_alert(user_id, demo_notifications[2])
        await asyncio.sleep(0.5)
        
        # Send traffic alert
        await notification_service.send_traffic_alert(user_id, demo_notifications[3])
        await asyncio.sleep(0.5)
        
        # Send eco achievement
        await notification_service.send_eco_achievement(user_id, "Green Commuter Level 2", 50)
        await asyncio.sleep(0.5)
        
        # Send hidden gem alert
        await notification_service.send_hidden_gem_alert(user_id, "Secret Rooftop Cafe", 150)
        
        return {
            "success": True,
            "status": "demo_completed",
            "message": "🎉 Demo notifications sent successfully!",
            "notifications_sent": 6,
            "user_id": user_id,
            "types": ["weather", "flight", "schedule", "traffic", "eco_achievement", "hidden_gem"],
            "demo_note": "Perfect for hackathon presentation! All notification types demonstrated."
        }
        
    except Exception as e:
        logger.error(f"Demo notifications failed: {e}")
        raise HTTPException(status_code=500, detail=f"Demo notifications failed: {str(e)}")

@router.get("/test",
            summary="Test Notification System",
            description="Test endpoint to verify notification system health")
async def test_notifications():
    """🧪 Test notification system"""
    
    stats = notification_service.get_statistics()
    
    return {
        "success": True,
        "status": "healthy",
        "message": "Smart notification system operational",
        "features": [
            "Real-time WebSocket notifications",
            "Enhanced weather alerts with temperature & humidity",
            "Flight updates with gate & terminal info", 
            "Schedule alerts with location & priority",
            "Traffic alerts with congestion levels",
            "Eco achievement notifications",
            "Hidden gem discovery alerts",
            "Notification history & preferences",
            "Offline notification storage"
        ],
        "statistics": stats,
        "endpoints": {
            "websocket": "ws://localhost:8000/api/simple-notifications/ws/{user_id}",
            "custom": "POST /api/simple-notifications/send",
            "weather": "POST /api/simple-notifications/weather",
            "flight": "POST /api/simple-notifications/flight",
            "schedule": "POST /api/simple-notifications/schedule", 
            "traffic": "POST /api/simple-notifications/traffic",
            "eco_achievement": "POST /api/simple-notifications/eco-achievement",
            "hidden_gem": "POST /api/simple-notifications/hidden-gem",
            "demo": "POST /api/simple-notifications/demo",
            "history": "GET /api/simple-notifications/history/{user_id}",
            "preferences": "PUT /api/simple-notifications/preferences/{user_id}",
            "statistics": "GET /api/simple-notifications/statistics"
        },
        "supported_types": [t.value for t in NotificationType],
        "priority_levels": [p.value for p in Priority]
    }

@router.get("/health",
            summary="Notification Service Health",
            description="Check notification service health status")
async def notification_service_health():
    """🏥 Notification service health check"""
    
    stats = notification_service.get_statistics()
    
    return {
        "service": "simple_notifications",
        "status": "healthy",
        "features": {
            "real_time_websockets": True,
            "offline_storage": True,
            "user_preferences": True,
            "notification_history": True,
            "priority_levels": True,
            "enhanced_data": True,
            "demo_mode": True
        },
        "statistics": stats,
        "notification_types": len(NotificationType),
        "priority_levels": len(Priority),
        "version": "2.0.0"
    }
