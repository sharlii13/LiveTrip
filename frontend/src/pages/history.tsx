import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Camera, MapPin, Medal, RefreshCw, Trophy } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/livetrip";

interface History {
  trips: { id: number; destination: string; start_date: string; end_date: string; status: string; days: number;
           visited: { name: string; category: string }[]; photos: number; points: number }[];
  badges: { code: string; title: string }[];
  challenges_completed: number;
  total_points: number;
}

export default function TravelHistory() {
  const { user, refresh } = useAuth();
  const [data, setData] = useState<History | null>(null);

  useEffect(() => { api<History>("/api/history").then(setData); }, []);

  const setPublic = async (on: boolean) => {
    await api("/api/users/me", { method: "PATCH", json: { historyPublic: on } });
    refresh();
  };

  if (!data) return <div className="flex justify-center p-16"><RefreshCw className="w-8 h-8 animate-spin text-primary" /></div>;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold">Travel history</h1>
          <p className="text-muted-foreground">{data.trips.length} trips · {data.total_points} points · {data.challenges_completed} challenges completed</p>
        </div>
        <label className="flex items-center gap-2 text-sm">
          Show my history on my public profile
          <Switch checked={user?.settings?.historyPublic ?? false} onCheckedChange={setPublic} />
        </label>
      </div>
      {data.badges.length > 0 && (
        <div className="flex flex-wrap gap-2">{data.badges.map((b) => <Badge key={b.code}><Medal className="w-3 h-3 mr-1" />{b.title}</Badge>)}</div>
      )}
      {data.trips.length === 0 && <p className="text-muted-foreground">No trips yet. <Link to="/trips" className="text-primary underline">Plan one</Link>.</p>}
      {data.trips.map((t) => (
        <Card key={t.id}>
          <CardHeader className="pb-2">
            <CardTitle className="flex flex-wrap justify-between gap-2 text-xl">
              <Link to={`/trips/${t.id}`} className="hover:underline">{t.destination}</Link>
              <span className="text-sm font-normal text-muted-foreground">{t.start_date} → {t.end_date} · <Badge variant="secondary" className="capitalize">{t.status}</Badge></span>
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-2">
            <p className="flex flex-wrap gap-4 text-muted-foreground">
              <span><MapPin className="w-3 h-3 inline mr-1" />{t.visited.length} places visited</span>
              <span><Camera className="w-3 h-3 inline mr-1" />{t.photos} photos</span>
              <span><Trophy className="w-3 h-3 inline mr-1" />{t.points} points</span>
            </p>
            {t.visited.length > 0 && <p>{t.visited.map((v) => v.name).join(" · ")}</p>}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
