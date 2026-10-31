/* LiveTrip service worker: fast repeat loads and a friendly offline page.
 * Pages and API data always come from the network, so trips, sign-ins and live data are never stale and no
 * personal data is stored here. Only the app's static files are cached.
 * shortcut: no offline viewing of trips; to add it, cache GET /api/itinerary/* (and clear it on sign-out). */
const STATIC_CACHE = "livetrip-static-v1";
const OFFLINE_URL = "/offline.html";
const PRECACHE = [OFFLINE_URL, "/favicon.svg", "/icons/icon-192.png"];
const MAX_STATIC_ENTRIES = 80;  // old build files drop out as new ones arrive

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.filter((n) => n !== STATIC_CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim()),
  );
});

function isCacheableStatic(url) {
  // /assets/ holds Vite's content-hashed build files; videos are left out (range requests, large files)
  return url.pathname.startsWith("/assets/") || url.pathname.startsWith("/icons/") || url.pathname === "/favicon.svg"
    || /^\/videos\/clips\/.*\.jpg$/.test(url.pathname);
}

async function trim(cache) {
  const keys = await cache.keys();
  await Promise.all(keys.slice(0, Math.max(0, keys.length - MAX_STATIC_ENTRIES))
    .filter((k) => !PRECACHE.includes(new URL(k.url).pathname))
    .map((k) => cache.delete(k)));
}

async function cacheFirst(request) {
  const cache = await caches.open(STATIC_CACHE);
  const hit = await cache.match(request);
  if (hit) return hit;
  const response = await fetch(request);
  if (response.ok) {
    await cache.put(request, response.clone());
    await trim(cache);
  }
  return response;
}

async function pageOrOffline(request) {
  try {
    return await fetch(request);
  } catch (error) {
    const offline = await caches.match(OFFLINE_URL);
    if (offline) return offline;
    throw error;
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;  // maps, fonts, photos: the browser handles them
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/uploads/")) return;  // always live, never stored
  if (request.mode === "navigate") event.respondWith(pageOrOffline(request));
  else if (isCacheableStatic(url)) event.respondWith(cacheFirst(request));
});
