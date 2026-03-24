from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, validator
from typing import Dict, Optional, List, Any
from datetime import datetime
from enum import Enum
import logging
import json
import sys
import os
import re

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

# ✅ Translation Service
class TranslationService:
    def __init__(self):
        self.supported_languages = {
            "en": "English",
            "hi": "Hindi (हिन्दी)",
            "es": "Spanish (Español)",
            "fr": "French (Français)",
            "de": "German (Deutsch)",
            "it": "Italian (Italiano)",
            "pt": "Portuguese (Português)",
            "ja": "Japanese (日本語)",
            "ko": "Korean (한국어)",
            "zh": "Chinese (中文)",
            "ar": "Arabic (العربية)",
            "ru": "Russian (Русский)",
            "th": "Thai (ไทย)",
            "vi": "Vietnamese (Tiếng Việt)",
            "tr": "Turkish (Türkçe)",
            "nl": "Dutch (Nederlands)",
            "pl": "Polish (Polski)"
        }
        
        self.phrase_database = {
            "india": {
                "hi": [
                    {"english": "Hello", "local": "नमस्ते", "pronunciation": "na-mas-te", "context": "greeting"},
                    {"english": "Thank you", "local": "धन्यवाद", "pronunciation": "dhan-ya-vaad", "context": "gratitude"},
                    {"english": "Please", "local": "कृपया", "pronunciation": "krip-ya", "context": "request"},
                    {"english": "Excuse me", "local": "माफ़ करें", "pronunciation": "maaf ka-ren", "context": "attention"},
                    {"english": "How much?", "local": "कितना?", "pronunciation": "kit-na", "context": "shopping"},
                    {"english": "Where is...?", "local": "कहाँ है...?", "pronunciation": "ka-han hai", "context": "directions"},
                    {"english": "Help!", "local": "मदद!", "pronunciation": "ma-dad", "context": "emergency"},
                    {"english": "Water", "local": "पानी", "pronunciation": "paa-ni", "context": "basic_needs"},
                    {"english": "Food", "local": "खाना", "pronunciation": "khaa-na", "context": "basic_needs"},
                    {"english": "Bathroom", "local": "शौचालय", "pronunciation": "shauch-aa-lay", "context": "basic_needs"}
                ]
            },
            "spain": {
                "es": [
                    {"english": "Hello", "local": "Hola", "pronunciation": "oh-la", "context": "greeting"},
                    {"english": "Thank you", "local": "Gracias", "pronunciation": "gra-see-ahs", "context": "gratitude"},
                    {"english": "Please", "local": "Por favor", "pronunciation": "por fa-vor", "context": "request"},
                    {"english": "How much?", "local": "¿Cuánto cuesta?", "pronunciation": "kwan-to kwes-ta", "context": "shopping"},
                    {"english": "Where is...?", "local": "¿Dónde está...?", "pronunciation": "don-de es-ta", "context": "directions"},
                    {"english": "Help!", "local": "¡Ayuda!", "pronunciation": "ah-yu-da", "context": "emergency"},
                    {"english": "Water", "local": "Agua", "pronunciation": "ah-gwa", "context": "basic_needs"},
                    {"english": "Food", "local": "Comida", "pronunciation": "ko-mee-da", "context": "basic_needs"}
                ]
            },
            "france": {
                "fr": [
                    {"english": "Hello", "local": "Bonjour", "pronunciation": "bon-zhoor", "context": "greeting"},
                    {"english": "Thank you", "local": "Merci", "pronunciation": "mer-see", "context": "gratitude"},
                    {"english": "Please", "local": "S'il vous plaît", "pronunciation": "see voo play", "context": "request"},
                    {"english": "How much?", "local": "Combien?", "pronunciation": "kom-bee-an", "context": "shopping"},
                    {"english": "Where is...?", "local": "Où est...?", "pronunciation": "oo eh", "context": "directions"},
                    {"english": "Help!", "local": "Au secours!", "pronunciation": "oh suh-koor", "context": "emergency"},
                    {"english": "Water", "local": "Eau", "pronunciation": "oh", "context": "basic_needs"},
                    {"english": "Food", "local": "Nourriture", "pronunciation": "noo-ree-tur", "context": "basic_needs"}
                ]
            }
        }
        
        self.translation_examples = {
            "hi": {
                "Hello, how are you?": "नमस्ते, आप कैसे हैं?",
                "I am visiting India": "मैं भारत आया हूँ",
                "Can you help me?": "क्या आप मेरी मदद कर सकते हैं?",
                "Where is the nearest restaurant?": "सबसे नजदीकी रेस्टोरेंट कहाँ है?"
            },
            "es": {
                "Hello, how are you?": "Hola, ¿cómo estás?",
                "I am visiting Spain": "Estoy visitando España",
                "Can you help me?": "¿Puedes ayudarme?",
                "Where is the nearest restaurant?": "¿Dónde está el restaurante más cercano?"
            },
            "fr": {
                "Hello, how are you?": "Bonjour, comment allez-vous?",
                "I am visiting France": "Je visite la France",
                "Can you help me?": "Pouvez-vous m'aider?",
                "Where is the nearest restaurant?": "Où est le restaurant le plus proche?"
            }
        }
        
        self.translation_history = {}
    
    def translate_text(self, text: str, target_language: str, source_language: str = "auto", context: str = None) -> Dict:
        """Translate text to target language"""
        
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        if target_language not in self.supported_languages:
            raise ValueError(f"Unsupported target language: {target_language}")
        
        # Detect source language
        detected_source = self.detect_language(text) if source_language == "auto" else source_language
        
        # Get translation
        if target_language in self.translation_examples:
            examples = self.translation_examples[target_language]
            translated_text = examples.get(text, f"[{target_language.upper()}] {text}")
        else:
            translated_text = f"[{target_language.upper()}] {text}"
        
        # Apply context
        if context:
            translated_text = f"[{context.upper()}] {translated_text}"
        
        return {
            "original_text": text,
            "translated_text": translated_text,
            "source_language": detected_source,
            "source_language_name": self.supported_languages.get(detected_source, "Unknown"),
            "target_language": target_language,
            "target_language_name": self.supported_languages.get(target_language, "Unknown"),
            "confidence": 0.90,
            "context": context,
            "translation_service": "Translation Service",
            "translation_time": datetime.now().isoformat(),
            "character_count": len(text),
            "word_count": len(text.split())
        }
    
    def translate_itinerary(self, itinerary_data: Dict, target_language: str, translate_fields: List[str] = None) -> Dict:
        """Translate itinerary data"""
        
        if target_language not in self.supported_languages:
            raise ValueError(f"Unsupported target language: {target_language}")
        
        default_fields = ["title", "description", "name", "destination", "activity_name", "notes"]
        fields_to_translate = translate_fields or default_fields
        
        translated_itinerary = {
            "original_language": "en",
            "target_language": target_language,
            "target_language_name": self.supported_languages[target_language],
            "translation_timestamp": datetime.now().isoformat(),
            "translated_fields": []
        }
        
        def translate_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if key in fields_to_translate and isinstance(value, str) and value.strip():
                        try:
                            result = self.translate_text(value, target_language, context="travel")
                            obj[key] = result["translated_text"]
                            translated_itinerary["translated_fields"].append(current_path)
                        except Exception as e:
                            logger.warning(f"Failed to translate field {current_path}: {e}")
                            obj[key] = f"[{target_language.upper()}] {value}"
                    elif isinstance(value, (dict, list)):
                        translate_recursive(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    translate_recursive(item, f"{path}[{i}]")
        
        translated_data = json.loads(json.dumps(itinerary_data))  # Deep copy
        translate_recursive(translated_data)
        
        translated_itinerary["itinerary"] = translated_data
        translated_itinerary["fields_translated"] = len(translated_itinerary["translated_fields"])
        
        return translated_itinerary
    
    def get_local_phrases(self, destination: str, user_language: str = "en", categories: List[str] = None) -> Dict:
        """Get local phrases for destination"""
        
        destination_lower = destination.lower()
        phrases_data = None
        matched_destination = None
        
        for dest_key, dest_phrases in self.phrase_database.items():
            if dest_key in destination_lower:
                phrases_data = dest_phrases
                matched_destination = dest_key
                break
        
        if not phrases_data:
            phrases_data = {
                "en": [
                    {"english": "Hello", "local": "Hello", "pronunciation": "heh-lo", "context": "greeting"},
                    {"english": "Thank you", "local": "Thank you", "pronunciation": "thank you", "context": "gratitude"}
                ]
            }
            matched_destination = "general"
        
        local_language = list(phrases_data.keys())[0]
        phrases = phrases_data[local_language]
        
        # Filter by categories if specified
        if categories:
            phrases = [p for p in phrases if p.get("context") in categories]
        
        # Categorize phrases
        categorized_phrases = {}
        for phrase in phrases:
            category = phrase.get("context", "general")
            if category not in categorized_phrases:
                categorized_phrases[category] = []
            categorized_phrases[category].append(phrase)
        
        return {
            "destination": destination,
            "matched_destination": matched_destination.title(),
            "local_language": local_language,
            "local_language_name": self.supported_languages.get(local_language, "Local Language"),
            "user_language": user_language,
            "phrases_by_category": categorized_phrases,
            "total_phrases": len(phrases),
            "categories_available": list(categorized_phrases.keys()),
            "essential_phrases": phrases[:5],
            "cultural_tips": self.get_cultural_tips(matched_destination)
        }
    
    def get_cultural_tips(self, destination: str) -> List[str]:
        """Get cultural tips for destination"""
        tips = {
            "india": [
                "Use 'Namaste' with palms together as a respectful greeting",
                "Remove shoes before entering homes and temples",
                "Use your right hand for eating and greeting"
            ],
            "spain": [
                "Meals are typically eaten later than in other countries",
                "A light kiss on both cheeks is a common greeting",
                "Siesta time (2-5 PM) - many shops may be closed"
            ],
            "france": [
                "Always say 'Bonjour' when entering shops",
                "French people value politeness and formal greetings",
                "Dress well - appearance matters in French culture"
            ]
        }
        return tips.get(destination, ["Learn basic local phrases", "Respect local customs"])
    
    def detect_language(self, text: str) -> str:
        """Simple language detection"""
        text_lower = text.lower()
        
        # Hindi patterns
        if any(char in text for char in "नमस्ते धन्यवाद कृपया"):
            return "hi"
        # Spanish patterns
        elif any(char in text for char in "¿¡ñáéíóú"):
            return "es"
        # French patterns
        elif any(char in text for char in "àâäéèêëïîôöùûü"):
            return "fr"
        # Check for common words
        elif any(word in text_lower for word in ["hola", "gracias"]):
            return "es"
        elif any(word in text_lower for word in ["bonjour", "merci"]):
            return "fr"
        elif any(word in text_lower for word in ["namaste", "dhanyawad"]):
            return "hi"
        else:
            return "en"
    
    def save_translation_history(self, user_id: int, translation_data: Dict):
        """Save translation to history"""
        if user_id not in self.translation_history:
            self.translation_history[user_id] = []
        
        history_entry = {
            "id": len(self.translation_history[user_id]) + 1,
            "timestamp": datetime.now().isoformat(),
            **translation_data
        }
        
        self.translation_history[user_id].append(history_entry)
        
        # Keep only last 50 translations
        if len(self.translation_history[user_id]) > 50:
            self.translation_history[user_id] = self.translation_history[user_id][-50:]
    
    def get_translation_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get user translation history"""
        if user_id not in self.translation_history:
            return []
        
        return sorted(
            self.translation_history[user_id],
            key=lambda x: x["timestamp"],
            reverse=True
        )[:limit]

# Initialize service
translation_service = TranslationService()

# ✅ Create router
router = APIRouter(prefix="/translation", tags=["🌍 Translation Service"])

# ✅ Enums
class LanguageCode(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    JAPANESE = "ja"
    KOREAN = "ko"
    CHINESE = "zh"

class ContextType(str, Enum):
    TRAVEL = "travel"
    BUSINESS = "business"
    CASUAL = "casual"
    FORMAL = "formal"
    EMERGENCY = "emergency"

# ✅ Pydantic Models
class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    target_language: str = Field(..., min_length=2, max_length=5)
    source_language: str = Field("auto")
    context: Optional[str] = Field(None)
    save_to_history: bool = Field(True)
    
    @validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Text cannot be empty')
        return v.strip()
    
    @validator('target_language')
    def validate_target_language(cls, v):
        if len(v) < 2:
            raise ValueError('Language code must be at least 2 characters')
        return v.lower()

class ItineraryTranslationRequest(BaseModel):
    itinerary_data: Dict[str, Any] = Field(...)
    target_language: str = Field(..., min_length=2, max_length=5)
    translate_fields: Optional[List[str]] = Field(None)

class LocalPhrasesRequest(BaseModel):
    destination: str = Field(..., min_length=1, max_length=100)
    user_language: str = Field("en")
    categories: Optional[List[str]] = Field(None)

class BatchTranslationRequest(BaseModel):
    texts: List[str] = Field(..., min_items=1, max_items=50)
    target_language: str = Field(..., min_length=2, max_length=5)
    source_language: str = Field("auto")
    context: Optional[str] = Field(None)
    
    @validator('texts')
    def validate_texts(cls, v):
        return [text.strip() for text in v if text and text.strip()]

# ✅ Helper functions
async def get_current_user_id() -> int:
    return 1

# ✅ API Endpoints
@router.post("/translate")
async def translate_text(
    request: TranslationRequest,
    user_id: int = Depends(get_current_user_id)
):
    """Translate text to target language"""
    try:
        if request.target_language not in translation_service.supported_languages:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported target language: {request.target_language}"
            )
        
        result = translation_service.translate_text(
            text=request.text,
            target_language=request.target_language,
            source_language=request.source_language,
            context=request.context
        )
        
        # Save to history
        if request.save_to_history:
            translation_service.save_translation_history(user_id, {
                "type": "text",
                "original_text": request.text,
                "translated_text": result["translated_text"],
                "source_language": result["source_language"],
                "target_language": request.target_language,
                "context": request.context
            })
        
        return {
            "success": True,
            "translation": result,
            "service": "Translation Service v1.0"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

@router.post("/translate-itinerary")
async def translate_itinerary(
    request: ItineraryTranslationRequest,
    user_id: int = Depends(get_current_user_id)
):
    """Translate itinerary data"""
    try:
        if request.target_language not in translation_service.supported_languages:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported target language: {request.target_language}"
            )
        
        translated_itinerary = translation_service.translate_itinerary(
            itinerary_data=request.itinerary_data,
            target_language=request.target_language,
            translate_fields=request.translate_fields
        )
        
        # Save to history
        translation_service.save_translation_history(user_id, {
            "type": "itinerary",
            "target_language": request.target_language,
            "fields_translated": translated_itinerary["fields_translated"]
        })
        
        return {
            "success": True,
            "translated_itinerary": translated_itinerary,
            "service": "Translation Service v1.0"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Itinerary translation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Itinerary translation failed: {str(e)}")

@router.post("/local-phrases")
async def get_local_phrases(request: LocalPhrasesRequest):
    """Get local phrases for destination"""
    try:
        phrases = translation_service.get_local_phrases(
            destination=request.destination,
            user_language=request.user_language,
            categories=request.categories
        )
        
        return {
            "success": True,
            "destination_phrases": phrases,
            "service": "Translation Service v1.0"
        }
        
    except Exception as e:
        logger.error(f"Failed to get local phrases: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get local phrases: {str(e)}")

@router.post("/batch-translate")
async def batch_translate(
    request: BatchTranslationRequest,
    user_id: int = Depends(get_current_user_id)
):
    """Translate multiple texts"""
    try:
        if request.target_language not in translation_service.supported_languages:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported target language: {request.target_language}"
            )
        
        translations = []
        successful_count = 0
        
        for i, text in enumerate(request.texts):
            try:
                result = translation_service.translate_text(
                    text=text,
                    target_language=request.target_language,
                    source_language=request.source_language,
                    context=request.context
                )
                
                translations.append({
                    "index": i,
                    "success": True,
                    "original_text": text,
                    "translated_text": result["translated_text"],
                    "confidence": result["confidence"]
                })
                successful_count += 1
                
            except Exception as e:
                translations.append({
                    "index": i,
                    "success": False,
                    "original_text": text,
                    "error": str(e)
                })
        
        # Save to history
        translation_service.save_translation_history(user_id, {
            "type": "batch",
            "target_language": request.target_language,
            "total_texts": len(request.texts),
            "successful_translations": successful_count
        })
        
        return {
            "success": True,
            "batch_translation": {
                "translations": translations,
                "statistics": {
                    "total_texts": len(request.texts),
                    "successful": successful_count,
                    "failed": len(request.texts) - successful_count,
                    "success_rate": round((successful_count / len(request.texts)) * 100, 1)
                }
            },
            "service": "Translation Service v1.0"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch translation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch translation failed: {str(e)}")

@router.get("/supported-languages")
async def get_supported_languages():
    """Get supported languages"""
    try:
        languages = translation_service.supported_languages
        
        language_details = []
        for code, name in languages.items():
            parts = name.split(" (")
            english_name = parts[0]
            native_name = parts[1].rstrip(")") if len(parts) > 1 else english_name
            
            language_details.append({
                "code": code,
                "english_name": english_name,
                "native_name": native_name,
                "full_name": name
            })
        
        return {
            "success": True,
            "supported_languages": languages,
            "language_details": language_details,
            "total_languages": len(languages),
            "service": "Translation Service v1.0"
        }
        
    except Exception as e:
        logger.error(f"Failed to get supported languages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get supported languages: {str(e)}")

@router.get("/detect-language")
async def detect_language(
    text: str = Query(..., min_length=1, max_length=1000)
):
    """Detect language of text"""
    try:
        detected_lang = translation_service.detect_language(text)
        
        return {
            "success": True,
            "text": text,
            "detected_language": detected_lang,
            "language_name": translation_service.supported_languages.get(detected_lang, "Unknown"),
            "confidence": 0.85,
            "text_length": len(text),
            "service": "Translation Service v1.0"
        }
        
    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Language detection failed: {str(e)}")

@router.get("/history/{user_id}")
async def get_translation_history(
    user_id: int,
    limit: int = Query(20, ge=1, le=100)
):
    """Get user translation history"""
    try:
        history = translation_service.get_translation_history(user_id, limit)
        
        return {
            "success": True,
            "user_id": user_id,
            "translation_history": history,
            "total_translations": len(history),
            "service": "Translation Service v1.0"
        }
        
    except Exception as e:
        logger.error(f"Failed to get translation history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get translation history: {str(e)}")

@router.get("/popular-destinations")
async def get_popular_destinations():
    """Get popular destinations with phrase support"""
    
    destinations = []
    for dest_key, phrases_data in translation_service.phrase_database.items():
        primary_lang = list(phrases_data.keys())[0]
        phrase_count = len(phrases_data[primary_lang])
        
        destinations.append({
            "destination": dest_key.title(),
            "primary_language": primary_lang,
            "language_name": translation_service.supported_languages.get(primary_lang, "Unknown"),
            "phrases_available": phrase_count,
            "cultural_tips": translation_service.get_cultural_tips(dest_key),
            "sample_phrase": phrases_data[primary_lang][0] if phrase_count > 0 else None
        })
    
    return {
        "success": True,
        "popular_destinations": destinations,
        "total_destinations": len(destinations),
        "service": "Translation Service v1.0"
    }

@router.get("/examples/{language}")
async def get_translation_examples(language: str):
    """Get translation examples for language"""
    try:
        if language not in translation_service.supported_languages:
            raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")
        
        examples = translation_service.translation_examples.get(language, {})
        
        if not examples:
            examples = {
                "Hello": f"[{language.upper()}] Hello",
                "Thank you": f"[{language.upper()}] Thank you",
                "Please": f"[{language.upper()}] Please"
            }
        
        example_list = [
            {
                "english": english_text,
                "translated": translated_text,
                "language": language,
                "language_name": translation_service.supported_languages[language]
            }
            for english_text, translated_text in examples.items()
        ]
        
        return {
            "success": True,
            "language": language,
            "language_name": translation_service.supported_languages[language],
            "translation_examples": example_list,
            "total_examples": len(example_list),
            "service": "Translation Service v1.0"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get translation examples: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get translation examples: {str(e)}")

@router.get("/health")
async def translation_health():
    """Translation service health check"""
    try:
        return {
            "success": True,
            "service": "translation",
            "status": "healthy",
            "version": "1.0.0",
            "features": {
                "text_translation": True,
                "batch_translation": True,
                "itinerary_translation": True,
                "local_phrases": True,
                "language_detection": True,
                "translation_history": True
            },
            "capabilities": {
                "supported_languages_count": len(translation_service.supported_languages),
                "destinations_with_phrases": len(translation_service.phrase_database),
                "batch_translation_limit": 50,
                "text_length_limit": 5000
            },
            "supported_languages": list(translation_service.supported_languages.keys()),
            "destinations_supported": list(translation_service.phrase_database.keys()),
            "last_health_check": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Translation health check failed: {e}")
        return {
            "success": False,
            "service": "translation",
            "status": "degraded",
            "error": str(e),
            "last_health_check": datetime.now().isoformat()
        }
