"""Accounts (email and Google sign-in), profiles, destinations and reviews."""
import json
import os
import re
import secrets
from typing import Optional, Tuple
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import User, get_db
from .core import (utc_iso, SESSION_COOKIE, TOKEN_DAYS, create_token, current_user, hash_password, loads, optional_user,
                   profile_of, user_public, verify_password)
from .models import Destination, Profile, Review

router = APIRouter(prefix="/api", tags=["accounts"])
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    email: str = Field(..., max_length=200)
    password: str = Field(..., min_length=8, max_length=200)
    username: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9_]{3,30}$")


class LoginIn(BaseModel):
    email: str
    password: str


def _session_response(db: Session, user: User) -> JSONResponse:
    token = create_token(user.id)
    response = JSONResponse({"user": user_public(db, user), "token": token})
    response.set_cookie(SESSION_COOKIE, token, max_age=TOKEN_DAYS * 86400, httponly=True, samesite="lax")
    return response


@router.post("/auth/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Enter a valid email address")
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(409, "An account with this email already exists")
    if body.username and db.query(Profile).filter(func.lower(Profile.username) == body.username.lower()).first():
        raise HTTPException(409, "That username is taken")
    user = User(email=email, name=body.name.strip(), hashed_password=hash_password(body.password))
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id, username=body.username or f"traveler{user.id}"))
    db.commit()
    return _session_response(db, user)


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == body.email.strip().lower()).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "Email or password is incorrect")
    return _session_response(db, user)


@router.get("/auth/me")
def me(user: Optional[User] = Depends(optional_user), db: Session = Depends(get_db)):
    if user is None:  # signed out is a normal state, not an error (a 401 here logs red errors on every page)
        return {"user": None}
    return {"user": user_public(db, user)}


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE)
    return {"success": True}


# ---------- Google sign-in (OAuth 2.0 authorization code flow) ----------
# app/.env: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET (Google Cloud > APIs & Services > Credentials > OAuth client ID,
# type "Web application"), and the app's address as the browser sees it, PUBLIC_APP_URL (default
# http://localhost:5173). Register {PUBLIC_APP_URL}/api/auth/google/callback as an authorized redirect URI.
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"
OAUTH_STATE_COOKIE = "lt_oauth_state"


def _google_config() -> Optional[Tuple[str, str, str]]:
    cid, secret = os.getenv("GOOGLE_CLIENT_ID"), os.getenv("GOOGLE_CLIENT_SECRET")
    if not cid or not secret:
        return None
    base = os.getenv("PUBLIC_APP_URL", "http://localhost:5173").rstrip("/")
    return cid, secret, f"{base}/api/auth/google/callback"


def _safe_next(next_url: str) -> str:
    # only paths inside the app: an absolute or protocol-relative URL here would be an open redirect
    return next_url if next_url.startswith("/") and not next_url.startswith("//") and "\\" not in next_url else "/trips"


@router.get("/auth/providers")
def auth_providers():
    return {"google": _google_config() is not None}


@router.get("/auth/google")
def google_login(next: str = "/trips"):
    config = _google_config()
    if not config:
        return RedirectResponse("/login?error=google_not_configured")
    cid, _, redirect_uri = config
    state = secrets.token_urlsafe(24)
    url = GOOGLE_AUTH + "?" + urlencode({"client_id": cid, "redirect_uri": redirect_uri, "response_type": "code",
                                         "scope": "openid email profile", "state": state,
                                         "prompt": "select_account"})
    response = RedirectResponse(url)
    # the state (with where to go after) comes back from Google; the cookie proves this browser started it
    response.set_cookie(OAUTH_STATE_COOKIE, f"{state}|{_safe_next(next)}", max_age=600, httponly=True,
                        samesite="lax")
    return response


@router.get("/auth/google/callback")
async def google_callback(request: Request, code: str = "", state: str = "", error: str = "",
                          db: Session = Depends(get_db)):
    config = _google_config()
    saved_state, _, next_url = (request.cookies.get(OAUTH_STATE_COOKIE) or "").partition("|")
    if not config or error or not code or not state or not secrets.compare_digest(state, saved_state):
        return RedirectResponse("/login?error=google_failed")
    cid, secret, redirect_uri = config
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token = await client.post(GOOGLE_TOKEN, data={"code": code, "client_id": cid, "client_secret": secret,
                                                          "redirect_uri": redirect_uri,
                                                          "grant_type": "authorization_code"})
            token.raise_for_status()
            info = await client.get(GOOGLE_USERINFO,
                                    headers={"Authorization": f"Bearer {token.json()['access_token']}"})
            info.raise_for_status()
            info = info.json()
    except (httpx.HTTPError, KeyError, ValueError):
        return RedirectResponse("/login?error=google_failed")
    email = (info.get("email") or "").strip().lower()
    if not email or not info.get("email_verified"):  # an unverified address must not take over an account
        return RedirectResponse("/login?error=google_failed")
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user:
        # no password: Google is how this account signs in (a random hash nobody knows keeps email login closed)
        user = User(email=email, name=(info.get("name") or email.split("@")[0])[:80],
                    hashed_password=hash_password(secrets.token_urlsafe(32)))
        db.add(user)
        db.flush()
        db.add(Profile(user_id=user.id, username=f"traveler{user.id}", avatar=(info.get("picture") or "")[:300]))
        db.commit()
    response = RedirectResponse(_safe_next(next_url) or "/trips")
    response.set_cookie(SESSION_COOKIE, create_token(user.id), max_age=TOKEN_DAYS * 86400, httponly=True,
                        samesite="lax")
    response.delete_cookie(OAUTH_STATE_COOKIE)
    return response


class ProfileIn(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=80)
    bio: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=120)
    avatar: Optional[str] = Field(None, max_length=300)
    onLeaderboard: Optional[bool] = None
    historyPublic: Optional[bool] = None
    isBusiness: Optional[bool] = None


@router.patch("/users/me")
def update_me(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = profile_of(db, user)
    if body.name is not None:
        user.name = body.name
    for field, attr in (("bio", "bio"), ("location", "location"), ("avatar", "avatar"),
                        ("onLeaderboard", "on_leaderboard"), ("historyPublic", "history_public"),
                        ("isBusiness", "is_business")):
        value = getattr(body, field)
        if value is not None:
            setattr(p, attr, value)
    db.commit()
    return {"user": user_public(db, user)}


@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    data = user_public(db, user)
    data.pop("email")
    return data


def _review_out(db: Session, r: Review, with_user: bool = True) -> dict:
    out = {"id": str(r.id), "userId": str(r.user_id), "destinationId": r.destination_id, "rating": r.rating,
           "title": r.title, "content": r.content, "images": [], "helpful": r.helpful,
           "createdAt": utc_iso(r.created_at)}
    if with_user:
        u = db.get(User, r.user_id)
        out["user"] = {k: v for k, v in user_public(db, u).items() if k != "email"} if u else None
    return out


@router.get("/users/{user_id}/reviews")
def user_reviews(user_id: int, db: Session = Depends(get_db)):
    return [_review_out(db, r, with_user=False)
            for r in db.query(Review).filter_by(user_id=user_id).order_by(Review.created_at.desc())]


def _destination_out(db: Session, d: Destination) -> dict:
    stats = db.query(func.count(Review.id), func.avg(Review.rating)).filter_by(destination_id=d.id).one()
    return {"id": d.id, "name": d.name, "location": d.location, "country": d.country, "category": d.category,
            "description": d.description, "shortDescription": d.short_description, "images": loads(d.images, []),
            "rating": f"{(stats[1] or 0):.2f}", "reviewCount": stats[0], "priceRange": d.price_range,
            "openingHours": d.opening_hours, "website": d.website, "phone": d.phone, "address": d.address,
            "features": loads(d.features, []), "lat": d.lat, "lng": d.lng, "createdAt": utc_iso(d.created_at)}


@router.get("/destinations")
def list_destinations(search: str = "", category: str = "", rating: Optional[float] = None,
                      priceRange: str = "", limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(Destination)
    if search:
        like = f"%{search.lower()}%"
        q = q.filter(or_(func.lower(Destination.name).like(like), func.lower(Destination.location).like(like),
                         func.lower(Destination.description).like(like)))
    if category:
        q = q.filter(Destination.category.in_(category.split(",")))
    if priceRange:
        q = q.filter(Destination.price_range.in_(priceRange.split(",")))
    items = [_destination_out(db, d) for d in q.order_by(Destination.id).all()]
    if rating:
        items = [d for d in items if float(d["rating"]) >= rating]
    return items[: max(1, min(limit, 200))]


@router.get("/destinations/{destination_id}")
def get_destination(destination_id: str, db: Session = Depends(get_db)):
    d = db.get(Destination, destination_id)
    if not d:
        raise HTTPException(404, "Destination not found")
    out = _destination_out(db, d)
    out["reviews"] = [_review_out(db, r) for r in
                      db.query(Review).filter_by(destination_id=d.id).order_by(Review.created_at.desc())]
    return out


@router.get("/destinations/{destination_id}/reviews")
def destination_reviews(destination_id: str, db: Session = Depends(get_db)):
    return [_review_out(db, r) for r in
            db.query(Review).filter_by(destination_id=destination_id).order_by(Review.created_at.desc())]


class ReviewIn(BaseModel):
    destinationId: str
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field("", max_length=200)
    content: str = Field(..., min_length=1, max_length=4000)


@router.post("/reviews")
def create_review(body: ReviewIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.get(Destination, body.destinationId):
        raise HTTPException(404, "Destination not found")
    review = Review(user_id=user.id, destination_id=body.destinationId, rating=body.rating,
                    title=body.title or "", content=body.content)
    db.add(review)
    db.commit()
    return _review_out(db, review)
