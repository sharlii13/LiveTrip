"""Place descriptions and photos from Wikipedia and Wikimedia Commons (free, no key, freely licensed photos).

Matching: the nearest Wikipedia article whose title matches the place name, else a name + city search.
Photos: the article's lead image plus Commons photos taken at that spot, each with author and licence for
attribution. Places with no matching article get no description (nothing is made up) and only photos taken
within a few metres. Results are cached for a day.
"""
import asyncio
import re
import time
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, unquote

from fastapi import APIRouter, HTTPException

from .osm import WIKIPEDIA, _get

COMMONS = "https://commons.wikimedia.org/w/api.php"
SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"
TTL_S = 24 * 3600
MAX_PHOTOS = 5
STOPWORDS = {"the", "of", "and", "a", "shri", "shree", "sri", "temple", "fort", "museum", "park", "lake", "beach"}
NOT_AN_ARTICLE = re.compile(r"constituency|railway station|metro station|bus station|district|ward\b|"
                            r"\(disambiguation\)|list of", re.IGNORECASE)
NOT_A_PHOTO = re.compile(r"\.(svg|gif|tif|tiff|pdf|webm|ogv)$|map|logo|plan|diagram|flag|signature", re.IGNORECASE)

router = APIRouter(prefix="/api", tags=["places"])
_cache: Dict[Tuple, Tuple[float, "asyncio.Task"]] = {}


def _norm(text: str) -> str:
    text = re.sub(r"\(.*?\)", " ", text.lower())
    return re.sub(r"[^a-z0-9 ]", " ", text).strip()


def similarity(a: str, b: str) -> float:
    """How alike two place names are (0..1): spelling plus shared distinctive words, so 'Fort Aguada' scores
    1.0 against 'Fort Aguada' but only ~0.5 against 'Taj Fort Aguada Resort'."""
    a, b = _norm(a), _norm(b)
    ratio = SequenceMatcher(None, a, b).ratio()
    ta, tb = set(a.split()) - STOPWORDS, set(b.split()) - STOPWORDS
    jaccard = len(ta & tb) / len(ta | tb) if ta and tb else ratio
    return (ratio + jaccard) / 2


def _best(name: str, titles: List[str]) -> Optional[str]:
    scored = [(similarity(name, t), -len(t), t) for t in titles if not NOT_AN_ARTICLE.search(t)]
    best = max(scored, default=(0, 0, None))
    return best[2] if best[0] >= 0.6 else None


def _clean(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


async def _find_article(name: str, lat: Optional[float], lng: Optional[float], city: str) -> Optional[str]:
    if lat is not None and lng is not None:
        data = await _get(WIKIPEDIA, {"action": "query", "format": "json", "formatversion": 2, "list": "geosearch",
                                      "gscoord": f"{lat}|{lng}", "gsradius": 1500, "gslimit": 40})
        match = _best(name, [p["title"] for p in data.get("query", {}).get("geosearch", [])])
        if match:
            return match
    data = await _get(WIKIPEDIA, {"action": "query", "format": "json", "formatversion": 2, "list": "search",
                                  "srsearch": f"{name} {city}".strip(), "srlimit": 5})
    return _best(name, [r["title"] for r in data.get("query", {}).get("search", [])])


def _photo(info: Dict, title: str) -> Optional[Dict]:
    ii = (info.get("imageinfo") or [{}])[0]
    meta = ii.get("extmetadata") or {}
    if not ii.get("thumburl") or not str(ii.get("mime", "")).startswith("image/") or NOT_A_PHOTO.search(title):
        return None
    return {"url": ii["thumburl"], "author": _clean(meta.get("Artist", {}).get("value", ""))[:80] or "Unknown",
            "license": _clean(meta.get("LicenseShortName", {}).get("value", "")) or "see source",
            "source_url": f"https://commons.wikimedia.org/wiki/{quote(title.replace(' ', '_'))}"}


async def _commons(params: Dict) -> List[Dict]:
    data = await _get(COMMONS, {"action": "query", "format": "json", "formatversion": 2, "prop": "imageinfo",
                                "iiprop": "url|extmetadata|mime", "iiurlwidth": 960,
                                "iiextmetadatafilter": "Artist|LicenseShortName", **params})
    pages = data.get("query", {}).get("pages", [])
    return [p for p in (_photo(page, page["title"]) for page in pages) if p]


async def _nearby_photos(lat: Optional[float], lng: Optional[float], radius: int) -> List[Dict]:
    if lat is None or lng is None:
        return []
    return await _commons({"generator": "geosearch", "ggscoord": f"{lat}|{lng}", "ggsradius": radius,
                           "ggslimit": 12, "ggsnamespace": 6})


async def _lookup(name: str, lat: Optional[float], lng: Optional[float], city: str) -> Dict:
    # the article search and the photos taken at the spot run at the same time
    title, nearby = await asyncio.gather(_find_article(name, lat, lng, city), _nearby_photos(lat, lng, 250))
    description, url, photos = None, None, []
    if title:
        summary = await _get(SUMMARY + quote(title.replace(" ", "_"), safe=""), {})
        description = (summary.get("extract") or "").strip() or None
        url = (summary.get("content_urls") or {}).get("desktop", {}).get("page")
        lead = (summary.get("originalimage") or summary.get("thumbnail") or {}).get("source", "")
        if lead:
            file_name = re.sub(r"^\d+px-", "", unquote(lead.split("/")[-1]))
            photos += await _commons({"titles": f"File:{file_name}"})
    else:
        nearby = await _nearby_photos(lat, lng, 60)  # without a matching article, only photos taken right there
    seen = {p["url"] for p in photos}
    photos += [p for p in nearby if p["url"] not in seen][: MAX_PHOTOS - len(photos)]
    return {"name": name, "article": title, "description": description, "url": url, "photos": photos,
            "source": "wikipedia" if title else ("wikimedia commons" if photos else "none")}


def prefetch(places: List[Dict], city: str) -> None:
    """Warm the cache for a new trip's stops in the background (three at a time, politely)."""
    async def run():
        for i in range(0, len(places), 3):
            await asyncio.gather(*[place_info(p["name"], p.get("lat"), p.get("lng"), city) for p in places[i:i + 3]],
                                 return_exceptions=True)
    asyncio.ensure_future(run())


@router.get("/places/info")
async def place_info(name: str, lat: Optional[float] = None, lng: Optional[float] = None, city: str = ""):
    if not name.strip() or len(name) > 200:
        raise HTTPException(400, "A place name is required")
    key = (name.strip().lower(), round(lat, 3) if lat is not None else None,
           round(lng, 3) if lng is not None else None)
    hit = _cache.get(key)
    if hit and hit[0] > time.monotonic():
        task = hit[1]
    else:
        task = asyncio.ensure_future(_lookup(name.strip(), lat, lng, city.strip()))
        _cache[key] = (time.monotonic() + TTL_S, task)
    try:
        return await asyncio.shield(task)
    except HTTPException:
        _cache.pop(key, None)
        # descriptions are optional extras: answer with an empty result rather than failing the page
        return {"name": name, "article": None, "description": None, "url": None, "photos": [], "source": "none"}
