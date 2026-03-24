from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
import math
import sys
import os
import asyncio

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

logger = logging.getLogger(__name__)

# ✅ Database import handling
try:
    from database import get_db
    DATABASE_AVAILABLE = True
except ImportError:
    def get_db():
        return None
    DATABASE_AVAILABLE = False

# ✅ Create router
router = APIRouter(
    prefix="/notifications",
    tags=["🔔 Smart Push Notifications"]
)

# ✅ Enums
class NotificationType(str, Enum):
    WEATHER_ALERT = "weather_alert"
    FLIGHT_UPDATE = "flight_update"
    SCHEDULE_DELAY = "schedule_delay"
    TRAFFIC_ALERT = "traffic_alert"
    ITINERARY_CHANGE = "itinerary_change"
    ECO_ACHIEVEMENT = "eco_achievement"
    HIDDEN_GEM_NEARBY = "hidden_gem_nearby"
    EMERGENCY_ALERT = "emergency_alert"
    TRAVEL_REMINDER = "travel_reminder"
    PRICE_ALERT = "price_alert"
    LOCATION_ARRIVAL = "location_arrival"
    BUDGET_WARNING = "budget_warning"

class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class PlatformType(str, Enum):
    WEB = "web"
    ANDROID = "android"
    IOS = "ios"

# ✅ Fixed Pydantic Models
class NotificationSubscription(BaseModel):
    device_token: str = Field(..., min_length=10, max_length=500)
    platform: PlatformType = Field(PlatformType.WEB)
    enable_weather: bool = Field(True)
    enable_traffic: bool = Field(True)
    enable_flights: bool = Field(True)
    enable_eco: bool = Field(True)
    enable_hidden_gems: bool = Field(True)
    enable_price_alerts: bool = Field(False)
    quiet_hours_start: Optional[str] = Field("22:00")
    quiet_hours_end: Optional[str] = Field("08:00")
    
    @validator('quiet_hours_start', 'quiet_hours_end')
    def validate_time_format(cls, v):
        if v and len(v) == 5 and v[2] == ':':
            try:
                hour, minute = map(int, v.split(':'))
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return v
            except ValueError:
                pass
        raise ValueError('Time must be in HH:MM format')

class LocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = Field(None, ge=0)
    altitude: Optional[float] = None
    heading: Optional[float] = Field(None, ge=0, le=360)
    speed: Optional[float] = Field(None, ge=0)
    timestamp: Optional[str] = None

class TestNotification(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=500)
    priority: NotificationPriority = Field(NotificationPriority.MEDIUM)
    notification_type: NotificationType = Field(NotificationType.ITINERARY_CHANGE)
    data: Optional[Dict[str, Any]] = None
    action_button: Optional[str] = None
    action_url: Optional[str] = None

class GeofenceCreate(BaseModel):
    center_lat: float = Field(..., ge=-90, le=90)
    center_lng: float = Field(..., ge=-180, le=180)
    radius_meters: float = Field(100, ge=10, le=5000)
    poi_name: Optional[str] = Field(None, max_length=200)
    poi_id: Optional[int] = None

class NotificationPreferences(BaseModel):
    enable_push: bool = Field(True)
    enable_email: bool = Field(False)
    enable_sms: bool = Field(False)
    weather_threshold: str = Field("medium")
    traffic_threshold: str = Field("medium")
    price_drop_percentage: int = Field(10, ge=5, le=50)
    location_radius_km: float = Field(5.0, ge=0.5, le=50.0)
    
    @validator('weather_threshold', 'traffic_threshold')
    def validate_threshold(cls, v):
        if v not in ['low', 'medium', 'high']:
            raise ValueError('Threshold must be low, medium, or high')
        return v

class Notification(BaseModel):
    id: str
    user_id: int
    type: NotificationType
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    priority: NotificationPriority
    created_at: str
    sent_at: Optional[str] = None
    read_at: Optional[str] = None
    clicked_at: Optional[str] = None
    action_button: Optional[str] = None
    action_url: Optional[str] = None
    expires_at: Optional[str] = None

# ✅ Storage
USER_SUBSCRIPTIONS = {}
USER_LOCATIONS = {}
NOTIFICATION_HISTORY = {}
GEOFENCES = {}
MONITORING_ACTIVE = False
NOTIFICATION_STATS = {
    "total_sent": 0,
    "total_delivered": 0,
    "total_clicked": 0,
    "by_type": {},
    "by_priority": {}
}

# ✅ Service Classes
class NotificationService:
    def __init__(self):
        self.user_subscriptions = USER_SUBSCRIPTIONS
        self.notification_history = NOTIFICATION_HISTORY
        self.rate_limits = {}
    
    def _check_rate_limit(self, user_id: int, notification_type: str) -> bool:
        """Check rate limits"""
        now = datetime.now()
        key = f"{user_id}_{notification_type}"
        
        if key not in self.rate_limits:
            self.rate_limits[key] = []
        
        # Remove old entries (older than 1 hour)
        self.rate_limits[key] = [
            timestamp for timestamp in self.rate_limits[key]
            if (now - timestamp).total_seconds() < 3600
        ]
        
        # Check limits
        limits = {
            "weather_alert": 5,
            "traffic_alert": 10,
            "flight_update": 20,
            "eco_achievement": 3,
            "hidden_gem_nearby": 5
        }
        
        limit = limits.get(notification_type, 10)
        
        if len(self.rate_limits[key]) >= limit:
            return False
        
        self.rate_limits[key].append(now)
        return True
    
    def _is_quiet_hours(self, user_id: int) -> bool:
        """Check quiet hours"""
        subscriptions = self.user_subscriptions.get(user_id, [])
        if not subscriptions:
            return False
        
        subscription = subscriptions[0]
        quiet_start = subscription.get("quiet_hours_start", "22:00")
        quiet_end = subscription.get("quiet_hours_end", "08:00")
        
        try:
            now = datetime.now().time()
            start_time = datetime.strptime(quiet_start, "%H:%M").time()
            end_time = datetime.strptime(quiet_end, "%H:%M").time()
            
            if start_time <= end_time:
                return start_time <= now <= end_time
            else:
                return now >= start_time or now <= end_time
        except ValueError:
            return False
    
    def subscribe_user(self, user_id: int, subscription_data: Dict):
        """Subscribe user"""
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = []
        
        device_token = subscription_data.get("device_token")
        
        # Check if token exists
        existing = [sub for sub in self.user_subscriptions[user_id] 
                   if sub["device_token"] == device_token]
        if existing:
            existing[0].update({
                **subscription_data,
                "updated_at": datetime.now().isoformat()
            })
        else:
            subscription = {
                **subscription_data,
                "subscribed_at": datetime.now().isoformat(),
                "active": True
            }
            self.user_subscriptions[user_id].append(subscription)
        
        logger.info(f"User {user_id} subscribed")
    
    def unsubscribe_user(self, user_id: int, device_token: Optional[str] = None) -> bool:
        """Unsubscribe user"""
        if user_id not in self.user_subscriptions:
            return False
        
        if device_token:
            original_count = len(self.user_subscriptions[user_id])
            self.user_subscriptions[user_id] = [
                sub for sub in self.user_subscriptions[user_id] 
                if sub["device_token"] != device_token
            ]
            return len(self.user_subscriptions[user_id]) < original_count
        else:
            count = len(self.user_subscriptions[user_id])
            self.user_subscriptions[user_id] = []
            return count > 0
    
    async def send_push_notification(self, user_id: int, notification: Notification) -> Dict[str, Any]:
        """Send push notification"""
        if user_id not in self.user_subscriptions or not self.user_subscriptions[user_id]:
            return {
                "success": False,
                "error": "User not subscribed",
                "user_id": user_id
            }
        
        # Check rate limits
        if not self._check_rate_limit(user_id, notification.type.value):
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "user_id": user_id
            }
        
        # Check quiet hours for non-urgent notifications
        if notification.priority != NotificationPriority.URGENT and self._is_quiet_hours(user_id):
            return {
                "success": True,
                "status": "queued_quiet_hours",
                "message": "Notification queued for after quiet hours"
            }
        
        # Store in history
        if user_id not in self.notification_history:
            self.notification_history[user_id] = []
        
        notification_dict = notification.dict()
        notification_dict["sent_at"] = datetime.now().isoformat()
        
        self.notification_history[user_id].append(notification_dict)
        
        # Keep only last 100 notifications
        if len(self.notification_history[user_id]) > 100:
            self.notification_history[user_id] = self.notification_history[user_id][-100:]
        
        # Update stats
        NOTIFICATION_STATS["total_sent"] += 1
        notif_type = notification.type.value
        NOTIFICATION_STATS["by_type"][notif_type] = NOTIFICATION_STATS["by_type"].get(notif_type, 0) + 1
        
        # Simulate sending
        subscriptions = self.user_subscriptions[user_id]
        sent_count = 0
        
        for subscription in subscriptions:
            if subscription.get("active", True):
                sent_count += 1
                logger.info(f"📱 Sent '{notification.title}' to {subscription.get('platform', 'web')}")
        
        return {
            "success": True,
            "notification_id": notification.id,
            "user_id": user_id,
            "devices_sent": sent_count,
            "message": f"Notification sent to {sent_count} device(s)"
        }

class MonitoringService:
    def __init__(self, notification_service: NotificationService):
        self.monitoring_active = False
        self.monitored_users = {}
        self.notification_service = notification_service
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in km"""
        R = 6371
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lng/2)**2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def update_user_location(self, user_id: int, location_data: Dict):
        """Update user location"""
        USER_LOCATIONS[user_id] = {
            **location_data,
            "updated_at": datetime.now().isoformat()
        }
        
        self.monitored_users[user_id] = {
            "location": {
                "lat": location_data["latitude"], 
                "lng": location_data["longitude"]
            },
            "last_update": datetime.now().isoformat(),
            "monitoring_enabled": True
        }
        
        logger.info(f"Updated location for user {user_id}")
        
        # Check geofences
        self._check_geofences(user_id, location_data["latitude"], location_data["longitude"])
    
    def _check_geofences(self, user_id: int, lat: float, lng: float):
        """Check geofences"""
        user_geofences = GEOFENCES.get(user_id, [])
        
        for geofence in user_geofences:
            distance = self._calculate_distance(
                lat, lng,
                geofence["center_lat"], geofence["center_lng"]
            ) * 1000  # Convert to meters
            
            is_inside = distance <= geofence["radius_meters"]
            was_inside = geofence.get("user_inside", False)
            
            if is_inside and not was_inside:
                geofence["user_inside"] = True
                self._trigger_geofence_event(user_id, geofence, "enter")
            elif not is_inside and was_inside:
                geofence["user_inside"] = False
                self._trigger_geofence_event(user_id, geofence, "exit")
    
    def _trigger_geofence_event(self, user_id: int, geofence: Dict, event_type: str):
        """Trigger geofence event"""
        poi_name = geofence.get("poi_name", "location")
        
        if event_type == "enter":
            title = f"📍 Arrived at {poi_name}"
            message = f"Welcome to {poi_name}! Check out local recommendations."
        else:
            title = f"👋 Left {poi_name}"
            message = f"Thanks for visiting {poi_name}."
        
        notification = Notification(
            id=f"geofence_{user_id}_{event_type}_{datetime.now().timestamp()}",
            user_id=user_id,
            type=NotificationType.LOCATION_ARRIVAL,
            title=title,
            message=message,
            data={
                "geofence_id": geofence.get("id"),
                "poi_name": poi_name,
                "event_type": event_type
            },
            priority=NotificationPriority.MEDIUM,
            created_at=datetime.now().isoformat()
        )
        
        # Schedule notification
        asyncio.create_task(
            self.notification_service.send_push_notification(user_id, notification)
        )
    
    async def start_monitoring(self):
        """Start monitoring"""
        global MONITORING_ACTIVE
        MONITORING_ACTIVE = True
        self.monitoring_active = True
        
        logger.info("🔍 Monitoring service started")
        
        # Start monitoring tasks
        await self.check_alerts()
    
    async def stop_monitoring(self):
        """Stop monitoring"""
        global MONITORING_ACTIVE
        MONITORING_ACTIVE = False
        self.monitoring_active = False
        
        logger.info("🛑 Monitoring service stopped")
    
    async def check_alerts(self):
        """Check various alerts"""
        for user_id in self.monitored_users.keys():
            # Weather alerts
            if self._should_send_weather_alert():
                await self._send_weather_alert(user_id)
            
            # Traffic alerts
            if self._should_send_traffic_alert():
                await self._send_traffic_alert(user_id)
    
    def _should_send_weather_alert(self) -> bool:
        """Check if should send weather alert"""
        import random
        return random.random() < 0.1  # 10% chance
    
    def _should_send_traffic_alert(self) -> bool:
        """Check if should send traffic alert"""
        import random
        return random.random() < 0.1  # 10% chance
    
    async def _send_weather_alert(self, user_id: int):
        """Send weather alert"""
        notification = Notification(
            id=f"weather_{user_id}_{datetime.now().timestamp()}",
            user_id=user_id,
            type=NotificationType.WEATHER_ALERT,
            title="🌧️ Weather Alert",
            message="Rain expected in your area. Consider carrying an umbrella.",
            priority=NotificationPriority.MEDIUM,
            created_at=datetime.now().isoformat(),
            data={"weather_type": "rain"}
        )
        
        await self.notification_service.send_push_notification(user_id, notification)
    
    async def _send_traffic_alert(self, user_id: int):
        """Send traffic alert"""
        notification = Notification(
            id=f"traffic_{user_id}_{datetime.now().timestamp()}",
            user_id=user_id,
            type=NotificationType.TRAFFIC_ALERT,
            title="🚗 Traffic Alert",
            message="Heavy traffic detected on your usual route.",
            priority=NotificationPriority.MEDIUM,
            created_at=datetime.now().isoformat(),
            data={"traffic_level": "heavy"}
        )
        
        await self.notification_service.send_push_notification(user_id, notification)

# Initialize services
notification_service = NotificationService()
monitoring_service = MonitoringService(notification_service)

# ✅ Helper functions
async def get_current_user_id() -> int:
    return 1

def generate_notification_id(user_id: int, notification_type: str) -> str:
    return f"{notification_type}_{user_id}_{datetime.now().timestamp()}"

# ✅ API Endpoints
@router.post("/subscribe")
async def subscribe_notifications(
    subscription: NotificationSubscription,
    user_id: int = Depends(get_current_user_id)
):
    """Subscribe to notifications"""
    try:
        subscription_data = {
            "device_token": subscription.device_token,
            "platform": subscription.platform.value,
            "preferences": {
                "weather_alerts": subscription.enable_weather,
                "traffic_alerts": subscription.enable_traffic,
                "flight_updates": subscription.enable_flights,
                "eco_achievements": subscription.enable_eco,
                "hidden_gem_alerts": subscription.enable_hidden_gems,
                "price_alerts": subscription.enable_price_alerts
            },
            "quiet_hours_start": subscription.quiet_hours_start,
            "quiet_hours_end": subscription.quiet_hours_end
        }
        
        notification_service.subscribe_user(user_id, subscription_data)
        
        return {
            "success": True,
            "status": "subscribed",
            "message": "Successfully subscribed to notifications",
            "user_id": user_id,
            "platform": subscription.platform.value,
            "subscribed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Subscription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/unsubscribe")
async def unsubscribe_notifications(
    device_token: Optional[str] = Query(None),
    user_id: int = Depends(get_current_user_id)
):
    """Unsubscribe from notifications"""
    try:
        success = notification_service.unsubscribe_user(user_id, device_token)
        
        if success:
            return {
                "success": True,
                "status": "unsubscribed",
                "message": "Successfully unsubscribed",
                "user_id": user_id
            }
        else:
            raise HTTPException(status_code=404, detail="No subscription found")
        
    except Exception as e:
        logger.error(f"Unsubscription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/location")
async def update_location(
    location: LocationUpdate,
    user_id: int = Depends(get_current_user_id)
):
    """Update location"""
    try:
        monitoring_service.update_user_location(user_id, location.dict())
        
        return {
            "success": True,
            "status": "location_updated",
            "message": "Location updated successfully",
            "user_id": user_id,
            "coordinates": {
                "latitude": location.latitude,
                "longitude": location.longitude
            },
            "updated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Location update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/geofence")
async def create_geofence(
    geofence_data: GeofenceCreate,
    user_id: int = Depends(get_current_user_id)
):
    """Create geofence"""
    try:
        if user_id not in GEOFENCES:
            GEOFENCES[user_id] = []
        
        geofence = {
            "id": f"geofence_{user_id}_{len(GEOFENCES[user_id]) + 1}",
            "center_lat": geofence_data.center_lat,
            "center_lng": geofence_data.center_lng,
            "radius_meters": geofence_data.radius_meters,
            "poi_id": geofence_data.poi_id,
            "poi_name": geofence_data.poi_name,
            "created_at": datetime.now().isoformat(),
            "active": True,
            "user_inside": False
        }
        
        GEOFENCES[user_id].append(geofence)
        
        return {
            "success": True,
            "status": "geofence_created",
            "message": "Geofence created successfully",
            "geofence_id": geofence["id"],
            "center": {"lat": geofence_data.center_lat, "lng": geofence_data.center_lng},
            "radius_meters": geofence_data.radius_meters
        }
        
    except Exception as e:
        logger.error(f"Geofence creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def send_test_notification(
    test_notification: TestNotification,
    user_id: int = Depends(get_current_user_id)
):
    """Send test notification"""
    try:
        notification = Notification(
            id=generate_notification_id(user_id, "test"),
            user_id=user_id,
            type=test_notification.notification_type,
            title=test_notification.title,
            message=test_notification.message,
            data={
                **(test_notification.data or {}),
                "test": True
            },
            priority=test_notification.priority,
            action_button=test_notification.action_button,
            action_url=test_notification.action_url,
            created_at=datetime.now().isoformat()
        )
        
        result = await notification_service.send_push_notification(user_id, notification)
        
        return {
            "success": True,
            "status": "test_sent",
            "message": "Test notification sent successfully",
            "notification_id": notification.id,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Test notification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monitoring/start")
async def start_monitoring(background_tasks: BackgroundTasks):
    """Start monitoring"""
    try:
        background_tasks.add_task(monitoring_service.start_monitoring)
        
        return {
            "success": True,
            "status": "monitoring_started",
            "message": "Monitoring started successfully",
            "started_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Monitoring start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monitoring/stop")
async def stop_monitoring():
    """Stop monitoring"""
    try:
        await monitoring_service.stop_monitoring()
        
        return {
            "success": True,
            "status": "monitoring_stopped",
            "message": "Monitoring stopped successfully",
            "stopped_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Monitoring stop failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{user_id}")
async def get_notification_history(
    user_id: int,
    limit: int = Query(20, ge=1, le=100),
    notification_type: Optional[NotificationType] = Query(None),
    unread_only: bool = Query(False)
):
    """Get notification history"""
    try:
        user_notifications = NOTIFICATION_HISTORY.get(user_id, [])
        
        # Apply filters
        if notification_type:
            user_notifications = [
                n for n in user_notifications 
                if n.get("type") == notification_type.value
            ]
        
        if unread_only:
            user_notifications = [
                n for n in user_notifications
                if not n.get("read_at")
            ]
        
        # Sort and limit
        sorted_notifications = sorted(
            user_notifications,
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )
        
        limited_notifications = sorted_notifications[:limit]
        
        return {
            "success": True,
            "user_id": user_id,
            "notifications": limited_notifications,
            "total_available": len(user_notifications),
            "returned_count": len(limited_notifications),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Getting history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/read/{notification_id}")
async def mark_notification_read(
    notification_id: str,
    user_id: int = Depends(get_current_user_id)
):
    """Mark notification as read"""
    try:
        user_notifications = NOTIFICATION_HISTORY.get(user_id, [])
        
        for notification in user_notifications:
            if notification.get("id") == notification_id:
                notification["read_at"] = datetime.now().isoformat()
                
                return {
                    "success": True,
                    "status": "marked_read",
                    "notification_id": notification_id,
                    "read_at": notification["read_at"]
                }
        
        raise HTTPException(status_code=404, detail="Notification not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mark read failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/preferences")
async def update_notification_preferences(
    preferences: NotificationPreferences,
    user_id: int = Depends(get_current_user_id)
):
    """Update preferences"""
    try:
        user_subscriptions = USER_SUBSCRIPTIONS.get(user_id, [])
        if not user_subscriptions:
            raise HTTPException(status_code=404, detail="User not subscribed")
        
        updated_devices = 0
        for subscription in user_subscriptions:
            if "preferences" not in subscription:
                subscription["preferences"] = {}
            
            subscription["preferences"].update({
                "enable_push": preferences.enable_push,
                "enable_email": preferences.enable_email,
                "enable_sms": preferences.enable_sms,
                "weather_threshold": preferences.weather_threshold,
                "traffic_threshold": preferences.traffic_threshold,
                "price_drop_percentage": preferences.price_drop_percentage,
                "location_radius_km": preferences.location_radius_km
            })
            updated_devices += 1
        
        return {
            "success": True,
            "status": "preferences_updated",
            "message": f"Preferences updated for {updated_devices} device(s)",
            "user_id": user_id,
            "devices_updated": updated_devices,
            "updated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preferences update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_notification_status(user_id: int = Depends(get_current_user_id)):
    """Get notification status"""
    try:
        user_subscriptions = USER_SUBSCRIPTIONS.get(user_id, [])
        user_notifications = NOTIFICATION_HISTORY.get(user_id, [])
        
        total_subscriptions = sum(len(subs) for subs in USER_SUBSCRIPTIONS.values())
        total_notifications_sent = sum(len(history) for history in NOTIFICATION_HISTORY.values())
        
        return {
            "success": True,
            "status": "healthy",
            "user_status": {
                "user_id": user_id,
                "subscribed": len(user_subscriptions) > 0,
                "active_devices": len(user_subscriptions),
                "total_notifications_received": len(user_notifications),
                "unread_notifications": sum(1 for n in user_notifications if not n.get("read_at"))
            },
            "system_status": {
                "monitoring_active": MONITORING_ACTIVE,
                "total_subscribed_users": len(USER_SUBSCRIPTIONS),
                "total_device_subscriptions": total_subscriptions,
                "total_notifications_sent": total_notifications_sent
            },
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def notification_service_health():
    """Service health check"""
    try:
        total_users = len(USER_SUBSCRIPTIONS)
        total_notifications = sum(len(history) for history in NOTIFICATION_HISTORY.values())
        
        return {
            "service": "notifications",
            "status": "healthy",
            "version": "2.0.0",
            "features": {
                "push_notifications": True,
                "location_monitoring": True,
                "geofencing": True,
                "rate_limiting": True,
                "quiet_hours": True,
                "notification_history": True,
                "preferences": True
            },
            "statistics": {
                "total_subscribed_users": total_users,
                "total_device_subscriptions": sum(len(subs) for subs in USER_SUBSCRIPTIONS.values()),
                "total_notifications_sent": total_notifications,
                "monitoring_active": MONITORING_ACTIVE,
                "monitored_users": len(monitoring_service.monitored_users),
                "active_geofences": sum(len(geofences) for geofences in GEOFENCES.values()),
                "location_updates_tracked": len(USER_LOCATIONS)
            },
            "notification_types": [nt.value for nt in NotificationType],
            "supported_platforms": [pt.value for pt in PlatformType],
            "last_health_check": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "service": "notifications",
            "status": "degraded",
            "error": str(e),
            "last_health_check": datetime.now().isoformat()
        }
