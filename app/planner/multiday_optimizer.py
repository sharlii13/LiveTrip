"""
Multi-day route optimizer using OR-Tools VRPTW for optimal day-wise visit ordering.
"""
import time
import logging
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from app.models.multiday_schemas import (
    MultiDayPlanRequest, DayAssignmentResult, ScoredPOIForMultiDay,
    DayItinerary, ScheduledPOI, Location, OptimizationConfig,
    time_str_to_minutes, minutes_to_time_str, hours_to_time_str
)
from app.utils.mock_data import get_mock_distance_matrix
from app.utils.cache_utils import get_cached_distance_matrix, cache_distance_matrix


logger = logging.getLogger(__name__)


def _format_time_5min(minutes: int) -> str:
    """Round minutes to nearest 5-minute block and format as HH:MM."""
    hours = minutes // 60
    mins = minutes % 60
    # Round to nearest 5 minutes
    mins = 5 * round(mins / 5)
    if mins == 60:
        hours += 1
        mins = 0
    return f"{hours:02d}:{mins:02d}"


def _insert_dinner_slot(schedule: List[ScheduledPOI], fallback_coords: Location) -> List[ScheduledPOI]:
    """Insert a Dinner Break between 19:30–21:00, defaulting to 20:00–21:00.

    The dinner item is appended after the last POI that ends between 19:30 and 20:30,
    otherwise appended at the end. Coordinates default to the last POI of the day or fallback_coords.
    """
    if schedule is None:
        schedule = []

    insert_index = None
    last_before_window_index = None
    for i, item in enumerate(schedule):
        try:
            depart_min = time_str_to_minutes(item.end)
        except Exception:
            continue
        if 19 * 60 + 30 <= depart_min <= 20 * 60 + 30:
            last_before_window_index = i
    if last_before_window_index is not None:
        insert_index = last_before_window_index + 1
    else:
        insert_index = len(schedule)

    # Coordinates: use previous item's coords if available, else fallback
    coords = fallback_coords
    if insert_index > 0 and len(schedule) > 0:
        try:
            coords = schedule[min(insert_index - 1, len(schedule) - 1)].coordinates
        except Exception:
            coords = fallback_coords

    dinner_item = ScheduledPOI(
        poi="Dinner Break",
        poi_id=-1,
        start="20:00",
        end="21:00",
        duration_hr=1.0,
        travel_time_to_next=None,
        category="food",
        coordinates=Location(lat=coords.lat, lng=coords.lng)
    )

    schedule.insert(insert_index, dinner_item)
    return schedule


class MultiDayRouteOptimizer:
    """Multi-day route optimizer using OR-Tools VRPTW."""
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        """
        Initialize the optimizer with configuration.
        
        Args:
            config: Optimization configuration
        """
        self.config = config or OptimizationConfig()
    
    async def get_distance_matrix_for_day(self, locations: List[Dict[str, float]], 
                                         mode: str = "driving") -> List[List[int]]:
        """
        Get distance matrix for a day's locations.
        
        Args:
            locations: List of {lat, lng} location dictionaries
            mode: Transportation mode
            
        Returns:
            Distance matrix with travel times in minutes
        """
        # Try cache first
        cached_matrix = await get_cached_distance_matrix(locations, mode)
        if cached_matrix:
            if isinstance(cached_matrix, dict) and 'durations' in cached_matrix:
                return cached_matrix['durations']
            elif hasattr(cached_matrix, 'durations'):
                return cached_matrix.durations
        
        # Prefer real-time Google Distance Matrix API
        try:
            from app.services.google_distance import get_distance_service, TravelMode
            distance_service = await get_distance_service()
            coords = [(loc["lat"], loc["lng"]) for loc in locations]
            result = await distance_service.get_distance_matrix(
                origins=coords,
                destinations=coords,
                mode=TravelMode(mode)
            )
            durations_min: list[list[int]] = []
            for i in range(len(coords)):
                row = []
                for j in range(len(coords)):
                    dur_sec = result.get_duration(i, j, use_traffic=True) or 0
                    row.append(0 if dur_sec == 0 else max(1, int(round(dur_sec / 60))))
                durations_min.append(row)
            # Cache full matrix structure for reuse
            from app.models.schemas import DistanceMatrix as OneDayDistanceMatrix
            dm = OneDayDistanceMatrix(
                origins=locations,
                destinations=locations,
                durations=durations_min,
                distances=[[result.get_distance(i, j) or 0 for j in range(len(coords))] for i in range(len(coords))]
            )
            await cache_distance_matrix(locations, dm.model_dump(), mode)
            return durations_min
        except Exception as e:
            logger.error(f"Falling back to mock distance matrix for multi-day: {e}")
            matrix = get_mock_distance_matrix(locations)
            await cache_distance_matrix(locations, matrix.model_dump(), mode)
            return matrix.durations
    
    def create_vrptw_data_model(self, day_pois: List[ScoredPOIForMultiDay],
                               start_location: Location, request: MultiDayPlanRequest,
                               distance_matrix: List[List[int]]) -> Dict:
        """
        Create OR-Tools VRPTW data model for a single day.
        
        Args:
            day_pois: POIs assigned to this day
            start_location: Starting location (hotel)
            request: Multi-day planning request
            distance_matrix: Travel time matrix in minutes
            
        Returns:
            VRPTW data model dictionary
        """
        num_locations = len(day_pois) + 1  # +1 for hotel/start location
        
        # Create time windows for each location
        time_windows = []
        service_times = []
        
        # Hotel/start location time window
        day_start_min = time_str_to_minutes(request.start_time)
        day_end_min = day_start_min + int(request.available_hours_per_day * 60)
        time_windows.append([day_start_min, day_end_min])
        service_times.append(0)  # No service time at start location
        
        # POI time windows and service times
        for poi in day_pois:
            poi_open = time_str_to_minutes(poi.poi.open)
            poi_close = time_str_to_minutes(poi.poi.close)
            
            # Ensure POI can be visited within the day
            effective_open = max(poi_open, day_start_min)
            effective_close = min(poi_close, day_end_min)
            
            time_windows.append([effective_open, effective_close])
            service_times.append(int(poi.poi.duration * 60))  # Convert hours to minutes
        
        data = {
            'distance_matrix': distance_matrix,
            'time_windows': time_windows,
            'service_times': service_times,
            'num_vehicles': 1,
            'depot': 0,  # Hotel is at index 0
            'num_locations': num_locations
        }
        
        return data
    
    def solve_day_vrptw(self, data: Dict) -> Optional[Dict]:
        """
        Solve VRPTW for a single day using OR-Tools.
        
        Args:
            data: VRPTW data model
            
        Returns:
            Solution dictionary or None if no solution found
        """
        start_time = time.time()
        
        # Create routing model
        manager = pywrapcp.RoutingIndexManager(
            data['num_locations'],
            data['num_vehicles'],
            data['depot']
        )
        routing = pywrapcp.RoutingModel(manager)
        
        # Create transit callback
        def time_callback(from_index, to_index):
            """Return travel time + service time at origin."""
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['distance_matrix'][from_node][to_node] + data['service_times'][from_node]
        
        transit_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Add time dimension
        time_dimension_name = 'Time'
        routing.AddDimension(
            transit_callback_index,
            30,  # Allow 30 minutes slack
            1440,  # Maximum 24 hours
            False,  # Don't force start cumul to zero
            time_dimension_name
        )
        time_dimension = routing.GetDimensionOrDie(time_dimension_name)
        
        # Set time windows for each location
        for location_idx, (start_time_window, end_time_window) in enumerate(data['time_windows']):
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(start_time_window, end_time_window)
        
        # Allow dropping POIs if infeasible
        for node in range(1, data['num_locations']):  # Skip depot
            routing.AddDisjunction([manager.NodeToIndex(node)], self.config.drop_penalty)
        
        # Set solver parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = self.config.time_limit_ms // 1000
        
        # Solve
        solution = routing.SolveWithParameters(search_parameters)
        solve_time_ms = int((time.time() - start_time) * 1000)
        
        if solution:
            return self._extract_day_solution(solution, manager, routing, time_dimension, solve_time_ms)
        
        return None
    
    def _extract_day_solution(self, solution, manager, routing, time_dimension, solve_time_ms: int) -> Dict:
        """Extract solution from OR-Tools solver for a single day."""
        route = []
        total_time = 0
        dropped_nodes = []
        
        # Get route for vehicle 0
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
                total_time += routing.GetArcCostForVehicle(previous_index, index, 0)
        
        # Add final return to depot
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
    
    def build_day_itinerary(self, day: int, day_pois: List[ScoredPOIForMultiDay],
                           solution: Dict, distance_matrix: List[List[int]],
                           request: MultiDayPlanRequest) -> DayItinerary:
        """
        Build day itinerary from OR-Tools solution.
        
        Args:
            day: Day number
            day_pois: POIs assigned to this day
            solution: OR-Tools solution
            distance_matrix: Distance matrix
            request: Multi-day planning request
            
        Returns:
            Day itinerary with scheduled POIs
        """
        scheduled_pois = []
        total_travel_time = 0
        total_distance_km = 0.0
        
        # Process route (skip first and last depot visits)
        route_nodes = [stop['node'] for stop in solution['route'][1:-1]]
        
        for i, node_idx in enumerate(route_nodes):
            poi_idx = node_idx - 1  # Adjust for depot at index 0
            if poi_idx < 0 or poi_idx >= len(day_pois):
                continue
            
            scored_poi = day_pois[poi_idx]
            poi = scored_poi.poi
            
            # Get arrival time from solution
            arrival_time_min = solution['route'][i + 1]['arrival_time']
            
            # Calculate departure time
            duration_min = int(poi.duration * 60)
            departure_time_min = arrival_time_min + duration_min
            
            # Calculate travel time to next POI
            travel_time_to_next = None
            if i < len(route_nodes) - 1:
                next_node = route_nodes[i + 1]
                travel_time_to_next = distance_matrix[node_idx][next_node]
                total_travel_time += travel_time_to_next
                
                # Estimate distance (rough conversion: 1 minute = ~0.5 km in city driving)
                total_distance_km += travel_time_to_next * 0.5
            
            # Create scheduled POI with rounded times
            scheduled_poi = ScheduledPOI(
                poi=poi.name,
                poi_id=poi.id,
                start=_format_time_5min(arrival_time_min),
                end=_format_time_5min(departure_time_min),
                duration_hr=poi.duration,
                travel_time_to_next=travel_time_to_next,
                category=poi.category,
                coordinates=Location(lat=poi.lat, lng=poi.lng)
            )
            scheduled_pois.append(scheduled_poi)
        
        # Calculate day statistics
        total_visit_duration = sum(poi.duration_hr for poi in scheduled_pois)
        total_duration_hr = total_visit_duration + (total_travel_time / 60.0)
        utilization_percent = (total_duration_hr / request.available_hours_per_day) * 100
        categories_covered = list(set(poi.category for poi in scheduled_pois))
        
        # Calculate enhanced fields
        from collections import Counter
        category_mix = dict(Counter(poi.category for poi in scheduled_pois))
        
        # Calculate diversity score
        from app.planner.greedy_day_assignment import category_diversity_score
        # Create mock ScoredPOI objects for diversity calculation
        mock_scored_pois = []
        for poi in scheduled_pois:
            # We need to create mock objects for diversity calculation
            from app.models.multiday_schemas import MultiDayPOI, ScoredPOIForMultiDay
            mock_poi = MultiDayPOI(
                id=poi.poi_id,
                name=poi.poi,
                lat=poi.coordinates.lat,
                lng=poi.coordinates.lng,
                duration=poi.duration_hr,
                open="08:00",  # Default values since we don't have them
                close="18:00",
                category=poi.category,
                score=5.0
            )
            mock_scored_poi = ScoredPOIForMultiDay(
                poi=mock_poi,
                final_score=5.0,
                preference_score=0.5,
                distance_penalty=0.1,
                category_bonus=0.1
            )
            mock_scored_pois.append(mock_scored_poi)
        
        diversity_score = category_diversity_score(mock_scored_pois)
        
        return DayItinerary(
            day=day,
            total_distance_km=round(total_distance_km, 1),
            total_duration_hr=round(total_duration_hr, 2),
            visit_duration_hr=round(total_visit_duration, 2),
            utilization_percent=round(utilization_percent, 1),
            schedule=scheduled_pois,
            categories_covered=categories_covered,
            category_mix=category_mix,
            diversity_score=round(diversity_score, 2),
            solver_time_ms=solution.get('solve_time_ms', 0)
        )
    
    async def optimize_single_day(self, day: int, day_pois: List[ScoredPOIForMultiDay],
                                 start_location: Location, request: MultiDayPlanRequest) -> DayItinerary:
        """
        Optimize route for a single day.
        
        Args:
            day: Day number
            day_pois: POIs assigned to this day
            start_location: Starting location
            request: Multi-day planning request
            
        Returns:
            Optimized day itinerary
        """
        logger.info(f"Day {day}: Optimizing route for {len(day_pois)} POIs")
        
        if not day_pois:
            logger.warning(f"Day {day}: No POIs to optimize")
            return DayItinerary(
                day=day,
                total_distance_km=0,
                total_duration_hr=0,
                visit_duration_hr=0,
                utilization_percent=0,
                schedule=[],
                categories_covered=[],
                category_mix={},
                diversity_score=1.0,  # Empty day has perfect potential diversity
                solver_time_ms=0
            )
        
        # Create locations list (start location first, then POIs)
        locations = [{'lat': start_location.lat, 'lng': start_location.lng}]
        for poi in day_pois:
            locations.append({'lat': poi.poi.lat, 'lng': poi.poi.lng})
        
        # Get distance matrix
        distance_matrix = await self.get_distance_matrix_for_day(
            locations, request.transportation_mode
        )
        
        # Create VRPTW data model
        data = self.create_vrptw_data_model(day_pois, start_location, request, distance_matrix)
        
        # Solve VRPTW
        solution = self.solve_day_vrptw(data)
        
        if not solution:
            logger.error(f"Day {day}: Failed to find optimal solution, using simple order")
            day_itinerary = self._create_simple_day_itinerary(day, day_pois, request)
        else:
            # Build optimized itinerary
            day_itinerary = self.build_day_itinerary(day, day_pois, solution, distance_matrix, request)
        
        # Insert dinner slot after optimization
        day_itinerary.schedule = _insert_dinner_slot(day_itinerary.schedule, start_location)
        
        logger.info(f"Day {day}: Optimized {len(day_itinerary.schedule)} items (incl. dinner), "
                   f"{day_itinerary.utilization_percent:.1f}% utilization")
        
        return day_itinerary
    
    def _create_simple_day_itinerary(self, day: int, day_pois: List[ScoredPOIForMultiDay],
                                    request: MultiDayPlanRequest) -> DayItinerary:
        """Create simple day itinerary without optimization (fallback)."""
        scheduled_pois = []
        current_time_min = time_str_to_minutes(request.start_time)
        total_travel_time = 15  # Assume 15 min travel between POIs
        
        for poi in day_pois:
            # Simple scheduling
            arrival_time = max(current_time_min, time_str_to_minutes(poi.poi.open))
            duration_min = int(poi.poi.duration * 60)
            departure_time = arrival_time + duration_min
            
            scheduled_poi = ScheduledPOI(
                poi=poi.poi.name,
                poi_id=poi.poi.id,
                start=_format_time_5min(arrival_time),
                end=_format_time_5min(departure_time),
                duration_hr=poi.poi.duration,
                travel_time_to_next=15,  # Simple assumption
                category=poi.poi.category,
                coordinates=Location(lat=poi.poi.lat, lng=poi.poi.lng)
            )
            scheduled_pois.append(scheduled_poi)
            
            current_time_min = departure_time + 15  # Travel time
        
        total_duration_hr = (current_time_min - time_str_to_minutes(request.start_time)) / 60.0
        visit_duration_hr = sum(poi.poi.duration for poi in day_pois)
        utilization_percent = (total_duration_hr / request.available_hours_per_day) * 100
        categories_covered = list(set(poi.poi.category for poi in day_pois))
        
        # Calculate enhanced fields
        from collections import Counter
        from app.planner.greedy_day_assignment import category_diversity_score
        
        category_mix = dict(Counter(poi.poi.category for poi in day_pois))
        diversity_score = category_diversity_score(day_pois)
        
        return DayItinerary(
            day=day,
            total_distance_km=len(day_pois) * 2.0,  # Simple estimate
            total_duration_hr=round(total_duration_hr, 2),
            visit_duration_hr=round(visit_duration_hr, 2),
            utilization_percent=round(utilization_percent, 1),
            schedule=scheduled_pois,
            categories_covered=categories_covered,
            category_mix=category_mix,
            diversity_score=round(diversity_score, 2),
            solver_time_ms=0
        )
    
    async def optimize_multi_day_itinerary(self, assignment_result: DayAssignmentResult,
                                          request: MultiDayPlanRequest) -> List[DayItinerary]:
        """
        Optimize routes for all days in the multi-day itinerary.
        
        Args:
            assignment_result: Day assignment result
            request: Multi-day planning request
            
        Returns:
            List of optimized day itineraries
        """
        logger.info(f"Starting multi-day route optimization for {request.days} days")
        
        day_itineraries = []
        used_poi_ids: set[int] = set()
        
        # Optimize each day separately, ensuring uniqueness of POIs across days
        for day in range(1, request.days + 1):
            original_day_pois = assignment_result.day_assignments.get(day, [])
            # Filter out already used POIs to avoid repetition across days
            day_pois = [p for p in original_day_pois if p.poi.id not in used_poi_ids]
            
            day_itinerary = await self.optimize_single_day(
                day, day_pois, request.start_location, request
            )
            day_itineraries.append(day_itinerary)
            
            # Mark used POIs from this day
            for sp in day_pois:
                used_poi_ids.add(sp.poi.id)
        
        logger.info(f"Multi-day optimization completed for {len(day_itineraries)} days")
        return day_itineraries


# Global optimizer instance
_optimizer_instance = None


def get_multiday_optimizer() -> MultiDayRouteOptimizer:
    """Get or create the global multi-day optimizer instance."""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = MultiDayRouteOptimizer()
    return _optimizer_instance


async def optimize_multiday_routes(assignment_result: DayAssignmentResult,
                                  request: MultiDayPlanRequest) -> List[DayItinerary]:
    """
    Optimize routes for multi-day itinerary using the global optimizer.
    
    Args:
        assignment_result: Day assignment result
        request: Multi-day planning request
        
    Returns:
        List of optimized day itineraries
    """
    optimizer = get_multiday_optimizer()
    return await optimizer.optimize_multi_day_itinerary(assignment_result, request)
