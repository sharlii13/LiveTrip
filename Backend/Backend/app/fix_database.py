# app/fix_database.py
"""Direct database fix for gamification columns."""

import sqlite3
import os

def fix_database():
    """Manually add missing columns to existing database."""
    
    db_path = "hackathon_travel.db"
    
    if not os.path.exists(db_path):
        print("❌ Database not found!")
        return False
    
    try:
        # Connect directly to SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Adding missing columns to users table...")
        
        # Add columns one by one
        columns_to_add = [
            "ALTER TABLE users ADD COLUMN total_eco_points INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1",
            "ALTER TABLE users ADD COLUMN carbon_footprint_saved REAL DEFAULT 0.0"
        ]
        
        for command in columns_to_add:
            try:
                cursor.execute(command)
                column_name = command.split()[-3]
                print(f"✅ Added column: {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    column_name = command.split()[-3]
                    print(f"⚠️  Column {column_name} already exists")
                else:
                    print(f"❌ Error: {e}")
        
        # Add trip table columns
        print("🔄 Adding columns to trips table...")
        trip_columns = [
            "ALTER TABLE trips ADD COLUMN eco_mode_enabled BOOLEAN DEFAULT 0",
            "ALTER TABLE trips ADD COLUMN transport_preference TEXT DEFAULT 'mixed'"
        ]
        
        for command in trip_columns:
            try:
                cursor.execute(command)
                column_name = command.split()[-3]
                print(f"✅ Added column: {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    column_name = command.split()[-3]
                    print(f"⚠️  Column {column_name} already exists")
                else:
                    print(f"❌ Error: {e}")
        
        # Commit changes
        conn.commit()
        
        # Verify the changes
        print("\n🔍 Verifying users table structure:")
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        required_columns = ['total_eco_points', 'level', 'carbon_footprint_saved']
        existing_columns = [col[1] for col in columns]
        
        for req_col in required_columns:
            if req_col in existing_columns:
                print(f"✅ {req_col} - exists")
            else:
                print(f"❌ {req_col} - missing")
        
        conn.close()
        print("\n✨ Database columns updated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating database: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Fixing Database Structure")
    print("=" * 40)
    
    if fix_database():
        print("🎮 Now run: python testdata.py")
    else:
        print("❌ Database fix failed!")
