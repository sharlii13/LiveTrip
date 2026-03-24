# services/gamification.py
from geopy.distance import geodesic
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

# Import database models and session
from ..database import SessionLocal, User, EcoReward, EcoAction, HiddenGem, LocationTracking
from ..models.rewards import ActionType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GamificationService:
    """
    Complete gamification service for travel eco-rewards system
    """
    
    def __init__(self, db: Optional[Session] = None):
        """Initialize with optional database session"""
        self.db = db or SessionLocal()
        self._should_close_db = db is None  # Only close if we created the session
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_db:
            self.db.close()
    
    # ✅ Eco points configuration
    ECO_POINTS_CONFIG = {
        ActionType.PUBLIC_TRANSPORT: 20,
        ActionType.BIKE_USAGE: 25,        # Increased for cycling
        ActionType.WALKING: 15,           # Increased for walking
        ActionType.ECO_HOTEL: 30,
        ActionType.LOCAL_FOOD: 25,
        ActionType.HIDDEN_GEM_DISCOVERY: 50,
        ActionType.CONTENT_SUBMISSION: 40
    }
    
    # ✅ CO2 savings per action type (kg CO2 saved)
    CO2_SAVINGS_CONFIG = {
        ActionType.PUBLIC_TRANSPORT: 0.15,  # per km vs car
        ActionType.BIKE_USAGE: 0.21,        # per km vs car
        ActionType.WALKING: 0.21,           # per km vs car
        ActionType.ECO_HOTEL: 5.0,          # per night vs regular hotel
        ActionType.LOCAL_FOOD: 1.2,         # per meal vs imported/processed
        ActionType.HIDDEN_GEM_DISCOVERY: 0.0,
        ActionType.CONTENT_SUBMISSION: 0.0
    }
    
    async def award_eco_points(
        self, 
        user_id: int, 
        action_type: ActionType, 
        location: Optional[Tuple[float, float]] = None, 
        proof_data: Optional[str] = None,
        distance_km: Optional[float] = None
    ) -> int:
        """
        Award eco points for sustainable actions
        """
        try:
            base_points = self.ECO_POINTS_CONFIG.get(action_type, 10)
            total_points = base_points
            
            # Calculate distance-based points for transport
            if distance_km and action_type in [ActionType.PUBLIC_TRANSPORT, ActionType.BIKE_USAGE, ActionType.WALKING]:
                distance_points = int(base_points * distance_km)
                total_points = max(base_points, distance_points)  # At least base points
            
            # Bonus for location-based actions
            if location and action_type == ActionType.HIDDEN_GEM_DISCOVERY:
                exploration_bonus = await self._calculate_exploration_bonus(user_id, location)
                total_points += exploration_bonus
            
            # Calculate CO2 savings
            co2_saved = self.CO2_SAVINGS_CONFIG.get(action_type, 0.0)
            if distance_km and co2_saved > 0:
                co2_saved *= distance_km
            
            # Save to database
            eco_action = EcoAction(
                user_id=user_id,
                action_type=action_type.value,  # Convert enum to string
                points_earned=total_points,
                location_data=f"{location[0]},{location[1]}" if location else None,
                proof_image_url=proof_data,
                description=f"Earned {total_points} points for {action_type.value}",
                timestamp=datetime.utcnow()
            )
            
            self.db.add(eco_action)
            
            # Create eco reward record
            eco_reward = EcoReward(
                user_id=user_id,
                points=total_points,
                action_type=action_type.value,
                location_lat=location[0] if location else None,
                location_lng=location[1] if location else None,
                distance_km=distance_km,
                co2_saved=co2_saved,
                timestamp=datetime.utcnow()
            )
            
            self.db.add(eco_reward)
            
            # Update user total points and level
            await self._update_user_stats(user_id, total_points, co2_saved)
            
            self.db.commit()
            
            logger.info(f"Awarded {total_points} points to user {user_id} for {action_type.value}")
            return total_points
            
        except Exception as e:
            logger.error(f"Error awarding eco points: {e}")
            self.db.rollback()
            return 0
    
    async def check_geofence_discovery(self, user_id: int, lat: float, lng: float) -> Optional[dict]:
        """Check if user discovered a new hidden gem"""
        try:
            user_location = (lat, lng)
            
            # Check existing hidden gems within 50m radius
            nearby_gems = await self._get_nearby_gems(lat, lng, radius_meters=50)
            
            if not nearby_gems:
                # Potential new discovery - verify with AI/manual review
                discovery_data = {
                    "user_id": user_id,
                    "location": user_location,
                    "timestamp": datetime.utcnow(),
                    "requires_verification": True,
                    "potential_points": 50
                }
                return discovery_data
            else:
                # Check if user has already discovered these gems
                user_discoveries = await self._get_user_discoveries(user_id)
                undiscovered_gems = [gem for gem in nearby_gems if gem.id not in user_discoveries]
                
                if undiscovered_gems:
                    return {
                        "user_id": user_id,
                        "discovered_gems": [
                            {
                                "id": gem.id,
                                "name": gem.name,
                                "points": gem.discovery_points
                            }
                            for gem in undiscovered_gems
                        ],
                        "location": user_location
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking geofence discovery: {e}")
            return None
    
    async def award_discovery_points(self, user_id: int, gem_id: int, location: Tuple[float, float]) -> int:
        """Award points specifically for discovering a hidden gem"""
        try:
            gem = self.db.query(HiddenGem).filter(HiddenGem.id == gem_id).first()
            if not gem:
                return 0
            
            points = gem.discovery_points or 50
            
            # Award the points
            return await self.award_eco_points(
                user_id=user_id,
                action_type=ActionType.HIDDEN_GEM_DISCOVERY,
                location=location
            )
            
        except Exception as e:
            logger.error(f"Error awarding discovery points: {e}")
            return 0
    
    # ✅ Private helper methods
    async def _calculate_exploration_bonus(self, user_id: int, new_location: Tuple[float, float]) -> int:
        """Calculate bonus points for exploring new areas"""
        try:
            user_history = await self._get_user_location_history(user_id)
            
            if not user_history:
                return 20  # First exploration bonus
            
            # Calculate distance from previous locations
            min_distance = float('inf')
            for prev_location in user_history:
                distance = geodesic(new_location, prev_location).meters
                min_distance = min(min_distance, distance)
            
            if min_distance > 1000:  # 1km from any previous location
                return 30
            elif min_distance > 500:  # 500m
                return 15
            
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating exploration bonus: {e}")
            return 0
    
    async def _get_nearby_gems(self, lat: float, lng: float, radius_meters: int = 50) -> List[HiddenGem]:
        """Get hidden gems within specified radius"""
        try:
            # Convert meters to degrees (rough approximation)
            radius_deg = radius_meters / 111000  # 1 degree ≈ 111km
            
            nearby_gems = self.db.query(HiddenGem).filter(
                HiddenGem.lat.between(lat - radius_deg, lat + radius_deg),
                HiddenGem.lng.between(lng - radius_deg, lng + radius_deg),
                HiddenGem.is_verified == True
            ).all()
            
            return nearby_gems
            
        except Exception as e:
            logger.error(f"Error getting nearby gems: {e}")
            return []
    
    async def _get_user_location_history(self, user_id: int, limit: int = 50) -> List[Tuple[float, float]]:
        """Get user's recent location history"""
        try:
            locations = (
                self.db.query(LocationTracking.lat, LocationTracking.lng)
                .filter(LocationTracking.user_id == user_id)
                .order_by(LocationTracking.timestamp.desc())
                .limit(limit)
                .all()
            )
            
            return [(loc.lat, loc.lng) for loc in locations]
            
        except Exception as e:
            logger.error(f"Error getting user location history: {e}")
            return []
    
    async def _get_user_discoveries(self, user_id: int) -> List[int]:
        """Get list of gem IDs already discovered by user"""
        try:
            discoveries = (
                self.db.query(HiddenGem.id)
                .filter(HiddenGem.created_by_user_id == user_id)
                .all()
            )
            
            return [disc.id for disc in discoveries]
            
        except Exception as e:
            logger.error(f"Error getting user discoveries: {e}")
            return []
    
    async def _update_user_stats(self, user_id: int, points: int, co2_saved: float = 0.0):
        """Update user's total points, level, and CO2 savings"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found")
                return
            
            # Update points and CO2 savings
            user.total_eco_points += points
            user.carbon_footprint_saved += co2_saved
            
            # Calculate new level (100 points per level)
            new_level = (user.total_eco_points // 100) + 1
            
            if new_level > user.level:
                old_level = user.level
                user.level = new_level
                
                # Award level-up bonus
                level_bonus = EcoAction(
                    user_id=user_id,
                    action_type="level_up",
                    points_earned=10,
                    description=f"Level up bonus: {old_level} → {new_level}",
                    timestamp=datetime.utcnow()
                )
                self.db.add(level_bonus)
                user.total_eco_points += 10  # Level up bonus
                
                logger.info(f"User {user_id} leveled up: {old_level} → {new_level}")
            
        except Exception as e:
            logger.error(f"Error updating user stats: {e}")
    
    # ✅ Additional utility methods
    async def get_user_stats(self, user_id: int) -> dict:
        """Get comprehensive user statistics"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {}
            
            # Get recent actions
            recent_actions = (
                self.db.query(EcoAction)
                .filter(EcoAction.user_id == user_id)
                .order_by(EcoAction.timestamp.desc())
                .limit(10)
                .all()
            )
            
            # Get total distance traveled sustainably
            total_distance = (
                self.db.query(func.sum(EcoReward.distance_km))
                .filter(EcoReward.user_id == user_id)
                .scalar() or 0
            )
            
            # Get gems discovered
            gems_discovered = (
                self.db.query(HiddenGem)
                .filter(HiddenGem.created_by_user_id == user_id)
                .count()
            )
            
            return {
                "user_id": user_id,
                "name": user.name,
                "total_eco_points": user.total_eco_points,
                "level": user.level,
                "carbon_footprint_saved": round(user.carbon_footprint_saved, 2),
                "total_distance_km": round(total_distance, 2),
                "gems_discovered": gems_discovered,
                "recent_actions": [
                    {
                        "action_type": action.action_type,
                        "points": action.points_earned,
                        "timestamp": action.timestamp.isoformat() if action.timestamp else None
                    }
                    for action in recent_actions
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}
    
    async def get_leaderboard(self, limit: int = 50) -> List[dict]:
        """Get eco-friendly travelers leaderboard"""
        try:
            top_users = (
                self.db.query(User)
                .order_by(User.total_eco_points.desc())
                .limit(limit)
                .all()
            )
            
            leaderboard = []
            for idx, user in enumerate(top_users):
                leaderboard.append({
                    "rank": idx + 1,
                    "user_id": user.id,
                    "name": user.name,
                    "total_eco_points": user.total_eco_points,
                    "level": user.level,
                    "carbon_footprint_saved": round(user.carbon_footprint_saved, 2)
                })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []

# ✅ Convenience functions for easy usage
async def award_transport_points(user_id: int, transport_mode: str, distance_km: float, location: Tuple[float, float]) -> int:
    """Convenience function to award transport points"""
    
    transport_mapping = {
        "walking": ActionType.WALKING,
        "cycling": ActionType.BIKE_USAGE,
        "public_transport": ActionType.PUBLIC_TRANSPORT
    }
    
    action_type = transport_mapping.get(transport_mode)
    if not action_type:
        return 0
    
    with GamificationService() as service:
        return await service.award_eco_points(
            user_id=user_id,
            action_type=action_type,
            location=location,
            distance_km=distance_km
        )

async def check_gem_discovery(user_id: int, lat: float, lng: float) -> Optional[dict]:
    """Convenience function to check for gem discoveries"""
    with GamificationService() as service:
        return await service.check_geofence_discovery(user_id, lat, lng)

async def get_user_gamification_stats(user_id: int) -> dict:
    """Convenience function to get user stats"""
    with GamificationService() as service:
        return await service.get_user_stats(user_id)

# ✅ Export main class and convenience functions
__all__ = [
    'GamificationService',
    'award_transport_points', 
    'check_gem_discovery',
    'get_user_gamification_stats'
]
