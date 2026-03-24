"""
Main FastAPI application for the Travel Itinerary Planning API.
Production-grade hybrid system combining greedy POI selection with OR-Tools optimization.
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from dotenv import load_dotenv

from app.api import itinerary_routes, places_routes


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting Travel Itinerary Planning API")
    
    try:
        logger.info("Live-only mode: skipping any sample cache seeding")
    except Exception as e:
        logger.warning(f"Startup note: {e}")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Travel Itinerary Planning API")


# Create FastAPI application
app = FastAPI(
    title="Travel Itinerary Planning API",
    description="""
    A production-grade hybrid itinerary planning system that creates optimal one-day travel itineraries.
    
    ## Features
    
    * **Greedy POI Selection**: Intelligent scoring algorithm considering ratings, reviews, weather compatibility, travel penalties, and category diversity
    * **Route Optimization**: Google OR-Tools VRPTW solver for optimal visit ordering with time windows  
    * **Async Architecture**: Built with FastAPI for high-performance async operations
    * **Caching System**: Lightweight JSON caching for POIs and distance matrices
    * **Modular Design**: Extensible architecture ready for multi-day planning expansion
    
    ## Algorithm
    
    The system uses a two-step approach:
    
    1. **POI Selection**: Greedy algorithm with weighted scoring:
       ```
       score = w1*rating + w2*log(1 + reviews) + w3*weather_match - w4*travel_penalty - w5*category_repetition
       ```
    
    2. **Route Optimization**: OR-Tools VRPTW solver minimizes travel time while respecting:
       - POI opening/closing hours
       - Visit durations by category
       - Transportation mode constraints
       - Day start/end times
    
    ## Usage
    
    Send a POST request to `/api/itinerary/plan-one-day` with your preferences and get back an optimized itinerary with precise arrival/departure times and travel statistics.
    """,
    version="1.0.0",
    contact={
        "name": "Travel Planning API Team",
        "email": "contact@travelplanning.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(itinerary_routes.router)
app.include_router(places_routes.router)
app.include_router(places_routes.root_router)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to documentation."""
    return RedirectResponse(url="/docs")


@app.get("/places/search",
         summary="Search Places (live only)",
         description="This endpoint no longer serves mock data. Use /api/itinerary/places/search for live Google Places results.")
async def search_places(query: str, limit: int = 8) -> Dict[str, Any]:
    """
    Deprecated mock endpoint: live data only.
    """
    raise HTTPException(
        status_code=503,
        detail="Mock search is disabled. Use /api/itinerary/places/search with a valid API key for live data."
    )


@app.get("/info", 
         summary="API Information",
         description="Get API version and configuration information.")
async def get_info() -> Dict[str, Any]:
    """
    Get API information including version, configuration, and system details.
    
    Returns:
        Dictionary with API information
    """
    return {
        "name": "Travel Itinerary Planning API",
        "version": "1.0.0",
        "description": "Production-grade hybrid itinerary planning system",
        "features": [
            "Greedy POI Selection",
            "OR-Tools Route Optimization", 
            "Async Architecture",
            "JSON Caching",
            "Time Window Constraints",
            "Multi-category Support"
        ],
        "algorithms": {
            "poi_selection": "Greedy scoring with weighted factors",
            "route_optimization": "OR-Tools VRPTW (Vehicle Routing Problem with Time Windows)"
        },
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug": os.getenv("DEBUG", "False").lower() == "true"
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom exception handler for HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path
        }
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not found",
            "message": f"The requested path '{request.url.path}' was not found",
            "available_endpoints": [
                "/docs - API Documentation",
                "/api/itinerary/plan-one-day - Main planning endpoint",
                "/api/itinerary/health - Health check",
                "/info - API information"
            ],
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler."""
    logger.error(f"Internal server error on {request.url.path}: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": str(id(request)),  # Simple request ID for debugging
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Custom exception handler for general exceptions."""
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred while processing your request",
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path
        }
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for monitoring and debugging."""
    logger.info(f"{request.method} {request.url.path} - {request.client.host if request.client else 'unknown'}")
    
    response = await call_next(request)
    
    logger.info(f"{request.method} {request.url.path} - {response.status_code}")
    return response


if __name__ == "__main__":
    import uvicorn
    
    # Configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port} (debug={debug})")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )