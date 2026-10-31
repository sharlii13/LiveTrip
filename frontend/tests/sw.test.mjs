// Self-check for public/sw.js with fake browser APIs. Run: npm run test:sw
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const ORIGIN = "https://livetrip.example";

function loadWorker(network) {
  const stores = new Map();
  const open = async (name) => {
    if (!stores.has(name)) stores.set(name, new Map());
    const store = stores.get(name);
    return {
      addAll: async (paths) => paths.forEach((p) => store.set(new URL(p, ORIGIN).href, `cached ${p}`)),
      match: async (r) => store.get(r.url ?? new URL(r, ORIGIN).href),
      put: async (r, value) => store.set(r.url, value),
      keys: async () => [...store.keys()].map((url) => ({ url })),
      delete: async (k) => store.delete(k.url),
    };
  };
  const caches = {
    open,
    keys: async () => [...stores.keys()],
    delete: async (name) => stores.delete(name),
    match: async (r) => {
      for (const store of stores.values()) {
        const hit = store.get(new URL(r, ORIGIN).href);
        if (hit) return hit;
      }
    },
  };
  const handlers = {};
  const self = { location: { origin: ORIGIN }, addEventListener: (n, h) => { handlers[n] = h; },
                 skipWaiting: async () => {}, clients: { claim: async () => {} } };
  vm.runInNewContext(readFileSync(new URL("../public/sw.js", import.meta.url), "utf8"),
                     { self, caches, fetch: network, URL, Promise, Math, console });
  const lifecycle = async (name) => {
    let done;
    handlers[name]({ waitUntil: (p) => { done = p; } });
    await done;
  };
  const request = (path, extra = {}) => {
    let responded;
    handlers.fetch({ request: { url: new URL(path, ORIGIN).href, method: "GET", mode: "cors", ...extra },
                     respondWith: (p) => { responded = p; } });
    return responded;
  };
  return { lifecycle, request, stores };
}

const ok = (body) => ({ ok: true, body, clone() { return this; } });

test("API, uploads, writes and other sites are never touched", async () => {
  const w = loadWorker(async () => assert.fail("the worker must not fetch these"));
  await w.lifecycle("install");
  assert.equal(w.request("/api/itinerary/1"), undefined);
  assert.equal(w.request("/api/auth/google", { mode: "navigate" }), undefined);  // sign-in redirects stay untouched
  assert.equal(w.request("/uploads/photo.jpg"), undefined);
  assert.equal(w.request("/assets/app.js", { method: "POST" }), undefined);
  assert.equal(w.request("https://tile.openstreetmap.org/1/1/1.png"), undefined);
  assert.equal(w.request("/videos/hero-video.mp4"), undefined);
});

test("pages come from the network and are not stored; offline shows the offline page", async () => {
  let online = true;
  const w = loadWorker(async () => { if (!online) throw new TypeError("offline"); return ok("live page"); });
  await w.lifecycle("install");
  assert.equal((await w.request("/trips/5", { mode: "navigate" })).body, "live page");
  const stored = [...w.stores.values()].flatMap((s) => [...s.keys()]);
  assert.ok(!stored.some((u) => u.includes("/trips/5")));
  online = false;
  assert.equal(await w.request("/trips/5", { mode: "navigate" }), "cached /offline.html");
});

test("build files are cached after the first load; old caches and old entries go", async () => {
  let fetches = 0;
  const w = loadWorker(async () => { fetches += 1; return ok("file"); });
  await w.lifecycle("install");
  await w.request("/assets/app-abc.js");
  await w.request("/assets/app-abc.js");
  assert.equal(fetches, 1);
  w.stores.set("livetrip-static-v0", new Map());
  await w.lifecycle("activate");
  assert.ok(!w.stores.has("livetrip-static-v0"));
  for (let i = 0; i < 100; i += 1) await w.request(`/assets/f${i}.js`);
  const store = w.stores.get("livetrip-static-v1");
  assert.ok(store.size <= 80 + 3);
  assert.ok(store.has(`${ORIGIN}/offline.html`));  // the offline page survives trimming
});
