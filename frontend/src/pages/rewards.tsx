import { useEffect, useState } from "react";
import { Award, Flame, Gift, Medal, RefreshCw, Trophy } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/livetrip";

interface Dashboard {
  total_earned: number;
  balance: number;
  streak: number;
  badges: { code: string; title: string; description: string; earned: boolean }[];
  challenges_today: { code: string; title: string; goal: number; progress: number; completed: boolean; points: number }[];
  completed_challenges: { title: string; points: number; date: string }[];
  upcoming_challenges: { date: string; codes: string[] }[];
  redemptions: { code: string; offer: string; business: string; cost: number; date: string }[];
  recent_activity: { kind: string; points: number; date: string }[];
  point_rules: Record<string, number>;
}
interface Offer { id: number; business_name: string; title: string; description: string; cost_points: number; remaining: number; expires_on: string }
interface Board { entries: { rank: number; name: string; username: string; points: number; is_me: boolean }[]; me_on_leaderboard: boolean }

const KIND_LABEL: Record<string, string> = {
  visit_complete: "Visited a planned stop", new_attraction: "New attraction", daily_challenge: "Daily challenge",
  photo_upload: "Shared a photo", destination_challenge: "Destination challenge", trip_complete: "Finished a trip",
  distance_bonus: "Distance bonus", redemption: "Redeemed an offer",
};

export default function Rewards() {
  const { toast } = useToast();
  const { user, refresh } = useAuth();
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [board, setBoard] = useState<Board | null>(null);
  const [scope, setScope] = useState("global");
  const [city, setCity] = useState("");

  const load = () => {
    api<Dashboard>("/api/points/dashboard").then(setDash);
    api<Offer[]>("/api/offers").then(setOffers);
  };
  const loadBoard = () => {
    const q = scope === "city" ? `?scope=city&city=${encodeURIComponent(city)}` : "";
    if (scope === "city" && !city) return;
    api<Board>(`/api/points/leaderboard${q}`).then(setBoard).catch(() => setBoard(null));
  };
  useEffect(load, []);
  useEffect(loadBoard, [scope]);

  const redeem = async (o: Offer) => {
    try {
      const r = await api<{ code: string; balance: number }>(`/api/offers/${o.id}/redeem`, { method: "POST" });
      toast({ title: `Your code: ${r.code}`, description: `Show it at ${o.business_name}. Balance: ${r.balance} points.` });
      load();
    } catch (e) {
      toast({ title: "Could not redeem", description: (e as Error).message, variant: "destructive" });
    }
  };

  const toggleBoard = async (on: boolean) => {
    await api("/api/users/me", { method: "PATCH", json: { onLeaderboard: on } });
    await refresh();
    loadBoard();
  };

  if (!dash) return <div className="flex justify-center p-16"><RefreshCw className="w-8 h-8 animate-spin text-primary" /></div>;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <h1 className="text-3xl font-bold">Rewards & progress</h1>
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat icon={Trophy} label="Points earned" value={dash.total_earned} />
        <Stat icon={Gift} label="Available to spend" value={dash.balance} />
        <Stat icon={Flame} label="Day streak" value={dash.streak} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Today's challenges</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {dash.challenges_today.map((c) => (
              <div key={c.code} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>{c.title}</span>
                  {c.completed ? <Badge className="bg-green-600">+{c.points} done</Badge> : <span className="text-muted-foreground">{c.progress}/{c.goal} · {c.points} pts</span>}
                </div>
                <Progress value={(c.progress / c.goal) * 100} />
              </div>
            ))}
            <div className="text-xs text-muted-foreground">
              Coming up: {dash.upcoming_challenges.map((u) => `${u.date}: ${u.codes.join(", ")}`).join(" · ")}
            </div>
            <p className="text-xs text-muted-foreground">Challenges are optional. Visits count when you check in within 500 m of the place.</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Badges</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            {dash.badges.map((b) => (
              <div key={b.code} className={`rounded-lg border p-3 ${b.earned ? "border-primary bg-primary/5" : "opacity-60"}`}>
                <p className="font-medium flex items-center gap-1"><Medal className={`w-4 h-4 ${b.earned ? "text-primary" : ""}`} />{b.title}</p>
                <p className="text-xs text-muted-foreground">{b.description}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Redeem points</CardTitle></CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {offers.map((o) => (
            <div key={o.id} className="rounded-lg border p-3 flex flex-col justify-between gap-2">
              <div>
                <p className="font-medium">{o.title}</p>
                <p className="text-xs text-muted-foreground">{o.business_name}</p>
                <p className="text-xs mt-1">{o.description}</p>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">{o.cost_points} pts</span>
                <Button size="sm" onClick={() => redeem(o)} disabled={dash.balance < o.cost_points || o.remaining === 0}>Redeem</Button>
              </div>
            </div>
          ))}
          {offers.length === 0 && <p className="text-sm text-muted-foreground">No offers right now.</p>}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Leaderboard
              <label className="flex items-center gap-2 text-sm font-normal">
                Show me <Switch checked={user?.settings?.onLeaderboard ?? board?.me_on_leaderboard ?? true} onCheckedChange={toggleBoard} />
              </label>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs value={scope} onValueChange={setScope}>
              <TabsList><TabsTrigger value="global">Everyone</TabsTrigger><TabsTrigger value="city">By destination</TabsTrigger></TabsList>
              <TabsContent value="city" className="flex gap-2 pt-2">
                <Input placeholder="City" value={city} onChange={(e) => setCity(e.target.value)} />
                <Button variant="outline" onClick={loadBoard}>Show</Button>
              </TabsContent>
            </Tabs>
            <ol className="mt-3 space-y-1">
              {board?.entries.map((e) => (
                <li key={e.rank} className={`flex justify-between text-sm rounded px-2 py-1 ${e.is_me ? "bg-primary/10 font-medium" : ""}`}>
                  <span>{e.rank}. {e.name} <span className="text-muted-foreground">@{e.username}</span></span>
                  <span>{e.points} pts</span>
                </li>
              ))}
              {board?.entries.length === 0 && <li className="text-sm text-muted-foreground">No one here yet.</li>}
            </ol>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>History</CardTitle></CardHeader>
          <CardContent className="space-y-1 text-sm max-h-80 overflow-y-auto">
            {dash.recent_activity.map((e, i) => (
              <div key={i} className="flex justify-between">
                <span>{KIND_LABEL[e.kind] ?? e.kind} <span className="text-xs text-muted-foreground">{new Date(e.date).toLocaleDateString()}</span></span>
                <span className={e.points < 0 ? "text-red-600" : "text-green-700"}>{e.points > 0 ? "+" : ""}{e.points}</span>
              </div>
            ))}
            {dash.redemptions.length > 0 && <p className="font-medium pt-2">Your codes</p>}
            {dash.redemptions.map((r) => (
              <div key={r.code} className="flex justify-between"><span>{r.offer} · {r.business}</span><code>{r.code}</code></div>
            ))}
            {dash.recent_activity.length === 0 && <p className="text-muted-foreground">Check in at a planned stop to earn your first points.</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value }: { icon: typeof Award; label: string; value: number }) {
  return (
    <Card>
      <CardContent className="pt-6 flex items-center gap-3">
        <Icon className="w-8 h-8 text-primary" />
        <div><p className="text-2xl font-bold">{value}</p><p className="text-sm text-muted-foreground">{label}</p></div>
      </CardContent>
    </Card>
  );
}
