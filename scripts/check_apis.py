import os
import sys
import json
from contextlib import redirect_stdout

# FastAPI TestClient
try:
    from fastapi.testclient import TestClient
except Exception as e:
    print(json.dumps({"error": f"Failed to import TestClient: {e}"}))
    raise

results = {
    "root_app": {},
    "live_trip_app": {}
}

# 1) Probe root app at app.main (endpoints under /api/itinerary)
try:
    import importlib
    # Ensure project root is on sys.path explicitly
    project_root = os.getcwd()
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if os.path.isdir(os.path.join(project_root, 'app')):
        root_app_mod = importlib.import_module("app.main")
    else:
        raise ImportError("'app' package not found at project root")
    root_app = getattr(root_app_mod, "app")
    client = TestClient(root_app)

    # Health check
    r = client.get("/api/itinerary/health")
    results["root_app"]["health"] = {"status_code": r.status_code, "json": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text}

    # Live Places check for Mumbai and Akola
    results["root_app"]["places_search"] = {}
    for city in ["mumbai", "akola"]:
        q = f"tourist attractions in {city}"
        rp = client.get("/api/itinerary/places/search", params={"query": q, "limit": 5})
        items_count = None
        try:
            if rp.status_code == 200 and rp.headers.get("content-type", "").startswith("application/json"):
                items = rp.json().get("items", [])
                items_count = len(items)
        except Exception:
            pass
        results["root_app"]["places_search"][city] = {"status_code": rp.status_code, "items": items_count}

    # Multi-day sample request
    payload = {
        "start_location": {"lat": 18.5204, "lng": 73.8567},
        "days": 2,
        "available_hours_per_day": 8,
        "poi_list": [
            {"id": 1, "name": "Shaniwar Wada", "lat": 18.5195, "lng": 73.8553, "duration": 2.0, "open": "09:00", "close": "18:00", "category": "fort", "score": 8.5},
            {"id": 2, "name": "Aga Khan Palace", "lat": 18.5566, "lng": 73.9030, "duration": 1.5, "open": "10:00", "close": "18:30", "category": "museum", "score": 8.0},
            {"id": 3, "name": "Pataleshwar Caves", "lat": 18.5308, "lng": 73.8471, "duration": 1.0, "open": "08:00", "close": "17:30", "category": "temple", "score": 7.2},
            {"id": 4, "name": "Saras Baug", "lat": 18.5006, "lng": 73.8532, "duration": 1.5, "open": "06:00", "close": "20:00", "category": "park", "score": 7.0}
        ],
        "user_preferences": {},
        "constraints": {},
        "start_time": "09:00",
        "transportation_mode": "driving"
    }
    r2 = client.post("/api/itinerary/plan-multi-day", json=payload)
    multiday_ok = r2.status_code == 200
    multiday_days = None
    if multiday_ok:
        try:
            data = r2.json()
            multiday_days = len(data.get("itinerary", []))
        except Exception:
            pass
    results["root_app"]["plan_multi_day"] = {
        "status_code": r2.status_code,
        "days_in_response": multiday_days,
        "summary_keys": list((r2.json().get("summary") or {}).keys()) if r2.status_code == 200 else []
    }
except Exception as e:
    results["root_app"]["error"] = str(e)

# 2) Probe Live Trip app under Backend/Backend/app/main.py
try:
    backend_base = os.path.join(os.getcwd(), "Backend", "Backend")
    backend_main_path = os.path.join(backend_base, "app", "main.py")
    # Load backend app as a uniquely named module to avoid clashing with root app
    import importlib.util
    spec = importlib.util.spec_from_file_location("livetrip_app_main", backend_main_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load backend app from {backend_main_path}")
    lt_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lt_mod)
    lt_app = getattr(lt_mod, "app")
    lt_client = TestClient(lt_app)

    # Create-complete-itinerary with a date range to trigger multi-day split (Pune sample)
    payload2 = {
        "title": "Test Trip",
        "user_id": 123,
        "destinations": [
            {"name": "Shaniwar Wada", "latitude": 18.5195, "longitude": 73.8553, "rating": 4.4, "stay_duration": 2.0, "category": "fort", "address": "Pune", "traffic_score": 5.0, "weather_match": 8.0},
            {"name": "Aga Khan Palace", "latitude": 18.5566, "longitude": 73.9030, "rating": 4.5, "stay_duration": 1.5, "category": "museum", "address": "Pune", "traffic_score": 5.0, "weather_match": 8.0},
            {"name": "Pataleshwar Caves", "latitude": 18.5308, "longitude": 73.8471, "rating": 4.2, "stay_duration": 1.0, "category": "temple", "address": "Pune", "traffic_score": 5.0, "weather_match": 8.0},
            {"name": "Saras Baug", "latitude": 18.5006, "longitude": 73.8532, "rating": 4.3, "stay_duration": 1.5, "category": "park", "address": "Pune", "traffic_score": 5.0, "weather_match": 8.0}
        ],
        "start_latitude": 18.5204,
        "start_longitude": 73.8567,
        "start_date": "2025-10-06",
        "end_date": "2025-10-07",
        "start_time": "09:00:00",
        "timezone": "Asia/Kolkata"
    }
    r3 = lt_client.post("/api/itinerary/create-complete-itinerary", json=payload2)
    days_estimated = None
    service_mode = None
    if r3.status_code == 200:
        j = r3.json()
        service_mode = j.get("service_mode")
        route_summary = j.get("route_summary", {})
        days_estimated = route_summary.get("estimated_duration_days")
    results["live_trip_app"]["create_complete_itinerary"] = {
        "status_code": r3.status_code,
        "service_mode": service_mode,
        "estimated_duration_days": days_estimated
    }
except Exception as e:
    results["live_trip_app"]["error"] = str(e)

print(json.dumps(results, indent=2))
