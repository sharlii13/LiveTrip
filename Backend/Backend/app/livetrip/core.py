"""Shared helpers: password hashing, session tokens, current-user dependencies, JSON fields."""
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database import User, get_db
from .models import Profile

APP_DIR = Path(__file__).resolve().parent.parent
SESSION_COOKIE = "lt_session"
TOKEN_DAYS = 14
_PBKDF2_ROUNDS = 200_000


def _secret_key() -> str:
    """LIVETRIP_SECRET_KEY, or a random key kept in a git-ignored file so sessions survive restarts."""
    key = os.getenv("LIVETRIP_SECRET_KEY")
    if key:
        return key
    path = APP_DIR / ".livetrip_secret"
    if not path.exists():
        path.write_text(secrets.token_urlsafe(48))
    return path.read_text().strip()


SECRET_KEY = _secret_key()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ROUNDS).hex()
    return f"pbkdf2${salt}${digest}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    if not stored or not stored.startswith("pbkdf2$"):
        return False
    _, salt, digest = stored.split("$")
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ROUNDS).hex()
    return hmac.compare_digest(check, digest)


def create_token(user_id: int) -> str:
    expires = datetime.utcnow() + timedelta(days=TOKEN_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": expires}, SECRET_KEY, algorithm="HS256")


def _token_from_request(request: Request) -> Optional[str]:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:]
    return request.cookies.get(SESSION_COOKIE)


def optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = _token_from_request(request)
    if not token:
        return None
    try:
        user_id = int(jwt.decode(token, SECRET_KEY, algorithms=["HS256"])["sub"])
    except (JWTError, KeyError, ValueError):
        return None
    return db.get(User, user_id)


def current_user(user: Optional[User] = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in first")
    return user


def profile_of(db: Session, user: User) -> Profile:
    profile = db.get(Profile, user.id)
    if profile is None:
        profile = Profile(user_id=user.id, username=f"traveler{user.id}")
        db.add(profile)
        db.commit()
    return profile


def user_public(db: Session, user: User) -> dict:
    """User in the shape the frontend's shared schema expects."""
    p = profile_of(db, user)
    return {
        "id": str(user.id),
        "username": p.username,
        "email": user.email,
        "name": user.name,
        "bio": p.bio,
        "location": p.location,
        "avatar": p.avatar,
        "provider": "local",
        "createdAt": (user.created_at or datetime.utcnow()).isoformat(),
        "settings": {"onLeaderboard": p.on_leaderboard, "historyPublic": p.history_public, "isBusiness": p.is_business},
    }


def loads(value: Optional[str], default: Any) -> Any:
    try:
        return json.loads(value) if value else default
    except (TypeError, ValueError):
        return default
