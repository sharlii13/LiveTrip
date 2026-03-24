"""
Route optimizer using Google OR-Tools VRPTW (Vehicle Routing Problem with Time Windows).
Optimizes the visit order of selected POIs to minimize travel time while respecting time constraints.
"""
import logging
import time
from typing import List, Dict, Optional, Tuple

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from app.models.schemas import (
    ScoredPOI, DayPlan, POI, ItineraryStats, OptimizationConfig,
    DistanceMatrix, PlanRequest, get_category_duration,
    time_str_to_minutes, minutes_to_time_str
)
from app.utils.mock_data import get_mock_distance_matrix
from app.utils.cache_utils import get_cached_distance_matrix, cache_distance_matrix


logger = logging.getLogger(__name__)


class RouteOptimizer:
    """OR-Tools based route optimization for itinerary planning."""
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        """
        Initialize the optimizer with configuration.
        
        Args:
            config: Optimization configuration
        """
        self.config = config
    
    async def get_distance_matrix(self, locations: List[Dict[str, float]], 
                                 mode: str = "driving") -> DistanceMatrix:
        """
        Get or compute distance matrix for the given locations.
        
        Args:
            locations: List of {lat, lng} location dictionaries
            mode: Transportation mode
            
        Returns:
            DistanceMatrix with travel times and distances
        """
        # Try to get from cache first
        cached_matrix = await get_cached_distance_matrix(locations, mode)
        if cached_matrix:
            logger.info(f"Using cached distance matrix for {len(locations)} locations")
            if isinstance(cached_matrix, dict):
                return DistanceMatrix(**cached_matrix)
            return cached_matrix
        
        # Prefer real-time Google Distance Matrix API
        try:
            from app.services.google_distance import get_distance_service, TravelMode
            distance_service = await get_distance_service()
            
            # Build origins/destinations as tuples in the same order
            coords = [(loc["lat"], loc["lng"]) for loc in locations]
            result = await distance_service.get_distance_matrix(
                origins=coords,
                destinations=coords,
                mode=TravelMode(mode)
            )
            
            # Convert durations (seconds) to minutes for our DistanceMatrix
            durations_min: list[list[int]] = []
            distances_m: list[list[int]] = []
            for i in range(len(coords)):
                row_durations = []
                row_distances = []
                for j in range(len(coords)):
                    dur_sec = result.get_duration(i, j, use_traffic=True) or 0
                    dist_m = result.get_distance(i, j) or 0
                    # Round up to at least 1 minute for non-zero links
                    dur_min = 0 if dur_sec == 0 else max(1, int(round(dur_sec / 60)))
                    row_durations.append(dur_min)
                    row_distances.append(dist_m)
                durations_min.append(row_durations)
                distances_m.append(row_distances)
            
            matrix = DistanceMatrix(
                origins=locations,
                destinations=locations,
                durations=durations_min,
                distances=distances_m
            )
            
            # Cache for future use
            await cache_distance_matrix(locations, matrix.model_dump(), mode)
            return matrix
        except Exception as e:
            logger.error(f"Falling back to mock distance matrix: {e}")
            # Fallback to mock distance matrix as a last resort
            matrix = get_mock_distance_matrix(locations)
            await cache_distance_matrix(locations, matrix.model_dump(), mode)
            return matrix
    
    def create_data_model(self, selected_pois: List[ScoredPOI], 
                         distance_matrix: DistanceMatrix,
                         config: OptimizationConfig) -> Dict:
        """
        Create data model for OR-Tools solver.
        
        Args:
            selected_pois: List of selected POIs
            distance_matrix: Distance matrix between locations
            config: Optimization configuration
            
        Returns:
            Data model dictionary for OR-Tools
        """
        num_locations = len(selected_pois) + 1  # +1 for hotel/depot
        
        # Create time windows
        time_windows = []
        
        # Hotel/depot time window (start and end of day)
        time_windows.append([config.start_time_min, config.end_time_min])
        
        # POI time windows
        for scored_poi in selected_pois:
            poi = scored_poi.poi
            open_time = time_str_to_minutes(poi.open_time)
            close_time = time_str_to_minutes(poi.close_time)
            
            # Ensure POI can be visited within the day
            effective_open = max(open_time, config.start_time_min)
            effective_close = min(close_time, config.end_time_min)
            
            time_windows.append([effective_open, effective_close])
        
        # Service times (visit durations)
        service_times = [0]  # No service time at depot
        for scored_poi in selected_pois:
            poi = scored_poi.poi
            duration = poi.duration_min or get_category_duration(poi.category)
            service_times.append(duration)
        
        data = {
            'distance_matrix': distance_matrix.durations,
            'time_windows': time_windows,
            'service_times': service_times,
            'num_vehicles': 1,
            'depot': 0,  # Hotel is at index 0
            'num_locations': num_locations
        }
        
        return data
    
    def solve_vrptw(self, data: Dict, config: OptimizationConfig) -> Optional[Dict]:
        """
        Solve the Vehicle Routing Problem with Time Windows.
        
        Args:
            data: Data model for the problem
            config: Optimization configuration
            
        Returns:
            Solution dictionary or None if no solution found
        """
        logger.info(f"Starting OR-Tools solver for {data['num_locations']} locations")
        start_time = time.time()
        
        # Create the routing index manager
        manager = pywrapcp.RoutingIndexManager(
            data['num_locations'],
            data['num_vehicles'], 
            data['depot']
        )
        
        # Create routing model
        routing = pywrapcp.RoutingModel(manager)
        
        # Create and register transit callback
        def time_callback(from_index, to_index):
            """Return the travel time between two points."""
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['distance_matrix'][from_node][to_node] + data['service_times'][from_node]
        
        transit_callback_index = routing.RegisterTransitCallback(time_callback)
        
        # Define cost of each arc (travel time)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Add time window constraints
        time_dimension_name = 'Time'
        routing.AddDimension(
            transit_callback_index,
            30,  # Allow waiting time
            1440,  # Maximum time (24 hours in minutes)
            False,  # Don't force start cumul to zero
            time_dimension_name
        )
        time_dimension = routing.GetDimensionOrDie(time_dimension_name)
        
        # Add time window constraints for each location
        for location_idx, (start_time, end_time) in enumerate(data['time_windows']):
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(start_time, end_time)
        
        # Add start and end constraints for depot
        for vehicle_id in range(data['num_vehicles']):
            start_index = routing.Start(vehicle_id)
            end_index = routing.End(vehicle_id)
            
            # Ensure we start at the beginning of the time window
            time_dimension.CumulVar(start_index).SetRange(
                data['time_windows'][0][0], 
                data['time_windows'][0][1]
            )
            time_dimension.CumulVar(end_index).SetRange(
                data['time_windows'][0][0], 
                data['time_windows'][0][1]
            )
        
        # Allow dropping POIs if they can't be visited (with penalty)
        for node in range(1, data['num_locations']):  # Skip depot
            routing.AddDisjunction([manager.NodeToIndex(node)], config.drop_penalty)
        
        # Set solver parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = config.time_limit_ms // 1000
        
        # Solve the problem
        logger.debug(f"Running solver with {config.time_limit_ms}ms time limit")
        solution = routing.SolveWithParameters(search_parameters)
        
        solve_time_ms = int((time.time() - start_time) * 1000)
        
        if solution:
            logger.info(f"Solution found in {solve_time_ms}ms")
            return self._extract_solution(solution, manager, routing, time_dimension, solve_time_ms)
        else:
            logger.warning(f"No solution found in {solve_time_ms}ms")
            return None
    
    def _extract_solution(self, solution, manager, routing, time_dimension, 
                         solve_time_ms: int) -> Dict:
        """
        Extract solution from OR-Tools solver.
        
        Args:
            solution: OR-Tools solution object
            manager: Index manager
            routing: Routing model
            time_dimension: Time dimension
            solve_time_ms: Solver time in milliseconds
            
        Returns:
            Solution dictionary
        """
        route = []
        total_time = 0
        dropped_nodes = []
        
        # Get the route for vehicle 0
        index = routing.Start(0)
        
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            time_var = time_dimension.CumulVar(index)
            arrival_time = solution.Value(time_var)
            
            route.append({
                'node': node_index,
                'arrival_time': arrival_time
            })
            
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            
            if not routing.IsEnd(index):
                total_time += routing.GetArcCostForVehicle(
                    previous_index, index, 0
                )
        
        # Add final depot visit
        final_node = manager.IndexToNode(index)
        time_var = time_dimension.CumulVar(index)
        final_time = solution.Value(time_var)
        
        route.append({
            'node': final_node,
            'arrival_time': final_time
        })
        
        # Find dropped nodes
        for node in range(1, manager.GetNumberOfNodes()):
            if solution.Value(routing.NextVar(manager.NodeToIndex(node))) == manager.NodeToIndex(node):
                dropped_nodes.append(node)
        
        return {
            'route': route,
            'total_time': total_time,
            'dropped_nodes': dropped_nodes,
            'solve_time_ms': solve_time_ms,
            'objective_value': solution.ObjectiveValue()
        }
    
    async def optimize_day(self, selected_pois: List[ScoredPOI], 
                          hotel_location: Dict[str, float],
                          request: PlanRequest) -> DayPlan:
        """
        Optimize the route for a day's itinerary.
        
        Args:
            selected_pois: List of selected POIs
            hotel_location: Hotel coordinates {lat, lng}
            request: Original planning request
            
        Returns:
            Optimized day plan
        """
        logger.info(f"Optimizing route for {len(selected_pois)} POIs")
        
        if not selected_pois:
            logger.warning("No POIs to optimize")
            return self._create_empty_plan(request)
        
        # Create locations list (hotel first, then POIs)
        locations = [hotel_location]
        for scored_poi in selected_pois:
            locations.append({
                "lat": scored_poi.poi.lat,
                "lng": scored_poi.poi.lng
            })
        
        # Get distance matrix
        distance_matrix = await self.get_distance_matrix(locations, request.mode)
        
        # Create optimization config
        config = self.config or OptimizationConfig(
            time_limit_ms=1000,
            drop_penalty=300,
            start_time_min=time_str_to_minutes(request.start_time),
            end_time_min=time_str_to_minutes(request.end_time)
        )
        
        # Create data model
        data = self.create_data_model(selected_pois, distance_matrix, config)
        
        # Solve VRPTW
        solution = self.solve_vrptw(data, config)
        
        if not solution:
            logger.error("Failed to find optimal solution, falling back to simple order")
            return self._create_fallback_plan(selected_pois, request)
        
        # Build optimized itinerary
        return self._build_itinerary_from_solution(
            solution, selected_pois, distance_matrix, request, config
        )
    
    def _create_empty_plan(self, request: PlanRequest) -> DayPlan:
        """Create empty day plan."""
        return DayPlan(
            date=request.date or "2025-10-06",
            items=[],
            stats=ItineraryStats(
                total_travel_min=0,
                total_duration=0,
                total_pois=0,
                solver_time_ms=0,
                dropped_pois=0
            )
        )
    
    def _create_fallback_plan(self, selected_pois: List[ScoredPOI], 
                             request: PlanRequest) -> DayPlan:
        """Create fallback plan using simple ordering."""
        items = []
        current_time = time_str_to_minutes(request.start_time)
        total_travel_time = 0
        
        for i, scored_poi in enumerate(selected_pois):
            poi = scored_poi.poi
            
            # Add travel time
            if i > 0:
                current_time += scored_poi.travel_time_min
                total_travel_time += scored_poi.travel_time_min
            
            # Ensure arrival is after opening time
            open_time = time_str_to_minutes(poi.open_time)
            arrival_time = max(current_time, open_time)
            
            # Calculate visit duration
            duration = poi.duration_min or get_category_duration(poi.category)
            departure_time = arrival_time + duration
            
            # Create POI item
            poi_item = POI(
                name=poi.name,
                category=poi.category,
                arrive_at=minutes_to_time_str(arrival_time),
                depart_at=minutes_to_time_str(departure_time),
                duration_min=duration,
                lat=poi.lat,
                lng=poi.lng
            )
            items.append(poi_item)
            
            current_time = departure_time
        
        # Calculate total duration
        if items:
            start_time = time_str_to_minutes(items[0].arrive_at)
            end_time = time_str_to_minutes(items[-1].depart_at)
            total_duration = end_time - start_time
        else:
            total_duration = 0
        
        return DayPlan(
            date=request.date or "2025-10-06",
            items=items,
            stats=ItineraryStats(
                total_travel_min=total_travel_time,
                total_duration=total_duration,
                total_pois=len(items),
                solver_time_ms=0,
                dropped_pois=0
            )
        )
    
    def _build_itinerary_from_solution(self, solution: Dict, 
                                      selected_pois: List[ScoredPOI],
                                      distance_matrix: DistanceMatrix,
                                      request: PlanRequest,
                                      config: OptimizationConfig) -> DayPlan:
        """Build itinerary from OR-Tools solution."""
        items = []
        total_travel_time = 0
        
        # Process route (skip first and last depot visits)
        route_nodes = [stop['node'] for stop in solution['route'][1:-1]]
        
        for i, node_idx in enumerate(route_nodes):
            poi_idx = node_idx - 1  # Adjust for depot at index 0
            if poi_idx < 0 or poi_idx >= len(selected_pois):
                continue
                
            scored_poi = selected_pois[poi_idx]
            poi = scored_poi.poi
            
            # Get arrival time from solution
            arrival_time_min = solution['route'][i + 1]['arrival_time']
            
            # Calculate visit duration
            duration = poi.duration_min or get_category_duration(poi.category)
            departure_time_min = arrival_time_min + duration
            
            # Add travel time (from previous location)
            if i > 0:
                prev_node = route_nodes[i - 1]
                travel_time = distance_matrix.durations[prev_node][node_idx]
                total_travel_time += travel_time
            else:
                # Travel from hotel
                travel_time = distance_matrix.durations[0][node_idx]
                total_travel_time += travel_time
            
            # Create POI item
            poi_item = POI(
                name=poi.name,
                category=poi.category,
                arrive_at=minutes_to_time_str(arrival_time_min),
                depart_at=minutes_to_time_str(departure_time_min),
                duration_min=duration,
                lat=poi.lat,
                lng=poi.lng
            )
            items.append(poi_item)
        
        # Calculate total duration
        if items:
            start_time = time_str_to_minutes(items[0].arrive_at)
            end_time = time_str_to_minutes(items[-1].depart_at)
            total_duration = end_time - start_time
        else:
            total_duration = 0
        
        # Calculate dropped POIs
        dropped_pois = len(solution.get('dropped_nodes', []))
        
        return DayPlan(
            date=request.date or "2025-10-06",
            items=items,
            stats=ItineraryStats(
                total_travel_min=total_travel_time,
                total_duration=total_duration,
                total_pois=len(items),
                solver_time_ms=solution.get('solve_time_ms', 0),
                dropped_pois=dropped_pois
            )
        )


# Global optimizer instance
_optimizer_instance = None


def get_optimizer() -> RouteOptimizer:
    """Get or create the global optimizer instance."""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = RouteOptimizer()
    return _optimizer_instance


async def optimize_day(selected_pois: List[ScoredPOI], 
                      hotel_location: Dict[str, float],
                      request: PlanRequest) -> DayPlan:
    """
    Optimize the route for a day's itinerary using the global optimizer.
    
    Args:
        selected_pois: List of selected POIs
        hotel_location: Hotel coordinates {lat, lng}
        request: Original planning request
        
    Returns:
        Optimized day plan
    """
    optimizer = get_optimizer()
    return await optimizer.optimize_day(selected_pois, hotel_location, request)
