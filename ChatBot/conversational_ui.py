"""
LiveTripBuddy - Conversational UI Layer
This is the lightweight conversational interface that communicates with the FastAPI backend.
The backend handles all decision-making, API calls, and the Greedy Algorithm.
The chatbot only handles natural language presentation and user confirmations.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from gemini_client import GeminiClient
from backend_client import BackendClient, MockBackendClient, BackendSuggestion


@dataclass
class PendingConfirmation:
    """Represents a pending user confirmation"""
    event_id: str
    event_type: str
    message: str
    suggestion: str
    created_at: datetime


class ConversationalUI:
    """
    Lightweight conversational UI for LiveTripBuddy
    
    Responsibilities:
    - Present backend suggestions in natural language
    - Handle user confirmations (yes/no)
    - Forward user responses to backend
    - Provide conversational flow
    
    NOT responsible for:
    - Decision making (backend does this)
    - API calls to external services (backend does this)
    - Itinerary optimization (backend's Greedy Algorithm does this)
    """
    
    def __init__(self, backend_url: str = None, use_mock_backend: bool = False):
        """
        Initialize the conversational UI
        
        Args:
            backend_url: URL of the FastAPI backend (if None, uses localhost:8000)
            use_mock_backend: If True, uses mock backend for testing
        """
        self.gemini_client = GeminiClient()
        self.logger = logging.getLogger(__name__)
        
        # Initialize backend client
        if use_mock_backend:
            self.backend_client = MockBackendClient()
            self.logger.info("Using mock backend for testing")
        else:
            backend_url = backend_url or "http://localhost:8000"
            self.backend_client = BackendClient(backend_url)
        
        # Store pending confirmations per user
        self.pending_confirmations: Dict[str, List[PendingConfirmation]] = {}
        
        # Travel keywords for basic filtering (lightweight check)
        self.travel_keywords = {
            'flight', 'hotel', 'itinerary', 'trip', 'travel', 'weather', 'traffic',
            'restaurant', 'activity', 'booking', 'reservation', 'transport', 'bus',
            'train', 'taxi', 'uber', 'airport', 'destination', 'route', 'delay',
            'cancel', 'reschedule', 'check-in', 'boarding', 'gate', 'luggage',
            'passport', 'visa', 'accommodation', 'sightseeing', 'tour', 'guide',
            'map', 'direction', 'location', 'attraction', 'museum', 'park'
        }
        
        self.logger.info("Conversational UI initialized successfully")
    
    def is_healthy(self) -> bool:
        """Check if both the UI and backend are healthy"""
        ui_healthy = self.gemini_client.is_healthy()
        backend_healthy = self.backend_client.is_healthy()
        
        self.logger.info(f"UI Health: {ui_healthy}, Backend Health: {backend_healthy}")
        return ui_healthy and backend_healthy
    
    def process_message(self, user_id: str, message: str) -> str:
        """
        Process user message through the conversational UI
        
        Args:
            user_id: Unique identifier for the user
            message: User's input message
            
        Returns:
            Conversational response to the user
        """
        try:
            # First check if user is responding to a pending confirmation
            if self._has_pending_confirmations(user_id):
                confirmation_response = self._handle_user_confirmation(user_id, message)
                if confirmation_response:
                    return confirmation_response
            
            # Basic travel-related check (lightweight filtering)
            if not self._is_travel_related(message):
                return self._get_off_topic_response()
            
            # Send message to backend for processing
            backend_response = self.backend_client.send_user_message(user_id, message)
            
            if not backend_response:
                return self._get_backend_error_response()
            
            # Extract response and handle any suggestions
            response_text = backend_response.get('response', '')
            suggestions = backend_response.get('suggestions', [])
            
            # If there are suggestions, present them to the user
            if suggestions:
                return self._present_suggestions(user_id, suggestions)
            
            # If backend provided a response, make it conversational
            if response_text:
                return self._make_conversational(response_text)
            
            return self._get_fallback_response()
            
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            return self._get_error_response()
    
    def handle_backend_suggestion(self, user_id: str, suggestion: BackendSuggestion) -> str:
        """
        Handle a suggestion from the backend (for proactive updates)
        
        Args:
            user_id: User ID
            suggestion: Suggestion from backend
            
        Returns:
            Natural language presentation of the suggestion
        """
        try:
            if suggestion.auto_update:
                # Auto-update: Just inform the user
                return self._present_auto_update(suggestion)
            else:
                # Ask for confirmation
                return self._present_confirmation_request(user_id, suggestion)
                
        except Exception as e:
            self.logger.error(f"Error handling backend suggestion: {str(e)}")
            return self._get_error_response()
    
    def _has_pending_confirmations(self, user_id: str) -> bool:
        """Check if user has pending confirmations"""
        return user_id in self.pending_confirmations and len(self.pending_confirmations[user_id]) > 0
    
    def _handle_user_confirmation(self, user_id: str, message: str) -> Optional[str]:
        """Handle user's response to a pending confirmation"""
        message_lower = message.lower().strip()
        
        # Check for yes/no responses
        if message_lower in ['yes', 'y', 'ok', 'okay', 'sure', 'go ahead', 'proceed']:
            return self._process_user_confirmation(user_id, 'yes')
        elif message_lower in ['no', 'n', 'nope', 'cancel', 'skip']:
            return self._process_user_confirmation(user_id, 'no')
        
        # If not a clear yes/no, treat as regular message but still process confirmation
        return None
    
    def _process_user_confirmation(self, user_id: str, choice: str) -> str:
        """Process the user's confirmation choice"""
        if not self._has_pending_confirmations(user_id):
            return "I don't have any pending requests for you right now."
        
        # Get the oldest pending confirmation
        confirmation = self.pending_confirmations[user_id].pop(0)
        
        # Send confirmation to backend
        success = self.backend_client.send_user_confirmation(
            user_id, 
            confirmation.event_id, 
            confirmation.event_type, 
            choice
        )
        
        if success:
            if choice == 'yes':
                return f"✅ Great! I've updated your plans based on the {confirmation.event_type.replace('_', ' ')}."
            else:
                return f"👍 No problem! I'll keep your current plans as they are and continue monitoring."
        else:
            return "⚠️ I had trouble updating the system. Your request has been noted, but please check your itinerary manually."
    
    def _is_travel_related(self, message: str) -> bool:
        """Lightweight check if message is travel-related"""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.travel_keywords)
    
    def _present_suggestions(self, user_id: str, suggestions: List[Dict[str, Any]]) -> str:
        """Present backend suggestions to the user"""
        responses = []
        
        for suggestion_data in suggestions:
            suggestion = BackendSuggestion(
                event_type=suggestion_data.get('event_type', 'general'),
                message=suggestion_data.get('message', ''),
                suggestion=suggestion_data.get('suggestion', ''),
                auto_update=suggestion_data.get('auto_update', False),
                priority=suggestion_data.get('priority', 'normal'),
                metadata=suggestion_data.get('metadata', {})
            )
            
            if suggestion.auto_update:
                responses.append(self._present_auto_update(suggestion))
            else:
                responses.append(self._present_confirmation_request(user_id, suggestion))
        
        return "\n\n".join(responses)
    
    def _present_auto_update(self, suggestion: BackendSuggestion) -> str:
        """Present an auto-update to the user"""
        emoji_map = {
            'flight_delay': '✈️',
            'weather_change': '🌧️',
            'traffic_alert': '🚗',
            'safety_alert': '⚠️'
        }
        
        emoji = emoji_map.get(suggestion.event_type, '📢')
        
        return f"{emoji} {suggestion.message} I've automatically updated your itinerary."
    
    def _present_confirmation_request(self, user_id: str, suggestion: BackendSuggestion) -> str:
        """Present a confirmation request to the user"""
        emoji_map = {
            'weather_change': '🌧️',
            'traffic_alert': '🚗',
            'activity_suggestion': '🎯'
        }
        
        emoji = emoji_map.get(suggestion.event_type, '💡')
        
        # Create pending confirmation
        event_id = str(uuid.uuid4())
        confirmation = PendingConfirmation(
            event_id=event_id,
            event_type=suggestion.event_type,
            message=suggestion.message,
            suggestion=suggestion.suggestion,
            created_at=datetime.now()
        )
        
        # Store pending confirmation
        if user_id not in self.pending_confirmations:
            self.pending_confirmations[user_id] = []
        self.pending_confirmations[user_id].append(confirmation)
        
        return f"{emoji} {suggestion.message} {suggestion.suggestion}"
    
    def _make_conversational(self, response_text: str) -> str:
        """Make backend response more conversational using Gemini"""
        try:
            conversational_prompt = f"""Make this travel response more friendly and conversational while keeping all the important information:

"{response_text}"

Make it sound like a helpful travel companion. Keep it concise and add appropriate emojis."""
            
            conversational_response = self.gemini_client.generate_response(conversational_prompt)
            
            return conversational_response or response_text
            
        except Exception as e:
            self.logger.error(f"Error making response conversational: {str(e)}")
            return response_text
    
    def _get_off_topic_response(self) -> str:
        """Response for off-topic messages"""
        return "I'm here to help with your trip and itinerary. Would you like me to adjust or suggest something for your journey? 🗺️"
    
    def _get_backend_error_response(self) -> str:
        """Response when backend is unavailable"""
        return "⚠️ I'm having trouble connecting to my planning system right now. Please try again in a moment, or let me know if you need immediate assistance!"
    
    def _get_fallback_response(self) -> str:
        """Fallback response when nothing else works"""
        fallback_responses = [
            "I'm here to help with your travel plans! What would you like to know or adjust? ✈️",
            "How can I assist you with your trip today? 🌍",
            "What aspect of your journey would you like to explore or modify? 🗺️"
        ]
        import random
        return random.choice(fallback_responses)
    
    def _get_error_response(self) -> str:
        """Response for system errors"""
        return "⚠️ I'm experiencing some technical difficulties. Please try again in a moment, and I'll do my best to help with your travel needs!"
    
    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context from backend"""
        try:
            return self.backend_client.get_user_itinerary(user_id) or {}
        except Exception as e:
            self.logger.error(f"Error getting user context: {str(e)}")
            return {}
    
    def clear_pending_confirmations(self, user_id: str):
        """Clear pending confirmations for a user"""
        if user_id in self.pending_confirmations:
            del self.pending_confirmations[user_id]
    
    def close(self):
        """Clean up resources"""
        if hasattr(self.backend_client, 'close'):
            self.backend_client.close()
