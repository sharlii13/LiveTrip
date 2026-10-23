import { useEffect, useState } from "react";
import { buddySay } from "@/components/AssistantBuddy";
import { Loader2, MapPin } from "lucide-react";

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
        <Loader2 className="w-12 h-12 mx-auto animate-spin text-primary" />
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
