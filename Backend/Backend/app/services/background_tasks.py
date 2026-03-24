# services/background_tasks.py
from celery import Celery
import asyncio
from typing import List, Dict, Optional
import random
import logging
from datetime import datetime

# Import your database models and session
from ..database import SessionLocal, User, EcoReward, HiddenGem, EcoAction
from ..models.rewards import ActionType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Configure Celery (optional for hackathon, can be disabled)
celery_app = Celery(
    'travel_rewards',
    broker='redis://localhost:6379/0',  # Use Redis as broker
    backend='redis://localhost:6379/0'   # Use Redis as result backend
)

# ✅ Mock ML and AI services for hackathon
class MLService:
    """Mock ML service for transport mode prediction"""
    
    @staticmethod
    def predict_transport_mode(speed: float, accelerometer_data: Dict) -> str:
        """
        Mock transport mode prediction based on speed
        In production, this would use actual ML models
        """
        if speed is None:
            return "unknown"
        
        # Simple speed-based classification
        if speed < 2:  # km/h
            return "walking"
        elif speed < 15:  # km/h
            return "cycling" 
        elif speed < 30:  # km/h
            return "public_transport"
        else:
            return "car"  # Not eco-friendly

class AIService:
    """Mock AI service for location verification"""
    
    @staticmethod
    def verify_location_authenticity(photos: List[str], description: str, coordinates: tuple) -> bool:
        """
        Mock AI verification of hidden gem submissions
        In production, this would use computer vision and NLP
        """
        # Simple mock validation
        if not description or len(description) < 10:
            return False
        
        # Mock photo validation
        if photos and len(photos) > 0:
            return True
        
        # Random verification for demo purposes
        return random.choice([True, True, False])  # 66% success rate

# ✅ Create service instances
ml_service = MLService()
ai_service = AIService()

# ✅ Database helper functions
def get_pending_gem_submissions() -> List[HiddenGem]:
    """Get all pending hidden gem submissions"""
    db = SessionLocal()
    try:
        pending_gems = db.query(HiddenGem).filter(
            HiddenGem.is_verified == False
        ).all()
        return pending_gems
    except Exception as e:
        logger.error(f"Error fetching pending gems: {e}")
        return []
    finally:
        db.close()

def award_transport_points(user_id: int, transport_mode: str) -> int:
    """Award points for eco-friendly transport"""
    db = SessionLocal()
    try:
        # Point values for different transport modes
        points_map = {
            "walking": 15,
            "cycling": 25,
            "public_transport": 20
        }
        
        points = points_map.get(transport_mode, 0)
        
        if points > 0:
            # Create eco reward
            reward = EcoReward(
                user_id=user_id,
                points=points,
                action_type=f"transport_{transport_mode}",
                transport_mode=transport_mode,
                timestamp=datetime.utcnow()
            )
            db.add(reward)
            
            # Update user total points
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.total_eco_points += points
            
            db.commit()
            logger.info(f"Awarded {points} points to user {user_id} for {transport_mode}")
            return points
        
        return 0
    except Exception as e:
        logger.error(f"Error awarding transport points: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

def award_verification_bonus(user_id: int, bonus_points: int) -> bool:
    """Award bonus points for verified gem submission"""
    db = SessionLocal()
    try:
        # Create bonus eco action
        bonus_action = EcoAction(
            user_id=user_id,
            action_type="gem_verification_bonus",
            points_earned=bonus_points,
            timestamp=datetime.utcnow()
        )
        db.add(bonus_action)
        
        # Update user total points
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.total_eco_points += bonus_points
        
        db.commit()
        logger.info(f"Awarded {bonus_points} verification bonus to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error awarding verification bonus: {e}")
        db.rollback()
        return False
    finally:
        db.close()

# ✅ Fixed Celery tasks
@celery_app.task
def process_location_batch(location_updates: List[dict]):
    """Process multiple location updates for eco-transport detection"""
    logger.info(f"Processing batch of {len(location_updates)} location updates")
    
    processed_count = 0
    points_awarded = 0
    
    for update in location_updates:
        try:
            # Extract data with defaults
            speed = update.get('speed', 0)
            accelerometer_data = update.get('accelerometer_data', {})
            user_id = update.get('user_id')
            
            if not user_id:
                logger.warning("Skipping update without user_id")
                continue
            
            # Detect transport mode using ML model
            transport_mode = ml_service.predict_transport_mode(speed, accelerometer_data)
            
            # Award eco points if sustainable transport
            if transport_mode in ['walking', 'cycling', 'public_transport']:
                points = award_transport_points(user_id, transport_mode)
                points_awarded += points
                processed_count += 1
                
        except Exception as e:
            logger.error(f"Error processing location update: {e}")
            continue
    
    logger.info(f"Processed {processed_count} updates, awarded {points_awarded} points total")
    return {
        "processed": processed_count,
        "total_points_awarded": points_awarded,
        "total_updates": len(location_updates)
    }

@celery_app.task
def verify_hidden_gem_submissions():
    """Verify pending hidden gem submissions"""
    logger.info("Starting hidden gem verification process")
    
    pending_gems = get_pending_gem_submissions()
    
    if not pending_gems:
        logger.info("No pending gems to verify")
        return {"verified": 0, "rejected": 0, "total": 0}
    
    verified_count = 0
    rejected_count = 0
    
    db = SessionLocal()
    try:
        for gem in pending_gems:
            try:
                # Parse photos (assuming JSON string or comma-separated)
                photos = []
                if gem.photo_urls:
                    if gem.photo_urls.startswith('['):
                        import json
                        photos = json.loads(gem.photo_urls)
                    else:
                        photos = gem.photo_urls.split(',')
                
                # Use AI to verify location legitimacy
                is_valid = ai_service.verify_location_authenticity(
                    photos, gem.description, (gem.lat, gem.lng)
                )
                
                if is_valid:
                    gem.is_verified = True
                    gem.verified_at = datetime.utcnow()
                    verified_count += 1
                    
                    # Award bonus points to submitter
                    award_verification_bonus(gem.created_by_user_id, 25)
                    
                    logger.info(f"Verified gem: {gem.name} by user {gem.created_by_user_id}")
                else:
                    rejected_count += 1
                    logger.info(f"Rejected gem: {gem.name} - failed AI verification")
                
            except Exception as e:
                logger.error(f"Error verifying gem {gem.id}: {e}")
                rejected_count += 1
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error in verification process: {e}")
        db.rollback()
    finally:
        db.close()
    
    logger.info(f"Verification complete: {verified_count} verified, {rejected_count} rejected")
    return {
        "verified": verified_count,
        "rejected": rejected_count,
        "total": len(pending_gems)
    }

# ✅ Additional useful background tasks
@celery_app.task
def update_user_levels():
    """Update user levels based on accumulated points"""
    logger.info("Starting user level update process")
    
    db = SessionLocal()
    try:
        users = db.query(User).all()
        updated_count = 0
        
        for user in users:
            # Calculate new level (100 points per level)
            new_level = (user.total_eco_points // 100) + 1
            
            if new_level > user.level:
                old_level = user.level
                user.level = new_level
                updated_count += 1
                
                # Create level-up action
                level_action = EcoAction(
                    user_id=user.id,
                    action_type="level_up",
                    points_earned=10,  # Bonus for leveling up
                    description=f"Leveled up from {old_level} to {new_level}",
                    timestamp=datetime.utcnow()
                )
                db.add(level_action)
                
                # Add bonus points
                user.total_eco_points += 10
                
                logger.info(f"User {user.id} leveled up: {old_level} -> {new_level}")
        
        db.commit()
        logger.info(f"Updated {updated_count} user levels")
        return {"users_updated": updated_count}
        
    except Exception as e:
        logger.error(f"Error updating user levels: {e}")
        db.rollback()
        return {"users_updated": 0, "error": str(e)}
    finally:
        db.close()

@celery_app.task
def cleanup_old_location_data():
    """Clean up old location tracking data (keep last 30 days)"""
    logger.info("Starting location data cleanup")
    
    from datetime import timedelta
    from ..database import LocationTracking
    
    db = SessionLocal()
    try:
        # Delete location data older than 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        deleted_count = db.query(LocationTracking).filter(
            LocationTracking.timestamp < cutoff_date
        ).delete()
        
        db.commit()
        logger.info(f"Cleaned up {deleted_count} old location records")
        return {"deleted_records": deleted_count}
        
    except Exception as e:
        logger.error(f"Error cleaning location data: {e}")
        db.rollback()
        return {"deleted_records": 0, "error": str(e)}
    finally:
        db.close()

# ✅ Non-Celery versions (for development without Redis/Celery)
def process_location_batch_sync(location_updates: List[dict]) -> Dict:
    """Synchronous version for development without Celery"""
    return process_location_batch.apply(args=[location_updates]).result

def verify_hidden_gem_submissions_sync() -> Dict:
    """Synchronous version for development without Celery"""
    return verify_hidden_gem_submissions.apply().result

# ✅ Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # Beat schedule for periodic tasks
    beat_schedule={
        'verify-gems-every-hour': {
            'task': 'services.background_tasks.verify_hidden_gem_submissions',
            'schedule': 3600.0,  # Every hour
        },
        'update-levels-daily': {
            'task': 'services.background_tasks.update_user_levels', 
            'schedule': 86400.0,  # Every day
        },
        'cleanup-location-data-weekly': {
            'task': 'services.background_tasks.cleanup_old_location_data',
            'schedule': 604800.0,  # Every week
        },
    },
)

# ✅ For hackathon - disable Celery if Redis not available
CELERY_ENABLED = False  # Set to True if you have Redis running

if not CELERY_ENABLED:
    logger.info("Celery disabled for development - using synchronous processing")
