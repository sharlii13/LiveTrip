// Client for the LiveTrip feature API (same origin; the dev server proxies /api to FastAPI).

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T = any>(path: string, options: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, headers, ...rest } = options;
  let res: Response;
  try {
    res = await fetch(path, {
      credentials: "include",
      ...rest,
      headers: json !== undefined ? { "Content-Type": "application/json", ...headers } : headers,
      body: json !== undefined ? JSON.stringify(json) : rest.body,
    });
  } catch {
    throw new ApiError(0, BACKEND_DOWN);
  }
  const text = await res.text();
  const data = text ? safeJson(text) : null;
  if (!res.ok) {
    const structured = data && typeof data === "object" && !("raw" in data);
    if (!structured && res.status >= 500) {
      // a bare 500/502/504 with no JSON body comes from the dev-server proxy when the backend is unreachable
      throw new ApiError(res.status, BACKEND_DOWN);
    }
    const detail = data?.detail ?? data?.message ?? data?.error ?? res.statusText;
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data as T;
}

const BACKEND_DOWN =
  "The LiveTrip server isn't responding. Check that the backend window is still running " +
  "(python -m uvicorn main:app --port 8000), wait a few seconds, and try again.";

function safeJson(text: string) {
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text, raw: true };
  }
}

// Trips planned before signing in are remembered on this device and attached to the account at sign-in.
const RECENT_KEY = "livetrip-recent-trips";

export function rememberTrip(id: string | number) {
  try {
    const ids = recentTrips().filter((x) => x !== String(id));
    localStorage.setItem(RECENT_KEY, JSON.stringify([String(id), ...ids].slice(0, 20)));
  } catch {
    /* storage unavailable: the trip is still reachable by its link */
  }
}

export function recentTrips(): string[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
  } catch {
    return [];
  }
}

export function forgetRecentTrips() {
  try {
    localStorage.removeItem(RECENT_KEY);
  } catch {
    /* ignore */
  }
}

/** YYYY-MM-DD in the traveler's own time zone (toISOString would give the UTC date). */
export function localDate(d: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function currentPosition(timeoutMs = 10000): Promise<{ lat: number; lng: number } | null> {
  return new Promise((resolve) => {
    if (!("geolocation" in navigator)) return resolve(null);
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
      () => resolve(null),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 60000 },
    );
  });
}

// ---------- shared types ----------

export interface Place {
  name: string;
  place_id: string;
  address?: string;
  lat: number;
  lng: number;
  rating: number;
  rating_count: number;
  category: string;
  outdoor?: boolean;
  distance_km?: number;
  travel_min?: number;
  visit_min?: number;
}

export interface Slot {
  item_id: number;
  start_time: string;
  end_time: string;
  status: "planned" | "completed" | "skipped";
  kind: "visit" | "meal";
  locked: boolean;
  travel_min: number;
  overflow: boolean;
  activity: {
    id: string;
    name: string;
    description: string;
    location: { latitude: number; longitude: number; address: string; city: string };
    activity_type: string;
    estimated_duration: number;
    rating: number;
    rating_count: number;
    place_id: string;
    weather_dependent: boolean;
  };
}

export interface Trip {
  id: string;
  user_id: string | null;
  destination: string;
  start_date: string;
  end_date: string;
  status: string;
  version: number;
  distance_source: string;
  distance_note: string;
  places_note?: string;
  start_location: { lat: number; lng: number };
  user_preferences: Record<string, any>;
  days: { day: number; date: string; time_slots: Slot[]; total_travel_time: number }[];
}

export interface Op {
  op: "skip" | "replace" | "delay" | "add" | "reorder";
  item_id?: number;
  day?: number;
  minutes?: number;
  place?: Place;
  order?: number[];
}

export interface Proposal {
  ops: Op[];
  notes: string[];
  version: number;
  preview?: Trip;
}

export interface Award {
  type: string;
  points?: number;
  title: string;
  code?: string;
}

export interface Photo {
  id: number;
  url: string;
  caption: string;
  hashtags: string[];
  place_name: string;
  city: string;
  lat: number | null;
  lng: number | null;
  location_precise: boolean;
  visibility: string;
  trip_id: number | null;
  activity: string | null;
  created_at: string;
  user: { id: number; name: string; username: string };
  likes: number;
  comments: number;
  liked_by_me: boolean;
  saved_by_me: boolean;
  mine: boolean;
  comment_list?: { id: number; text: string; created_at: string; user: { id: number; name: string } }[];
}

export function describeAwards(awards: Award[]): string {
  return awards
    .map((a) => (a.points ? `+${a.points} ${a.title}` : a.type === "badge" ? `Badge: ${a.title}` : a.title))
    .join(" · ");
}
