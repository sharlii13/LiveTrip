import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown, Flame, Navigation, Sparkles, Star } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, Place, Slot } from "@/lib/livetrip";

interface Spot extends Place { known_for: string | null }
interface Found {
  dishes: { dish: string; veg: boolean; about: string }[];
  spots: Spot[];
  veg_only: boolean;
  note: string;
}

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
  const [found, setFound] = useState<Found | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toggle = () => {
    setOpen((o) => !o);
    if (found || open) return;
    setError(null);
    const { latitude, longitude } = slot.activity.location;
    const q = new URLSearchParams({ lat: String(latitude), lng: String(longitude), city, diet: diet || "any" });
    api<Found>(`/api/recommendations/famous-food?${q}`).then(setFound).catch((e) => setError((e as Error).message));
  };

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
              {!found && !error && <div className="space-y-2"><Skeleton className="h-5 w-2/3" /><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div>}
              {found && (
                <>
                  {found.dishes.length > 0 && (
                    <section>
                      <h4 className="font-semibold mb-1.5 flex items-center gap-2">
                        <span>Must-try in <span className="capitalize">{city}</span></span>{found.veg_only && <Badge variant="outline" className="border-green-600 text-green-700">Veg only</Badge>}
                      </h4>
                      <ul className="grid sm:grid-cols-2 gap-x-4 gap-y-1.5">
                        {found.dishes.map((d, i) => (
                          <motion.li key={d.dish} {...item(i)} className="flex gap-2">
                            <span className="mt-0.5"><DietMark veg={d.veg} /></span>
                            <span><span className="font-medium">{d.dish}</span>
                              {d.about && <span className="block text-xs text-muted-foreground">{d.about}</span>}</span>
                          </motion.li>
                        ))}
                      </ul>
                    </section>
                  )}
                  <section>
                    <h4 className="font-semibold mb-1.5">Famous spots near this stop</h4>
                    {found.spots.length === 0 && <p className="text-muted-foreground">No well-known food spots found within 10 km.</p>}
                    <ul className="space-y-2">
                      {found.spots.map((s, i) => (
                        <motion.li key={s.place_id} {...item(i + found.dishes.length)}
                                   className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-background/80 p-2">
                          <div className="min-w-0">
                            <p className="font-medium">{s.name}</p>
                            <p className="text-xs text-muted-foreground flex flex-wrap items-center gap-x-2">
                              {s.known_for && <span className="inline-flex items-center text-orange-700 dark:text-orange-300 font-medium"><Flame className="w-3 h-3 mr-0.5" />Famous for {s.known_for}</span>}
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
                  <p className="text-[11px] text-muted-foreground">{found.note}</p>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
