"""Photo feed: upload, location tagging, reactions, comments, saves, gallery albums, add-to-itinerary."""
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import User, get_db
from . import rewards
from .core import APP_DIR, current_user, optional_user, profile_of
from .geo import search_places, today
from .models import (Group, GroupMember, ItineraryItem, Photo, PhotoComment, PhotoReaction, PhotoSave, PointEvent,
                     Trip)
from .planning import fit_place, get_trip, load_items

router = APIRouter(prefix="/api", tags=["photos"])
UPLOAD_DIR = Path(os.getenv("LIVETRIP_UPLOAD_DIR", APP_DIR / "uploads"))
PHOTO_DIR = UPLOAD_DIR / "photos"
MAX_BYTES = 8 * 1024 * 1024
SIGNATURES = {b"\xff\xd8\xff": ".jpg", b"\x89PNG\r\n\x1a\n": ".png", b"GIF87a": ".gif", b"GIF89a": ".gif"}


def _extension(head: bytes) -> Optional[str]:
    for sig, ext in SIGNATURES.items():
        if head.startswith(sig):
            return ext
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


def _group_ids(db: Session, user: Optional[User]) -> List[int]:
    if not user:
        return []
    return [g.trip_id for g in db.query(Group).join(GroupMember, GroupMember.group_id == Group.id)
            .filter(GroupMember.user_id == user.id, Group.trip_id.isnot(None))]


def _visible(db: Session, photo: Photo, user: Optional[User]) -> bool:
    if photo.visibility == "public" or (user and photo.user_id == user.id):
        return True
    return photo.visibility == "group" and photo.trip_id in _group_ids(db, user)


def photo_out(db: Session, p: Photo, user: Optional[User]) -> Dict:
    owner = db.get(User, p.user_id)
    mine = bool(user and user.id == p.user_id)
    item = db.get(ItineraryItem, p.item_id) if p.item_id else None
    lat, lng = p.lat, p.lng
    if lat is not None and not mine:  # others only see an approximate (~1 km) position
        lat, lng = round(lat, 2), round(lng, 2)
    return {
        "id": p.id, "url": f"/uploads/photos/{p.file_name}", "caption": p.caption,
        "hashtags": [h for h in (p.hashtags or "").split() if h], "place_name": p.place_name,
        "place_id": p.place_id, "city": p.city, "lat": lat, "lng": lng, "location_precise": mine,
        "visibility": p.visibility, "trip_id": p.trip_id, "activity": item.name if item else None,
        "created_at": p.created_at.isoformat(),
        "user": {"id": p.user_id, "name": owner.name if owner else "Traveler",
                 "username": profile_of(db, owner).username if owner else ""},
        "likes": db.query(PhotoReaction).filter_by(photo_id=p.id).count(),
        "comments": db.query(PhotoComment).filter_by(photo_id=p.id).count(),
        "liked_by_me": bool(user and db.query(PhotoReaction).filter_by(photo_id=p.id, user_id=user.id).first()),
        "saved_by_me": bool(user and db.query(PhotoSave).filter_by(photo_id=p.id, user_id=user.id).first()),
        "mine": mine,
    }


@router.post("/photos")
async def upload_photo(file: UploadFile = File(...), caption: str = Form(""), hashtags: str = Form(""),
                       place_name: str = Form(""), place_id: str = Form(""), city: str = Form(""),
                       lat: Optional[float] = Form(None), lng: Optional[float] = Form(None),
                       share_location: bool = Form(False), visibility: str = Form("public"),
                       trip_id: Optional[int] = Form(None), item_id: Optional[int] = Form(None),
                       challenge_code: str = Form(""),
                       user: User = Depends(current_user), db: Session = Depends(get_db)):
    if visibility not in ("public", "private", "group"):
        raise HTTPException(400, "visibility must be public, private or group")
    if len(caption) > 1000 or len(hashtags) > 300 or len(place_name) > 200:
        raise HTTPException(400, "Caption, hashtags or place name is too long")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Photos must be 8 MB or smaller")
    ext = _extension(data[:16])
    if not ext:
        raise HTTPException(400, "Upload a JPEG, PNG, WebP or GIF image")
    trip = None
    if trip_id:
        trip = get_trip(db, trip_id, user)
        city = city or trip.destination
    if item_id:
        item = db.query(ItineraryItem).filter_by(id=item_id, trip_id=trip_id).first() if trip_id else None
        if not item:
            raise HTTPException(404, "That itinerary stop is not part of this trip")
        place_name, place_id = place_name or item.name, place_id or item.place_id
        if share_location and lat is None:
            lat, lng = item.lat, item.lng
    if visibility == "group" and not trip:
        raise HTTPException(400, "Group photos must belong to a trip")
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (PHOTO_DIR / name).write_bytes(data)
    tags = " ".join(sorted({t.strip("#").lower() for t in hashtags.replace(",", " ").split() if t.strip("#")}))
    photo = Photo(user_id=user.id, trip_id=trip_id, item_id=item_id, file_name=name, caption=caption.strip(),
                  hashtags=tags, place_name=place_name.strip(), place_id=place_id, city=city.strip(),
                  lat=lat if share_location else None, lng=lng if share_location else None,
                  visibility=visibility, challenge_code=challenge_code)
    db.add(photo)
    db.flush()
    awards: List[Dict] = []
    if visibility == "public" and photo.place_name:
        awarded_today = db.query(PointEvent).filter(PointEvent.user_id == user.id, PointEvent.kind == "photo_upload",
                                                    func.date(PointEvent.created_at) == today()).count()
        if awarded_today < rewards.PHOTO_AWARDS_PER_DAY:
            key = (photo.place_id or photo.place_name).lower()
            e = rewards.award(db, user.id, "photo_upload", f"photo:{key}:{today()}", city=photo.city,
                              trip_id=trip_id, meta={"photo_id": photo.id, "place": photo.place_name})
            if e:
                awards.append({"type": "photo_upload", "points": e.points, "title": photo.place_name})
        awards += rewards.evaluate(db, user.id, photo.city, trip_id)
    db.commit()
    return {"photo": photo_out(db, photo, user), "awards": awards}


@router.get("/photos/feed")
def feed(city: str = "", hashtag: str = "", place: str = "", limit: int = 30, before_id: Optional[int] = None,
         user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    q = db.query(Photo).filter((Photo.visibility == "public") |
                               ((Photo.visibility == "group") & Photo.trip_id.in_(_group_ids(db, user) or [-1])))
    if city:
        q = q.filter(func.lower(Photo.city) == city.lower())
    if hashtag:
        q = q.filter(Photo.hashtags.like(f"%{hashtag.strip('#').lower()}%"))
    if place:
        q = q.filter(func.lower(Photo.place_name).like(f"%{place.lower()}%"))
    if before_id:
        q = q.filter(Photo.id < before_id)
    photos = q.order_by(Photo.id.desc()).limit(max(1, min(limit, 100))).all()
    return {"photos": [photo_out(db, p, user) for p in photos],
            "next_before_id": photos[-1].id if len(photos) == limit else None}


def _get_visible(db: Session, photo_id: int, user: Optional[User]) -> Photo:
    photo = db.get(Photo, photo_id)
    if not photo or not _visible(db, photo, user):
        raise HTTPException(404, "Photo not found")
    return photo


@router.get("/photos/saved")
def saved(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Photo).join(PhotoSave, PhotoSave.photo_id == Photo.id).filter(PhotoSave.user_id == user.id)
    return [photo_out(db, p, user) for p in rows if _visible(db, p, user)]


@router.get("/photos/{photo_id}")
def get_photo(photo_id: int, user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    photo = _get_visible(db, photo_id, user)
    out = photo_out(db, photo, user)
    out["comment_list"] = [{"id": c.id, "text": c.text, "created_at": c.created_at.isoformat(),
                            "user": {"id": c.user_id, "name": db.get(User, c.user_id).name}}
                           for c in db.query(PhotoComment).filter_by(photo_id=photo.id).order_by(PhotoComment.id)]
    return out


@router.post("/photos/{photo_id}/like")
def like(photo_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    photo = _get_visible(db, photo_id, user)
    row = db.query(PhotoReaction).filter_by(photo_id=photo.id, user_id=user.id).first()
    if row:
        db.delete(row)
    else:
        db.add(PhotoReaction(photo_id=photo.id, user_id=user.id))
    db.commit()
    return photo_out(db, photo, user)


@router.post("/photos/{photo_id}/save")
def save(photo_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    photo = _get_visible(db, photo_id, user)
    row = db.query(PhotoSave).filter_by(photo_id=photo.id, user_id=user.id).first()
    if row:
        db.delete(row)
    else:
        db.add(PhotoSave(photo_id=photo.id, user_id=user.id))
    db.commit()
    return photo_out(db, photo, user)


class CommentIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)


@router.post("/photos/{photo_id}/comments")
def comment(photo_id: int, body: CommentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    photo = _get_visible(db, photo_id, user)
    db.add(PhotoComment(photo_id=photo.id, user_id=user.id, text=body.text.strip()))
    db.commit()
    return get_photo(photo_id, user, db)


@router.delete("/photos/{photo_id}")
def delete_photo(photo_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    photo = db.get(Photo, photo_id)
    if not photo or photo.user_id != user.id:
        raise HTTPException(404, "Photo not found")
    for model in (PhotoReaction, PhotoSave, PhotoComment):
        db.query(model).filter_by(photo_id=photo.id).delete()
    (PHOTO_DIR / photo.file_name).unlink(missing_ok=True)
    db.delete(photo)
    db.commit()
    return {"deleted": True}


@router.get("/gallery/me")
def gallery(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Personal gallery, grouped into trip albums ("Jaipur Trip – October 2026") or city/month albums."""
    albums: Dict[str, Dict] = {}
    for p in db.query(Photo).filter_by(user_id=user.id).order_by(Photo.created_at.desc()):
        trip = db.get(Trip, p.trip_id) if p.trip_id else None
        if trip:
            when = date.fromisoformat(trip.start_date)
            key, title = f"trip:{trip.id}", f"{trip.destination} Trip – {when.strftime('%B %Y')}"
        else:
            key = f"{(p.city or 'Other').lower()}:{p.created_at.strftime('%Y-%m')}"
            title = f"{p.city or 'Other places'} – {p.created_at.strftime('%B %Y')}"
        album = albums.setdefault(key, {"key": key, "title": title, "trip_id": trip.id if trip else None, "photos": []})
        album["photos"].append(photo_out(db, p, user))
    return {"albums": list(albums.values())}


class AddToTripIn(BaseModel):
    trip_id: int


@router.post("/photos/{photo_id}/add-to-itinerary")
async def add_to_itinerary(photo_id: int, body: AddToTripIn, user: User = Depends(current_user),
                           db: Session = Depends(get_db)):
    """Looks up the photo's place and proposes the best day for it. Apply with /itinerary/{id}/apply."""
    photo = _get_visible(db, photo_id, user)
    trip = get_trip(db, body.trip_id, user, edit=True)
    if not photo.place_name:
        raise HTTPException(400, "This photo is not tagged with a place")
    found = await search_places(f"{photo.place_name}, {photo.city}".strip(", "), limit=1)
    if not found:
        raise HTTPException(404, f"Could not find {photo.place_name}")
    place = found[0]
    items = load_items(db, trip)
    if any(i["name"] == place["name"] and i["status"] != "skipped" for i in items):
        return {"fits": False, "message": f"{place['name']} is already in your itinerary"}
    from .geo import road_km
    if road_km((trip.start_lat, trip.start_lng), (place["lat"], place["lng"])) > 80:
        return {"fits": False, "message": f"{place['name']} is too far from your {trip.destination} trip"}
    op = fit_place(trip, items, place)
    if not op:
        return {"fits": False, "message": f"{place['name']} does not fit in the remaining days"}
    return {"fits": True, "place": place, "version": trip.version,
            "ops": [{"op": "add", "day": op["day"], "place": place}],
            "message": f"Add {place['name']} on day {op['day']} at about {op['start']}"}
