"""Multi-day itinerary endpoint backed by the merged root planner (app.rootplan).

The root planner returns {status, message, data: {days}}; the frontend's
MultiDayPlanner expects {itinerary, summary}. This module converts between them
and turns planner errors into non-2xx responses so the UI shows the message.
"""
from collections import Counter

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.rootplan.api.itinerary_routes import plan_multi_day as _plan_multi_day

router = APIRouter(prefix="/api/itinerary", tags=["itinerary"])


def _to_frontend_day(day: dict, index: int) -> dict:
    items = day.get("items", [])
    schedule = [
        {
            "poi": it.get("name", ""),
            "category": it.get("category", ""),
            "start": it.get("arrive_at", ""),
            "end": it.get("depart_at", ""),
            "duration_hr": round(it.get("duration_min", 0) / 60, 2),
            "coordinates": it.get("coordinates") or {"lat": 0.0, "lng": 0.0},
        }
        for it in items
    ]
    stats = day.get("stats", {})
    return {
        "day": day.get("day", index + 1),
        "total_distance_km": day.get("total_distance_km", 0),
        "total_duration_hr": stats.get("total_duration", day.get("total_duration_hr", 0)),
        "utilization_percent": day.get("utilization_percent", 0),
        "category_mix": day.get("category_mix") or dict(Counter(s["category"] for s in schedule)),
        "diversity_score": day.get("diversity_score", 0),
        "schedule": schedule,
    }


@router.post("/plan-multi-day", summary="Plan Multi-Day Itinerary")
async def plan_multi_day(request: Request):
    payload = await request.json()
    result = await _plan_multi_day(payload)
    if result.get("status") != "success":
        return JSONResponse(status_code=400, content={"message": result.get("message", "Planning failed")})

    days = [_to_frontend_day(d, i) for i, d in enumerate(result["data"]["days"])]
    all_categories = Counter()
    for d in days:
        all_categories.update(d["category_mix"])
    n = len(days) or 1
    return {
        "itinerary": days,
        "summary": {
            "total_days": len(days),
            "total_pois_covered": sum(len(d["schedule"]) for d in days),
            "avg_daily_diversity": f"{sum(d['diversity_score'] for d in days) / n:.2f}",
            "avg_daily_utilization": f"{sum(d['utilization_percent'] for d in days) / n:.1f}%",
            "categories_distribution": dict(all_categories),
            "unassigned_pois": [],
        },
        "metadata": {"last_updated": result["data"].get("last_updated")},
    }
