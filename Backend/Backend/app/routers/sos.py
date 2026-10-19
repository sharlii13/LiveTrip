from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
import sys
import os

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

logger = logging.getLogger(__name__)

# ✅ FIXED IMPORTS - Handle both relative and absolute
try:
    from database import get_db
    DATABASE_AVAILABLE = True
except ImportError:
    try:
        from ..database import get_db
        DATABASE_AVAILABLE = True
    except ImportError:
        def get_db():
            return None
        DATABASE_AVAILABLE = False

# ✅ Create router
router = APIRouter(
    prefix="/sos",
    tags=["🚨 SOS Emergency System"],
    responses={404: {"description": "Not found"}}
)

# ✅ Enums and Models
class AlertType(str, Enum):
    EMERGENCY = "emergency"
    MEDICAL = "medical"
    SAFETY = "safety"
    LOST = "lost"
    ACCIDENT = "accident"
    HARASSMENT = "harassment"
    THEFT = "theft"
    NATURAL_DISASTER = "natural_disaster"

class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_ALARM = "false_alarm"

class ContactRelationship(str, Enum):
    FAMILY = "family"
    FRIEND = "friend"
    SPOUSE = "spouse"
    PARENT = "parent"
    SIBLING = "sibling"
    COLLEAGUE = "colleague"
    EMERGENCY_CONTACT = "emergency_contact"

# ✅ Enhanced Pydantic Models
class SOSAlertCreate(BaseModel):
    alert_type: AlertType = Field(AlertType.EMERGENCY, description="Type of emergency")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Current latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Current longitude")
    location_address: Optional[str] = Field(None, max_length=500, description="Current address")
    message: Optional[str] = Field("Emergency! Please help me.", max_length=1000, description="Emergency message")
    trip_id: Optional[int] = Field(None, description="Associated trip ID")
    is_silent: bool = Field(False, description="Silent alert (no audio/vibration)")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Additional emergency details")

class EmergencyContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Contact name")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number with country code")
    contact_relationship: ContactRelationship = Field(ContactRelationship.EMERGENCY_CONTACT, description="Relationship to user")
    email: Optional[str] = Field(None, description="Email address")
    is_primary: bool = Field(False, description="Primary emergency contact")
    notification_preference: str = Field("both", pattern="^(sms|call|both)$", description="How to contact")

class LocationShare(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = Field(None, ge=0, description="GPS accuracy in meters")
    address: Optional[str] = Field(None, description="Human-readable address")
    share_duration_hours: int = Field(24, ge=1, le=168, description="How long to share location")

# ✅ Mock Data Storage
MOCK_EMERGENCY_CONTACTS = {
    1: [
        {
            "id": 1,
            "user_id": 1,
            "name": "John Doe",
            "phone_number": "+91-9876543210",
            "contact_relationship": "family",
            "email": "john.doe@example.com",
            "is_primary": True,
            "notification_preference": "both"
        },
        {
            "id": 2,
            "user_id": 1,
            "name": "Emergency Services",
            "phone_number": "+91-100",
            "contact_relationship": "emergency_contact",
            "email": None,
            "is_primary": False,
            "notification_preference": "call"
        }
    ]
}

MOCK_SOS_ALERTS = {
    1: [
        {
            "id": 1,
            "user_id": 1,
            "trip_id": None,
            "alert_type": "emergency",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "location_address": "Mumbai, Maharashtra, India",
            "message": "Emergency! Need immediate help!",
            "status": "resolved",
            "created_at": "2025-01-10T14:30:00",
            "resolved_at": "2025-01-10T14:45:00",
            "is_silent": False
        }
    ]
}

# ✅ Enhanced SOS Service Implementation
class SOSService:
    def __init__(self):
        self.development_mode = True
        self.active_alerts = {}
        self.location_shares = {}
    
    async def trigger_emergency_alert(self, user_name: str, contacts_data: List[Dict], location_data: Dict, message: str):
        """Trigger emergency alert to all contacts"""
        
        logger.info(f"🚨 EMERGENCY ALERT TRIGGERED for {user_name}")
        logger.info(f"📍 Location: {location_data}")
        logger.info(f"💬 Message: {message}")
        
        # In production, this would send real SMS/calls
        for contact in contacts_data:
            notification_method = contact.get("notification_preference", "both")
            
            if self.development_mode:
                logger.info(f"📱 [MOCK] Sending {notification_method} to {contact['name']} ({contact['phone_number']})")
                logger.info(f"    Message: EMERGENCY - {user_name} needs help! {message}")
                if location_data.get("latitude") and location_data.get("longitude"):
                    logger.info(f"    Location: https://maps.google.com/?q={location_data['latitude']},{location_data['longitude']}")
            else:
                # Real implementation would use Twilio, AWS SNS, etc.
                await self.send_emergency_sms(contact, user_name, message, location_data)
                if notification_method in ["call", "both"]:
                    await self.make_emergency_call(contact, user_name, message, location_data)
        
        logger.info(f"✅ Emergency alert sent to {len(contacts_data)} contacts")
    
    async def send_emergency_sms(self, contact: Dict, user_name: str, message: str, location_data: Dict):
        """Send emergency SMS (placeholder for real implementation)"""
        # Would integrate with Twilio, AWS SNS, or other SMS service
        pass
    
    async def make_emergency_call(self, contact: Dict, user_name: str, message: str, location_data: Dict):
        """Make emergency call (placeholder for real implementation)"""
        # Would integrate with Twilio Voice or similar service
        pass
    
    async def start_location_sharing(self, user_id: int, location_data: LocationShare):
        """Start sharing location with emergency contacts"""
        
        share_id = f"loc_share_{user_id}_{datetime.now().timestamp()}"
        
        self.location_shares[share_id] = {
            "user_id": user_id,
            "latitude": location_data.latitude,
            "longitude": location_data.longitude,
            "accuracy": location_data.accuracy,
            "address": location_data.address,
            "started_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=location_data.share_duration_hours),
            "is_active": True
        }
        
        logger.info(f"📍 Location sharing started for user {user_id} - Share ID: {share_id}")
        
        return share_id
    
    def get_shared_location(self, share_id: str) -> Optional[Dict]:
        """Get shared location by ID"""
        location_data = self.location_shares.get(share_id)
        
        if location_data and datetime.now() < location_data["expires_at"]:
            return location_data
        
        return None

# Initialize SOS service
sos_service = SOSService()

# ✅ Helper Functions
async def get_current_user_id() -> int:
    """Get current user ID - replace with your auth"""
    return 1

def get_emergency_numbers_by_country(country: str) -> Dict[str, Any]:
    """Get emergency numbers for a specific country"""
    
    emergency_numbers = {
        "india": {
            "country": "India",
            "police": "100",
            "fire": "101", 
            "ambulance": "102",
            "general_emergency": "112",
            "women_helpline": "1091",
            "child_helpline": "1098",
            "tourist_helpline": "1363",
            "disaster_management": "108",
            "cyber_crime": "155620"
        },
        "usa": {
            "country": "United States",
            "general_emergency": "911",
            "non_emergency_police": "311",
            "poison_control": "1-800-222-1222",
            "suicide_prevention": "988"
        },
        "uk": {
            "country": "United Kingdom",
            "general_emergency": "999",
            "non_emergency": "101",
            "coastguard": "999",
            "mountain_rescue": "999"
        },
        "australia": {
            "country": "Australia",
            "general_emergency": "000",
            "non_emergency_police": "131444",
            "poison_information": "13 11 26",
            "mental_health": "1800 011 511"
        },
        "canada": {
            "country": "Canada",
            "general_emergency": "911",
            "poison_control": "1-844-764-7669",
            "mental_health": "1-833-456-4566"
        },
        "germany": {
            "country": "Germany",
            "general_emergency": "112",
            "police": "110",
            "poison_control": "030 19240"
        },
        "france": {
            "country": "France",
            "general_emergency": "112",
            "police": "17",
            "fire": "18",
            "medical": "15"
        },
        "japan": {
            "country": "Japan",
            "police": "110",
            "fire_ambulance": "119",
            "coast_guard": "118"
        },
        "default": {
            "country": "International",
            "general_emergency": "112",
            "note": "112 works in most countries worldwide"
        }
    }
    
    return emergency_numbers.get(country.lower(), emergency_numbers["default"])

# ✅ API Endpoints
@router.post("/trigger",
             summary="🚨 TRIGGER EMERGENCY ALERT",
             description="Immediately trigger SOS alert to all emergency contacts")
async def trigger_sos_alert(
    alert_data: SOSAlertCreate,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id)
):
    """🚨 EMERGENCY: Trigger SOS alert to emergency contacts"""
    
    try:
        # Get emergency contacts from mock data
        emergency_contacts = MOCK_EMERGENCY_CONTACTS.get(user_id, [])
        
        if not emergency_contacts:
            raise HTTPException(
                status_code=400, 
                detail="No emergency contacts found. Please add emergency contacts first."
            )
        
        # Create SOS alert record in mock storage
        alert_id = len(MOCK_SOS_ALERTS.get(user_id, [])) + 1
        
        new_alert = {
            "id": alert_id,
            "user_id": user_id,
            "trip_id": alert_data.trip_id,
            "alert_type": alert_data.alert_type,
            "latitude": alert_data.latitude,
            "longitude": alert_data.longitude,
            "location_address": alert_data.location_address,
            "message": alert_data.message,
            "status": AlertStatus.ACTIVE,
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
            "is_silent": alert_data.is_silent,
            "additional_info": alert_data.additional_info
        }
        
        if user_id not in MOCK_SOS_ALERTS:
            MOCK_SOS_ALERTS[user_id] = []
        MOCK_SOS_ALERTS[user_id].append(new_alert)
        
        # Prepare contact data for SOS service
        contacts_data = [
            {
                "name": contact["name"],
                "phone_number": contact["phone_number"],
                "relationship": contact["contact_relationship"],
                "notification_preference": contact.get("notification_preference", "both")
            }
            for contact in emergency_contacts
        ]
        
        location_data = {
            "latitude": alert_data.latitude,
            "longitude": alert_data.longitude,
            "address": alert_data.location_address
        }
        
        # Get user name (mock)
        user_name = f"User {user_id}"
        
        # Trigger emergency alert in background
        background_tasks.add_task(
            sos_service.trigger_emergency_alert,
            user_name,
            contacts_data,
            location_data,
            alert_data.message
        )
        
        return {
            "success": True,
            "status": "emergency_alert_triggered",
            "alert_id": alert_id,
            "alert_type": alert_data.alert_type,
            "message": "🚨 Emergency alert sent to all contacts!",
            "contacts_notified": len(contacts_data),
            "timestamp": new_alert["created_at"],
            "location_shared": bool(alert_data.latitude and alert_data.longitude),
            "silent_mode": alert_data.is_silent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SOS trigger failed: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency alert failed: {str(e)}")

@router.post("/contacts",
             summary="Add Emergency Contact",
             description="Add a new emergency contact for SOS alerts")
async def add_emergency_contact(
    contact: EmergencyContactCreate,
    user_id: int = Depends(get_current_user_id)
):
    """Add emergency contact"""
    
    try:
        # Create new contact
        contact_id = len(MOCK_EMERGENCY_CONTACTS.get(user_id, [])) + 1
        
        new_contact = {
            "id": contact_id,
            "user_id": user_id,
            "name": contact.name,
            "phone_number": contact.phone_number,
            "contact_relationship": contact.contact_relationship,
            "email": contact.email,
            "is_primary": contact.is_primary,
            "notification_preference": contact.notification_preference,
            "created_at": datetime.now().isoformat()
        }
        
        if user_id not in MOCK_EMERGENCY_CONTACTS:
            MOCK_EMERGENCY_CONTACTS[user_id] = []
        
        MOCK_EMERGENCY_CONTACTS[user_id].append(new_contact)
        
        return {
            "success": True,
            "message": "Emergency contact added successfully",
            "contact_id": contact_id,
            "name": new_contact["name"],
            "phone_number": new_contact["phone_number"],
            "relationship": new_contact["contact_relationship"],
            "is_primary": new_contact["is_primary"]
        }
        
    except Exception as e:
        logger.error(f"Error adding emergency contact: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add emergency contact: {str(e)}")

@router.get("/contacts",
            summary="Get Emergency Contacts",
            description="Get all emergency contacts for the user")
async def get_emergency_contacts(user_id: int = Depends(get_current_user_id)):
    """Get user's emergency contacts"""
    
    try:
        contacts = MOCK_EMERGENCY_CONTACTS.get(user_id, [])
        
        # Separate primary and secondary contacts
        primary_contacts = [c for c in contacts if c.get("is_primary", False)]
        secondary_contacts = [c for c in contacts if not c.get("is_primary", False)]
        
        return {
            "success": True,
            "user_id": user_id,
            "contacts": contacts,
            "primary_contacts": primary_contacts,
            "secondary_contacts": secondary_contacts,
            "total_contacts": len(contacts),
            "has_primary_contact": len(primary_contacts) > 0
        }
        
    except Exception as e:
        logger.error(f"Error getting emergency contacts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get emergency contacts: {str(e)}")

@router.get("/alerts/history",
            summary="Get SOS Alert History",
            description="Get user's SOS alert history")
async def get_sos_history(
    user_id: int = Depends(get_current_user_id),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of alerts to return"),
    status: Optional[AlertStatus] = Query(None, description="Filter by alert status")
):
    """Get user's SOS alert history"""
    
    try:
        alerts = MOCK_SOS_ALERTS.get(user_id, [])
        
        # Filter by status if specified
        if status:
            alerts = [alert for alert in alerts if alert.get("status") == status]
        
        # Sort by creation date (newest first) and limit
        sorted_alerts = sorted(alerts, key=lambda x: x.get("created_at", ""), reverse=True)
        limited_alerts = sorted_alerts[:limit]
        
        # Calculate statistics
        total_alerts = len(alerts)
        active_alerts = len([a for a in alerts if a.get("status") == AlertStatus.ACTIVE])
        resolved_alerts = len([a for a in alerts if a.get("status") == AlertStatus.RESOLVED])
        
        return {
            "success": True,
            "user_id": user_id,
            "alerts": limited_alerts,
            "statistics": {
                "total_alerts": total_alerts,
                "active_alerts": active_alerts,
                "resolved_alerts": resolved_alerts,
                "returned_count": len(limited_alerts)
            },
            "filter_applied": status.value if status else None
        }
        
    except Exception as e:
        logger.error(f"Error getting SOS history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get SOS history: {str(e)}")

@router.put("/alerts/{alert_id}/resolve",
            summary="Resolve SOS Alert",
            description="Mark SOS alert as resolved")
async def resolve_sos_alert(
    alert_id: int,
    resolution_note: Optional[str] = Query(None, description="Resolution note"),
    user_id: int = Depends(get_current_user_id)
):
    """Mark SOS alert as resolved"""
    
    try:
        user_alerts = MOCK_SOS_ALERTS.get(user_id, [])
        alert = None
        
        for a in user_alerts:
            if a["id"] == alert_id:
                alert = a
                break
        
        if not alert:
            raise HTTPException(status_code=404, detail="SOS alert not found")
        
        # Update alert status
        alert["status"] = AlertStatus.RESOLVED
        alert["resolved_at"] = datetime.now().isoformat()
        if resolution_note:
            alert["resolution_note"] = resolution_note
        
        return {
            "success": True,
            "message": "SOS alert marked as resolved",
            "alert_id": alert_id,
            "resolved_at": alert["resolved_at"],
            "resolution_note": resolution_note
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving SOS alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resolve SOS alert: {str(e)}")

@router.post("/location-share",
             summary="Start Location Sharing",
             description="Start sharing live location with emergency contacts")
async def start_location_sharing(
    location_data: LocationShare,
    user_id: int = Depends(get_current_user_id)
):
    """Start sharing location with emergency contacts"""
    
    try:
        share_id = await sos_service.start_location_sharing(user_id, location_data)
        
        return {
            "success": True,
            "message": "Location sharing started",
            "share_id": share_id,
            "share_url": f"https://maps.google.com/?q={location_data.latitude},{location_data.longitude}",
            "expires_at": (datetime.now() + timedelta(hours=location_data.share_duration_hours)).isoformat(),
            "duration_hours": location_data.share_duration_hours,
            "accuracy_meters": location_data.accuracy
        }
        
    except Exception as e:
        logger.error(f"Error starting location sharing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start location sharing: {str(e)}")

@router.get("/location-share/{share_id}",
            summary="View Shared Location",
            description="View shared location (public endpoint)")
async def view_shared_location(share_id: str):
    """View shared location (public endpoint for emergency contacts)"""
    
    try:
        location_data = sos_service.get_shared_location(share_id)
        
        if not location_data:
            raise HTTPException(status_code=404, detail="Location share not found or expired")
        
        return {
            "success": True,
            "location": {
                "latitude": location_data["latitude"],
                "longitude": location_data["longitude"],
                "accuracy": location_data["accuracy"],
                "address": location_data["address"],
                "maps_url": f"https://maps.google.com/?q={location_data['latitude']},{location_data['longitude']}",
                "last_updated": location_data["started_at"].isoformat(),
                "expires_at": location_data["expires_at"].isoformat()
            },
            "is_active": location_data["is_active"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing shared location: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to view shared location: {str(e)}")

@router.delete("/contacts/{contact_id}",
               summary="Delete Emergency Contact",
               description="Delete an emergency contact")
async def delete_emergency_contact(
    contact_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """Delete emergency contact"""
    
    try:
        user_contacts = MOCK_EMERGENCY_CONTACTS.get(user_id, [])
        contact = None
        contact_index = -1
        
        for i, c in enumerate(user_contacts):
            if c["id"] == contact_id:
                contact = c
                contact_index = i
                break
        
        if not contact:
            raise HTTPException(status_code=404, detail="Emergency contact not found")
        
        contact_name = contact["name"]
        MOCK_EMERGENCY_CONTACTS[user_id].pop(contact_index)
        
        return {
            "success": True,
            "message": f"Emergency contact '{contact_name}' deleted successfully",
            "contact_id": contact_id,
            "remaining_contacts": len(MOCK_EMERGENCY_CONTACTS[user_id])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting emergency contact: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete emergency contact: {str(e)}")

@router.get("/emergency-numbers/{country}",
            summary="Get Emergency Numbers",
            description="Get local emergency numbers by country")
async def get_emergency_numbers(country: str):
    """Get local emergency numbers by country"""
    
    try:
        numbers_data = get_emergency_numbers_by_country(country)
        
        return {
            "success": True,
            "country": numbers_data["country"],
            "emergency_numbers": {k: v for k, v in numbers_data.items() if k != "country"},
            "message": f"Emergency numbers for {numbers_data['country']}",
            "international_note": "112 works in most countries worldwide as a backup"
        }
        
    except Exception as e:
        logger.error(f"Error getting emergency numbers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get emergency numbers: {str(e)}")

@router.get("/countries",
            summary="Get Supported Countries",
            description="Get list of countries with emergency numbers")
async def get_supported_countries():
    """Get list of countries with emergency numbers"""
    
    countries = [
        {"code": "india", "name": "India", "primary_number": "112"},
        {"code": "usa", "name": "United States", "primary_number": "911"},
        {"code": "uk", "name": "United Kingdom", "primary_number": "999"},
        {"code": "australia", "name": "Australia", "primary_number": "000"},
        {"code": "canada", "name": "Canada", "primary_number": "911"},
        {"code": "germany", "name": "Germany", "primary_number": "112"},
        {"code": "france", "name": "France", "primary_number": "112"},
        {"code": "japan", "name": "Japan", "primary_number": "110/119"}
    ]
    
    return {
        "success": True,
        "supported_countries": countries,
        "total_countries": len(countries),
        "note": "112 works as international emergency number in most countries"
    }

@router.get("/test",
            summary="Test SOS System",
            description="Test SOS system functionality and health")
async def test_sos_system():
    """Test SOS system status"""
    
    try:
        # Test service availability
        service_status = {
            "sos_service_available": True,
            "development_mode": sos_service.development_mode,
            "active_alerts": len(sos_service.active_alerts),
            "location_shares": len(sos_service.location_shares)
        }
        
        return {
            "success": True,
            "status": "healthy",
            "message": "🚨 SOS emergency system is operational",
            "service_status": service_status,
            "features": {
                "emergency_alerts": True,
                "contact_management": True,
                "location_sharing": True,
                "alert_history": True,
                "emergency_numbers": True,
                "multi_country_support": True
            },
            "endpoints": {
                "trigger_alert": "POST /api/sos/trigger",
                "add_contact": "POST /api/sos/contacts",
                "get_contacts": "GET /api/sos/contacts",
                "alert_history": "GET /api/sos/alerts/history",
                "resolve_alert": "PUT /api/sos/alerts/{alert_id}/resolve",
                "location_share": "POST /api/sos/location-share",
                "emergency_numbers": "GET /api/sos/emergency-numbers/{country}"
            },
            "mock_data": {
                "users_with_contacts": len(MOCK_EMERGENCY_CONTACTS),
                "users_with_alerts": len(MOCK_SOS_ALERTS),
                "total_contacts": sum(len(contacts) for contacts in MOCK_EMERGENCY_CONTACTS.values()),
                "total_alerts": sum(len(alerts) for alerts in MOCK_SOS_ALERTS.values())
            }
        }
        
    except Exception as e:
        logger.error(f"SOS test failed: {e}")
        return {
            "success": False,
            "status": "error",
            "message": f"SOS system test failed: {str(e)}"
        }

@router.get("/health",
            summary="SOS Service Health",
            description="Check SOS service health status")
async def sos_service_health():
    """SOS service health check"""
    
    return {
        "service": "sos_emergency",
        "status": "healthy",
        "features": {
            "emergency_alerts": True,
            "contact_management": True,
            "location_sharing": True,
            "alert_history": True,
            "emergency_numbers": True,
            "multi_country_support": True,
            "silent_mode": True,
            "background_alerts": True
        },
        "alert_types": [t.value for t in AlertType],
        "contact_relationships": [r.value for r in ContactRelationship],
        "alert_statuses": [s.value for s in AlertStatus],
        "supported_countries": 8,
        "version": "1.0.0"
    }
