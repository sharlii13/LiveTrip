import { ReactNode, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { animate, motion, useInView, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";

interface Props {
  to: string;
  clip: string;       // /videos/clips/{clip}.mp4 and .jpg
  icon: ReactNode;
  title: string;
  subtitle: string;
  count: number;
  unit: string;
  note: string;
  accent: string;     // tailwind gradient, e.g. "from-brand-500 to-brand-400"
  delay?: number;
}

/** A category tile that plays its travel clip on hover (or when on screen on touch devices), tilts toward the
 *  pointer, and counts its number up the first time it scrolls into view. */
export default function VideoCategoryCard({ to, clip, icon, title, subtitle, count, unit, note, accent, delay = 0 }: Props) {
  const card = useRef<HTMLAnchorElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const calm = useReducedMotion();
  const inView = useInView(card, { amount: 0.5 });
  const seen = useInView(card, { once: true, amount: 0.4 });
  const [hover, setHover] = useState(false);
  const [shown, setShown] = useState(0);
  const touch = typeof window !== "undefined" && window.matchMedia?.("(hover: none)").matches;

  const mx = useMotionValue(0.5), my = useMotionValue(0.5);
  const rotateX = useSpring(useTransform(my, [0, 1], [8, -8]), { stiffness: 200, damping: 18 });
  const rotateY = useSpring(useTransform(mx, [0, 1], [-10, 10]), { stiffness: 200, damping: 18 });

  useEffect(() => {
    const v = video.current;
    if (!v || calm) return;
    if (hover || (touch && inView)) v.play().catch(() => {});
    else v.pause();
  }, [hover, inView, touch, calm]);

  useEffect(() => {
    if (!seen) return;
    if (calm) { setShown(count); return; }
    const controls = animate(0, count, { duration: 1.6, delay: delay + 0.2, ease: "easeOut", onUpdate: (v) => setShown(Math.round(v)) });
    return () => controls.stop();
  }, [seen]);

  return (
    <motion.div initial={calm ? false : { opacity: 0, y: 50 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }} transition={{ duration: 0.6, delay }} style={{ perspective: 900 }}>
      <motion.div style={calm ? undefined : { rotateX, rotateY, transformStyle: "preserve-3d" }}>
        <Link ref={card} to={to}
              onMouseEnter={() => setHover(true)}
              onMouseLeave={() => { setHover(false); mx.set(0.5); my.set(0.5); }}
              onMouseMove={(e) => {
                const r = e.currentTarget.getBoundingClientRect();
                mx.set((e.clientX - r.left) / r.width);
                my.set((e.clientY - r.top) / r.height);
              }}
              className="group relative block h-80 rounded-3xl overflow-hidden shadow-lg hover:shadow-2xl transition-shadow focus:outline-none focus-visible:ring-4 focus-visible:ring-brand-400">
          <video ref={video} src={`/videos/clips/${clip}.mp4`} poster={`/videos/clips/${clip}.jpg`} muted loop playsInline
                 preload="none" aria-hidden="true"
                 className="absolute inset-0 w-full h-full object-cover scale-105 group-hover:scale-110 transition-transform duration-700" />
          <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-black/10" />
          <div className="relative h-full flex flex-col justify-end p-6 text-white" style={{ transform: "translateZ(40px)" }}>
            <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${accent} flex items-center justify-center mb-4 shadow-lg
                             group-hover:-translate-y-1 group-hover:rotate-6 transition-transform`}>
              {icon}
            </div>
            <h3 className="text-2xl font-bold">{title}</h3>
            <p className="text-white/80">{subtitle}</p>
            <p className="mt-3 text-sm font-semibold">
              <span className="text-2xl tabular-nums">{shown.toLocaleString()}+</span> {unit}
            </p>
            <p className="text-xs text-white/70 max-h-0 opacity-0 group-hover:max-h-10 group-hover:opacity-100 transition-all duration-500">
              {note}
            </p>
          </div>
        </Link>
      </motion.div>
    </motion.div>
  );
}
