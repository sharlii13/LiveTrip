"""Runs the real app against a temporary SQLite database, with Google Places and Open-Meteo replaced by fakes."""
import math
import os
import sys
import tempfile
import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parent.parent / "app"
WORK = Path(tempfile.mkdtemp(prefix="livetrip-test-"))
os.chdir(WORK)  # database.py creates ./hackathon_travel.db in the working directory
os.environ.update({"LIVETRIP_UPLOAD_DIR": str(WORK / "uploads"), "LIVETRIP_SECRET_KEY": "test-secret",
                   "PYTHONUTF8": "1"})
for key in ("GOOGLE_PLACES_API_KEY", "GOOGLE_MAPS_API_KEY", "GOOGLE_DISTANCE_MATRIX_API_KEY", "GEMINI_API_KEY",
            "ANTHROPIC_API_KEY", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"):
    os.environ[key] = ""  # set (not removed) so load_dotenv() never pulls a real key from app/.env
sys.path[:0] = [str(APP_DIR), str(APP_DIR.parent)]

CENTER = (26.9124, 75.7873)  # Jaipur
KINDS = [  # (keyword in query, google types)
    ("restaurant", ["restaurant", "food"]),
    ("hotel", ["lodging", "hotel"]), ("hostel", ["lodging"]), ("stays", ["lodging"]),
    ("indoor", ["museum"]), ("museum", ["museum"]),
    ("park", ["park"]), ("garden", ["park"]), ("cafe", ["cafe", "food"]), ("free", ["park"]),
]


def fake_places(query, near=None, limit=20):
    q = query.lower()
    base = near or CENTER
    if limit == 1 and "," in query:  # looking up one named place ("Hawa Mahal, Jaipur")
        name = query.split(",")[0].strip()
        return [_place(name, ["tourist_attraction", "historical_landmark"], base, 0.004, 4.6, 50000)]
    if q.strip() in ("jaipur", "goa"):
        return [_place(query.title(), ["locality"], CENTER, 0, 4.5, 100)]
    types = next((t for kw, t in KINDS if kw in q), None)
    if types is None:
        mix = [["historical_landmark", "tourist_attraction"], ["park"], ["museum"], ["hindu_temple"],
               ["shopping_mall"]]
        out = [_place(f"{query[:18]} spot {i}", mix[i % len(mix)], base, 0.006 * (i + 1), 4.0 + (i % 5) / 10,
                      200 + 900 * i) for i in range(min(limit, 8))]
    else:
        out = [_place(f"{types[0]} {query[:12]} {i}", types, base, 0.004 * (i + 1), 4.1 + (i % 4) / 10, 300 + 50 * i)
               for i in range(min(limit, 6))]
    return out


def _place(name, types, base, offset, rating, count):
    from livetrip.geo import OUTDOOR_CATEGORIES, categorize
    cat = categorize(types)
    return {"name": name, "place_id": f"pid-{abs(hash(name)) % 10**8}", "address": f"{name}, Jaipur",
            "lat": base[0] + offset, "lng": base[1] + offset * math.cos(offset * 100), "rating": rating,
            "rating_count": count, "types": types, "category": cat, "outdoor": cat in OUTDOOR_CATEGORIES,
            "hours": ["Monday: 9:00 AM – 6:00 PM"]}


async def async_fake_places(query, near=None, limit=20):
    return fake_places(query, near, limit)


async def fake_weather(lat, lng):
    start = date.today()
    days = {}
    for i in range(16):
        d = (start + timedelta(days=i)).isoformat()
        wet = i == 0  # today is rainy, the rest is clear
        days[d] = {"date": d, "condition": "rain" if wet else "clear sky", "code": 63 if wet else 0,
                   "temp_max": 31, "temp_min": 22, "precipitation_probability": 90 if wet else 5, "wet": wet}
    return {"source": "test", "current": {"temperature": 27, "humidity": 70, "wind_speed": 8, "precipitation": 2,
                                          "condition": "rain", "timestamp": "now"}, "days": days}


@pytest.fixture(scope="session")
def app():
    import main  # noqa: E402  (imports after sys.path / cwd setup)
    from livetrip import geo, photos, planning, recommend, social
    geo.real_search_places = geo.search_places  # kept for the cache test
    from livetrip import placeinfo
    placeinfo.prefetch = lambda places, city: None  # no background calls to Wikipedia from tests
    for module in (geo, planning, recommend, photos, social):
        if hasattr(module, "search_places"):
            module.search_places = async_fake_places
    for module in (geo, planning):
        if hasattr(module, "weather"):
            module.weather = fake_weather
    return main.app


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture()
def make_user(app):
    from fastapi.testclient import TestClient
    counter = {"n": 0}

    def _make(name="Asha"):
        counter["n"] += 1
        c = TestClient(app)
        email = f"{name.lower()}-{uuid.uuid4().hex[:12]}@example.com"
        r = c.post("/api/auth/register", json={"name": name, "email": email, "password": "travel-pass-1"})
        assert r.status_code == 200, r.text
        c.user = r.json()["user"]
        c.email = email
        return c
    return _make
