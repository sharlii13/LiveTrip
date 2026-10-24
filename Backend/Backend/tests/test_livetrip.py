"""End-to-end API flows for every LiveTrip feature (Google and weather are faked in conftest)."""
import asyncio
from datetime import date, timedelta

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def make_trip(c, days=2, **extra):
    start = date.today()
    body = {"destination": "Jaipur", "startDate": start.isoformat(),
            "endDate": (start + timedelta(days=days - 1)).isoformat(), "interests": ["culture", "nature"],
            "foodPreference": "vegetarian", "transportPreference": "car", **extra}
    r = c.post("/api/trips", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def visits(itin, day=None):
    return [s for d in itin["days"] if day in (None, d["day"]) for s in d["time_slots"] if s["kind"] == "visit"]


def check_in(c, trip_id, slot, at_place=True):
    loc = slot["activity"]["location"]
    body = {"lat": loc["latitude"], "lng": loc["longitude"]} if at_place else {}
    r = c.post(f"/api/itinerary/{trip_id}/items/{slot['item_id']}/complete", json=body)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- accounts ----------

def test_register_login_me_logout(client, make_user):
    a = make_user("Asha")
    assert a.get("/api/auth/me").json()["user"]["name"] == "Asha"
    assert client.post("/api/auth/login", json={"email": a.email, "password": "wrong-pass"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": a.email, "password": "travel-pass-1"})
    assert r.status_code == 200 and r.json()["token"]
    assert client.post("/api/auth/register", json={"name": "X", "email": a.email,
                                                   "password": "travel-pass-1"}).status_code == 409
    a.post("/api/auth/logout")
    assert a.get("/api/auth/me").json() == {"user": None}  # signed out is not an error
    bearer = {"Authorization": f"Bearer {r.json()['token']}"}
    assert client.get("/api/auth/me", headers=bearer).json()["user"]["name"] == "Asha"


def test_profile_update_and_public_view(make_user, client):
    a = make_user("Ravi")
    a.patch("/api/users/me", json={"bio": "Fort lover", "location": "Pune"})
    pub = client.get(f"/api/users/{a.user['id']}").json()
    assert pub["bio"] == "Fort lover" and "email" not in pub


# ---------- destinations & reviews ----------

def test_destinations_search_and_reviews(make_user, client):
    assert len(client.get("/api/destinations?limit=3").json()) == 3
    found = client.get("/api/destinations?search=jaipur").json()
    assert {d["name"] for d in found} >= {"Hawa Mahal", "Amber Fort"}
    a = make_user("Meera")
    assert client.post("/api/reviews", json={"destinationId": "dest1", "rating": 5, "content": "x"}).status_code == 401
    r = a.post("/api/reviews", json={"destinationId": "dest1", "rating": 5, "title": "Wow", "content": "Beautiful"})
    assert r.status_code == 200
    detail = client.get("/api/destinations/dest1").json()
    assert detail["reviewCount"] >= 1 and detail["reviews"][0]["user"]["name"] == "Meera"
    assert client.get(f"/api/users/{a.user['id']}/reviews").json()[0]["destinationId"] == "dest1"


# ---------- itinerary generation ----------

def test_trip_generation_personalised_with_meals(make_user):
    a = make_user()
    itin = make_trip(a, days=2)
    assert len(itin["days"]) == 2
    for d in itin["days"]:
        kinds = [s["kind"] for s in d["time_slots"]]
        assert "visit" in kinds and kinds.count("meal") == 2
        times = [s["start_time"] for s in d["time_slots"]]
        assert times == sorted(times), times
        meals = [s for s in d["time_slots"] if s["kind"] == "meal"]
        assert meals[0]["activity"]["name"].startswith("Lunch") and meals[-1]["activity"]["name"].startswith("Dinner")
    assert itin["distance_source"] == "estimate" and itin["distance_note"]
    assert a.get(f"/api/itinerary/{itin['id']}").json()["id"] == itin["id"]
    assert "Day 1" in a.get(f"/api/itinerary/{itin['id']}/export?format=txt").text
    assert any(t["id"] == int(itin["id"]) for t in a.get("/api/trips").json())


def test_generated_days_never_run_past_the_evening(make_user):
    a = make_user()
    itin = make_trip(a, days=2, transportPreference="walking", pace="fast", interests=["culture", "nature", "shopping"])
    for slot in visits(itin):
        assert not slot["overflow"] and slot["end_time"] <= "21:30", slot


def test_create_itinerary_frontend_contract(client):
    start = date.today().isoformat()
    r = client.post("/api/itinerary/create", json={
        "user_id": "x", "destination": "Jaipur", "start_date": start + "T00:00:00Z", "end_date": start + "T00:00:00Z",
        "user_preferences": {"food_preference": "both", "interests": ["shopping"], "preferred_transport": ["walking"]},
        "must_visit_places": ["Hawa Mahal"]})
    assert r.status_code == 200, r.text
    names = [s["activity"]["name"] for s in visits(r.json())]
    assert "Hawa Mahal" in names  # must-visit places are always scheduled


def test_opening_hours_parsing_handles_late_and_odd_hours():
    from livetrip.planning import _open_close
    assert _open_close(["Monday: 9:00 AM – 5:30 PM"]) == ("09:00", "17:30")
    assert _open_close(["Monday: 6:00 PM – 1:00 AM"]) == ("18:00", "23:59")  # open past midnight
    assert _open_close(["Mo-Su 18:00-02:00"]) == ("18:00", "23:59")
    assert _open_close(["Monday: Open 24 hours"]) == ("00:00", "23:59")
    assert _open_close(["Monday: Closed"]) == ("09:00", "18:00")
    assert _open_close([]) == ("09:00", "18:00")


def test_each_day_is_one_compact_area_and_route_is_shortest():
    from livetrip.planning import area_days, order_route
    place = lambda name, lat, lng, **kw: {"name": name, "lat": lat, "lng": lng, "hours": [], **kw}
    lake = [place(f"Lake {i}", 17.41 + i * 0.002, 78.47) for i in range(6)]
    old_city = [place(f"Old {i}", 17.36 + i * 0.002, 78.47) for i in range(4)]  # ~5.5 km south of the lake
    ranked = [lake[0], old_city[0]] + lake[1:] + old_city[1:]  # quality order mixes the two areas
    days = area_days(ranked, 2, 4)
    assert {p["name"][:3] for p in days[1]} == {"Lak"} and {p["name"][:3] for p in days[2]} == {"Old"}
    # evening-only places are left out unless they are must-visit
    night = place("Night market", 17.41, 78.47, hours=["Monday: 6:00 PM – 11:00 PM"])
    assert night not in area_days([night] + lake, 1, 4)[1]
    must = dict(night, must_visit=True)
    assert must in area_days([must] + lake, 1, 4)[1]
    # near-duplicates (same kind, shared distinctive word) go to different days
    wax = [place(n, 24.58, 73.68, category="museum") for n in ("Wax Museum Udaipur", "Celebrity Wax Museum Udaipur")]
    others = [place(f"Sight {i} Udaipur", 24.58, 73.68, category="museum") for i in range(4)]
    days = area_days(wax + others, 2, 3)
    assert sum(p["name"].count("Wax") for p in days[1]) == 1
    # a stop across town is swapped for a spare near the rest, or dropped; must-visit stays
    from livetrip.planning import trim_outliers
    day = lake[:4] + [old_city[0]]
    assert [p["name"] for p in trim_outliers(list(day), [lake[5]])] == ["Lake 0", "Lake 1", "Lake 2", "Lake 3", "Lake 5"]
    assert "Old 0" not in [p["name"] for p in trim_outliers(list(day), [])]
    assert "Old 0" in [p["name"] for p in trim_outliers(lake[:4] + [dict(old_city[0], must_visit=True)], [])]
    # a zig-zag line of stops is visited in order along the line
    line = [place(str(i), 17.0 + i * 0.01, 78.0) for i in (3, 1, 4, 2)]
    assert [p["name"] for p in order_route(line, (17.0, 78.0))] == ["1", "2", "3", "4"]


def test_times_are_rounded_to_five_minutes(make_user):
    itin = make_trip(make_user())
    for d in itin["days"]:
        for s in d["time_slots"]:
            assert int(s["start_time"][-2:]) % 5 == 0, s["start_time"]


def test_date_picker_timestamps_keep_the_picked_day():
    from livetrip.planning import _parse_date
    fallback = date(2000, 1, 1)
    assert _parse_date("2026-11-05", fallback) == date(2026, 11, 5)
    assert _parse_date("2026-11-04T18:30:00.000Z", fallback) == date(2026, 11, 5)  # local midnight in IST
    assert _parse_date("2026-11-05T05:00:00.000Z", fallback) == date(2026, 11, 5)  # local midnight in New York
    assert _parse_date(None, fallback) == fallback


def test_search_cache_shares_calls_and_forgets_failures(app, monkeypatch):
    import asyncio
    from fastapi import HTTPException
    from livetrip import geo
    calls = {"n": 0, "fail": False}

    async def fake_google(query, near):
        calls["n"] += 1
        await asyncio.sleep(0.01)
        if calls["fail"]:
            raise HTTPException(429, geo.QUOTA_MESSAGE)
        return [{"name": f"{query} {i}"} for i in range(5)]

    monkeypatch.setattr(geo, "_text_search_any", fake_google)  # the provider call the cache wraps
    geo._search_cache.clear()

    async def scenario():
        same = await asyncio.gather(*[geo.real_search_places("cafes", (26.91241, 75.78731), 3) for _ in range(4)])
        assert calls["n"] == 1 and all(len(r) == 3 for r in same)  # one Google call for four lookups
        await geo.real_search_places("cafes", (26.9119, 75.7869))  # rounds to the same ~1 km cell
        assert calls["n"] == 1
        calls["fail"] = True
        for _ in range(2):
            try:
                await geo.real_search_places("museums", None)
            except HTTPException as e:
                assert e.status_code == 429
        assert calls["n"] == 3  # the failure was retried, not cached

    asyncio.run(scenario())
    geo._search_cache.clear()


def test_open_data_fallback_when_google_is_out_of_quota(app, monkeypatch):
    import asyncio
    from fastapi import HTTPException
    from livetrip import geo, osm
    google_calls = {"n": 0}

    async def google_quota(query, near):
        google_calls["n"] += 1
        raise HTTPException(429, geo.QUOTA_MESSAGE)

    async def open_data(query, near):
        return [{"name": "Charminar", "source": "openstreetmap", "category": "history"}]

    monkeypatch.setattr(geo, "_google_text_search", google_quota)
    monkeypatch.setattr(osm, "search", open_data)
    monkeypatch.setattr(geo, "_google_down_until", 0.0)
    geo._search_cache.clear()

    async def scenario():
        first = await geo.real_search_places("attractions in hyderabad")
        second = await geo.real_search_places("museums in hyderabad")
        return first, second

    first, second = asyncio.run(scenario())
    assert first[0]["source"] == second[0]["source"] == "openstreetmap"
    assert google_calls["n"] == 1  # after a quota error Google is skipped for a while
    assert not geo.google_available()
    geo._search_cache.clear()


def test_google_network_failure_falls_back_instead_of_crashing(app, monkeypatch):
    import asyncio
    import aiohttp
    from livetrip import geo, osm
    from app.rootplan.services import google_places

    async def broken(self, query, location):
        raise aiohttp.ClientConnectionError("connection reset")

    async def open_data(query, near):
        return [{"name": "Fort Aguada", "source": "openstreetmap"}]

    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "test-key")
    monkeypatch.setattr(google_places.GooglePlacesService, "text_search", broken)
    monkeypatch.setattr(osm, "search", open_data)
    monkeypatch.setattr(geo, "_google_down_until", 0.0)
    result = asyncio.run(geo._text_search_any("attractions in goa", None))
    assert result[0]["name"] == "Fort Aguada"


def test_unexpected_errors_return_a_readable_message(app, monkeypatch):
    from fastapi.testclient import TestClient
    from livetrip import planning

    async def boom(*args, **kwargs):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(planning, "generate", boom)
    r = TestClient(app, raise_server_exceptions=False).post("/api/trips", json={"destination": "Goa"})
    assert r.status_code == 500
    assert "RuntimeError: database is locked" in r.json()["detail"]


def test_place_info_matches_the_right_article_and_credits_photos(app, monkeypatch):
    import asyncio
    from livetrip import placeinfo
    from fastapi import HTTPException

    assert placeinfo._best("Charminar", ["Charminar Assembly constituency", "Charminar", "Charminar metro station"]) == "Charminar"
    assert placeinfo._best("Fort Aguada", ["Taj Fort Aguada Resort", "Fort Aguada"]) == "Fort Aguada"
    assert placeinfo._best("Hotel Panchsheel Pakwaan", ["Hyderabad", "Golconda"]) is None

    async def fake_get(url, params):
        if "rest_v1" in url:
            return {"extract": " Fort Aguada is a 17th-century Portuguese fort. ",
                    "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Fort_Aguada"}},
                    "originalimage": {"source": "https://upload.wikimedia.org/x/Fort_aguada.jpg"}}
        if params.get("list") == "geosearch":
            return {"query": {"geosearch": [{"title": "Taj Fort Aguada Resort"}, {"title": "Fort Aguada"}]}}
        if "commons" in url:
            page = {"title": "File:Fort aguada.jpg", "imageinfo": [{"thumburl": "https://thumb/Fort_aguada.jpg",
                    "mime": "image/jpeg", "extmetadata": {"Artist": {"value": "<a>Jane Doe</a>"},
                                                          "LicenseShortName": {"value": "CC BY-SA 4.0"}}}]}
            plan = {"title": "File:Fort plan.svg", "imageinfo": [{"thumburl": "https://thumb/plan.png", "mime": "image/svg+xml"}]}
            if params.get("generator") == "geosearch":  # geotagged next door, but of something else
                bust = {"title": "File:LV Prasad bust.jpg", "imageinfo": [{"thumburl": "https://thumb/bust.jpg", "mime": "image/jpeg"}]}
                return {"query": {"pages": [page, bust]}}
            namesake = {"title": "File:Fort Aguada replica.jpg", "coordinates": [{"lat": 24.86, "lon": 67.0}],
                        "imageinfo": [{"thumburl": "https://thumb/replica.jpg", "mime": "image/jpeg"}]}
            return {"query": {"pages": [page, plan, namesake]}}
        if params.get("prop") == "images":
            return {"query": {"pages": [{"images": [{"title": "File:Fort Aguada replica.jpg"}, {"title": "File:Goa map.png"}]}]}}
        return {}

    monkeypatch.setattr(placeinfo, "_get", fake_get)
    placeinfo._cache.clear()
    info = asyncio.run(placeinfo.place_info("Fort Aguada", 15.4923, 73.7735, "Goa"))
    assert info["article"] == "Fort Aguada" and info["description"].startswith("Fort Aguada is")
    assert info["photos"] == [{"url": "https://thumb/Fort_aguada.jpg", "author": "Jane Doe", "license": "CC BY-SA 4.0",
                               "source_url": "https://commons.wikimedia.org/wiki/File%3AFort_aguada.jpg", "taken_at": None}]

    async def down(url, params):
        raise HTTPException(503, "Wikipedia unavailable")

    monkeypatch.setattr(placeinfo, "_get", down)
    placeinfo._cache.clear()
    empty = asyncio.run(placeinfo.place_info("Somewhere", 1.0, 2.0, "X"))
    assert empty["description"] is None and empty["photos"] == []  # optional extras never break the page
    placeinfo._cache.clear()


def test_tour_operators_are_not_places_to_visit(app):
    from livetrip.geo import is_service
    assert is_service(["tour_agency", "travel_agency", "point_of_interest"], "Jaipur City Sightseeing")
    assert is_service(["tourist_attraction"], "Things to do in Jaipur")
    assert not is_service(["castle", "tourist_attraction"], "Hawa Mahal")
    assert not is_service(["museum"], "Things Museum")
    assert is_service(["point_of_interest"], "Mumbai Bollywood Tours")
    assert not is_service(["tourist_attraction"], "Tour Montparnasse")


def test_wikipedia_sights_keep_only_places_to_visit(monkeypatch):
    import asyncio
    from livetrip import osm

    osm._wiki_cache.clear()

    async def fake_get(url, params):
        pages = [
            ("Golconda Fort", "Fort in Hyderabad, India", 40000),
            ("Salar Jung Museum", "Art Museum in Hyderabad", 26000),
            ("Birla Mandir, Hyderabad", "Hindu temple in Telangana", 9000),
            ("Hussain Sagar", "Lake in Hyderabad", 12000),
            ("Kacheguda railway station", "Train station in Hyderabad", 9000),
            ("Osmania General Hospital", "Hospital in Telangana", 12000),
        ]
        return {"query": {"pages": [{"pageid": i, "title": t, "description": d, "length": n,
                                     "coordinates": [{"lat": 17.38 + i / 1000, "lon": 78.48}]}
                                    for i, (t, d, n) in enumerate(pages)]}}

    monkeypatch.setattr(osm, "_get", fake_get)
    found = asyncio.run(osm.wikipedia_sights((17.38, 78.48), osm.INTENTS["attractions"][0]))
    by_name = {p["name"]: p["category"] for p in found}
    assert by_name == {"Golconda Fort": "history", "Salar Jung Museum": "museum", "Birla Mandir": "religious",
                       "Hussain Sagar": "nature"}
    assert all(p["rating"] == 0 for p in found)  # open data has no star ratings; never invent them
    assert osm.intents_for("pure vegetarian restaurant") == ["food"]
    assert osm.intents_for("museums and heritage sites in mumbai") == ["museum", "history"]
    assert osm.intents_for("Charminar, Hyderabad") == []
    osm._wiki_cache.clear()

    async def fake_nominatim(url, params):  # vegetarian by OSM tag, by name, and a non-veg place
        return [{"name": n, "lat": "17.38", "lon": "78.48", "type": "restaurant", "category": "amenity",
                 "importance": 0.1, "osm_type": "node", "osm_id": i, "extratags": tags}
                for i, (n, tags) in enumerate([("Chutneys", {"diet:vegetarian": "only"}), ("Anand Bhavan", {}),
                                               ("Madina Hotel", {})])]

    monkeypatch.setattr(osm, "_get", fake_nominatim)
    monkeypatch.setattr(osm, "wikipedia_sights", lambda *a: asyncio.sleep(0, []))
    monkeypatch.setattr(osm, "_last_nominatim", 0.0)
    veg = asyncio.run(osm.search("pure vegetarian restaurant", (17.38, 78.48)))
    assert {p["name"] for p in veg} == {"Chutneys", "Anand Bhavan"}  # never "any restaurant" for a veg search


def test_trips_planned_before_sign_in_are_claimed(client, make_user):
    anonymous = make_trip(client, days=1)  # no account yet
    a, b = make_user("Claimer"), make_user("Other")
    assert anonymous["user_id"] is None
    r = a.post("/api/trips/claim", json={"ids": [int(anonymous["id"])]}).json()
    assert r["claimed"] == [int(anonymous["id"])]
    assert any(t["id"] == int(anonymous["id"]) for t in a.get("/api/trips").json())
    assert b.post("/api/trips/claim", json={"ids": [int(anonymous["id"])]}).json()["claimed"] == []  # already owned
    assert b.get(f"/api/itinerary/{anonymous['id']}").status_code == 403


def test_other_users_cannot_edit_or_view_private_trip(make_user):
    a, b = make_user("Owner"), make_user("Other")
    itin = make_trip(a, days=1)
    assert b.get(f"/api/itinerary/{itin['id']}").status_code == 403
    assert b.post(f"/api/itinerary/{itin['id']}/reschedule", json={"reason": "skip_next"}).status_code == 403


# ---------- rescheduling ----------

def test_skip_proposal_then_apply_and_version_check(make_user):
    a = make_user()
    itin = make_trip(a, days=1)
    first = visits(itin)[0]
    prop = a.post(f"/api/itinerary/{itin['id']}/reschedule", json={"reason": "skip_next"}).json()
    assert prop["ops"] == [{"op": "skip", "item_id": first["item_id"]}]
    assert a.get(f"/api/itinerary/{itin['id']}").json()["version"] == itin["version"]  # nothing saved yet
    applied = a.post(f"/api/itinerary/{itin['id']}/apply", json={"ops": prop["ops"], "expected_version": prop["version"]})
    assert applied.status_code == 200
    assert visits(applied.json())[0]["status"] == "skipped"
    stale = a.post(f"/api/itinerary/{itin['id']}/apply", json={"ops": prop["ops"], "expected_version": prop["version"]})
    assert stale.status_code == 409


def test_weather_relaxed_delay_and_optimise(make_user):
    a = make_user()
    itin = make_trip(a, days=2)
    tid = itin["id"]
    weather = a.post(f"/api/itinerary/{tid}/reschedule", json={"reason": "weather"}).json()
    outdoor_today = [s for s in visits(itin, 1) if s["activity"]["weather_dependent"]]
    assert len(weather["ops"]) == len(outdoor_today)
    assert all(op["op"] == "replace" and not op["place"]["outdoor"] for op in weather["ops"])
    alerts = a.get(f"/api/itinerary/{tid}/alerts").json()
    assert len(alerts) == len(outdoor_today)
    a.post(f"/api/itinerary/{tid}/alerts/{alerts[0]['id']}/acknowledge") if alerts else None

    relaxed = a.post(f"/api/itinerary/{tid}/reschedule", json={"reason": "relaxed", "day": 1}).json()
    kept = [s for s in visits(relaxed["preview"], 1) if s["status"] == "planned"]
    assert len(kept) <= 2

    delay = a.post(f"/api/itinerary/{tid}/reschedule", json={"reason": "delay", "day": 1, "minutes": 45}).json()
    assert delay["ops"][0] == {"op": "delay", "day": 1, "minutes": 45}
    before = visits(itin, 1)[0]["start_time"]
    after = next(s for s in visits(delay["preview"], 1) if s["item_id"] == visits(itin, 1)[0]["item_id"])["start_time"]
    assert after > before

    optimised = a.post(f"/api/itinerary/{tid}/route-optimization?day_index=0")
    assert optimised.status_code == 200


def test_completed_and_locked_stops_are_preserved(make_user):
    a = make_user()
    itin = make_trip(a, days=1)
    tid = itin["id"]
    v = visits(itin)
    check_in(a, tid, v[0])
    a.patch(f"/api/itinerary/{tid}/items/{v[1]['item_id']}", json={"locked": True})
    bad = a.post(f"/api/itinerary/{tid}/apply", json={"ops": [{"op": "skip", "item_id": v[0]["item_id"]}]})
    assert bad.status_code == 400
    bad = a.post(f"/api/itinerary/{tid}/apply", json={"ops": [{"op": "skip", "item_id": v[1]["item_id"]}]})
    assert bad.status_code == 400
    relaxed = a.post(f"/api/itinerary/{tid}/reschedule", json={"reason": "relaxed", "day": 1}).json()
    assert all(op["item_id"] not in (v[0]["item_id"], v[1]["item_id"]) for op in relaxed["ops"])


def test_alternatives_and_replace(make_user):
    a = make_user()
    itin = make_trip(a, days=1)
    slot = visits(itin)[0]
    alts = a.get(f"/api/itinerary/{itin['id']}/items/{slot['item_id']}/alternatives?reason=indoor").json()
    assert alts["alternatives"] and all(not p["outdoor"] for p in alts["alternatives"])
    r = a.post(f"/api/itinerary/{itin['id']}/apply",
               json={"ops": [{"op": "replace", "item_id": slot["item_id"], "place": alts["alternatives"][0]}]})
    assert visits(r.json())[0]["activity"]["name"] == alts["alternatives"][0]["name"]


def test_weather_endpoint(make_user):
    a = make_user()
    itin = make_trip(a, days=2)
    w = a.get(f"/api/itinerary/{itin['id']}/current-weather").json()
    assert w["condition"] == "rain" and len(w["trip_forecast"]) == 2


# ---------- recommendations & assistant ----------

def test_recommendations(make_user, client):
    a = make_user()
    itin = make_trip(a, days=1)
    lat, lng = itin["start_location"]["lat"], itin["start_location"]["lng"]
    food = client.get(f"/api/recommendations/restaurants?lat={lat}&lng={lng}&diet=vegetarian").json()["results"]
    assert food and all(p["category"] == "food" for p in food)
    stays = a.get(f"/api/recommendations/stays?trip_id={itin['id']}&budget=low").json()
    assert stays["results"] and "not live" in stays["note"]
    mood = client.get(f"/api/recommendations/mood?mood=relaxed&lat={lat}&lng={lng}&minutes_left=90").json()
    assert all(p["visit_min"] + p["travel_min"] * 2 <= 90 for p in mood["results"])
    near = client.get(f"/api/recommendations/nearby?lat={lat}&lng={lng}&radius_km=2").json()["results"]
    assert all(p["distance_km"] <= 2 for p in near)
    assert client.get("/api/places/search?query=Jaipur attractions").json()["items"][0]["location"]["lat"]


def test_assistant_commands(make_user):
    a = make_user()
    itin = make_trip(a, days=1)
    tid = int(itin["id"])
    ask = lambda m: a.post("/api/assistant/message", json={"message": m, "trip_id": tid}).json()
    assert ask("What should I visit next?")["intent"] == "next"
    veg = ask("Find a vegetarian restaurant nearby")
    assert veg["intent"] == "restaurants" and veg["places"]
    indoor = ask("Replace my next activity with an indoor attraction")
    assert indoor["intent"] == "indoor_next" and indoor["proposal"]["ops"][0]["op"] == "replace"
    assert ask("Make the rest of my day more relaxed")["intent"] == "relaxed"
    assert ask("Find something interesting within 2 km")["intent"] == "nearby"
    assert ask("I have only two hours left. What can I visit?")["intent"] == "time_left"
    assert ask("Suggest a cheaper alternative")["intent"] == "cheaper"
    late = ask("I'm running forty minutes late")
    assert late["intent"] == "delay" and late["proposal"]["ops"][0]["minutes"] == 40
    applied = a.post(f"/api/itinerary/{tid}/apply", json={"ops": indoor["proposal"]["ops"],
                                                          "expected_version": indoor["proposal"]["version"]})
    assert applied.status_code == 200
    assert ask("hello")["intent"] == "help"


def test_rule_assistant_uses_the_chat_and_the_trip(make_user):
    a = make_user()
    itin = make_trip(a, days=1)
    tid = int(itin["id"])
    stop = visits(itin)[0]["activity"]["name"]
    about = a.post("/api/assistant/message", json={"message": f"Tell me about {stop}", "trip_id": tid}).json()
    assert about["intent"] == "about" and stop in about["reply"]
    follow = a.post("/api/assistant/message", json={
        "message": "and vegetarian?", "trip_id": tid,
        "history": [{"role": "user", "text": "Find a restaurant nearby"},
                    {"role": "assistant", "text": "Places to eat nearby: ..."}]}).json()
    assert follow["intent"] == "restaurants"


def test_ai_assistant_tool_loop_proposal_and_context(make_user, monkeypatch):
    """Claude is faked: it asks for a plan change, then answers. The app gets the reply plus the proposal."""
    from types import SimpleNamespace as NS
    from livetrip import ai_assistant
    a = make_user()
    itin = make_trip(a, days=1)
    tid = int(itin["id"])
    seen = []

    class FakeMessages:
        async def create(self, **kw):
            seen.append({**kw, "messages": list(kw["messages"])})  # the list grows as the loop runs
            if len(seen) == 1:
                return NS(stop_reason="tool_use", content=[
                    NS(type="text", text="Let me lighten your day."),
                    NS(type="tool_use", id="t1", name="propose_plan_change", input={"change": "relaxed"})])
            return NS(stop_reason="end_turn", content=[NS(type="text", text="I proposed a lighter day; review it.")])

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(ai_assistant, "_client", NS(beta=NS(messages=FakeMessages())))
    res = a.post("/api/assistant/message", json={
        "message": "I'm tired, make it easier", "trip_id": tid, "page": f"/trips/{tid}", "language": "hi",
        "history": [{"role": "assistant", "text": "Hi!"}, {"role": "user", "text": "Hello"},
                    {"role": "assistant", "text": "Hello! How can I help?"}]}).json()
    assert res["reply"].startswith("I proposed") and res["proposal"]["ops"]
    first = seen[0]
    assert first["model"] == "claude-opus-5-5" and first["messages"][0] == {"role": "user", "content": "Hello"}
    ctx = first["messages"][-1]["content"]
    assert "<context>" in ctx and "App language: hi" in ctx and visits(itin)[0]["activity"]["name"] in ctx
    tool_result = seen[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and "preview" not in tool_result["content"]  # big preview stays out


# ---------- points, badges, challenges, rewards ----------

def test_check_in_points_are_verified_and_not_duplicated(make_user):
    a = make_user()
    itin = make_trip(a, days=1)
    tid = itin["id"]
    v = visits(itin)
    far = check_in(a, tid, v[1], at_place=False)
    assert not far["verified"] and far["awards"] == []
    near = check_in(a, tid, v[0])
    kinds = {x["type"] for x in near["awards"]}
    assert near["verified"] and {"visit_complete", "new_attraction"} <= kinds
    again = check_in(a, tid, v[0])
    assert again["awards"] == []
    dash = a.get("/api/points/dashboard").json()
    assert dash["total_earned"] >= 80 and dash["streak"] == 1


def test_trip_completion_badges_destination_challenge_and_redemption(make_user):
    a = make_user()
    itin = make_trip(a, days=2)
    tid = itin["id"]
    for slot in visits(itin):
        check_in(a, tid, slot)
    dash = a.get("/api/points/dashboard").json()
    earned = {b["code"] for b in dash["badges"] if b["earned"]}
    assert "trip_master" in earned
    assert a.get(f"/api/itinerary/{tid}").json()["status"] == "completed"
    assert any(e["kind"] == "destination_challenge" for e in dash["recent_activity"]) or len(visits(itin)) < 5
    assert any(e["kind"] == "trip_complete" for e in dash["recent_activity"])

    offers = a.get("/api/offers").json()
    cheapest = min(offers, key=lambda o: o["cost_points"])
    expensive = max(offers, key=lambda o: o["cost_points"])
    if dash["balance"] < expensive["cost_points"]:
        assert a.post(f"/api/offers/{expensive['id']}/redeem").status_code == 400
    r = a.post(f"/api/offers/{cheapest['id']}/redeem")
    assert r.status_code == 200 and len(r.json()["code"]) == 8
    assert r.json()["balance"] == dash["balance"] - cheapest["cost_points"]
    assert a.post(f"/api/offers/{cheapest['id']}/redeem").status_code == 409
    assert a.get("/api/points/dashboard").json()["redemptions"][0]["code"] == r.json()["code"]


def test_daily_challenges_and_leaderboard_opt_out(make_user):
    a = make_user("Leader")
    itin = make_trip(a, days=1)
    for slot in visits(itin)[:3]:
        check_in(a, itin["id"], slot)
    ch = a.get("/api/challenges").json()["challenges"]
    assert len(ch) == 3 and all(0 <= c["progress"] <= c["goal"] for c in ch)
    board = a.get("/api/points/leaderboard").json()
    assert any(e["is_me"] for e in board["entries"])
    city = a.get("/api/points/leaderboard?scope=city&city=Jaipur").json()
    assert any(e["is_me"] for e in city["entries"])
    a.patch("/api/users/me", json={"onLeaderboard": False})
    assert not any(e["is_me"] for e in a.get("/api/points/leaderboard").json()["entries"])


def test_business_offers(make_user):
    a = make_user("Shop")
    offer = {"business_name": "Test Café", "title": "Free tea", "cost_points": 50,
             "expires_on": (date.today() + timedelta(days=30)).isoformat()}
    assert a.post("/api/offers", json=offer).status_code == 403
    a.patch("/api/users/me", json={"isBusiness": True})
    assert a.post("/api/offers", json=offer).json()["title"] == "Free tea"


def test_distance_bonus_needs_long_trip(make_user):
    a = make_user()
    itin = make_trip(a, days=1, hotel={"lat": 26.0, "lng": 75.0})  # roughly 130 km from the stops
    result = check_in(a, itin["id"], visits(itin)[0])
    assert any(x["type"] == "distance_bonus" and x["points"] <= 100 for x in result["awards"])


# ---------- photos ----------

def test_photo_feed_privacy_reactions_gallery(make_user, client):
    a, b = make_user("Photog"), make_user("Viewer")
    itin = make_trip(a, days=1)
    slot = visits(itin)[0]
    bad = a.post("/api/photos", files={"file": ("x.txt", b"not an image", "text/plain")}, data={})
    assert bad.status_code == 400
    up = a.post("/api/photos", files={"file": ("p.png", PNG, "image/png")},
                data={"caption": "Pink city", "hashtags": "#Jaipur #heritage", "trip_id": itin["id"],
                      "item_id": slot["item_id"], "share_location": "true", "visibility": "public"})
    assert up.status_code == 200, up.text
    photo = up.json()["photo"]
    assert photo["place_name"] == slot["activity"]["name"] and photo["hashtags"] == ["heritage", "jaipur"]
    assert any(x["type"] == "photo_upload" for x in up.json()["awards"])
    assert client.get(photo["url"]).status_code == 200

    private = a.post("/api/photos", files={"file": ("q.png", PNG, "image/png")},
                     data={"visibility": "private", "city": "Jaipur"}).json()["photo"]
    feed = b.get("/api/photos/feed?city=Jaipur").json()["photos"]
    ids = {p["id"] for p in feed}
    assert photo["id"] in ids and private["id"] not in ids
    seen = next(p for p in feed if p["id"] == photo["id"])
    assert not seen["location_precise"] and seen["lat"] == round(slot["activity"]["location"]["latitude"], 2)
    assert b.get(f"/api/photos/{private['id']}").status_code == 404

    assert b.post(f"/api/photos/{photo['id']}/like").json()["likes"] == 1
    assert b.post(f"/api/photos/{photo['id']}/like").json()["likes"] == 0
    b.post(f"/api/photos/{photo['id']}/save")
    assert b.get("/api/photos/saved").json()[0]["id"] == photo["id"]
    assert b.post(f"/api/photos/{photo['id']}/comments", json={"text": "Gorgeous!"}).json()["comment_list"][0]["text"] == "Gorgeous!"
    assert a.get("/api/photos/feed?hashtag=heritage").json()["photos"][0]["id"] == photo["id"]

    albums = a.get("/api/gallery/me").json()["albums"]
    assert any(al["title"].startswith("Jaipur Trip – ") for al in albums)
    assert b.delete(f"/api/photos/{photo['id']}").status_code == 404
    assert a.delete(f"/api/photos/{private['id']}").json()["deleted"]


def test_photo_to_itinerary_and_wishlist(make_user):
    a, b = make_user("Sharer"), make_user("Planner")
    a_trip = make_trip(a, days=1)
    up = a.post("/api/photos", files={"file": ("p.jpg", b"\xff\xd8\xff" + b"\x00" * 32, "image/jpeg")},
                data={"place_name": "Nahargarh Fort", "city": "Jaipur", "visibility": "public"}).json()["photo"]
    b_trip = make_trip(b, days=2, pace="relaxed")  # leaves room for extra stops
    prop = b.post(f"/api/photos/{up['id']}/add-to-itinerary", json={"trip_id": int(b_trip["id"])}).json()
    assert prop["fits"] and prop["ops"][0]["op"] == "add"
    applied = b.post(f"/api/itinerary/{b_trip['id']}/apply", json={"ops": prop["ops"]}).json()
    assert "Nahargarh Fort" in [s["activity"]["name"] for s in visits(applied)]
    again = b.post(f"/api/photos/{up['id']}/add-to-itinerary", json={"trip_id": int(b_trip["id"])}).json()
    assert not again["fits"]

    wish = b.post(f"/api/wishlist/from-photo/{up['id']}").json()
    assert wish["source"] == "photo"
    b.post("/api/wishlist", json={"name": "Jal Mahal", "city": "Jaipur"})
    matches = b.get(f"/api/wishlist/matches?trip_id={b_trip['id']}").json()["matches"]
    assert [m["wish"]["name"] for m in matches] == ["Jal Mahal"] and matches[0]["fits"]
    new_trip = make_trip(b, days=1)  # saved places are proposed automatically for the next trip there
    assert "Jal Mahal" in [s["activity"]["name"] for s in visits(new_trip)]
    b.delete(f"/api/wishlist/{wish['id']}")
    assert len(b.get("/api/wishlist").json()) == 1


# ---------- groups, history, feedback ----------

def test_groups_voting_and_roles(make_user):
    a, b = make_user("Lead"), make_user("Friend")
    itin = make_trip(a, days=2)
    group = a.post("/api/groups", json={"name": "Goa gang", "trip_id": int(itin["id"])}).json()
    joined = b.post("/api/groups/join", json={"invite_code": group["invite_code"]}).json()
    assert joined["my_role"] == "viewer" and joined["invite_code"] is None
    assert b.get(f"/api/itinerary/{itin['id']}").status_code == 200  # members can view the shared trip
    g = b.post(f"/api/groups/{group['id']}/suggestions", json={"name": "Albert Hall Museum"}).json()
    sid = g["suggestions"][0]["id"]
    a.post(f"/api/groups/{group['id']}/suggestions/{sid}/vote", json={"value": 1})
    g = b.post(f"/api/groups/{group['id']}/suggestions/{sid}/vote", json={"value": 1}).json()
    assert g["suggestions"][0]["score"] == 2
    assert b.post(f"/api/groups/{group['id']}/suggestions/{sid}/accept").status_code == 403
    a.patch(f"/api/groups/{group['id']}/members/{b.user['id']}", json={"role": "editor"})
    g = b.post(f"/api/groups/{group['id']}/suggestions/{sid}/accept").json()
    assert g["suggestions"][0]["status"] == "added"
    assert "Albert Hall Museum" in [s["activity"]["name"] for s in visits(g["trip"])]
    assert g["group_challenge"]["goal"] == 1000
    board = b.get(f"/api/points/leaderboard?scope=group&group_id={group['id']}").json()
    assert board["scope"] == "group"
    assert len(a.get("/api/groups").json()) == 1


def test_history_feedback_and_preferences(make_user, client):
    a = make_user("Historian")
    itin = make_trip(a, days=1)
    slot = visits(itin)[0]
    check_in(a, itin["id"], slot)
    assert a.post(f"/api/itinerary/{itin['id']}/items/{slot['item_id']}/feedback", json={"rating": 5}).json()["saved"]
    hist = a.get("/api/history").json()
    assert hist["trips"][0]["visited"][0]["name"] == slot["activity"]["name"]
    assert client.get(f"/api/users/{a.user['id']}/history").status_code == 404
    a.patch("/api/users/me", json={"historyPublic": True})
    assert client.get(f"/api/users/{a.user['id']}/history").status_code == 200
    updated = a.put(f"/api/itinerary/{itin['id']}/preferences", json={"pace": "relaxed"}).json()
    names = [s["activity"]["name"] for s in visits(updated)]
    assert slot["activity"]["name"] in names  # completed stops survive a regeneration
    assert next(s for s in visits(updated) if s["activity"]["name"] == slot["activity"]["name"])["status"] == "completed"


def test_gemini_assistant_tool_loop(make_user, monkeypatch):
    """Gemini is faked: it calls a tool (its turn must go back unchanged, signature included), then answers."""
    import copy
    from livetrip import ai_assistant
    a = make_user()
    tid = int(make_trip(a, days=1)["id"])
    sent = []
    replies = [
        {"candidates": [{"content": {"role": "model", "parts": [
            {"functionCall": {"name": "find_restaurants", "args": {"diet": "vegetarian"}}, "thoughtSignature": "sig"}]}}]},
        {"candidates": [{"content": {"role": "model", "parts": [{"text": "Try the first one, it's close."}]}}]},
    ]

    class FakeResponse:
        status_code = 200
        def __init__(self, body): self.body = body
        def json(self): return self.body

    class FakeClient:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, headers, json):
            sent.append((url, copy.deepcopy(json)))
            return FakeResponse(replies[len(sent) - 1])

    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setattr(ai_assistant, "_gemini_last_good", None)  # start from the first model in the list
    monkeypatch.setattr(ai_assistant, "_gemini_resting", {})
    monkeypatch.setattr(ai_assistant.httpx, "AsyncClient", FakeClient)
    res = a.post("/api/assistant/message", json={"message": "veg food near my next stop?", "trip_id": tid}).json()
    assert res["reply"] == "Try the first one, it's close." and res["places"]
    url, second = sent[1]
    assert "gemini-3.5-flash-lite:generateContent" in url
    assert second["contents"][-2]["parts"][0]["thoughtSignature"] == "sig"
    assert "functionResponse" in second["contents"][-1]["parts"][0]
    assert "additionalProperties" not in str(second["tools"])


def test_gemini_quota_falls_back_to_rules_and_trip_totals(make_user, monkeypatch):
    from livetrip import ai_assistant

    class Busy:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **kw):
            class R:
                status_code, text = 429, "quota"
            return R()

    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setattr(ai_assistant.httpx, "AsyncClient", Busy)
    a = make_user()
    tid = int(make_trip(a, days=2)["id"])
    res = a.post("/api/assistant/message", json={"message": "what is my total travel time", "trip_id": tid}).json()
    assert res["intent"] == "trip_stats" and "Day 2" in res["reply"] and "travel in total" in res["reply"]


def test_google_sign_in(app, monkeypatch):
    from fastapi.testclient import TestClient
    from livetrip import accounts
    c = TestClient(app)
    assert c.get("/api/auth/providers").json() == {"google": False}
    assert "google_not_configured" in c.get("/api/auth/google", follow_redirects=False).headers["location"]

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    profile = {"email": "Traveller@Example.com", "email_verified": True, "name": "Tia", "picture": "https://p/x.png"}

    class FakeGoogle:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, data):
            assert data["code"] == "the-code" and data["client_secret"] == "secret"
            return FakeResp({"access_token": "tok"})
        async def get(self, url, headers):
            assert headers["Authorization"] == "Bearer tok"
            return FakeResp(profile)

    class FakeResp:
        def __init__(self, body): self.body = body
        def raise_for_status(self): pass
        def json(self): return self.body

    monkeypatch.setattr(accounts.httpx, "AsyncClient", FakeGoogle)
    start = c.get("/api/auth/google?next=/groups", follow_redirects=False)
    assert start.headers["location"].startswith("https://accounts.google.com/") and "client_id=cid" in start.headers["location"]
    state = start.headers["location"].split("state=")[1].split("&")[0]
    # a callback with someone else's state is refused
    bad = c.get("/api/auth/google/callback?code=the-code&state=forged", follow_redirects=False)
    assert "google_failed" in bad.headers["location"]
    done = c.get(f"/api/auth/google/callback?code=the-code&state={state}", follow_redirects=False)
    assert done.headers["location"] == "/groups"
    me = c.get("/api/auth/me").json()["user"]
    assert me["email"] == "traveller@example.com" and me["name"] == "Tia"
    # an unverified Google address never signs in, and next can't point off-site
    profile["email_verified"] = False
    c2 = TestClient(app)
    start = c2.get("/api/auth/google?next=//evil.example", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    assert "google_failed" in c2.get(f"/api/auth/google/callback?code=the-code&state={state}",
                                      follow_redirects=False).headers["location"]
    assert accounts._safe_next("//evil.example") == "/trips" and accounts._safe_next("https://x") == "/trips"


def test_gemini_moves_on_from_a_busy_model(make_user, monkeypatch):
    from livetrip import ai_assistant
    tried = []

    class Chain:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, headers, json):
            tried.append(url.split("/models/")[1].split(":")[0])
            class R:
                status_code = 503 if len(tried) == 1 else 200
                text = "busy"
                def json(self): return {"candidates": [{"content": {"parts": [{"text": "Hello from the backup."}]}}]}
            return R()

    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setattr(ai_assistant, "_gemini_last_good", None)
    monkeypatch.setattr(ai_assistant, "_gemini_resting", {})
    monkeypatch.setattr(ai_assistant.httpx, "AsyncClient", Chain)
    a = make_user()
    res = a.post("/api/assistant/message", json={"message": "hi"}).json()
    assert res["reply"] == "Hello from the backup." and tried == ["gemini-3.5-flash-lite", "gemini-flash-lite-latest"]
    assert ai_assistant._gemini_last_good == "gemini-flash-lite-latest"  # next time it starts with the one that worked
    # the busy model rests for a while: the next message doesn't waste time on it
    monkeypatch.setattr(ai_assistant, "_gemini_last_good", None)
    tried.clear()
    a.post("/api/assistant/message", json={"message": "hi again"})
    assert tried[0] == "gemini-flash-lite-latest"


def test_rule_assistant_answers_top_places_anywhere_and_admits_ai_trouble(make_user, monkeypatch):
    from livetrip import ai_assistant
    a = make_user()
    top = a.post("/api/assistant/message", json={"message": "what are the top 5 attraction of kerela"}).json()
    assert top["intent"] == "top_places" and top["reply"].startswith("Top ") and 0 < len(top["places"]) <= 5

    async def down(*args, **kw):
        raise ai_assistant.Unavailable("busy")
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setattr(ai_assistant, "reply", down)
    busy = a.post("/api/assistant/message", json={"message": "hello there"}).json()
    assert busy["intent"] == "help" and busy["reply"].startswith("My AI brain is busy")


def test_small_towns_still_fill_every_day(make_user, monkeypatch):
    """Open-data searches for a small town can find only a handful of places: each day still gets some."""
    from livetrip import planning
    from livetrip.planning import area_days
    place = lambda name, lat, lng: {"name": name, "lat": lat, "lng": lng, "hours": [], "category": "culture"}
    few = [place(f"Sight {c}", 19.09 + i * 0.003, 74.74) for i, c in enumerate("ABCDEF")]
    days = area_days(few, 3, 5)
    assert sorted(days) == [1, 2, 3] and all(days[d] for d in days)

    six = [{"name": f"Ahilyanagar sight {c}", "place_id": f"a{c}", "address": "", "lat": 19.09 + i * 0.004,
            "lng": 74.74, "rating": 4.2, "rating_count": 100, "types": ["tourist_attraction"], "category": "culture",
            "outdoor": False, "hours": [], "source": "openstreetmap"} for i, c in enumerate("ABCDEF")]

    async def only_six(query, near=None, limit=20):
        return [dict(p) for p in six][:limit]

    monkeypatch.setattr(planning, "search_places", only_six)
    monkeypatch.setattr(planning, "geocode", lambda name: asyncio.sleep(0, (19.09, 74.74)))
    itin = make_trip(make_user(), days=3, destination="Ahilyanagar")
    per_day = [len(visits(itin, d["day"])) for d in itin["days"]]
    assert len(per_day) == 3 and all(n >= 1 for n in per_day), per_day


def test_meals_fit_the_time_of_day_and_day_start_moves_the_day(make_user):
    from livetrip.planning import fits_meal
    assert not fits_meal({"name": "Sudamache Pohe", "types": ["restaurant"]}, "Dinner")
    assert not fits_meal({"name": "Chitale Bandhu Mithaiwale Sweets", "types": []}, "Lunch")
    assert not fits_meal({"name": "Brew Lab", "types": ["coffee_shop"]}, "Lunch")
    assert fits_meal({"name": "Cafe Goodluck", "types": ["cafe", "restaurant"]}, "Dinner")
    assert not fits_meal({"name": "Morning Thali", "types": ["restaurant"], "hours": ["Monday: 7:00 AM – 3:00 PM"]}, "Dinner")
    assert fits_meal({"name": "Vaishali", "types": ["restaurant"], "hours": ["Monday: 7:00 AM – 11:00 PM"]}, "Dinner")

    a = make_user()
    itin = make_trip(a, days=2)
    tid = itin["id"]
    first_before = visits(itin, 1)[0]["start_time"]
    r = a.post(f"/api/itinerary/{tid}/day-start", json={"day": 1, "time": "07:30"})
    assert r.status_code == 200, r.text
    after = r.json()
    assert visits(after, 1)[0]["start_time"] == "07:30" and first_before == "09:00"
    assert visits(after, 2)[0]["start_time"] == "09:00"  # other days unchanged
    assert after["days"][0]["day_start"] == "07:30"
    # later edits keep the chosen start
    skip = a.post(f"/api/itinerary/{tid}/reschedule", json={"reason": "skip_next"}).json()
    applied = a.post(f"/api/itinerary/{tid}/apply", json={"ops": skip["ops"], "expected_version": skip["version"]}).json()
    assert [s for s in visits(applied, 1) if s["status"] != "skipped"][0]["start_time"] == "07:30"
    assert a.post(f"/api/itinerary/{tid}/day-start", json={"day": 1, "time": "02:00"}).status_code == 400


def test_dense_city_drops_a_stop_two_km_out():
    from livetrip.planning import trim_outliers
    near = [{"name": f"Peth {i}", "lat": 18.515 + i * 0.0015, "lng": 73.855} for i in range(5)]  # ~170 m apart
    far = {"name": "Ohel David Synagogue", "lat": 18.519, "lng": 73.876}                       # ~2.2 km east
    spare = {"name": "Kasba Ganpati", "lat": 18.519, "lng": 73.857}
    kept = [p["name"] for p in trim_outliers(near + [far], [spare])]
    assert "Ohel David Synagogue" not in kept and "Kasba Ganpati" in kept


def test_meals_stay_meals_and_the_buddy_adds_stops_before_dinner(make_user, monkeypatch):
    import copy
    from livetrip import ai_assistant
    a = make_user()
    itin = make_trip(a, days=1)
    tid = itin["id"]
    slots = itin["days"][0]["time_slots"]
    dinner = next(s for s in slots if s["activity"]["name"].startswith("Dinner"))
    temple = {"name": "Ratneshwar Mahadev temple", "lat": 25.3, "lng": 83.0, "category": "religious", "place_id": "t1"}
    bad = a.post(f"/api/itinerary/{tid}/apply", json={"ops": [{"op": "replace", "item_id": dinner["item_id"], "place": temple}],
                                                      "expected_version": itin["version"]})
    assert bad.status_code == 400 and "place to eat" in bad.json()["detail"]

    replies = [
        {"candidates": [{"content": {"parts": [{"functionCall": {"name": "propose_replace_stop",
                                                                  "args": {"item_id": dinner["item_id"], "place_name": "x"}}}]}}]},
        {"candidates": [{"content": {"parts": [{"functionCall": {"name": "propose_add_stop", "args": {"query": "temple"}}}]}}]},
        {"candidates": [{"content": {"parts": [{"text": "I added one more stop before dinner; review it."}]}}]},
    ]
    sent = []

    class Fake:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *x): return False
        async def post(self, url, headers, json):
            sent.append(copy.deepcopy(json))
            body = replies[len(sent) - 1]
            class R:
                status_code = 200
                def json(self): return body
            return R()

    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setattr(ai_assistant, "_gemini_last_good", None)
    monkeypatch.setattr(ai_assistant, "_gemini_resting", {})
    monkeypatch.setattr(ai_assistant.httpx, "AsyncClient", Fake)
    res = a.post("/api/assistant/message", json={"message": "one more", "trip_id": int(tid)}).json()
    assert res["proposal"]["ops"][0]["op"] == "add"
    preview = res["proposal"]["preview"]["days"][0]["time_slots"]
    assert preview[-1]["activity"]["name"].startswith("Dinner")          # dinner kept, and still last
    assert len(preview) == len(slots) + 1


def test_stays_sort_by_location_and_destination_suggestions(make_user, monkeypatch):
    a = make_user()
    itin = make_trip(a, days=2)
    tid = itin["id"]
    near = a.get(f"/api/recommendations/stays?trip_id={tid}&sort=nearest").json()
    km = [p["distance_km"] for p in near["results"]]
    assert km == sorted(km) and "planned stops" in near["note"]
    day2 = a.get(f"/api/recommendations/stays?trip_id={tid}&day=2&sort=nearest").json()
    assert "day 2" in day2["note"]
    me = a.get(f"/api/recommendations/stays?trip_id={tid}&lat=26.95&lng=75.85&sort=rating").json()
    ratings = [p["rating"] for p in me["results"]]
    assert ratings == sorted(ratings, reverse=True) and "location you shared" in me["note"]
    assert a.get(f"/api/recommendations/stays?trip_id={tid}&sort=price").status_code == 400

    from livetrip import suggest
    async def no_network(q, limit):
        return [{"name": "Pune Cantonment", "detail": "Maharashtra, India", "source": "openstreetmap"},
                {"name": "Pune", "detail": "Maharashtra, India", "source": "openstreetmap"}]  # duplicate of the list
    monkeypatch.setattr(suggest, "photon", no_network)
    names = [s["name"] for s in a.get("/api/places/suggest?q=pu").json()["suggestions"]]
    assert set(names[:3]) == {"Pune", "Puri", "Puducherry"}  # names starting with what was typed
    assert "Pune Cantonment" not in names  # two letters: built-in list only
    names = [s["name"] for s in a.get("/api/places/suggest?q=pun").json()["suggestions"]]
    assert names.count("Pune") == 1 and "Pune Cantonment" in names
