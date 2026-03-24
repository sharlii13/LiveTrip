from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from ..schemas.itinerary import (
    Itinerary, CreateItineraryRequest, UpdatePreferencesRequest,
    RealTimeAlert, ItineraryUpdate, Activity, Location, UserPreferences,
    WeatherData, TrafficData, FlightData
)
from ..core.itinerary_optimizer import ItineraryOptimizer
from ..services.weather_service import WeatherService
from ..services.maps_service import MapsService
from ..services.flight_service import FlightService
from ..services.events_service import EventsService

# Global storage for itineraries (in production, use a database)
itineraries_storage: Dict[str, Itinerary] = {}
alerts_storage: Dict[str, List[RealTimeAlert]] = {}

router = APIRouter(prefix="/api/itinerary", tags=["itinerary"])

# Dependency injection for services
async def get_services():
    # In production, these would be properly configured with API keys
    weather_service = WeatherService("a600ed96feeead9ded6fa7c54ab0811e")
    maps_service = MapsService("AIzaSyBVY85Q1NN2FaXMH-GiIyGVNEnFcYKol1I")
    flight_service = FlightService("d021025aed18cf0d44575b63a855baea")
    events_service = EventsService("6ZTMHZNQ7FOXLISWMTQH")
    
    optimizer = ItineraryOptimizer(weather_service, maps_service, flight_service, events_service)
    return optimizer, weather_service, maps_service, flight_service, events_service


@router.post("/create", response_model=Itinerary)
async def create_itinerary(
    request: CreateItineraryRequest,
    services = Depends(get_services)
):
    """Create a new optimized itinerary"""
    try:
        optimizer, weather_service, maps_service, flight_service, events_service = services
        
        # Get destination location
        destination_location = await maps_service.geocode_address(request.destination)
        if not destination_location:
            raise HTTPException(status_code=400, detail="Invalid destination")
        
        # Find activities near destination
        activities = []
        
        # Get places of interest
        places = await maps_service.find_nearby_places(
            destination_location, "tourist_attraction", radius=15000
        )
        
        for place in places[:20]:  # Limit to 20 places
            place_details = await maps_service.get_place_details(place["place_id"])
            if place_details and place_details.get("result"):
                result = place_details["result"]
                geometry = result.get("geometry", {}).get("location", {})
                
                activity_location = Location(
                    latitude=geometry.get("lat", destination_location.latitude),
                    longitude=geometry.get("lng", destination_location.longitude),
                    address=result.get("formatted_address", ""),
                    city=destination_location.city,
                    country=destination_location.country
                )
                
                activity = Activity(
                    id=f"place_{place['place_id']}",
                    name=result.get("name", "Unknown Place"),
                    description=result.get("editorial_summary", {}).get("overview", ""),
                    location=activity_location,
                    activity_type="sightseeing",
                    estimated_duration=120,  # Default 2 hours
                    cost=None,
                    rating=result.get("rating"),
                    weather_dependent=place.get("types", []) and any(
                        t in place["types"] for t in ["park", "tourist_attraction"]
                    ),
                    opening_hours=result.get("opening_hours", {}).get("weekday_text"),
                    booking_required=False
                )
                activities.append(activity)
        
        # Get events from EventBrite
        event_activities = await events_service.get_events_for_itinerary(
            destination_location, request.start_date, request.end_date, 
            request.user_preferences.dict()
        )
        activities.extend(event_activities[:10])  # Limit to 10 events
        
        # Create optimized itinerary
        itinerary = await optimizer.create_optimal_itinerary(
            activities, request.user_preferences, request.start_date, 
            request.end_date, request.flight_details
        )
        
        # Set user ID
        itinerary.user_id = request.user_id
        
        # Store itinerary
        itineraries_storage[itinerary.id] = itinerary
        alerts_storage[itinerary.id] = []
        
        return itinerary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create itinerary: {str(e)}")


@router.get("/{itinerary_id}", response_model=Itinerary)
async def get_itinerary(itinerary_id: str):
    """Get itinerary by ID"""
    if itinerary_id not in itineraries_storage:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    return itineraries_storage[itinerary_id]


@router.get("/user/{user_id}", response_model=List[Itinerary])
async def get_user_itineraries(user_id: str):
    """Get all itineraries for a user"""
    user_itineraries = [
        itinerary for itinerary in itineraries_storage.values()
        if itinerary.user_id == user_id
    ]
    return user_itineraries


@router.put("/{itinerary_id}/preferences")
async def update_preferences(
    itinerary_id: str,
    request: UpdatePreferencesRequest,
    services = Depends(get_services)
):
    """Update user preferences and re-optimize itinerary"""
    if itinerary_id not in itineraries_storage:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    try:
        optimizer, _, _, _, _ = services
        itinerary = itineraries_storage[itinerary_id]
        
        # Update preferences
        for key, value in request.preferences.items():
            if hasattr(itinerary.user_preferences, key):
                setattr(itinerary.user_preferences, key, value)
        
        if request.apply_immediately:
            # Re-optimize itinerary with new preferences
            # For now, just update the preferences
            itinerary.updated_at = datetime.now()
            itinerary.version += 1
            
            # Create alert for preference update
            alert = RealTimeAlert(
                id=f"pref_update_{datetime.now().timestamp()}",
                itinerary_id=itinerary_id,
                alert_type="suggestion",
                severity="low",
                message="Preferences updated. Itinerary has been adjusted accordingly.",
                suggested_actions=["Review updated itinerary"],
                timestamp=datetime.now()
            )
            
            if itinerary_id not in alerts_storage:
                alerts_storage[itinerary_id] = []
            alerts_storage[itinerary_id].append(alert)
        
        return {"message": "Preferences updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")


@router.get("/{itinerary_id}/alerts", response_model=List[RealTimeAlert])
async def get_alerts(itinerary_id: str):
    """Get all alerts for an itinerary"""
    if itinerary_id not in itineraries_storage:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    return alerts_storage.get(itinerary_id, [])


@router.post("/{itinerary_id}/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(itinerary_id: str, alert_id: str):
    """Mark an alert as acknowledged"""
    if itinerary_id not in itineraries_storage:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    alerts = alerts_storage.get(itinerary_id, [])
    for alert in alerts:
        if alert.id == alert_id:
            alert.acknowledged = True
            return {"message": "Alert acknowledged"}
    
    raise HTTPException(status_code=404, detail="Alert not found")


@router.post("/{itinerary_id}/weather-update")
async def handle_weather_update(
    itinerary_id: str,
    weather_data: WeatherData,
    background_tasks: BackgroundTasks,
    services = Depends(get_services)
):
    """Handle weather update and adapt itinerary"""
    if itinerary_id not in itineraries_storage:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    try:
        optimizer, _, _, _, _ = services
        itinerary = itineraries_storage[itinerary_id]
        
        # Adapt itinerary to weather change
        updated_itinerary, new_alerts = await optimizer.adapt_to_weather_change(
            itinerary, weather_data
        )
        
        # Update stored itinerary
        itineraries_storage[itinerary_id] = updated_itinerary
        
        # Add new alerts
        if itinerary_id not in alerts_storage:
            alerts_storage[itinerary_id] = []
        alerts_storage[itinerary_id].extend(new_alerts)
        
        return {
            "message": "Itinerary updated for weather change",
            "alerts_count": len(new_alerts),
            "version": updated_itinerary.version
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to handle weather update: {str(e)}")


@router.post("/{itinerary_id}/traffic-update")
async def handle_traffic_update(
    itinerary_id: str,
    traffic_data: TrafficData,
    background_tasks: BackgroundTasks,
    services = Depends(get_services)
):
    """Handle traffic update and adapt itinerary"""
    if itinerary_id not in itineraries_storage:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    try:
        optimizer, _, _, _, _ = services
        itinerary = itineraries_storage[itinerary_id]
        
        # Adapt itinerary to traffic delay
        updated_itinerary, new_alerts = await optimizer.adapt_to_traffic_delay(
            itinerary, traffic_data
        )
        
        # Update stored itinerary
        itineraries_storage[itinerary_id] = updated_itinerary
        
        # Add new alerts
        if itinerary_id not in alerts_storage:
            alerts_storage[itinerary_id] = []
        alerts_storage[itinerary_id].extend(new_alerts)
        
        return {
            "message": "Itinerary updated for traffic delay",
            "alerts_count": len(new_alerts),
            "version": updated_itinerary.version
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to handle traffic update: {str(e)}")


@router.post("/{itinerary_id}/flight-update")
async def handle_flight_update(
    itinerary_id: str,
    flight_data: FlightData,
    background_tasks: BackgroundTasks,
    services = Depends(get_services)
):
    """Handle flight update and adapt itinerary"""
    if itinerary_id not in itineraries_storage:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    try:
        optimizer, _, _, _, _ = services
        itinerary = itineraries_storage[itinerary_id]
        
        # Adapt itinerary to flight delay
        updated_itinerary, new_alerts = await optimizer.adapt_to_flight_delay(
            itinerary, flight_data
        )
        
        # Update stored itinerary
        itineraries_storage[itinerary_id] = updated_itinerary
        
        # Add new alerts
        if itinerary_id not in alerts_storage:
            alerts_storage[itinerary_id] = []
        alerts_storage[itinerary_id].extend(new_alerts)
        
        return {
            "message": "Itinerary updated for flight change",
            "alerts_count": len(new_alerts),
            "version": updated_itinerary.version
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to handle flight update: {str(e)}")


@router.get("/{itinerary_id}/current-weather")
async def get_current_weather(
    itinerary_id: str,
    services = Depends(get_services)
):
    """Get current weather for itinerary destination"""
    if itinerary_id not in itineraries_storage:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    try:
        _, weather_service, _, _, _ = services
        itinerary = itineraries_storage[itinerary_id]
        
        # Get location from first activity or use destination
        location = None
        if itinerary.days and itinerary.days[0].time_slots:
            location = itinerary.days[0].time_slots[0].activity.location
        else:
            # Geocode destination
            _, maps_service, _, _, _ = services
            location = await maps_service.geocode_address(itinerary.destination)
        
        if not location:
            raise HTTPException(status_code=400, detail="Cannot determine location")
        
        weather = await weather_service.get_current_weather(location)
        return weather
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get weather: {str(e)}")


@router.get("/{itinerary_id}/route-optimization")
async def optimize_route(
    itinerary_id: str,
    day_index: int = 0,
    services = Depends(get_services)
):
    """Optimize route for a specific day"""
    if itinerary_id not in itineraries_storage:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    try:
        _, _, maps_service, _, _ = services
        itinerary = itineraries_storage[itinerary_id]
        
        if day_index >= len(itinerary.days):
            raise HTTPException(status_code=400, detail="Invalid day index")
        
        day = itinerary.days[day_index]
        locations = [slot.activity.location for slot in day.time_slots]
        
        if len(locations) > 1:
            optimized_locations = await maps_service.get_optimal_route(locations)
            
            # Reorder time slots based on optimized route
            location_to_slot = {
                (slot.activity.location.latitude, slot.activity.location.longitude): slot 
                for slot in day.time_slots
            }
            
            optimized_slots = []
            for location in optimized_locations:
                key = (location.latitude, location.longitude)
                if key in location_to_slot:
                    optimized_slots.append(location_to_slot[key])
            
            # Update time slots with new order
            current_time = day.date.replace(hour=9, minute=0, second=0)
            for slot in optimized_slots:
                slot.start_time = current_time
                slot.end_time = current_time + datetime.timedelta(minutes=slot.activity.estimated_duration)
                current_time = slot.end_time + datetime.timedelta(minutes=15)  # Buffer
            
            day.time_slots = optimized_slots
            itinerary.updated_at = datetime.now()
            itinerary.version += 1
            
            itineraries_storage[itinerary_id] = itinerary
        
        return {
            "message": "Route optimized successfully",
            "day_index": day_index,
            "activities_count": len(day.time_slots)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to optimize route: {str(e)}")


@router.delete("/{itinerary_id}")
async def delete_itinerary(itinerary_id: str):
    """Delete an itinerary"""
    if itinerary_id not in itineraries_storage:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    del itineraries_storage[itinerary_id]
    if itinerary_id in alerts_storage:
        del alerts_storage[itinerary_id]
    
    return {"message": "Itinerary deleted successfully"}


@router.get("/{itinerary_id}/export")
async def export_itinerary(itinerary_id: str, format: str = "json"):
    """Export itinerary in different formats"""
    if itinerary_id not in itineraries_storage:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    itinerary = itineraries_storage[itinerary_id]
    
    if format.lower() == "json":
        return itinerary
    elif format.lower() == "summary":
        # Return a summary format
        summary = {
            "destination": itinerary.destination,
            "dates": f"{itinerary.start_date.date()} to {itinerary.end_date.date()}",
            "total_budget": itinerary.total_budget,
            "days_count": len(itinerary.days),
            "activities": []
        }
        
        for day in itinerary.days:
            day_activities = []
            for slot in day.time_slots:
                day_activities.append({
                    "name": slot.activity.name,
                    "time": f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}",
                    "location": slot.activity.location.address,
                    "cost": slot.activity.cost
                })
            summary["activities"].append({
                "date": day.date.date().isoformat(),
                "activities": day_activities
            })
        
        return summary
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")


# Background task for monitoring real-time updates
async def monitor_itinerary_updates():
    """Background task to monitor and update itineraries"""
    while True:
        try:
            for itinerary_id, itinerary in itineraries_storage.items():
                # Check for weather updates
                # Check for traffic updates  
                # Check for flight updates
                # This would be implemented with proper monitoring logic
                pass
            
            await asyncio.sleep(300)  # Check every 5 minutes
        except Exception as e:
            print(f"Error in monitoring task: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying