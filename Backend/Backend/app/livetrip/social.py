"""Trip groups and voting, saved places (wishlist), and travel history."""
import secrets
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import User, get_db
from . import rewards
from .core import utc_iso, current_user, profile_of
from .geo import road_km, search_places
from .models import (Group, GroupMember, GroupSuggestion, GroupVote, ItineraryItem, Photo, PointEvent, Trip,
                     UserBadge, WishlistItem)
from .photos import photo_out
from .planning import _trip_summary, apply_ops, fit_place, get_trip, itinerary_out, load_items, save_items, trip_days
from .core import loads

router = APIRouter(prefix="/api", tags=["social"])
GROUP_CHALLENGE_POINTS = 1000


# ---------- groups ----------

class GroupIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    trip_id: Optional[int] = None


def _member(db: Session, group_id: int, user: User) -> GroupMember:
    m = db.query(GroupMember).filter_by(group_id=group_id, user_id=user.id).first()
    if not m:
        raise HTTPException(403, "You are not a member of this group")
    return m


@router.post("/groups")
def create_group(body: GroupIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.trip_id:
        trip = db.get(Trip, body.trip_id)
        if not trip or trip.owner_id != user.id:
            raise HTTPException(403, "You can only share trips you own")
    group = Group(name=body.name.strip(), owner_id=user.id, trip_id=body.trip_id,
                  invite_code=secrets.token_urlsafe(6)[:8])
    db.add(group)
    db.flush()
    db.add(GroupMember(group_id=group.id, user_id=user.id, role="owner"))
    db.commit()
    return group_detail(group.id, user, db)


class JoinIn(BaseModel):
    invite_code: str


@router.post("/groups/join")
def join_group(body: JoinIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    group = db.query(Group).filter_by(invite_code=body.invite_code.strip()).first()
    if not group:
        raise HTTPException(404, "No group has that invite code")
    if not db.query(GroupMember).filter_by(group_id=group.id, user_id=user.id).first():
        db.add(GroupMember(group_id=group.id, user_id=user.id, role="viewer"))
        db.commit()
    return group_detail(group.id, user, db)


@router.get("/groups")
def my_groups(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Group, GroupMember.role).join(GroupMember, GroupMember.group_id == Group.id) \
        .filter(GroupMember.user_id == user.id).all()
    out = []
    for g, role in rows:
        trip = db.get(Trip, g.trip_id) if g.trip_id else None
        out.append({"id": g.id, "name": g.name, "role": role, "trip": trip.destination if trip else None,
                    "members": db.query(GroupMember).filter_by(group_id=g.id).count()})
    return out


@router.get("/groups/{group_id}")
def group_detail(group_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    me = _member(db, group_id, user)
    group = db.get(Group, group_id)
    members = db.query(GroupMember).filter_by(group_id=group_id).all()
    points = rewards.leaderboard_points_for_group(db, group_id)
    trip = db.get(Trip, group.trip_id) if group.trip_id else None
    trip_points = 0
    if trip:
        trip_points = int(db.query(func.coalesce(func.sum(PointEvent.points), 0))
                          .filter(PointEvent.trip_id == trip.id, PointEvent.points > 0,
                                  PointEvent.user_id.in_([m.user_id for m in members])).scalar())
    suggestions = []
    for s in db.query(GroupSuggestion).filter_by(group_id=group_id).order_by(GroupSuggestion.id.desc()):
        votes = db.query(GroupVote).filter_by(suggestion_id=s.id).all()
        suggestions.append({"id": s.id, "name": s.name, "category": s.category, "status": s.status,
                            "suggested_by": db.get(User, s.user_id).name, "score": sum(v.value for v in votes),
                            "up": sum(1 for v in votes if v.value > 0), "down": sum(1 for v in votes if v.value < 0),
                            "my_vote": next((v.value for v in votes if v.user_id == user.id), 0)})
    photos = db.query(Photo).filter(Photo.trip_id == group.trip_id, Photo.visibility.in_(["group", "public"])) \
        .order_by(Photo.id.desc()).limit(30).all() if trip else []
    return {
        "id": group.id, "name": group.name, "invite_code": group.invite_code if me.role in ("owner", "editor") else None,
        "my_role": me.role,
        "members": [{"user_id": m.user_id, "name": db.get(User, m.user_id).name, "role": m.role,
                     "points": points.get(m.user_id, 0) if profile_of(db, db.get(User, m.user_id)).on_leaderboard else None}
                    for m in members],
        "trip": itinerary_out(db, trip) if trip else None,
        "suggestions": suggestions,
        "photos": [photo_out(db, p, user) for p in photos],
        "group_challenge": {"title": f"Earn {GROUP_CHALLENGE_POINTS} points together on this trip",
                            "progress": trip_points, "goal": GROUP_CHALLENGE_POINTS,
                            "completed": trip_points >= GROUP_CHALLENGE_POINTS} if trip else None,
    }


class RoleIn(BaseModel):
    role: str = Field(..., pattern="^(editor|viewer)$")


@router.patch("/groups/{group_id}/members/{user_id}")
def set_role(group_id: int, user_id: int, body: RoleIn, user: User = Depends(current_user),
             db: Session = Depends(get_db)):
    if _member(db, group_id, user).role != "owner":
        raise HTTPException(403, "Only the trip owner can change roles")
    m = db.query(GroupMember).filter_by(group_id=group_id, user_id=user_id).first()
    if not m or m.role == "owner":
        raise HTTPException(404, "Member not found")
    m.role = body.role
    db.commit()
    return group_detail(group_id, user, db)


@router.delete("/groups/{group_id}/members/{user_id}")
def remove_member(group_id: int, user_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    me = _member(db, group_id, user)
    if user_id != user.id and me.role != "owner":
        raise HTTPException(403, "Only the owner can remove other members")
    m = db.query(GroupMember).filter_by(group_id=group_id, user_id=user_id).first()
    if not m or m.role == "owner":
        raise HTTPException(400, "The owner cannot leave their own group")
    db.delete(m)
    db.commit()
    return {"removed": True}


class SuggestionIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    place_id: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    category: str = ""


@router.post("/groups/{group_id}/suggestions")
async def suggest(group_id: int, body: SuggestionIn, user: User = Depends(current_user),
                  db: Session = Depends(get_db)):
    _member(db, group_id, user)
    group = db.get(Group, group_id)
    lat, lng, category, name, place_id = body.lat, body.lng, body.category, body.name, body.place_id
    if lat is None or lng is None:
        trip = db.get(Trip, group.trip_id) if group.trip_id else None
        found = await search_places(f"{body.name}, {trip.destination}" if trip else body.name, limit=1)
        if not found:
            raise HTTPException(404, f"Could not find {body.name}")
        p = found[0]
        name, place_id, lat, lng, category = p["name"], p["place_id"], p["lat"], p["lng"], p["category"]
    db.add(GroupSuggestion(group_id=group_id, user_id=user.id, name=name, place_id=place_id, lat=lat, lng=lng,
                           category=category or "culture"))
    db.commit()
    return group_detail(group_id, user, db)


class VoteIn(BaseModel):
    value: int = Field(..., ge=-1, le=1)


@router.post("/groups/{group_id}/suggestions/{suggestion_id}/vote")
def vote(group_id: int, suggestion_id: int, body: VoteIn, user: User = Depends(current_user),
         db: Session = Depends(get_db)):
    _member(db, group_id, user)
    s = db.query(GroupSuggestion).filter_by(id=suggestion_id, group_id=group_id).first()
    if not s:
        raise HTTPException(404, "Suggestion not found")
    row = db.query(GroupVote).filter_by(suggestion_id=s.id, user_id=user.id).first()
    if body.value == 0:
        if row:
            db.delete(row)
    elif row:
        row.value = body.value
    else:
        db.add(GroupVote(suggestion_id=s.id, user_id=user.id, value=body.value))
    db.commit()
    return group_detail(group_id, user, db)


@router.post("/groups/{group_id}/suggestions/{suggestion_id}/accept")
def accept(group_id: int, suggestion_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if _member(db, group_id, user).role not in ("owner", "editor"):
        raise HTTPException(403, "Only the owner or editors can change the itinerary")
    group = db.get(Group, group_id)
    s = db.query(GroupSuggestion).filter_by(id=suggestion_id, group_id=group_id).first()
    if not s or s.status != "open":
        raise HTTPException(404, "Open suggestion not found")
    if not group.trip_id:
        raise HTTPException(400, "Link a trip to this group first")
    trip = db.get(Trip, group.trip_id)
    items = load_items(db, trip)
    if any(i["name"].lower() == s.name.lower() and i["status"] != "skipped" for i in items):
        s.status = "added"  # already planned, so the vote is settled
        db.commit()
        return group_detail(group_id, user, db)
    place = {"name": s.name, "place_id": s.place_id, "lat": s.lat, "lng": s.lng, "category": s.category}
    op = fit_place(trip, items, place)
    if not op:
        raise HTTPException(409, f"{s.name} does not fit in the remaining days")
    save_items(db, trip, apply_ops(items, [op], loads(trip.preferences, {}).get("mode", "driving")))
    s.status = "added"
    db.commit()
    return group_detail(group_id, user, db)


@router.post("/groups/{group_id}/link-trip")
def link_trip(group_id: int, body: Dict[str, int], user: User = Depends(current_user), db: Session = Depends(get_db)):
    if _member(db, group_id, user).role != "owner":
        raise HTTPException(403, "Only the group owner can link a trip")
    trip = db.get(Trip, body.get("trip_id"))
    if not trip or trip.owner_id != user.id:
        raise HTTPException(403, "You can only link trips you own")
    db.get(Group, group_id).trip_id = trip.id
    db.commit()
    return group_detail(group_id, user, db)


# ---------- wishlist ----------

class WishIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    city: str = Field("", max_length=120)
    place_id: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    category: str = ""
    source: str = Field("manual", pattern="^(manual|photo|recommendation|friend|trip)$")


def _wish_out(w: WishlistItem) -> Dict:
    return {"id": w.id, "name": w.name, "city": w.city, "place_id": w.place_id, "lat": w.lat, "lng": w.lng,
            "category": w.category, "source": w.source, "created_at": utc_iso(w.created_at)}


@router.get("/wishlist")
def wishlist(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [_wish_out(w) for w in db.query(WishlistItem).filter_by(user_id=user.id).order_by(WishlistItem.id.desc())]


@router.post("/wishlist")
def add_wish(body: WishIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    existing = db.query(WishlistItem).filter_by(user_id=user.id, name=body.name, city=body.city).first()
    if existing:
        return _wish_out(existing)
    w = WishlistItem(user_id=user.id, **body.model_dump())
    db.add(w)
    db.commit()
    return _wish_out(w)


@router.post("/wishlist/from-photo/{photo_id}")
def wish_from_photo(photo_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .photos import _get_visible
    photo = _get_visible(db, photo_id, user)
    if not photo.place_name:
        raise HTTPException(400, "This photo is not tagged with a place")
    return add_wish(WishIn(name=photo.place_name, city=photo.city, place_id=photo.place_id, source="photo"), user, db)


@router.delete("/wishlist/{wish_id}")
def remove_wish(wish_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    w = db.query(WishlistItem).filter_by(id=wish_id, user_id=user.id).first()
    if not w:
        raise HTTPException(404, "Saved place not found")
    db.delete(w)
    db.commit()
    return {"deleted": True}


@router.get("/wishlist/matches")
async def wishlist_matches(trip_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Saved places that belong to this trip's destination and still fit the schedule."""
    trip = get_trip(db, trip_id, user)
    items = load_items(db, trip)
    taken = {i["name"] for i in items if i["status"] != "skipped"}
    out = []
    for w in db.query(WishlistItem).filter_by(user_id=user.id):
        if w.name in taken:
            continue
        lat, lng, category, place_id = w.lat, w.lng, w.category, w.place_id
        if lat is None:
            found = await search_places(f"{w.name}, {w.city or trip.destination}", limit=1)
            if not found:
                continue
            lat, lng, category, place_id = found[0]["lat"], found[0]["lng"], found[0]["category"], found[0]["place_id"]
        if road_km((trip.start_lat, trip.start_lng), (lat, lng)) > 80:
            continue
        place = {"name": w.name, "place_id": place_id, "lat": lat, "lng": lng, "category": category or "culture"}
        op = fit_place(trip, items, place)
        out.append({"wish": _wish_out(w), "fits": bool(op),
                    "ops": [{"op": "add", "day": op["day"], "place": place}] if op else [],
                    "message": f"Day {op['day']} at about {op['start']}" if op else "Does not fit the remaining days"})
    return {"trip_id": trip.id, "version": trip.version, "matches": out}


# ---------- history ----------

def _history(db: Session, user_id: int, viewer: Optional[User]) -> Dict:
    trips = db.query(Trip).filter_by(owner_id=user_id).order_by(Trip.start_date.desc()).all()
    out = []
    for t in trips:
        summary = _trip_summary(db, t, viewer)
        visited = db.query(ItineraryItem).filter_by(trip_id=t.id, kind="visit", status="completed").all()
        summary.update({
            "days": trip_days(t),
            "visited": [{"name": i.name, "category": i.category} for i in visited],
            "photos": db.query(Photo).filter_by(trip_id=t.id, user_id=user_id).count(),
            "points": int(db.query(func.coalesce(func.sum(PointEvent.points), 0))
                          .filter(PointEvent.trip_id == t.id, PointEvent.user_id == user_id, PointEvent.points > 0).scalar()),
        })
        out.append(summary)
    badges = [b.code for b in db.query(UserBadge).filter_by(user_id=user_id)]
    challenges = db.query(PointEvent).filter(PointEvent.user_id == user_id,
                                             PointEvent.kind.in_(["daily_challenge", "destination_challenge"])).count()
    return {"trips": out, "badges": [{"code": c, "title": rewards.BADGES[c][0]} for c in badges if c in rewards.BADGES],
            "challenges_completed": challenges, "total_points": rewards.earned(db, user_id)}


@router.get("/history")
def my_history(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _history(db, user.id, user)


@router.get("/users/{user_id}/history")
def user_history(user_id: int, db: Session = Depends(get_db)):
    owner = db.get(User, user_id)
    if not owner or not profile_of(db, owner).history_public:
        raise HTTPException(404, "This traveler's history is private")
    data = _history(db, user_id, None)
    for t in data["trips"]:
        t.pop("owned", None)
    return data
