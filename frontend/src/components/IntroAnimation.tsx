import { useEffect, useState } from "react";

/**
 * Opening animation: a plane and the word "LiveTrip" rise out of the dark; the plane flies off, and the dark splits
 * open from the word's band to uncover the home page, which has loaded underneath the whole time.
 * Plays once per browser session; a click, a key or "Skip" ends it, and reduced-motion users never see it.
 */

const DURATION_MS = 3700;
const SEEN_KEY = "liveTrip-intro-seen";
const FILL = "linear-gradient(135deg, #67e8f9 0%, #06b6d4 45%, #0e7490 100%)";  // the brand teal, light to deep
const PLANE = "M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z";
const PLANE_MASK = `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='${PLANE}'/></svg>")`;

export function shouldPlayIntro(): boolean {
  try {
    if (sessionStorage.getItem(SEEN_KEY)) return false;
  } catch { /* storage blocked: play it, it's short */ }
  return !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

export default function IntroAnimation({ onDone }: { onDone: () => void }) {
  const [leaving, setLeaving] = useState(false);
  const skip = () => { setLeaving(true); window.setTimeout(onDone, 350); };  // quick fade, then the app

  useEffect(() => {
    try { sessionStorage.setItem(SEEN_KEY, "1"); } catch { /* fine */ }
    const timer = window.setTimeout(onDone, DURATION_MS);
    const onKey = () => { window.clearTimeout(timer); skip(); };
    window.addEventListener("keydown", onKey);
    return () => { window.clearTimeout(timer); window.removeEventListener("keydown", onKey); };
  }, []);

  return (
    <div className={`fixed inset-0 z-[100] overflow-hidden intro-root ${leaving ? "intro-leave" : ""}`}
         onClick={skip} role="img" aria-label="LiveTrip">
      {/* the dark, in two halves that part from the word's band to show the home page */}
      <div className="absolute inset-x-0 top-0 h-1/2 bg-black intro-curtain-top" />
      <div className="absolute inset-x-0 bottom-0 h-1/2 bg-black intro-curtain-bottom" />

      <div className="absolute left-1/2 top-1/2 intro-plane"
           style={{ background: FILL, width: "min(34vw, 190px)", height: "min(34vw, 190px)",
                    marginLeft: "calc(min(34vw, 190px) / -2)",
                    WebkitMaskImage: PLANE_MASK, maskImage: PLANE_MASK, WebkitMaskSize: "contain", maskSize: "contain",
                    WebkitMaskRepeat: "no-repeat", maskRepeat: "no-repeat", WebkitMaskPosition: "center", maskPosition: "center" }} />

      <div className="absolute inset-x-0 top-1/2 flex justify-center intro-word" translate="no">
        <span className="font-black tracking-tight leading-none select-none"
              style={{ background: FILL, fontSize: "clamp(3.5rem, 17vw, 10rem)", WebkitBackgroundClip: "text",
                       backgroundClip: "text", color: "transparent", WebkitTextFillColor: "transparent" }}>
          LiveTrip
        </span>
      </div>

      <button type="button" className="absolute bottom-6 right-6 text-white/70 hover:text-white text-sm px-3 py-1 rounded-full border border-white/30 intro-skip"
              onClick={(e) => { e.stopPropagation(); skip(); }}>
        Skip
      </button>
    </div>
  );
}
