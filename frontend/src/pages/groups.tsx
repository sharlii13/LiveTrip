import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Copy, RefreshCw, ThumbsDown, ThumbsUp, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/AuthContext";
import { api, Photo, Trip } from "@/lib/livetrip";
import PageHero from "@/components/PageHero";

interface GroupRow { id: number; name: string; role: string; trip: string | null; members: number }
interface GroupDetail {
  id: number; name: string; invite_code: string | null; my_role: string;
  members: { user_id: number; name: string; role: string; points: number | null }[];
  trip: Trip | null;
  suggestions: { id: number; name: string; category: string; status: string; suggested_by: string; score: number; up: number; down: number; my_vote: number }[];
  photos: Photo[];
  group_challenge: { title: string; progress: number; goal: number; completed: boolean } | null;
}
interface TripSummary { id: number; destination: string; owned: boolean }

export function GroupsList() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [groups, setGroups] = useState<GroupRow[] | null>(null);
  const [trips, setTrips] = useState<TripSummary[]>([]);
  const [name, setName] = useState("");
  const [tripId, setTripId] = useState("none");
  const [code, setCode] = useState("");

  useEffect(() => {
    api<GroupRow[]>("/api/groups").then(setGroups).catch(() => setGroups([]));
    api<TripSummary[]>("/api/trips").then((t) => setTrips(t.filter((x) => x.owned))).catch(() => {});
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const g = await api<{ id: number }>("/api/groups", { method: "POST", json: { name, trip_id: tripId === "none" ? null : Number(tripId) } });
      navigate(`/groups/${g.id}`);
    } catch (err) { toast({ title: "Could not create group", description: (err as Error).message, variant: "destructive" }); }
  };

  const join = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const g = await api<{ id: number }>("/api/groups/join", { method: "POST", json: { invite_code: code } });
      navigate(`/groups/${g.id}`);
    } catch (err) { toast({ title: "Could not join", description: (err as Error).message, variant: "destructive" }); }
  };

  return (
    <>
    <PageHero title="Trip groups" clip="stays" icon={<Users className="w-6 h-6" />} subtitle="Plan together: suggest places, vote, share photos and take on group challenges." />
    <div className="max-w-5xl mx-auto px-4 py-8 grid gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2 space-y-3">
        {groups === null && <RefreshCw className="w-6 h-6 animate-spin text-primary" />}
        {groups?.length === 0 && <p className="text-muted-foreground">You are not in any group yet.</p>}
        {groups?.map((g) => (
          <Link key={g.id} to={`/groups/${g.id}`}>
            <Card className="hover:shadow-md transition-shadow mb-3">
              <CardContent className="py-4 flex justify-between items-center">
                <div>
                  <p className="font-semibold flex items-center gap-2"><Users className="w-4 h-4" />{g.name}</p>
                  <p className="text-sm text-muted-foreground">{g.trip ? `Trip to ${g.trip}` : "No trip linked"} · {g.members} member{g.members > 1 ? "s" : ""}</p>
                </div>
                <Badge variant="secondary" className="capitalize">{g.role}</Badge>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
      <div className="space-y-4">
        <Card>
          <CardHeader><CardTitle className="text-lg">New group</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={create} className="space-y-2">
              <Input placeholder="Group name" value={name} onChange={(e) => setName(e.target.value)} required minLength={2} />
              <Select value={tripId} onValueChange={setTripId}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Link a trip later</SelectItem>
                  {trips.map((t) => <SelectItem key={t.id} value={String(t.id)}>{t.destination}</SelectItem>)}
                </SelectContent>
              </Select>
              <Button type="submit" className="w-full">Create</Button>
            </form>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-lg">Join with a code</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={join} className="flex gap-2">
              <Input placeholder="Invite code" value={code} onChange={(e) => setCode(e.target.value)} required />
              <Button type="submit">Join</Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
    </>
  );
}

export function GroupDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { toast } = useToast();
  const [g, setG] = useState<GroupDetail | null>(null);
  const [suggestion, setSuggestion] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<GroupDetail>(`/api/groups/${id}`).then(setG).catch((e) => setError(e.message));
  }, [id]);

  const act = async (path: string, json?: unknown, method = "POST") => {
    try {
      setG(await api<GroupDetail>(path, { method, json }));
    } catch (e) {
      toast({ title: "That did not work", description: (e as Error).message, variant: "destructive" });
    }
  };

  if (error) return <p className="p-8 text-center">{error}</p>;
  if (!g) return <div className="flex justify-center p-16"><RefreshCw className="w-8 h-8 animate-spin text-primary" /></div>;
  const canEdit = g.my_role === "owner" || g.my_role === "editor";

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 grid gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2 space-y-4">
        <div className="flex flex-wrap justify-between items-start gap-2">
          <div>
            <h1 className="text-3xl font-bold">{g.name}</h1>
            {g.trip && <Link className="text-primary underline" to={`/trips/${g.trip.id}`}>Open the {g.trip.destination} itinerary</Link>}
          </div>
          {g.invite_code && (
            <Button variant="outline" onClick={() => { navigator.clipboard?.writeText(g.invite_code!); toast({ title: "Invite code copied" }); }}>
              <Copy className="w-4 h-4 mr-1" />Invite code: {g.invite_code}
            </Button>
          )}
        </div>

        {g.group_challenge && (
          <Card>
            <CardContent className="pt-4 space-y-2">
              <p className="text-sm font-medium">{g.group_challenge.title}</p>
              <Progress value={Math.min(100, (g.group_challenge.progress / g.group_challenge.goal) * 100)} />
              <p className="text-xs text-muted-foreground">{g.group_challenge.progress} / {g.group_challenge.goal} points{g.group_challenge.completed && " · completed!"}</p>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader><CardTitle className="text-lg">Suggestions and votes</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); act(`/api/groups/${id}/suggestions`, { name: suggestion }); setSuggestion(""); }}>
              <Input placeholder="Suggest a place" value={suggestion} onChange={(e) => setSuggestion(e.target.value)} required minLength={2} />
              <Button type="submit">Suggest</Button>
            </form>
            {g.suggestions.length === 0 && <p className="text-sm text-muted-foreground">No suggestions yet.</p>}
            {g.suggestions.map((s) => (
              <div key={s.id} className="flex flex-wrap items-center justify-between gap-2 border-b pb-2">
                <div>
                  <p className="font-medium">{s.name} {s.status !== "open" && <Badge className="ml-1 capitalize">{s.status}</Badge>}</p>
                  <p className="text-xs text-muted-foreground">by {s.suggested_by} · score {s.score}</p>
                </div>
                <div className="flex items-center gap-1">
                  <Button size="sm" variant={s.my_vote === 1 ? "default" : "outline"} aria-label="Vote up"
                          onClick={() => act(`/api/groups/${id}/suggestions/${s.id}/vote`, { value: s.my_vote === 1 ? 0 : 1 })}>
                    <ThumbsUp className="w-4 h-4 mr-1" />{s.up}
                  </Button>
                  <Button size="sm" variant={s.my_vote === -1 ? "default" : "outline"} aria-label="Vote down"
                          onClick={() => act(`/api/groups/${id}/suggestions/${s.id}/vote`, { value: s.my_vote === -1 ? 0 : -1 })}>
                    <ThumbsDown className="w-4 h-4 mr-1" />{s.down}
                  </Button>
                  {canEdit && s.status === "open" && g.trip && (
                    <Button size="sm" onClick={() => act(`/api/groups/${id}/suggestions/${s.id}/accept`)}>Add to trip</Button>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {g.photos.length > 0 && (
          <Card>
            <CardHeader><CardTitle className="text-lg">Group photos</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {g.photos.map((p) => <img key={p.id} src={p.url} alt={p.caption || p.place_name || "Group photo"} className="h-32 w-full object-cover rounded" />)}
            </CardContent>
          </Card>
        )}
      </div>

      <Card className="h-fit">
        <CardHeader><CardTitle className="text-lg">Members</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {g.members.map((m) => (
            <div key={m.user_id} className="flex items-center justify-between gap-2 text-sm">
              <span>{m.name}{m.points !== null && <span className="text-muted-foreground"> · {m.points} pts</span>}</span>
              {g.my_role === "owner" && m.role !== "owner" ? (
                <Select value={m.role} onValueChange={(role) => act(`/api/groups/${id}/members/${m.user_id}`, { role }, "PATCH")}>
                  <SelectTrigger className="w-28 h-8"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="editor">Can edit</SelectItem><SelectItem value="viewer">View only</SelectItem></SelectContent>
                </Select>
              ) : <Badge variant="secondary" className="capitalize">{m.role}</Badge>}
            </div>
          ))}
          {g.my_role !== "owner" && (
            <Button variant="ghost" className="text-red-600 w-full" onClick={async () => {
              await api(`/api/groups/${id}/members/${user?.id}`, { method: "DELETE" });
              window.location.href = "/groups";
            }}>Leave group</Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
