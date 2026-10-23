import { ReactNode, useEffect, useState } from "react";
import { Clock, ExternalLink, GripVertical, ImageOff, MapPin, Navigation, Star, Utensils } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from "@/components/ui/carousel";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { api, Slot } from "@/lib/livetrip";

export interface PlaceInfo {
  article: string | null;
  description: string | null;
  url: string | null;
  photos: { url: string; author: string; license: string; source_url: string }[];
}

const infoCache = new Map<string, Promise<PlaceInfo>>();

/** Description and photos for a stop (Wikipedia / Wikimedia Commons), fetched once per page load. */
function usePlaceInfo(slot: Slot, city: string): PlaceInfo | null | undefined {
  const name = slot.activity.name.replace(/^(Lunch|Dinner) at /, "");
  const skip = /^(Lunch|Dinner) break$/.test(slot.activity.name);
  const { latitude: lat, longitude: lng } = slot.activity.location;
  const [info, setInfo] = useState<PlaceInfo | null | undefined>(skip ? null : undefined);
  useEffect(() => {
    if (skip) return;
    const key = `${name}|${lat?.toFixed(3)}|${lng?.toFixed(3)}`;
    if (!infoCache.has(key)) {
      const q = new URLSearchParams({ name, city, ...(lat != null ? { lat: String(lat), lng: String(lng) } : {}) });
      infoCache.set(key, api<PlaceInfo>(`/api/places/info?${q}`).catch(() => ({ article: null, description: null, url: null, photos: [] })));
    }
    let alive = true;
    infoCache.get(key)!.then((r) => alive && setInfo(r));
    return () => { alive = false; };
  }, [name, lat, lng]);
  return info;
}

function Photos({ info, name, large = false }: { info: PlaceInfo | null | undefined; name: string; large?: boolean }) {
  const height = large ? "h-72" : "h-40 sm:h-full";
  if (info === undefined) return <Skeleton className={`w-full ${height} rounded-md`} />;
  if (!info?.photos.length) {
    return (
      <div className={`w-full ${height} rounded-md bg-muted flex flex-col items-center justify-center text-muted-foreground text-xs gap-1`}>
        <ImageOff className="w-6 h-6" />No photo yet
      </div>
    );
  }
  return (
    <Carousel opts={{ loop: info.photos.length > 1 }} className="w-full">
      <CarouselContent>
        {info.photos.map((p, i) => (
          <CarouselItem key={p.url}>
            <figure>
              <img src={p.url} alt={`${name} (photo ${i + 1} of ${info.photos.length})`} loading="lazy"
                   className={`w-full ${large ? "h-72" : "h-40"} object-cover rounded-md`} />
              {large && (
                <figcaption className="text-[11px] text-muted-foreground mt-1">
                  Photo: {p.author} · {p.license} · <a className="underline" href={p.source_url} target="_blank" rel="noreferrer">source</a>
                </figcaption>
              )}
            </figure>
          </CarouselItem>
        ))}
      </CarouselContent>
      {info.photos.length > 1 && (
        <>
          <CarouselPrevious className="left-1 h-7 w-7 bg-background/80" />
          <CarouselNext className="right-1 h-7 w-7 bg-background/80" />
        </>
      )}
    </Carousel>
  );
}

/** Splits off the first sentence, not fooled by initials or abbreviations ("officially T. Anjaiah", "St. Mary's"). */
export function firstSentence(text: string): [string, string] {
  const end = /[.!?](\s|$)/g;
  for (let m; (m = end.exec(text)); ) {
    const word = text.slice(0, m.index).split(/\s/).pop() || "";
    if (word.length > 1 && !word.includes(".") && !/^(St|Dr|Mr|Mrs|Ms|Jr|Sr|No|Mt|Ft|Rs|Smt)$/.test(word)) {
      return [text.slice(0, m.index + 1), text.slice(m.index + 1).trim()];
    }
  }
  return [text, ""];
}

interface Props {
  slot: Slot;
  number?: number;
  city: string;
  selected: boolean;
  onSelect: () => void;
  actions: ReactNode;
  dragProps?: React.HTMLAttributes<HTMLDivElement> & { draggable?: boolean };
  moveControls?: ReactNode;
}

export default function PlaceCard({ slot, number, city, selected, onSelect, actions, dragProps, moveControls }: Props) {
  const info = usePlaceInfo(slot, city);
  const [open, setOpen] = useState(false);
  const a = slot.activity;
  const loc = a.location;
  const directions = loc.latitude != null
    ? `https://www.google.com/maps/dir/?api=1&destination=${loc.latitude},${loc.longitude}` : null;
  const [lead, rest] = info?.description ? firstSentence(info.description) : ["", ""];

  return (
    <Card
      id={`stop-${slot.item_id}`}
      onClick={onSelect}
      {...dragProps}
      className={`transition-shadow ${selected ? "ring-2 ring-primary shadow-lg" : "hover:shadow-md"} ${slot.status === "skipped" ? "opacity-50" : ""}`}
    >
      <CardContent className="p-3 sm:p-4 flex flex-col sm:flex-row gap-4">
        <div className="sm:w-48 shrink-0" onClick={(e) => e.stopPropagation()}>
          {slot.kind === "meal" && info !== undefined && !info?.photos.length
            ? <div className="h-40 sm:h-full rounded-md bg-orange-50 dark:bg-orange-950/30 flex items-center justify-center"><Utensils className="w-8 h-8 text-orange-500" /></div>
            : <Photos info={info} name={a.name} />}
        </div>
        <div className="flex-1 min-w-0 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className={`font-semibold text-lg leading-tight ${slot.status === "skipped" ? "line-through" : ""}`}>
                {number !== undefined && <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-teal-700 text-white text-xs mr-2 align-middle">{number}</span>}
                {slot.kind === "meal" && <Utensils className="w-4 h-4 inline mr-1 -mt-1 text-orange-500" />}
                <span translate="no">{a.name}</span>
              </p>
              <p className="text-xs text-muted-foreground flex flex-wrap items-center gap-2 mt-1">
                {a.rating > 0 && (
                  <span className="flex items-center text-foreground">
                    <Star className="w-3 h-3 mr-0.5 fill-yellow-400 text-yellow-400" />{a.rating}
                    {a.rating_count > 0 && <span className="text-muted-foreground ml-1">({a.rating_count.toLocaleString()})</span>}
                  </span>
                )}
                <span className="capitalize">{a.activity_type}</span>
                {a.weather_dependent && <span>· outdoor</span>}
                {slot.status === "completed" && <Badge className="bg-green-600">visited</Badge>}
                {slot.status === "skipped" && <Badge variant="secondary">skipped</Badge>}
                {slot.locked && <Badge variant="outline">confirmed</Badge>}
                {slot.overflow && <Badge variant="destructive">runs late</Badge>}
              </p>
            </div>
            <div className="flex items-center gap-1 shrink-0 text-muted-foreground">
              {moveControls}
              {dragProps?.draggable && <GripVertical className="w-4 h-4 cursor-grab" aria-label="Drag to reorder" />}
            </div>
          </div>
          <p className="text-sm text-muted-foreground flex flex-wrap items-center gap-3">
            <span className="flex items-center font-medium text-foreground"><Clock className="w-3 h-3 mr-1" />{slot.start_time}–{slot.end_time}</span>
            {slot.travel_min > 0 && <span>{slot.travel_min} min travel</span>}
          </p>
          {info === undefined && slot.kind === "visit" && <Skeleton className="h-10 w-full" />}
          {info?.description && (
            <p className="text-sm line-clamp-3">
              <mark className="bg-green-100 dark:bg-green-900/40 text-foreground rounded px-0.5">{lead}</mark> {rest}
            </p>
          )}
          {info && !info.description && slot.kind === "visit" && (
            <p className="text-sm text-muted-foreground">{a.description || "No description available yet."}</p>
          )}
          <div className="flex flex-wrap items-center gap-1 pt-1" onClick={(e) => e.stopPropagation()}>
            {actions}
            {slot.kind === "visit" && (
              <Button size="sm" variant="outline" className="ml-auto" onClick={() => setOpen(true)}>See details</Button>
            )}
          </div>
        </div>
      </CardContent>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
          <DialogHeader>
            <DialogTitle translate="no">{a.name}</DialogTitle>
            <DialogDescription className="flex flex-wrap gap-2 items-center">
              <span className="capitalize">{a.activity_type}</span>
              {a.rating > 0 && <span className="flex items-center"><Star className="w-3 h-3 mr-0.5 fill-yellow-400 text-yellow-400" />{a.rating} ({a.rating_count.toLocaleString()})</span>}
              <span>· {slot.start_time}–{slot.end_time}</span>
            </DialogDescription>
          </DialogHeader>
          <Photos info={info} name={a.name} large />
          <p className="text-sm leading-relaxed">{info?.description || a.description || "No description available yet."}</p>
          {a.location.address && <p className="text-sm text-muted-foreground flex gap-1"><MapPin className="w-4 h-4 shrink-0" />{a.location.address}</p>}
          <div className="flex flex-wrap gap-2">
            {directions && (
              <Button asChild size="sm"><a href={directions} target="_blank" rel="noreferrer"><Navigation className="w-4 h-4 mr-1" />Directions</a></Button>
            )}
            {info?.url && (
              <Button asChild size="sm" variant="outline"><a href={info.url} target="_blank" rel="noreferrer"><ExternalLink className="w-4 h-4 mr-1" />Read more on Wikipedia</a></Button>
            )}
          </div>
          {info?.description && <p className="text-[11px] text-muted-foreground">Description from Wikipedia (CC BY-SA). Photos from Wikimedia Commons.</p>}
        </DialogContent>
      </Dialog>
    </Card>
  );
}
