"""Restaurant, stay, mood and nearby recommendations, plus the conversational assistant."""
import re
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import User, get_db
from .core import loads, optional_user
from .geo import VISIT_MINUTES, road_km, search_places, travel_minutes
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

class AssistantIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    trip_id: Optional[int] = None
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)


def _where(trip: Optional[Trip], items: List[Dict], body: AssistantIn) -> Optional[Tuple[float, float]]:
    if body.lat is not None and body.lng is not None:
        return body.lat, body.lng
    if trip:
        nxt = next_item(trip, items)
        return (nxt["lat"], nxt["lng"]) if nxt else (trip.start_lat, trip.start_lng)
    return None


NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                "nine": 9, "ten": 10, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45}


def _numbers_to_digits(text: str) -> str:
    text = re.sub(r"\bhalf\s+(?:an?\s+)?hour", "0.5 hour", text)
    text = re.sub(r"\b(?:an|a)\s+(hour|hr)", r"1 \1", text)
    words = "|".join(sorted(NUMBER_WORDS, key=len, reverse=True))  # longest first so "forty-five" wins
    return re.sub(r"\b(" + words + r")\b", lambda m: str(NUMBER_WORDS[m.group(1)]), text)


def _names(places: List[Dict], n: int = 5) -> str:
    return "\n".join(f"- {p['name']} ({p['rating']}★, {p['distance_km']} km)" for p in places[:n])


@router.post("/assistant/message")
async def assistant(body: AssistantIn, user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    """Understands common trip requests and calls the matching recommendation or rescheduling feature.
    Changes come back as a proposal; the app applies them with /itinerary/{id}/apply after the user confirms."""
    text = _numbers_to_digits(body.message.lower())
    trip = get_trip(db, body.trip_id, user) if body.trip_id else None
    items = load_items(db, trip) if trip else []
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
        return {"reply": (f"{'Vegetarian ' if diet == 'vegetarian' else 'Vegan ' if diet == 'vegan' else ''}places to eat nearby:\n"
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
    return {"intent": "help", "reply": (
        "I can help with:\n- \"What should I visit next?\"\n- \"Find a vegetarian restaurant nearby\"\n"
        "- \"Replace my next activity with an indoor attraction\"\n- \"Make the rest of my day more relaxed\"\n"
        "- \"Find something interesting within 2 km\"\n- \"I have only two hours left\"\n- \"Suggest a cheaper alternative\"\n"
        "- \"I'm running 40 minutes late\"")}
