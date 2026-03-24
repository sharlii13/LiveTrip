from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime

from ..schemas.itinerary import RealTimeAlert, WeatherData, TrafficData, FlightData
from .itinerary_routes import itineraries_storage, alerts_storage, get_services

router = APIRouter()

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        # Map itinerary_id to list of websocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Map websocket to itinerary_id for cleanup
        self.connection_to_itinerary: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, itinerary_id: str):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()
        
        if itinerary_id not in self.active_connections:
            self.active_connections[itinerary_id] = []
        
        self.active_connections[itinerary_id].append(websocket)
        self.connection_to_itinerary[websocket] = itinerary_id
        
        # Send initial connection success message
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "itinerary_id": itinerary_id,
            "timestamp": datetime.now().isoformat(),
            "message": "Real-time updates connected successfully"
        }))
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.connection_to_itinerary:
            itinerary_id = self.connection_to_itinerary[websocket]
            
            if itinerary_id in self.active_connections:
                self.active_connections[itinerary_id].remove(websocket)
                
                # Remove empty lists
                if not self.active_connections[itinerary_id]:
                    del self.active_connections[itinerary_id]
            
            del self.connection_to_itinerary[websocket]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_text(message)
        except:
            # Connection might be closed
            self.disconnect(websocket)
    
    async def broadcast_to_itinerary(self, message: str, itinerary_id: str):
        """Send a message to all connections for a specific itinerary"""
        if itinerary_id in self.active_connections:
            disconnected_connections = []
            
            for connection in self.active_connections[itinerary_id]:
                try:
                    await connection.send_text(message)
                except:
                    # Connection is closed, mark for removal
                    disconnected_connections.append(connection)
            
            # Clean up disconnected connections
            for connection in disconnected_connections:
                self.disconnect(connection)
    
    async def broadcast_alert(self, alert: RealTimeAlert):
        """Broadcast an alert to all connections for an itinerary"""
        message = json.dumps({
            "type": "alert",
            "data": alert.dict(),
            "timestamp": datetime.now().isoformat()
        })
        
        await self.broadcast_to_itinerary(message, alert.itinerary_id)
    
    async def broadcast_itinerary_update(self, itinerary_id: str, update_type: str, data: dict):
        """Broadcast an itinerary update"""
        message = json.dumps({
            "type": "itinerary_update",
            "update_type": update_type,
            "itinerary_id": itinerary_id,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        
        await self.broadcast_to_itinerary(message, itinerary_id)


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/itinerary/{itinerary_id}")
async def websocket_endpoint(websocket: WebSocket, itinerary_id: str):
    """WebSocket endpoint for real-time itinerary updates"""
    
    # Verify itinerary exists
    if itinerary_id not in itineraries_storage:
        await websocket.close(code=4004, reason="Itinerary not found")
        return
    
    await manager.connect(websocket, itinerary_id)
    
    try:
        # Send initial data
        itinerary = itineraries_storage[itinerary_id]
        alerts = alerts_storage.get(itinerary_id, [])
        
        # Send current alerts
        if alerts:
            for alert in alerts[-5:]:  # Send last 5 alerts
                await manager.send_personal_message(
                    json.dumps({
                        "type": "alert",
                        "data": alert.dict(),
                        "timestamp": datetime.now().isoformat()
                    }),
                    websocket
                )
        
        # Send current weather if available
        try:
            services = await get_services()
            _, weather_service, maps_service, _, _ = services
            
            # Get location for weather
            location = None
            if itinerary.days and itinerary.days[0].time_slots:
                location = itinerary.days[0].time_slots[0].activity.location
            else:
                location = await maps_service.geocode_address(itinerary.destination)
            
            if location:
                current_weather = await weather_service.get_current_weather(location)
                await manager.send_personal_message(
                    json.dumps({
                        "type": "weather_update",
                        "data": current_weather.dict(),
                        "timestamp": datetime.now().isoformat()
                    }),
                    websocket
                )
        except Exception as e:
            print(f"Error sending initial weather: {e}")
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        }),
                        websocket
                    )
                elif message.get("type") == "request_weather_update":
                    # Send current weather
                    await send_weather_update(itinerary_id, websocket)
                elif message.get("type") == "request_alerts":
                    # Send current alerts
                    current_alerts = alerts_storage.get(itinerary_id, [])
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "alerts_list",
                            "data": [alert.dict() for alert in current_alerts],
                            "timestamp": datetime.now().isoformat()
                        }),
                        websocket
                    )
                elif message.get("type") == "acknowledge_alert":
                    # Mark alert as acknowledged
                    alert_id = message.get("alert_id")
                    if alert_id:
                        current_alerts = alerts_storage.get(itinerary_id, [])
                        for alert in current_alerts:
                            if alert.id == alert_id:
                                alert.acknowledged = True
                                break
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": datetime.now().isoformat()
                    }),
                    websocket
                )
            except Exception as e:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat()
                    }),
                    websocket
                )
    
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


async def send_weather_update(itinerary_id: str, websocket: WebSocket = None):
    """Send weather update to specific websocket or all connections for itinerary"""
    try:
        if itinerary_id not in itineraries_storage:
            return
        
        services = await get_services()
        _, weather_service, maps_service, _, _ = services
        itinerary = itineraries_storage[itinerary_id]
        
        # Get location
        location = None
        if itinerary.days and itinerary.days[0].time_slots:
            location = itinerary.days[0].time_slots[0].activity.location
        else:
            location = await maps_service.geocode_address(itinerary.destination)
        
        if location:
            current_weather = await weather_service.get_current_weather(location)
            message = json.dumps({
                "type": "weather_update",
                "data": current_weather.dict(),
                "timestamp": datetime.now().isoformat()
            })
            
            if websocket:
                await manager.send_personal_message(message, websocket)
            else:
                await manager.broadcast_to_itinerary(message, itinerary_id)
    
    except Exception as e:
        error_message = json.dumps({
            "type": "error",
            "message": f"Failed to get weather update: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })
        
        if websocket:
            await manager.send_personal_message(error_message, websocket)
        else:
            await manager.broadcast_to_itinerary(error_message, itinerary_id)


# Background task for monitoring and sending real-time updates
async def real_time_monitoring_task():
    """Background task to monitor conditions and send updates"""
    while True:
        try:
            # Check each active itinerary for updates
            for itinerary_id in list(manager.active_connections.keys()):
                if itinerary_id in itineraries_storage:
                    await check_and_send_updates(itinerary_id)
            
            # Wait 2 minutes before next check
            await asyncio.sleep(120)
            
        except Exception as e:
            print(f"Error in real-time monitoring: {e}")
            await asyncio.sleep(30)  # Shorter wait on error


async def check_and_send_updates(itinerary_id: str):
    """Check for updates and send notifications for a specific itinerary"""
    try:
        itinerary = itineraries_storage[itinerary_id]
        current_date = datetime.now().date()
        
        # Only check itineraries that are currently active (today or in the future)
        if itinerary.end_date.date() < current_date:
            return
        
        services = await get_services()
        optimizer, weather_service, maps_service, flight_service, _ = services
        
        # Get current location (first activity of today or destination)
        location = None
        for day in itinerary.days:
            if day.date.date() == current_date and day.time_slots:
                location = day.time_slots[0].activity.location
                break
        
        if not location:
            location = await maps_service.geocode_address(itinerary.destination)
        
        if location:
            # Check weather changes
            try:
                current_weather = await weather_service.get_current_weather(location)
                
                # Check if weather conditions have significantly changed
                # (This is a simplified check - in production, you'd store previous weather)
                if current_weather.condition.value in ["rainy", "stormy"]:
                    # Check if there are outdoor activities planned for today
                    for day in itinerary.days:
                        if day.date.date() == current_date:
                            outdoor_activities = [
                                slot for slot in day.time_slots 
                                if slot.activity.weather_dependent and slot.start_time > datetime.now()
                            ]
                            
                            if outdoor_activities:
                                # Send weather alert
                                alert = RealTimeAlert(
                                    id=f"weather_alert_{datetime.now().timestamp()}",
                                    itinerary_id=itinerary_id,
                                    alert_type="weather",
                                    severity="medium",
                                    message=f"Weather alert: {current_weather.condition.value} conditions detected. Consider indoor alternatives.",
                                    suggested_actions=[
                                        "Check indoor alternatives",
                                        "Reschedule outdoor activities",
                                        "Bring appropriate weather gear"
                                    ],
                                    timestamp=datetime.now()
                                )
                                
                                # Store alert
                                if itinerary_id not in alerts_storage:
                                    alerts_storage[itinerary_id] = []
                                alerts_storage[itinerary_id].append(alert)
                                
                                # Broadcast alert
                                await manager.broadcast_alert(alert)
                            break
                
                # Always send weather update
                await send_weather_update(itinerary_id)
                
            except Exception as e:
                print(f"Error checking weather for itinerary {itinerary_id}: {e}")
        
        # Check for traffic updates (simplified)
        # In production, you'd check traffic for upcoming activities
        
        # Send periodic status updates
        await manager.broadcast_itinerary_update(
            itinerary_id,
            "status_update",
            {
                "message": "Itinerary monitoring active",
                "last_check": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        print(f"Error checking updates for itinerary {itinerary_id}: {e}")


# Utility functions to be called from other parts of the application

async def notify_weather_change(itinerary_id: str, weather_data: WeatherData):
    """Notify about weather changes"""
    message = json.dumps({
        "type": "weather_change",
        "data": weather_data.dict(),
        "timestamp": datetime.now().isoformat()
    })
    
    await manager.broadcast_to_itinerary(message, itinerary_id)


async def notify_traffic_update(itinerary_id: str, traffic_data: TrafficData):
    """Notify about traffic updates"""
    message = json.dumps({
        "type": "traffic_update",
        "data": traffic_data.dict(),
        "timestamp": datetime.now().isoformat()
    })
    
    await manager.broadcast_to_itinerary(message, itinerary_id)


async def notify_flight_update(itinerary_id: str, flight_data: FlightData):
    """Notify about flight updates"""
    message = json.dumps({
        "type": "flight_update",
        "data": flight_data.dict(),
        "timestamp": datetime.now().isoformat()
    })
    
    await manager.broadcast_to_itinerary(message, itinerary_id)


async def notify_itinerary_updated(itinerary_id: str):
    """Notify that itinerary has been updated"""
    if itinerary_id in itineraries_storage:
        itinerary = itineraries_storage[itinerary_id]
        message = json.dumps({
            "type": "itinerary_updated",
            "data": {
                "version": itinerary.version,
                "updated_at": itinerary.updated_at.isoformat()
            },
            "timestamp": datetime.now().isoformat()
        })
        
        await manager.broadcast_to_itinerary(message, itinerary_id)


# Export the manager for use in other modules
__all__ = ["manager", "real_time_monitoring_task", "notify_weather_change", 
           "notify_traffic_update", "notify_flight_update", "notify_itinerary_updated"]