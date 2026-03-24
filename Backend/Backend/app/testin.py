# test_integration.py
import asyncio
from app.settings import get_settings
from app.http import get_client, with_retries
from app.cache import cache5m

async def test_flight_status():
    """Test flight status with your existing setup"""
    
    # Test settings
    settings = get_settings()
    print(f"✅ Settings loaded")
    print(f"API Key: {settings.AVIATIONSTACK_API_KEY[:10]}...")
    print(f"Base URL: {settings.AVIATIONSTACK_BASE}")
    
    # Test HTTP client
    client = get_client()
    print(f"✅ HTTP client created")
    
    # Test cache
    cache5m.set("test", {"status": "working"})
    cached_value = cache5m.get("test")
    print(f"✅ Cache test: {cached_value}")
    
    # Test API call
    try:
        url = f"{settings.AVIATIONSTACK_BASE}/flights"
        params = {
            "access_key": settings.AVIATIONSTACK_API_KEY,
            "flight_iata": "AA123",
            "limit": 1
        }
        
        response = await with_retries(client.get(url, params=params))
        print(f"✅ API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            flights_count = len(data.get("data", []))
            print(f"✅ Flights found: {flights_count}")
            
            # Test your existing flight status endpoint logic
            if flights_count > 0:
                flight = data["data"][0]
                print(f"✅ Sample flight: {flight.get('flight', {}).get('iata', 'N/A')}")
        else:
            print(f"⚠️  API Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ API Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_flight_status())
