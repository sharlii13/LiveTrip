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
import { api, localDate, Trip } from "@/lib/livetrip";

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

const INTERESTS = ["culture", "history", "nature", "adventure", "food", "nightlife", "shopping", "relaxation"];
const today = () => localDate();

export default function Trips() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { toast } = useToast();
  const [trips, setTrips] = useState<TripSummary[] | null>(null);
  const [destination, setDestination] = useState("");
  const [start, setStart] = useState(today());
  const [end, setEnd] = useState(today());
  const [interests, setInterests] = useState<string[]>(["culture"]);
  const [food, setFood] = useState("both");
  const [pace, setPace] = useState("normal");
  const [transport, setTransport] = useState("car");
  const [travelers, setTravelers] = useState("2");
  const [mustVisit, setMustVisit] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (isAuthenticated) api<TripSummary[]>("/api/trips").then(setTrips).catch(() => setTrips([]));
    else setTrips([]);
  }, [isAuthenticated]);

  const toggle = (i: string) => setInterests((list) => (list.includes(i) ? list.filter((x) => x !== i) : [...list, i]));

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const trip = await api<Trip>("/api/trips", {
        method: "POST",
        json: {
          destination, startDate: start, endDate: end, interests, foodPreference: food, pace,
          transportPreference: transport, travelers: Number(travelers) || 1,
          mustVisit: mustVisit.split(",").map((s) => s.trim()).filter(Boolean),
        },
      });
      navigate(`/trips/${trip.id}`);
    } catch (err) {
      toast({ title: "Could not plan this trip", description: (err as Error).message, variant: "destructive" });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 grid gap-6 lg:grid-cols-5">
      <div className="lg:col-span-3 space-y-4">
        <h1 className="text-3xl font-bold">My trips</h1>
        {!isAuthenticated && (
          <Card><CardContent className="pt-6 text-sm">
            <Link to="/login?next=/trips" className="text-primary underline">Sign in</Link> to keep your trips, check in at places and earn points. You can still plan a trip without an account.
          </CardContent></Card>
        )}
        {trips === null && <RefreshCw className="w-6 h-6 animate-spin text-primary" />}
        {trips?.length === 0 && isAuthenticated && <p className="text-muted-foreground">No trips yet. Plan your first one.</p>}
        {trips?.map((t) => (
          <Link key={t.id} to={`/trips/${t.id}`}>
            <Card className="hover:shadow-md transition-shadow mb-3">
              <CardContent className="py-4 flex items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-lg flex items-center gap-2"><MapPin className="w-4 h-4" />{t.destination}</p>
                  <p className="text-sm text-muted-foreground flex items-center gap-1"><CalendarDays className="w-3 h-3" />{t.start_date} → {t.end_date}</p>
                </div>
                <div className="text-right text-sm">
                  <Badge variant={t.status === "completed" ? "default" : "secondary"} className="capitalize">{t.status}</Badge>
                  <p className="text-muted-foreground mt-1">{t.completed}/{t.visits} visited{t.owned ? "" : " · shared"}</p>
                </div>
              </CardContent>
            </Card>
          </Link>
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
            <div className="space-y-1">
              <Label>Interests</Label>
              <div className="flex flex-wrap gap-1">
                {INTERESTS.map((i) => (
                  <button type="button" key={i} onClick={() => toggle(i)} aria-pressed={interests.includes(i)}
                          className={`text-xs capitalize rounded-full border px-2 py-1 ${interests.includes(i) ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}>
                    {i}
                  </button>
                ))}
              </div>
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
              <div className="space-y-1">
                <Label>Pace</Label>
                <Select value={pace} onValueChange={setPace}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="relaxed">Relaxed</SelectItem>
                    <SelectItem value="normal">Normal</SelectItem>
                    <SelectItem value="fast">Packed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>Getting around</Label>
                <Select value={transport} onValueChange={setTransport}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="car">Car / taxi</SelectItem>
                    <SelectItem value="public-transport">Public transport</SelectItem>
                    <SelectItem value="walking">Walking</SelectItem>
                    <SelectItem value="bicycle">Bicycle</SelectItem>
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
  );
}
