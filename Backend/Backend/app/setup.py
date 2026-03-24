# setup.py - Run this to create initial data
from database import SessionLocal, User, engine, Base
import asyncio

def create_default_user():
    """Create a default user for testing"""
    db = SessionLocal()
    try:
        # Check if user exists
        existing_user = db.query(User).filter(User.id == 1).first()
        if not existing_user:
            default_user = User(
                id=1,
                name="Test User",
                email="test@example.com",
                hashed_password="password123"  # Hash in production!
            )
            db.add(default_user)
            db.commit()
            print("✅ Default user created!")
        else:
            print("✅ Default user already exists!")
    except Exception as e:
        print(f"❌ Error creating default user: {e}")
    finally:
        db.close()

def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    print("🚀 Setting up Travel Planning API...")
    create_tables()
    create_default_user()
    print("✨ Setup complete! Run: uvicorn main:app --reload")