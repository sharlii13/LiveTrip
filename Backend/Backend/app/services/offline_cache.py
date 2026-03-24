# services/offline_cache.py
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

class OfflineCacheService:
    def __init__(self):
        self.cache_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'user_itineraries')
        self.ensure_cache_directory()
    
    def ensure_cache_directory(self):
        """Create cache directory if it doesn't exist"""
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def save_itinerary_to_cache(self, user_id: int, trip_id: int, itinerary_data: Dict) -> str:
        """Save complete itinerary to local JSON file for offline access"""
        try:
            # Create filename: user_1_trip_5_2025-09-24.json
            timestamp = datetime.now().strftime("%Y-%m-%d")
            filename = f"user_{user_id}_trip_{trip_id}_{timestamp}.json"
            filepath = os.path.join(self.cache_dir, filename)
            
            # Prepare data for offline storage
            offline_data = {
                "user_id": user_id,
                "trip_id": trip_id,
                "cached_at": datetime.now().isoformat(),
                "destination": itinerary_data.get("destination"),
                "start_date": itinerary_data.get("start_date"),
                "end_date": itinerary_data.get("end_date"),
                "total_days": itinerary_data.get("total_days"),
                "mood": itinerary_data.get("mood"),
                "full_itinerary": itinerary_data.get("itinerary", {}),
                "weather_info": itinerary_data.get("general_weather", {}),
                "local_events": itinerary_data.get("local_events", []),
                "recommended_places": itinerary_data.get("recommended_places", []),
                "data_sources": itinerary_data.get("data_sources", {}),
                "offline_mode": True
            }
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(offline_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Itinerary cached offline: {filename}")
            return filepath
            
        except Exception as e:
            print(f"❌ Failed to cache itinerary: {e}")
            return None
    
    def load_cached_itinerary(self, user_id: int, trip_id: int) -> Optional[Dict]:
        """Load itinerary from cache for offline viewing"""
        try:
            # Find the latest cached file for this user and trip
            pattern = f"user_{user_id}_trip_{trip_id}_"
            cached_files = [f for f in os.listdir(self.cache_dir) if f.startswith(pattern)]
            
            if not cached_files:
                return None
            
            # Get the most recent file
            latest_file = sorted(cached_files)[-1]
            filepath = os.path.join(self.cache_dir, latest_file)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            print(f"✅ Loaded cached itinerary: {latest_file}")
            return cached_data
            
        except Exception as e:
            print(f"❌ Failed to load cached itinerary: {e}")
            return None
    
    def get_user_cached_trips(self, user_id: int) -> List[Dict]:
        """Get all cached trips for a user"""
        try:
            pattern = f"user_{user_id}_trip_"
            cached_files = [f for f in os.listdir(self.cache_dir) if f.startswith(pattern)]
            
            trips = []
            for filename in cached_files:
                try:
                    filepath = os.path.join(self.cache_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    trips.append({
                        "trip_id": data.get("trip_id"),
                        "destination": data.get("destination"),
                        "start_date": data.get("start_date"),
                        "end_date": data.get("end_date"),
                        "cached_at": data.get("cached_at"),
                        "filename": filename
                    })
                except Exception as e:
                    print(f"❌ Error reading {filename}: {e}")
                    continue
            
            return sorted(trips, key=lambda x: x.get("cached_at", ""), reverse=True)
            
        except Exception as e:
            print(f"❌ Failed to get cached trips: {e}")
            return []
    
    def cleanup_old_cache(self, days_to_keep: int = 30):
        """Clean up cache files older than specified days"""
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            files_deleted = 0
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                
                # Check file modification time
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_time < cutoff_date:
                    os.remove(filepath)
                    files_deleted += 1
            
            print(f"🧹 Cleaned up {files_deleted} old cache files")
            return files_deleted
            
        except Exception as e:
            print(f"❌ Cache cleanup failed: {e}")
            return 0
    
    def export_user_data(self, user_id: int) -> Optional[str]:
        """Export all user's itinerary data to a single JSON file"""
        try:
            user_trips = self.get_user_cached_trips(user_id)
            
            if not user_trips:
                return None
            
            export_data = {
                "user_id": user_id,
                "export_date": datetime.now().isoformat(),
                "total_trips": len(user_trips),
                "trips": []
            }
            
            for trip_info in user_trips:
                cached_data = self.load_cached_itinerary(user_id, trip_info["trip_id"])
                if cached_data:
                    export_data["trips"].append(cached_data)
            
            # Save export file
            export_filename = f"user_{user_id}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            export_path = os.path.join(self.cache_dir, export_filename)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"📁 Exported user data: {export_filename}")
            return export_path
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return None

# Service instance
offline_cache = OfflineCacheService()