"""Restaurant, stay, mood and nearby recommendations, plus the conversational assistant."""
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import User, get_db
from . import ai_assistant
from .core import loads, optional_user
from .geo import VISIT_MINUTES, geocode, road_km, search_places, travel_minutes
from .models import Trip
from .planning import (build_ops, get_trip, itinerary_out, load_items, next_item, place_score, preferred_categories,
                       apply_ops)

router = APIRouter(prefix="/api", tags=["recommendations"])

MOODS = {
    "adventurous": "adventure activities and viewpoints",
    "relaxed": "quiet cafes gardens and lakes",
    "cultural": "museums heritage sites and temples",
    "food": "famous local food places",
    "nature": "parks nature trails and gardens",
    "family": "family friendly attractions",
    "low-energy": "cafes and short scenic spots",
}
STAY_TYPES = {"hotel": "hotels", "hostel": "hostels", "homestay": "homestays", "resort": "resorts",
              "apartment": "serviced apartments"}
BUDGET_WORDS = {"low": "budget", "medium": "", "high": "luxury"}


def _rank(places: List[Dict], origin: Tuple[float, float], boosts: Dict[str, float], mode: str = "driving") -> List[Dict]:
    out = []
    for p in places:
        km = road_km(origin, (p["lat"], p["lng"]))
        out.append({**p, "distance_km": round(km, 2), "travel_min": travel_minutes(origin, (p["lat"], p["lng"]), mode),
                    "score": round(place_score(p["rating"], p["rating_count"]) + boosts.get(p["category"], 0) - km * 0.3, 2)})
    return sorted(out, key=lambda p: p["score"], reverse=True)


async def restaurants(lat: float, lng: float, diet: str = "any", budget: str = "medium", radius_km: float = 3,
                      family: bool = False, pets: bool = False, boosts: Optional[Dict] = None) -> List[Dict]:
    words = [w for w in (BUDGET_WORDS.get(budget, ""), "pure vegetarian" if diet == "vegetarian" else
                         "vegan" if diet == "vegan" else "", "family friendly" if family else "",
                         "pet friendly" if pets else "") if w]
    found = await search_places(" ".join(words + ["restaurant"]), near=(lat, lng), limit=20)
    found = [p for p in found if p["category"] == "food"]
    ranked = _rank(found, (lat, lng), boosts or {})
    return [p for p in ranked if p["distance_km"] <= radius_km][:10]


@router.get("/recommendations/restaurants")
async def recommend_restaurants(lat: float, lng: float, diet: str = "any", budget: str = "medium",
                                radius_km: float = 3, family: bool = False, pets: bool = False,
                                user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    return {"results": await restaurants(lat, lng, diet, budget, min(radius_km, 20), family, pets,
                                         preferred_categories(db, user)),
            "note": "Ratings and hours come from Google Places; dietary match is based on the place listing."}


@router.get("/recommendations/stays")
async def recommend_stays(trip_id: Optional[int] = None, city: str = "", lat: Optional[float] = None,
                          lng: Optional[float] = None, budget: str = "medium", type: str = "hotel",
                          family: bool = False, pets: bool = False,
                          user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    """Stays near the trip's planned stops. Live prices and availability need a booking API."""
    if trip_id:
        trip = get_trip(db, trip_id, user)
        city = trip.destination
        stops = [(i["lat"], i["lng"]) for i in load_items(db, trip) if i["kind"] == "visit" and i["lat"] is not None]
        center = (sum(s[0] for s in stops) / len(stops), sum(s[1] for s in stops) / len(stops)) if stops \
            else (trip.start_lat, trip.start_lng)
    elif lat is not None and lng is not None:
        center = (lat, lng)
    elif city:
        center = None
    else:
        raise HTTPException(400, "Give a trip_id, a city, or lat/lng")
    words = [BUDGET_WORDS.get(budget, ""), "family friendly" if family else "", "pet friendly" if pets else "",
             STAY_TYPES.get(type, "hotels")]
    query = " ".join(w for w in words if w) + (f" in {city}" if city else "")
    found = [p for p in await search_places(query, near=center, limit=20) if p["category"] == "lodging"]
    ranked = _rank(found, center or (found[0]["lat"], found[0]["lng"]) if found else (0, 0), {})
    return {"results": ranked[:10], "center": center,
            "note": "Distances are to the middle of your planned stops. Prices and availability are not live; "
                    "check with the property or a booking site."}


async def mood_places(mood: str, lat: float, lng: float, radius_km: float = 5, minutes_left: Optional[int] = None,
                      boosts: Optional[Dict] = None, exclude: Optional[set] = None) -> List[Dict]:
    if mood not in MOODS:
        raise HTTPException(400, f"mood must be one of: {', '.join(MOODS)}")
    found = await search_places(MOODS[mood], near=(lat, lng), limit=20)
    ranked = _rank([p for p in found if p["category"] != "lodging" and p["name"] not in (exclude or set())],
                   (lat, lng), boosts or {})
    out = []
    for p in ranked:
        if p["distance_km"] > radius_km:
            continue
        visit = VISIT_MINUTES.get(p["category"], 60)
        if mood == "low-energy":
            visit = min(visit, 45)
        p["visit_min"] = visit
        if minutes_left is not None and visit + p["travel_min"] * 2 > minutes_left:
            continue
        out.append(p)
    return out[:8]


@router.get("/recommendations/mood")
async def recommend_mood(mood: str, lat: float, lng: float, radius_km: float = 5, minutes_left: Optional[int] = None,
                         user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    return {"mood": mood, "results": await mood_places(mood, lat, lng, min(radius_km, 30), minutes_left,
                                                       preferred_categories(db, user))}


@router.get("/recommendations/nearby")
async def recommend_nearby(lat: float, lng: float, radius_km: float = 2, q: str = "interesting places to visit",
                           user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    found = await search_places(q, near=(lat, lng), limit=20)
    ranked = _rank([p for p in found if p["category"] != "lodging"], (lat, lng), preferred_categories(db, user))
    return {"results": [p for p in ranked if p["distance_km"] <= min(radius_km, 30)][:10]}


@router.get("/places/search")
async def places_search(query: str, limit: int = 8, lat: Optional[float] = None, lng: Optional[float] = None):
    """Replaces the older legacy-API search; the itinerary page reads items[].location/rating/types/address."""
    near = (lat, lng) if lat is not None and lng is not None else None
    found = await search_places(query, near=near, limit=max(1, min(limit, 20)))
    return {"query": query, "total": len(found), "items": [
        {"name": p["name"], "place_id": p["place_id"], "address": p["address"], "rating": p["rating"],
         "user_ratings_total": p["rating_count"], "types": p["types"], "category": p["category"],
         "location": {"lat": p["lat"], "lng": p["lng"]}} for p in found]}


# ---------- assistant ----------

class ChatTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    text: str = Field(..., max_length=2000)


class AssistantIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    trip_id: Optional[int] = None
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    history: List[ChatTurn] = Field(default_factory=list, max_length=20)  # the chat so far, oldest first
    page: Optional[str] = Field(None, max_length=200)  # where in the app the traveller is
    language: Optional[str] = Field(None, max_length=10)  # app language code, e.g. "hi"


def _where(trip: Optional[Trip], items: List[Dict], body: AssistantIn) -> Optional[Tuple[float, float]]:
    if body.lat is not None and body.lng is not None:
        return body.lat, body.lng
    if trip:
        nxt = next_item(trip, items)
        return (nxt["lat"], nxt["lng"]) if nxt else (trip.start_lat, trip.start_lng)
    return None


NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                "nine": 9, "ten": 10, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45}


def trip_stats(items: List[Dict]) -> Dict:
    """Totals the traveller asks about: travel time, stops, and each day's span."""
    active = [i for i in items if i["status"] != "skipped"]
    days: Dict[int, Dict] = {}
    for i in sorted(active, key=lambda i: (i["day"], i["position"])):
        d = days.setdefault(i["day"], {"day": i["day"], "travel_min": 0, "stops": 0, "meals": 0,
                                       "start": i["start"], "end": i["end"]})
        d["travel_min"] += i.get("travel_min") or 0
        d["stops" if i["kind"] == "visit" else "meals"] += 1
        d["end"] = i["end"]
    return {"travel_min": sum(d["travel_min"] for d in days.values()),
            "stops": sum(d["stops"] for d in days.values()),
            "visited": sum(1 for i in active if i["kind"] == "visit" and i["status"] == "completed"),
            "days": list(days.values())}


def _hm(minutes: int) -> str:
    return f"{minutes // 60} h {minutes % 60} min" if minutes >= 60 else f"{minutes} min"


def _numbers_to_digits(text: str) -> str:
    text = re.sub(r"\bhalf\s+(?:an?\s+)?hour", "0.5 hour", text)
    text = re.sub(r"\b(?:an|a)\s+(hour|hr)", r"1 \1", text)
    words = "|".join(sorted(NUMBER_WORDS, key=len, reverse=True))  # longest first so "forty-five" wins
    return re.sub(r"\b(" + words + r")\b", lambda m: str(NUMBER_WORDS[m.group(1)]), text)


TOP_PLACES = re.compile(
    r"(?:(?:top|best|famous|popular|must[- ]see)\s+)?(\d+)?\s*(?:tourist\s+)?"
    r"(?:attractions?|places(?: to (?:visit|see|go))?|sights|things to do|spots|destinations)\s+"
    r"(?:in|of|at|around|near)\s+([a-z][a-z .'-]{1,60})")


async def _top_places(match: "re.Match") -> Dict:
    """ "top 5 attractions of kerala": the best-rated sights of a city or region, no trip needed."""
    where = match.group(2).strip(" .?!'").removeprefix("the ")
    n = max(1, min(int(match.group(1) or 5), 10))
    try:
        found = await search_places(f"top tourist attractions in {where}", limit=20)
    except HTTPException:
        return {"intent": "top_places", "reply": "I can't search places right now. Please try again in a minute."}
    found = [p for p in found if p["category"] not in ("lodging", "food")]
    found.sort(key=lambda p: place_score(p["rating"], p["rating_count"]), reverse=True)
    if not found:
        return {"intent": "top_places", "reply": f"I couldn't find attractions for \"{where}\"."}
    lines = [f"- {p['name']}" + (f" ({p['rating']}★, {p['rating_count']:,} reviews)" if p.get("rating") else "")
             for p in found[:n]]
    return {"intent": "top_places", "places": found[:n],
            "reply": f"Top {min(n, len(found))} attractions in {where.title()}:\n" + "\n".join(lines)}


def _names(places: List[Dict], n: int = 5) -> str:
    return "\n".join(f"- {p['name']} ({str(p['rating']) + '★, ' if p.get('rating') else ''}{p['distance_km']} km)"
                     for p in places[:n])  # open-data places have no rating: say nothing rather than "0★"


async def _rules(message: str, body: "AssistantIn", trip: Optional[Trip], items: List[Dict], user: Optional[User],
                 db: Session) -> Dict:
    """Keyword assistant (used without an Anthropic key): recognises common trip requests and calls the matching
    recommendation or rescheduling feature. Changes come back as a proposal the user confirms."""
    text = _numbers_to_digits(message.lower())
    prefs = loads(trip.preferences, {}) if trip else {}
    where = _where(trip, items, body)
    boosts = preferred_categories(db, user)
    taken = {i["name"] for i in items}

    async def proposal(reason: str, day: Optional[int] = None, minutes: Optional[int] = None):
        if not trip:
            return {"reply": "Open one of your trips first so I can change its plan.", "intent": reason}
        ops, notes = await build_ops(trip, items, reason, day, minutes)
        if not ops:
            return {"reply": notes[0] if notes else "There is nothing to change.", "intent": reason}
        preview = itinerary_out(db, trip, apply_ops(items, ops, prefs.get("mode", "driving")))
        return {"reply": "Here is what I would change:\n" + "\n".join(f"- {n}" for n in notes) +
                         "\nConfirm to apply it.", "intent": reason,
                "proposal": {"ops": ops, "notes": notes, "version": trip.version, "preview": preview}}

    def need_location():
        return {"reply": "Share your location or open a trip so I know where you are.", "intent": "location"}

    top = TOP_PLACES.search(text)
    if top:
        return await _top_places(top)
    km_match = re.search(r"(\d+(?:\.\d+)?)\s*km", text)
    hours_match = re.search(r"(\d+(?:\.\d+)?)\s*(hour|hr)", text)
    delay_match = (re.search(r"(?:late|delay\w*|stuck)\D*(\d+)\s*(?:min|minute)", text)  # "delayed by 30 min"
                   or re.search(r"(\d+)\s*(?:min|minute)s?\s+(?:late|behind|delay)", text))  # "40 minutes late"

    if delay_match:
        return await proposal("delay", minutes=int(delay_match.group(1)))
    if "skip" in text:
        return await proposal("skip_next")
    if "indoor" in text or ("replace" in text and "rain" in text):
        return await proposal("indoor_next")
    if "weather" in text or "rain" in text:
        return await proposal("weather")
    if any(w in text for w in ("relax", "tired", "slow down", "slower", "exhausted")):
        result = await proposal("relaxed")
        if where:
            calm = await mood_places("relaxed", *where, radius_km=3, boosts=boosts, exclude=taken)
            result["places"] = calm
            if calm:
                result["reply"] += "\n\nCalm spots nearby:\n" + _names(calm)
        return result
    if any(w in text for w in ("hotel", "stay", "accommodation", "hostel")):
        if not trip:
            return {"reply": "Open a trip first and I will find stays near its stops.", "intent": "stays"}
        stays = await recommend_stays(trip_id=trip.id, budget=prefs.get("budget_level", "medium"), user=user, db=db)
        return {"reply": "Stays close to your planned stops:\n" + _names(stays["results"]) + "\n" + stays["note"],
                "intent": "stays", "places": stays["results"]}
    if any(w in text for w in ("vegetarian", "vegan", "restaurant", "eat", "food", "lunch", "dinner", "hungry")):
        if not where:
            return need_location()
        diet = "vegan" if "vegan" in text else "vegetarian" if ("vegetarian" in text or prefs.get("food") == "vegetarian") else "any"
        found = await restaurants(*where, diet=diet, radius_km=float(km_match.group(1)) if km_match else 3, boosts=boosts)
        return {"reply": (f"{'Vegetarian places' if diet == 'vegetarian' else 'Vegan places' if diet == 'vegan' else 'Places'} to eat nearby:\n"
                          + _names(found)) if found else "I could not find a matching restaurant nearby.",
                "intent": "restaurants", "places": found}
    if any(w in text for w in ("cheap", "budget", "free", "cost less")):
        if not trip:
            return {"reply": "Open a trip so I know which stop to replace.", "intent": "cheaper"}
        from .planning import alternatives_for
        nxt = next_item(trip, items)
        if not nxt:
            return {"reply": "Nothing left to replace.", "intent": "cheaper"}
        alts = await alternatives_for(nxt, "cheaper", taken)
        if not alts:
            return {"reply": f"No cheaper option found near {nxt['name']}.", "intent": "cheaper"}
        preview = itinerary_out(db, trip, apply_ops(items, [{"op": "replace", "item_id": nxt["id"], "place": alts[0]}],
                                                    prefs.get("mode", "driving")))
        return {"reply": f"Cheaper option instead of {nxt['name']}: {alts[0]['name']}. Confirm to swap.",
                "intent": "cheaper", "places": alts,
                "proposal": {"ops": [{"op": "replace", "item_id": nxt["id"], "place": alts[0]}],
                             "notes": [f"Replace {nxt['name']} with {alts[0]['name']}"], "version": trip.version,
                             "preview": preview}}
    if hours_match or "left" in text:
        if not where:
            return need_location()
        minutes = int(float(hours_match.group(1)) * 60) if hours_match else 120
        found = await mood_places("cultural", *where, radius_km=5, minutes_left=minutes, boosts=boosts, exclude=taken)
        return {"reply": f"With about {minutes // 60}h {minutes % 60}m you can fit:\n" + _names(found)
                if found else "Nothing fits in that time nearby.", "intent": "time_left", "places": found}
    if km_match or any(w in text for w in ("nearby", "near me", "around", "interesting")):
        if not where:
            return need_location()
        radius = float(km_match.group(1)) if km_match else 2
        found = await recommend_nearby(*where, radius_km=radius, user=user, db=db)
        return {"reply": f"Within {radius:g} km:\n" + _names(found["results"]) if found["results"]
                else f"Nothing found within {radius:g} km.", "intent": "nearby", "places": found["results"]}
    if "next" in text:
        if not trip:
            return {"reply": "Open a trip and I will tell you what is next.", "intent": "next"}
        nxt = next_item(trip, items)
        if not nxt:
            return {"reply": "You have finished every planned stop. Nice work!", "intent": "next"}
        travel = ""
        if body.lat is not None and body.lng is not None:
            travel = f" It is about {travel_minutes((body.lat, body.lng), (nxt['lat'], nxt['lng']), prefs.get('mode', 'driving'))} min away."
        return {"reply": f"Next up: {nxt['name']} on day {nxt['day']} at {nxt['start']}.{travel}", "intent": "next",
                "item_id": nxt["id"]}
    for mood in MOODS:
        if mood.split("-")[0] in text:
            if not where:
                return need_location()
            found = await mood_places(mood, *where, boosts=boosts, exclude=taken)
            return {"reply": f"For a {mood} mood:\n" + _names(found) if found else "Nothing matched nearby.",
                    "intent": "mood", "places": found}
    if trip and re.search(r"travel(ling)? time|time .*travel|how long .*(travel|driv|commut|on the road)|"
                          r"how many (stops|places)|when .*(day )?(end|finish)|total (travel|time|distance|stops)", text):
        st = trip_stats(items)
        per_day = "\n".join(f"- Day {d['day']}: {_hm(d['travel_min'])} of travel, {d['stops']} stops, "
                             f"{d['start']}-{d['end']}" for d in st["days"])
        return {"intent": "trip_stats", "reply": (
            f"Your {trip.destination} trip has {_hm(st['travel_min'])} of travel in total between "
            f"{st['stops']} stops ({st['visited']} visited so far).\n{per_day}\n"
            "Travel times are estimates between stops, not counting the trip to your first stop.")}
    return {"intent": "help", "reply": (
        "I can help with:\n- \"What should I visit next?\"\n- \"Find a vegetarian restaurant nearby\"\n"
        "- \"Replace my next activity with an indoor attraction\"\n- \"Make the rest of my day more relaxed\"\n"
        "- \"Find something interesting within 2 km\"\n- \"I have only two hours left\"\n- \"Suggest a cheaper alternative\"\n"
        "- \"I'm running 40 minutes late\"")}


def _trip_context(trip: Optional[Trip], items: List[Dict], body: AssistantIn) -> str:
    """What the AI needs to know about the traveller's situation, as compact text."""
    lines = [f"Now: {datetime.now().strftime('%A %d %B %Y, %H:%M')} (server time)",
             f"App page: {body.page or 'unknown'}", f"App language: {body.language or 'en'}"]
    if body.lat is not None and body.lng is not None:
        lines.append(f"Traveller's location: {body.lat:.5f}, {body.lng:.5f}")
    if not trip:
        lines.append("No trip is open.")
        return "\n".join(lines)
    prefs = loads(trip.preferences, {})
    lines.append(f"Open trip: {trip.destination}, {trip.start_date} to {trip.end_date}; food preference "
                 f"{prefs.get('food') or 'none'}; getting around by {prefs.get('mode', 'driving')}.")
    nxt = next_item(trip, items)
    if nxt:
        lines.append(f"Next stop: {nxt['name']} (item_id {nxt['id']}, day {nxt['day']} at {nxt['start']}).")
    st = trip_stats(items)
    lines.append(f"Totals: {st['travel_min']} min of travel between stops, {st['stops']} stops, "
                 f"{st['visited']} visited. Per day: " + "; ".join(
                     f"day {d['day']} {d['start']}-{d['end']}, {d['travel_min']} min travel, {d['stops']} stops"
                     for d in st["days"]) + ".")
    day = None
    for i in sorted(items, key=lambda i: (i["day"], i["position"])):
        if i["day"] != day:
            day = i["day"]
            lines.append(f"Day {day}:")
        rating = f", {i['rating']} stars" if i.get("rating") else ""
        travel = f", {i['travel_min']} min travel before it" if i.get("travel_min") else ""
        lines.append(f"- [{i['id']}] {i['start']}-{i['end']} {i['name']} ({i['kind']}, {i['category']}{rating}, "
                     f"{i['status']}{', confirmed' if i.get('locked') else ''}{travel})")
    return "\n".join(lines)


def _compact(places: List[Dict], n: int = 6) -> List[Dict]:
    keys = ("name", "place_id", "address", "lat", "lng", "rating", "rating_count", "category", "outdoor",
            "distance_km", "travel_min")
    return [{k: p[k] for k in keys if k in p} for p in places[:n]]


def _ai_tools(body: AssistantIn, trip: Optional[Trip], items: List[Dict], user: Optional[User], db: Session):
    """The assistant's tools, each a thin wrapper over an existing LiveTrip feature."""
    from .placeinfo import place_info
    from .planning import alternatives_for

    prefs = loads(trip.preferences, {}) if trip else {}
    boosts = preferred_categories(db, user)
    taken = {i["name"] for i in items}
    last_found: List[Dict] = []

    def point(near: str = "next_stop") -> Optional[Tuple[float, float]]:
        if near == "my_location" and body.lat is not None and body.lng is not None:
            return body.lat, body.lng
        stops = [(i["lat"], i["lng"]) for i in items if i["kind"] == "visit" and i.get("lat") is not None]
        if near == "trip_centre" and stops:
            return sum(s[0] for s in stops) / len(stops), sum(s[1] for s in stops) / len(stops)
        return _where(trip, items, body)

    def no_point():
        return {"error": "No location: ask the traveller to share their location or open a trip."}

    def remember(places: List[Dict]) -> Dict:
        last_found[:] = places
        return {"places": _compact(places)}

    async def around(near: str, near_place: Optional[str]) -> Optional[Tuple[float, float]]:
        if near_place:  # "near the Hawa Mahal in Jaipur": no trip or shared location needed
            return await geocode(f"{near_place}, {trip.destination}" if trip and "," not in near_place else near_place)
        return point(near)

    async def find_places(query: str, near: str = "next_stop", radius_km: float = 3,
                          near_place: Optional[str] = None):
        where = await around(near, near_place)
        if not where:
            return no_point()
        found = await search_places(query[:100], near=where, limit=20)
        ranked = _rank([p for p in found if p["category"] != "lodging" and p["name"] not in taken], where, boosts)
        return remember([p for p in ranked if p["distance_km"] <= min(max(radius_km, 0.5), 30)])

    async def find_restaurants(diet: str = "any", near: str = "next_stop", radius_km: float = 3,
                               near_place: Optional[str] = None):
        where = await around(near, near_place)
        if not where:
            return no_point()
        return remember(await restaurants(*where, diet=diet, radius_km=min(max(radius_km, 0.5), 20), boosts=boosts))

    async def find_stays(budget: str = "medium"):
        if not trip:
            return {"error": "No trip is open."}
        stays = await recommend_stays(trip_id=trip.id, budget=budget, user=user, db=db)
        return {**remember(stays["results"]), "note": stays["note"]}

    async def get_place_info(name: str):
        stop = next((i for i in items if name.lower() in i["name"].lower()), None)
        info = await place_info(name[:200], stop["lat"] if stop else None, stop["lng"] if stop else None,
                                trip.destination if trip else "")
        return {"name": name, "description": info["description"] or "No Wikipedia article found.",
                "url": info["url"]}

    def proposal(ops: List[Dict], notes: List[str]) -> Dict:
        preview = itinerary_out(db, trip, apply_ops(items, ops, prefs.get("mode", "driving")))
        return {"proposed": notes, "proposal": {"ops": ops, "notes": notes, "version": trip.version,
                                                "preview": preview}}

    async def propose_plan_change(change: str, day: Optional[int] = None, minutes: Optional[int] = None):
        if not trip:
            return {"error": "No trip is open."}
        get_trip(db, trip.id, user, edit=True)  # viewers of a shared trip can't change it
        ops, notes = await build_ops(trip, items, change, day, max(1, min(minutes, 600)) if minutes else None)
        return proposal(ops, notes) if ops else {"result": notes[0] if notes else "Nothing to change."}

    async def propose_replace_stop(item_id: int, place_name: Optional[str] = None, reason: str = "nearby"):
        if not trip:
            return {"error": "No trip is open."}
        get_trip(db, trip.id, user, edit=True)
        item = next((i for i in items if i["id"] == item_id), None)
        if not item or item["status"] != "planned":
            return {"error": f"Item {item_id} is not a planned stop of this trip."}
        place = next((p for p in last_found if place_name and p["name"].lower() == place_name.lower()), None)
        if not place:
            alts = await alternatives_for(item, reason if reason in ("indoor", "cheaper", "relaxed") else "nearby",
                                          taken)
            if not alts:
                return {"error": f"No alternative found near {item['name']}."}
            place = alts[0]
        return proposal([{"op": "replace", "item_id": item_id, "place": place}],
                        [f"Replace {item['name']} with {place['name']}"])

    return {"find_places": find_places, "find_restaurants": find_restaurants, "find_stays": find_stays,
            "get_place_info": get_place_info, "propose_plan_change": propose_plan_change,
            "propose_replace_stop": propose_replace_stop}


async def _about_stop(text: str, trip: Optional[Trip], items: List[Dict]) -> Optional[Dict]:
    """Rule-based fallback for "tell me about X" / "when is X" where X is one of the trip's stops."""
    from .placeinfo import place_info
    low = text.lower()
    stop = next((i for i in sorted(items, key=lambda i: -len(i["name"]))
                 if i["kind"] == "visit" and i["name"].lower() in low), None)
    if not stop:
        return None
    info = await place_info(stop["name"], stop["lat"], stop["lng"], trip.destination if trip else "")
    when = f"{stop['name']} is on day {stop['day']}, {stop['start']}-{stop['end']}."
    about = ". ".join((info.get("description") or "").split(". ")[:2]).strip()
    return {"intent": "about", "reply": f"{when} {about}".strip(), "item_id": stop["id"]}


@router.post("/assistant/message")
async def assistant(body: AssistantIn, user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    """The travel assistant. With ANTHROPIC_API_KEY set, Claude answers with the chat history and trip as context
    and calls LiveTrip's features as tools; otherwise (or if Claude is unreachable) the keyword assistant answers.
    Plan changes always come back as a proposal; the app applies them with /itinerary/{id}/apply on confirm."""
    trip = get_trip(db, body.trip_id, user) if body.trip_id else None
    items = load_items(db, trip) if trip else []
    history = [t.model_dump() for t in body.history[-12:]]
    ai_failed = False
    if ai_assistant.available():
        try:
            return await ai_assistant.reply(body.message, history, _trip_context(trip, items, body),
                                            _ai_tools(body, trip, items, user, db))
        except ai_assistant.Unavailable:
            ai_failed = True
    result = await _rules(body.message, body, trip, items, user, db)
    if result.get("intent") != "help":
        return result
    about = await _about_stop(body.message, trip, items)
    if about:
        return about
    # a short follow-up ("and vegetarian?", "within 5 km?") continues the previous request
    previous = next((t["text"] for t in reversed(history) if t["role"] == "user"), None)
    if previous:
        again = await _rules(f"{previous} {body.message}", body, trip, items, user, db)
        if again.get("intent") != "help":
            return again
    if ai_failed:  # be honest: the question was fine, the AI just didn't answer
        result["reply"] = ("My AI brain is busy right now (the Gemini service didn't answer), so I can only do "
                           "quick tasks for a moment. Try again shortly, or ask me something like:\n"
                           + result["reply"].split("\n", 1)[1])
    return result
