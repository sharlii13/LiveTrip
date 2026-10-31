"""Production mode (LIVETRIP_ENV=production): one address for site and API, only the routes the site uses, rate limits.

Local development never loads this: Vite serves the site there and every older route stays available.
"""
import mimetypes
import os
import re
import time
from collections import deque
from pathlib import Path
from typing import Deque, Dict, Tuple

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount

from .core import APP_DIR

mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("text/javascript", ".js")
RANGE_CHUNK = 2 * 1024 * 1024  # a video request gets at most this much; the browser asks again for the rest

# (method, path prefix, requests, seconds) per visitor, first match wins. They protect the Google and Gemini quotas
# and slow down password guessing. shortcut: counted in this process, so it needs one worker; use Redis for several.
LIMITS = [
    ("POST", "/api/auth/login", 10, 60),
    ("POST", "/api/auth/register", 10, 3600),
    ("GET", "/api/auth/google", 20, 60),
    ("POST", "/api/trips", 6, 60),
    ("POST", "/api/itinerary/create", 6, 60),
    ("POST", "/api/itinerary/plan-multi-day", 6, 60),
    ("PUT", "/api/itinerary/", 6, 60),  # regenerates a trip
    ("POST", "/api/assistant/message", 20, 60),
    ("POST", "/api/photos", 10, 60),
    ("GET", "/api/recommendations/", 30, 60),
    ("GET", "/api/places/search", 30, 60),
    ("GET", "/api/places/", 120, 60),
    ("GET", "/api/itinerary/", 120, 60),
    ("POST", "/api/itinerary/", 60, 60),
]


def _keep(route) -> bool:
    """The routes the website uses. The older routers (SOS SMS, flights, location tracking...) have no sign-in checks
    and nothing calls them, so they must not be on the public internet; the API docs go too."""
    if isinstance(route, Mount):
        return True
    module = getattr(getattr(route, "endpoint", None), "__module__", "")
    return module.startswith("livetrip") or module == "routers.multiday" or route.path == "/health"


def _send_file(file: Path, request: Request) -> Response:
    if file.parent.name == "assets":
        cache = "public, max-age=31536000, immutable"  # the name changes whenever the content does
    elif file.suffix in (".html", ".js", ".webmanifest"):
        cache = "no-cache"  # index.html, sw.js: always check for a new version
    else:
        cache = "public, max-age=86400"
    media = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
    headers = {"Cache-Control": cache, "Accept-Ranges": "bytes"}
    wanted = re.fullmatch(r"bytes=(\d*)-(\d*)", request.headers.get("range", ""))
    if not wanted or not (wanted[1] or wanted[2]):
        return FileResponse(file, media_type=media, headers=headers)
    # iPhones won't play a video from a server that can't send parts of it
    size = file.stat().st_size
    start = int(wanted[1]) if wanted[1] else max(0, size - int(wanted[2]))
    end = min(int(wanted[2]) if wanted[1] and wanted[2] else size - 1, size - 1, start + RANGE_CHUNK - 1)
    if start >= size or end < start:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
    with file.open("rb") as f:
        f.seek(start)
        data = f.read(end - start + 1)
    headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return Response(data, status_code=206, media_type=media, headers=headers)


def harden(app: FastAPI, dist: Path = None) -> None:
    """Call last, after every route is registered."""
    dist = Path(dist or os.getenv("LIVETRIP_FRONTEND_DIST", APP_DIR.parents[2] / "frontend" / "dist")).resolve()
    index = dist / "index.html"
    if not index.is_file():
        raise RuntimeError(f"No built website at {dist}: run 'npm run build' in frontend/ or set LIVETRIP_FRONTEND_DIST")

    app.router.routes = [r for r in app.router.routes if _keep(r)]
    app.openapi_url = app.docs_url = app.redoc_url = None

    hits: Dict[Tuple[str, str], Deque[float]] = {}

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        rule = next((r for r in LIMITS if request.method == r[0] and request.url.path.startswith(r[1])), None)
        if rule:
            now = time.monotonic()
            if len(hits) > 50_000:  # don't let a flood of addresses fill the memory
                hits.clear()
            seen = hits.setdefault((request.client.host if request.client else "?", rule[1]), deque())
            while seen and seen[0] <= now - rule[3]:
                seen.popleft()
            if len(seen) >= rule[2]:
                return JSONResponse({"detail": "Too many requests. Please wait a moment and try again."},
                                    status_code=429, headers={"Retry-After": str(int(seen[0] + rule[3] - now) + 1)})
            seen.append(now)
        return await call_next(request)

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def website(path: str, request: Request):
        if path.startswith(("api/", "uploads/")):
            raise HTTPException(404, "Not Found")
        file = (dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(dist):
            return _send_file(file, request)
        if Path(path).suffix:  # a missing file is a 404, not the app page (it would be cached as a script)
            raise HTTPException(404, "Not Found")
        return _send_file(index, request)  # /trips/5 and friends: the app's own router takes it from here
