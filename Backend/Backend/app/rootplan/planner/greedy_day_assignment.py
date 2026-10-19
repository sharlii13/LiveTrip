"""
Enhanced greedy day assignment algorithm for multi-day itinerary planning.
Focuses on category diversity, balanced utilization, and optimized POI distribution.
"""
import logging
from typing import List, Dict, Optional, Set, Tuple
from collections import Counter, defaultdict
import math

from app.rootplan.models.multiday_schemas import (
    ScoredPOIForMultiDay, MultiDayPlanRequest, DayAssignmentResult,
    PlanningConstraints, time_str_to_minutes, MultiDayPOI
)


logger = logging.getLogger(__name__)


def category_diversity_score(day_pois: List[ScoredPOIForMultiDay]) -> float:
    """
    Calculate category diversity score for a day.
    
    Args:
        day_pois: POIs assigned to the day
        
    Returns:
        Diversity score (0.0 to 1.0, where 1.0 is maximum diversity)
    """
    if not day_pois:
        return 1.0  # Empty day has perfect "potential" diversity
    
    categories = [poi.poi.category for poi in day_pois]
    unique_categories = len(set(categories))
    total_pois = len(categories)
    
    return unique_categories / total_pois if total_pois > 0 else 0.0


class EnhancedGreedyDayAssigner:
    """Enhanced greedy algorithm for assigning POIs to days with category diversity focus."""
    
    def __init__(self):
        """Initialize the enhanced day assigner."""
        self.category_weights = {
            'historical': 1.0,
            'nature': 1.0,
            'food': 0.8,
            'shopping': 0.7,
            'cultural': 1.0,
            'religious': 0.9,
            'entertainment': 0.8,
            'fort': 1.0,
            'museum': 1.0,
            'park': 0.9,
            'temple': 0.9,
            'historic': 1.0,
        }
    
    def calculate_enhanced_poi_score(
        self, 
        poi: ScoredPOIForMultiDay, 
        day_pois: List[ScoredPOIForMultiDay],
        available_hours: float, 
        constraints: PlanningConstraints,
        start_time: str,
        all_day_assignments: Dict[int, List[ScoredPOIForMultiDay]]
    ) -> float:
        """
        Calculate enhanced POI score using the new formula with diversity bonuses.
        
        Formula: final_score = (
            base_score * 0.3 +
            preference_score * 0.35 +
            category_bonus * 0.1 +
            time_feasibility * 0.1 +
            opening_compatibility * 0.1 -
            distance_penalty * 0.25 -
            repetition_penalty * 0.15
        )
        
        Args:
            poi: POI to score
            day_pois: POIs already assigned to this day
            available_hours: Available hours for the day
            constraints: Planning constraints
            start_time: Day start time
            all_day_assignments: All day assignments for cross-day analysis
            
        Returns:
            Enhanced score (higher is better, -1 if impossible)
        """
        current_duration = sum(p.poi.duration for p in day_pois)
        
        # Check if POI fits in available time
        if current_duration + poi.poi.duration > available_hours:
            return -1  # Cannot fit
        
        # Check POI count constraints
        if len(day_pois) >= constraints.max_pois_per_day:
            return -1  # Day is full
        
        # Check opening hours compatibility
        if not self._can_fit_in_opening_hours(poi, current_duration, start_time):
            return -1  # Cannot fit in opening hours
        
        # Calculate score components
        base_score = poi.final_score  # Already normalized 0-1
        preference_score = poi.preference_score
        
        # Category diversity bonus - reward new categories in this day
        day_categories = {p.poi.category for p in day_pois}
        category_bonus = 0.2 if poi.poi.category not in day_categories else 0.05
        
        # Time feasibility score
        time_feasibility = self._calculate_time_feasibility_score(
            poi, current_duration, available_hours
        )
        
        # Opening hours compatibility
        opening_compatibility = self._calculate_opening_compatibility(poi, start_time)
        
        # Distance penalty (using existing penalty from scoring)
        distance_penalty = poi.distance_penalty
        
        # Repetition penalty - penalize categories that appear too frequently across days
        repetition_penalty = self._calculate_repetition_penalty(
            poi.poi.category, all_day_assignments
        )
        
        # Enhanced scoring formula
        final_score = (
            base_score * 0.3 +
            preference_score * 0.35 +
            category_bonus * 0.1 +
            time_feasibility * 0.1 +
            opening_compatibility * 0.1 -
            distance_penalty * 0.25 -
            repetition_penalty * 0.15
        )
        
        return max(0.0, final_score)
    
    def _calculate_repetition_penalty(
        self, 
        category: str, 
        all_day_assignments: Dict[int, List[ScoredPOIForMultiDay]]
    ) -> float:
        """
        Calculate penalty for category repetition across all days.
        
        Args:
            category: Category to check
            all_day_assignments: All current day assignments
            
        Returns:
            Repetition penalty (0.0 to 0.3)
        """
        category_count = 0
        total_days = len(all_day_assignments)
        
        for day_pois in all_day_assignments.values():
            day_categories = [p.poi.category for p in day_pois]
            category_count += day_categories.count(category)
        
        if category_count == 0:
            return 0.0  # No penalty for new category
        elif category_count == 1:
            return 0.05  # Small penalty for second occurrence
        elif category_count == 2:
            return 0.15  # Moderate penalty for third occurrence
        else:
            return 0.3   # High penalty for excessive repetition
    
    def _calculate_time_feasibility_score(
        self, 
        poi: ScoredPOIForMultiDay, 
        current_duration: float, 
        available_hours: float
    ) -> float:
        """Calculate time feasibility score."""
        remaining_hours = available_hours - current_duration
        
        if poi.poi.duration > remaining_hours:
            return 0.0  # Doesn't fit
        
        # Perfect utilization gets highest score
        utilization = poi.poi.duration / remaining_hours
        
        if utilization >= 0.8:
            return 1.0  # Excellent utilization
        elif utilization >= 0.5:
            return 0.8  # Good utilization
        elif utilization >= 0.3:
            return 0.6  # Acceptable utilization
        else:
            return 0.4  # Low utilization
    
    def _calculate_opening_compatibility(self, poi: ScoredPOIForMultiDay, start_time: str) -> float:
        """Calculate opening hours compatibility score."""
        poi_open = time_str_to_minutes(poi.poi.open)
        poi_close = time_str_to_minutes(poi.poi.close)
        day_start = time_str_to_minutes(start_time)
        
        # Calculate available window
        available_start = max(poi_open, day_start)
        available_duration = poi_close - available_start
        
        if available_duration <= 0:
            return 0.0  # No available time
        
        # Check if POI duration fits
        if poi.poi.duration * 60 > available_duration:
            return 0.3  # Partial compatibility
        
        # Longer availability gets higher score
        total_possible = poi_close - poi_open
        availability_ratio = available_duration / total_possible if total_possible > 0 else 0
        
        return min(availability_ratio + 0.2, 1.0)
    
    def _can_fit_in_opening_hours(
        self, 
        poi: ScoredPOIForMultiDay, 
        current_day_duration: float, 
        start_time: str
    ) -> bool:
        """Check if POI can fit within opening hours."""
        poi_open = time_str_to_minutes(poi.poi.open)
        poi_close = time_str_to_minutes(poi.poi.close)
        day_start = time_str_to_minutes(start_time)
        
        # Calculate earliest possible start time
        current_duration_minutes = current_day_duration * 60
        earliest_start = day_start + current_duration_minutes
        
        # Must start after POI opens
        actual_start = max(earliest_start, poi_open)
        
        # Must finish before POI closes
        finish_time = actual_start + (poi.poi.duration * 60)
        
        return finish_time <= poi_close
    
    def calculate_day_balance_score(
        self, 
        day_assignments: Dict[int, List[ScoredPOIForMultiDay]],
        target_utilization: float = 0.85
    ) -> Dict[int, float]:
        """
        Calculate balance score for each day based on utilization and diversity.
        
        Args:
            day_assignments: Current day assignments
            target_utilization: Target utilization percentage
            
        Returns:
            Dictionary of day numbers to balance scores
        """
        balance_scores = {}
        
        for day, pois in day_assignments.items():
            if not pois:
                balance_scores[day] = 0.0
                continue
                
            # Calculate utilization score (closer to target is better)
            total_duration = sum(p.poi.duration for p in pois)
            utilization = total_duration / 8.0  # Assume 8 hours available
            utilization_score = 1.0 - abs(utilization - target_utilization)
            
            # Calculate diversity score
            diversity = category_diversity_score(pois)
            
            # Combine scores
            balance_scores[day] = (utilization_score * 0.6 + diversity * 0.4)
        
        return balance_scores
    
    async def assign_pois_to_days_enhanced(
        self, 
        scored_pois: List[ScoredPOIForMultiDay],
        request: MultiDayPlanRequest
    ) -> DayAssignmentResult:
        """
        Enhanced POI assignment with category diversity focus.
        
        Args:
            scored_pois: List of scored POIs
            request: Multi-day planning request
            
        Returns:
            Enhanced day assignment result
        """
        logger.info(f"Starting enhanced greedy assignment for {len(scored_pois)} POIs across {request.days} days")
        
        # Initialize day assignments
        day_assignments: Dict[int, List[ScoredPOIForMultiDay]] = {}
        for day in range(1, request.days + 1):
            day_assignments[day] = []
        
        unassigned_pois = []
        assignment_attempts = 0
        successful_assignments = 0
        
        # Enhanced greedy assignment with category diversity
        for poi in scored_pois:
            assignment_attempts += 1
            best_day = None
            best_score = -1
            
            # Calculate scores for all days
            day_scores = []
            for day in range(1, request.days + 1):
                day_pois = day_assignments[day]
                
                assignment_score = self.calculate_enhanced_poi_score(
                    poi, day_pois, request.available_hours_per_day,
                    request.constraints, request.start_time, day_assignments
                )
                
                if assignment_score > 0:
                    # Add diversity bonus for days with low diversity
                    current_diversity = category_diversity_score(day_pois)
                    diversity_bonus = (1.0 - current_diversity) * 0.1
                    
                    # Add utilization bonus for underutilized days
                    current_duration = sum(p.poi.duration for p in day_pois)
                    utilization = current_duration / request.available_hours_per_day
                    utilization_bonus = 0.1 if utilization < 0.6 else 0.0
                    
                    final_assignment_score = assignment_score + diversity_bonus + utilization_bonus
                    day_scores.append((day, final_assignment_score))
            
            # Sort by score and pick the best day
            if day_scores:
                day_scores.sort(key=lambda x: x[1], reverse=True)
                best_day, best_score = day_scores[0]
            
            # Assign to best day if found
            if best_day is not None and best_score > 0:
                poi.assigned_day = best_day
                day_assignments[best_day].append(poi)
                successful_assignments += 1
                
                logger.debug(f"Enhanced assignment: {poi.poi.name} to day {best_day} "
                           f"(score: {best_score:.3f}, category: {poi.poi.category})")
            else:
                unassigned_pois.append(poi)
                logger.debug(f"Could not assign {poi.poi.name} to any day")
        
        # Calculate enhanced statistics
        daily_stats = {}
        total_diversity_score = 0
        
        for day, pois in day_assignments.items():
            day_duration = sum(p.poi.duration for p in pois)
            utilization = (day_duration / request.available_hours_per_day) * 100
            diversity = category_diversity_score(pois)
            total_diversity_score += diversity
            
            category_mix = Counter(p.poi.category for p in pois)
            
            daily_stats[day] = {
                'pois_count': len(pois),
                'duration_hours': day_duration,
                'utilization_percent': utilization,
                'diversity_score': diversity,
                'category_mix': dict(category_mix)
            }
            
            logger.info(f"Day {day}: {len(pois)} POIs, {day_duration:.1f}h, "
                       f"{utilization:.1f}% utilization, {diversity:.2f} diversity")
        
        avg_daily_diversity = total_diversity_score / request.days if request.days > 0 else 0
        
        assignment_stats = {
            "total_attempts": assignment_attempts,
            "successful_assignments": successful_assignments,
            "assignment_rate": successful_assignments / assignment_attempts if assignment_attempts > 0 else 0,
            "avg_daily_diversity": f"{avg_daily_diversity:.2f}",
            "daily_stats": daily_stats,
            "unassigned_count": len(unassigned_pois)
        }
        
        logger.info(f"Enhanced assignment completed: {successful_assignments}/{assignment_attempts} POIs assigned "
                   f"({assignment_stats['assignment_rate']:.1%}), avg diversity: {avg_daily_diversity:.2f}")
        
        return DayAssignmentResult(
            day_assignments=day_assignments,
            unassigned_pois=unassigned_pois,
            assignment_stats=assignment_stats
        )


# Global enhanced assigner instance
_enhanced_assigner_instance = None


def get_enhanced_day_assigner() -> EnhancedGreedyDayAssigner:
    """Get or create the global enhanced day assigner instance."""
    global _enhanced_assigner_instance
    if _enhanced_assigner_instance is None:
        _enhanced_assigner_instance = EnhancedGreedyDayAssigner()
    return _enhanced_assigner_instance


async def assign_pois_to_days_enhanced(
    scored_pois: List[ScoredPOIForMultiDay],
    request: MultiDayPlanRequest
) -> DayAssignmentResult:
    """
    Assign POIs to days using enhanced category diversity algorithm.
    
    Args:
        scored_pois: List of scored POIs
        request: Multi-day planning request
        
    Returns:
        Enhanced day assignment result
    """
    assigner = get_enhanced_day_assigner()
    return await assigner.assign_pois_to_days_enhanced(scored_pois, request)