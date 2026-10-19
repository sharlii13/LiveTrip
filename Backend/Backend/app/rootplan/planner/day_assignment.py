"""
Greedy day assignment algorithm for multi-day itinerary planning.
Distributes POIs across days based on score, duration, and category diversity.
"""
import logging
from typing import List, Dict, Optional, Set
from collections import Counter, defaultdict

from app.rootplan.models.multiday_schemas import (
    ScoredPOIForMultiDay, MultiDayPlanRequest, DayAssignmentResult,
    PlanningConstraints, time_str_to_minutes
)


logger = logging.getLogger(__name__)


class GreedyDayAssigner:
    """Greedy algorithm for assigning POIs to days."""
    
    def __init__(self):
        """Initialize the day assigner."""
        pass
    
    def calculate_day_utilization(self, day_pois: List[ScoredPOIForMultiDay], 
                                 available_hours: float) -> float:
        """
        Calculate utilization percentage for a day.
        
        Args:
            day_pois: POIs assigned to the day
            available_hours: Available hours for the day
            
        Returns:
            Utilization percentage (0.0 to 1.0)
        """
        total_duration = sum(poi.poi.duration for poi in day_pois)
        return min(total_duration / available_hours, 1.0)
    
    def get_day_categories(self, day_pois: List[ScoredPOIForMultiDay]) -> Set[str]:
        """Get set of categories already assigned to a day."""
        return {poi.poi.category for poi in day_pois}
    
    def calculate_category_penalty(self, poi_category: str, day_categories: Set[str], 
                                  avoid_repetition: bool) -> float:
        """
        Calculate penalty for category repetition within a day.
        
        Args:
            poi_category: Category of POI to add
            day_categories: Categories already in the day
            avoid_repetition: Whether to avoid category repetition
            
        Returns:
            Penalty score (0.0 to 1.0, where 0 is no penalty)
        """
        if not avoid_repetition:
            return 0.0
        
        if poi_category in day_categories:
            return 0.5  # Moderate penalty for repetition
        
        return 0.0  # No penalty for new category
    
    def calculate_time_fit_score(self, poi: ScoredPOIForMultiDay, 
                                current_day_duration: float, available_hours: float) -> float:
        """
        Calculate how well a POI fits in the remaining time for a day.
        
        Args:
            poi: POI to evaluate
            current_day_duration: Current total duration for the day
            available_hours: Total available hours for the day
            
        Returns:
            Fit score (0.0 to 1.0)
        """
        remaining_hours = available_hours - current_day_duration
        
        if poi.poi.duration > remaining_hours:
            return 0.0  # Doesn't fit
        
        # Perfect fit gets highest score
        if poi.poi.duration == remaining_hours:
            return 1.0
        
        # Prefer POIs that use time efficiently
        utilization = poi.poi.duration / remaining_hours
        
        if utilization >= 0.8:
            return 0.9  # Good utilization
        elif utilization >= 0.5:
            return 0.7  # Decent utilization
        elif utilization >= 0.2:
            return 0.5  # Some utilization
        else:
            return 0.3  # Low utilization
    
    def can_fit_in_opening_hours(self, poi: ScoredPOIForMultiDay, 
                               current_day_duration: float, start_time: str) -> bool:
        """
        Check if POI can fit within its opening hours given current day schedule.
        
        Args:
            poi: POI to check
            current_day_duration: Current day duration in hours
            start_time: Day start time in HH:MM format
            
        Returns:
            True if POI can fit within opening hours
        """
        poi_open = time_str_to_minutes(poi.poi.open)
        poi_close = time_str_to_minutes(poi.poi.close)
        day_start = time_str_to_minutes(start_time)
        
        # Calculate earliest possible start time for this POI
        current_duration_minutes = current_day_duration * 60
        earliest_start = day_start + current_duration_minutes
        
        # Must start after POI opens
        actual_start = max(earliest_start, poi_open)
        
        # Must finish before POI closes
        finish_time = actual_start + (poi.poi.duration * 60)
        
        return finish_time <= poi_close
    
    def calculate_day_assignment_score(self, poi: ScoredPOIForMultiDay, day_pois: List[ScoredPOIForMultiDay],
                                      available_hours: float, constraints: PlanningConstraints,
                                      start_time: str) -> float:
        """
        Calculate score for assigning a POI to a specific day.
        
        Args:
            poi: POI to assign
            day_pois: POIs already assigned to the day
            available_hours: Available hours for the day
            constraints: Planning constraints
            start_time: Day start time
            
        Returns:
            Assignment score (higher is better, -1 if impossible)
        """
        current_duration = sum(p.poi.duration for p in day_pois)
        
        # Check if POI fits in available time
        if current_duration + poi.poi.duration > available_hours:
            return -1  # Cannot fit
        
        # Check POI count constraints
        if len(day_pois) >= constraints.max_pois_per_day:
            return -1  # Day is full
        
        # Check opening hours compatibility
        if not self.can_fit_in_opening_hours(poi, current_duration, start_time):
            return -1  # Cannot fit in opening hours
        
        # Calculate positive factors
        base_score = poi.final_score
        time_fit = self.calculate_time_fit_score(poi, current_duration, available_hours)
        
        # Calculate penalties
        day_categories = self.get_day_categories(day_pois)
        category_penalty = self.calculate_category_penalty(
            poi.poi.category, day_categories, constraints.avoid_repetition
        )
        
        # Combine factors
        assignment_score = (
            base_score * 0.6 +  # 60% POI quality
            time_fit * 0.3 -    # 30% time fit
            category_penalty * 0.2  # 20% category penalty
        )
        
        return max(0.0, assignment_score)
    
    async def assign_pois_to_days(self, scored_pois: List[ScoredPOIForMultiDay],
                                request: MultiDayPlanRequest) -> DayAssignmentResult:
        """
        Assign POIs to days using greedy algorithm.
        
        Args:
            scored_pois: List of scored POIs sorted by score
            request: Multi-day planning request
            
        Returns:
            Day assignment result
        """
        logger.info(f"Starting greedy day assignment for {len(scored_pois)} POIs across {request.days} days")
        
        # Initialize day assignments
        day_assignments: Dict[int, List[ScoredPOIForMultiDay]] = {}
        for day in range(1, request.days + 1):
            day_assignments[day] = []
        
        unassigned_pois = []
        assignment_attempts = 0
        successful_assignments = 0
        
        # Greedy assignment loop
        for poi in scored_pois:
            assignment_attempts += 1
            best_day = None
            best_score = -1
            
            # Find the best day for this POI
            for day in range(1, request.days + 1):
                day_pois = day_assignments[day]
                
                assignment_score = self.calculate_day_assignment_score(
                    poi, day_pois, request.available_hours_per_day,
                    request.constraints, request.start_time
                )
                
                if assignment_score > best_score:
                    best_score = assignment_score
                    best_day = day
            
            # Assign to best day if possible
            if best_day is not None and best_score > 0:
                poi.assigned_day = best_day
                day_assignments[best_day].append(poi)
                successful_assignments += 1
                
                logger.debug(f"Assigned {poi.poi.name} to day {best_day} "
                           f"(score: {best_score:.3f}, duration: {poi.poi.duration}h)")
            else:
                unassigned_pois.append(poi)
                logger.debug(f"Could not assign {poi.poi.name} to any day")
        
        # Log assignment statistics
        total_assigned_duration = 0
        for day, pois in day_assignments.items():
            day_duration = sum(p.poi.duration for p in pois)
            total_assigned_duration += day_duration
            utilization = (day_duration / request.available_hours_per_day) * 100
            
            logger.info(f"Day {day}: {len(pois)} POIs, {day_duration:.1f}h duration, "
                       f"{utilization:.1f}% utilization")
        
        assignment_stats = {
            "total_attempts": assignment_attempts,
            "successful_assignments": successful_assignments,
            "assignment_rate": successful_assignments / assignment_attempts if assignment_attempts > 0 else 0,
            "total_assigned_duration": total_assigned_duration,
            "average_utilization": (total_assigned_duration / (request.days * request.available_hours_per_day)) * 100,
            "unassigned_count": len(unassigned_pois)
        }
        
        logger.info(f"Assignment completed: {successful_assignments}/{assignment_attempts} POIs assigned "
                   f"({assignment_stats['assignment_rate']:.1%})")
        
        return DayAssignmentResult(
            day_assignments=day_assignments,
            unassigned_pois=unassigned_pois,
            assignment_stats=assignment_stats
        )
    
    def balance_days(self, assignment_result: DayAssignmentResult, 
                    request: MultiDayPlanRequest) -> DayAssignmentResult:
        """
        Balance POIs across days to improve utilization and fairness.
        
        Args:
            assignment_result: Initial assignment result
            request: Multi-day planning request
            
        Returns:
            Balanced assignment result
        """
        logger.info("Starting day balancing process")
        
        day_assignments = assignment_result.day_assignments.copy()
        unassigned_pois = assignment_result.unassigned_pois.copy()
        
        # Calculate current utilizations
        utilizations = {}
        for day, pois in day_assignments.items():
            duration = sum(p.poi.duration for p in pois)
            utilizations[day] = duration / request.available_hours_per_day
        
        # Find underutilized days (less than 60% utilization)
        underutilized_days = [
            day for day, util in utilizations.items() 
            if util < 0.6 and len(day_assignments[day]) < request.constraints.max_pois_per_day
        ]
        
        # Try to assign unassigned POIs to underutilized days
        reassigned_count = 0
        remaining_unassigned = []
        
        for poi in unassigned_pois:
            assigned = False
            
            # Try underutilized days first
            for day in sorted(underutilized_days, key=lambda d: utilizations[d]):
                day_pois = day_assignments[day]
                assignment_score = self.calculate_day_assignment_score(
                    poi, day_pois, request.available_hours_per_day,
                    request.constraints, request.start_time
                )
                
                if assignment_score > 0:
                    poi.assigned_day = day
                    day_assignments[day].append(poi)
                    
                    # Update utilization
                    new_duration = sum(p.poi.duration for p in day_assignments[day])
                    utilizations[day] = new_duration / request.available_hours_per_day
                    
                    reassigned_count += 1
                    assigned = True
                    
                    logger.debug(f"Reassigned {poi.poi.name} to underutilized day {day}")
                    break
            
            if not assigned:
                remaining_unassigned.append(poi)
        
        if reassigned_count > 0:
            logger.info(f"Balancing completed: reassigned {reassigned_count} POIs")
            
            # Update assignment stats
            new_stats = assignment_result.assignment_stats.copy()
            new_stats["successful_assignments"] += reassigned_count
            new_stats["unassigned_count"] = len(remaining_unassigned)
            new_stats["assignment_rate"] = (
                new_stats["successful_assignments"] / new_stats["total_attempts"]
                if new_stats["total_attempts"] > 0 else 0
            )
            
            return DayAssignmentResult(
                day_assignments=day_assignments,
                unassigned_pois=remaining_unassigned,
                assignment_stats=new_stats
            )
        
        logger.info("No additional POIs could be reassigned during balancing")
        return assignment_result


# Global day assigner instance
_day_assigner_instance = None


def get_day_assigner() -> GreedyDayAssigner:
    """Get or create the global day assigner instance."""
    global _day_assigner_instance
    if _day_assigner_instance is None:
        _day_assigner_instance = GreedyDayAssigner()
    return _day_assigner_instance


async def assign_pois_to_days(scored_pois: List[ScoredPOIForMultiDay],
                             request: MultiDayPlanRequest) -> DayAssignmentResult:
    """
    Assign POIs to days using the global day assigner.
    
    Args:
        scored_pois: List of scored POIs
        request: Multi-day planning request
        
    Returns:
        Day assignment result with balancing applied
    """
    assigner = get_day_assigner()
    initial_result = await assigner.assign_pois_to_days(scored_pois, request)
    balanced_result = assigner.balance_days(initial_result, request)
    return balanced_result