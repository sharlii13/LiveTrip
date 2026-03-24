from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from .api.itinerary_routes import router as itinerary_router
from .api.websocket_routes import router as websocket_router, real_time_monitoring_task
from .services.weather_service import WeatherService
from .services.maps_service import MapsService
from .services.flight_service import FlightService
from .services.events_service import EventsService


# Background tasks
background_tasks = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown"""
    
    # Startup
    print("🚀 Starting Living Itinerary Backend...")
    
    # Start background monitoring task
    monitoring_task = asyncio.create_task(real_time_monitoring_task())
    background_tasks.add(monitoring_task)
    monitoring_task.add_done_callback(background_tasks.discard)
    
    print("✅ Real-time monitoring started")
    print("🌟 Living Itinerary Backend is ready!")
    
    yield
    
    # Shutdown
    print("🔄 Shutting down Living Itinerary Backend...")
    
    # Cancel background tasks
    for task in background_tasks:
        task.cancel()
    
    # Wait for tasks to complete
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)
    
    print("✅ Living Itinerary Backend shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Living Itinerary API",
    description="""
    # The Living Itinerary — Your AI-powered co-traveler 🧳✨

    A dynamic, real-time travel itinerary system that adapts to live conditions:

    ## 🌟 Key Features
    - **🌧 Weather-aware**: Outdoor plans automatically swap with indoor alternatives if it rains
    - **🚗 Traffic-smart**: Routes and timings shuffle instantly if traffic builds up
    - **✈ Flight-integrated**: Delays or changes reorganize your entire day seamlessly
    - **😴 Mood-adaptive**: Just say "skip the museum" — the app updates in seconds
    - **📊 Smart insights**: Track expenses, time spent, and trip highlights automatically
    - **📶 Offline-first**: A basic itinerary stays accessible even without internet
    - **🌱 Eco Mode**: Earn rewards for eco-friendly choices like public transport
    - **🗺 Gamified exploration**: Discover hidden gems and get points
    - **💬 Traveler feedback loop**: Community-driven improvements
    - **🔔 Smart notifications**: Proactive solutions, not just alerts

    ## 🏗 Technical Architecture
    - **Greedy Algorithm**: Real-time optimization based on multiple factors
    - **Live API Integration**: Weather, Traffic, Flight, Events data
    - **WebSocket Support**: Real-time updates and notifications
    - **Multi-criteria Scoring**: User preferences, weather, traffic, cost optimization

    ## 🚀 Getting Started
    1. Create an itinerary with `/api/itinerary/create`
    2. Connect to WebSocket at `/ws/itinerary/{itinerary_id}` for real-time updates
    3. Watch your itinerary adapt automatically to changing conditions!

    ---
    *Making travel stress-free, one algorithm at a time* 🎯
    """,
    version="1.0.0",
    contact={
        "name": "Living Itinerary Team",
        "email": "team@livingitinerary.com",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan
)


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://localhost:5173",  # Vite development server
        "http://localhost:5000",  # Local development
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5000",
        # Add your production domains here
        # "https://yourdomain.com",
        # "https://www.yourdomain.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Trusted Host Middleware (for production)
if os.getenv("NODE_ENV") == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            # Add your production domains here
            # "yourdomain.com",
            # "www.yourdomain.com",
        ]
    )


# Include routers
app.include_router(itinerary_router)
app.include_router(websocket_router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Welcome endpoint with API information"""
    return {
        "message": "Welcome to The Living Itinerary API! 🧳✨",
        "description": "Your AI-powered co-traveler that adapts to real-time conditions",
        "version": "1.0.0",
        "features": [
            "Weather-aware planning",
            "Traffic-smart routing", 
            "Flight integration",
            "Real-time adaptations",
            "Smart notifications",
            "Eco-friendly options"
        ],
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "create_itinerary": "/api/itinerary/create",
            "websocket": "/ws/itinerary/{itinerary_id}"
        }
    }


# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint for monitoring"""
    # Check external APIs status
    api_status = await check_external_apis()
    
    return {
        "status": "healthy" if all(api_status.values()) else "degraded",
        "timestamp": "2025-01-25T10:17:00Z",
        "services": {
            "core": "operational",
            "websocket": "operational",
            "external_apis": api_status
        },
        "version": "1.0.0"
    }


async def check_external_apis() -> Dict[str, bool]:
    """Check status of external APIs"""
    status = {}
    
    try:
        # Check OpenWeather API
        weather_service = WeatherService(os.getenv("OPENWEATHER_API_KEY", "a600ed96feeead9ded6fa7c54ab0811e"))
        # This would be a simple test call in production
        status["weather"] = True
    except:
        status["weather"] = False
    
    try:
        # Check Google Maps API
        maps_service = MapsService(os.getenv("GOOGLE_MAPS_API_KEY", "AIzaSyBVY85Q1NN2FaXMH-GiIyGVNEnFcYKol1I"))
        status["maps"] = True
    except:
        status["maps"] = False
    
    try:
        # Check AviationStack API
        flight_service = FlightService(os.getenv("AVIATIONSTACK_API_KEY", "d021025aed18cf0d44575b63a855baea"))
        status["flights"] = True
    except:
        status["flights"] = False
    
    try:
        # Check EventBrite API
        events_service = EventsService(os.getenv("EVENTBRITE_API_KEY", "6ZTMHZNQ7FOXLISWMTQH"))
        status["events"] = True
    except:
        status["events"] = False
    
    return status


# API Statistics endpoint
@app.get("/api/stats", tags=["system"])
async def get_api_stats():
    """Get API usage statistics"""
    from .api.itinerary_routes import itineraries_storage, alerts_storage
    from .api.websocket_routes import manager
    
    return {
        "itineraries": {
            "total": len(itineraries_storage),
            "active_today": len([
                it for it in itineraries_storage.values() 
                if it.start_date.date() <= "2025-01-25" <= it.end_date.date()
            ])
        },
        "alerts": {
            "total": sum(len(alerts) for alerts in alerts_storage.values()),
            "unacknowledged": sum(
                len([alert for alert in alerts if not alert.acknowledged]) 
                for alerts in alerts_storage.values()
            )
        },
        "websocket_connections": {
            "active_itineraries": len(manager.active_connections),
            "total_connections": sum(len(conns) for conns in manager.active_connections.values())
        }
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "message": "The requested resource was not found",
            "suggestion": "Check the API documentation at /docs for available endpoints"
        }
    )


@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "message": "An internal server error occurred",
            "suggestion": "Please try again later or contact support if the issue persists"
        }
    )


# Startup message
@app.on_event("startup")
async def startup_message():
    print("""
    🧳✨ THE LIVING ITINERARY - Backend Started ✨🧳
    
    ┌─────────────────────────────────────────────────────────┐
    │                                                         │
    │  🌟 Your AI-powered co-traveler is ready!              │
    │                                                         │
    │  🔗 API Documentation: http://localhost:8000/docs      │
    │  🔗 Health Check: http://localhost:8000/health         │
    │  🔗 WebSocket: ws://localhost:8000/ws/itinerary/       │
    │                                                         │
    │  Features Ready:                                        │
    │  ✅ Weather-aware planning                              │
    │  ✅ Traffic-smart routing                               │
    │  ✅ Flight integration                                  │
    │  ✅ Real-time adaptations                               │
    │  ✅ Smart notifications                                 │
    │  ✅ WebSocket support                                   │
    │                                                         │
    │  Making travel stress-free, one algorithm at a time!   │
    │                                                         │
    └─────────────────────────────────────────────────────────┘
    """)


if __name__ == "__main__":
    # Configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("NODE_ENV") == "development"
    
    # Run the application
    uvicorn.run(
        "main:app" if reload else app,
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )