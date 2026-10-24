"""Destination suggestions while typing ("pu" -> Pune, Puducherry, Puri...).

Popular Indian destinations come from a built-in list (instant, always available); anything else comes from Photon,
OpenStreetMap's search-as-you-type service (free, no key). Nominatim's policy forbids per-keystroke use, and Google's
autocomplete would spend the Places quota, so neither is used here.
"""
import time
from typing import Dict, List, Tuple

import httpx
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api", tags=["places"])

# (name, region) - popular with Indian travellers; region is shown under the name
POPULAR: List[Tuple[str, str]] = [
    ("Agra", "Uttar Pradesh"), ("Ahilyanagar", "Maharashtra"), ("Ahmedabad", "Gujarat"), ("Ajmer", "Rajasthan"),
    ("Alleppey", "Kerala"), ("Amritsar", "Punjab"), ("Andaman Islands", "Andaman and Nicobar"),
    ("Aurangabad", "Maharashtra"), ("Ayodhya", "Uttar Pradesh"), ("Badrinath", "Uttarakhand"),
    ("Bengaluru", "Karnataka"), ("Bhopal", "Madhya Pradesh"), ("Bhubaneswar", "Odisha"), ("Bikaner", "Rajasthan"),
    ("Bodh Gaya", "Bihar"), ("Chandigarh", "Chandigarh"), ("Chennai", "Tamil Nadu"), ("Chikmagalur", "Karnataka"),
    ("Coorg", "Karnataka"), ("Corbett", "Uttarakhand"), ("Dalhousie", "Himachal Pradesh"),
    ("Darjeeling", "West Bengal"), ("Dehradun", "Uttarakhand"), ("Delhi", "Delhi"), ("Dharamshala", "Himachal Pradesh"),
    ("Dwarka", "Gujarat"), ("Gangtok", "Sikkim"), ("Goa", "Goa"), ("Gokarna", "Karnataka"), ("Guwahati", "Assam"),
    ("Gwalior", "Madhya Pradesh"), ("Hampi", "Karnataka"), ("Haridwar", "Uttarakhand"), ("Hyderabad", "Telangana"),
    ("Indore", "Madhya Pradesh"), ("Jaipur", "Rajasthan"), ("Jaisalmer", "Rajasthan"), ("Jodhpur", "Rajasthan"),
    ("Kanyakumari", "Tamil Nadu"), ("Kasol", "Himachal Pradesh"), ("Kaziranga", "Assam"),
    ("Khajuraho", "Madhya Pradesh"),
    ("Kochi", "Kerala"), ("Kodaikanal", "Tamil Nadu"), ("Kolkata", "West Bengal"), ("Konark", "Odisha"),
    ("Kovalam", "Kerala"), ("Kullu", "Himachal Pradesh"), ("Leh", "Ladakh"), ("Lonavala", "Maharashtra"),
    ("Lucknow", "Uttar Pradesh"), ("Madurai", "Tamil Nadu"), ("Mahabaleshwar", "Maharashtra"),
    ("Mahabalipuram", "Tamil Nadu"), ("Manali", "Himachal Pradesh"), ("Mangaluru", "Karnataka"),
    ("Mathura", "Uttar Pradesh"), ("McLeod Ganj", "Himachal Pradesh"), ("Mount Abu", "Rajasthan"),
    ("Mumbai", "Maharashtra"), ("Munnar", "Kerala"), ("Mussoorie", "Uttarakhand"), ("Mysuru", "Karnataka"),
    ("Nagpur", "Maharashtra"), ("Nainital", "Uttarakhand"), ("Nashik", "Maharashtra"), ("Ooty", "Tamil Nadu"),
    ("Orchha", "Madhya Pradesh"), ("Pachmarhi", "Madhya Pradesh"), ("Patna", "Bihar"), ("Puducherry", "Puducherry"),
    ("Pune", "Maharashtra"), ("Puri", "Odisha"), ("Pushkar", "Rajasthan"), ("Rameswaram", "Tamil Nadu"),
    ("Ranthambore", "Rajasthan"), ("Rishikesh", "Uttarakhand"), ("Shillong", "Meghalaya"),
    ("Shimla", "Himachal Pradesh"),
    ("Shirdi", "Maharashtra"), ("Somnath", "Gujarat"), ("Spiti Valley", "Himachal Pradesh"),
    ("Srinagar", "Jammu and Kashmir"),
    ("Surat", "Gujarat"), ("Thanjavur", "Tamil Nadu"), ("Thekkady", "Kerala"), ("Tirupati", "Andhra Pradesh"),
    ("Udaipur", "Rajasthan"), ("Ujjain", "Madhya Pradesh"), ("Vadodara", "Gujarat"), ("Varanasi", "Uttar Pradesh"),
    ("Varkala", "Kerala"), ("Visakhapatnam", "Andhra Pradesh"), ("Wayanad", "Kerala"),
]
PHOTON = "https://photon.komoot.io/api/"
PLACE_KEYS = {"place", "tourism", "historic", "natural", "boundary", "leisure"}
_cache: Dict[str, Tuple[float, List[Dict]]] = {}
CACHE_S = 24 * 3600


def popular_matches(q: str) -> List[Dict]:
    """Names starting with what was typed first, then names containing it."""
    q = q.lower()
    starts = [(n, r) for n, r in POPULAR if n.lower().startswith(q)]
    contains = [(n, r) for n, r in POPULAR if q in n.lower() and (n, r) not in starts]
    return [{"name": n, "detail": f"{r}, India", "source": "popular"} for n, r in starts + contains]


async def photon(q: str, limit: int) -> List[Dict]:
    key = q.lower()
    hit = _cache.get(key)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    try:
        async with httpx.AsyncClient(timeout=3, headers={"User-Agent": "LiveTrip/1.0 (trip planner)"}) as client:
            # biased towards India (most LiveTrip trips) but not limited to it
            r = await client.get(PHOTON, params={"q": q, "limit": limit + 4, "lang": "en", "lat": 22.5, "lon": 79})
            r.raise_for_status()
            features = r.json().get("features", [])
    except (httpx.HTTPError, ValueError):
        return []  # suggestions are a convenience: the built-in list still answers
    out = []
    for f in features:
        p = f.get("properties", {})
        if p.get("osm_key") not in PLACE_KEYS or not p.get("name"):
            continue
        detail = ", ".join(x for x in (p.get("state"), p.get("country")) if x and x != p["name"])
        lng, lat = (f.get("geometry", {}).get("coordinates") or [None, None])[:2]
        out.append({"name": p["name"], "detail": detail, "lat": lat, "lng": lng, "source": "openstreetmap"})
    _cache[key] = (time.monotonic() + CACHE_S, out)
    return out


@router.get("/places/suggest")
async def suggest(q: str = Query(..., min_length=1, max_length=80), limit: int = Query(8, ge=1, le=15)):
    q = q.strip()
    found = popular_matches(q)
    if len(q) >= 3 and len(found) < limit:  # two letters are too vague to ask the map for
        found += await photon(q, limit)
    seen, out = set(), []
    for s in found:
        k = (s["name"].lower(), s["detail"].split(",")[0].lower())
        if k not in seen:
            seen.add(k)
            out.append(s)
    return {"query": q, "suggestions": out[:limit]}
