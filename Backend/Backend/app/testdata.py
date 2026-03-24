# app/testdata.py
"""Test gamification database features."""

from database import SessionLocal, User, EcoReward, HiddenGem, UserBadge
from datetime import datetime

def create_user():
    """Create sample user."""
    db = SessionLocal()
    
    try:
        # Check existing
        user = db.query(User).filter(User.email == "test@eco.com").first()
        if user:
            print(f"👤 Found user: {user.name}")
            return user
        
        # Create new
        user = User(
            email="test@eco.com",
            name="Eco Tester",
            hashed_password="test_hash",
            total_eco_points=0,
            level=1,
            carbon_footprint_saved=0.0
        )
        
        db.add(user)
        db.commit()
        print("✅ Created test user")
        return user
        
    except Exception as e:
        print(f"❌ User error: {e}")
        return None
    finally:
        db.close()

def test_rewards():
    """Test eco rewards."""
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.email == "test@eco.com").first()
        if not user:
            print("❌ No user found")
            return
        
        print(f"\n🎯 Testing rewards for {user.name}")
        
        # Create reward
        reward = EcoReward(
            user_id=user.id,
            points=30,
            action_type="transport_cycling",
            transport_mode="cycling",
            distance_km=6.5,
            co2_saved=1.4
        )
        
        db.add(reward)
        
        # Update user
        user.total_eco_points += 30
        user.carbon_footprint_saved += 1.4
        
        db.commit()
        
        print("✅ Reward created")
        print(f"   Points: {user.total_eco_points}")
        print(f"   CO2 saved: {user.carbon_footprint_saved} kg")
        
    except Exception as e:
        print(f"❌ Reward error: {e}")
    finally:
        db.close()

def test_gems():
    """Test hidden gems."""
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.email == "test@eco.com").first()
        if not user:
            return
        
        print(f"\n💎 Testing hidden gems")
        
        gem = HiddenGem(
            name="Cool Cafe",
            description="Hidden gem with great coffee",
            category="cafe",
            lat=40.7128,
            lng=-74.0060,
            created_by_user_id=user.id,
            is_verified=True
        )
        
        db.add(gem)
        db.commit()
        
        print("✅ Hidden gem created")
        print(f"   Name: {gem.name}")
        print(f"   Category: {gem.category}")
        
    except Exception as e:
        print(f"❌ Gem error: {e}")
    finally:
        db.close()

def test_badges():
    """Test user badges."""
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.email == "test@eco.com").first()
        if not user:
            return
        
        print(f"\n🏆 Testing badges")
        
        badge = UserBadge(
            user_id=user.id,
            badge_name="first_ride",
            badge_level=1,
            badge_description="First eco-friendly ride"
        )
        
        db.add(badge)
        db.commit()
        
        print("✅ Badge awarded")
        print(f"   Badge: {badge.badge_name}")
        
    except Exception as e:
        print(f"❌ Badge error: {e}")
    finally:
        db.close()

def show_stats():
    """Show final stats."""
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.email == "test@eco.com").first()
        if not user:
            return
        
        rewards = db.query(EcoReward).filter(EcoReward.user_id == user.id).count()
        gems = db.query(HiddenGem).filter(HiddenGem.created_by_user_id == user.id).count()
        badges = db.query(UserBadge).filter(UserBadge.user_id == user.id).count()
        
        print(f"\n📊 Final Stats for {user.name}")
        print(f"   🌱 Eco Points: {user.total_eco_points}")
        print(f"   ⭐ Level: {user.level}")
        print(f"   🌍 CO2 Saved: {round(user.carbon_footprint_saved, 2)} kg")
        print(f"   🏆 Rewards: {rewards}")
        print(f"   💎 Gems: {gems}")
        print(f"   🥇 Badges: {badges}")
        
    except Exception as e:
        print(f"❌ Stats error: {e}")
    finally:
        db.close()

def main():
    """Run tests."""
    print("🧪 Testing Gamification")
    print("=" * 30)
    
    # Create user
    create_user()
    
    # Run tests
    test_rewards()
    test_gems()
    test_badges()
    
    # Show results
    show_stats()
    
    print("\n" + "=" * 30)
    print("✨ Tests complete!")

if __name__ == "__main__":
    main()
