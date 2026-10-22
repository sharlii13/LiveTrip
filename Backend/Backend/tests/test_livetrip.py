"""End-to-end API flows for every LiveTrip feature (Google and weather are faked in conftest)."""
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
            return {"query": {"pages": [page, plan]}}
        return {}

    monkeypatch.setattr(placeinfo, "_get", fake_get)
    placeinfo._cache.clear()
    info = asyncio.run(placeinfo.place_info("Fort Aguada", 15.4923, 73.7735, "Goa"))
    assert info["article"] == "Fort Aguada" and info["description"].startswith("Fort Aguada is")
    assert info["photos"] == [{"url": "https://thumb/Fort_aguada.jpg", "author": "Jane Doe", "license": "CC BY-SA 4.0",
                               "source_url": "https://commons.wikimedia.org/wiki/File%3AFort_aguada.jpg"}]

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
