import { useEffect, useState } from "react";

/**
 * Opening animation: a plane and the word "LiveTrip", both cut out of a landscape photo, rise out of the dark;
 * the plane flies off, the photo opens out from the word to fill the screen, and the app fades in underneath.
 * Plays once per browser session; a click, a key or "Skip" ends it, and reduced-motion users never see it.
 */

const IMAGE = "/images/intro-hills.jpg";  // a frame of the home page's hero video
const DURATION_MS = 3700;
const SEEN_KEY = "liveTrip-intro-seen";
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

  const photo = { backgroundImage: `url(${IMAGE})`, backgroundSize: "cover", backgroundPosition: "center" };

  return (
    <div className={`fixed inset-0 z-[100] bg-black overflow-hidden intro-root ${leaving ? "intro-leave" : ""}`}
         onClick={skip} role="img" aria-label="LiveTrip">
      {/* the photo opening out from the word's band to full screen */}
      <div className="absolute inset-0 intro-reveal" style={photo} />

      {/* the plane, cut out of the photo */}
      <div className="absolute left-1/2 top-1/2 intro-plane"
           style={{ ...photo, width: "min(34vw, 190px)", height: "min(34vw, 190px)", marginLeft: "calc(min(34vw, 190px) / -2)",
                    WebkitMaskImage: PLANE_MASK, maskImage: PLANE_MASK, WebkitMaskSize: "contain", maskSize: "contain",
                    WebkitMaskRepeat: "no-repeat", maskRepeat: "no-repeat", WebkitMaskPosition: "center", maskPosition: "center" }} />

      {/* the word, cut out of the photo */}
      <div className="absolute inset-x-0 top-1/2 flex justify-center intro-word" translate="no">
        <span className="font-black tracking-tight leading-none select-none"
              style={{ ...photo, fontSize: "clamp(3.5rem, 17vw, 10rem)", WebkitBackgroundClip: "text", backgroundClip: "text",
                       color: "transparent", WebkitTextFillColor: "transparent" }}>
          LiveTrip
        </span>
      </div>

      <button type="button" className="absolute bottom-6 right-6 text-white/70 hover:text-white text-sm px-3 py-1 rounded-full border border-white/30"
              onClick={(e) => { e.stopPropagation(); skip(); }}>
        Skip
      </button>
    </div>
  );
}
