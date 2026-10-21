"""Trips and living itineraries: generation, live updates, rescheduling proposals, check-ins."""
import asyncio
import json
import logging
import math
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import User, get_db
from . import rewards
from .core import current_user, loads, optional_user
from .geo import (OUTDOOR_CATEGORIES, VISIT_MINUTES, haversine_km, hhmm_to_min, min_to_hhmm, road_km, search_places,
                  geocode, travel_minutes, weather)
from .models import Alert, Group, GroupMember, ItemFeedback, ItineraryItem, Trip, WishlistItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["itinerary"])

INTEREST_QUERIES = {
    "culture": ["museums", "historical monuments", "temples and heritage sites"],
    "history": ["historical places", "forts and palaces"],
    "nature": ["parks and gardens", "lakes and viewpoints"],
    "adventure": ["adventure activities", "trekking spots"],
    "food": ["famous local food places"],
    "nightlife": ["nightlife spots"],
    "shopping": ["markets and shopping streets"],
    "relaxation": ["peaceful gardens", "lakeside spots"],
}
INTEREST_WEIGHTS = {
    "culture": {"culture": 0.9, "museum": 0.9, "history": 0.9, "religious": 0.8, "fort": 0.9},
    "history": {"history": 1.0, "fort": 1.0, "museum": 0.8},
    "nature": {"nature": 0.9, "park": 0.9},
    "adventure": {"nature": 0.8, "entertainment": 0.7},
    "food": {"food": 0.9},
    "nightlife": {"entertainment": 0.9},
    "shopping": {"shopping": 0.9},
    "relaxation": {"park": 0.8, "nature": 0.6},
}
PACE = {  # hours per day, max visits per day, last activity end
    "relaxed": (6.0, 3, "18:00"),
    "normal": (8.0, 5, "19:00"),
    "fast": (10.0, 6, "20:30"),
}
DAY_START = "09:00"
LATEST_END = "21:30"
CHECKIN_RADIUS_KM = 0.5
DISTANCE_BONUS_MIN_KM = 20
VEG_WORDS = {"vegetarian", "veg"}


# ---------- request models ----------

class TripIn(BaseModel):
    """Accepts the frontend's TripPlanningData (camelCase) as sent by the planning pages."""
    destination: str = Field(..., min_length=2, max_length=120)
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    companyType: Optional[str] = None
    travelers: Optional[int] = Field(None, ge=1, le=50)
    withPets: Optional[bool] = None
    foodPreference: Optional[str] = None
    interests: List[str] = []
    budget: Optional[float] = None
    pace: Optional[str] = "normal"
    transportPreference: Optional[str] = None
    ecoMode: Optional[bool] = False
    hotel: Optional[Dict[str, float]] = None
    mustVisit: List[str] = []


class CreateItineraryIn(BaseModel):
    """The frontend apiService.createItinerary request."""
    user_id: Optional[str] = None
    destination: str
    start_date: str
    end_date: str
    user_preferences: Dict[str, Any] = {}
    must_visit_places: List[str] = []
    budget_limit: Optional[float] = None


class PlaceIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    place_id: str = ""
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    category: str = "culture"
    rating: float = 0
    rating_count: int = 0
    address: str = ""
    outdoor: Optional[bool] = None


class OpIn(BaseModel):
    op: str = Field(..., pattern="^(skip|replace|delay|add|reorder)$")
    item_id: Optional[int] = None
    day: Optional[int] = None
    minutes: Optional[int] = Field(None, ge=1, le=600)
    place: Optional[PlaceIn] = None
    order: Optional[List[int]] = None


class ApplyIn(BaseModel):
    ops: List[OpIn]
    expected_version: Optional[int] = None


class CheckInIn(BaseModel):
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)


# ---------- helpers ----------

def _parse_date(value: Optional[str], fallback: date) -> date:
    if not value:
        return fallback
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        raise HTTPException(400, f"Invalid date: {value}")


def _open_close(hours: List[str]) -> Tuple[str, str]:
    """Parse '9:00 AM – 5:30 PM' from the first weekday line; default 09:00-18:00."""
    for line in hours[:1]:
        if "24 hours" in line:
            return "00:00", "23:59"
        times = re.findall(r"(\d{1,2}):(\d{2})\s*([AP]M)", line)
        if len(times) >= 2:
            def conv(h, m, ap):
                h = int(h) % 12 + (12 if ap == "PM" else 0)
                return f"{h:02d}:{m}"
            return conv(*times[0]), conv(*times[-1])
    return "09:00", "18:00"


def place_score(rating: float, count: int) -> float:
    return min(10.0, max(0.0, (rating or 3.5) * 1.6 + math.log10(max(count, 1)) * 0.8))


def can_view(db: Session, trip: Trip, user: Optional[User]) -> bool:
    if trip.owner_id is None or (user and trip.owner_id == user.id):
        return True
    return bool(user and _group_role(db, trip, user))


def can_edit(db: Session, trip: Trip, user: Optional[User]) -> bool:
    if trip.owner_id is None or (user and trip.owner_id == user.id):
        return True
    return bool(user and _group_role(db, trip, user) in ("owner", "editor"))


def _group_role(db: Session, trip: Trip, user: User) -> Optional[str]:
    row = (db.query(GroupMember.role).join(Group, Group.id == GroupMember.group_id)
           .filter(Group.trip_id == trip.id, GroupMember.user_id == user.id).first())
    return row[0] if row else None


def get_trip(db: Session, trip_id: int, user: Optional[User], edit: bool = False) -> Trip:
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    if not (can_edit if edit else can_view)(db, trip, user):
        raise HTTPException(403, "You do not have access to this trip")
    return trip


def trip_days(trip: Trip) -> int:
    start, end = date.fromisoformat(trip.start_date), date.fromisoformat(trip.end_date)
    return (end - start).days + 1


def item_dict(i: ItineraryItem) -> Dict[str, Any]:
    return {c.name: getattr(i, c.name) for c in ItineraryItem.__table__.columns}


def load_items(db: Session, trip: Trip) -> List[Dict[str, Any]]:
    rows = db.query(ItineraryItem).filter_by(trip_id=trip.id).order_by(ItineraryItem.day, ItineraryItem.position)
    return [item_dict(i) for i in rows]


def reflow(items: List[Dict[str, Any]], mode: str, delays: Optional[Dict[int, int]] = None) -> List[Dict[str, Any]]:
    """Recompute times day by day. Completed and locked items keep their times; skipped items are ignored."""
    delays = delays or {}
    by_day: Dict[int, List[Dict]] = {}
    for it in items:
        by_day.setdefault(it["day"], []).append(it)
    for day, day_items in by_day.items():
        day_items.sort(key=lambda x: x["position"])
        cursor = hhmm_to_min(DAY_START)
        prev = None
        delay_left = delays.get(day, 0)
        for it in day_items:
            it["overflow"] = False
            if it["status"] == "skipped":
                continue
            if it["status"] == "completed" or it["locked"]:
                cursor = max(cursor, hhmm_to_min(it["end"]))
                prev = it
                continue
            travel = travel_minutes((prev["lat"], prev["lng"]), (it["lat"], it["lng"]), mode) if prev and it.get("lat") is not None and prev.get("lat") is not None else 0
            start = cursor + travel
            if delay_left:
                start += delay_left
                delay_left = 0
            if it["kind"] == "meal":
                target = 12 * 60 + 30 if it["name"].lower().startswith("lunch") else 19 * 60 + 30
                start = max(start, target)
            it["travel_min"] = travel
            it["start"] = min_to_hhmm(start)
            it["end"] = min_to_hhmm(start + it["duration_min"])
            it["overflow"] = start + it["duration_min"] > hhmm_to_min(LATEST_END)
            cursor = start + it["duration_min"]
            if it.get("lat") is not None:
                prev = it
    return items


def save_items(db: Session, trip: Trip, items: List[Dict[str, Any]]) -> None:
    existing = {i.id: i for i in db.query(ItineraryItem).filter_by(trip_id=trip.id)}
    keep = set()
    columns = {c.name for c in ItineraryItem.__table__.columns} - {"id", "trip_id"}
    for it in items:
        row = existing.get(it.get("id")) if it.get("id") else None
        if row is None:
            row = ItineraryItem(trip_id=trip.id)
            db.add(row)
        for c in columns:
            if c in it:
                setattr(row, c, it[c])
        db.flush()
        it["id"] = row.id
        keep.add(row.id)
    for item_id, row in existing.items():
        if item_id not in keep:
            db.delete(row)
    trip.version = (trip.version or 1) + 1
    trip.updated_at = datetime.utcnow()


def _new_item(day: int, position: int, place: Dict[str, Any], kind: str = "visit") -> Dict[str, Any]:
    category = place.get("category") or "culture"
    outdoor = place.get("outdoor")
    return {
        "id": None, "day": day, "position": position, "kind": kind, "name": place["name"], "category": category,
        "place_id": place.get("place_id", ""), "address": place.get("address", ""),
        "lat": place.get("lat"), "lng": place.get("lng"), "rating": place.get("rating") or 0,
        "rating_count": place.get("rating_count") or 0,
        "outdoor": (category in OUTDOOR_CATEGORIES) if outdoor is None else outdoor,
        "start": DAY_START, "end": DAY_START, "duration_min": place.get("duration_min") or VISIT_MINUTES.get(category, 75),
        "travel_min": 0, "status": "planned", "locked": False, "completed_at": None,
    }


def preferred_categories(db: Session, user: Optional[User]) -> Dict[str, float]:
    """Average explicit feedback per category -> small ranking boost (-0.5..+0.5)."""
    if not user:
        return {}
    rows = db.query(ItemFeedback.category, ItemFeedback.rating).filter_by(user_id=user.id).all()
    agg: Dict[str, List[int]] = {}
    for cat, r in rows:
        agg.setdefault(cat, []).append(r)
    return {c: (sum(v) / len(v) - 3) / 4 for c, v in agg.items()}


def rank_places(places: List[Dict], boosts: Dict[str, float], exclude: set) -> List[Dict]:
    out = [p for p in places if p["name"] not in exclude and p.get("place_id") not in exclude]
    return sorted(out, key=lambda p: place_score(p["rating"], p["rating_count"]) + boosts.get(p["category"], 0),
                  reverse=True)


async def restaurant_near(lat: float, lng: float, food_pref: str, exclude: set) -> Optional[Dict]:
    veg = (food_pref or "").lower() in VEG_WORDS
    query = "pure vegetarian restaurant" if veg else "popular restaurant"
    try:
        found = await search_places(query, near=(lat, lng), limit=10)
    except HTTPException:
        return None
    found = [p for p in found if p["name"] not in exclude and road_km((lat, lng), (p["lat"], p["lng"])) <= 3]
    found.sort(key=lambda p: place_score(p["rating"], p["rating_count"]), reverse=True)
    if not found:
        return None
    best = dict(found[0])
    best["category"] = "food"
    best["outdoor"] = False
    return best


# ---------- generation ----------

async def generate(db: Session, owner: Optional[User], destination: str, start: date, end: date,
                   prefs: Dict[str, Any], hotel: Optional[Dict[str, float]] = None,
                   must_visit: Optional[List[str]] = None) -> Trip:
    from app.rootplan.models.multiday_schemas import (Location, MultiDayPlanRequest, MultiDayPOI,
                                                      PlanningConstraints, UserPreferences)
    from app.rootplan.planner.multiday_planner import plan_multiday_itinerary
    from app.rootplan.services.google_distance import distance_source

    if end < start:
        raise HTTPException(400, "End date must be on or after the start date")
    days = (end - start).days + 1
    if days > 14:
        raise HTTPException(400, "Trips can be at most 14 days")
    center = await geocode(destination)
    origin = (hotel["lat"], hotel["lng"]) if hotel and hotel.get("lat") and hotel.get("lng") else center
    interests = [i.lower() for i in prefs.get("interests", [])]
    pace = prefs.get("pace") if prefs.get("pace") in PACE else "normal"
    hours, max_visits, _ = PACE[pace]
    mode = prefs.get("mode") or "driving"

    queries = [f"top tourist attractions in {destination}"]
    for interest in interests:
        queries += [f"{q} in {destination}" for q in INTEREST_QUERIES.get(interest, [])]
    results = await asyncio.gather(*[search_places(q, near=center, limit=20) for q in queries[:8]],
                                   return_exceptions=True)
    pool: Dict[str, Dict] = {}
    for res in results:
        if isinstance(res, Exception):
            continue
        for p in res:
            if p["category"] == "lodging" or (p["category"] == "food" and "food" not in interests):
                continue
            if road_km(center, (p["lat"], p["lng"])) > 60:
                continue
            pool.setdefault(p["place_id"] or p["name"], p)

    forced: List[Dict] = []
    wanted = list(must_visit or [])
    if owner:
        wanted += [w.name for w in db.query(WishlistItem).filter_by(user_id=owner.id)
                   if w.city and w.city.lower() == destination.lower()]
    for name in wanted[:10]:
        try:
            hit = await search_places(f"{name}, {destination}", near=center, limit=1)
        except HTTPException:
            hit = []
        if hit:
            forced.append(hit[0])
            pool.pop(hit[0]["place_id"] or hit[0]["name"], None)
    if not pool and not forced:
        raise HTTPException(404, f"No places found for '{destination}'")

    boosts = preferred_categories(db, owner)
    ranked = forced + rank_places(list(pool.values()), boosts, set())
    ranked = ranked[: max_visits * days * 2]
    weights = {}
    for interest in interests:
        for cat, w in INTEREST_WEIGHTS.get(interest, {}).items():
            weights[cat] = max(weights.get(cat, 0), w)
    if interests:
        weights = {c: weights.get(c, 0.3) for c in UserPreferences.model_fields}

    poi_list = []
    for idx, p in enumerate(ranked, 1):
        open_t, close_t = _open_close(p.get("hours", []))
        cat = p["category"] if p["category"] in UserPreferences.model_fields else "culture"
        score = 10.0 if p in forced else place_score(p["rating"], p["rating_count"])
        poi_list.append(MultiDayPOI(id=idx, name=p["name"], lat=p["lat"], lng=p["lng"],
                                    duration=VISIT_MINUTES.get(p["category"], 75) / 60, open=open_t, close=close_t,
                                    category=cat, score=round(score, 2)))
    state = {"estimated": False}
    distance_source.set(state)
    request = MultiDayPlanRequest(
        start_location=Location(lat=origin[0], lng=origin[1]), days=days, available_hours_per_day=hours,
        poi_list=poi_list, user_preferences=UserPreferences(**weights),
        constraints=PlanningConstraints(max_pois_per_day=max_visits, min_pois_per_day=1),
        start_time=DAY_START, transportation_mode="walking" if mode == "walking" else "driving")
    try:
        plan = await plan_multiday_itinerary(request)
        schedule = {d.day: [ranked[s.poi_id - 1] for s in d.schedule] for d in plan.itinerary}
    except Exception as e:  # the solver can fail on odd inputs; fall back to a greedy nearest-neighbour plan
        logger.warning(f"Planner failed, using greedy fallback: {e}")
        schedule = _greedy_days(ranked, origin, days, max_visits)
        state["estimated"] = True

    trip = Trip(owner_id=owner.id if owner else None, destination=destination, start_date=start.isoformat(),
                end_date=end.isoformat(), start_lat=origin[0], start_lng=origin[1], preferences=json.dumps(prefs),
                distance_source="estimate" if state["estimated"] else "google")
    db.add(trip)
    db.flush()

    items: List[Dict] = []
    used = {p["name"] for day_places in schedule.values() for p in day_places}
    for day in range(1, days + 1):
        pos = 0
        for p in schedule.get(day, []):
            pos += 1
            items.append(_new_item(day, pos, p))
        day_visits = [i for i in items if i["day"] == day]
        if not day_visits:
            continue
        reflow(items, mode)
        lunch_after = next((i for i in day_visits if hhmm_to_min(i["end"]) >= 12 * 60), day_visits[-1])
        for label, anchor in (("Lunch", lunch_after), ("Dinner", day_visits[-1])):
            spot = await restaurant_near(anchor["lat"], anchor["lng"], prefs.get("food", ""), used)
            meal = _new_item(day, anchor["position"], spot or {"name": "", "lat": anchor["lat"], "lng": anchor["lng"],
                                                               "category": "food", "outdoor": False}, kind="meal")
            meal["name"] = f"{label} at {spot['name']}" if spot else f"{label} break"
            meal["duration_min"] = 60
            if spot:
                used.add(spot["name"])
            if label == "Lunch":
                for i in items:
                    if i["day"] == day and i["position"] > anchor["position"]:
                        i["position"] += 1
                meal["position"] = anchor["position"] + 1
            else:
                meal["position"] = max(i["position"] for i in items if i["day"] == day) + 1
            items.append(meal)
    reflow(items, mode)
    save_items(db, trip, items)
    trip.version = 1
    db.commit()
    return trip


def _greedy_days(ranked: List[Dict], origin: Tuple[float, float], days: int, per_day: int) -> Dict[int, List[Dict]]:
    remaining = list(ranked)
    out: Dict[int, List[Dict]] = {}
    for day in range(1, days + 1):
        here, chosen = origin, []
        while remaining and len(chosen) < per_day:
            nxt = min(remaining, key=lambda p: haversine_km(here, (p["lat"], p["lng"])))
            remaining.remove(nxt)
            chosen.append(nxt)
            here = (nxt["lat"], nxt["lng"])
        out[day] = chosen
    return out


# ---------- serialisation ----------

def itinerary_out(db: Session, trip: Trip, items: Optional[List[Dict]] = None) -> Dict[str, Any]:
    items = items if items is not None else load_items(db, trip)
    prefs = loads(trip.preferences, {})
    start = date.fromisoformat(trip.start_date)
    days = []
    for d in range(1, trip_days(trip) + 1):
        slots = []
        for it in sorted([i for i in items if i["day"] == d], key=lambda x: x["position"]):
            slots.append({
                "item_id": it["id"], "start_time": it["start"], "end_time": it["end"], "status": it["status"],
                "kind": it["kind"], "locked": it["locked"], "travel_min": it["travel_min"],
                "overflow": it.get("overflow", False), "priority": 1, "flexibility": 0 if it["locked"] else 1,
                "activity": {
                    "id": str(it["id"]), "name": it["name"], "description": it["address"],
                    "location": {"latitude": it["lat"], "longitude": it["lng"], "address": it["address"],
                                 "city": trip.destination, "country": ""},
                    "activity_type": it["category"], "estimated_duration": it["duration_min"],
                    "rating": it["rating"], "rating_count": it["rating_count"], "place_id": it["place_id"],
                    "weather_dependent": bool(it["outdoor"]), "booking_required": False,
                },
            })
        days.append({"day": d, "date": (start + timedelta(days=d - 1)).isoformat(), "time_slots": slots,
                     "total_budget": 0, "total_travel_time": sum(s["travel_min"] for s in slots
                                                                 if s["status"] != "skipped")})
    return {
        "id": str(trip.id), "user_id": str(trip.owner_id) if trip.owner_id else None, "destination": trip.destination,
        "start_date": trip.start_date, "end_date": trip.end_date, "status": trip.status, "version": trip.version,
        "distance_source": trip.distance_source,
        "distance_note": "Travel times are estimates (Google Routes unavailable)." if trip.distance_source != "google" else "",
        "start_location": {"lat": trip.start_lat, "lng": trip.start_lng}, "user_preferences": prefs,
        "total_budget": prefs.get("budget") or 0, "days": days,
        "created_at": trip.created_at.isoformat(), "updated_at": (trip.updated_at or trip.created_at).isoformat(),
    }


# ---------- create / read ----------

def _prefs_from_trip_in(body: TripIn) -> Dict[str, Any]:
    mode = {"walking": "walking", "bicycle": "bicycle", "public-transport": "public-transport",
            "train": "public-transport", "car": "driving", "plane": "driving"}.get(body.transportPreference or "", "driving")
    return {"interests": body.interests, "food": body.foodPreference or "both", "budget": body.budget,
            "pace": body.pace or "normal", "company": body.companyType, "travelers": body.travelers,
            "pets": bool(body.withPets), "mode": mode, "eco": bool(body.ecoMode)}


@router.post("/trips")
async def create_trip(body: TripIn, user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    start = _parse_date(body.startDate, date.today())
    end = _parse_date(body.endDate, start)
    trip = await generate(db, user, body.destination.strip(), start, end, _prefs_from_trip_in(body),
                          body.hotel, body.mustVisit)
    return itinerary_out(db, trip)


@router.post("/itinerary/create")
async def create_itinerary(body: CreateItineraryIn, user: Optional[User] = Depends(optional_user),
                           db: Session = Depends(get_db)):
    up = body.user_preferences or {}
    transport = (up.get("preferred_transport") or ["driving"])[0]
    prefs = {"interests": up.get("interests", []), "food": up.get("food_preference", "both"),
             "budget": body.budget_limit, "pace": up.get("pace", "normal"), "company": up.get("travel_style"),
             "mode": "walking" if transport == "walking" else "driving", "eco": bool(up.get("eco_mode"))}
    start = _parse_date(body.start_date, date.today())
    trip = await generate(db, user, body.destination.strip(), start, _parse_date(body.end_date, start), prefs,
                          None, body.must_visit_places)
    return itinerary_out(db, trip)


@router.get("/trips")
def my_trips(user: User = Depends(current_user), db: Session = Depends(get_db)):
    group_trip_ids = [g.trip_id for g in db.query(Group).join(GroupMember, GroupMember.group_id == Group.id)
                      .filter(GroupMember.user_id == user.id, Group.trip_id.isnot(None))]
    trips = db.query(Trip).filter((Trip.owner_id == user.id) | (Trip.id.in_(group_trip_ids))) \
        .order_by(Trip.start_date.desc()).all()
    return [_trip_summary(db, t, user) for t in trips]


def _trip_summary(db: Session, t: Trip, user: Optional[User]) -> Dict[str, Any]:
    items = db.query(ItineraryItem).filter_by(trip_id=t.id, kind="visit").all()
    return {"id": t.id, "destination": t.destination, "start_date": t.start_date, "end_date": t.end_date,
            "status": t.status, "owned": bool(user and t.owner_id == user.id),
            "visits": len(items), "completed": sum(1 for i in items if i.status == "completed")}


@router.get("/itinerary/user/{user_id}")
def user_itineraries(user_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.id != user_id:
        raise HTTPException(403, "You can only list your own itineraries")
    return [itinerary_out(db, t) for t in db.query(Trip).filter_by(owner_id=user_id).order_by(Trip.created_at.desc())]


@router.get("/itinerary/{trip_id:int}")
def get_itinerary(trip_id: int, user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    return itinerary_out(db, get_trip(db, trip_id, user))


@router.delete("/itinerary/{trip_id:int}")
def delete_itinerary(trip_id: int, user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    trip = get_trip(db, trip_id, user, edit=True)
    if trip.owner_id and (not user or trip.owner_id != user.id):
        raise HTTPException(403, "Only the trip owner can delete it")
    db.query(ItineraryItem).filter_by(trip_id=trip.id).delete()
    db.query(Alert).filter_by(trip_id=trip.id).delete()
    db.delete(trip)
    db.commit()
    return {"deleted": True}


@router.put("/itinerary/{trip_id:int}/preferences")
async def update_preferences(trip_id: int, prefs: Dict[str, Any], user: Optional[User] = Depends(optional_user),
                             db: Session = Depends(get_db)):
    """Regenerates the trip with new preferences, keeping completed and locked stops."""
    trip = get_trip(db, trip_id, user, edit=True)
    merged = {**loads(trip.preferences, {}), **prefs}
    kept = [i for i in load_items(db, trip) if i["status"] == "completed" or i["locked"]]
    owner = db.get(User, trip.owner_id) if trip.owner_id else None
    fresh = await generate(db, owner, trip.destination, date.fromisoformat(trip.start_date),
                           date.fromisoformat(trip.end_date), merged, {"lat": trip.start_lat, "lng": trip.start_lng})
    new_items = [i for i in load_items(db, fresh) if i["name"] not in {k["name"] for k in kept}]
    db.query(ItineraryItem).filter_by(trip_id=fresh.id).delete()
    db.delete(fresh)
    for i in new_items:
        i["id"] = None
    items = kept + new_items
    for day in {i["day"] for i in items}:
        for pos, it in enumerate(sorted([i for i in items if i["day"] == day],
                                        key=lambda x: (x["status"] != "completed", x["start"])), 1):
            it["position"] = pos
    trip.preferences = json.dumps(merged)
    reflow(items, merged.get("mode", "driving"))
    save_items(db, trip, items)
    db.commit()
    return itinerary_out(db, trip)


# ---------- live updates ----------

@router.get("/itinerary/{trip_id:int}/current-weather")
async def current_weather(trip_id: int, user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    trip = get_trip(db, trip_id, user)
    w = await weather(trip.start_lat, trip.start_lng)
    start = date.fromisoformat(trip.start_date)
    trip_forecast = []
    for d in range(trip_days(trip)):
        day = (start + timedelta(days=d)).isoformat()
        trip_forecast.append(w["days"].get(day) or {"date": day, "condition": "forecast not available yet"})
    return {**w["current"], "source": w["source"], "trip_forecast": trip_forecast}


async def _weather_ops(db: Session, trip: Trip, items: List[Dict]) -> Tuple[List[Dict], List[str]]:
    """For outdoor stops on wet days, propose the best indoor alternative nearby."""
    w = await weather(trip.start_lat, trip.start_lng)
    start = date.fromisoformat(trip.start_date)
    ops, notes = [], []
    taken = {i["name"] for i in items}
    for it in items:
        if it["kind"] != "visit" or it["status"] != "planned" or it["locked"] or not it["outdoor"]:
            continue
        day = (start + timedelta(days=it["day"] - 1)).isoformat()
        forecast = w["days"].get(day)
        if not forecast or not forecast["wet"]:
            continue
        alts = await alternatives_for(it, "indoor", taken)
        if alts:
            taken.add(alts[0]["name"])
            ops.append({"op": "replace", "item_id": it["id"], "place": alts[0]})
            notes.append(f"Day {it['day']}: {forecast['condition']} ({forecast['precipitation_probability']}% rain) "
                         f"- swap {it['name']} for {alts[0]['name']}")
    return ops, notes


@router.get("/itinerary/{trip_id:int}/alerts")
async def alerts(trip_id: int, user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    trip = get_trip(db, trip_id, user)
    try:
        ops, notes = await _weather_ops(db, trip, load_items(db, trip))
    except HTTPException:
        ops, notes = [], []
    for note in notes:
        if not db.query(Alert).filter_by(trip_id=trip.id, alert_type="weather", message=note).first():
            db.add(Alert(trip_id=trip.id, alert_type="weather", severity="medium", message=note,
                         suggested_actions=json.dumps(["Review the indoor alternative", "Apply weather reschedule"])))
    db.commit()
    return [{"id": str(a.id), "itinerary_id": str(trip.id), "alert_type": a.alert_type, "severity": a.severity,
             "message": a.message, "suggested_actions": loads(a.suggested_actions, []),
             "timestamp": a.created_at.isoformat(), "acknowledged": a.acknowledged}
            for a in db.query(Alert).filter_by(trip_id=trip.id).order_by(Alert.created_at.desc())]


@router.post("/itinerary/{trip_id:int}/alerts/{alert_id}/acknowledge")
def acknowledge(trip_id: int, alert_id: int, user: Optional[User] = Depends(optional_user),
                db: Session = Depends(get_db)):
    trip = get_trip(db, trip_id, user)
    alert = db.query(Alert).filter_by(id=alert_id, trip_id=trip.id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.acknowledged = True
    db.commit()
    return {"acknowledged": True}


# ---------- alternatives & rescheduling ----------

ALT_QUERIES = {
    "indoor": "indoor attractions museums",
    "nearby": "attractions",
    "cheaper": "free public parks and attractions",
    "relaxed": "calm cafes and gardens",
    "food": "restaurants",
}


async def alternatives_for(item: Dict, reason: str, taken: set, radius_km: float = 3) -> List[Dict]:
    query = ALT_QUERIES.get(reason, "attractions")
    found = await search_places(query, near=(item["lat"], item["lng"]), limit=20)
    out = []
    for p in found:
        if p["name"] in taken or p["category"] == "lodging":
            continue
        if reason == "indoor" and p["outdoor"]:
            continue
        if reason in ("relaxed", "cheaper") and p["category"] in ("entertainment", "shopping"):
            continue
        dist = road_km((item["lat"], item["lng"]), (p["lat"], p["lng"]))
        if dist > radius_km:
            continue
        out.append({**p, "distance_km": round(dist, 2)})
    out.sort(key=lambda p: place_score(p["rating"], p["rating_count"]) - p["distance_km"] * 0.5, reverse=True)
    return out[:5]


@router.get("/itinerary/{trip_id:int}/items/{item_id}/alternatives")
async def item_alternatives(trip_id: int, item_id: int, reason: str = "nearby", radius_km: float = 3,
                            user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    trip = get_trip(db, trip_id, user)
    items = load_items(db, trip)
    item = next((i for i in items if i["id"] == item_id), None)
    if not item:
        raise HTTPException(404, "Item not found")
    return {"item_id": item_id, "reason": reason,
            "alternatives": await alternatives_for(item, reason, {i["name"] for i in items}, min(radius_km, 20))}


def apply_ops(items: List[Dict], ops: List[Dict], mode: str) -> List[Dict]:
    """Pure: returns a new item list with the operations applied and times recomputed."""
    items = [dict(i) for i in items]
    by_id = {i["id"]: i for i in items}
    delays: Dict[int, int] = {}
    for op in ops:
        kind = op["op"]
        target = by_id.get(op.get("item_id")) if op.get("item_id") else None
        if kind in ("skip", "replace") and (not target or target["status"] != "planned"):
            raise HTTPException(400, f"Item {op.get('item_id')} cannot be changed (missing, completed or skipped)")
        if kind in ("skip", "replace") and target["locked"]:
            raise HTTPException(400, f"{target['name']} is confirmed; unlock it first")
        if kind == "skip":
            target["status"] = "skipped"
        elif kind == "replace":
            place = op["place"]
            fresh = _new_item(target["day"], target["position"], place, kind=target["kind"])
            fresh["id"] = target["id"]
            if target["kind"] == "meal":
                fresh["name"] = f"{target['name'].split(' ')[0]} at {place['name']}"
                fresh["duration_min"] = target["duration_min"]
            target.update(fresh)
        elif kind == "delay":
            delays[op["day"]] = delays.get(op["day"], 0) + op["minutes"]
        elif kind == "add":
            day = op["day"]
            day_items = [i for i in items if i["day"] == day]
            dinner = next((i for i in day_items if i["kind"] == "meal" and i["name"].lower().startswith("dinner")
                           and i["status"] == "planned"), None)
            if dinner:  # new stops go before dinner, which stays the last thing of the day
                position = dinner["position"]
                for i in day_items:
                    if i["position"] >= position:
                        i["position"] += 1
            else:
                position = max([i["position"] for i in day_items] or [0]) + 1
            items.append(_new_item(day, position, op["place"]))
        elif kind == "reorder":
            for pos, item_id in enumerate(op["order"], 1):
                if item_id in by_id and by_id[item_id]["day"] == op["day"]:
                    by_id[item_id]["position"] = pos
    return reflow(items, mode, delays)


class RescheduleIn(BaseModel):
    reason: str = Field(..., pattern="^(weather|relaxed|delay|skip_next|indoor_next|optimize)$")
    day: Optional[int] = None
    minutes: Optional[int] = Field(None, ge=1, le=600)


def next_item(trip: Trip, items: List[Dict], kind: str = "visit") -> Optional[Dict]:
    today_idx = (date.today() - date.fromisoformat(trip.start_date)).days + 1
    planned = [i for i in items if i["status"] == "planned" and i["kind"] == kind]
    upcoming = [i for i in planned if i["day"] >= max(1, today_idx)] or planned
    return min(upcoming, key=lambda i: (i["day"], i["position"])) if upcoming else None


@router.post("/itinerary/{trip_id:int}/reschedule")
async def reschedule(trip_id: int, body: RescheduleIn, user: Optional[User] = Depends(optional_user),
                     db: Session = Depends(get_db)):
    """Builds a proposal (operations + preview). Nothing is saved until /apply."""
    trip = get_trip(db, trip_id, user, edit=True)
    items = load_items(db, trip)
    mode = loads(trip.preferences, {}).get("mode", "driving")
    ops, notes = await build_ops(trip, items, body.reason, body.day, body.minutes)
    preview = apply_ops(items, ops, mode) if ops else items
    return {"reason": body.reason, "ops": ops, "notes": notes, "version": trip.version,
            "preview": itinerary_out(db, trip, preview)}


async def build_ops(trip: Trip, items: List[Dict], reason: str, day: Optional[int] = None,
                    minutes: Optional[int] = None) -> Tuple[List[Dict], List[str]]:
    taken = {i["name"] for i in items}
    if reason == "weather":
        return await _weather_ops(None, trip, items)
    nxt = next_item(trip, items)
    if reason in ("skip_next", "indoor_next"):
        if not nxt:
            return [], ["Nothing left to change"]
        if reason == "skip_next":
            return [{"op": "skip", "item_id": nxt["id"]}], [f"Skip {nxt['name']}"]
        alts = await alternatives_for(nxt, "indoor", taken)
        if not alts:
            return [], [f"No indoor alternative found near {nxt['name']}"]
        return [{"op": "replace", "item_id": nxt["id"], "place": alts[0]}], [f"Replace {nxt['name']} with {alts[0]['name']}"]
    day = day or (nxt["day"] if nxt else 1)
    planned = [i for i in items if i["day"] == day and i["status"] == "planned" and i["kind"] == "visit" and not i["locked"]]
    if reason == "relaxed":
        keep = sorted(planned, key=lambda i: place_score(i["rating"], i["rating_count"]), reverse=True)[:2]
        drop = [i for i in planned if i not in keep]
        return ([{"op": "skip", "item_id": i["id"]} for i in drop],
                [f"Drop {i['name']} to slow down day {day}" for i in drop] or ["Day is already relaxed"])
    if reason == "delay":
        mins = minutes or 30
        ops = [{"op": "delay", "day": day, "minutes": mins}]
        shifted = apply_ops(items, ops, loads(trip.preferences, {}).get("mode", "driving"))
        overflow = [i for i in shifted if i["day"] == day and i.get("overflow") and i["status"] == "planned"]
        ops += [{"op": "skip", "item_id": i["id"]} for i in overflow]
        return ops, [f"Shift day {day} by {mins} min"] + [f"{i['name']} no longer fits; skip it" for i in overflow]
    if reason == "optimize":
        order = _nearest_order(trip, [i for i in items if i["day"] == day])
        return [{"op": "reorder", "day": day, "order": order}], [f"Reorder day {day} to cut travel"]
    return [], []


def _nearest_order(trip: Trip, day_items: List[Dict]) -> List[int]:
    fixed = sorted([i for i in day_items if i["status"] != "planned" or i["locked"]], key=lambda i: i["position"])
    free = [i for i in day_items if i["status"] == "planned" and not i["locked"]]
    here = (fixed[-1]["lat"], fixed[-1]["lng"]) if fixed and fixed[-1].get("lat") else (trip.start_lat, trip.start_lng)
    order = [i["id"] for i in fixed]
    visits = [i for i in free if i["kind"] == "visit"]
    meals = [i for i in free if i["kind"] == "meal"]
    while visits:
        nxt = min(visits, key=lambda i: haversine_km(here, (i["lat"], i["lng"])))
        visits.remove(nxt)
        order.append(nxt["id"])
        here = (nxt["lat"], nxt["lng"])
    # meals go back where lunch/dinner belong: lunch after the first half, dinner last
    for m in sorted(meals, key=lambda m: m["name"]):
        order.insert(max(1, len(order) // 2) if m["name"].lower().startswith("lunch") else len(order), m["id"])
    return order


@router.post("/itinerary/{trip_id:int}/route-optimization")
async def route_optimization(trip_id: int, day_index: int = 0, user: Optional[User] = Depends(optional_user),
                             db: Session = Depends(get_db)):
    trip = get_trip(db, trip_id, user, edit=True)
    items = load_items(db, trip)
    ops, _ = await build_ops(trip, items, "optimize", day_index + 1)
    items = apply_ops(items, ops, loads(trip.preferences, {}).get("mode", "driving"))
    save_items(db, trip, items)
    db.commit()
    return itinerary_out(db, trip)


@router.post("/itinerary/{trip_id:int}/apply")
def apply(trip_id: int, body: ApplyIn, user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    trip = get_trip(db, trip_id, user, edit=True)
    if body.expected_version and body.expected_version != trip.version:
        raise HTTPException(409, "The itinerary changed since this proposal was made; please review it again")
    items = load_items(db, trip)
    ops = [o.model_dump(exclude_none=True) for o in body.ops]
    items = apply_ops(items, ops, loads(trip.preferences, {}).get("mode", "driving"))
    save_items(db, trip, items)
    db.commit()
    return itinerary_out(db, trip)


@router.patch("/itinerary/{trip_id:int}/items/{item_id}")
def lock_item(trip_id: int, item_id: int, body: Dict[str, bool], user: Optional[User] = Depends(optional_user),
              db: Session = Depends(get_db)):
    trip = get_trip(db, trip_id, user, edit=True)
    row = db.query(ItineraryItem).filter_by(id=item_id, trip_id=trip.id).first()
    if not row:
        raise HTTPException(404, "Item not found")
    if "locked" in body:
        row.locked = bool(body["locked"])
    db.commit()
    return itinerary_out(db, trip)


@router.post("/itinerary/{trip_id:int}/items/{item_id}/complete")
def complete_item(trip_id: int, item_id: int, body: CheckInIn, user: User = Depends(current_user),
                  db: Session = Depends(get_db)):
    """Check in at a stop. Points need a location within 500 m of the place and a trip you own or belong to."""
    trip = get_trip(db, trip_id, user, edit=True)
    row = db.query(ItineraryItem).filter_by(id=item_id, trip_id=trip.id).first()
    if not row:
        raise HTTPException(404, "Item not found")
    if row.status == "skipped":
        raise HTTPException(400, "This stop was skipped")
    verified = (body.lat is not None and body.lng is not None and row.lat is not None
                and haversine_km((body.lat, body.lng), (row.lat, row.lng)) <= CHECKIN_RADIUS_KM)
    if row.status != "completed":
        row.status = "completed"
        row.completed_at = datetime.utcnow()
    awards: List[Dict] = []
    if trip.status == "planned":
        trip.status = "active"
    if verified and row.kind == "visit":
        place_key = row.place_id or f"{row.name}|{trip.destination}".lower()
        meta = {"place": place_key, "name": row.name, "category": row.category, "lat": row.lat, "lng": row.lng,
                "rating_count": row.rating_count, "city": trip.destination}
        for kind, key, pts in (("visit_complete", f"visit:{row.id}", None),
                               ("new_attraction", f"place:{place_key}", None)):
            e = rewards.award(db, user.id, kind, key, pts, city=trip.destination, trip_id=trip.id, meta=meta)
            if e:
                awards.append({"type": kind, "points": e.points, "title": row.name})
        km = road_km((trip.start_lat, trip.start_lng), (row.lat, row.lng))
        if km >= DISTANCE_BONUS_MIN_KM:
            bonus = min(100, int(km // 10) * 5)
            e = rewards.award(db, user.id, "distance_bonus", f"distance:{row.id}", bonus, city=trip.destination,
                              trip_id=trip.id, meta={"km": round(km, 1), "method": "road estimate from trip start"})
            if e:
                awards.append({"type": "distance_bonus", "points": e.points, "title": f"{round(km)} km from trip start"})
        awards += rewards.evaluate(db, user.id, trip.destination, trip.id)
        visits = db.query(ItineraryItem).filter_by(trip_id=trip.id, kind="visit").all()
        days_done = {i.day for i in visits if i.status == "completed"}
        awards += rewards.trip_completion(db, user.id, trip, len(days_done), trip_days(trip))
    db.commit()
    return {"verified": verified, "awards": awards,
            "message": None if verified else "Marked as visited. Points need location access within 500 m of the place.",
            "itinerary": itinerary_out(db, trip)}


class FeedbackIn(BaseModel):
    rating: int = Field(..., ge=1, le=5)


@router.post("/itinerary/{trip_id:int}/items/{item_id}/feedback")
def item_feedback(trip_id: int, item_id: int, body: FeedbackIn, user: User = Depends(current_user),
                  db: Session = Depends(get_db)):
    trip = get_trip(db, trip_id, user)
    row = db.query(ItineraryItem).filter_by(id=item_id, trip_id=trip.id).first()
    if not row:
        raise HTTPException(404, "Item not found")
    fb = db.query(ItemFeedback).filter_by(user_id=user.id, item_id=item_id).first() or \
        ItemFeedback(user_id=user.id, item_id=item_id, category=row.category)
    fb.rating = body.rating
    db.add(fb)
    db.commit()
    return {"saved": True}


def fit_place(trip: Trip, items: List[Dict], place: Dict) -> Optional[Dict]:
    """Pick the remaining day where adding this place costs the least travel and still fits before 21:30."""
    today_idx = max(1, (date.today() - date.fromisoformat(trip.start_date)).days + 1)
    mode = loads(trip.preferences, {}).get("mode", "driving")
    best = None
    for day in range(today_idx, trip_days(trip) + 1):
        trial = apply_ops(items, [{"op": "add", "day": day, "place": place}], mode)
        added = trial[-1]
        if any(i.get("overflow") and i["status"] == "planned" for i in trial if i["day"] == day):
            continue
        cost = added["travel_min"]
        if best is None or cost < best[1]:
            best = (day, cost, added)
    if not best:
        return None
    return {"op": "add", "day": best[0], "place": place, "start": best[2]["start"], "travel_min": best[1]}


@router.post("/itinerary/{trip_id:int}/propose-add")
def propose_add(trip_id: int, place: PlaceIn, user: Optional[User] = Depends(optional_user),
                db: Session = Depends(get_db)):
    trip = get_trip(db, trip_id, user, edit=True)
    items = load_items(db, trip)
    if any(i["name"] == place.name for i in items if i["status"] != "skipped"):
        raise HTTPException(409, f"{place.name} is already in this itinerary")
    op = fit_place(trip, items, place.model_dump())
    if not op:
        return {"fits": False, "message": f"{place.name} does not fit in the remaining days"}
    return {"fits": True, "ops": [{k: v for k, v in op.items() if k in ("op", "day", "place")}],
            "message": f"Add {place.name} on day {op['day']} at {op['start']}", "version": trip.version}


@router.get("/itinerary/{trip_id:int}/export")
def export(trip_id: int, format: str = "json", user: Optional[User] = Depends(optional_user),
           db: Session = Depends(get_db)):
    trip = get_trip(db, trip_id, user)
    data = itinerary_out(db, trip)
    if format == "json":
        return data
    lines = [f"LiveTrip itinerary: {trip.destination} ({trip.start_date} to {trip.end_date})", ""]
    for d in data["days"]:
        lines.append(f"Day {d['day']} - {d['date']}")
        for s in d["time_slots"]:
            mark = {"completed": "[x]", "skipped": "[-]"}.get(s["status"], "[ ]")
            lines.append(f"  {mark} {s['start_time']}-{s['end_time']}  {s['activity']['name']}")
        lines.append("")
    return PlainTextResponse("\n".join(lines), headers={
        "Content-Disposition": f'attachment; filename="livetrip-{trip.id}.txt"'})
