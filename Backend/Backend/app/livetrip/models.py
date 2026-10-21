"""LiveTrip tables. New tables only (prefixed lt_) so existing SQLite files keep working without migrations."""
from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
                        UniqueConstraint)

from database import Base


class Profile(Base):
    """Extra account data for a row in the existing `users` table."""
    __tablename__ = "lt_profiles"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    username = Column(String(40), unique=True, index=True)
    bio = Column(Text, default="")
    location = Column(String(120), default="")
    avatar = Column(String(300), default="")
    on_leaderboard = Column(Boolean, default=True)
    history_public = Column(Boolean, default=False)
    is_business = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class LTTrip(Base):
    __tablename__ = "lt_trips"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), index=True)
    destination = Column(String(120), index=True)
    start_date = Column(String(10))  # YYYY-MM-DD
    end_date = Column(String(10))
    start_lat = Column(Float)  # trip starting point (hotel or city centre); used for distance rewards
    start_lng = Column(Float)
    preferences = Column(Text, default="{}")  # JSON: interests, food, budget, pace, travelers, pets, mode
    status = Column(String(20), default="planned")  # planned | active | completed
    version = Column(Integer, default=1)
    distance_source = Column(String(20), default="estimate")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ItineraryItem(Base):
    __tablename__ = "lt_items"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("lt_trips.id"), index=True)
    day = Column(Integer)  # 1-based
    position = Column(Integer)
    kind = Column(String(20), default="visit")  # visit | meal
    name = Column(String(200))
    category = Column(String(40))
    place_id = Column(String(200), default="")
    address = Column(String(300), default="")
    lat = Column(Float)
    lng = Column(Float)
    rating = Column(Float, default=0)
    rating_count = Column(Integer, default=0)
    outdoor = Column(Boolean, default=True)
    start = Column(String(5))  # HH:MM
    end = Column(String(5))
    duration_min = Column(Integer, default=60)
    travel_min = Column(Integer, default=0)  # travel time from previous stop
    status = Column(String(20), default="planned")  # planned | completed | skipped
    locked = Column(Boolean, default=False)  # confirmed by the user; rescheduling keeps it
    completed_at = Column(DateTime, nullable=True)


class Alert(Base):
    __tablename__ = "lt_alerts"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("lt_trips.id"), index=True)
    alert_type = Column(String(30))  # weather | traffic | closure
    severity = Column(String(10))
    message = Column(Text)
    suggested_actions = Column(Text, default="[]")
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("trip_id", "alert_type", "message"),)


class Photo(Base):
    __tablename__ = "lt_photos"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    trip_id = Column(Integer, ForeignKey("lt_trips.id"), nullable=True, index=True)
    item_id = Column(Integer, ForeignKey("lt_items.id"), nullable=True)
    file_name = Column(String(200))
    caption = Column(Text, default="")
    hashtags = Column(String(300), default="")  # space separated, lowercase, no '#'
    place_name = Column(String(200), default="")
    place_id = Column(String(200), default="")
    city = Column(String(120), default="", index=True)
    lat = Column(Float, nullable=True)  # stored only when the user chose to share location
    lng = Column(Float, nullable=True)
    visibility = Column(String(10), default="public")  # public | private | group
    challenge_code = Column(String(40), default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class PhotoReaction(Base):
    __tablename__ = "lt_photo_reactions"
    id = Column(Integer, primary_key=True)
    photo_id = Column(Integer, ForeignKey("lt_photos.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    __table_args__ = (UniqueConstraint("photo_id", "user_id"),)


class PhotoSave(Base):
    __tablename__ = "lt_photo_saves"
    id = Column(Integer, primary_key=True)
    photo_id = Column(Integer, ForeignKey("lt_photos.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    __table_args__ = (UniqueConstraint("photo_id", "user_id"),)


class PhotoComment(Base):
    __tablename__ = "lt_photo_comments"
    id = Column(Integer, primary_key=True)
    photo_id = Column(Integer, ForeignKey("lt_photos.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class PointEvent(Base):
    """Points ledger. ref_key makes every award idempotent per user (no duplicate claims)."""
    __tablename__ = "lt_point_events"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    kind = Column(String(40))
    points = Column(Integer)
    ref_key = Column(String(200))
    city = Column(String(120), default="")
    trip_id = Column(Integer, nullable=True)
    meta = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    __table_args__ = (UniqueConstraint("user_id", "ref_key"),)


class LTBadge(Base):
    __tablename__ = "lt_user_badges"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    code = Column(String(40))
    awarded_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "code"),)


class Offer(Base):
    __tablename__ = "lt_offers"
    id = Column(Integer, primary_key=True)
    business_name = Column(String(120))
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(200))
    description = Column(Text, default="")
    city = Column(String(120), default="")
    cost_points = Column(Integer)
    per_user_limit = Column(Integer, default=1)
    total_limit = Column(Integer, default=100)
    expires_on = Column(String(10))  # YYYY-MM-DD
    active = Column(Boolean, default=True)


class Redemption(Base):
    __tablename__ = "lt_redemptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    offer_id = Column(Integer, ForeignKey("lt_offers.id"), index=True)
    code = Column(String(20), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Group(Base):
    __tablename__ = "lt_groups"
    id = Column(Integer, primary_key=True)
    name = Column(String(120))
    owner_id = Column(Integer, ForeignKey("users.id"))
    trip_id = Column(Integer, ForeignKey("lt_trips.id"), nullable=True)
    invite_code = Column(String(12), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GroupMember(Base):
    __tablename__ = "lt_group_members"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("lt_groups.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    role = Column(String(10), default="viewer")  # owner | editor | viewer
    __table_args__ = (UniqueConstraint("group_id", "user_id"),)


class GroupSuggestion(Base):
    __tablename__ = "lt_group_suggestions"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("lt_groups.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(200))
    category = Column(String(40), default="")
    place_id = Column(String(200), default="")
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    status = Column(String(10), default="open")  # open | added | rejected
    created_at = Column(DateTime, default=datetime.utcnow)


class GroupVote(Base):
    __tablename__ = "lt_group_votes"
    id = Column(Integer, primary_key=True)
    suggestion_id = Column(Integer, ForeignKey("lt_group_suggestions.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    value = Column(Integer)  # +1 or -1
    __table_args__ = (UniqueConstraint("suggestion_id", "user_id"),)


class WishlistItem(Base):
    __tablename__ = "lt_wishlist"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    name = Column(String(200))
    category = Column(String(40), default="")
    place_id = Column(String(200), default="")
    city = Column(String(120), default="")
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    source = Column(String(20), default="manual")  # manual | photo | recommendation | friend | trip
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "name", "city"),)


class ItemFeedback(Base):
    """Explicit feedback used to personalise later recommendations."""
    __tablename__ = "lt_item_feedback"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    item_id = Column(Integer, ForeignKey("lt_items.id"))
    category = Column(String(40))
    rating = Column(Integer)  # 1-5
    __table_args__ = (UniqueConstraint("user_id", "item_id"),)


class Destination(Base):
    __tablename__ = "lt_destinations"
    id = Column(String(40), primary_key=True)
    name = Column(String(120))
    location = Column(String(120))
    country = Column(String(80))
    category = Column(String(40))  # attraction | experience | hotel | restaurant
    description = Column(Text)
    short_description = Column(Text, default="")
    images = Column(Text, default="[]")
    price_range = Column(String(5), default="$$")
    opening_hours = Column(String(120), default="")
    website = Column(String(200), default="")
    phone = Column(String(40), default="")
    address = Column(String(300), default="")
    features = Column(Text, default="[]")
    lat = Column(Float)
    lng = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class Review(Base):
    __tablename__ = "lt_reviews"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    destination_id = Column(String(40), ForeignKey("lt_destinations.id"), index=True)
    rating = Column(Integer)
    title = Column(String(200), default="")
    content = Column(Text)
    helpful = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# Short names used across the package (class names differ from the older tables in database.py)
Trip = LTTrip
UserBadge = LTBadge
