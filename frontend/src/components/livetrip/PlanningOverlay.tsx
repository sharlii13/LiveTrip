import { useEffect, useId, useState } from "react";
import { buddySay } from "@/components/AssistantBuddy";
import { MapPin } from "lucide-react";

const PLANE = "M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z";

/** A plane flying a dotted route between two pins, over and over (still for reduced-motion users). */
function FlyingPlane() {
  const route = `planning-route-${useId().replace(/:/g, "")}`;
  const calm = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  return (
    <svg viewBox="0 0 240 100" className="w-60 h-24 mx-auto text-primary" aria-hidden="true">
      <path id={route} d="M 18 80 C 70 -10, 170 -10, 222 80" fill="none" stroke="currentColor" strokeOpacity=".35"
            strokeWidth="2.5" strokeDasharray="2 8" strokeLinecap="round" />
      {[18, 222].map((x) => (
        <g key={x} transform={`translate(${x} 80)`}>
          <path d="M0 0 C -6 -9 -8 -13 -8 -17 A 8 8 0 1 1 8 -17 C 8 -13 6 -9 0 0 Z" fill="currentColor" />
          <circle cy="-17" r="3" fill="white" />
        </g>
      ))}
      <g>
        {/* the icon points up; animateMotion's rotate="auto" lines up the x-axis with the route */}
        <path d={PLANE} transform="rotate(90) translate(-12 -12) scale(1.1)" fill="currentColor" />
        {calm ? <animateMotion dur="1s" fill="freeze" keyPoints="0.5;0.5" keyTimes="0;1" rotate="auto"><mpath href={`#${route}`} /></animateMotion>
              : <animateMotion dur="2.8s" repeatCount="indefinite" rotate="auto"><mpath href={`#${route}`} /></animateMotion>}
      </g>
    </svg>
  );
}

const STEPS = [
  "Finding the best places to visit",
  "Checking opening hours and the weather",
  "Arranging your stops to cut travel time",
  "Picking restaurants for lunch and dinner",
  "Putting your day-by-day plan together",
];

/** Full-screen wait message while an itinerary is being generated (it can take up to a minute). */
export default function PlanningOverlay({ open, destination }: { open: boolean; destination?: string }) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (!open) return;
    buddySay("Hang tight, I'm picking the best places for you...");
    setSeconds(0);
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [open]);

  if (!open) return null;
  const step = STEPS[Math.min(STEPS.length - 1, Math.floor(seconds / 6))];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 backdrop-blur-sm px-4"
         role="status" aria-live="polite">
      <div className="max-w-md w-full rounded-xl border bg-card p-8 text-center shadow-xl space-y-4">
        <FlyingPlane />
        <h2 className="text-2xl font-bold">Please wait while we plan your trip</h2>
        {destination && (
          <p className="flex items-center justify-center gap-1 text-muted-foreground">
            <MapPin className="w-4 h-4" />{destination}
          </p>
        )}
        <p className="font-medium">{step}...</p>
        <p className="text-sm text-muted-foreground">
          {seconds}s · Longer trips can take up to a minute. Please keep this page open.
        </p>
      </div>
    </div>
  );
}
