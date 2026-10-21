import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { api, Proposal, Trip } from "@/lib/livetrip";
import { useToast } from "@/hooks/use-toast";

interface Props {
  tripId: string | number;
  proposal: Proposal | null;
  title?: string;
  onClose: () => void;
  onApplied: (trip: Trip) => void;
}

/** Shows what a reschedule would change; nothing is saved until the traveler confirms. */
export default function ProposalDialog({ tripId, proposal, title = "Review changes", onClose, onApplied }: Props) {
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  const apply = async () => {
    if (!proposal) return;
    setSaving(true);
    try {
      const trip = await api<Trip>(`/api/itinerary/${tripId}/apply`, {
        method: "POST",
        json: { ops: proposal.ops, expected_version: proposal.version },
      });
      toast({ title: "Itinerary updated" });
      onApplied(trip);
      onClose();
    } catch (e) {
      toast({ title: "Could not apply", description: (e as Error).message, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const changed = proposal?.preview?.days.flatMap((d) =>
    d.time_slots.filter((s) => s.kind === "visit").map((s) => ({ day: d.day, ...s })),
  ) ?? [];

  return (
    <Dialog open={!!proposal} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>Completed and confirmed stops stay as they are.</DialogDescription>
        </DialogHeader>
        {proposal && proposal.ops.length > 0 ? (
          <div className="space-y-3">
            <ul className="list-disc pl-5 text-sm space-y-1">
              {proposal.notes.map((n, i) => <li key={i}>{n}</li>)}
            </ul>
            {changed.length > 0 && (
              <div className="max-h-56 overflow-y-auto rounded-md border p-2 text-xs space-y-1">
                <p className="font-medium text-muted-foreground">New schedule</p>
                {changed.map((s) => (
                  <div key={`${s.day}-${s.item_id}`} className={`flex justify-between ${s.status === "skipped" ? "line-through text-muted-foreground" : ""}`}>
                    <span>Day {s.day} · {s.start_time} {s.activity.name}</span>
                    {s.overflow && <span className="text-red-600">runs late</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{proposal?.notes?.[0] ?? "Nothing needs to change."}</p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Keep current plan</Button>
          {proposal && proposal.ops.length > 0 && (
            <Button onClick={apply} disabled={saving}>{saving ? "Applying..." : "Apply changes"}</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
