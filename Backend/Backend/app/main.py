from fastapi.responses import JSONResponse
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import json
import uvicorn
import os
import logging
import sys
import importlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Tags metadata for better docs organization
tags_metadata = [
    {
        "name": "🧠 Itinerary Optimization",
        "description": "**Smart itinerary optimization** using greedy algorithm with time scheduling. Formula: **score = w1×(rating) - w2×(distance) - w3×(traffic) + w4×(weather_match)**. Create optimal travel routes with arrival/departure times.",
    },
    {
        "name": "🚨 SOS Emergency System", 
        "description": "**Emergency SOS system** with SMS integration for sending alerts to emergency contacts with GPS location. Life-saving feature for travelers.",
    },
    {
        "name": "🔔 Push Notifications",
        "description": "**Push notification system** for flight updates, weather alerts, itinerary changes, and travel notifications with real-time delivery.",
    },
    {
        "name": "🌍 Translation Service",
        "description": "**Real-time language translation** service with automatic language detection and bulk translation support.",
    },
    {
        "name": "✈️ Flight Tracking",
        "description": "**Flight tracking and search** functionality with real-time updates, delay notifications, and comprehensive flight management.",
    },
    {
        "name": "💎 Hidden Gems Discovery",
        "description": "**Hidden gems discovery** system with community-submitted locations, eco-friendly recommendations, and local insights.",
    },
    {
        "name": "🏆 Rewards & Gamification",
        "description": "**Gamification and rewards** system with eco-points, achievements, leaderboards, and sustainable travel incentives.",
    },
    {
        "name": "📍 Location Services",
        "description": "**Location tracking and geofencing** with eco-travel monitoring, carbon footprint calculation, and smart location services.",
    },
    {
        "name": "🌤️ Weather Service",
        "description": "**Weather forecasting and alerts** for travel planning with conditions, forecasts, and travel recommendations.",
    },
    {
        "name": "📍 Places & Events",
        "description": "**Places search and events discovery** with local recommendations and activity suggestions.",
    },
    {
        "name": "📤 Export & Sharing",
        "description": "**Export itineraries** and share travel plans with enhanced formatting and social features.",
    },
    {
        "name": "🏠 Core API",
        "description": "**Core API endpoints** including health checks, user management, chatbot integration, and general travel services.",
    }
]

# ✅ Initialize all service status variables FIRST
ITINERARY_ENABLED = False
SOS_ENABLED = False
FLIGHTS_ENABLED = False
TRANSLATION_ENABLED = False
NOTIFICATIONS_ENABLED = False
GAMIFICATION_ENABLED = False
EXPORT_ENABLED = False
WEATHER_ENABLED = False
PLACES_ENABLED = False
EVENTS_ENABLED = False
ALGORITHM_SERVICE_AVAILABLE = False
DATABASE_AVAILABLE = False

# ✅ Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Add routers directory specifically
routers_path = os.path.join(current_dir, 'routers')
if routers_path not in sys.path:
    sys.path.insert(0, routers_path)

# ✅ Import database components (CLEAN)
try:
    try:
        from database import get_db, create_tables
        logger.info("✅ Database components imported successfully")
        DATABASE_AVAILABLE = True
    except ImportError:
        try:
            from .database import get_db, create_tables
            logger.info("✅ Database components imported successfully (relative)")
            DATABASE_AVAILABLE = True
        except ImportError:
            logger.warning("❌ Database not available")
            DATABASE_AVAILABLE = False
            def get_db():
                return None
            def create_tables():
                pass
except Exception as e:
    logger.warning(f"❌ Database import failed: {e}")
    DATABASE_AVAILABLE = False
    def get_db():
        return None
    def create_tables():
        pass

# ✅ Application Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    logger.info("🚀 Live Trip API Starting Up...")
    
    # Initialize database
    try:
        if DATABASE_AVAILABLE:
            create_tables()
            logger.info("📍 Database Available: True")
        else:
            logger.info("📍 Database Available: False (Mock Mode)")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Check algorithm service
    try:
        from services.algorithm_service import algorithm_service
        global ALGORITHM_SERVICE_AVAILABLE
        ALGORITHM_SERVICE_AVAILABLE = algorithm_service is not None
        if ALGORITHM_SERVICE_AVAILABLE:
            logger.info("🧠 Algorithm Service: Available")
        else:
            logger.info("🧠 Algorithm Service: Not Available")
    except ImportError:
        logger.info("🧠 Algorithm Service: Not Available")
        ALGORITHM_SERVICE_AVAILABLE = False
    
    logger.info("✅ Live Trip API ready!")
    yield
    logger.info("👋 Live Trip API shutting down...")

# ✅ Create FastAPI app with enhanced metadata
app = FastAPI(
    title="🌍 Live Trip - Smart Travel Planning API",
    description="""
    **🚀 Advanced Travel Planning Backend for Live Trip Project**
    
    ## 🔥 Key Features:
    * **🧠 Smart Itinerary Optimization** - Greedy algorithm with complete time scheduling
    * **⏰ Complete Time Management** - Arrival/departure times, daily schedules, break planning
    * **🚨 SOS Emergency System** - SMS alerts with GPS location
    * **✈️ Real-time Flight Tracking** - Live updates and delay notifications  
    * **🌍 Language Translation** - Multi-language support with pronunciations
    * **🔔 Push Notifications** - Weather, flight, and travel alerts
    * **💎 Hidden Gems Discovery** - Community-driven local recommendations
    * **🏆 Eco Gamification** - Rewards for sustainable travel choices
    * **📍 Smart Location Services** - Geofencing and carbon tracking
    * **🌤️ Weather Intelligence** - Forecasts and travel recommendations
    * **🤖 Chatbot Integration** - AI-powered travel assistant
    
    ## 🧮 Enhanced Greedy Algorithm Formula:
    `score = w1×(rating) - w2×(distance) - w3×(traffic) + w4×(weather_match)`
    
    **🆕 NEW**: Complete time scheduling with arrival/departure times, daily schedules, and break planning!
    
    ## 🔗 Quick Links:
    - **Create Complete Itinerary**: `/api/itinerary/create-complete-itinerary`
    - **Weather Forecast**: `/api/weather/current`
    - **Flight Tracking**: `/api/flights/status`
    - **SOS Emergency**: `/api/sos/trigger`
    - **Health Check**: `/health`
    - **API Documentation**: `/docs` (this page)
    """,
    version="2.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    contact={
        "name": "Live Trip API Support",
        "email": "support@livetrip.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# ✅ CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:5173", 
        "http://localhost:8000",
        "http://localhost:8501",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8501",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ **ENHANCED ROUTER IMPORTS** - Fixed with better error handling
def safe_import_router(module_name, router_name, enabled_flag_name):
    """Safely import a router module with enhanced debugging"""
    try:
        module = None
        
        # Strategy 1: Direct import from routers
        try:
            module = importlib.import_module(module_name)
            logger.debug(f"Direct import success for {module_name}")
        except ImportError:
            pass
            
        # Strategy 2: Try routers.module_name  
        if not module:
            try:
                module = importlib.import_module(f"routers.{module_name}")
                logger.debug(f"Routers import success for {module_name}")
            except ImportError:
                pass
                
        # Strategy 3: Try app.routers.module_name
        if not module:
            try:
                module = importlib.import_module(f"app.routers.{module_name}")
                logger.debug(f"App.routers import success for {module_name}")
            except ImportError:
                pass
        
        # Check if module was imported and has router
        if module and hasattr(module, 'router'):
            router_obj = getattr(module, 'router')
            if router_obj is not None:
                app.include_router(router_obj, prefix="/api")
                globals()[enabled_flag_name] = True
                # Avoid Unicode in logs to prevent Windows charmap issues
                logger.info(f"{router_name} router loaded successfully")
                return True
            else:
                logger.warning(f"❌ {router_name} router is None")
                return False
        else:
            logger.warning(f"❌ {router_name} router module not found or no 'router' attribute")
            return False
            
    except Exception as e:
        logger.error(f"❌ {router_name} router error: {e}")
        return False

# LiveTrip features (registered first so they win over older overlapping routes)
import livetrip
livetrip.install(app)

# ✅ Import all routers using the enhanced safe import function
logger.info("🔄 Loading routers...")

# Core travel routers
safe_import_router("weather", "Weather", "WEATHER_ENABLED")
safe_import_router("places", "Places", "PLACES_ENABLED")
safe_import_router("events", "Events", "EVENTS_ENABLED")
safe_import_router("flights", "Flights", "FLIGHTS_ENABLED")

# Advanced feature routers
safe_import_router("itinerary", "Itinerary", "ITINERARY_ENABLED")
safe_import_router("translation", "Translation", "TRANSLATION_ENABLED")
safe_import_router("notifications", "Notifications", "NOTIFICATIONS_ENABLED")
safe_import_router("sos", "SOS Emergency", "SOS_ENABLED")

# Gamification routers
gamification_count = 0
if safe_import_router("rewards", "Rewards", "temp1"):
    gamification_count += 1
if safe_import_router("location", "Location", "temp2"):
    gamification_count += 1
if safe_import_router("discovery", "Discovery", "temp3"):
    gamification_count += 1

GAMIFICATION_ENABLED = gamification_count >= 2
if GAMIFICATION_ENABLED:
    logger.info("✅ Gamification system loaded successfully")

# Export router
safe_import_router("export", "Export", "EXPORT_ENABLED")

# Multi-day planner (root planner merged in as app.rootplan)
from routers import multiday
app.include_router(multiday.router)

# Clear OpenAPI schema cache to reflect new routes
app.openapi_schema = None

# ✅ Enhanced Pydantic Models
class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    emergency_contact_name: str = Field(..., min_length=1, max_length=100)
    emergency_contact_phone: str = Field(..., min_length=10, max_length=20)
    emergency_contact_relationship: str = Field("family", max_length=50)

class EmergencyContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)
    relationship: str = Field(..., max_length=50)
    is_primary: bool = False

class SOSAlertCreate(BaseModel):
    alert_type: str = Field("emergency", max_length=50)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    location_address: Optional[str] = Field(None, max_length=500)
    message: Optional[str] = Field("Emergency! Please help me.", max_length=1000)
    trip_id: Optional[int] = None

class TripCreate(BaseModel):
    destination: str = Field(..., min_length=1, max_length=200)
    start_date: date
    end_date: date
    budget: float = Field(..., gt=0)
    preferences: Dict = Field(default_factory=dict)
    mood: Optional[str] = Field("happy", max_length=50)
    eco_mode_enabled: Optional[bool] = False
    transport_preference: Optional[str] = Field("mixed", max_length=50)

class FeedbackCreate(BaseModel):
    trip_id: int = Field(..., gt=0)
    feedback_type: str = Field(..., max_length=100)
    rating: int = Field(..., ge=1, le=5)
    comments: str = Field(..., max_length=2000)
    location_name: Optional[str] = Field(None, max_length=200)
    activity_name: Optional[str] = Field(None, max_length=200)
    eco_rating: Optional[int] = Field(None, ge=1, le=5)

class TripResponse(BaseModel):
    id: int
    destination: str
    start_date: date
    end_date: date
    budget: float
    mood: str
    eco_mode_enabled: Optional[bool] = False
    transport_preference: Optional[str] = "mixed"
    created_at: datetime

    class Config:
        from_attributes = True

# Smart Chatbot Integration Models
class ChatbotIntent(BaseModel):
    category: str = Field(..., max_length=100)
    action: str = Field(..., max_length=100)
    activity: Optional[str] = Field(None, max_length=200)
    confidence: float = Field(..., ge=0, le=1)
    location: Optional[str] = Field(None, max_length=200)
    timestamp: Optional[str] = None

class ChatbotResponse(BaseModel):
    status: str
    reasoning: Optional[str] = None
    suggested_changes: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None

# ✅ Root & Health Endpoints
@app.get("/", 
         summary="Live Trip API Root",
         description="Get API information and available features for Live Trip",
         tags=["🏠 Core API"])
async def root():
    """Get API information and available features"""
    features = ["basic-travel-planning"]
    
    if WEATHER_ENABLED:
        features.append("weather-forecasting")
    if PLACES_ENABLED:
        features.append("places-search")
    if EVENTS_ENABLED:
        features.append("events-discovery")
    if TRANSLATION_ENABLED:
        features.append("real-time-translation")
    if SOS_ENABLED:
        features.append("sos-emergency-system")
    if FLIGHTS_ENABLED:
        features.append("flight-tracking")
    if NOTIFICATIONS_ENABLED:
        features.append("push-notifications")
    if GAMIFICATION_ENABLED:
        features.extend(["eco-mode", "hidden-gems", "rewards"])
    if ITINERARY_ENABLED:
        features.append("smart-itinerary-optimization")
    if ALGORITHM_SERVICE_AVAILABLE:
        features.extend(["greedy-algorithm", "complete-time-scheduling"])
    if EXPORT_ENABLED:
        features.append("export-sharing")
    
    features.append("smart-chatbot-integration")
    
    return {
        "message": "🌍 Live Trip - Smart Travel Planning API", 
        "version": "2.0.0", 
        "project": "Live Trip Hackathon Project",
        "features": features,
        "algorithm": "greedy_scoring_with_complete_time_scheduling" if ALGORITHM_SERVICE_AVAILABLE else "basic",
        "new_features": {
            "complete_time_scheduling": ALGORITHM_SERVICE_AVAILABLE,
            "arrival_departure_times": ALGORITHM_SERVICE_AVAILABLE,
            "daily_schedule_generation": ALGORITHM_SERVICE_AVAILABLE,
            "break_time_calculation": ALGORITHM_SERVICE_AVAILABLE,
            "weather_intelligence": WEATHER_ENABLED,
            "places_discovery": PLACES_ENABLED,
            "events_finder": EVENTS_ENABLED
        },
        "docs": "/docs",
        "health": "/health",
        "services": {
            "weather": WEATHER_ENABLED,
            "places": PLACES_ENABLED,
            "events": EVENTS_ENABLED,
            "itinerary_optimization": ITINERARY_ENABLED,
            "sos_emergency": SOS_ENABLED,
            "flight_tracking": FLIGHTS_ENABLED,
            "translation": TRANSLATION_ENABLED,
            "gamification": GAMIFICATION_ENABLED,
            "notifications": NOTIFICATIONS_ENABLED,
            "export": EXPORT_ENABLED,
            "algorithm_service": ALGORITHM_SERVICE_AVAILABLE
        },
        "chatbot_integration": True,
        "endpoints": {
            "weather": "/api/weather/current" if WEATHER_ENABLED else None,
            "places": "/api/places/search" if PLACES_ENABLED else None,
            "events": "/api/events/search" if EVENTS_ENABLED else None,
            "flights": "/api/flights/status" if FLIGHTS_ENABLED else None,
            "itinerary": "/api/itinerary/create-complete-itinerary" if ITINERARY_ENABLED else None,
            "sos": "/api/sos/trigger" if SOS_ENABLED else None,
            "translation": "/api/translation/translate" if TRANSLATION_ENABLED else None
        }
    }

@app.get("/health",
         summary="Health Check",
         description="Comprehensive health check with service status for Live Trip",
         tags=["🏠 Core API"])
async def health_check():
    """Enhanced health check with service status"""
    try:
        database_status = "unavailable"
        if DATABASE_AVAILABLE:
            try:
                db = next(get_db()) if get_db else None
                if db:
                    # Simple database check
                    database_status = "connected"
                else:
                    database_status = "mock_mode"
            except Exception as e:
                database_status = f"error: {str(e)[:50]}"
        
        return {
            "status": "healthy", 
            "timestamp": datetime.now().isoformat(),
            "project": "Live Trip API",
            "version": "2.0.0",
            "database": database_status,
            "algorithm_features": {
                "greedy_optimization": ALGORITHM_SERVICE_AVAILABLE,
                "complete_time_scheduling": ALGORITHM_SERVICE_AVAILABLE,
                "daily_schedule_generation": ALGORITHM_SERVICE_AVAILABLE,
                "break_time_planning": ALGORITHM_SERVICE_AVAILABLE,
                "arrival_departure_times": ALGORITHM_SERVICE_AVAILABLE,
                "cost_estimation": ALGORITHM_SERVICE_AVAILABLE,
                "alternative_routes": ALGORITHM_SERVICE_AVAILABLE
            },
            "services": {
                "weather": WEATHER_ENABLED,
                "places": PLACES_ENABLED,
                "events": EVENTS_ENABLED,
                "itinerary_optimization": ITINERARY_ENABLED,
                "greedy_algorithm": ALGORITHM_SERVICE_AVAILABLE,
                "sos_system": SOS_ENABLED,
                "flights": FLIGHTS_ENABLED,
                "translation": TRANSLATION_ENABLED,
                "gamification": GAMIFICATION_ENABLED,
                "notifications": NOTIFICATIONS_ENABLED,
                "export": EXPORT_ENABLED
            },
            "endpoints": {
                "total_routes": len(app.routes),
                "itinerary_complete": "/api/itinerary/create-complete-itinerary" if ITINERARY_ENABLED else None,
                "weather_current": "/api/weather/current" if WEATHER_ENABLED else None,
                "places_search": "/api/places/search" if PLACES_ENABLED else None,
                "flights_status": "/api/flights/status" if FLIGHTS_ENABLED else None,
                "docs": "/docs",
                "openapi": "/openapi.json"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# ✅ Enhanced Smart Chatbot Integration
@app.post("/api/chatbot/quick-suggestion", 
          response_model=ChatbotResponse,
          summary="Quick AI Suggestion",
          description="Get quick AI-powered suggestions based on user intent",
          tags=["🏠 Core API"])
async def quick_suggestion(intent: ChatbotIntent):
    """Smart suggestion endpoint for chatbot integration"""
    try:
        category = intent.category.lower()
        
        if category == "emergency":
            return ChatbotResponse(
                status="emergency_alert_ready" if SOS_ENABLED else "emergency_unavailable",
                reasoning="🚨 Emergency detected - SOS system activated" if SOS_ENABLED else "🚨 Emergency detected - SOS system not available",
                message="🚨 EMERGENCY DETECTED! I can immediately alert your emergency contacts with your location. Say 'trigger SOS' to activate emergency alert." if SOS_ENABLED else "🚨 Emergency detected. Please contact local emergency services: 112 or 911"
            )
        elif category == "weather":
            return ChatbotResponse(
                status="weather_available" if WEATHER_ENABLED else "weather_unavailable",
                reasoning="🌤️ Weather service available" if WEATHER_ENABLED else "🌤️ Weather service not available",
                message="🌤️ I can provide weather forecasts, travel conditions, and weather alerts for your destination!" if WEATHER_ENABLED else "Weather service is currently unavailable"
            )
        elif category == "itinerary":
            if ALGORITHM_SERVICE_AVAILABLE:
                return ChatbotResponse(
                    status="complete_optimization_available",
                    reasoning="🧠 Complete itinerary optimization with time scheduling available",
                    message="🧠 I can create a complete optimized itinerary with arrival/departure times, daily schedules, break planning, and cost estimation! Using advanced greedy algorithm: w1×(rating) - w2×(distance) - w3×(traffic) + w4×(weather_match)"
                )
            elif ITINERARY_ENABLED:
                return ChatbotResponse(
                    status="basic_optimization_available",
                    reasoning="🧠 Basic itinerary optimization available",
                    message="🧠 I can help optimize your route using available services."
                )
            else:
                return ChatbotResponse(
                    status="itinerary_unavailable",
                    reasoning="Itinerary service not available",
                    message="Itinerary optimization is currently unavailable."
                )
        else:
            services = []
            if WEATHER_ENABLED:
                services.append("weather forecasting")
            if PLACES_ENABLED:
                services.append("places search")
            if FLIGHTS_ENABLED:
                services.append("flight tracking")
            if SOS_ENABLED:
                services.append("SOS emergencies")
            if TRANSLATION_ENABLED:
                services.append("translation")
            if ITINERARY_ENABLED:
                services.append("itinerary optimization")
            
            services_text = ", ".join(services) if services else "basic travel assistance"
            
            return ChatbotResponse(
                status="general_assistance",
                reasoning="✅ Live Trip assistant ready to help",
                message=f"Hello! I'm your Live Trip assistant. I can help with {services_text}{'with complete time scheduling' if ALGORITHM_SERVICE_AVAILABLE else ''}. What would you like to do?"
            )
    except Exception as e:
        logger.error(f"Error in quick_suggestion: {e}")
        return ChatbotResponse(status="error", message=f"Error processing suggestion: {str(e)}")

@app.get("/api/chatbot/status",
         summary="Chatbot Integration Status",
         description="Get chatbot integration status and available features",
         tags=["🏠 Core API"])
async def chatbot_status():
    """Chatbot integration status and available features"""
    return {
        "chatbot_integration": "active",
        "project": "Live Trip",
        "version": "2.0.0",
        "enhanced_features": {
            "complete_time_scheduling": ALGORITHM_SERVICE_AVAILABLE,
            "daily_schedule_generation": ALGORITHM_SERVICE_AVAILABLE, 
            "break_time_planning": ALGORITHM_SERVICE_AVAILABLE,
            "arrival_departure_times": ALGORITHM_SERVICE_AVAILABLE,
            "weather_intelligence": WEATHER_ENABLED,
            "places_discovery": PLACES_ENABLED,
            "events_finder": EVENTS_ENABLED
        },
        "features": {
            "weather": WEATHER_ENABLED,
            "places": PLACES_ENABLED,
            "events": EVENTS_ENABLED,
            "itinerary_optimization": ITINERARY_ENABLED,
            "greedy_algorithm": ALGORITHM_SERVICE_AVAILABLE,
            "sos_emergency_system": SOS_ENABLED,
            "flight_tracking": FLIGHTS_ENABLED,
            "translation": TRANSLATION_ENABLED,
            "gamification": GAMIFICATION_ENABLED,
            "export": EXPORT_ENABLED
        },
        "primary_endpoints": {
            "weather": "/api/weather/current" if WEATHER_ENABLED else None,
            "places": "/api/places/search" if PLACES_ENABLED else None,
            "events": "/api/events/search" if EVENTS_ENABLED else None,
            "complete_itinerary": "/api/itinerary/create-complete-itinerary" if ITINERARY_ENABLED else None,
            "multi_day_itinerary": "/api/itinerary/plan-multi-day",
            "sample_multi_day": "/api/itinerary/multi-day/sample",
            "sos_trigger": "/api/sos/trigger" if SOS_ENABLED else None,
            "flight_status": "/api/flights/status" if FLIGHTS_ENABLED else None,
            "translate": "/api/translation/translate" if TRANSLATION_ENABLED else None,
            "health": "/health"
        }
    }

# ✅ Multi-day Itinerary Planning Models
class MultiDayPlanRequest(BaseModel):
    city: str = Field(..., description="Destination city")
    days: int = Field(..., ge=1, le=14, description="Number of days (1-14)")
    start_time: str = Field(default="09:00", description="Daily start time (HH:MM)")
    end_time: str = Field(default="19:00", description="Daily end time (HH:MM)")
    mode: str = Field(default="walking", description="Transportation mode: driving, walking, transit")
    pace: str = Field(default="normal", description="Travel pace: slow, normal, fast")
    hotel: Dict[str, float] = Field(default={"lat": 0, "lng": 0}, description="Hotel coordinates")

class MultiDayPOI(BaseModel):
    name: str
    category: str
    arrive_at: str
    depart_at: str
    duration_min: int

class MultiDayItinerary(BaseModel):
    date: str
    items: List[MultiDayPOI]
    stats: Dict[str, int]

class MultiDayPlanResponse(BaseModel):
    days: List[MultiDayItinerary]
    last_updated: str

# Multi-day planning: real planner lives in routers/multiday.py

@app.get("/api/itinerary/multi-day/sample",
         summary="Get Sample Multi-Day Itinerary",
         description="Get a sample multi-day itinerary for testing",
         tags=["🧠 Itinerary Optimization"],
         response_model=MultiDayPlanResponse)
async def get_sample_multi_day():
    """Get a sample multi-day itinerary for testing"""
    return MultiDayPlanResponse(
        days=[
            MultiDayItinerary(
                date="2025-10-06",
                items=[
                    MultiDayPOI(
                        name="Dagadusheth Temple",
                        category="temple",
                        arrive_at="10:00",
                        depart_at="10:45",
                        duration_min=45
                    ),
                    MultiDayPOI(
                        name="Shaniwar Wada",
                        category="historic",
                        arrive_at="11:00",
                        depart_at="12:30",
                        duration_min=90
                    )
                ],
                stats={"total_travel_min": 42, "total_duration": 360}
            )
        ],
        last_updated="18:42"
    )

@app.post("/api/chatbot/process-message",
          summary="Process Chatbot Message",
          description="Process chatbot message with context awareness",
          tags=["🏠 Core API"])
async def process_chatbot_message(message: str, user_id: Optional[int] = None):
    """Process chatbot message with context awareness"""
    try:
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["emergency", "help", "sos", "danger"]):
            return {
                "response": "🚨 I detect this might be an emergency. Would you like me to trigger the SOS system?" if SOS_ENABLED else "🚨 I detect an emergency situation. Please contact local emergency services: 112 or 911",
                "intent": "emergency",
                "confidence": 0.95,
                "suggested_actions": ["trigger_sos", "add_emergency_contact"] if SOS_ENABLED else ["contact_local_emergency"]
            }
        elif any(word in message_lower for word in ["weather", "forecast", "rain", "temperature"]):
            return {
                "response": "🌤️ I can provide weather forecasts, travel conditions, and alerts for your destination!" if WEATHER_ENABLED else "Weather service is currently unavailable.",
                "intent": "weather",
                "confidence": 0.90,
                "suggested_actions": ["get_weather", "check_forecast"] if WEATHER_ENABLED else ["try_later"]
            }
        elif any(word in message_lower for word in ["itinerary", "optimize", "plan", "schedule"]):
            return {
                "response": "🧠 I can create a complete optimized itinerary with time scheduling, arrival/departure times, and break planning! Share your destinations." if ALGORITHM_SERVICE_AVAILABLE else "🧠 I can help with basic itinerary planning. Share your destinations." if ITINERARY_ENABLED else "Itinerary service is currently unavailable.",
                "intent": "itinerary",
                "confidence": 0.90,
                "suggested_actions": ["create_complete_itinerary", "optimize_route"] if ITINERARY_ENABLED else ["plan_manually"]
            }
        elif any(word in message_lower for word in ["flight", "airplane", "airline"]):
            return {
                "response": "✈️ I can track flights, check delays, and provide flight updates!" if FLIGHTS_ENABLED else "Flight tracking is currently unavailable.",
                "intent": "flight",
                "confidence": 0.85,
                "suggested_actions": ["track_flight", "check_status"] if FLIGHTS_ENABLED else ["check_airline_website"]
            }
        else:
            available_services = []
            if WEATHER_ENABLED:
                available_services.append("weather forecasting")
            if PLACES_ENABLED:
                available_services.append("places search")
            if EVENTS_ENABLED:
                available_services.append("events discovery")
            if ITINERARY_ENABLED:
                available_services.append("itinerary planning")
            if FLIGHTS_ENABLED:
                available_services.append("flight tracking")
            if SOS_ENABLED:
                available_services.append("SOS emergencies")
            if TRANSLATION_ENABLED:
                available_services.append("translation")
            
            services_text = ", ".join(available_services[:3]) + ("..." if len(available_services) > 3 else "")
            
            return {
                "response": f"Hi! I'm your Live Trip assistant. I can help with {services_text}{'with complete time scheduling' if ALGORITHM_SERVICE_AVAILABLE else ''}. What would you like to do?",
                "intent": "general",
                "confidence": 0.70,
                "suggested_actions": ["get_help", "view_features", "check_weather" if WEATHER_ENABLED else "explore_options"]
            }
    except Exception as e:
        logger.error(f"Error processing chatbot message: {e}")
        return {
            "response": "I'm sorry, I'm having trouble processing your message right now. Please try again.",
            "intent": "error",
            "confidence": 0.0,
            "error": str(e)
        }

# ✅ Run configuration
if __name__ == "__main__":
    # Use reload=False here to avoid import-string requirement in direct invocation
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
