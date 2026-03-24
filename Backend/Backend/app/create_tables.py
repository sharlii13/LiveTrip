# app/create_tables.py
"""Create new gamification tables."""

import sqlite3
import os

def create_gamification_tables():
    """Create all gamification tables directly in SQLite."""
    
    db_path = "hackathon_travel.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Creating gamification tables...")
        
        # Create eco_rewards table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS eco_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            points INTEGER,
            action_type VARCHAR(50),
            location_lat REAL,
            location_lng REAL,
            transport_mode VARCHAR(30),
            distance_km REAL,
            co2_saved REAL DEFAULT 0.0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_verified BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        print("✅ eco_rewards table created")
        
        # Create hidden_gems table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hidden_gems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100),
            description TEXT,
            category VARCHAR(50),
            lat REAL,
            lng REAL,
            discovery_points INTEGER DEFAULT 50,
            created_by_user_id INTEGER,
            is_verified BOOLEAN DEFAULT 0,
            photo_urls TEXT,
            address VARCHAR(200),
            opening_hours VARCHAR(100),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            verified_at DATETIME,
            FOREIGN KEY (created_by_user_id) REFERENCES users (id)
        )
        """)
        print("✅ hidden_gems table created")
        
        # Create eco_actions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS eco_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type VARCHAR(50),
            points_earned INTEGER,
            location_data VARCHAR(200),
            proof_image_url VARCHAR(500),
            description TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        print("✅ eco_actions table created")
        
        # Create user_badges table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            badge_name VARCHAR(50),
            badge_level INTEGER DEFAULT 1,
            earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            badge_description VARCHAR(200),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        print("✅ user_badges table created")
        
        conn.commit()
        conn.close()
        
        print("\n✨ All gamification tables created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Creating Gamification Tables")
    print("=" * 40)
    
    if create_gamification_tables():
        print("🎮 Database is ready for gamification!")
    else:
        print("❌ Table creation failed!")
