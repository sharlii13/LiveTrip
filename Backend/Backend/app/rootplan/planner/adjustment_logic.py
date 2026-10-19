"""
Adjustment logic for multi-day itinerary planning.
Handles day overflow/underutilization, category redistribution, and balance optimization.
"""
import logging
from typing import List, Dict, Optional, Tuple, Set
from collections import Counter, defaultdict
import copy

from app.rootplan.models.multiday_schemas import (
    ScoredPOIForMultiDay, MultiDayPlanRequest, DayAssignmentResult,
    DayItinerary, PlanningConstraints
)
from app.rootplan.planner.greedy_day_assignment import category_diversity_score


logger = logging.getLogger(__name__)


class ItineraryAdjuster:
    """Handles adjustment and optimization of multi-day itinerary assignments."""
    
    def __init__(self):
        """Initialize the itinerary adjuster."""
        self.min_utilization = 0.5  # 50% minimum utilization
        self.max_utilization = 0.95  # 95% maximum utilization
        self.target_utilization = 0.8  # 80% target utilization
        self.min_diversity = 0.6  # 60% minimum diversity score
    
    def analyze_day_imbalances(
        self, 
        day_assignments: Dict[int, List[ScoredPOIForMultiDay]],
        request: MultiDayPlanRequest
    ) -> Dict[str, List[int]]:
        """
        Analyze day assignments to identify imbalances.
        
        Args:
            day_assignments: Current day assignments
            request: Multi-day planning request
            
        Returns:
            Dictionary with lists of overutilized, underutilized, and low diversity days
        """
        overutilized_days = []
        underutilized_days = []
        low_diversity_days = []
        
        logger.info("Analyzing day imbalances...")
        
        for day, pois in day_assignments.items():
            if not pois:
                underutilized_days.append(day)
                low_diversity_days.append(day)
                continue
            
            # Calculate utilization
            total_duration = sum(p.poi.duration for p in pois)
            utilization = total_duration / request.available_hours_per_day
            
            # Calculate diversity
            diversity = category_diversity_score(pois)
            
            # Categorize days
            if utilization > self.max_utilization:
                overutilized_days.append(day)
            elif utilization < self.min_utilization:
                underutilized_days.append(day)
            
            if diversity < self.min_diversity:
                low_diversity_days.append(day)
            
            logger.debug(f"Day {day}: {utilization:.1%} utilization, {diversity:.2f} diversity")
        
        imbalances = {
            'overutilized': overutilized_days,
            'underutilized': underutilized_days,
            'low_diversity': low_diversity_days
        }
        
        logger.info(f"Imbalance analysis: {len(overutilized_days)} overutilized, "
                   f"{len(underutilized_days)} underutilized, {len(low_diversity_days)} low diversity")
        
        return imbalances
    
    def find_movable_pois(
        self,
        source_day_pois: List[ScoredPOIForMultiDay],
        reason: str = "balance"
    ) -> List[ScoredPOIForMultiDay]:
        """
        Find POIs that can be moved from a day based on the adjustment reason.
        
        Args:
            source_day_pois: POIs in the source day
            reason: Reason for moving ('overutilized', 'diversity', 'balance')
            
        Returns:
            List of POIs that can be moved
        """
        if not source_day_pois:
            return []
        
        movable_pois = []
        
        if reason == "overutilized":
            # Move lowest scoring POIs first
            sorted_pois = sorted(source_day_pois, key=lambda x: x.final_score)
            movable_pois = sorted_pois[:2]  # Move up to 2 lowest scoring POIs
            
        elif reason == "diversity":
            # Move POIs from overrepresented categories
            category_counts = Counter(p.poi.category for p in source_day_pois)
            overrepresented_categories = [
                cat for cat, count in category_counts.items() if count > 1
            ]
            
            for poi in source_day_pois:
                if poi.poi.category in overrepresented_categories:
                    movable_pois.append(poi)
                    
        elif reason == "balance":
            # Move moderately scoring POIs for general balance
            sorted_pois = sorted(source_day_pois, key=lambda x: x.final_score)
            middle_index = len(sorted_pois) // 2
            movable_pois = [sorted_pois[middle_index]] if middle_index < len(sorted_pois) else []
        
        return movable_pois
    
    def can_accept_poi(
        self,
        target_day_pois: List[ScoredPOIForMultiDay],
        poi_to_move: ScoredPOIForMultiDay,
        request: MultiDayPlanRequest
    ) -> bool:
        """
        Check if a target day can accept a POI without violating constraints.
        
        Args:
            target_day_pois: POIs in the target day
            poi_to_move: POI to move
            request: Multi-day planning request
            
        Returns:
            True if the POI can be accepted
        """
        # Check POI count constraint
        if len(target_day_pois) >= request.constraints.max_pois_per_day:
            return False
        
        # Check duration constraint
        current_duration = sum(p.poi.duration for p in target_day_pois)
        if current_duration + poi_to_move.poi.duration > request.available_hours_per_day:
            return False
        
        # Check if it improves or maintains diversity
        current_diversity = category_diversity_score(target_day_pois)
        target_categories = {p.poi.category for p in target_day_pois}
        
        # Accept if it's a new category (improves diversity)
        if poi_to_move.poi.category not in target_categories:
            return True
        
        # Accept if current diversity is already low (can't get much worse)
        if current_diversity < 0.7:
            return True
        
        # Otherwise, be selective
        return False
    
    def calculate_move_benefit(
        self,
        poi_to_move: ScoredPOIForMultiDay,
        source_day_pois: List[ScoredPOIForMultiDay],
        target_day_pois: List[ScoredPOIForMultiDay],
        request: MultiDayPlanRequest
    ) -> float:
        """
        Calculate the benefit score of moving a POI from source to target day.
        
        Args:
            poi_to_move: POI to move
            source_day_pois: POIs in source day
            target_day_pois: POIs in target day
            request: Multi-day planning request
            
        Returns:
            Benefit score (higher is better)
        """
        if not self.can_accept_poi(target_day_pois, poi_to_move, request):
            return -1  # Invalid move
        
        # Calculate current states
        source_duration = sum(p.poi.duration for p in source_day_pois)
        target_duration = sum(p.poi.duration for p in target_day_pois)
        source_diversity = category_diversity_score(source_day_pois)
        target_diversity = category_diversity_score(target_day_pois)
        
        # Calculate states after move
        source_pois_after = [p for p in source_day_pois if p != poi_to_move]
        target_pois_after = target_day_pois + [poi_to_move]
        
        source_duration_after = sum(p.poi.duration for p in source_pois_after)
        target_duration_after = sum(p.poi.duration for p in target_pois_after)
        source_diversity_after = category_diversity_score(source_pois_after)
        target_diversity_after = category_diversity_score(target_pois_after)
        
        # Calculate utilization changes
        source_util_before = source_duration / request.available_hours_per_day
        source_util_after = source_duration_after / request.available_hours_per_day
        target_util_before = target_duration / request.available_hours_per_day
        target_util_after = target_duration_after / request.available_hours_per_day
        
        # Calculate benefit components
        utilization_benefit = 0
        diversity_benefit = 0
        
        # Utilization benefit (moving toward target utilization is better)
        source_util_improvement = abs(source_util_before - self.target_utilization) - abs(source_util_after - self.target_utilization)
        target_util_improvement = abs(target_util_before - self.target_utilization) - abs(target_util_after - self.target_utilization)
        utilization_benefit = source_util_improvement + target_util_improvement
        
        # Diversity benefit
        diversity_benefit = (source_diversity_after - source_diversity) + (target_diversity_after - target_diversity)
        
        # Total benefit
        total_benefit = utilization_benefit * 0.6 + diversity_benefit * 0.4
        
        return total_benefit
    
    def redistribute_pois(
        self,
        day_assignments: Dict[int, List[ScoredPOIForMultiDay]],
        unassigned_pois: List[ScoredPOIForMultiDay],
        request: MultiDayPlanRequest,
        imbalances: Dict[str, List[int]]
    ) -> Tuple[Dict[int, List[ScoredPOIForMultiDay]], List[ScoredPOIForMultiDay]]:
        """
        Redistribute POIs to improve balance and diversity.
        
        Args:
            day_assignments: Current day assignments
            unassigned_pois: Unassigned POIs
            request: Multi-day planning request
            imbalances: Detected imbalances
            
        Returns:
            Tuple of (adjusted_assignments, remaining_unassigned)
        """
        logger.info("Starting POI redistribution...")
        
        # Make a deep copy to avoid modifying original
        adjusted_assignments = copy.deepcopy(day_assignments)
        remaining_unassigned = copy.deepcopy(unassigned_pois)
        
        moves_made = 0
        max_moves = len(request.poi_list) // 2  # Limit moves to prevent infinite loops
        
        # Phase 1: Move POIs from overutilized to underutilized days
        for source_day in imbalances['overutilized']:
            if moves_made >= max_moves:
                break
                
            source_pois = adjusted_assignments[source_day]
            movable_pois = self.find_movable_pois(source_pois, "overutilized")
            
            for poi_to_move in movable_pois:
                if moves_made >= max_moves:
                    break
                
                best_target_day = None
                best_benefit = 0
                
                # Find best target day
                for target_day in imbalances['underutilized']:
                    if target_day == source_day:
                        continue
                    
                    target_pois = adjusted_assignments[target_day]
                    benefit = self.calculate_move_benefit(
                        poi_to_move, source_pois, target_pois, request
                    )
                    
                    if benefit > best_benefit:
                        best_benefit = benefit
                        best_target_day = target_day
                
                # Execute move if beneficial
                if best_target_day is not None and best_benefit > 0.1:
                    adjusted_assignments[source_day].remove(poi_to_move)
                    adjusted_assignments[best_target_day].append(poi_to_move)
                    poi_to_move.assigned_day = best_target_day
                    moves_made += 1
                    
                    logger.debug(f"Moved {poi_to_move.poi.name} from day {source_day} to day {best_target_day} "
                               f"(benefit: {best_benefit:.3f})")
        
        # Phase 2: Improve diversity by moving redundant categories
        for source_day in imbalances['low_diversity']:
            if moves_made >= max_moves:
                break
            
            source_pois = adjusted_assignments[source_day]
            movable_pois = self.find_movable_pois(source_pois, "diversity")
            
            for poi_to_move in movable_pois:
                if moves_made >= max_moves:
                    break
                
                # Look for days where this category would be new
                for target_day in range(1, request.days + 1):
                    if target_day == source_day or moves_made >= max_moves:
                        continue
                    
                    target_pois = adjusted_assignments[target_day]
                    target_categories = {p.poi.category for p in target_pois}
                    
                    # Move if it's a new category for the target day
                    if (poi_to_move.poi.category not in target_categories and
                        self.can_accept_poi(target_pois, poi_to_move, request)):
                        
                        adjusted_assignments[source_day].remove(poi_to_move)
                        adjusted_assignments[target_day].append(poi_to_move)
                        poi_to_move.assigned_day = target_day
                        moves_made += 1
                        
                        logger.debug(f"Moved {poi_to_move.poi.name} from day {source_day} to day {target_day} "
                                   f"for diversity (category: {poi_to_move.poi.category})")
                        break
        
        # Phase 3: Try to assign unassigned POIs to underutilized days
        unassigned_assigned = 0
        for poi in remaining_unassigned[:]:  # Use slice copy to allow modification
            if moves_made >= max_moves:
                break
            
            best_target_day = None
            best_score = 0
            
            for target_day in imbalances['underutilized']:
                target_pois = adjusted_assignments[target_day]
                
                if self.can_accept_poi(target_pois, poi, request):
                    # Score based on how much it improves the day
                    current_utilization = sum(p.poi.duration for p in target_pois) / request.available_hours_per_day
                    current_diversity = category_diversity_score(target_pois)
                    
                    # Prefer days with low utilization and where this adds diversity
                    target_categories = {p.poi.category for p in target_pois}
                    diversity_bonus = 0.3 if poi.poi.category not in target_categories else 0
                    utilization_bonus = (self.target_utilization - current_utilization) * 0.5
                    
                    score = poi.final_score + diversity_bonus + utilization_bonus
                    
                    if score > best_score:
                        best_score = score
                        best_target_day = target_day
            
            # Assign to best day if found
            if best_target_day is not None:
                adjusted_assignments[best_target_day].append(poi)
                poi.assigned_day = best_target_day
                remaining_unassigned.remove(poi)
                unassigned_assigned += 1
                moves_made += 1
                
                logger.debug(f"Assigned unassigned POI {poi.poi.name} to day {best_target_day}")
        
        logger.info(f"Redistribution completed: {moves_made} moves made, "
                   f"{unassigned_assigned} unassigned POIs assigned")
        
        return adjusted_assignments, remaining_unassigned
    
    async def apply_adjustments(
        self,
        assignment_result: DayAssignmentResult,
        request: MultiDayPlanRequest
    ) -> DayAssignmentResult:
        """
        Apply adjustment logic to improve itinerary balance and diversity.
        
        Args:
            assignment_result: Initial assignment result
            request: Multi-day planning request
            
        Returns:
            Adjusted assignment result
        """
        logger.info("Applying itinerary adjustments...")
        
        # Analyze current imbalances
        imbalances = self.analyze_day_imbalances(
            assignment_result.day_assignments, request
        )
        
        # Skip adjustments if no significant imbalances
        total_imbalanced_days = (
            len(imbalances['overutilized']) + 
            len(imbalances['underutilized']) + 
            len(imbalances['low_diversity'])
        )
        
        if total_imbalanced_days == 0:
            logger.info("No significant imbalances detected, skipping adjustments")
            return assignment_result
        
        # Apply redistribution
        adjusted_assignments, remaining_unassigned = self.redistribute_pois(
            assignment_result.day_assignments,
            assignment_result.unassigned_pois,
            request,
            imbalances
        )
        
        # Recalculate statistics
        total_assigned = sum(len(pois) for pois in adjusted_assignments.values())
        new_assignment_rate = total_assigned / len(request.poi_list) if request.poi_list else 0
        
        # Calculate new daily statistics
        daily_stats = {}
        total_diversity_score = 0
        
        for day, pois in adjusted_assignments.items():
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
        
        avg_daily_diversity = total_diversity_score / request.days if request.days > 0 else 0
        
        adjusted_stats = {
            "total_attempts": assignment_result.assignment_stats.get("total_attempts", 0),
            "successful_assignments": total_assigned,
            "assignment_rate": new_assignment_rate,
            "avg_daily_diversity": f"{avg_daily_diversity:.2f}",
            "daily_stats": daily_stats,
            "unassigned_count": len(remaining_unassigned),
            "adjustments_applied": True,
            "imbalances_detected": imbalances
        }
        
        logger.info(f"Adjustments completed: assignment rate improved to {new_assignment_rate:.1%}, "
                   f"avg diversity: {avg_daily_diversity:.2f}")
        
        return DayAssignmentResult(
            day_assignments=adjusted_assignments,
            unassigned_pois=remaining_unassigned,
            assignment_stats=adjusted_stats
        )


# Global adjuster instance
_adjuster_instance = None


def get_itinerary_adjuster() -> ItineraryAdjuster:
    """Get or create the global itinerary adjuster instance."""
    global _adjuster_instance
    if _adjuster_instance is None:
        _adjuster_instance = ItineraryAdjuster()
    return _adjuster_instance


async def apply_adjustment_logic(
    assignment_result: DayAssignmentResult,
    request: MultiDayPlanRequest
) -> DayAssignmentResult:
    """
    Apply adjustment logic using the global adjuster instance.
    
    Args:
        assignment_result: Initial assignment result
        request: Multi-day planning request
        
    Returns:
        Adjusted assignment result
    """
    adjuster = get_itinerary_adjuster()
    return await adjuster.apply_adjustments(assignment_result, request)