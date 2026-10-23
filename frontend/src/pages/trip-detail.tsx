import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  AlertTriangle, CheckCircle2, CloudRain, Download, Lock, MapPin, RefreshCw, SkipForward,
  Star, Sun, Unlock, Camera, Users, Bed, Bookmark, Route as RouteIcon, ChevronUp, ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/AuthContext";
import { api, currentPosition, describeAwards, Award, Place, Proposal, Slot, Trip } from "@/lib/livetrip";
import ProposalDialog from "@/components/livetrip/ProposalDialog";
import PlaceList from "@/components/livetrip/PlaceList";
import PlaceCard from "@/components/livetrip/PlaceCard";
import TripMap from "@/components/livetrip/TripMap";

interface Weather {
  temperature: number;
  condition: string;
  humidity: number;
  wind_speed: number;
  trip_forecast: { date: string; condition: string; temp_max?: number; temp_min?: number; precipitation_probability?: number; wet?: boolean }[];
}

interface AlertItem { id: string; message: string; acknowledged: boolean; severity: string }

const REASONS: Record<string, string> = {
  nearby: "Something else nearby",
  indoor: "Indoor (bad weather)",
  cheaper: "Cheaper or free",
  relaxed: "More relaxed",
};

export default function TripDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { toast } = useToast();
  const [trip, setTrip] = useState<Trip | null>(null);
  useEffect(() => {  // a change confirmed in the buddy's chat
    const onChanged = (e: Event) => setTrip((e as CustomEvent<Trip>).detail);
    window.addEventListener("livetrip-trip-changed", onChanged);
    return () => window.removeEventListener("livetrip-trip-changed", onChanged);
  }, []);
  const [error, setError] = useState<string | null>(null);
  const [weather, setWeather] = useState<Weather | null | undefined>(undefined);  // undefined = still loading
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [proposal, setProposal] = useState<{ p: Proposal; title: string } | null>(null);
  const [replacing, setReplacing] = useState<Slot | null>(null);
  const [reason, setReason] = useState("nearby");
  const [alternatives, setAlternatives] = useState<Place[] | null>(null);
  const [lateMinutes, setLateMinutes] = useState("30");
  const [busy, setBusy] = useState<string | null>(null);
  const [stays, setStays] = useState<Place[] | null>(null);
  const [stayBudget, setStayBudget] = useState("medium");
  const [matches, setMatches] = useState<{ wish: { id: number; name: string }; fits: boolean; ops: any[]; message: string }[]>([]);
  const [day, setDay] = useState("1");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [dragId, setDragId] = useState<number | null>(null);

  const load = async () => {
    try {
      setTrip(await api<Trip>(`/api/itinerary/${id}`));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  useEffect(() => {
    load();
    api<Weather>(`/api/itinerary/${id}/current-weather`).then(setWeather).catch(() => setWeather(null));
    api<AlertItem[]>(`/api/itinerary/${id}/alerts`).then(setAlerts).catch(() => setAlerts([]));
  }, [id]);

  useEffect(() => {
    if (isAuthenticated && id) {
      api<{ matches: typeof matches }>(`/api/wishlist/matches?trip_id=${id}`).then((r) => setMatches(r.matches)).catch(() => {});
    }
  }, [isAuthenticated, id, trip?.version]);

  const run = async (label: string, fn: () => Promise<void>) => {
    setBusy(label);
    try {
      await fn();
    } catch (e) {
      toast({ title: "Something went wrong", description: (e as Error).message, variant: "destructive" });
    } finally {
      setBusy(null);
    }
  };

  const propose = (reasonKey: string, title: string, extra: Record<string, unknown> = {}) =>
    run(reasonKey, async () => {
      const p = await api<Proposal>(`/api/itinerary/${id}/reschedule`, { method: "POST", json: { reason: reasonKey, ...extra } });
      setProposal({ p, title });
    });

  const applyOps = (ops: unknown[], message: string) =>
    run("apply", async () => {
      setTrip(await api<Trip>(`/api/itinerary/${id}/apply`, { method: "POST", json: { ops, expected_version: trip?.version } }));
      toast({ title: message });
    });

  const checkIn = (slot: Slot) =>
    run(`checkin-${slot.item_id}`, async () => {
      if (!isAuthenticated) {
        navigate(`/login?next=/trips/${id}`);
        return;
      }
      const pos = await currentPosition();
      const res = await api<{ verified: boolean; awards: Award[]; message: string | null; itinerary: Trip }>(
        `/api/itinerary/${id}/items/${slot.item_id}/complete`, { method: "POST", json: pos ?? {} });
      setTrip(res.itinerary);
      toast({
        title: res.awards.length ? `Checked in at ${slot.activity.name}` : "Marked as visited",
        description: res.awards.length ? describeAwards(res.awards) : res.message ?? undefined,
      });
    });

  const toggleLock = (slot: Slot) =>
    run(`lock-${slot.item_id}`, async () => {
      setTrip(await api<Trip>(`/api/itinerary/${id}/items/${slot.item_id}`, { method: "PATCH", json: { locked: !slot.locked } }));
    });

  const rate = (slot: Slot, rating: number) =>
    run(`rate-${slot.item_id}`, async () => {
      await api(`/api/itinerary/${id}/items/${slot.item_id}/feedback`, { method: "POST", json: { rating } });
      toast({ title: "Thanks! Future suggestions will use this." });
    });

  const openReplace = (slot: Slot) => {
    setReplacing(slot);
    setReason(slot.kind === "meal" ? "food" : "nearby");
    setAlternatives(null);
  };

  useEffect(() => {
    if (!replacing) return;
    setAlternatives(null);
    const loc = replacing.activity.location;
    const url = replacing.kind === "meal"
      ? `/api/recommendations/restaurants?lat=${loc.latitude}&lng=${loc.longitude}&diet=${trip?.user_preferences?.food === "vegetarian" ? "vegetarian" : "any"}`
      : `/api/itinerary/${id}/items/${replacing.item_id}/alternatives?reason=${reason}`;
    api<{ alternatives?: Place[]; results?: Place[] }>(url)
      .then((r) => setAlternatives(r.alternatives ?? r.results ?? []))
      .catch((e) => { setAlternatives([]); toast({ title: "No alternatives", description: e.message, variant: "destructive" }); });
  }, [replacing, reason]);

  const replaceWith = (place: Place) => {
    if (!replacing) return;
    applyOps([{ op: "replace", item_id: replacing.item_id, place }], `Replaced with ${place.name}`);
    setReplacing(null);
  };

  const findStays = () =>
    run("stays", async () => {
      const r = await api<{ results: Place[] }>(`/api/recommendations/stays?trip_id=${id}&budget=${stayBudget}`);
      setStays(r.results);
    });

  const share = () =>
    run("share", async () => {
      const g = await api<{ id: number }>("/api/groups", { method: "POST", json: { name: `${trip?.destination} trip`, trip_id: Number(id) } });
      navigate(`/groups/${g.id}`);
    });

  const acknowledge = (a: AlertItem) =>
    run("ack", async () => {
      await api(`/api/itinerary/${id}/alerts/${a.id}/acknowledge`, { method: "POST" });
      setAlerts((list) => list.map((x) => (x.id === a.id ? { ...x, acknowledged: true } : x)));
    });

  if (error) {
    return (
      <div className="max-w-3xl mx-auto p-8 text-center space-y-4">
        <p className="text-lg">{error}</p>
        <Button onClick={() => navigate("/trips")}>Back to my trips</Button>
      </div>
    );
  }
  if (!trip) return <div className="flex justify-center p-16"><RefreshCw className="w-8 h-8 animate-spin text-primary" /></div>;

  const openAlerts = alerts.filter((a) => !a.acknowledged);
  const currentDay = trip.days.find((d) => String(d.day) === day) ?? trip.days[0];

  const selectFromMap = (itemId: number) => {
    setSelectedId(itemId);
    document.getElementById(`stop-${itemId}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const reorder = (dayNum: number, order: number[], message: string) =>
    applyOps([{ op: "reorder", day: dayNum, order }], message);

  const moveTo = (d: Trip["days"][number], fromId: number, toId: number) => {
    const ids = d.time_slots.map((s) => s.item_id);
    const without = ids.filter((x) => x !== fromId);
    without.splice(without.indexOf(toId) + (ids.indexOf(fromId) < ids.indexOf(toId) ? 1 : 0), 0, fromId);
    if (without.join() !== ids.join()) reorder(d.day, without, "Order updated");
  };

  const moveBy = (d: Trip["days"][number], itemId: number, delta: number) => {
    const ids = d.time_slots.map((s) => s.item_id);
    const i = ids.indexOf(itemId);
    const j = i + delta;
    if (j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    reorder(d.day, ids, "Order updated");
  };

  const slotActions = (s: Slot) => (
    <>
      {s.status === "planned" && (
        <>
          {s.kind === "visit" && (
            <Button size="sm" data-buddy="checkin" onClick={() => checkIn(s)} disabled={busy === `checkin-${s.item_id}`}>
              <CheckCircle2 className="w-4 h-4 mr-1" />Check in
            </Button>
          )}
          {!s.locked && (
            <>
              <Button size="sm" variant="outline" data-buddy="replace" onClick={() => openReplace(s)}><RefreshCw className="w-4 h-4 mr-1" />Replace</Button>
              <Button size="sm" variant="ghost" title="Skip" aria-label={`Skip ${s.activity.name}`} data-buddy="skip"
                      onClick={() => applyOps([{ op: "skip", item_id: s.item_id }], `Skipped ${s.activity.name}`)}>
                <SkipForward className="w-4 h-4" />
              </Button>
            </>
          )}
          <Button size="sm" variant="ghost" title={s.locked ? "Unconfirm" : "Confirm (keep when rescheduling)"}
                  aria-label={s.locked ? "Unconfirm" : "Confirm"} onClick={() => toggleLock(s)}>
            {s.locked ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
          </Button>
        </>
      )}
      {s.status === "completed" && s.kind === "visit" && isAuthenticated && (
        <>
          <span className="flex items-center" aria-label="Rate this stop">
            {[1, 2, 3, 4, 5].map((n) => (
              <button key={n} onClick={() => rate(s, n)} title={`${n} star${n > 1 ? "s" : ""}`}>
                <Star className="w-4 h-4 text-yellow-400 hover:fill-yellow-400" />
              </button>
            ))}
          </span>
          <Button size="sm" variant="outline" asChild>
            <Link to={`/feed?trip=${id}&item=${s.item_id}`}><Camera className="w-4 h-4 mr-1" />Photo</Link>
          </Button>
        </>
      )}
    </>
  );

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold capitalize">{trip.destination}</h1>
          <p className="text-muted-foreground">
            {trip.start_date} → {trip.end_date} · {trip.days.length} day{trip.days.length > 1 ? "s" : ""} ·{" "}
            <Badge variant="secondary" className="capitalize">{trip.status}</Badge>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" asChild data-buddy="export">
            <a href={`/api/itinerary/${id}/export?format=txt`}><Download className="w-4 h-4 mr-1" />Export</a>
          </Button>
          {isAuthenticated && trip.user_id && (
            <Button variant="outline" size="sm" onClick={share} disabled={busy === "share"}>
              <Users className="w-4 h-4 mr-1" />Plan with friends
            </Button>
          )}
        </div>
      </div>

      {[trip.places_note, trip.distance_note].filter(Boolean).map((note) => (
        <p key={note} className="text-xs text-muted-foreground flex items-center gap-1"><AlertTriangle className="w-3 h-3 shrink-0" />{note}</p>
      ))}

      {openAlerts.length > 0 && (
        <Card className="border-amber-300 bg-amber-50 dark:bg-amber-950/30">
          <CardContent className="pt-4 space-y-2">
            {openAlerts.map((a) => (
              <div key={a.id} className="flex items-start justify-between gap-2 text-sm">
                <span className="flex gap-2"><CloudRain className="w-4 h-4 mt-0.5 shrink-0" />{a.message}</span>
                <Button size="sm" variant="ghost" onClick={() => acknowledge(a)}>Dismiss</Button>
              </div>
            ))}
            <Button size="sm" onClick={() => propose("weather", "Weather changes")} disabled={!!busy}>Review weather changes</Button>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="lg:col-span-7 min-w-0">
          <Tabs value={day} onValueChange={(v) => { setDay(v); setSelectedId(null); }}>
            <TabsList className="flex-wrap h-auto">
              {trip.days.map((d) => {
                const f = weather?.trip_forecast?.[d.day - 1];
                return (
                  <TabsTrigger key={d.day} value={String(d.day)} className="gap-1">
                    Day {d.day}
                    {f?.wet ? <CloudRain className="w-3 h-3 text-blue-500" /> : f?.temp_max !== undefined ? <Sun className="w-3 h-3 text-amber-500" /> : null}
                  </TabsTrigger>
                );
              })}
            </TabsList>
            {trip.days.map((d) => {
              const visitNumbers = new Map(d.time_slots.filter((s) => s.kind === "visit").map((s, i) => [s.item_id, i + 1]));
              return (
                <TabsContent key={d.day} value={String(d.day)} className="space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
                    <span>
                      {new Date(d.date + "T00:00:00").toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" })}
                      {weather?.trip_forecast?.[d.day - 1] && ` · ${weather.trip_forecast[d.day - 1].condition}`}
                      {weather?.trip_forecast?.[d.day - 1]?.temp_max !== undefined &&
                        ` ${Math.round(weather.trip_forecast[d.day - 1].temp_min!)}–${Math.round(weather.trip_forecast[d.day - 1].temp_max!)}°C`}
                      {` · ${d.total_travel_time} min travel`}
                    </span>
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="outline" onClick={() => propose("relaxed", "A more relaxed day", { day: d.day })} disabled={!!busy} data-buddy="relaxed">Make it relaxed</Button>
                      <Button data-buddy="optimise" size="sm" variant="outline" onClick={() => run("optimize", async () => {
                        setTrip(await api<Trip>(`/api/itinerary/${id}/route-optimization?day_index=${d.day - 1}`, { method: "POST" }));
                        toast({ title: "Route reordered to cut travel" });
                      })} disabled={!!busy}><RouteIcon className="w-4 h-4 mr-1" />Optimise route</Button>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span>Running late?</span>
                    <Input className="w-20 h-8" type="number" min={5} max={600} value={lateMinutes} onChange={(e) => setLateMinutes(e.target.value)} />
                    <span>min</span>
                    <Button size="sm" variant="outline" disabled={!!busy} data-buddy="late"
                            onClick={() => propose("delay", "Shift the rest of the day", { day: d.day, minutes: Number(lateMinutes) || 30 })}>
                      Adjust schedule
                    </Button>
                    <span className="text-xs text-muted-foreground ml-auto">Drag cards (or use the arrows) to change the order.</span>
                  </div>

                  {d.time_slots.length === 0 && <p className="text-muted-foreground">Nothing planned for this day yet.</p>}
                  {d.time_slots.map((s, index) => {
                    const movable = s.status === "planned" && !s.locked;
                    return (
                      <div key={s.item_id}
                           className={dragId !== null && dragId !== s.item_id ? "rounded-lg outline-dashed outline-2 outline-transparent hover:outline-primary/40" : ""}
                           onDragOver={(e) => { if (dragId !== null) e.preventDefault(); }}
                           onDrop={(e) => { e.preventDefault(); if (dragId !== null && dragId !== s.item_id) moveTo(d, dragId, s.item_id); setDragId(null); }}>
                        <PlaceCard
                          slot={s}
                          number={visitNumbers.get(s.item_id)}
                          city={trip.destination}
                          selected={selectedId === s.item_id}
                          onSelect={() => setSelectedId(s.item_id)}
                          actions={slotActions(s)}
                          dragProps={movable ? {
                            draggable: true,
                            onDragStart: (e) => { setDragId(s.item_id); e.dataTransfer.effectAllowed = "move"; },
                            onDragEnd: () => setDragId(null),
                          } : undefined}
                          moveControls={movable ? (
                            <span onClick={(e) => e.stopPropagation()} className="flex">
                              <Button size="icon" variant="ghost" className="h-7 w-7" aria-label="Move earlier" disabled={index === 0 || !!busy}
                                      onClick={() => moveBy(d, s.item_id, -1)}><ChevronUp className="w-4 h-4" /></Button>
                              <Button size="icon" variant="ghost" className="h-7 w-7" aria-label="Move later" disabled={index === d.time_slots.length - 1 || !!busy}
                                      onClick={() => moveBy(d, s.item_id, 1)}><ChevronDown className="w-4 h-4" /></Button>
                            </span>
                          ) : undefined}
                        />
                      </div>
                    );
                  })}
                </TabsContent>
              );
            })}
          </Tabs>
        </div>

        <div className="lg:col-span-5 order-first lg:order-none">
          <div className="lg:sticky lg:top-20 space-y-2">
            <div className="h-72 sm:h-[420px] lg:h-[calc(100vh-8rem)] lg:max-h-[760px] rounded-lg border overflow-hidden shadow-sm">
              <TripMap slots={currentDay?.time_slots ?? []} selectedId={selectedId} onSelect={selectFromMap} start={trip.start_location} />
            </div>
            <p className="text-xs text-muted-foreground">
              Day {currentDay?.day}: numbers show the visiting order, 🍽 marks meals. Click a marker to jump to its card.
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-lg">Live weather</CardTitle></CardHeader>
          <CardContent className="text-sm">
            {weather ? (
              <>
                <p className="text-2xl font-semibold">{Math.round(weather.temperature)}°C <span className="text-base font-normal capitalize">{weather.condition}</span></p>
                <p className="text-muted-foreground">Humidity {weather.humidity}% · Wind {weather.wind_speed} km/h</p>
                <Button size="sm" variant="outline" className="mt-2" onClick={() => propose("weather", "Weather changes")} disabled={!!busy} data-buddy="weather">
                  <CloudRain className="w-4 h-4 mr-1" />Check outdoor plans
                </Button>
              </>
            ) : <p className="text-muted-foreground">{weather === undefined ? "Loading weather..." : "Weather is unavailable right now."}</p>}
          </CardContent>
        </Card>


        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-lg flex items-center gap-2"><Bed className="w-4 h-4" />Where to stay</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            <div className="flex gap-2">
              <Select value={stayBudget} onValueChange={setStayBudget}>
                <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Budget</SelectItem>
                  <SelectItem value="medium">Mid-range</SelectItem>
                  <SelectItem value="high">Luxury</SelectItem>
                </SelectContent>
              </Select>
              <Button size="sm" onClick={findStays} disabled={busy === "stays"} data-buddy="stays">Find stays</Button>
            </div>
            {stays && <PlaceList places={stays} empty="No stays found near your stops." />}
            {stays && <p className="text-xs text-muted-foreground">Sorted by distance to your planned stops. Prices and availability are not live.</p>}
          </CardContent>
        </Card>

        {matches.length > 0 && (
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-lg flex items-center gap-2"><Bookmark className="w-4 h-4" />Saved places for this trip</CardTitle></CardHeader>
            <CardContent className="space-y-2 text-sm">
              {matches.map((m) => (
                <div key={m.wish.id} className="flex items-center justify-between gap-2">
                  <span>{m.wish.name}<span className="block text-xs text-muted-foreground">{m.message}</span></span>
                  {m.fits && <Button size="sm" variant="outline" onClick={() => applyOps(m.ops, `Added ${m.wish.name}`)}>Add</Button>}
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>

      <ProposalDialog tripId={id!} proposal={proposal?.p ?? null} title={proposal?.title} onClose={() => setProposal(null)} onApplied={setTrip} />

      <Dialog open={!!replacing} onOpenChange={(open) => !open && setReplacing(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Replace {replacing?.activity.name}</DialogTitle>
            <DialogDescription>Pick an alternative; times for the rest of the day update automatically.</DialogDescription>
          </DialogHeader>
          {replacing?.kind === "visit" && (
            <Select value={reason} onValueChange={setReason}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {Object.entries(REASONS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
              </SelectContent>
            </Select>
          )}
          <div className="max-h-80 overflow-y-auto">
            {alternatives === null ? <p className="text-sm text-muted-foreground"><MapPin className="w-4 h-4 inline animate-pulse" /> Looking nearby...</p>
              : <PlaceList places={alternatives} actionLabel="Choose" onAction={replaceWith} empty="Nothing suitable nearby." />}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
