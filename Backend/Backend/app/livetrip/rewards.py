"""Points, badges, challenges, streaks, leaderboards and offer redemption."""
import hashlib
import json
import secrets
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import User, get_db
from .core import current_user, loads, profile_of
from .geo import haversine_km, today
from .models import GroupMember, Offer, Photo, PointEvent, Profile, Redemption, Trip, UserBadge

POINTS = {
    "visit_complete": 50, "new_attraction": 30, "daily_challenge": 100, "photo_upload": 20,
    "destination_challenge": 150, "trip_complete": 200,
}
PHOTO_AWARDS_PER_DAY = 5
DESTINATION_CHALLENGE_VISITS = 5
CULTURE = {"museum", "history", "religious", "culture", "fort"}
NATURE = {"park", "nature"}

BADGES = {
    "explorer": ("Explorer", "Visit 10 unique attractions"),
    "foodie": ("Foodie", "Visit 5 food places"),
    "culture_seeker": ("Culture Seeker", "Visit 5 cultural or historical places"),
    "nature_lover": ("Nature Lover", "Visit 5 parks or nature spots"),
    "weekend_wanderer": ("Weekend Wanderer", "Complete a trip that includes a weekend"),
    "photo_storyteller": ("Photo Storyteller", "Share 10 public photos tagged with a place"),
    "trip_master": ("Trip Master", "Complete a multi-day itinerary"),
    "streak_3": ("On a Roll", "Be active 3 days in a row"),
}

CHALLENGES = {
    "history3": ("Visit 3 historical or cultural landmarks", 3),
    "walk2": ("Explore 2 attractions within walking distance (1.5 km)", 2),
    "food1": ("Discover a local food place", 1),
    "hidden1": ("Visit a lesser-known attraction (under 1,000 reviews)", 1),
    "photo_landmark": ("Photo challenge: share a photo tagged with a landmark", 1),
}

router = APIRouter(prefix="/api", tags=["rewards"])


# ---------- engine ----------

def award(db: Session, user_id: int, kind: str, ref_key: str, points: Optional[int] = None,
          city: str = "", trip_id: Optional[int] = None, meta: Optional[dict] = None) -> Optional[PointEvent]:
    """Record points once per (user, ref_key). Returns None when already claimed."""
    if db.query(PointEvent).filter_by(user_id=user_id, ref_key=ref_key).first():
        return None
    event = PointEvent(user_id=user_id, kind=kind, points=POINTS.get(kind, 0) if points is None else points,
                       ref_key=ref_key, city=(city or "").lower(), trip_id=trip_id, meta=json.dumps(meta or {}))
    db.add(event)
    db.flush()
    return event


def balance(db: Session, user_id: int) -> int:
    return int(db.query(func.coalesce(func.sum(PointEvent.points), 0)).filter_by(user_id=user_id).scalar())


def earned(db: Session, user_id: int) -> int:
    return int(db.query(func.coalesce(func.sum(PointEvent.points), 0))
               .filter(PointEvent.user_id == user_id, PointEvent.points > 0).scalar())


def _visits(db: Session, user_id: int, day: Optional[str] = None) -> List[dict]:
    q = db.query(PointEvent).filter_by(user_id=user_id, kind="visit_complete")
    events = q.all()
    out = [dict(loads(e.meta, {}), created=e.created_at) for e in events]
    if day:
        out = [v for v in out if v["created"].date().isoformat() == day]
    return out


def active_days(db: Session, user_id: int) -> List[str]:
    rows = db.query(PointEvent.created_at).filter(PointEvent.user_id == user_id, PointEvent.points > 0).all()
    return sorted({r[0].date().isoformat() for r in rows})


def current_streak(db: Session, user_id: int) -> int:
    days = set(active_days(db, user_id))
    d = date.today()
    if d.isoformat() not in days:
        d -= timedelta(days=1)  # streak stays alive until the end of today
    streak = 0
    while d.isoformat() in days:
        streak += 1
        d -= timedelta(days=1)
    return streak


def daily_challenge_codes(day: str) -> List[str]:
    """Three challenges per day, the same for everyone, rotating by date."""
    codes = sorted(CHALLENGES)
    start = int(hashlib.sha256(day.encode()).hexdigest(), 16) % len(codes)
    return [codes[(start + i) % len(codes)] for i in range(3)]


def challenge_progress(db: Session, user_id: int, code: str, day: str) -> int:
    visits = _visits(db, user_id, day)
    if code == "history3":
        return sum(1 for v in visits if v.get("category") in CULTURE)
    if code == "food1":
        return sum(1 for v in visits if v.get("category") == "food")
    if code == "hidden1":
        return sum(1 for v in visits if 0 < v.get("rating_count", 0) < 1000)
    if code == "walk2":
        pts = [(v["lat"], v["lng"]) for v in visits if v.get("lat") is not None]
        best = 0
        for i, a in enumerate(pts):
            near = sum(1 for b in pts if haversine_km(a, b) <= 1.5)
            best = max(best, near)
        return best
    if code == "photo_landmark":
        return db.query(Photo).filter(Photo.user_id == user_id, Photo.visibility == "public", Photo.place_name != "",
                                      func.date(Photo.created_at) == day).count()
    return 0


def evaluate(db: Session, user_id: int, city: str = "", trip_id: Optional[int] = None) -> List[dict]:
    """Run after any eligible activity: completes challenges and unlocks badges. Returns what was newly earned."""
    new: List[dict] = []
    day = today()
    for code in daily_challenge_codes(day):
        goal = CHALLENGES[code][1]
        if challenge_progress(db, user_id, code, day) >= goal:
            e = award(db, user_id, "daily_challenge", f"daily:{day}:{code}", city=city, trip_id=trip_id,
                      meta={"challenge": code})
            if e:
                new.append({"type": "challenge", "code": code, "title": CHALLENGES[code][0], "points": e.points})

    if city:
        city_visits = [v for v in _visits(db, user_id) if (v.get("city") or "").lower() == city.lower()]
        if len({v.get("place") for v in city_visits}) >= DESTINATION_CHALLENGE_VISITS:
            e = award(db, user_id, "destination_challenge", f"dest:{city.lower()}", city=city, trip_id=trip_id,
                      meta={"city": city})
            if e:
                new.append({"type": "challenge", "code": "destination", "title": f"Explore {city}", "points": e.points})

    visits = _visits(db, user_id)
    places = {v.get("place") for v in visits}
    counts = {
        "explorer": len(places) >= 10,
        "foodie": len({v.get("place") for v in visits if v.get("category") == "food"}) >= 5,
        "culture_seeker": len({v.get("place") for v in visits if v.get("category") in CULTURE}) >= 5,
        "nature_lover": len({v.get("place") for v in visits if v.get("category") in NATURE}) >= 5,
        "photo_storyteller": db.query(Photo).filter(Photo.user_id == user_id, Photo.visibility == "public",
                                                    Photo.place_name != "").count() >= 10,
        "streak_3": current_streak(db, user_id) >= 3,
    }
    for code, done in counts.items():
        if done:
            new += grant_badge(db, user_id, code)
    return new


def grant_badge(db: Session, user_id: int, code: str) -> List[dict]:
    if db.query(UserBadge).filter_by(user_id=user_id, code=code).first():
        return []
    db.add(UserBadge(user_id=user_id, code=code))
    db.flush()
    return [{"type": "badge", "code": code, "title": BADGES[code][0]}]


# ---------- API ----------

@router.get("/points/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    day = today()
    owned = {b.code: b.awarded_at for b in db.query(UserBadge).filter_by(user_id=user.id)}
    completed = db.query(PointEvent).filter(PointEvent.user_id == user.id,
                                            PointEvent.kind.in_(["daily_challenge", "destination_challenge"])).all()
    redemptions = (db.query(Redemption, Offer).join(Offer, Offer.id == Redemption.offer_id)
                   .filter(Redemption.user_id == user.id).order_by(Redemption.created_at.desc()).all())
    recent = (db.query(PointEvent).filter_by(user_id=user.id).order_by(PointEvent.created_at.desc()).limit(20).all())
    return {
        "total_earned": earned(db, user.id),
        "balance": balance(db, user.id),
        "streak": current_streak(db, user.id),
        "badges": [{"code": c, "title": t, "description": d, "earned": c in owned,
                    "awarded_at": owned[c].isoformat() if c in owned else None} for c, (t, d) in BADGES.items()],
        "challenges_today": challenges_for(db, user.id, day),
        "completed_challenges": [{"title": loads(e.meta, {}).get("challenge") or loads(e.meta, {}).get("city"),
                                  "points": e.points, "date": e.created_at.date().isoformat()} for e in completed],
        "upcoming_challenges": [{"date": d, "codes": [CHALLENGES[c][0] for c in daily_challenge_codes(d)]}
                                for d in [(date.today() + timedelta(days=i)).isoformat() for i in (1, 2)]],
        "redemptions": [{"code": r.code, "offer": o.title, "business": o.business_name, "cost": o.cost_points,
                         "date": r.created_at.isoformat()} for r, o in redemptions],
        "recent_activity": [{"kind": e.kind, "points": e.points, "date": e.created_at.isoformat(),
                             "meta": loads(e.meta, {})} for e in recent],
        "point_rules": POINTS,
    }


def challenges_for(db: Session, user_id: int, day: str) -> List[dict]:
    out = []
    for code in daily_challenge_codes(day):
        title, goal = CHALLENGES[code]
        done = db.query(PointEvent).filter_by(user_id=user_id, ref_key=f"daily:{day}:{code}").first() is not None
        out.append({"code": code, "title": title, "goal": goal, "points": POINTS["daily_challenge"],
                    "progress": min(goal, challenge_progress(db, user_id, code, day)), "completed": done})
    return out


@router.get("/challenges")
def challenges(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"date": today(), "challenges": challenges_for(db, user.id, today())}


@router.get("/badges/catalog")
def badge_catalog():
    return [{"code": c, "title": t, "description": d} for c, (t, d) in BADGES.items()]


@router.get("/points/leaderboard")
def leaderboard(scope: str = "global", city: str = "", group_id: Optional[int] = None, limit: int = 20,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = (db.query(PointEvent.user_id, func.sum(PointEvent.points).label("pts"))
         .join(Profile, Profile.user_id == PointEvent.user_id)
         .filter(PointEvent.points > 0, Profile.on_leaderboard.is_(True)))
    if scope == "city":
        if not city:
            raise HTTPException(400, "city is required for a city leaderboard")
        q = q.filter(PointEvent.city == city.lower())
    elif scope == "group":
        if not group_id or not db.query(GroupMember).filter_by(group_id=group_id, user_id=user.id).first():
            raise HTTPException(403, "You are not a member of this group")
        members = [m.user_id for m in db.query(GroupMember).filter_by(group_id=group_id)]
        q = q.filter(PointEvent.user_id.in_(members))
    rows = q.group_by(PointEvent.user_id).order_by(func.sum(PointEvent.points).desc()).limit(limit).all()
    out = []
    for rank, (uid, pts) in enumerate(rows, 1):
        u = db.get(User, uid)
        out.append({"rank": rank, "user_id": uid, "name": u.name, "username": profile_of(db, u).username,
                    "points": int(pts), "is_me": uid == user.id})
    return {"scope": scope, "entries": out, "me_on_leaderboard": profile_of(db, user).on_leaderboard}


class OfferIn(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=120)
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field("", max_length=1000)
    city: str = Field("", max_length=120)
    cost_points: int = Field(..., ge=10, le=100000)
    per_user_limit: int = Field(1, ge=1, le=100)
    total_limit: int = Field(100, ge=1, le=100000)
    expires_on: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


def _offer_out(db: Session, o: Offer) -> dict:
    used = db.query(Redemption).filter_by(offer_id=o.id).count()
    return {"id": o.id, "business_name": o.business_name, "title": o.title, "description": o.description,
            "city": o.city, "cost_points": o.cost_points, "per_user_limit": o.per_user_limit,
            "remaining": max(0, o.total_limit - used), "expires_on": o.expires_on,
            "active": o.active and o.expires_on >= today()}


@router.get("/offers")
def list_offers(city: str = "", db: Session = Depends(get_db)):
    q = db.query(Offer).filter(Offer.active.is_(True), Offer.expires_on >= today())
    if city:
        q = q.filter((Offer.city == "") | (func.lower(Offer.city) == city.lower()))
    return [_offer_out(db, o) for o in q.order_by(Offer.cost_points)]


@router.post("/offers")
def create_offer(body: OfferIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not profile_of(db, user).is_business:
        raise HTTPException(403, "Only business accounts can publish offers")
    offer = Offer(owner_id=user.id, **body.model_dump())
    db.add(offer)
    db.commit()
    return _offer_out(db, offer)


@router.post("/offers/{offer_id}/redeem")
def redeem(offer_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    offer = db.get(Offer, offer_id)
    if not offer or not offer.active or offer.expires_on < today():
        raise HTTPException(404, "This offer is not available")
    if db.query(Redemption).filter_by(offer_id=offer.id).count() >= offer.total_limit:
        raise HTTPException(409, "This offer has been fully redeemed")
    if db.query(Redemption).filter_by(offer_id=offer.id, user_id=user.id).count() >= offer.per_user_limit:
        raise HTTPException(409, "You have already redeemed this offer")
    if balance(db, user.id) < offer.cost_points:
        raise HTTPException(400, f"You need {offer.cost_points} points; your balance is {balance(db, user.id)}")
    code = secrets.token_hex(4).upper()
    db.add(Redemption(user_id=user.id, offer_id=offer.id, code=code))
    award(db, user.id, "redemption", f"redeem:{code}", points=-offer.cost_points, meta={"offer": offer.title})
    db.commit()
    return {"code": code, "offer": _offer_out(db, offer), "balance": balance(db, user.id)}


def trip_completion(db: Session, user_id: int, trip: Trip, completed_days: int, total_days: int) -> List[dict]:
    """Trip Master / Weekend Wanderer / trip_complete points once every day has a completed visit."""
    new: List[dict] = []
    if total_days < 1 or completed_days < total_days:
        return new
    trip.status = "completed"
    e = award(db, user_id, "trip_complete", f"trip:{trip.id}", city=trip.destination, trip_id=trip.id)
    if e:
        new.append({"type": "trip", "title": f"Completed {trip.destination} trip", "points": e.points})
    if total_days >= 2:
        new += grant_badge(db, user_id, "trip_master")
    try:
        start = datetime.strptime(trip.start_date, "%Y-%m-%d").date()
        weekdays = {(start + timedelta(days=i)).weekday() for i in range(total_days)}
        if {5, 6} <= weekdays:
            new += grant_badge(db, user_id, "weekend_wanderer")
    except (TypeError, ValueError):
        pass
    return new


def leaderboard_points_for_group(db: Session, group_id: int) -> Dict[int, int]:
    members = [m.user_id for m in db.query(GroupMember).filter_by(group_id=group_id)]
    rows = (db.query(PointEvent.user_id, func.sum(PointEvent.points)).filter(PointEvent.user_id.in_(members),
            PointEvent.points > 0).group_by(PointEvent.user_id).all())
    return {uid: int(p) for uid, p in rows}
