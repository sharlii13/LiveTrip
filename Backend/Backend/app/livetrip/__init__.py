"""LiveTrip features: accounts, living itineraries, recommendations, assistant, photos, rewards, groups."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import Base, SessionLocal, engine
from . import accounts, planning, photos, recommend, rewards, social
from .seed import seed


def install(app: FastAPI) -> None:
    """Create tables, seed starter data, mount uploads and register routes (before the older routers)."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
    photos.PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=photos.UPLOAD_DIR), name="uploads")
    for module in (accounts, planning, recommend, photos, rewards, social):
        app.include_router(module.router)
