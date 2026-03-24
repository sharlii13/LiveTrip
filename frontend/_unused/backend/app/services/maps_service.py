import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from ..schemas.itinerary import TrafficData, TrafficLevel, Location
import json


class MapsService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    def _determine_traffic_level(self, current_duration: int, typical_duration: int) -> TrafficLevel:
        """Determine traffic level based on duration comparison"""
        if current_duration <= typical_duration * 1.1:
            return TrafficLevel.LOW
        elif current_duration <= typical_duration * 1.3:
            return TrafficLevel.MEDIUM
        elif current_duration <= typical_duration * 1.6:
            return TrafficLevel.HIGH
        else:
            return TrafficLevel.SEVERE

    async def get_directions(self, origin: Location, destination: Location, 
                            mode: str = "driving", departure_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get directions between two locations"""
        session = await self._get_session()
        
        params = {
            "origin": f"{origin.latitude},{origin.longitude}",
            "destination": f"{destination.latitude},{destination.longitude}",
            "mode": mode,
            "key": self.api_key,
            "traffic_model": "best_guess",
            "units": "metric"
        }
        
        if departure_time:
            params["departure_time"] = int(departure_time.timestamp())
        else:
            params["departure_time"] = "now"

        async with session.get(f"{self.base_url}/directions/json", params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Directions API error: {response.status}")

    async def get_traffic_data(self, origin: Location, destination: Location) -> TrafficData:
        """Get current traffic data between two locations"""
        directions = await self.get_directions(origin, destination)
        
        if directions["status"] == "OK" and directions["routes"]:
            route = directions["routes"][0]
            leg = route["legs"][0]
            
            current_duration = leg["duration_in_traffic"]["value"] // 60 if "duration_in_traffic" in leg else leg["duration"]["value"] // 60
            typical_duration = leg["duration"]["value"] // 60
            
            # Get alternative routes
            alternative_routes = []
            for i, alt_route in enumerate(directions["routes"][1:3]):  # Get up to 2 alternatives
                alt_leg = alt_route["legs"][0]
                alt_duration = alt_leg["duration_in_traffic"]["value"] // 60 if "duration_in_traffic" in alt_leg else alt_leg["duration"]["value"] // 60
                
                alternative_routes.append({
                    "route_index": i + 1,
                    "duration_minutes": alt_duration,
                    "distance_km": alt_leg["distance"]["value"] / 1000,
                    "summary": alt_route.get("summary", f"Alternative route {i + 1}")
                })
            
            return TrafficData(
                route=f"{origin.address} to {destination.address}",
                current_duration=current_duration,
                typical_duration=typical_duration,
                traffic_level=self._determine_traffic_level(current_duration, typical_duration),
                alternative_routes=alternative_routes,
                timestamp=datetime.now()
            )
        else:
            raise Exception(f"No route found: {directions.get('status', 'Unknown error')}")

    async def get_distance_matrix(self, origins: List[Location], destinations: List[Location]) -> Dict[str, Any]:
        """Get distance and time matrix for multiple origins and destinations"""
        session = await self._get_session()
        
        origins_str = "|".join([f"{loc.latitude},{loc.longitude}" for loc in origins])
        destinations_str = "|".join([f"{loc.latitude},{loc.longitude}" for loc in destinations])
        
        params = {
            "origins": origins_str,
            "destinations": destinations_str,
            "mode": "driving",
            "traffic_model": "best_guess",
            "departure_time": "now",
            "key": self.api_key,
            "units": "metric"
        }

        async with session.get(f"{self.base_url}/distancematrix/json", params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Distance Matrix API error: {response.status}")

    async def find_nearby_places(self, location: Location, place_type: str, radius: int = 5000) -> List[Dict[str, Any]]:
        """Find nearby places of interest"""
        session = await self._get_session()
        
        params = {
            "location": f"{location.latitude},{location.longitude}",
            "radius": radius,
            "type": place_type,
            "key": self.api_key
        }

        async with session.get(f"{self.base_url}/place/nearbysearch/json", params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("results", [])
            else:
                raise Exception(f"Places API error: {response.status}")

    async def get_place_details(self, place_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific place"""
        session = await self._get_session()
        
        params = {
            "place_id": place_id,
            "fields": "name,rating,formatted_address,geometry,opening_hours,price_level,photos,reviews,formatted_phone_number,website",
            "key": self.api_key
        }

        async with session.get(f"{self.base_url}/place/details/json", params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Place Details API error: {response.status}")

    async def search_places(self, query: str, location: Location, radius: int = 10000) -> List[Dict[str, Any]]:
        """Search for places by text query"""
        session = await self._get_session()
        
        params = {
            "query": query,
            "location": f"{location.latitude},{location.longitude}",
            "radius": radius,
            "key": self.api_key
        }

        async with session.get(f"{self.base_url}/place/textsearch/json", params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("results", [])
            else:
                raise Exception(f"Text Search API error: {response.status}")

    async def geocode_address(self, address: str) -> Optional[Location]:
        """Convert address to coordinates"""
        session = await self._get_session()
        
        params = {
            "address": address,
            "key": self.api_key
        }

        async with session.get(f"{self.base_url}/geocode/json", params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data["status"] == "OK" and data["results"]:
                    result = data["results"][0]
                    geometry = result["geometry"]["location"]
                    
                    return Location(
                        latitude=geometry["lat"],
                        longitude=geometry["lng"],
                        address=result["formatted_address"],
                        city=self._extract_city(result["address_components"]),
                        country=self._extract_country(result["address_components"])
                    )
            return None

    async def reverse_geocode(self, location: Location) -> Optional[str]:
        """Convert coordinates to address"""
        session = await self._get_session()
        
        params = {
            "latlng": f"{location.latitude},{location.longitude}",
            "key": self.api_key
        }

        async with session.get(f"{self.base_url}/geocode/json", params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data["status"] == "OK" and data["results"]:
                    return data["results"][0]["formatted_address"]
            return None

    def _extract_city(self, address_components: List[Dict[str, Any]]) -> str:
        """Extract city from address components"""
        for component in address_components:
            if "locality" in component["types"]:
                return component["long_name"]
            elif "administrative_area_level_2" in component["types"]:
                return component["long_name"]
        return "Unknown"

    def _extract_country(self, address_components: List[Dict[str, Any]]) -> str:
        """Extract country from address components"""
        for component in address_components:
            if "country" in component["types"]:
                return component["long_name"]
        return "Unknown"

    async def get_optimal_route(self, locations: List[Location], start_location: Optional[Location] = None) -> List[Location]:
        """Get optimal route visiting all locations (Traveling Salesman Problem approximation)"""
        if not locations:
            return []
        
        if len(locations) == 1:
            return locations
        
        # For small number of locations, use brute force
        if len(locations) <= 8:
            return await self._solve_tsp_brute_force(locations, start_location)
        
        # For larger sets, use nearest neighbor heuristic
        return await self._solve_tsp_nearest_neighbor(locations, start_location)

    async def _solve_tsp_nearest_neighbor(self, locations: List[Location], start_location: Optional[Location] = None) -> List[Location]:
        """Solve TSP using nearest neighbor heuristic"""
        if start_location:
            current = start_location
            unvisited = locations.copy()
        else:
            current = locations[0]
            unvisited = locations[1:]
        
        route = [current]
        
        while unvisited:
            # Get distance matrix for current location to all unvisited
            distances = await self.get_distance_matrix([current], unvisited)
            
            if distances["status"] != "OK":
                # Fallback: add remaining locations in original order
                route.extend(unvisited)
                break
            
            # Find nearest unvisited location
            min_distance = float('inf')
            nearest_index = 0
            
            for i, element in enumerate(distances["rows"][0]["elements"]):
                if element["status"] == "OK":
                    distance = element["distance"]["value"]
                    if distance < min_distance:
                        min_distance = distance
                        nearest_index = i
            
            # Move to nearest location
            current = unvisited.pop(nearest_index)
            route.append(current)
        
        return route

    async def _solve_tsp_brute_force(self, locations: List[Location], start_location: Optional[Location] = None) -> List[Location]:
        """Solve TSP using brute force for small sets"""
        from itertools import permutations
        
        if start_location and start_location not in locations:
            all_locations = [start_location] + locations
        else:
            all_locations = locations
        
        if len(all_locations) <= 1:
            return all_locations
        
        # Get distance matrix for all locations
        distance_matrix = await self.get_distance_matrix(all_locations, all_locations)
        
        if distance_matrix["status"] != "OK":
            return all_locations
        
        # Build distance lookup
        distances = {}
        for i, row in enumerate(distance_matrix["rows"]):
            for j, element in enumerate(row["elements"]):
                if element["status"] == "OK":
                    distances[(i, j)] = element["distance"]["value"]
                else:
                    distances[(i, j)] = float('inf')
        
        # Find best permutation
        if start_location and start_location in all_locations:
            start_idx = all_locations.index(start_location)
            other_indices = [i for i in range(len(all_locations)) if i != start_idx]
            
            best_distance = float('inf')
            best_route = all_locations
            
            for perm in permutations(other_indices):
                route_indices = [start_idx] + list(perm)
                total_distance = sum(distances.get((route_indices[i], route_indices[i+1]), float('inf')) 
                                   for i in range(len(route_indices) - 1))
                
                if total_distance < best_distance:
                    best_distance = total_distance
                    best_route = [all_locations[i] for i in route_indices]
            
            return best_route
        else:
            # No fixed start location
            best_distance = float('inf')
            best_route = all_locations
            
            for perm in permutations(range(len(all_locations))):
                total_distance = sum(distances.get((perm[i], perm[i+1]), float('inf')) 
                                   for i in range(len(perm) - 1))
                
                if total_distance < best_distance:
                    best_distance = total_distance
                    best_route = [all_locations[i] for i in perm]
            
            return best_route

    async def check_traffic_incidents(self, location: Location, radius: int = 10000) -> List[Dict[str, Any]]:
        """Check for traffic incidents in the area (this would require additional APIs)"""
        # Note: Google Maps API doesn't directly provide traffic incidents
        # This would need to be implemented with traffic APIs or news APIs
        # For now, return empty list
        return []