import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CalendarDays, MapPin, Plus, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/AuthContext";
import { api, localDate, recentTrips, rememberTrip, Trip } from "@/lib/livetrip";
import PlanningOverlay from "@/components/livetrip/PlanningOverlay";
import PageHero, { HeroStat } from "@/components/PageHero";
import Reveal from "@/components/home/Reveal";

interface TripSummary {
  id: number;
  destination: string;
  start_date: string;
  end_date: string;
  status: string;
  owned: boolean;
  visits: number;
  completed: number;
}

const today = () => localDate();
const SCENES = ["plan", "map", "adapt", "earn", "stays", "food", "sights", "experiences"];
// the same destination always gets the same scenic thumbnail
const sceneFor = (name: string) => SCENES[name.split("").reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7) % SCENES.length];

export default function Trips() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { toast } = useToast();
  const [trips, setTrips] = useState<TripSummary[] | null>(null);
  const [destination, setDestination] = useState("");
  const [start, setStart] = useState(today());
  const [end, setEnd] = useState(today());
  const [food, setFood] = useState("both");
  const [travelers, setTravelers] = useState("2");
  const [mustVisit, setMustVisit] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      api<TripSummary[]>("/api/trips").then(setTrips).catch(() => setTrips([]));
      return;
    }
    // signed out: show the trips planned on this device
    Promise.all(recentTrips().map((id) => api<Trip>(`/api/itinerary/${id}`).catch(() => null))).then((list) =>
      setTrips(list.filter((t): t is Trip => !!t).map((t) => {
        const visits = t.days.flatMap((d) => d.time_slots.filter((s) => s.kind === "visit"));
        return { id: Number(t.id), destination: t.destination, start_date: t.start_date, end_date: t.end_date,
                 status: t.status, owned: true, visits: visits.length,
                 completed: visits.filter((s) => s.status === "completed").length };
      })));
  }, [isAuthenticated]);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const trip = await api<Trip>("/api/trips", {
        method: "POST",
        json: {
          destination, startDate: start, endDate: end, foodPreference: food, pace: "normal",
          transportPreference: "car", travelers: Number(travelers) || 1,
          mustVisit: mustVisit.split(",").map((s) => s.trim()).filter(Boolean),
        },
      });
      rememberTrip(trip.id);
      navigate(`/trips/${trip.id}`);
    } catch (err) {
      toast({ title: "Could not plan this trip", description: (err as Error).message, variant: "destructive" });
    } finally {
      setCreating(false);
    }
  };

  const visited = trips?.reduce((n, t) => n + t.completed, 0) ?? 0;
  return (
    <>
    <PageHero title="My trips" clip="plan" icon={<MapPin className="w-6 h-6" />}
              subtitle="Every trip you've planned, live and up to date.">
      <HeroStat label="trips" value={trips?.length ?? "–"} />
      <HeroStat label="places visited" value={visited} />
    </PageHero>
    <div className="max-w-6xl mx-auto px-4 py-8 grid gap-6 lg:grid-cols-5">
      <PlanningOverlay open={creating} destination={destination} />
      <div className="lg:col-span-3 space-y-4">
        {!isAuthenticated && (
          <Card><CardContent className="pt-6 text-sm">
            <Link to="/login?next=/trips" className="text-primary underline">Sign in</Link> to keep your trips on every device, check in at places and earn points. Trips you plan now are saved on this device and moved to your account when you sign in.
          </CardContent></Card>
        )}
        {trips === null && <RefreshCw className="w-6 h-6 animate-spin text-primary" />}
        {trips?.length === 0 && <p className="text-muted-foreground">No trips yet. Plan your first one with the form.</p>}
        {trips?.map((t, i) => (
          <Reveal key={t.id} delay={Math.min(i, 6) * 0.07}>
            <Link to={`/trips/${t.id}`} className="group block mb-3">
              <Card className="overflow-hidden group-hover:-translate-y-1 transition-transform duration-300">
                <div className="flex">
                  <div className="relative w-28 sm:w-36 shrink-0 overflow-hidden">
                    <img src={`/videos/clips/${sceneFor(t.destination)}.jpg`} alt="" loading="lazy"
                         className="absolute inset-0 w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
                  </div>
                  <CardContent className="py-4 flex-1 min-w-0 space-y-2">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-semibold text-lg flex items-center gap-2 truncate" translate="no"><MapPin className="w-4 h-4 shrink-0 text-primary" />{t.destination}</p>
                        <p className="text-sm text-muted-foreground flex items-center gap-1"><CalendarDays className="w-3 h-3" />{t.start_date} → {t.end_date}</p>
                      </div>
                      <Badge variant={t.status === "completed" ? "default" : "secondary"} className="capitalize shrink-0">{t.status}</Badge>
                    </div>
                    <div>
                      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                        <div className="h-full rounded-full bg-gradient-to-r from-brand-500 to-brand-500 transition-all duration-700"
                             style={{ width: `${t.visits ? (100 * t.completed) / t.visits : 0}%` }} />
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{t.completed}/{t.visits} visited{t.owned ? "" : " · shared"}</p>
                    </div>
                  </CardContent>
                </div>
              </Card>
            </Link>
          </Reveal>
        ))}
        <p className="text-sm text-muted-foreground">
          Prefer a guided flow? Use the <Link to="/trip-planning" className="text-primary underline">step-by-step planner</Link>.
        </p>
      </div>

      <Card className="lg:col-span-2 h-fit">
        <CardHeader><CardTitle className="flex items-center gap-2"><Plus className="w-5 h-5" />Plan a trip</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={create} className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="dest">Destination</Label>
              <Input id="dest" placeholder="e.g. Jaipur" value={destination} onChange={(e) => setDestination(e.target.value)} required minLength={2} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1"><Label htmlFor="start">From</Label><Input id="start" type="date" value={start} onChange={(e) => setStart(e.target.value)} required /></div>
              <div className="space-y-1"><Label htmlFor="end">To</Label><Input id="end" type="date" value={end} min={start} onChange={(e) => setEnd(e.target.value)} required /></div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label>Food</Label>
                <Select value={food} onValueChange={setFood}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="both">No preference</SelectItem>
                    <SelectItem value="vegetarian">Vegetarian</SelectItem>
                    <SelectItem value="non-vegetarian">Non-vegetarian</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1"><Label htmlFor="trav">Travelers</Label><Input id="trav" type="number" min={1} max={50} value={travelers} onChange={(e) => setTravelers(e.target.value)} /></div>
            </div>
            <div className="space-y-1">
              <Label htmlFor="must">Must-visit places (optional, comma separated)</Label>
              <Input id="must" placeholder="e.g. Hawa Mahal, Amber Fort" value={mustVisit} onChange={(e) => setMustVisit(e.target.value)} />
            </div>
            <Button type="submit" className="w-full" disabled={creating}>
              {creating ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Building your itinerary...</> : "Create itinerary"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
    </>
  );
}
