"""Free open-data place search, used when Google Places is unavailable (quota reached, no key, outage).

- Wikipedia's location search finds notable sights (museums, forts, temples, parks...) around a point.
- Nominatim (OpenStreetMap) finds cities and named places, and restaurants, cafes, hotels and shops in an area.

Neither has star ratings: rating stays 0 (the UI hides it) and rating_count holds a notability score used only
for ranking (Wikipedia article length, or Nominatim's importance).
"""
import asyncio
import math
import re
import time
from typing import Dict, List, Optional, Tuple

import httpx
from fastapi import HTTPException

USER_AGENT = "LiveTrip/1.0 (travel itinerary planner; https://github.com/yashrajarvind06/LiveTrip)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
WIKIPEDIA = "https://en.wikipedia.org/w/api.php"
TIMEOUT = httpx.Timeout(12, connect=5)  # a dead service should fail in seconds, not minutes

# Wikipedia description/title keyword -> Google-style type (so geo.categorize() treats both sources alike)
SIGHT_TYPES = [
    (r"museum|gallery|planetarium|science cent", "museum"),
    (r"temple|mosque|masjid|church|cathedral|basilica|dargah|shrine|gurdwara|monastery|ashurkhana|synagogue", "place_of_worship"),
    (r"zoo|zoological", "zoo"),
    (r"amusement|theme park|water park", "amusement_park"),
    (r"beach", "beach"),
    (r"lake|waterfall|falls|hill\b|hills|valley|reserve|sanctuary|national park|viewpoint|cave", "natural_feature"),
    (r"park|garden", "park"),
    (r"fort|palace|tomb|mausoleum|monument|memorial|historic|heritage|baradari|gate\b|minaret|ruins|"
     r"archaeolog|stepwell|step well|observatory|clock tower|statue|haveli", "historical_landmark"),
    (r"market|bazaar|mall", "market"),
    (r"restaurant|cafe|eatery", "restaurant"),
]
NOT_A_SIGHT = re.compile(r"hotel|station|constituency|hospital|college|university|school|office|company|ministry|"
                         r"government|authority|neighbourhood|neighborhood|suburb|village|district|road|street|"
                         r"bank|airport|depot|corporation|organisation|organization|body of", re.IGNORECASE)
# Nominatim result type -> Google-style type
NOMINATIM_TYPES = {
    "museum": "museum", "gallery": "art_gallery", "fort": "castle", "castle": "castle", "palace": "castle",
    "park": "park", "garden": "park", "beach": "beach", "zoo": "zoo", "place_of_worship": "place_of_worship",
    "monument": "historical_landmark", "memorial": "historical_landmark", "attraction": "tourist_attraction",
    "viewpoint": "natural_feature", "restaurant": "restaurant", "fast_food": "restaurant", "food_court": "restaurant",
    "cafe": "cafe", "hotel": "lodging", "hostel": "lodging", "guest_house": "lodging", "motel": "lodging",
    "mall": "shopping_mall", "marketplace": "market", "bar": "bar", "pub": "bar", "nightclub": "night_club",
}

# intent -> (sight types kept from Wikipedia, words searched with Nominatim inside the area)
INTENTS: Dict[str, Tuple[set, List[str]]] = {
    "attractions": ({"museum", "place_of_worship", "zoo", "amusement_park", "beach", "natural_feature", "park",
                     "historical_landmark", "market"}, []),
    "history": ({"historical_landmark", "place_of_worship"}, []),
    "museum": ({"museum"}, []),
    "nature": ({"park", "natural_feature", "beach", "zoo"}, []),
    "beach": ({"beach"}, ["beach"]),
    "shopping": ({"market"}, ["mall", "market"]),
    "night": (set(), ["bar", "pub"]),
    "food": (set(), ["restaurant"]),
    "cafe": (set(), ["cafe"]),
    "lodging": (set(), ["hotel", "hostel", "guest house"]),
}
KEYWORDS = [  # a query can match several intents
    (("restaurant", "food", "eat", "dining", "thali", "dhaba"), "food"),
    (("cafe", "coffee"), "cafe"),
    (("hotel", "hostel", "stay", "resort", "homestay", "lodging", "apartment"), "lodging"),
    (("museum", "indoor", "gallery"), "museum"),
    (("park", "garden", "lake", "nature", "viewpoint", "trek", "scenic", "calm", "peaceful", "lakeside"), "nature"),
    (("temple", "heritage", "historic", "fort", "palace", "monument", "culture", "cultural"), "history"),
    (("market", "shopping", "mall"), "shopping"),
    (("nightlife", "bar", "pub", "club"), "night"),
    (("beach",), "beach"),
    (("attraction", "tourist", "places", "spots", "family", "adventure", "interesting", "visit", "free"), "attractions"),
]
VEG_PATTERN = re.compile(r"\b(veg|vegetarian|bhavan|udupi|udipi|sagar|annapurna|saravana|shudh|pure|tiffins?)\b",
                         re.IGNORECASE)

_nominatim_lock = asyncio.Lock()
_last_nominatim = 0.0
_wiki_cache: Dict[Tuple[float, float], Tuple[float, "asyncio.Task"]] = {}
WIKI_TTL_S = 6 * 3600


def intents_for(query: str) -> List[str]:
    q = query.lower()
    found = [intent for words, intent in KEYWORDS if any(re.search(rf"\b{w}", q) for w in words)]
    return list(dict.fromkeys(found))


def _place(name: str, lat: float, lng: float, types: List[str], place_id: str, notability: int,
           address: str = "") -> Dict:
    from .geo import OUTDOOR_CATEGORIES, categorize
    category = categorize(types)
    return {"name": name, "place_id": place_id, "address": address, "lat": lat, "lng": lng, "rating": 0,
            "rating_count": notability, "types": types, "category": category,
            "outdoor": category in OUTDOOR_CATEGORIES, "source": "openstreetmap", "hours": [],
            "vegetarian": bool(VEG_PATTERN.search(name))}


async def _get(url: str, params) -> Dict:
    """GET JSON, retrying once when the service asks us to slow down."""
    last = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
                r = await client.get(url, params=params)
                if r.status_code in (429, 502, 503, 504) and attempt == 0:
                    await asyncio.sleep(1.5)
                    continue
                r.raise_for_status()
                return r.json()
        except (httpx.HTTPError, ValueError) as e:
            last = e
            if attempt == 0 and not isinstance(e, httpx.ConnectTimeout):
                await asyncio.sleep(1.0)
                continue
            break
    raise HTTPException(503, f"Place search is unavailable right now ({last.__class__.__name__ if last else 'busy'}). "
                             "Please try again in a minute.")


async def nominatim(query: str, limit: int = 5, center: Optional[Tuple[float, float]] = None,
                    radius_km: float = 4) -> List[Dict]:
    """Free-text search; with a center it searches only inside that area (e.g. 'restaurant' near a stop)."""
    global _last_nominatim
    params = {"q": query, "format": "jsonv2", "limit": limit, "accept-language": "en"}
    if center:
        dlat = radius_km / 111
        dlng = radius_km / (111 * max(0.2, math.cos(math.radians(center[0]))))
        params.update(viewbox=f"{center[1] - dlng},{center[0] + dlat},{center[1] + dlng},{center[0] - dlat}", bounded=1)
    async with _nominatim_lock:  # Nominatim policy: at most one request per second
        wait = 1.05 - (time.monotonic() - _last_nominatim)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            rows = await _get(NOMINATIM, params)
        finally:
            _last_nominatim = time.monotonic()
    out = []
    for row in rows:
        kind = row.get("type", "")
        if row.get("category") in ("place", "boundary"):
            types = ["locality"]
        else:
            types = [NOMINATIM_TYPES.get(kind, "tourist_attraction")]
        name = row.get("name") or row.get("display_name", "").split(",")[0]
        if not name:
            continue
        out.append(_place(name, float(row["lat"]), float(row["lon"]), types,
                          f"osm:{(row.get('osm_type') or 'x')[0]}{row.get('osm_id')}",
                          int(float(row.get("importance") or 0) * 1000), row.get("display_name", "")))
    return out


async def _wiki_pages(center: Tuple[float, float]) -> List[Dict]:
    """Articles within 10 km of a point, fetched once per area and reused by every search for a few hours."""
    key = (round(center[0], 2), round(center[1], 2))
    hit = _wiki_cache.get(key)
    if hit and hit[0] > time.monotonic():
        task = hit[1]
    else:
        task = asyncio.ensure_future(_get(WIKIPEDIA, {
            "action": "query", "format": "json", "formatversion": 2, "generator": "geosearch",
            "ggscoord": f"{key[0]}|{key[1]}", "ggsradius": 10000, "ggslimit": 500,
            "prop": "coordinates|description|info", "colimit": "max"}))  # coordinates default to 10 pages
        _wiki_cache[key] = (time.monotonic() + WIKI_TTL_S, task)
    try:
        data = await asyncio.shield(task)
    except Exception:
        _wiki_cache.pop(key, None)
        raise
    return (data.get("query") or {}).get("pages", [])


async def wikipedia_sights(center: Tuple[float, float], keep: set) -> List[Dict]:
    out = []
    for page in await _wiki_pages(center):
        coords = (page.get("coordinates") or [{}])[0]
        text = f"{page.get('description', '')} {page['title']}"
        if "lat" not in coords or NOT_A_SIGHT.search(page.get("description", "")):
            continue
        sight = next((t for pattern, t in SIGHT_TYPES if re.search(pattern, text, re.IGNORECASE)), None)
        if sight not in keep:
            continue
        title = re.sub(r",\s*[^,]+$", "", page["title"]) if "," in page["title"] else page["title"]  # "X, Hyderabad"
        out.append(_place(title, coords["lat"], coords["lon"], [sight, "tourist_attraction"],
                          f"wiki:{page['pageid']}", page.get("length", 0) // 10, page.get("description", "")))
    return out


async def search(query: str, near: Optional[Tuple[float, float]] = None) -> List[Dict]:
    """Same contract as geo._google_text_search: a list of place dicts, best first."""
    intents = intents_for(query)
    match = re.search(r"\b(?:in|near)\s+(.+)$", query, re.IGNORECASE)
    city = match.group(1).strip() if match else None
    if not intents or (near is None and not city):
        return await nominatim(query)  # a specific place or a city name
    if near is None:
        hits = await nominatim(city, limit=1)
        if not hits:
            return []
        near = (hits[0]["lat"], hits[0]["lng"])

    keep = set().union(*(INTENTS[i][0] for i in intents))
    jobs = []
    if keep:
        # Wikipedia's location search reaches 10 km; four extra points ~9 km out cover the rest of a city
        step = 0.08
        centers = [near] + [(near[0] + dy * step, near[1] + dx * step) for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        jobs += [wikipedia_sights(c, keep) for c in centers]
    veg = bool(re.search(r"\b(veg|vegetarian|vegan)\b", query.lower()))
    words = [w for i in intents for w in INTENTS[i][1]]
    if veg and "food" in intents:
        words.insert(0, "vegetarian restaurant")
    radius = 6 if "lodging" in intents else 4
    jobs += [nominatim(w, limit=40, center=near, radius_km=radius) for w in words]
    results = await asyncio.gather(*jobs, return_exceptions=True)
    places, seen = [], set()
    for res in results:
        if isinstance(res, Exception):
            continue
        for p in res:
            if p["name"].lower() not in seen and p["types"] != ["locality"]:
                seen.add(p["name"].lower())
                places.append(p)
    if not places and any(isinstance(r, Exception) for r in results):
        raise next(r for r in results if isinstance(r, Exception))
    from .geo import haversine_km
    places.sort(key=lambda p: ((veg and p["vegetarian"]), p["rating_count"] - haversine_km(near, (p["lat"], p["lng"])) * 20),
                reverse=True)
    return places[:25]
