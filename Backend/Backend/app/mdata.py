# app/mdata.py
"""Migration script for adding gamification features to the database."""

from database import engine, Base, SessionLocal
from sqlalchemy import text
import os

def check_database():
    """Check if database exists."""
    return os.path.exists("hackathon_travel.db")

def migrate_tables():
    """Add gamification columns to existing tables."""
    db = SessionLocal()
    
    try:
        print("🔄 Migrating existing tables...")
        
        # User table enhancements
        user_columns = [
            "ALTER TABLE users ADD COLUMN total_eco_points INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1", 
            "ALTER TABLE users ADD COLUMN carbon_footprint_saved REAL DEFAULT 0.0"
        ]
        
        # Trip table enhancements
        trip_columns = [
            "ALTER TABLE trips ADD COLUMN eco_mode_enabled BOOLEAN DEFAULT 0",
            "ALTER TABLE trips ADD COLUMN transport_preference TEXT DEFAULT 'mixed'"
        ]
        
        all_columns = user_columns + trip_columns
        
        for command in all_columns:
            try:
                db.execute(text(command))
                print(f"✅ Added column: {command.split('ADD COLUMN')[1].split()[0]}")
            except Exception as e:
                print(f"⚠️  Column exists: {command.split('ADD COLUMN')[1].split()[0]}")
        
        db.commit()
        print("✅ Table migration complete!")
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        db.rollback()
    finally:
        db.close()

def create_tables():
    """Create new gamification tables."""
    try:
        print("🔄 Creating gamification tables...")
        Base.metadata.create_all(bind=engine)
        
        tables = [
            "eco_rewards", "hidden_gems", "eco_actions", 
            "user_badges", "location_tracking", "eco_challenges"
        ]
        
        print("✅ Created tables:")
        for table in tables:
            print(f"   - {table}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Run migration."""
    print("🚀 Starting migration...")
