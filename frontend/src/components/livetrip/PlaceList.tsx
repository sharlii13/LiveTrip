import { Star, MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Place } from "@/lib/livetrip";

interface Props {
  places: Place[];
  actionLabel?: string;
  onAction?: (p: Place) => void;
  secondaryLabel?: string;
  onSecondary?: (p: Place) => void;
  empty?: string;
}

export default function PlaceList({ places, actionLabel, onAction, secondaryLabel, onSecondary, empty = "No places found." }: Props) {
  if (!places.length) return <p className="text-sm text-muted-foreground">{empty}</p>;
  return (
    <ul className="divide-y">
      {places.map((p) => (
        <li key={p.place_id || p.name} className="py-2 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-medium truncate">{p.name}</p>
            <p className="text-xs text-muted-foreground flex flex-wrap items-center gap-2">
              <span className="capitalize">{p.category}</span>
              {p.rating > 0 && <span className="flex items-center"><Star className="w-3 h-3 mr-0.5 fill-yellow-400 text-yellow-400" />{p.rating} ({p.rating_count})</span>}
              {p.distance_km !== undefined && <span className="flex items-center"><MapPin className="w-3 h-3 mr-0.5" />{p.distance_km} km</span>}
              {p.travel_min !== undefined && <span>~{p.travel_min} min away</span>}
            </p>
            {p.address && <p className="text-xs text-muted-foreground truncate">{p.address}</p>}
          </div>
          <div className="flex gap-1 shrink-0">
            {onSecondary && <Button size="sm" variant="ghost" onClick={() => onSecondary(p)}>{secondaryLabel}</Button>}
            {onAction && <Button size="sm" variant="outline" onClick={() => onAction(p)}>{actionLabel}</Button>}
          </div>
        </li>
      ))}
    </ul>
  );
}
