"""The travel assistant's AI brain: Claude with tools that call LiveTrip's own features.

Claude answers in conversation (it sees the chat so far, the open trip and the page the traveller is on) and uses
tools for anything live - places, ratings, distances, descriptions - so it never makes those up. Plan changes come
back as proposals the traveller confirms in the app; Claude cannot change a trip by itself.

Needs ANTHROPIC_API_KEY in app/.env. Without it (or when the API is unreachable) the rule-based assistant in
recommend.py answers instead.
"""
import asyncio
import json
import logging
import os
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

MODEL = "claude-opus-5-5"
MAX_TOOL_ROUNDS = 6

SYSTEM = """You are LiveTrip's travel buddy: a friendly, practical assistant inside a trip-planning app. Travellers \
chat with you while planning and while on the road, usually on a phone.

How to answer:
- Keep replies short: two to five sentences, or a few short lines. Plain text only (no markdown headings, tables \
or bold); simple "- " bullets are fine for a short list.
- Use the conversation so far and the <context> block (date, page, the open trip and its stops, the traveller's \
location if shared). "It", "there", "that place", "the next one" refer to what was just discussed or to the trip.
- Reply in the traveller's app language given in <context> unless they write to you in another language. Keep \
place names as they are.
- For anything live or specific to a place (what is nearby, ratings, distances, restaurants, stays) call a tool. \
Never invent ratings, distances, prices, phone numbers or opening hours; if a tool gives nothing, say so.
- For facts about a sight (history, what to see) use get_place_info, and you may add well-known background. \
General travel questions (customs, packing, best time to visit) you can answer from knowledge.
- To change the plan, call propose_plan_change or propose_replace_stop. The app then shows the change for the \
traveller to confirm; say briefly what you proposed and that they can review it. Never claim a change is done.
- If there is no open trip and they ask to change a plan, ask them to open the trip first.
- Stay on travel and the trip. If something is unclear, ask one short question."""

NEAR = {"type": "string", "enum": ["next_stop", "my_location", "trip_centre"],
        "description": "Search around the next planned stop (default), the traveller's shared location, "
                       "or the middle of the trip's stops."}
TOOLS = [
    {"name": "find_places",
     "description": "Search real places (sights, cafes, parks, shops...) around a point. Returns name, rating, "
                    "review count, distance and category for the best matches.",
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "What to look for, e.g. 'quiet cafe', 'museum', 'viewpoint'."},
         "near": NEAR,
         "radius_km": {"type": "number", "description": "Search radius in km (default 3, max 30)."}},
         "required": ["query"], "additionalProperties": False}},
    {"name": "find_restaurants",
     "description": "Restaurants around a point that match a diet. Returns name, rating and distance.",
     "input_schema": {"type": "object", "properties": {
         "diet": {"type": "string", "enum": ["any", "vegetarian", "vegan"]},
         "near": NEAR,
         "radius_km": {"type": "number", "description": "Default 3, max 20."}},
         "required": ["diet"], "additionalProperties": False}},
    {"name": "find_stays",
     "description": "Hotels and other stays near the open trip's stops. Prices and availability are not live.",
     "input_schema": {"type": "object", "properties": {
         "budget": {"type": "string", "enum": ["low", "medium", "high"]}},
         "required": [], "additionalProperties": False}},
    {"name": "get_place_info",
     "description": "Wikipedia description of a sight (what it is, history). Use it before telling the traveller "
                    "about a place.",
     "input_schema": {"type": "object", "properties": {
         "name": {"type": "string", "description": "The place name as it appears in the trip or a search result."}},
         "required": ["name"], "additionalProperties": False}},
    {"name": "propose_plan_change",
     "description": "Prepare a change to the open trip for the traveller to confirm: weather (swap outdoor stops "
                    "on rainy days), relaxed (fewer stops on a day), delay (shift a day by N minutes because they "
                    "are running late), skip_next (skip the next stop), indoor_next (replace the next stop with an "
                    "indoor one), optimize (reorder a day for the shortest route).",
     "input_schema": {"type": "object", "properties": {
         "change": {"type": "string",
                    "enum": ["weather", "relaxed", "delay", "skip_next", "indoor_next", "optimize"]},
         "day": {"type": "integer", "description": "Trip day number; default is the day of the next stop."},
         "minutes": {"type": "integer", "description": "For delay: how many minutes late (1-600)."}},
         "required": ["change"], "additionalProperties": False}},
    {"name": "propose_replace_stop",
     "description": "Prepare swapping one planned stop (by item_id from <context>) for another place, for the "
                    "traveller to confirm. Give place_name to use a place from your last find_places / "
                    "find_restaurants result; otherwise the best nearby alternative for the reason is used.",
     "input_schema": {"type": "object", "properties": {
         "item_id": {"type": "integer"},
         "place_name": {"type": "string"},
         "reason": {"type": "string", "enum": ["nearby", "indoor", "cheaper", "relaxed"]}},
         "required": ["item_id"], "additionalProperties": False}},
]
# render order is tools -> system -> messages: the tools and this prompt never change, so they cache together
SYSTEM_BLOCKS = [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}]

Handler = Callable[..., Awaitable[Dict[str, Any]]]


class Unavailable(Exception):
    """The AI could not answer (no key, network, rate limit...); the rule-based assistant takes over."""


def available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.AsyncAnthropic(timeout=60, max_retries=2)
    return _client


def build_messages(history: List[Dict[str, str]], message: str, context: str) -> List[Dict[str, Any]]:
    """Earlier turns as plain text (the conversation must start with the traveller), then the new message with
    the live context in front of it."""
    turns = [{"role": h["role"], "content": h["text"]} for h in history if h.get("text")]
    while turns and turns[0]["role"] != "user":
        turns.pop(0)
    return turns + [{"role": "user", "content": f"<context>\n{context}\n</context>\n\n{message}"}]


async def reply(message: str, history: List[Dict[str, str]], context: str,
                handlers: Dict[str, Handler]) -> Dict[str, Any]:
    """One assistant turn. Returns {reply, places?, proposal?}; raises Unavailable if Claude can't be reached."""
    import anthropic

    messages = build_messages(history, message, context)
    out: Dict[str, Any] = {"intent": "ai"}
    for _ in range(MAX_TOOL_ROUNDS):
        try:
            response = await _get_client().beta.messages.create(
                model=MODEL, max_tokens=8000, system=SYSTEM_BLOCKS, tools=TOOLS, messages=messages,
                output_config={"effort": "low"},  # chat: quick answers; tools carry the facts
                betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        except anthropic.AuthenticationError as e:
            logger.error(f"Anthropic key rejected: {e}")
            raise Unavailable("key rejected") from e
        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.APIStatusError) as e:
            logger.warning(f"Claude unavailable, using the rule-based assistant: {e}")
            raise Unavailable(str(e)) from e

        if response.stop_reason == "refusal":
            out["reply"] = "Sorry, I can't help with that one. Ask me anything about your trip."
            return out
        if response.stop_reason != "tool_use":
            text = "\n".join(b.text for b in response.content if b.type == "text").strip()
            out["reply"] = text or "Sorry, I didn't catch that. Could you say it another way?"
            return out

        messages.append({"role": "assistant", "content": response.content})  # thinking blocks included, unchanged
        calls = [b for b in response.content if b.type == "tool_use"]
        results = await asyncio.gather(*[_run(handlers, c.name, c.input, out) for c in calls])
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": c.id, "content": json.dumps(r, ensure_ascii=False),
             **({"is_error": True} if "error" in r else {})} for c, r in zip(calls, results)]})
    out["reply"] = "That took me too many steps. Could you ask in a simpler way?"
    return out


async def _run(handlers: Dict[str, Handler], name: str, args: Any, out: Dict[str, Any]) -> Dict[str, Any]:
    handler = handlers.get(name)
    if not handler or not isinstance(args, dict):
        return {"error": f"Unknown tool {name}"}
    try:
        result = await handler(**args)
    except TypeError as e:  # arguments that don't fit the schema
        return {"error": f"Bad arguments: {e}"}
    except Exception as e:  # a failing feature becomes a message Claude can explain, not a crash
        logger.warning(f"Assistant tool {name} failed: {e}")
        return {"error": getattr(e, "detail", None) or str(e)}
    # what the app shows under the reply: the latest place list and proposal
    if result.get("places"):
        out["places"] = result["places"]
    if result.get("proposal"):
        out["proposal"] = result.pop("proposal")
    return result
