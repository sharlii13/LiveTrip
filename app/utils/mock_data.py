"""
Mock data utilities for testing the itinerary planning system.
Provides sample POIs and distance matrix data for Pune, India.
"""
from typing import List, Dict
from app.models.schemas import RawPOI, DistanceMatrix


# Sample POIs for Pune with realistic ratings, locations, and timings
MOCK_PUNE_POIS = [
    {
        "name": "Dagadusheth Halwai Ganpati Temple",
        "category": "temple",
        "lat": 18.5158,
        "lng": 73.8567,
        "rating": 4.6,
        "reviews": 12453,
        "open_time": "06:00",
        "close_time": "22:00"
    },
    {
        "name": "Kelkar Museum",
        "category": "museum", 
        "lat": 18.5089,
        "lng": 73.8553,
        "rating": 4.2,
        "reviews": 2847,
        "open_time": "10:00",
        "close_time": "17:30"
    },
    {
        "name": "Shaniwar Wada",
        "category": "historic",
        "lat": 18.5195,
        "lng": 73.8553,
        "rating": 4.1,
        "reviews": 8962,
        "open_time": "08:00", 
        "close_time": "18:30"
    },
    {
        "name": "Tulsi Baug Market",
        "category": "shopping",
        "lat": 18.5167,
        "lng": 73.8520,
        "rating": 3.9,
        "reviews": 3421,
        "open_time": "10:00",
        "close_time": "21:00"
    },
    {
        "name": "Osho International Meditation Resort",
        "category": "cultural",
        "lat": 18.5292,
        "lng": 73.8674,
        "rating": 4.3,
        "reviews": 1876,
        "open_time": "06:00",
        "close_time": "21:00"
    },
    {
        "name": "Empress Garden",
        "category": "park",
        "lat": 18.5314,
        "lng": 73.8446,
        "rating": 4.0,
        "reviews": 4563,
        "open_time": "06:00",
        "close_time": "20:00"
    },
    {
        "name": "Lal Mahal",
        "category": "historic",
        "lat": 18.5177,
        "lng": 73.8536,
        "rating": 3.8,
        "reviews": 1923,
        "open_time": "09:00",
        "close_time": "18:00"
    },
    {
        "name": "Pune University",
        "category": "cultural",
        "lat": 18.5089,
        "lng": 73.8067,
        "rating": 4.4,
        "reviews": 6543,
        "open_time": "08:00",
        "close_time": "17:00"
    },
    {
        "name": "German Bakery",
        "category": "food",
        "lat": 18.5292,
        "lng": 73.8674,
        "rating": 4.1,
        "reviews": 2187,
        "open_time": "08:00",
        "close_time": "23:00"
    },
    {
        "name": "Sinhagad Fort",
        "category": "historic",
        "lat": 18.3668,
        "lng": 73.7555,
        "rating": 4.5,
        "reviews": 15634,
        "open_time": "06:00",
        "close_time": "18:00"
    },
    {
        "name": "Koregaon Park",
        "category": "park", 
        "lat": 18.5367,
        "lng": 73.8956,
        "rating": 4.2,
        "reviews": 3421,
        "open_time": "05:00",
        "close_time": "22:00"
    },
    {
        "name": "FC Road Shopping",
        "category": "shopping",
        "lat": 18.5204,
        "lng": 73.8567,
        "rating": 4.0,
        "reviews": 2876,
        "open_time": "11:00",
        "close_time": "22:00"
    }
]


def get_mock_pois(city: str = "pune") -> List[RawPOI]:
    """
    Get mock POI data for testing.
    
    Args:
        city: City name (currently only supports 'pune')
        
    Returns:
        List of RawPOI objects
    """
    if city.lower() != "pune":
        # Return a subset for unknown cities
        return [RawPOI(**poi) for poi in MOCK_PUNE_POIS[:5]]
    
    return [RawPOI(**poi) for poi in MOCK_PUNE_POIS]


def get_mock_distance_matrix(locations: List[Dict[str, float]]) -> DistanceMatrix:
    """
    Generate a mock distance matrix for given locations.
    Uses simplified distance calculation based on coordinates.
    
    Args:
        locations: List of {lat, lng} dictionaries
        
    Returns:
        DistanceMatrix with travel times and distances
    """
    import math
    
    n = len(locations)
    durations = []
    distances = []
    
    for i in range(n):
        duration_row = []
        distance_row = []
        
        for j in range(n):
            if i == j:
                # Same location
                duration_row.append(0)
                distance_row.append(0)
            else:
                # Calculate approximate distance using Haversine formula
                lat1, lng1 = locations[i]["lat"], locations[i]["lng"]
                lat2, lng2 = locations[j]["lat"], locations[j]["lng"]
                
                # Convert to radians
                lat1_rad = math.radians(lat1)
                lat2_rad = math.radians(lat2)
                delta_lat = math.radians(lat2 - lat1)
                delta_lng = math.radians(lng2 - lng1)
                
                # Haversine formula
                a = (math.sin(delta_lat / 2) ** 2 + 
                     math.cos(lat1_rad) * math.cos(lat2_rad) * 
                     math.sin(delta_lng / 2) ** 2)
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                
                # Earth radius in kilometers
                earth_radius = 6371
                distance_km = earth_radius * c
                
                # Convert to meters
                distance_m = int(distance_km * 1000)
                
                # Estimate travel time (assuming average speed)
                # Driving: ~30 km/h in city, Walking: ~5 km/h
                avg_speed_kmh = 30  # Default to driving speed
                duration_min = int((distance_km / avg_speed_kmh) * 60)
                
                # Add some minimum time for very short distances
                duration_min = max(duration_min, 3)
                
                duration_row.append(duration_min)
                distance_row.append(distance_m)
        
        durations.append(duration_row)
        distances.append(distance_row)
    
    return DistanceMatrix(
        origins=locations,
        destinations=locations,
        durations=durations,
        distances=distances
    )


def get_predefined_distance_matrix() -> DistanceMatrix:
    """
    Get a predefined distance matrix for common Pune locations.
    This provides more realistic travel times than the calculated version.
    
    Returns:
        DistanceMatrix with realistic travel times between key Pune POIs
    """
    # Key locations: Hotel (Koregaon Park), Temple, Museum, Shaniwar Wada, Market, Garden
    locations = [
        {"lat": 18.5204, "lng": 73.8567},  # Hotel (city center)
        {"lat": 18.5158, "lng": 73.8567},  # Dagadusheth Temple
        {"lat": 18.5089, "lng": 73.8553},  # Kelkar Museum
        {"lat": 18.5195, "lng": 73.8553},  # Shaniwar Wada
        {"lat": 18.5167, "lng": 73.8520},  # Tulsi Baug Market
        {"lat": 18.5314, "lng": 73.8446},  # Empress Garden
    ]
    
    # Realistic travel times in minutes (symmetric matrix)
    durations = [
        [0,   8,  12,  10,  9,  15],  # From Hotel
        [8,   0,   7,   5,  6,  18],  # From Temple
        [12,  7,   0,   8,  9,  20],  # From Museum
        [10,  5,   8,   0,  7,  22],  # From Shaniwar Wada
        [9,   6,   9,   7,  0,  25],  # From Market
        [15, 18,  20,  22, 25,   0],  # From Garden
    ]
    
    # Realistic distances in meters
    distances = [
        [0,    800,  1200, 1000, 900,  1500],  # From Hotel
        [800,  0,    700,  500,  600,  1800],  # From Temple
        [1200, 700,  0,    800,  900,  2000],  # From Museum
        [1000, 500,  800,  0,    700,  2200],  # From Shaniwar Wada
        [900,  600,  900,  700,  0,    2500],  # From Market
        [1500, 1800, 2000, 2200, 2500, 0],    # From Garden
    ]
    
    return DistanceMatrix(
        origins=locations,
        destinations=locations,
        durations=durations,
        distances=distances
    )


def create_sample_cache_data() -> Dict:
    """
    Create sample cache data for testing caching functionality.
    
    Returns:
        Dictionary with cache entries
    """
    return {
        "pune_pois_2025": {
            "data": MOCK_PUNE_POIS,
            "timestamp": 1696435200,  # Sample timestamp
            "ttl": 86400
        },
        "distance_matrix_pune_center": {
            "data": get_predefined_distance_matrix().model_dump(),
            "timestamp": 1696435200,
            "ttl": 86400
        }
    }


# Weather compatibility scores by category (0.0 to 1.0)
WEATHER_COMPATIBILITY = {
    "temple": 0.9,      # Generally covered
    "museum": 1.0,      # Indoor
    "historic": 0.6,    # Often outdoor ruins
    "shopping": 0.9,    # Often covered/indoor
    "food": 0.8,        # Mix of indoor/outdoor
    "park": 0.3,        # Outdoor
    "cultural": 0.8,    # Mix
    "market": 0.5,      # Often semi-outdoor
    "entertainment": 0.9, # Usually indoor
    "scenic": 0.2       # Outdoor viewpoints
}


def get_weather_compatibility(category: str) -> float:
    """
    Get weather compatibility score for a POI category.
    
    Args:
        category: POI category
        
    Returns:
        Weather compatibility score (0.0 to 1.0)
    """
    return WEATHER_COMPATIBILITY.get(category.lower(), 0.5)