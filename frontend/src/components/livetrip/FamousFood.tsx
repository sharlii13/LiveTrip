import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown, Flame, Navigation, Sparkles, Star } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, Place, Slot } from "@/lib/livetrip";

interface Spot extends Place { known_for: string | null }
interface Nearby { spots: Spot[]; veg_only: boolean; note: string }
interface Dishes { dishes: { dish: string; veg: boolean; about: string }[]; spots: Spot[]; unavailable: boolean }

const compact = new Intl.NumberFormat(undefined, { notation: "compact" });

/** The Indian veg / non-veg mark: a green or red dot in a square. */
function DietMark({ veg }: { veg: boolean }) {
  return (
    <span title={veg ? "Vegetarian" : "Non-vegetarian"} aria-label={veg ? "Vegetarian" : "Non-vegetarian"}
          className={`inline-flex items-center justify-center w-3.5 h-3.5 shrink-0 border-[1.5px] rounded-[3px] ${veg ? "border-green-600" : "border-red-600"}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${veg ? "bg-green-600" : "bg-red-600"}`} />
    </span>
  );
}

/** On a lunch or dinner card: the city's signature dishes and the famous (often viral) eateries near this stop. */
export default function FamousFood({ slot, city, diet, onEatHere }: {
  slot: Slot; city: string; diet?: string; onEatHere?: (place: Place) => void;
}) {
  const calm = useReducedMotion();
  const [open, setOpen] = useState(false);
  const [nearby, setNearby] = useState<Nearby | null>(null);  // fast: the famous eateries around this stop
  const [extra, setExtra] = useState<Dishes | null>(null);     // slow: the AI's dishes, and what each eatery is known for
  const [error, setError] = useState<string | null>(null);

  const { latitude, longitude } = slot.activity.location;
  const query = new URLSearchParams({ lat: String(latitude), lng: String(longitude), city, diet: diet || "any" });
  const loadDishes = () => {
    setExtra(null);
    api<Dishes>(`/api/recommendations/famous-food/dishes?${query}`)
      .then(setExtra).catch(() => setExtra({ dishes: [], spots: [], unavailable: true }));
  };
  const toggle = () => {
    setOpen((o) => !o);
    if (nearby || open) return;
    setError(null);
    // both at once: the eateries show as soon as they're found, the dishes join when the AI answers
    api<Nearby>(`/api/recommendations/famous-food?${query}`).then(setNearby).catch((e) => setError((e as Error).message));
    loadDishes();
  };
  const spots = extra?.spots.length ? extra.spots : nearby?.spots ?? [];
  const dishes = extra?.dishes ?? [];

  const item = (i: number) => (calm ? {} : {
    initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { delay: i * 0.05 },
  });

  return (
    <div className="pt-1" onClick={(e) => e.stopPropagation()}>
      <Button size="sm" variant="outline" onClick={toggle} aria-expanded={open}
              className="border-orange-300 text-orange-700 hover:bg-orange-50 dark:border-orange-800 dark:text-orange-300 dark:hover:bg-orange-950/40">
        <Sparkles className="w-4 h-4 mr-1" />Famous food here
        <ChevronDown className={`w-4 h-4 ml-1 transition-transform ${open ? "rotate-180" : ""}`} />
      </Button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div key="panel" className="overflow-hidden"
                      initial={calm ? false : { height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
                      exit={calm ? undefined : { height: 0, opacity: 0 }} transition={{ duration: 0.25 }}>
            <div className="mt-2 rounded-lg border border-orange-200 dark:border-orange-900 bg-orange-50/60 dark:bg-orange-950/20 p-3 space-y-3 text-sm">
              {error && <p className="text-destructive">{error}</p>}
              {!nearby && !error && <div className="space-y-2"><Skeleton className="h-5 w-2/3" /><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div>}
              {nearby && (
                <>
                  <section>
                    <h4 className="font-semibold mb-1.5 flex items-center gap-2">
                      <span>Must-try in <span className="capitalize">{city}</span></span>{nearby.veg_only && <Badge variant="outline" className="border-green-600 text-green-700">Veg only</Badge>}
                    </h4>
                    {!extra && (
                      <p className="text-xs text-muted-foreground flex items-center gap-2" role="status">
                        <Sparkles className="w-3.5 h-3.5 text-orange-500 animate-pulse" />Asking our food guide about local favourites...
                      </p>
                    )}
                    {extra?.unavailable && (
                      <p className="text-xs text-muted-foreground flex flex-wrap items-center gap-2">
                        The food guide is busy right now, so local dishes couldn't load.
                        <Button size="sm" variant="outline" className="h-7" onClick={loadDishes}>Try again</Button>
                      </p>
                    )}
                    {dishes.length > 0 && (
                      <ul className="grid sm:grid-cols-2 gap-x-4 gap-y-1.5">
                        {dishes.map((d, i) => (
                          <motion.li key={d.dish} {...item(i)} className="flex gap-2">
                            <span className="mt-0.5"><DietMark veg={d.veg} /></span>
                            <span><span className="font-medium">{d.dish}</span>
                              {d.about && <span className="block text-xs text-muted-foreground">{d.about}</span>}</span>
                          </motion.li>
                        ))}
                      </ul>
                    )}
                  </section>
                  <section>
                    <h4 className="font-semibold mb-1.5">Famous spots near this stop</h4>
                    {spots.length === 0 && <p className="text-muted-foreground">No well-known food spots found within 10 km.</p>}
                    <ul className="space-y-2">
                      {spots.map((s, i) => (
                        <motion.li key={s.place_id} layout={!calm} {...item(i)}
                                   className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-background/80 p-2">
                          <div className="min-w-0">
                            <p className="font-medium">{s.name}</p>
                            <p className="text-xs text-muted-foreground flex flex-wrap items-center gap-x-2">
                              {s.known_for && (
                                <motion.span initial={calm ? false : { opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
                                             className="inline-flex items-center text-orange-700 dark:text-orange-300 font-medium">
                                  <Flame className="w-3 h-3 mr-0.5" />Famous for {s.known_for}
                                </motion.span>
                              )}
                              {s.rating > 0 && <span className="inline-flex items-center"><Star className="w-3 h-3 mr-0.5 fill-yellow-400 text-yellow-400" />{s.rating} ({compact.format(s.rating_count)})</span>}
                              <span>{s.distance_km} km · {s.travel_min} min</span>
                            </p>
                          </div>
                          <div className="flex gap-1">
                            <Button asChild size="sm" variant="ghost" className="h-8 px-2">
                              <a href={`https://www.google.com/maps/dir/?api=1&destination=${s.lat},${s.lng}`} target="_blank" rel="noreferrer"
                                 aria-label={`Directions to ${s.name}`}><Navigation className="w-4 h-4" /></a>
                            </Button>
                            {onEatHere && <Button size="sm" className="h-8" onClick={() => onEatHere(s)}>Eat here</Button>}
                          </div>
                        </motion.li>
                      ))}
                    </ul>
                  </section>
                  <p className="text-[11px] text-muted-foreground">{nearby.note}</p>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
