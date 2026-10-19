const ENV_BASE = (import.meta as any).env?.VITE_API_BASE as string | undefined;
const DEFAULT_BASE = "http://127.0.0.1:8000";
let COMPUTED_BASE = ENV_BASE || DEFAULT_BASE;
// Dev safeguard: if an unexpected 8001 base is present locally, fall back to 8000 where backend runs
if (typeof window !== 'undefined') {
  try {
    const host = window.location.hostname;
    if ((host === 'localhost' || host === '127.0.0.1') && /:8001\b/.test(COMPUTED_BASE)) {
      COMPUTED_BASE = DEFAULT_BASE;
    }
  } catch {}
}
export const API_BASE = COMPUTED_BASE;
export function getApiBase() { return API_BASE; }

export async function getSuggestions(): Promise<any> {
  const res = await fetch(`${API_BASE}/suggestions`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`Failed to fetch suggestions: ${res.status}`);
  return res.json();
}

export async function apiGet(path: string): Promise<any> {
  const url = `${API_BASE}/${path.replace(/^\/+/, "")}`;
  const res = await fetch(url, { headers: { "Content-Type": "application/json" } });
  if (!res.ok) throw new Error(`GET ${url} failed: ${res.status}`);
  return res.json();
}

export async function apiPost(path: string, body: unknown): Promise<any> {
  const url = `${API_BASE}/${path.replace(/^\/+/, "")}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) throw new Error(`POST ${url} failed: ${res.status}`);
  return res.json();
}

// Minimal integration helper: fetch top places for a city and create a backend itinerary
export async function createCompleteItineraryFromCity(city: string, userId = 1, opts?: { startDate?: Date | string; endDate?: Date | string; startTime?: string; timezone?: string; }) {
  if (!city) throw new Error("City is required");

  const headers = { "Content-Type": "application/json" } as const;

  // Try a focused attractions search first
  let items: any[] = [];
  for (const q of [
    `${city} tourist attractions`,
    `${city} points of interest`,
    city,
  ]) {
    // Debug: log each query
    console.log('[createCompleteItineraryFromCity] Querying places:', q, 'API_BASE:', API_BASE);
    const res = await fetch(`${API_BASE}/api/places/search?query=${encodeURIComponent(q)}&limit=8`, { headers });
    if (res.ok) {
      const json = await res.json();
      if (json?.items?.length) {
        console.log('[createCompleteItineraryFromCity] Found places:', json.items.length, 'for query');
        items = json.items;
        break;
      } else {
        console.log('[createCompleteItineraryFromCity] No items for query');
      }
    }
  }

  // Live-only mode: if no items returned, raise an error (no fallback)
  if (!items.length) {
    throw new Error(`No places found via live API for ${city}.`);
  }

  // Map places to the itinerary destination format
  const destinations = items.map((p: any) => ({
    name: p.name,
    latitude: p.location?.lat ?? p.geometry?.location?.lat,
    longitude: p.location?.lng ?? p.geometry?.location?.lng,
    rating: p.rating ?? 4.0,
    stay_duration: 2.0,
    category: (p.types && p.types[0]) || "point_of_interest",
    address: p.address || p.formatted_address || "",
    traffic_score: 5.0,
    weather_match: 8.0,
  })).filter((d: any) => typeof d.latitude === "number" && typeof d.longitude === "number");

  if (destinations.length === 0) {
    throw new Error(`No geocoded places found for ${city}`);
  }

  const toDateStr = (d: any) => {
    try {
      if (!d) return undefined;
      const dd = (d instanceof Date) ? d : new Date(d);
      return dd.toISOString().slice(0,10);
    } catch { return undefined; }
  };

  const payload: any = {
    title: `${city} Trip`,
    user_id: userId,
    destinations,
    start_latitude: destinations[0].latitude,
    start_longitude: destinations[0].longitude,
    start_time: opts?.startTime || "09:00:00",
    timezone: opts?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Kolkata",
  };
  const sd = toDateStr(opts?.startDate);
  const ed = toDateStr(opts?.endDate);
  if (sd) payload.start_date = sd;
  if (ed) payload.end_date = ed;

  console.log('[createCompleteItineraryFromCity] Creating itinerary with', destinations.length, 'destinations');
  const createRes = await fetch(`${API_BASE}/api/itinerary/create-complete-itinerary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!createRes.ok) {
    const text = await createRes.text();
    throw new Error(`Failed to create itinerary: ${createRes.status} ${text}`);
  }

  const json = await createRes.json();
  // New universal backend shape: { status, message, responseCity, data }
  if (json && typeof json === 'object' && 'status' in json) {
    if (json.status === 'success') {
      return json.data;
    }
    const msg = json.message || 'Backend returned error';
    throw new Error(msg);
  }
  // Backward compatibility
  return json;
}
