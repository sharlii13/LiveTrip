"""
Backend API Client for LiveTripBuddy
Handles communication with the FastAPI backend that contains the Greedy Algorithm
and external API integrations (weather, flights, traffic, maps, etc.)
"""

import requests
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import json


class BackendEventType(Enum):
    """Types of events from the backend"""
    WEATHER_CHANGE = "weather_change"
    FLIGHT_DELAY = "flight_delay"
    TRAFFIC_ALERT = "traffic_alert"
    ACTIVITY_SUGGESTION = "activity_suggestion"
    SAFETY_ALERT = "safety_alert"
    GENERAL_UPDATE = "general_update"


@dataclass
class BackendSuggestion:
    """Represents a suggestion from the backend"""
    event_type: str
    message: str
    suggestion: str
    auto_update: bool
    priority: str = "normal"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class UserResponse:
    """User's response to a backend suggestion"""
    event_id: str
    event_type: str
    user_choice: str  # "yes", "no", or custom response
    user_message: str = ""


class BackendClient:
    """Client for communicating with the FastAPI backend"""
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        """
        Initialize the backend client
        
        Args:
            backend_url: Base URL of the FastAPI backend
        """
        self.backend_url = backend_url.rstrip("/")
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "LiveTripBuddy-ChatBot/1.0"
        })
        
        self.logger.info(f"Backend client initialized for {self.backend_url}")
    
    def is_healthy(self) -> bool:
        """
        Check if the backend is healthy and reachable
        
        Returns:
            True if backend is healthy, False otherwise
        """
        try:
            response = self.session.get(f"{self.backend_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Backend health check failed: {str(e)}")
            return False
    
    def send_user_message(self, user_id: str, message: str) -> Optional[Dict[str, Any]]:
        """
        Send user message to backend for processing
        
        Args:
            user_id: Unique identifier for the user
            message: User's message
            
        Returns:
            Backend response or None if failed
        """
        try:
            payload = {
                "user_id": user_id,
                "message": message,
                "timestamp": self._get_timestamp()
            }
            
            response = self.session.post(
                f"{self.backend_url}/api/chat/message",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Backend message failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending message to backend: {str(e)}")
            return None
    
    def send_user_confirmation(self, user_id: str, event_id: str, event_type: str, user_choice: str) -> bool:
        """
        Send user's confirmation/response to backend
        
        Args:
            user_id: Unique identifier for the user
            event_id: ID of the event being responded to
            event_type: Type of the event
            user_choice: User's choice ("yes", "no", etc.)
            
        Returns:
            True if successfully sent, False otherwise
        """
        try:
            payload = {
                "user_id": user_id,
                "event_id": event_id,
                "event_type": event_type,
                "user_choice": user_choice,
                "timestamp": self._get_timestamp()
            }
            
            response = self.session.post(
                f"{self.backend_url}/api/chat/confirmation",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"User confirmation sent successfully: {user_choice}")
                return True
            else:
                self.logger.error(f"Backend confirmation failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending confirmation to backend: {str(e)}")
            return False
    
    def get_pending_suggestions(self, user_id: str) -> List[BackendSuggestion]:
        """
        Get pending suggestions from backend for a user
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            List of pending suggestions
        """
        try:
            response = self.session.get(
                f"{self.backend_url}/api/suggestions/{user_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                suggestions = []
                
                for item in data.get("suggestions", []):
                    suggestion = BackendSuggestion(
                        event_type=item.get("event_type", "general_update"),
                        message=item.get("message", ""),
                        suggestion=item.get("suggestion", ""),
                        auto_update=item.get("auto_update", False),
                        priority=item.get("priority", "normal"),
                        metadata=item.get("metadata", {})
                    )
                    suggestions.append(suggestion)
                
                return suggestions
            else:
                self.logger.error(f"Failed to get suggestions: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting suggestions from backend: {str(e)}")
            return []
    
    def update_user_context(self, user_id: str, context: Dict[str, Any]) -> bool:
        """
        Update user context in the backend
        
        Args:
            user_id: Unique identifier for the user
            context: Context data to update
            
        Returns:
            True if successfully updated, False otherwise
        """
        try:
            payload = {
                "user_id": user_id,
                "context": context,
                "timestamp": self._get_timestamp()
            }
            
            response = self.session.post(
                f"{self.backend_url}/api/users/{user_id}/context",
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Error updating user context: {str(e)}")
            return False
    
    def get_user_itinerary(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current user itinerary from backend
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            User's itinerary or None if failed
        """
        try:
            response = self.session.get(
                f"{self.backend_url}/api/users/{user_id}/itinerary",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get itinerary: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting itinerary from backend: {str(e)}")
            return None
    
    def simulate_backend_event(self, user_id: str, event_type: str, message: str, 
                              suggestion: str, auto_update: bool = False) -> BackendSuggestion:
        """
        Simulate a backend event for testing purposes
        (Remove this in production when real backend is connected)
        
        Args:
            user_id: User ID
            event_type: Type of event
            message: Event message
            suggestion: Suggested action
            auto_update: Whether to auto-update
            
        Returns:
            Simulated backend suggestion
        """
        return BackendSuggestion(
            event_type=event_type,
            message=message,
            suggestion=suggestion,
            auto_update=auto_update,
            priority="normal",
            metadata={"simulated": True, "user_id": user_id}
        )
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()


# Mock backend responses for testing
class MockBackendClient(BackendClient):
    """Mock backend client for testing when real backend is not available"""
    
    def __init__(self):
        # Don't call super().__init__() to avoid network calls
        self.logger = logging.getLogger(__name__)
        self.mock_suggestions = {}
        self.logger.info("Mock backend client initialized")
    
    def is_healthy(self) -> bool:
        """Mock backend is always healthy"""
        return True
    
    def send_user_message(self, user_id: str, message: str) -> Optional[Dict[str, Any]]:
        """Mock response based on message content"""
        message_lower = message.lower()
        
        # Simulate different types of responses
        if any(word in message_lower for word in ['weather', 'rain', 'sunny']):
            return {
                "response": "I can help you with weather-related planning! The backend is processing current weather data for your location.",
                "suggestions": []
            }
        elif any(word in message_lower for word in ['flight', 'plane', 'airport']):
            return {
                "response": "Let me check your flight status and any potential updates.",
                "suggestions": [
                    {
                        "event_type": "flight_delay",
                        "message": "Your flight AA123 is delayed by 30 minutes",
                        "suggestion": "Adjust your arrival plans accordingly",
                        "auto_update": True
                    }
                ]
            }
        else:
            return {
                "response": "I'm processing your request with the backend systems.",
                "suggestions": []
            }
    
    def send_user_confirmation(self, user_id: str, event_id: str, event_type: str, user_choice: str) -> bool:
        """Mock confirmation always succeeds"""
        self.logger.info(f"Mock: User {user_id} confirmed {user_choice} for {event_type}")
        return True
    
    def get_pending_suggestions(self, user_id: str) -> List[BackendSuggestion]:
        """Return mock suggestions"""
        return self.mock_suggestions.get(user_id, [])
    
    def add_mock_suggestion(self, user_id: str, suggestion: BackendSuggestion):
        """Add a mock suggestion for testing"""
        if user_id not in self.mock_suggestions:
            self.mock_suggestions[user_id] = []
        self.mock_suggestions[user_id].append(suggestion)