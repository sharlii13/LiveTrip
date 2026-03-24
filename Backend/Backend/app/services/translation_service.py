# app/services/translation_service.py
from googletrans import Translator
from langdetect import detect
import logging
from typing import Dict, List, Optional
import os

logger = logging.getLogger(__name__)

class TranslationService:
    def __init__(self):
        self.translator = Translator()
        
        # Popular travel languages
        self.supported_languages = {
            'en': 'English',
            'es': 'Spanish', 
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'hi': 'Hindi',
            'ar': 'Arabic',
            'th': 'Thai',
            'vi': 'Vietnamese',
            'tr': 'Turkish',
            'nl': 'Dutch'
        }
    
    async def translate_text(self, text: str, target_language: str, source_language: str = 'auto') -> Dict:
        """Translate text to target language"""
        try:
            if not text or not text.strip():
                return {"translated_text": "", "source_language": "unknown", "target_language": target_language}
            
            # Detect source language if auto
            if source_language == 'auto':
                try:
                    detected_lang = detect(text)
                    source_language = detected_lang
                except:
                    source_language = 'auto'
            
            # Skip translation if same language
            if source_language == target_language:
                return {
                    "translated_text": text,
                    "source_language": source_language,
                    "target_language": target_language,
                    "confidence": 1.0
                }
            
            # Perform translation
            result = self.translator.translate(text, dest=target_language, src=source_language)
            
            return {
                "translated_text": result.text,
                "source_language": result.src,
                "target_language": target_language,
                "confidence": getattr(result, 'confidence', 0.9),
                "original_text": text
            }
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return {
                "translated_text": text,  # Return original on failure
                "source_language": "unknown",
                "target_language": target_language,
                "error": str(e)
            }
    
    async def translate_itinerary(self, itinerary_data: Dict, target_language: str) -> Dict:
        """Translate entire itinerary to target language"""
        try:
            translated_itinerary = itinerary_data.copy()
            
            # Translate destination
            if 'destination' in itinerary_data:
                dest_result = await self.translate_text(itinerary_data['destination'], target_language)
                translated_itinerary['destination'] = dest_result['translated_text']
            
            # Translate activities
            if 'recommended_places' in itinerary_data:
                translated_places = []
                for place in itinerary_data['recommended_places']:
                    translated_place = place.copy()
                    
                    # Translate place name
                    if 'name' in place:
                        name_result = await self.translate_text(place['name'], target_language)
                        translated_place['name'] = name_result['translated_text']
                    
                    # Translate description
                    if 'description' in place:
                        desc_result = await self.translate_text(place['description'], target_language)
                        translated_place['description'] = desc_result['translated_text']
                    
                    translated_places.append(translated_place)
                
                translated_itinerary['recommended_places'] = translated_places
            
            # Translate eco suggestions
            if 'eco_suggestions' in itinerary_data:
                translated_suggestions = []
                for suggestion in itinerary_data['eco_suggestions']:
                    if isinstance(suggestion, dict) and 'suggestion' in suggestion:
                        sugg_result = await self.translate_text(suggestion['suggestion'], target_language)
                        translated_suggestion = suggestion.copy()
                        translated_suggestion['suggestion'] = sugg_result['translated_text']
                        translated_suggestions.append(translated_suggestion)
                    else:
                        translated_suggestions.append(suggestion)
                
                translated_itinerary['eco_suggestions'] = translated_suggestions
            
            translated_itinerary['language'] = target_language
            translated_itinerary['translation_timestamp'] = "2025-01-01T10:00:00Z"
            
            return translated_itinerary
            
        except Exception as e:
            logger.error(f"Itinerary translation failed: {e}")
            return itinerary_data  # Return original on failure
    
    async def get_local_phrases(self, destination: str, user_language: str = 'en') -> Dict:
        """Get useful travel phrases for destination"""
        
        # Common travel phrases in English
        travel_phrases = {
            "greetings": [
                "Hello",
                "Good morning", 
                "Good evening",
                "Thank you",
                "Please",
                "Excuse me"
            ],
            "directions": [
                "Where is the bathroom?",
                "How much does this cost?",
                "Where is the train station?",
                "Can you help me?",
                "I am lost",
                "Where is the hotel?"
            ],
            "emergency": [
                "Help me!",
                "Call the police!",
                "I need a doctor",
                "Emergency!",
                "I need help"
            ],
            "food": [
                "I would like to order",
                "Water please",
                "The bill please",
                "Is this spicy?",
                "I am vegetarian"
            ]
        }
        
        # Detect destination language (simple mapping)
        destination_languages = {
            'spain': 'es', 'madrid': 'es', 'barcelona': 'es',
            'france': 'fr', 'paris': 'fr', 'lyon': 'fr',
            'germany': 'de', 'berlin': 'de', 'munich': 'de',
            'italy': 'it', 'rome': 'it', 'milan': 'it',
            'japan': 'ja', 'tokyo': 'ja', 'osaka': 'ja',
            'china': 'zh', 'beijing': 'zh', 'shanghai': 'zh',
            'india': 'hi', 'delhi': 'hi', 'mumbai': 'hi',
            'thailand': 'th', 'bangkok': 'th',
            'vietnam': 'vi', 'hanoi': 'vi', 'saigon': 'vi'
        }
        
        # Determine target language
        dest_lower = destination.lower()
        target_language = 'en'  # Default
        
        for location, lang_code in destination_languages.items():
            if location in dest_lower:
                target_language = lang_code
                break
        
        # If destination is in user's language, return English phrases
        if target_language == user_language:
            target_language = 'en'
        
        # Translate phrases
        translated_phrases = {}
        
        try:
            for category, phrases in travel_phrases.items():
                translated_category = []
                
                for phrase in phrases:
                    translation_result = await self.translate_text(phrase, target_language)
                    translated_category.append({
                        "english": phrase,
                        "local": translation_result['translated_text'],
                        "pronunciation": self._get_pronunciation_hint(phrase, target_language)
                    })
                
                translated_phrases[category] = translated_category
            
            return {
                "destination": destination,
                "target_language": target_language,
                "language_name": self.supported_languages.get(target_language, "Unknown"),
                "phrases": translated_phrases
            }
            
        except Exception as e:
            logger.error(f"Failed to get local phrases: {e}")
            return {"error": str(e)}
    
    def _get_pronunciation_hint(self, text: str, language: str) -> str:
        """Simple pronunciation hints for common languages"""
        pronunciation_hints = {
            'es': {
                'Hello': 'OH-lah',
                'Thank you': 'GRAH-see-ahs',
                'Please': 'por fah-VOR'
            },
            'fr': {
                'Hello': 'bon-ZHOOR',
                'Thank you': 'mer-SEE',
                'Please': 'seel voo PLAY'
            },
            'de': {
                'Hello': 'HAH-lo',
                'Thank you': 'DAHN-keh',
                'Please': 'BIT-teh'
            }
        }
        
        return pronunciation_hints.get(language, {}).get(text, "")
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages"""
        return self.supported_languages

# Global translation service instance
translation_service = TranslationService()
