"""
Gemini API Client for LiveTripBuddy
Handles communication with Google's Gemini AI model
"""

import google.generativeai as genai
import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GeminiClient:
    """Client for interacting with Google's Gemini AI API"""
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model = None
        self.logger = logging.getLogger(__name__)
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Gemini API client"""
        try:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables")
            
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.logger.info("Gemini client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise
    
    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Generate a response using Gemini AI
        
        Args:
            prompt: The user's message/prompt
            context: Optional context dictionary for conversation history
            
        Returns:
            Generated response string or None if failed
        """
        try:
            if not self.model:
                raise RuntimeError("Gemini model not initialized")
            
            # Prepare the full prompt with context if available
            full_prompt = self._prepare_prompt(prompt, context)
            
            # Generate response
            response = self.model.generate_content(full_prompt)
            
            if response and response.text:
                return response.text.strip()
            else:
                self.logger.warning("Empty response received from Gemini")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            return None
    
    def _prepare_prompt(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Prepare the full prompt with system instructions and context
        
        Args:
            user_message: The user's input message
            context: Optional conversation context
            
        Returns:
            Formatted prompt string
        """
        system_prompt = """You are The Living Itinerary Chatbot (LiveTripBuddy), an AI-powered co-traveler.

🎯 Core Behavior Rules:

1. Stay Focused:
   - Only discuss travel, itinerary, transport, flights, weather, activities, or trip-related insights
   - If asked something unrelated, politely redirect: "I'm here to help with your trip and itinerary. Would you like me to adjust or suggest something for your journey?"

2. Event Handling:
   - Auto-update (no confirmation): flight delays, gate changes, boarding updates, critical safety alerts
   - Ask first (user confirmation): weather changes, traffic jams, activity replacements, mood-based swaps

3. User Interaction:
   - Ask politely before changes: "There's heavy traffic ahead 🚗. Would you like me to suggest a faster route?"
   - If yes → confirm and proceed
   - If no → acknowledge and keep monitoring

4. Tone & Style:
   - Be friendly, concise, and proactive
   - Always provide solutions, not just problems
   - Use light emojis 🌧 ✈ 🚗 for clarity, not decoration

5. Response Format:
   - When APIs succeed → confirm updates: "✅ Updated your itinerary with a new indoor option."
   - If APIs fail → fallback: "⚠️ I couldn't update the system right now. Do you want to adjust manually, or stick with your basic itinerary?"

"""
        
        # Add context if available
        context_str = ""
        if context:
            if 'conversation_history' in context:
                context_str += f"\nConversation History:\n{context['conversation_history']}\n"
            if 'current_itinerary' in context:
                context_str += f"\nCurrent Itinerary:\n{context['current_itinerary']}\n"
            if 'user_preferences' in context:
                context_str += f"\nUser Preferences:\n{context['user_preferences']}\n"
        
        full_prompt = f"{system_prompt}{context_str}\nUser: {user_message}\n\nLiveTripBuddy:"
        
        return full_prompt
    
    def is_healthy(self) -> bool:
        """
        Check if the Gemini client is healthy and ready to use
        
        Returns:
            True if client is ready, False otherwise
        """
        try:
            if not self.model:
                return False
            
            # Test with a simple prompt
            test_response = self.model.generate_content("Hello")
            return test_response is not None
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False