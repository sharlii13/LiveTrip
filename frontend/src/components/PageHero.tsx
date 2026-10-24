import { ReactNode, useEffect, useRef } from "react";
import { motion, useReducedMotion } from "framer-motion";

interface Props {
  title: string;
  subtitle?: ReactNode;
  clip: "plan" | "map" | "adapt" | "earn" | "stays" | "food" | "sights" | "experiences";  // /videos/clips/*
  icon?: ReactNode;
  children?: ReactNode;  // actions or stats shown on the right
}

/** The animated header every tab shares: a travel clip behind the title, a plane crossing on a dotted route,
 *  and the words sliding in. Reduced-motion users get the still poster and no movement. */
export default function PageHero({ title, subtitle, clip, icon, children }: Props) {
  const calm = useReducedMotion();
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => { if (!calm) video.current?.play().catch(() => {}); }, [calm]);

  return (
    <section className="relative h-56 sm:h-64 overflow-hidden bg-slate-900 text-white">
      {calm
        ? <img src={`/videos/clips/${clip}.jpg`} alt="" className="absolute inset-0 w-full h-full object-cover" />
        : <video ref={video} src={`/videos/clips/${clip}.mp4`} poster={`/videos/clips/${clip}.jpg`} muted loop playsInline
                 aria-hidden="true" className="absolute inset-0 w-full h-full object-cover page-hero-zoom" />}
      <div className="absolute inset-0 bg-gradient-to-r from-slate-950/85 via-slate-900/55 to-transparent" />

      {!calm && (
        <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 1000 260" preserveAspectRatio="none" aria-hidden="true">
          <path d="M -40 210 C 250 60, 600 230, 1040 40" fill="none" stroke="white" strokeOpacity=".35"
                strokeWidth="1.5" strokeDasharray="3 9" />
        </svg>
      )}
      {!calm && (
        <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
          <svg viewBox="0 0 24 24" className="page-hero-plane absolute w-7 h-7 fill-white drop-shadow">
            <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
          </svg>
        </div>
      )}

      <div className="relative h-full max-w-6xl mx-auto px-4 flex flex-col sm:flex-row sm:items-end justify-end sm:justify-between gap-4 pb-8">
        <motion.div initial={calm ? false : { opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}>
          <h1 className="text-3xl sm:text-5xl font-black tracking-tight flex items-center gap-3">
            {icon && <span className="inline-flex w-11 h-11 rounded-2xl bg-white/15 backdrop-blur items-center justify-center">{icon}</span>}
            {title}
          </h1>
          {subtitle && <p className="mt-2 text-white/80 max-w-xl">{subtitle}</p>}
        </motion.div>
        {children && (
          <motion.div initial={calm ? false : { opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.6, delay: 0.15 }} className="flex flex-wrap gap-2">
            {children}
          </motion.div>
        )}
      </div>
      {/* a soft curved edge into the page */}
      <svg className="absolute -bottom-px left-0 w-full h-6 text-background" viewBox="0 0 1000 24" preserveAspectRatio="none" aria-hidden="true">
        <path d="M0 24 C 300 0, 700 0, 1000 24 Z" fill="currentColor" />
      </svg>
    </section>
  );
}

/** A small frosted chip for numbers in a PageHero ("3 trips", "120 points"). */
export function HeroStat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-2xl bg-white/15 backdrop-blur px-4 py-2 text-center min-w-[5.5rem]">
      <p className="text-xl font-bold tabular-nums">{value}</p>
      <p className="text-[11px] uppercase tracking-wider text-white/75">{label}</p>
    </div>
  );
}
