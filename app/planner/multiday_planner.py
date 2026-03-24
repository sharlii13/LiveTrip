"""
Main multi-day itinerary planner that orchestrates the complete planning process.
Combines POI scoring, day assignment, route optimization, and adjustment logic.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any
from collections import Counter

from app.models.multiday_schemas import (
    MultiDayPlanRequest, MultiDayItinerary, DayItinerary, ItinerarySummary
)
from app.planner.multiday_scorer import score_pois_for_multiday
from app.planner.greedy_day_assignment import assign_pois_to_days_enhanced, category_diversity_score
from app.planner.adjustment_logic import apply_adjustment_logic
from app.planner.multiday_optimizer import optimize_multiday_routes


logger = logging.getLogger(__name__)


class MultiDayPlanner:
    """Main orchestrator for multi-day itinerary planning."""
    
    def __init__(self):
        """Initialize the multi-day planner."""
        pass
    
    async def create_multiday_itinerary(self, request: MultiDayPlanRequest) -> MultiDayItinerary:
        """
        Create a complete multi-day itinerary following the specified planning logic.
        
        Args:
            request: Multi-day planning request
            
        Returns:
            Complete multi-day itinerary
        """
        logger.info(f"Starting multi-day itinerary planning for {request.days} days "
                   f"with {len(request.poi_list)} POIs")
        
        planning_start_time = datetime.now()
        
        # Step 1: Score Calculation - Combine POI score with user preference weights and distance penalties
        logger.info("Step 1: Calculating POI scores with preference weights and distance penalties")
        scored_pois = await score_pois_for_multiday(request)
        
        logger.info(f"POI scoring completed: {len(scored_pois)} POIs scored and ranked")
        
        # Step 2: Enhanced Greedy Day Assignment - Distribute POIs across days with category diversity
        logger.info("Step 2: Performing enhanced greedy day assignment with category diversity focus")
        assignment_result = await assign_pois_to_days_enhanced(scored_pois, request)
        
        logger.info(f"Day assignment completed: {assignment_result.assignment_stats['successful_assignments']} POIs assigned, "
                   f"{assignment_result.assignment_stats['unassigned_count']} unassigned")
        
        # Step 3: Route Optimization per Day - Use OR-Tools VRPTW solver
        logger.info("Step 3: Optimizing routes for each day using OR-Tools VRPTW")
        day_itineraries = await optimize_multiday_routes(assignment_result, request)
        
        logger.info(f"Route optimization completed for {len(day_itineraries)} days")
        
        # Step 4: Adjustment Logic - Handle day overflow/underutilization
        logger.info("Step 4: Applying enhanced adjustment logic for day balancing")
        adjusted_assignment_result = await apply_adjustment_logic(assignment_result, request)
        
        # Re-optimize routes after adjustments if assignments changed
        if adjusted_assignment_result.assignment_stats.get("adjustments_applied", False):
            logger.info("Re-optimizing routes after adjustments")
            day_itineraries = await optimize_multiday_routes(adjusted_assignment_result, request)
        
        adjusted_itineraries = day_itineraries
        
        # Create summary
        summary = self._create_itinerary_summary(
            adjusted_itineraries, adjusted_assignment_result, request, planning_start_time
        )
        
        # Create metadata
        metadata = {
            "planning_time_ms": int((datetime.now() - planning_start_time).total_seconds() * 1000),
            "algorithm_version": "1.0.0",
            "request_summary": {
                "city_area": f"{request.start_location.lat:.4f},{request.start_location.lng:.4f}",
                "total_available_hours": request.days * request.available_hours_per_day,
                "transportation_mode": request.transportation_mode,
                "max_daily_distance": request.constraints.max_daily_distance_km
            }
        }
        
        final_itinerary = MultiDayItinerary(
            itinerary=adjusted_itineraries,
            summary=summary,
            metadata=metadata
        )
        
        logger.info(f"Multi-day planning completed successfully: "
                   f"{summary.total_pois_covered} POIs across {summary.total_days} days, "
                   f"{summary.avg_daily_utilization} average utilization")
        
        return final_itinerary
    
    async def _apply_adjustment_logic(self, day_itineraries: List[DayItinerary],
                                     assignment_result, request: MultiDayPlanRequest) -> List[DayItinerary]:
        """
        Apply adjustment logic to handle day overflow/underutilization.
        
        Args:
            day_itineraries: Initial day itineraries
            assignment_result: Day assignment result
            request: Multi-day planning request
            
        Returns:
            Adjusted day itineraries
        """
        logger.info("Analyzing day utilizations for potential adjustments")
        
        # Analyze utilizations
        overutilized_days = []
        underutilized_days = []
        
        for day_itinerary in day_itineraries:
            utilization = day_itinerary.utilization_percent
            
            if utilization > 95:  # Over 95% utilization
                overutilized_days.append(day_itinerary.day)
            elif utilization < 60:  # Under 60% utilization
                underutilized_days.append(day_itinerary.day)
        
        logger.info(f"Day analysis: {len(overutilized_days)} overutilized, "
                   f"{len(underutilized_days)} underutilized days")
        
        # For now, return as-is. In future versions, implement POI redistribution
        # This is where you would implement:
        # - Moving POIs from overutilized days to underutilized days
        # - Adding unassigned POIs to underutilized days
        # - Re-running OR-Tools optimization after adjustments
        
        if overutilized_days or underutilized_days:
            logger.info("Adjustment opportunities identified but not implemented in this version")
        
        return day_itineraries
    
    def _create_itinerary_summary(self, day_itineraries: List[DayItinerary],
                                 assignment_result, request: MultiDayPlanRequest,
                                 planning_start_time: datetime) -> ItinerarySummary:
        """Create comprehensive itinerary summary."""
        
        # Calculate totals
        total_pois_covered = sum(len(day.schedule) for day in day_itineraries)
        total_distance_km = sum(day.total_distance_km for day in day_itineraries)
        
        # Calculate average utilization
        utilizations = [day.utilization_percent for day in day_itineraries if day.schedule]
        avg_utilization = sum(utilizations) / len(utilizations) if utilizations else 0
        avg_utilization_str = f"{avg_utilization:.1f}%"
        
        # Calculate category distribution
        categories_distribution = Counter()
        for day in day_itineraries:
            for category in day.categories_covered:
                categories_distribution[category] += 1
        
        # Get unassigned POIs
        unassigned_pois = [poi.poi.name for poi in assignment_result.unassigned_pois]
        
        # Calculate optimization stats
        total_solver_time = sum(day.solver_time_ms or 0 for day in day_itineraries)
        optimization_stats = {
            "total_solver_time_ms": total_solver_time,
            "avg_solver_time_per_day_ms": total_solver_time // request.days if request.days > 0 else 0,
            "planning_time_ms": int((datetime.now() - planning_start_time).total_seconds() * 1000),
            "assignment_rate": assignment_result.assignment_stats.get("assignment_rate", 0),
            "days_with_schedule": len([day for day in day_itineraries if day.schedule])
        }
        
        # Calculate average daily diversity
        avg_daily_diversity = sum(day.diversity_score for day in day_itineraries if hasattr(day, 'diversity_score')) / len(day_itineraries) if day_itineraries else 0
        
        return ItinerarySummary(
            total_days=request.days,
            total_pois_covered=total_pois_covered,
            total_distance_km=round(total_distance_km, 1),
            avg_daily_utilization=avg_utilization_str,
            avg_daily_diversity=f"{avg_daily_diversity:.2f}",
            categories_distribution=dict(categories_distribution),
            unassigned_pois=unassigned_pois,
            optimization_stats=optimization_stats
        )
    
    def validate_request(self, request: MultiDayPlanRequest) -> List[str]:
        """
        Validate the multi-day planning request and return any validation errors.
        
        Args:
            request: Multi-day planning request
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check if we have enough POIs for the number of days
        min_pois_needed = request.days * request.constraints.min_pois_per_day
        if len(request.poi_list) < min_pois_needed:
            errors.append(f"Need at least {min_pois_needed} POIs for {request.days} days "
                         f"(minimum {request.constraints.min_pois_per_day} per day)")
        
        # Check if daily hours are reasonable
        if request.available_hours_per_day > 16:
            errors.append("Available hours per day cannot exceed 16 hours")
        
        if request.available_hours_per_day < 2:
            errors.append("Available hours per day must be at least 2 hours")
        
        # Check POI durations
        max_single_poi_duration = max(poi.duration for poi in request.poi_list)
        if max_single_poi_duration > request.available_hours_per_day:
            errors.append(f"POI with {max_single_poi_duration}h duration exceeds daily available hours")
        
        # Check for duplicate POI IDs
        poi_ids = [poi.id for poi in request.poi_list]
        if len(poi_ids) != len(set(poi_ids)):
            errors.append("Duplicate POI IDs found in request")
        
        return errors


# Global planner instance
_planner_instance = None


def get_multiday_planner() -> MultiDayPlanner:
    """Get or create the global multi-day planner instance."""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = MultiDayPlanner()
    return _planner_instance


async def plan_multiday_itinerary(request: MultiDayPlanRequest) -> MultiDayItinerary:
    """
    Plan a multi-day itinerary using the global planner.
    
    Args:
        request: Multi-day planning request
        
    Returns:
        Complete multi-day itinerary
        
    Raises:
        ValueError: If request validation fails
    """
    planner = get_multiday_planner()
    
    # Validate request
    validation_errors = planner.validate_request(request)
    if validation_errors:
        error_message = "Request validation failed: " + "; ".join(validation_errors)
        logger.error(error_message)
        raise ValueError(error_message)
    
    # Create itinerary
    return await planner.create_multiday_itinerary(request)