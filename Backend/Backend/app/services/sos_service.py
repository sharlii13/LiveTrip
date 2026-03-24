# app/services/sos_service.py
from twilio.rest import Client
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SOSService:
    def __init__(self):
        # Twilio configuration
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
            self.development_mode = False
        else:
            self.client = None
            self.development_mode = True
            logger.warning("Twilio credentials not found - running in development mode")
        
    async def trigger_emergency_alert(
        self, 
        user_name: str,
        emergency_contacts: list,
        location: dict,
        message: str = "Emergency! Please help me."
    ) -> dict:
        """Trigger SOS alert to all emergency contacts"""
        try:
            results = []
            
            # Prepare emergency message
            if location.get('latitude') and location.get('longitude'):
                location_text = f"https://maps.google.com/?q={location['latitude']},{location['longitude']}"
            else:
                location_text = "Location unavailable"
                
            full_message = f"""🚨 EMERGENCY ALERT 🚨
{user_name} needs help!

Message: {message}

Location: {location.get('address', 'Unknown')}
GPS: {location_text}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This is an automated emergency alert from TravelBuddy SOS system.""".strip()
            
            # Send SMS to each emergency contact
            for contact in emergency_contacts:
                try:
                    sms_result = await self._send_emergency_sms(
                        contact['phone_number'], 
                        full_message
                    )
                    
                    results.append({
                        "contact_name": contact['name'],
                        "phone": contact['phone_number'],
                        "status": "sent" if sms_result else "failed",
                        "relationship": contact.get('relationship', 'unknown')
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to send SMS to {contact['phone_number']}: {e}")
                    results.append({
                        "contact_name": contact['name'],
                        "phone": contact['phone_number'],
                        "status": "failed",
                        "error": str(e)
                    })
            
            return {
                "status": "completed",
                "alerts_sent": len([r for r in results if r["status"] == "sent"]),
                "total_contacts": len(results),
                "contact_results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Emergency alert failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _send_emergency_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS using Twilio"""
        try:
            if self.development_mode:
                print(f"📱 [DEV] SMS to {phone_number}: {message}")
                return True
            
            if not self.client:
                logger.error("Twilio client not initialized")
                return False
            
            # Send SMS via Twilio
            twilio_message = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=phone_number
            )
            
            logger.info(f"SMS sent successfully to {phone_number}. SID: {twilio_message.sid}")
            return twilio_message.status in ["queued", "sent", "delivered"]
                
        except Exception as e:
            logger.error(f"Twilio SMS failed: {e}")
            return False

# Global SOS service instance
sos_service = SOSService()
