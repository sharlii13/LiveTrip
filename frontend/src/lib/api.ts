const ENV_BASE = (import.meta as any).env?.VITE_API_BASE as string | undefined;
const DEFAULT_BASE = ""; // same origin: the Vite dev proxy forwards /api to the backend
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

