import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/livetrip";
import AssistantPanel from "@/components/livetrip/AssistantPanel";
import PageHero from "@/components/PageHero";

interface TripSummary { id: number; destination: string; start_date: string }

export default function Assistant() {
  const { isAuthenticated } = useAuth();
  const [trips, setTrips] = useState<TripSummary[]>([]);
  const [tripId, setTripId] = useState<string>("none");

  useEffect(() => {
    if (isAuthenticated) {
      api<TripSummary[]>("/api/trips").then((t) => {
        setTrips(t);
        if (t.length) setTripId(String(t[0].id));
      }).catch(() => {});
    }
  }, [isAuthenticated]);

  return (
    <>
    <PageHero title="Travel buddy" clip="plan" subtitle="Ask anything about your trip, or about where to go next." />
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <CardTitle>Travel assistant</CardTitle>
          {trips.length > 0 && (
            <Select value={tripId} onValueChange={setTripId}>
              <SelectTrigger className="w-56"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No trip</SelectItem>
                {trips.map((t) => <SelectItem key={t.id} value={String(t.id)}>{t.destination} · {t.start_date}</SelectItem>)}
              </SelectContent>
            </Select>
          )}
        </CardHeader>
        <CardContent>
          <AssistantPanel key={tripId} tripId={tripId === "none" ? null : tripId} />
        </CardContent>
      </Card>
    </div>
    </>
  );
}
