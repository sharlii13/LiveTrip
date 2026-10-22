"""LiveTrip features: accounts, living itineraries, recommendations, assistant, photos, rewards, groups."""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from database import Base, SessionLocal, engine
from . import accounts, placeinfo, planning, photos, recommend, rewards, social
from .seed import seed

logger = logging.getLogger("livetrip")


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Any unhandled error: log the traceback and tell the client what failed instead of a bare 500."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={
        "detail": f"Something went wrong on the server ({exc.__class__.__name__}: {str(exc)[:200]}). "
                  "Please try again; if it keeps happening, check the backend window for the full error."})


def install(app: FastAPI) -> None:
    """Create tables, seed starter data, mount uploads and register routes (before the older routers)."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
    photos.PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=photos.UPLOAD_DIR), name="uploads")
    app.add_exception_handler(Exception, _unexpected_error)
    for module in (accounts, planning, recommend, placeinfo, photos, rewards, social):
        app.include_router(module.router)
