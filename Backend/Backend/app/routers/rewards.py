from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
import json
import asyncio
from datetime import datetime, timedelta
from enum import Enum
import logging
import sys
import os
import random

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

logger = logging.getLogger(__name__)

# ✅ Database import handling
try:
    from database import get_db
    DATABASE_AVAILABLE = True
except ImportError:
    def get_db():
        return None
    DATABASE_AVAILABLE = False

# ✅ Create router
router = APIRouter(prefix="/rewards", tags=["🏆 Rewards & Gamification"])

# ✅ Enums
class ActionType(str, Enum):
    WALKING = "walking"
    CYCLING = "cycling"
    PUBLIC_TRANSPORT = "public_transport"
    ECO_HOTEL = "eco_hotel"
    LOCAL_FOOD = "local_food"
    HIDDEN_GEM_DISCOVERY = "hidden_gem_discovery"
    CONTENT_SUBMISSION = "content_submission"
    CARBON_OFFSET = "carbon_offset"

class BadgeType(str, Enum):
    GREEN_COMMUTER = "green_commuter"
    CYCLING_ENTHUSIAST = "cycling_enthusiast"
    EXPLORER = "explorer"
    ECO_WARRIOR = "eco_warrior"
    SUSTAINABLE_TRAVELER = "sustainable_traveler"
    COMMUNITY_CONTRIBUTOR = "community_contributor"
    WALKING_WARRIOR = "walking_warrior"

class TimePeriod(str, Enum):
    ALL_TIME = "all_time"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

# ✅ Pydantic Models
class UserStats(BaseModel):
    total_points: int = 0
    level: int = 1
    badges: List[Dict[str, Any]] = []
    recent_actions: List[Dict[str, Any]] = []
    co2_saved: float = 0.0
    gems_count: int = 0

class RewardClaimRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    achievement_type: str = Field(..., min_length=1)
    achievement_level: int = Field(1, ge=1, le=5)
    
    @validator('achievement_type')
    def validate_achievement_type(cls, v):
        valid_types = ["green_commuter", "cycling_enthusiast", "explorer", "eco_warrior", "walking_warrior", "community_contributor"]
        if v not in valid_types:
            raise ValueError(f"Invalid achievement type. Must be one of: {valid_types}")
        return v

class WeeklyChallenge(BaseModel):
    name: str
    description: str
    target: float
    progress: float
    completed: bool
    percentage: float
    reward: str
    days_remaining: int

# ✅ Enhanced Mock Data Storage
MOCK_USERS = {
    1: {
        "id": 1,
        "username": "EcoTraveler",
        "email": "eco@example.com",
        "total_eco_points": 1250,
        "level": 6,
        "carbon_footprint_saved": 45.6,
        "created_at": "2025-01-01T00:00:00",
        "last_active": "2025-01-20T15:30:00",
        "streak_days": 12
    },
    2: {
        "id": 2,
        "username": "GreenExplorer",
        "email": "green@example.com",
        "total_eco_points": 980,
        "level": 4,
        "carbon_footprint_saved": 32.4,
        "created_at": "2025-01-05T00:00:00",
        "last_active": "2025-01-19T12:15:00",
        "streak_days": 8
    },
    3: {
        "id": 3,
        "username": "SustainableNomad",
        "email": "sustainable@example.com",
        "total_eco_points": 850,
        "level": 4,
        "carbon_footprint_saved": 28.1,
        "created_at": "2025-01-10T00:00:00",
        "last_active": "2025-01-18T09:45:00",
        "streak_days": 5
    },
    4: {
        "id": 4,
        "username": "CyclingChampion",
        "email": "cycling@example.com",
        "total_eco_points": 720,
        "level": 3,
        "carbon_footprint_saved": 35.2,
        "created_at": "2025-01-12T00:00:00",
        "last_active": "2025-01-17T18:20:00",
        "streak_days": 15
    },
    5: {
        "id": 5,
        "username": "WalkingWarrior",
        "email": "walking@example.com",
        "total_eco_points": 650,
        "level": 3,
        "carbon_footprint_saved": 22.8,
        "created_at": "2025-01-15T00:00:00",
        "last_active": "2025-01-16T14:10:00",
        "streak_days": 7
    }
}

MOCK_REWARDS = {
    1: [
        {
            "id": 1,
            "user_id": 1,
            "points": 35,
            "action_type": "cycling",
            "transport_mode": "cycling",
            "distance_km": 8.5,
            "co2_saved": 2.1,
            "timestamp": "2025-01-20T10:30:00",
            "location": "Central Park Route"
        },
        {
            "id": 2,
            "user_id": 1,
            "points": 25,
            "action_type": "public_transport",
            "transport_mode": "public_transport",
            "distance_km": 15.2,
            "co2_saved": 3.5,
            "timestamp": "2025-01-19T08:45:00",
            "location": "Metro Line 2"
        },
        {
            "id": 3,
            "user_id": 1,
            "points": 50,
            "action_type": "hidden_gem_discovery",
            "gem_name": "Secret Rooftop Garden",
            "timestamp": "2025-01-18T16:20:00",
            "location": "Downtown District"
        }
    ],
    2: [
        {
            "id": 4,
            "user_id": 2,
            "points": 30,
            "action_type": "walking",
            "transport_mode": "walking",
            "distance_km": 4.2,
            "co2_saved": 1.8,
            "timestamp": "2025-01-19T12:15:00",
            "location": "Riverside Walk"
        }
    ]
}

MOCK_BADGES = {
    1: [
        {
            "id": 1,
            "user_id": 1,
            "badge_name": "green_commuter",
            "badge_level": 3,
            "earned_at": "2025-01-15T00:00:00",
            "badge_description": "Public Transport Master - Level 3",
            "icon": "🚌"
        },
        {
            "id": 2,
            "user_id": 1,
            "badge_name": "cycling_enthusiast",
            "badge_level": 2,
            "earned_at": "2025-01-12T00:00:00",
            "badge_description": "Cycling Champion - Level 2",
            "icon": "🚴"
        },
        {
            "id": 3,
            "user_id": 1,
            "badge_name": "explorer",
            "badge_level": 2,
            "earned_at": "2025-01-18T00:00:00",
            "badge_description": "Hidden Gem Hunter - Level 2",
            "icon": "💎"
        }
    ],
    2: [
        {
            "id": 4,
            "user_id": 2,
            "badge_name": "walking_warrior",
            "badge_level": 1,
            "earned_at": "2025-01-16T00:00:00",
            "badge_description": "Walking Master - Level 1",
            "icon": "🚶"
        }
    ]
}

MOCK_GEMS = {
    1: [
        {
            "id": 1,
            "name": "Secret Rooftop Garden",
            "description": "Hidden garden with city views",
            "created_by_user_id": 1,
            "is_verified": True,
            "discovery_points": 50,
            "created_at": "2025-01-08T00:00:00",
            "location": "Downtown District",
            "category": "nature"
        },
        {
            "id": 2,
            "name": "Underground Art Gallery",
            "description": "Hidden street art collection",
            "created_by_user_id": 1,
            "is_verified": True,
            "discovery_points": 40,
            "created_at": "2025-01-12T00:00:00",
            "location": "Arts Quarter",
            "category": "culture"
        },
        {
            "id": 3,
            "name": "Vintage Market Alley",
            "description": "Local artisan market",
            "created_by_user_id": 1,
            "is_verified": False,
            "discovery_points": 30,
            "created_at": "2025-01-18T00:00:00",
            "location": "Old Town",
            "category": "shopping"
        }
    ]
}

# ✅ WebSocket connections storage
active_connections: Dict[int, WebSocket] = {}

# ✅ Helper Functions
def get_user_level(points: int) -> int:
    """Calculate user level based on points"""
    if points < 100:
        return 1
    elif points < 300:
        return 2
    elif points < 600:
        return 3
    elif points < 1000:
        return 4
    elif points < 1500:
        return 5
    elif points < 2500:
        return 6
    else:
        return 7 + (points - 2500) // 1000

def get_next_level_points(current_level: int) -> int:
    """Get points required for next level"""
    level_thresholds = [0, 100, 300, 600, 1000, 1500, 2500]
    if current_level < len(level_thresholds):
        return level_thresholds[current_level]
    else:
        return 2500 + ((current_level - 6) * 1000)

async def get_users_by_eco_points(limit: int, time_period: str = "all_time") -> List[Dict[str, Any]]:
    """Get top users by eco points"""
    try:
        # Filter users based on time period (mock implementation)
        filtered_users = MOCK_USERS.copy()
        
        if time_period == "weekly":
            # Mock: filter for weekly activity
            weekly_cutoff = datetime.now() - timedelta(days=7)
            filtered_users = {
                uid: user for uid, user in filtered_users.items()
                if datetime.fromisoformat(user["last_active"]) > weekly_cutoff
            }
        elif time_period == "monthly":
            # Mock: filter for monthly activity
            monthly_cutoff = datetime.now() - timedelta(days=30)
            filtered_users = {
                uid: user for uid, user in filtered_users.items()
                if datetime.fromisoformat(user["last_active"]) > monthly_cutoff
            }
        
        # Sort by eco points
        sorted_users = sorted(filtered_users.values(), key=lambda x: x["total_eco_points"], reverse=True)
        
        leaderboard = []
        for idx, user in enumerate(sorted_users[:limit]):
            # Calculate additional metrics
            user_rewards = MOCK_REWARDS.get(user["id"], [])
            recent_activity_count = len([r for r in user_rewards if 
                datetime.fromisoformat(r["timestamp"]) > datetime.now() - timedelta(days=7)
            ])
            
            leaderboard.append({
                "rank": idx + 1,
                "user_id": user["id"],
                "username": user["username"],
                "total_eco_points": user["total_eco_points"],
                "level": user["level"],
                "carbon_footprint_saved": user["carbon_footprint_saved"],
                "recent_activity": recent_activity_count,
                "streak_days": user.get("streak_days", 0),
                "badges_earned": len(MOCK_BADGES.get(user["id"], [])),
                "gems_discovered": len([g for g in MOCK_GEMS.get(user["id"], []) if g.get("is_verified", False)]),
                "last_active": user["last_active"]
            })
        
        return leaderboard
        
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return []

async def calculate_user_stats(user_id: int) -> UserStats:
    """Calculate comprehensive user statistics"""
    try:
        user_data = MOCK_USERS.get(user_id, {})
        user_rewards = MOCK_REWARDS.get(user_id, [])
        user_badges = MOCK_BADGES.get(user_id, [])
        user_gems = MOCK_GEMS.get(user_id, [])
        
        if not user_data:
            return UserStats()
        
        # Format recent actions (last 10)
        recent_actions = []
        for reward in user_rewards[-10:]:
            action = {
                "action_type": reward["action_type"],
                "points": reward["points"],
                "timestamp": reward["timestamp"],
                "co2_saved": reward.get("co2_saved", 0)
            }
            
            if "transport_mode" in reward:
                action["transport_mode"] = reward["transport_mode"]
                action["distance_km"] = reward.get("distance_km", 0)
            
            if "gem_name" in reward:
                action["gem_name"] = reward["gem_name"]
            
            if "location" in reward:
                action["location"] = reward["location"]
                
            recent_actions.append(action)
        
        # Format badges
        formatted_badges = []
        for badge in user_badges:
            formatted_badges.append({
                "name": badge["badge_name"],
                "level": badge["badge_level"],
                "earned_at": badge["earned_at"],
                "description": badge["badge_description"],
                "icon": badge.get("icon", "🏆")
            })
        
        # Count verified gems
        verified_gems = len([gem for gem in user_gems if gem.get("is_verified", False)])
        
        return UserStats(
            total_points=user_data.get("total_eco_points", 0),
            level=user_data.get("level", 1),
            badges=formatted_badges,
            recent_actions=recent_actions,
            co2_saved=user_data.get("carbon_footprint_saved", 0.0),
            gems_count=verified_gems
        )
        
    except Exception as e:
        logger.error(f"Error calculating user stats: {e}")
        return UserStats()

async def wait_for_user_reward(user_id: int):
    """Simulate waiting for user reward events"""
    await asyncio.sleep(random.uniform(3, 8))  # Random interval 3-8 seconds
    
    # Mock reward generation (10% chance)
    if random.random() < 0.1:
        reward_types = ["walking", "cycling", "public_transport", "hidden_gem_discovery"]
        points_range = {"walking": [10, 20], "cycling": [20, 35], "public_transport": [15, 30], "hidden_gem_discovery": [40, 60]}
        
        action_type = random.choice(reward_types)
        point_range = points_range[action_type]
        points = random.randint(point_range[0], point_range[1])
        
        return {
            "points": points,
            "action_type": action_type,
            "timestamp": datetime.now().isoformat(),
            "co2_saved": round(random.uniform(0.5, 3.0), 1) if action_type != "hidden_gem_discovery" else 0
        }
    
    return None

# ✅ API Endpoints
@router.get("/leaderboard")
async def get_eco_leaderboard(
    limit: int = Query(50, ge=1, le=100, description="Number of top users"),
    time_period: TimePeriod = Query(TimePeriod.ALL_TIME, description="Time period for ranking")
):
    """Get eco-friendly travelers leaderboard"""
    try:
        leaderboard = await get_users_by_eco_points(limit, time_period.value)
        
        # Calculate statistics
        total_users = len(MOCK_USERS)
        total_points = sum(user["total_eco_points"] for user in leaderboard)
        total_co2_saved = sum(user["carbon_footprint_saved"] for user in leaderboard)
        total_badges = sum(user["badges_earned"] for user in leaderboard)
        
        return {
            "success": True,
            "time_period": time_period.value,
            "leaderboard": leaderboard,
            "statistics": {
                "total_users_ranked": len(leaderboard),
                "total_users_in_system": total_users,
                "total_eco_points": total_points,
                "total_co2_saved_kg": round(total_co2_saved, 2),
                "total_badges_earned": total_badges,
                "average_points_per_user": round(total_points / max(1, len(leaderboard)), 1),
                "top_performer": leaderboard[0] if leaderboard else None
            },
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting leaderboard: {str(e)}")

@router.get("/user-stats/{user_id}")
async def get_user_rewards_stats(user_id: int):
    """Get detailed user reward statistics"""
    try:
        if user_id not in MOCK_USERS:
            raise HTTPException(status_code=404, detail="User not found")
        
        stats = await calculate_user_stats(user_id)
        user_data = MOCK_USERS[user_id]
        
        # Calculate additional metrics
        total_distance = sum(
            action.get("distance_km", 0) for action in stats.recent_actions
            if "distance_km" in action
        )
        
        current_level = user_data["level"]
        next_level_points = get_next_level_points(current_level)
        points_to_next = max(0, next_level_points - stats.total_points)
        
        return {
            "success": True,
            "user_id": user_id,
            "username": user_data["username"],
            "total_eco_points": stats.total_points,
            "level": stats.level,
            "next_level_points": next_level_points,
            "points_to_next_level": points_to_next,
            "level_progress_percentage": round(((stats.total_points - get_next_level_points(current_level - 1)) / 
                                             (next_level_points - get_next_level_points(current_level - 1))) * 100, 1) if current_level > 1 else 0,
            "badges": stats.badges,
            "recent_actions": stats.recent_actions,
            "carbon_footprint_saved": stats.co2_saved,
            "hidden_gems_discovered": stats.gems_count,
            "total_distance_km": round(total_distance, 2),
            "achievements_unlocked": len(stats.badges),
            "streak_days": user_data.get("streak_days", 0),
            "last_activity": stats.recent_actions[0]["timestamp"] if stats.recent_actions else None,
            "joined_date": user_data["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting user stats: {str(e)}")

@router.get("/user-achievements/{user_id}")
async def get_user_achievements(user_id: int):
    """Get user achievements and progress toward badges"""
    try:
        if user_id not in MOCK_USERS:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = MOCK_USERS[user_id]
        user_rewards = MOCK_REWARDS.get(user_id, [])
        user_gems = MOCK_GEMS.get(user_id, [])
        
        # Calculate distances and actions by type
        transport_stats = {
            "public_transport_km": 0,
            "cycling_km": 0,
            "walking_km": 0,
            "gems_discovered": 0,
            "content_submissions": 0
        }
        
        for reward in user_rewards:
            transport_mode = reward.get("transport_mode", "")
            distance = reward.get("distance_km", 0)
            
            if transport_mode == "public_transport":
                transport_stats["public_transport_km"] += distance
            elif transport_mode == "cycling":
                transport_stats["cycling_km"] += distance
            elif transport_mode == "walking":
                transport_stats["walking_km"] += distance
            elif reward.get("action_type") == "hidden_gem_discovery":
                transport_stats["gems_discovered"] += 1
            elif reward.get("action_type") == "content_submission":
                transport_stats["content_submissions"] += 1
        
        # Add verified gems from MOCK_GEMS
        transport_stats["gems_discovered"] += len([g for g in user_gems if g.get("is_verified", False)])
        
        # Define badge progress
        badge_progress = {
            "green_commuter": {
                "name": "Green Commuter",
                "description": "Master public transportation",
                "levels": [
                    {"requirement": 50, "description": "Use 50km of public transport", "reward": "20 bonus points"},
                    {"requirement": 100, "description": "Use 100km of public transport", "reward": "50 bonus points"},
                    {"requirement": 250, "description": "Use 250km of public transport", "reward": "100 bonus points"}
                ],
                "progress": transport_stats["public_transport_km"],
                "icon": "🚌",
                "category": "transport"
            },
            "cycling_enthusiast": {
                "name": "Cycling Enthusiast",
                "description": "Two-wheeled eco warrior",
                "levels": [
                    {"requirement": 25, "description": "Cycle 25km in total", "reward": "25 bonus points"},
                    {"requirement": 50, "description": "Cycle 50km in total", "reward": "50 bonus points"},
                    {"requirement": 100, "description": "Cycle 100km in total", "reward": "100 bonus points"}
                ],
                "progress": transport_stats["cycling_km"],
                "icon": "🚴",
                "category": "transport"
            },
            "walking_warrior": {
                "name": "Walking Warrior",
                "description": "Walking is the best transport",
                "levels": [
                    {"requirement": 10, "description": "Walk 10km in total", "reward": "15 bonus points"},
                    {"requirement": 25, "description": "Walk 25km in total", "reward": "40 bonus points"},
                    {"requirement": 50, "description": "Walk 50km in total", "reward": "75 bonus points"}
                ],
                "progress": transport_stats["walking_km"],
                "icon": "🚶",
                "category": "transport"
            },
            "explorer": {
                "name": "Explorer",
                "description": "Discoverer of hidden gems",
                "levels": [
                    {"requirement": 5, "description": "Discover 5 hidden gems", "reward": "30 bonus points"},
                    {"requirement": 10, "description": "Discover 10 hidden gems", "reward": "75 bonus points"},
                    {"requirement": 25, "description": "Discover 25 hidden gems", "reward": "150 bonus points"}
                ],
                "progress": transport_stats["gems_discovered"],
                "icon": "💎",
                "category": "discovery"
            },
            "eco_warrior": {
                "name": "Eco Warrior",
                "description": "Champion of sustainable travel",
                "levels": [
                    {"requirement": 500, "description": "Earn 500 eco points", "reward": "50 bonus points"},
                    {"requirement": 1000, "description": "Earn 1000 eco points", "reward": "100 bonus points"},
                    {"requirement": 2500, "description": "Earn 2500 eco points", "reward": "250 bonus points"}
                ],
                "progress": user_data["total_eco_points"],
                "icon": "🌱",
                "category": "achievement"
            },
            "community_contributor": {
                "name": "Community Contributor",
                "description": "Helping other travelers",
                "levels": [
                    {"requirement": 5, "description": "Submit 5 content pieces", "reward": "25 bonus points"},
                    {"requirement": 15, "description": "Submit 15 content pieces", "reward": "60 bonus points"},
                    {"requirement": 30, "description": "Submit 30 content pieces", "reward": "120 bonus points"}
                ],
                "progress": transport_stats["content_submissions"],
                "icon": "🤝",
                "category": "community"
            }
        }
        
        # Calculate progress percentages and completion status
        for badge_type, badge_info in badge_progress.items():
            current_progress = badge_info["progress"]
            
            # Determine current level and progress
            current_badge_level = 0
            next_level_requirement = badge_info["levels"][0]["requirement"]
            
            for i, level in enumerate(badge_info["levels"]):
                if current_progress >= level["requirement"]:
                    current_badge_level = i + 1
                    if i + 1 < len(badge_info["levels"]):
                        next_level_requirement = badge_info["levels"][i + 1]["requirement"]
                    else:
                        next_level_requirement = level["requirement"]
                else:
                    next_level_requirement = level["requirement"]
                    break
            
            badge_info.update({
                "current_level": current_badge_level,
                "next_level_requirement": next_level_requirement,
                "progress_to_next": min(current_progress, next_level_requirement),
                "percentage": min((current_progress / next_level_requirement) * 100, 100),
                "completed_levels": current_badge_level,
                "total_levels": len(badge_info["levels"]),
                "is_max_level": current_badge_level >= len(badge_info["levels"])
            })
        
        # Calculate next level requirements for user level
        current_level = user_data["level"]
        current_points = user_data["total_eco_points"]
        next_level_requirement = get_next_level_points(current_level)
        points_to_next_level = max(0, next_level_requirement - current_points)
        
        return {
            "success": True,
            "user_id": user_id,
            "username": user_data["username"],
            "current_level": current_level,
            "current_points": current_points,
            "next_level_points": next_level_requirement,
            "points_to_next_level": points_to_next_level,
            "level_progress_percentage": round(((current_points - get_next_level_points(current_level - 1)) / 
                                              (next_level_requirement - get_next_level_points(current_level - 1))) * 100, 1) if current_level > 1 else round((current_points / next_level_requirement) * 100, 1),
            "transport_statistics": transport_stats,
            "badge_progress": badge_progress,
            "achievements_summary": {
                "total_badge_types": len(badge_progress),
                "completed_badge_levels": sum(badge["completed_levels"] for badge in badge_progress.values()),
                "total_possible_levels": sum(badge["total_levels"] for badge in badge_progress.values()),
                "completion_percentage": round((sum(badge["completed_levels"] for badge in badge_progress.values()) / 
                                              sum(badge["total_levels"] for badge in badge_progress.values())) * 100, 1)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user achievements: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting user achievements: {str(e)}")

@router.get("/weekly-challenge")
async def get_weekly_challenge(
    user_id: int = Query(1, description="User ID")
):
    """Get current weekly challenge progress"""
    try:
        if user_id not in MOCK_USERS:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Calculate week boundaries
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        days_remaining = (week_end - today).days + 1
        
        # Mock weekly progress calculation
        user_rewards = MOCK_REWARDS.get(user_id, [])
        
        # Simulate weekly activity (in real app, filter by date)
        weekly_points = sum(r["points"] for r in user_rewards[-3:])  # Mock: last 3 activities
        weekly_distance = sum(r.get("distance_km", 0) for r in user_rewards[-3:])
        weekly_co2_saved = sum(r.get("co2_saved", 0) for r in user_rewards[-3:])
        
        # Define weekly challenges
        challenges = {
            "eco_points_challenge": WeeklyChallenge(
                name="Weekly Eco Points Master",
                description="Earn 150 eco points this week through sustainable actions",
                target=150,
                progress=weekly_points,
                completed=weekly_points >= 150,
                percentage=min((weekly_points / 150) * 100, 100),
                reward="🏆 75 bonus points + Weekly Champion badge",
                days_remaining=days_remaining
            ),
            "green_distance_challenge": WeeklyChallenge(
                name="Sustainable Transportation",
                description="Travel 20km using eco-friendly transport methods",
                target=20,
                progress=round(weekly_distance, 1),
                completed=weekly_distance >= 20,
                percentage=min((weekly_distance / 20) * 100, 100),
                reward="🌱 Green Distance Badge + 50 bonus points",
                days_remaining=days_remaining
            ),
            "carbon_saver_challenge": WeeklyChallenge(
                name="Carbon Footprint Hero",
                description="Save 5kg of CO2 through sustainable choices",
                target=5,
                progress=round(weekly_co2_saved, 1),
                completed=weekly_co2_saved >= 5,
                percentage=min((weekly_co2_saved / 5) * 100, 100),
                reward="🌍 Carbon Hero Badge + 60 bonus points",
                days_remaining=days_remaining
            ),
            "daily_streak_challenge": WeeklyChallenge(
                name="Consistency Champion",
                description="Log sustainable activities for 5 consecutive days",
                target=5,
                progress=MOCK_USERS[user_id].get("streak_days", 0),
                completed=MOCK_USERS[user_id].get("streak_days", 0) >= 5,
                percentage=min((MOCK_USERS[user_id].get("streak_days", 0) / 5) * 100, 100),
                reward="⚡ Consistency Master + 100 bonus points",
                days_remaining=days_remaining
            )
        }
        
        # Calculate summary statistics
        total_challenges = len(challenges)
        completed_challenges = sum(1 for c in challenges.values() if c.completed)
        available_bonus_points = sum([75, 50, 60, 100][i] for i, c in enumerate(challenges.values()) if c.completed)
        
        return {
            "success": True,
            "user_id": user_id,
            "week_period": {
                "start": week_start.strftime("%Y-%m-%d"),
                "end": week_end.strftime("%Y-%m-%d"),
                "days_remaining": days_remaining,
                "week_number": week_start.isocalendar()[1]
            },
            "challenges": {key: challenge.dict() for key, challenge in challenges.items()},
            "progress_summary": {
                "total_challenges": total_challenges,
                "completed_challenges": completed_challenges,
                "completion_percentage": round((completed_challenges / total_challenges) * 100, 1),
                "weekly_points_earned": weekly_points,
                "weekly_distance_covered": round(weekly_distance, 1),
                "weekly_co2_saved": round(weekly_co2_saved, 1),
                "current_streak": MOCK_USERS[user_id].get("streak_days", 0)
            },
            "rewards_summary": {
                "bonus_points_available": available_bonus_points,
                "badges_available": completed_challenges,
                "total_potential_bonus": 285  # Sum of all possible bonus points
            },
            "next_reset": (week_start + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting weekly challenge: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting weekly challenge: {str(e)}")

@router.get("/badges")
async def get_available_badges():
    """Get comprehensive list of available badges"""
    try:
        badge_definitions = {
            "green_commuter": {
                "name": "Green Commuter",
                "description": "Master of public transportation",
                "levels": [
                    {"level": 1, "requirement": "50km public transport", "points_reward": 20, "co2_impact": "12kg saved"},
                    {"level": 2, "requirement": "100km public transport", "points_reward": 50, "co2_impact": "25kg saved"},
                    {"level": 3, "requirement": "250km public transport", "points_reward": 100, "co2_impact": "65kg saved"}
                ],
                "icon": "🚌",
                "category": "Transport",
                "rarity": "Common",
                "tips": ["Use buses and trains instead of cars", "Plan routes using public transport apps"]
            },
            "cycling_enthusiast": {
                "name": "Cycling Enthusiast",
                "description": "Two-wheeled eco warrior",
                "levels": [
                    {"level": 1, "requirement": "25km cycling", "points_reward": 25, "co2_impact": "6kg saved"},
                    {"level": 2, "requirement": "50km cycling", "points_reward": 50, "co2_impact": "12kg saved"},
                    {"level": 3, "requirement": "100km cycling", "points_reward": 100, "co2_impact": "25kg saved"}
                ],
                "icon": "🚴",
                "category": "Transport",
                "rarity": "Common",
                "tips": ["Use bike-sharing services", "Cycle for short-distance trips"]
            },
            "walking_warrior": {
                "name": "Walking Warrior",
                "description": "Walking is the ultimate eco transport",
                "levels": [
                    {"level": 1, "requirement": "10km walking", "points_reward": 15, "co2_impact": "2.5kg saved"},
                    {"level": 2, "requirement": "25km walking", "points_reward": 40, "co2_impact": "6kg saved"},
                    {"level": 3, "requirement": "50km walking", "points_reward": 75, "co2_impact": "12kg saved"}
                ],
                "icon": "🚶",
                "category": "Transport",
                "rarity": "Common",
                "tips": ["Walk for trips under 2km", "Use walking for sightseeing"]
            },
            "explorer": {
                "name": "Hidden Gem Explorer",
                "description": "Master discoverer of secret places",
                "levels": [
                    {"level": 1, "requirement": "5 hidden gems", "points_reward": 30, "co2_impact": "Local discovery"},
                    {"level": 2, "requirement": "10 hidden gems", "points_reward": 75, "co2_impact": "Community impact"},
                    {"level": 3, "requirement": "25 hidden gems", "points_reward": 150, "co2_impact": "Explorer legend"}
                ],
                "icon": "💎",
                "category": "Discovery",
                "rarity": "Rare",
                "tips": ["Explore local neighborhoods", "Share unique finds with community"]
            },
            "eco_warrior": {
                "name": "Eco Warrior",
                "description": "Champion of sustainable travel",
                "levels": [
                    {"level": 1, "requirement": "500 eco points", "points_reward": 50, "co2_impact": "Significant impact"},
                    {"level": 2, "requirement": "1000 eco points", "points_reward": 100, "co2_impact": "Major impact"},
                    {"level": 3, "requirement": "2500 eco points", "points_reward": 250, "co2_impact": "Legendary impact"}
                ],
                "icon": "🌱",
                "category": "Achievement",
                "rarity": "Epic",
                "tips": ["Consistently choose eco-friendly options", "Inspire others through actions"]
            },
            "community_contributor": {
                "name": "Community Hero",
                "description": "Helping fellow travelers",
                "levels": [
                    {"level": 1, "requirement": "5 contributions", "points_reward": 25, "co2_impact": "Community building"},
                    {"level": 2, "requirement": "15 contributions", "points_reward": 60, "co2_impact": "Strong community impact"},
                    {"level": 3, "requirement": "30 contributions", "points_reward": 120, "co2_impact": "Community leader"}
                ],
                "icon": "🤝",
                "category": "Community",
                "rarity": "Rare",
                "tips": ["Share travel tips and guides", "Help other travelers with recommendations"]
            }
        }
        
        # Calculate statistics
        total_badge_types = len(badge_definitions)
        total_levels = sum(len(badge["levels"]) for badge in badge_definitions.values())
        total_possible_points = sum(sum(level["points_reward"] for level in badge["levels"]) for badge in badge_definitions.values())
        
        # Group by category and rarity
        categories = {}
        rarities = {}
        
        for badge_type, badge_info in badge_definitions.items():
            category = badge_info["category"]
            rarity = badge_info["rarity"]
            
            if category not in categories:
                categories[category] = []
            categories[category].append(badge_type)
            
            if rarity not in rarities:
                rarities[rarity] = []
            rarities[rarity].append(badge_type)
        
        return {
            "success": True,
            "badges": badge_definitions,
            "statistics": {
                "total_badge_types": total_badge_types,
                "total_badge_levels": total_levels,
                "total_possible_points": total_possible_points,
                "categories": list(categories.keys()),
                "rarities": list(rarities.keys())
            },
            "badges_by_category": categories,
            "badges_by_rarity": rarities,
            "earning_strategy": {
                "beginner_focus": ["green_commuter", "walking_warrior"],
                "intermediate_goals": ["cycling_enthusiast", "explorer"],
                "advanced_challenges": ["eco_warrior", "community_contributor"]
            },
            "pro_tips": [
                "🚌 Start with public transport for easy early points",
                "🚴 Combine cycling with sightseeing for double benefits",
                "🚶 Walk short distances to build walking warrior status",
                "💎 Explore off-the-beaten-path locations for gems",
                "🌱 Consistency is key for eco warrior progression",
                "🤝 Share your experiences to help the community"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting badges: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting badges: {str(e)}")

@router.post("/claim-reward")
async def claim_achievement_reward(request: RewardClaimRequest):
    """Claim reward for completed achievement"""
    try:
        user_id = request.user_id
        achievement_type = request.achievement_type
        achievement_level = request.achievement_level
        
        if user_id not in MOCK_USERS:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Define reward amounts
        reward_amounts = {
            "green_commuter": [20, 50, 100],
            "cycling_enthusiast": [25, 50, 100],
            "walking_warrior": [15, 40, 75],
            "explorer": [30, 75, 150],
            "eco_warrior": [50, 100, 250],
            "community_contributor": [25, 60, 120]
        }
        
        if achievement_level > len(reward_amounts[achievement_type]):
            raise HTTPException(status_code=400, detail=f"Invalid achievement level for {achievement_type}")
        
        reward_points = reward_amounts[achievement_type][achievement_level - 1]
        
        # Update user points (in real app, update database)
        user_data = MOCK_USERS[user_id]
        old_points = user_data["total_eco_points"]
        new_points = old_points + reward_points
        user_data["total_eco_points"] = new_points
        
        # Check if level up occurred
        old_level = get_user_level(old_points)
        new_level = get_user_level(new_points)
        level_up = new_level > old_level
        
        if level_up:
            user_data["level"] = new_level
        
        # Add badge to user's collection (if not already present)
        user_badges = MOCK_BADGES.get(user_id, [])
        badge_exists = any(
            badge["badge_name"] == achievement_type and badge["badge_level"] >= achievement_level
            for badge in user_badges
        )
        
        if not badge_exists:
            new_badge = {
                "id": len(user_badges) + 1,
                "user_id": user_id,
                "badge_name": achievement_type,
                "badge_level": achievement_level,
                "earned_at": datetime.now().isoformat(),
                "badge_description": f"{achievement_type.replace('_', ' ').title()} - Level {achievement_level}",
                "icon": {"green_commuter": "🚌", "cycling_enthusiast": "🚴", "walking_warrior": "🚶",
                        "explorer": "💎", "eco_warrior": "🌱", "community_contributor": "🤝"}[achievement_type]
            }
            user_badges.append(new_badge)
            MOCK_BADGES[user_id] = user_badges
        
        # Send real-time notification if user is connected
        if user_id in active_connections:
            try:
                notification_data = {
                    "type": "achievement_claimed",
                    "achievement_type": achievement_type,
                    "achievement_level": achievement_level,
                    "reward_points": reward_points,
                    "level_up": level_up,
                    "new_level": new_level if level_up else None,
                    "message": f"🎉 Achievement unlocked: {achievement_type.replace('_', ' ').title()} Level {achievement_level}!",
                    "timestamp": datetime.now().isoformat()
                }
                await active_connections[user_id].send_text(json.dumps(notification_data))
            except Exception as e:
                logger.warning(f"Failed to send real-time notification: {e}")
        
        response = {
            "success": True,
            "user_id": user_id,
            "achievement_type": achievement_type,
            "achievement_level": achievement_level,
            "reward_points": reward_points,
            "old_total_points": old_points,
            "new_total_points": new_points,
            "level_up": level_up,
            "message": f"🎉 Congratulations! You earned {reward_points} bonus points!"
        }
        
        if level_up:
            response["new_level"] = new_level
            response["level_up_bonus"] = 25  # Bonus points for leveling up
            response["message"] += f" 🆙 Level up to {new_level}!"
            user_data["total_eco_points"] += 25  # Add level up bonus
            response["new_total_points"] += 25
        
        response["claimed_at"] = datetime.now().isoformat()
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error claiming reward: {e}")
        raise HTTPException(status_code=500, detail=f"Error claiming reward: {str(e)}")

# ✅ WebSocket endpoint for real-time notifications
@router.websocket("/live-updates/{user_id}")
async def websocket_rewards(websocket: WebSocket, user_id: int):
    """Real-time reward notifications via WebSocket"""
    await websocket.accept()
    active_connections[user_id] = websocket
    
    logger.info(f"WebSocket connected for user {user_id}")
    
    try:
        # Send welcome message with user stats
        user_data = MOCK_USERS.get(user_id, {})
        welcome_message = {
            "type": "connection_established",
            "message": "🔔 Real-time rewards connected!",
            "user_id": user_id,
            "current_points": user_data.get("total_eco_points", 0),
            "current_level": user_data.get("level", 1),
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        # Listen for reward events
        while True:
            reward_event = await wait_for_user_reward(user_id)
            
            if reward_event:
                # Update user data (mock)
                if user_id in MOCK_USERS:
                    MOCK_USERS[user_id]["total_eco_points"] += reward_event["points"]
                    MOCK_USERS[user_id]["level"] = get_user_level(MOCK_USERS[user_id]["total_eco_points"])
                
                notification = {
                    "type": "reward_earned",
                    "points": reward_event["points"],
                    "action": reward_event["action_type"],
                    "co2_saved": reward_event.get("co2_saved", 0),
                    "message": f"🌱 +{reward_event['points']} eco points for {reward_event['action_type'].replace('_', ' ')}!",
                    "timestamp": reward_event["timestamp"],
                    "user_id": user_id,
                    "new_total": MOCK_USERS.get(user_id, {}).get("total_eco_points", 0),
                    "current_level": MOCK_USERS.get(user_id, {}).get("level", 1)
                }
                
                await websocket.send_text(json.dumps(notification))
                logger.info(f"Sent reward notification to user {user_id}: {reward_event['points']} points for {reward_event['action_type']}")
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        if user_id in active_connections:
            del active_connections[user_id]

@router.get("/health")
async def rewards_service_health():
    """Comprehensive rewards service health check"""
    try:
        # Calculate system statistics
        total_points_in_system = sum(user["total_eco_points"] for user in MOCK_USERS.values())
        total_co2_saved = sum(user["carbon_footprint_saved"] for user in MOCK_USERS.values())
        total_badges_earned = sum(len(badges) for badges in MOCK_BADGES.values())
        total_gems_discovered = sum(len([gem for gem in gems if gem.get("is_verified", False)]) for gems in MOCK_GEMS.values())
        
        return {
            "success": True,
            "service": "rewards_gamification",
            "status": "healthy",
            "version": "2.0.0",
            "features": {
                "leaderboard": True,
                "user_statistics": True,
                "achievement_tracking": True,
                "badge_system": True,
                "weekly_challenges": True,
                "real_time_notifications": True,
                "reward_claiming": True,
                "level_system": True,
                "websocket_support": True
            },
            "system_statistics": {
                "total_users": len(MOCK_USERS),
                "active_websocket_connections": len(active_connections),
                "total_eco_points_awarded": total_points_in_system,
                "total_co2_saved_kg": round(total_co2_saved, 2),
                "total_badges_earned": total_badges_earned,
                "total_verified_gems": total_gems_discovered,
                "badge_types_available": 6,
                "total_achievement_levels": 18,
                "challenge_types": 4
            },
            "gamification_elements": {
                "points_system": "Eco points for sustainable actions",
                "level_system": "Progressive leveling based on points",
                "badge_system": "Multi-level badges with 3 tiers each",
                "weekly_challenges": "4 different weekly challenge types",
                "leaderboards": "Global rankings with time period filters",
                "real_time_updates": "WebSocket notifications for instant feedback",
                "achievement_rewards": "Bonus points for completing milestones",
                "streak_tracking": "Daily consistency rewards"
            },
            "performance_metrics": {
                "average_user_points": round(total_points_in_system / max(1, len(MOCK_USERS)), 1),
                "average_co2_saved_per_user": round(total_co2_saved / max(1, len(MOCK_USERS)), 2),
                "badge_completion_rate": round((total_badges_earned / (len(MOCK_USERS) * 18)) * 100, 1),
                "websocket_uptime": "99.9%"
            },
            "supported_actions": [action.value for action in ActionType],
            "supported_badges": [badge.value for badge in BadgeType],
            "database_mode": "mock_data" if not DATABASE_AVAILABLE else "database_available",
            "last_health_check": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "success": False,
            "service": "rewards_gamification",
            "status": "degraded",
            "error": str(e),
            "last_health_check": datetime.now().isoformat()
        }
