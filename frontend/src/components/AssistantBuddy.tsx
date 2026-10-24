import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { X } from "lucide-react";
import AssistantPanel from "@/components/livetrip/AssistantPanel";

/**
 * LiveTrip's buddy: a little character that lives in the corner, watches the cursor, glides next to the button or
 * field you rest on to explain it, greets you on each page, and opens the travel assistant chat when clicked.
 * Speech bubbles are normal page text, so they follow the app language like everything else.
 */

const HINTS: Record<string, string> = {
  checkin: "Tap this when you get there. I'll mark it visited and you earn points!",
  replace: "Not feeling it? I'll find something similar close by.",
  skip: "Skip it and I'll move the rest of your day up.",
  details: "Photos, a bit of history and directions for this stop.",
  relaxed: "Too packed? I can thin the day out for you.",
  optimise: "I'll reorder the stops so you spend less time travelling.",
  late: "Running late? Tell me how much and I'll shift everything.",
  weather: "I'll check if rain spoils any outdoor stops and suggest indoor ones.",
  stays: "I'll look for places to stay close to your stops.",
  export: "Save your plan as a file you can keep offline.",
  plan: "Hit this and I'll build your plan in a few seconds.",
  destination: "Just type where you want to go. I'll do the rest!",
  search: "Let's find your next adventure!",
  next: "Looks good! On to the next question.",
  language: "Pick a language and I'll switch the whole app to it.",
  signin: "Sign in to keep your trips on every device and earn points.",
};
// English button texts -> hint (data-buddy tags win; these cover the rest while the app is in English)
const TEXT_KEYS: Record<string, string> = {
  "see details": "details", "create itinerary": "plan", "create trip plan": "plan", "search": "search",
  "next": "next", "sign in": "signin", "check in": "checkin", "replace": "replace",
};
const GREETINGS: [RegExp, string][] = [
  [/^\/$/, "Hey there! Tell me where you want to go."],
  [/^\/trips\/\d+/, "Your plan is ready! Tap me if you want to change anything."],
  [/^\/trips$/, "Plan a new trip here, or open one you've made."],
  [/^\/(search|trip-planning)/, "Just a few quick questions and I'll plan it for you."],
  [/^\/feed/, "Share a photo from your trip and earn points!"],
  [/^\/rewards/, "Your points turn into real offers here."],
  [/^\/groups/, "Planning with friends? Everyone can suggest and vote."],
];

const SIZE = 56;
const SAID = new Set<string>();  // a page greets you once per visit to the app

/** Lets any part of the app make the buddy say something, e.g. while a trip is being planned. */
export function buddySay(text: string) {
  window.dispatchEvent(new CustomEvent("livetrip-buddy", { detail: text }));
}

function hintFor(el: Element | null): { key: string; target: Element } | null {
  const tagged = el?.closest<HTMLElement>("[data-buddy]");
  if (tagged?.dataset.buddy && HINTS[tagged.dataset.buddy]) return { key: tagged.dataset.buddy, target: tagged };
  const field = el?.closest<HTMLInputElement>("input[type=text], input:not([type])");
  if (field && /where|destination|jaipur/i.test(field.placeholder + field.id)) return { key: "destination", target: field };
  const button = el?.closest("button, a[role=button]");
  const key = button && TEXT_KEYS[(button.textContent || "").trim().toLowerCase()];
  return key ? { key, target: button! } : null;
}

export default function AssistantBuddy() {
  const { pathname } = useLocation();
  const calm = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const touch = typeof window !== "undefined" && window.matchMedia?.("(pointer: coarse)").matches;
  const home = () => ({ x: window.innerWidth - SIZE - 24, y: window.innerHeight - SIZE - 24 });
  const [pos, setPos] = useState(home);
  const [bubble, setBubble] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [look, setLook] = useState({ x: 0, y: 0 });
  const self = useRef<HTMLButtonElement>(null);
  const timers = useRef<{ hover?: number; hide?: number; back?: number }>({});
  const tripId = pathname.match(/^\/trips\/(\d+)/)?.[1] ?? null;

  const say = (text: string, ms = 5000) => {
    setBubble(text);
    window.clearTimeout(timers.current.hide);
    timers.current.hide = window.setTimeout(() => setBubble(null), ms);
  };
  const goHome = () => setPos(home());

  // greet on each page (once), and speak when another part of the app asks
  useEffect(() => {
    const greeting = GREETINGS.find(([re]) => re.test(pathname));
    if (greeting && !SAID.has(greeting[1])) {
      SAID.add(greeting[1]);
      const t = window.setTimeout(() => say(greeting[1]), 900);
      return () => window.clearTimeout(t);
    }
  }, [pathname]);
  useEffect(() => {
    const onSay = (e: Event) => say((e as CustomEvent<string>).detail, 8000);
    const onResize = () => setPos(home());
    window.addEventListener("livetrip-buddy", onSay);
    window.addEventListener("resize", onResize);
    return () => { window.removeEventListener("livetrip-buddy", onSay); window.removeEventListener("resize", onResize); };
  }, []);

  // eyes follow the pointer; resting on a known button or field brings the buddy over to explain it
  useEffect(() => {
    if (touch) return;
    let frame = 0;
    const onMove = (e: PointerEvent) => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const r = self.current?.getBoundingClientRect();
        if (!r) return;
        const dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2);
        const d = Math.hypot(dx, dy) || 1;
        setLook({ x: (dx / d) * Math.min(3, d / 40), y: (dy / d) * Math.min(3, d / 40) });
      });
    };
    const onOver = (e: PointerEvent) => {
      if (open) return;
      window.clearTimeout(timers.current.hover);
      const found = hintFor(e.target as Element);
      if (!found) return;
      timers.current.hover = window.setTimeout(() => {
        const r = found.target.getBoundingClientRect();
        if (!calm) {
          const right = r.right + 12 + SIZE < window.innerWidth;
          setPos({ x: right ? r.right + 12 : Math.max(8, r.left - SIZE - 12),
                   y: Math.min(Math.max(8, r.top + r.height / 2 - SIZE / 2), window.innerHeight - SIZE - 8) });
        }
        say(HINTS[found.key], 4500);
        window.clearTimeout(timers.current.back);
        timers.current.back = window.setTimeout(goHome, 5000);
      }, 600);
    };
    const onOut = () => window.clearTimeout(timers.current.hover);
    const onScroll = () => { window.clearTimeout(timers.current.back); goHome(); };
    window.addEventListener("pointermove", onMove);
    document.addEventListener("pointerover", onOver);
    document.addEventListener("pointerout", onOut);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerover", onOver);
      document.removeEventListener("pointerout", onOut);
      window.removeEventListener("scroll", onScroll);
    };
  }, [open, touch, calm]);

  useEffect(() => {
    if (!open) return;
    goHome();
    setBubble(null);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (pathname.startsWith("/assistant")) return null;  // that page is the chat already
  const bubbleLeft = pos.x > window.innerWidth / 2;

  return (
    <>
      <div className="fixed z-40 pointer-events-none" style={{
        left: 0, top: 0, transform: `translate(${pos.x}px, ${pos.y}px)`,
        transition: calm ? "none" : "transform 700ms cubic-bezier(.34,1.4,.64,1)",
      }}>
        {bubble && !open && (
          <div role="status" aria-live="polite"
               className={`absolute bottom-full mb-2 w-56 rounded-2xl bg-white text-slate-800 text-sm shadow-lg border px-3 py-2
                           buddy-pop ${bubbleLeft ? "right-0 rounded-br-sm" : "left-0 rounded-bl-sm"}`}>
            {bubble}
          </div>
        )}
        <button ref={self} type="button" onClick={() => setOpen((o) => !o)}
                aria-label={open ? "Close travel assistant" : "Open travel assistant"} aria-expanded={open}
                className={`pointer-events-auto block rounded-full focus:outline-none focus-visible:ring-4 focus-visible:ring-brand-300 ${calm ? "" : "buddy-bob"}`}
                style={{ width: SIZE, height: SIZE }}>
          <svg viewBox="0 0 64 64" width={SIZE} height={SIZE} aria-hidden="true">
            <defs>
              <radialGradient id="buddy-body" cx="35%" cy="30%" r="75%">
                <stop offset="0%" stopColor="#67e8f9" />
                <stop offset="100%" stopColor="#0e7490" />
              </radialGradient>
            </defs>
            <path d="M32 9 C34 4 39 3 42 5 C38 6 35 8 33 11 Z" fill="#155e75" />{/* leaf */}
            <ellipse cx="32" cy="60" rx="15" ry="2.5" fill="black" opacity=".15" />
            <circle cx="32" cy="34" r="23" fill="url(#buddy-body)" />
            <g className={calm ? "" : "buddy-blink"} style={{ transformOrigin: "32px 31px" }}>
              <ellipse cx="24" cy="31" rx="6" ry="7" fill="white" />
              <ellipse cx="40" cy="31" rx="6" ry="7" fill="white" />
              <circle cx={24 + look.x} cy={32 + look.y} r="3" fill="#0f172a" />
              <circle cx={40 + look.x} cy={32 + look.y} r="3" fill="#0f172a" />
            </g>
            <path d={bubble || open ? "M26 43 Q32 49 38 43" : "M27 44 Q32 47 37 44"} stroke="#083344" strokeWidth="2.2"
                  fill="none" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      {open && (
        <div role="dialog" aria-label="Travel assistant"
             className="fixed z-40 right-4 bottom-24 w-[min(24rem,calc(100vw-2rem))] rounded-2xl border bg-background shadow-2xl p-3 buddy-pop">
          <div className="flex items-center justify-between mb-2">
            <p className="font-semibold">Travel buddy{tripId ? "" : " · no trip open"}</p>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close" className="p-1 rounded hover:bg-muted">
              <X className="w-4 h-4" />
            </button>
          </div>
          <AssistantPanel key={tripId ?? "none"} tripId={tripId}
                          onTripChanged={(t) => window.dispatchEvent(new CustomEvent("livetrip-trip-changed", { detail: t }))}
                          className="h-[min(30rem,calc(100vh-12rem))]" />
        </div>
      )}
    </>
  );
}
