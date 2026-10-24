import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { motion, MotionValue, useMotionValueEvent, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { ArrowRight } from "lucide-react";

/**
 * Scroll story: a full-screen stage stays pinned while you scroll through four chapters. Each chapter is a clip
 * from the hero video that the "camera" slowly pushes into; chapters cross-fade, their words slide in and out,
 * and a plane flies along a route that draws itself, dropping a pin at every chapter.
 */

const CHAPTERS = [
  { clip: "plan", kicker: "01 · Plan", title: "Tell us where. We plan the rest.",
    body: "Pick a place and your dates. LiveTrip builds a day-by-day route of the best spots, timed and close together.",
    cta: { to: "/trip-planning", label: "Plan a trip" }, pin: "Plan" },
  { clip: "map", kicker: "02 · See it live", title: "Every stop on a live map.",
    body: "Photos, stories and the shortest way between stops. Drag a card to reorder your day and the map follows.",
    cta: { to: "/trips", label: "See my trips" }, pin: "Map" },
  { clip: "adapt", kicker: "03 · Adapt", title: "Rain? Running late? Your plan adapts.",
    body: "Live weather and one tap to shift, swap or slow down your day. Your travel buddy suggests what fits right now.",
    cta: { to: "/assistant", label: "Ask the buddy" }, pin: "Adapt" },
  { clip: "earn", kicker: "04 · Share & earn", title: "Check in, earn points, share the moment.",
    body: "Collect badges and real rewards as you explore, and plan the next trip together with friends.",
    cta: { to: "/rewards", label: "View rewards" }, pin: "Earn" },
];
const N = CHAPTERS.length;
// the flight route across the stage (viewBox 0 0 1000 600) and where on it each chapter's pin sits
const ROUTE = "M 560 590 C 650 520, 590 430, 690 400 S 830 360, 830 270 S 880 150, 975 80";  // right side, clear of the text
const PIN_AT = [0.1, 0.38, 0.64, 0.9];

function Chapter({ index, progress, active }: { index: number; progress: MotionValue<number>; active: number }) {
  const c = CHAPTERS[index];
  const start = index / N, end = (index + 1) / N, fade = 0.05;
  const opacity = useTransform(progress, index === 0 ? [0, end - fade, end + fade] : [start - fade, start + fade, end - fade, end + fade],
                               index === 0 ? [1, 1, 0] : index === N - 1 ? [0, 1, 1, 1] : [0, 1, 1, 0]);
  const scale = useTransform(progress, [start - fade, end + fade], [1.04, 1.32]);  // the camera pushing in
  const textY = useTransform(progress, [start, start + 0.07, end - 0.07, end], index === 0 ? [0, 0, 0, -60] : [70, 0, 0, -60]);
  const textOpacity = useTransform(progress, [start, start + 0.06, end - 0.06, end],
                                   index === 0 ? [1, 1, 1, 0] : index === N - 1 ? [0, 1, 1, 1] : [0, 1, 1, 0]);
  const video = useRef<HTMLVideoElement>(null);

  useEffect(() => {  // only the chapter on screen (and the next) play: smooth hand-over, no wasted decoding
    const v = video.current;
    if (!v) return;
    if (Math.abs(active - index) <= 1) v.play().catch(() => {});
    else v.pause();
  }, [active, index]);

  return (
    <motion.div className="absolute inset-0" style={{ opacity }} aria-hidden={active !== index}>
      <motion.video ref={video} className="absolute inset-0 w-full h-full object-cover" style={{ scale }}
                    src={`/videos/clips/${c.clip}.mp4`} poster={`/videos/clips/${c.clip}.jpg`}
                    muted loop playsInline preload="metadata" />
      <div className="absolute inset-0 bg-gradient-to-r from-black/75 via-black/35 to-transparent" />
      {/* outer box places the text; the inner one moves (framer's transform would undo a CSS centring) */}
      <div className="absolute inset-y-0 left-6 sm:left-16 right-14 flex items-end sm:items-center pb-24 sm:pb-0">
        <motion.div className="max-w-xl text-white" style={{ y: textY, opacity: textOpacity }}>
          <p className="uppercase tracking-[0.3em] text-sm text-brand-300 mb-3">{c.kicker}</p>
          <h3 className="text-4xl sm:text-6xl font-black leading-[1.05] mb-4">{c.title}</h3>
          <p className="text-lg sm:text-xl text-white/85 mb-6">{c.body}</p>
          <Link to={c.cta.to}
                className="inline-flex items-center gap-2 rounded-full bg-white text-slate-900 px-5 py-2.5 font-semibold hover:gap-3 transition-all">
            {c.cta.label}<ArrowRight className="w-4 h-4" />
          </Link>
        </motion.div>
      </div>
    </motion.div>
  );
}

function FlightPath({ progress }: { progress: MotionValue<number> }) {
  const path = useRef<SVGPathElement>(null);
  const plane = useRef<SVGGElement>(null);
  const [reached, setReached] = useState(0);
  const drawn = useTransform(progress, [0, 0.97], [0, 1]);

  useMotionValueEvent(drawn, "change", (v) => {
    const p = path.current, g = plane.current;
    if (!p || !g) return;
    const len = p.getTotalLength();
    const at = p.getPointAtLength(v * len), ahead = p.getPointAtLength(Math.min(len, v * len + 2));
    const angle = (Math.atan2(ahead.y - at.y, ahead.x - at.x) * 180) / Math.PI + 90;  // the icon points up
    g.setAttribute("transform", `translate(${at.x} ${at.y}) rotate(${angle})`);
    setReached(PIN_AT.filter((t) => v >= t).length);
  });

  return (
    <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 1000 600" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <path d={ROUTE} fill="none" stroke="white" strokeOpacity=".25" strokeWidth="2" strokeDasharray="2 10" strokeLinecap="round" />
      <motion.path ref={path} d={ROUTE} fill="none" stroke="#67e8f9" strokeWidth="3" strokeLinecap="round" style={{ pathLength: drawn }} />
      {PIN_AT.map((t, i) => <Pin key={i} at={t} label={CHAPTERS[i].pin} shown={i < reached} />)}
      <g ref={plane}>
        <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"
              transform="translate(-18 -18) scale(1.5)" fill="white" />
      </g>
    </svg>
  );
}

function Pin({ at, label, shown }: { at: number; label: string; shown: boolean }) {
  const [pt, setPt] = useState<{ x: number; y: number } | null>(null);
  useEffect(() => {
    const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", ROUTE);
    const point = p.getPointAtLength(p.getTotalLength() * at);
    setPt({ x: point.x, y: point.y });
  }, [at]);
  if (!pt) return null;
  return (
    <motion.g initial={false} animate={{ opacity: shown ? 1 : 0, y: shown ? 0 : -30 }}
              transition={{ type: "spring", stiffness: 300, damping: 18 }}>
      <g transform={`translate(${pt.x} ${pt.y})`}>
        <path d="M0 0 C -9 -14 -12 -20 -12 -26 A 12 12 0 1 1 12 -26 C 12 -20 9 -14 0 0 Z" fill="#0891b2" stroke="white" strokeWidth="2" />
        <circle cy="-26" r="4.5" fill="white" />
        <text y="-46" textAnchor="middle" fill="white" fontSize="16" fontWeight="700">{label}</text>
      </g>
    </motion.g>
  );
}

export default function JourneyStory() {
  const section = useRef<HTMLElement>(null);
  const calm = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: section, offset: ["start start", "end end"] });
  const [active, setActive] = useState(0);
  useMotionValueEvent(scrollYProgress, "change", (v) => setActive(Math.min(N - 1, Math.floor(v * N))));

  const goTo = (i: number) => {
    const el = section.current;
    if (!el) return;
    const top = el.getBoundingClientRect().top + window.scrollY;
    window.scrollTo({ top: top + ((el.offsetHeight - window.innerHeight) * (i + 0.15)) / N, behavior: "smooth" });
  };

  if (calm) {  // no scroll-linked motion: the same story as plain blocks
    return (
      <section aria-label="How LiveTrip works">
        {CHAPTERS.map((c) => (
          <div key={c.clip} className="relative h-[70vh] overflow-hidden">
            <img src={`/videos/clips/${c.clip}.jpg`} alt="" className="absolute inset-0 w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-r from-black/75 to-transparent" />
            <div className="relative h-full flex flex-col justify-center px-6 sm:px-16 max-w-2xl text-white">
              <p className="uppercase tracking-[0.3em] text-sm text-brand-300 mb-3">{c.kicker}</p>
              <h3 className="text-4xl sm:text-5xl font-black mb-4">{c.title}</h3>
              <p className="text-lg text-white/85 mb-6">{c.body}</p>
              <Link to={c.cta.to} className="self-start rounded-full bg-white text-slate-900 px-5 py-2.5 font-semibold">{c.cta.label}</Link>
            </div>
          </div>
        ))}
      </section>
    );
  }

  return (
    <section ref={section} className="relative bg-black" style={{ height: `${N * 100}vh` }} aria-label="How LiveTrip works">
      <div className="sticky top-0 h-screen overflow-hidden">
        {CHAPTERS.map((_, i) => <Chapter key={i} index={i} progress={scrollYProgress} active={active} />)}
        <FlightPath progress={scrollYProgress} />
        <nav className="absolute right-4 sm:right-8 top-1/2 -translate-y-1/2 flex flex-col gap-3" aria-label="Chapters">
          {CHAPTERS.map((c, i) => (
            <button key={c.clip} type="button" onClick={() => goTo(i)} aria-label={c.kicker} aria-current={active === i}
                    className={`h-3 rounded-full transition-all ${active === i ? "w-8 bg-brand-400" : "w-3 bg-white/50 hover:bg-white"}`} />
          ))}
        </nav>
        <motion.div className="absolute left-0 bottom-0 h-1 bg-brand-400 origin-left w-full" style={{ scaleX: scrollYProgress }} />
      </div>
    </section>
  );
}
