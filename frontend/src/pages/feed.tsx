import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Bookmark, Camera, Heart, MapPin, MessageCircle, Plus, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/AuthContext";
import { api, currentPosition, describeAwards, Award, Photo, Proposal, Trip } from "@/lib/livetrip";
import ProposalDialog from "@/components/livetrip/ProposalDialog";
import PageHero from "@/components/PageHero";

interface TripSummary { id: number; destination: string; start_date: string }

export default function Feed() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { toast } = useToast();
  const [photos, setPhotos] = useState<Photo[] | null>(null);
  const [city, setCity] = useState(params.get("city") ?? "");
  const [hashtag, setHashtag] = useState("");
  const [uploadOpen, setUploadOpen] = useState(!!params.get("trip"));
  const [open, setOpen] = useState<Photo | null>(null);
  const [comment, setComment] = useState("");
  const [trips, setTrips] = useState<TripSummary[]>([]);
  const [addTarget, setAddTarget] = useState<Photo | null>(null);
  const [addTrip, setAddTrip] = useState("");
  const [proposal, setProposal] = useState<{ tripId: string; p: Proposal } | null>(null);

  const load = () => {
    const q = new URLSearchParams();
    if (city) q.set("city", city);
    if (hashtag) q.set("hashtag", hashtag);
    api<{ photos: Photo[] }>(`/api/photos/feed?${q}`).then((r) => setPhotos(r.photos)).catch(() => setPhotos([]));
  };

  useEffect(load, []);
  useEffect(() => {
    if (isAuthenticated) api<TripSummary[]>("/api/trips").then(setTrips).catch(() => {});
  }, [isAuthenticated]);

  const requireLogin = () => {
    if (!isAuthenticated) {
      navigate(`/login?next=/feed`);
      return true;
    }
    return false;
  };

  const update = (p: Photo) => {
    setPhotos((list) => list?.map((x) => (x.id === p.id ? { ...x, ...p } : x)) ?? null);
    if (open?.id === p.id) setOpen((o) => (o ? { ...o, ...p } : o));
  };

  const like = async (p: Photo) => { if (!requireLogin()) update(await api<Photo>(`/api/photos/${p.id}/like`, { method: "POST" })); };
  const save = async (p: Photo) => { if (!requireLogin()) update(await api<Photo>(`/api/photos/${p.id}/save`, { method: "POST" })); };

  const openPhoto = async (p: Photo) => setOpen(await api<Photo>(`/api/photos/${p.id}`));

  const sendComment = async (e: FormEvent) => {
    e.preventDefault();
    if (!open || requireLogin() || !comment.trim()) return;
    const updated = await api<Photo>(`/api/photos/${open.id}/comments`, { method: "POST", json: { text: comment } });
    setOpen(updated);
    update(updated);
    setComment("");
  };

  const savePlace = async (p: Photo) => {
    if (requireLogin()) return;
    try {
      await api(`/api/wishlist/from-photo/${p.id}`, { method: "POST" });
      toast({ title: `Saved ${p.place_name} to your wishlist` });
    } catch (e) {
      toast({ title: "Could not save", description: (e as Error).message, variant: "destructive" });
    }
  };

  const proposeAdd = async () => {
    if (!addTarget || !addTrip) return;
    try {
      const r = await api<{ fits: boolean; message: string; ops?: any[]; version?: number }>(
        `/api/photos/${addTarget.id}/add-to-itinerary`, { method: "POST", json: { trip_id: Number(addTrip) } });
      if (!r.fits) {
        toast({ title: "Not added", description: r.message });
      } else {
        setProposal({ tripId: addTrip, p: { ops: r.ops!, notes: [r.message], version: r.version! } });
      }
      setAddTarget(null);
    } catch (e) {
      toast({ title: "Could not check this place", description: (e as Error).message, variant: "destructive" });
    }
  };

  return (
    <>
    <PageHero title="Live photo feed" clip="earn" icon={<Camera className="w-6 h-6" />} subtitle="See what travelers are discovering right now.">
      <Button variant="secondary" onClick={() => !requireLogin() && setUploadOpen(true)}><Camera className="w-4 h-4 mr-2" />Share a photo</Button>
    </PageHero>
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); setPhotos(null); load(); }}>
        <Input className="w-48" placeholder="City (e.g. Goa)" value={city} onChange={(e) => setCity(e.target.value)} />
        <Input className="w-48" placeholder="#hashtag" value={hashtag} onChange={(e) => setHashtag(e.target.value)} />
        <Button type="submit" variant="outline">Filter</Button>
        {isAuthenticated && <Button variant="ghost" asChild><Link to="/gallery">My gallery</Link></Button>}
      </form>

      {photos === null && <RefreshCw className="w-6 h-6 animate-spin text-primary" />}
      {photos?.length === 0 && <p className="text-muted-foreground">No photos yet{city ? ` for ${city}` : ""}. Be the first to share one!</p>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {photos?.map((p) => (
          <Card key={p.id} className="overflow-hidden group">
            <button className="block w-full overflow-hidden" onClick={() => openPhoto(p)}>
              <img src={p.url} alt={p.caption || p.place_name || "Travel photo"} loading="lazy"
                   className="w-full h-60 object-cover group-hover:scale-105 transition-transform duration-500" />
            </button>
            <CardContent className="pt-3 space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">{p.user.name}</span>
                <span className="text-xs text-muted-foreground">{new Date(p.created_at).toLocaleDateString()}</span>
              </div>
              {(p.place_name || p.city) && (
                <p className="flex items-center text-muted-foreground"><MapPin className="w-3 h-3 mr-1" />{[p.place_name, p.city].filter(Boolean).join(", ")}</p>
              )}
              {p.caption && <p>{p.caption}</p>}
              {p.hashtags.length > 0 && <p className="text-primary text-xs">{p.hashtags.map((h) => `#${h}`).join(" ")}</p>}
              <div className="flex items-center gap-1">
                <Button size="sm" variant="ghost" onClick={() => like(p)} aria-label="Like">
                  <Heart className={`w-4 h-4 mr-1 ${p.liked_by_me ? "fill-red-500 text-red-500" : ""}`} />{p.likes}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => openPhoto(p)} aria-label="Comments"><MessageCircle className="w-4 h-4 mr-1" />{p.comments}</Button>
                <Button size="sm" variant="ghost" onClick={() => save(p)} aria-label="Save photo">
                  <Bookmark className={`w-4 h-4 ${p.saved_by_me ? "fill-current" : ""}`} />
                </Button>
                {p.place_name && (
                  <>
                    <Button size="sm" variant="ghost" onClick={() => savePlace(p)}>Save place</Button>
                    <Button size="sm" variant="outline" onClick={() => !requireLogin() && setAddTarget(p)}><Plus className="w-4 h-4 mr-1" />My trip</Button>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <UploadDialog open={uploadOpen} onClose={() => setUploadOpen(false)} trips={trips}
                    initialTrip={params.get("trip") ?? ""} initialItem={params.get("item") ?? ""}
                    onUploaded={(p, awards) => {
                      setPhotos((list) => [p, ...(list ?? [])]);
                      toast({ title: "Photo shared", description: awards.length ? describeAwards(awards) : undefined });
                    }} />

      <Dialog open={!!open} onOpenChange={(o) => !o && setOpen(null)}>
        <DialogContent className="max-w-2xl">
          {open && (
            <>
              <DialogHeader>
                <DialogTitle>{open.place_name || "Travel photo"}</DialogTitle>
                <DialogDescription>
                  by {open.user.name}{open.city ? ` · ${open.city}` : ""}{open.activity ? ` · during "${open.activity}"` : ""}
                  {open.lat !== null && !open.location_precise && " · approximate location"}
                </DialogDescription>
              </DialogHeader>
              <img src={open.url} alt={open.caption || "Travel photo"} className="w-full max-h-96 object-contain rounded" />
              {open.caption && <p className="text-sm">{open.caption}</p>}
              <div className="space-y-2 max-h-40 overflow-y-auto text-sm">
                {open.comment_list?.map((c) => <p key={c.id}><span className="font-medium">{c.user.name}</span> {c.text}</p>)}
                {open.comment_list?.length === 0 && <p className="text-muted-foreground">No comments yet.</p>}
              </div>
              <form onSubmit={sendComment} className="flex gap-2">
                <Input value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Add a comment" maxLength={1000} />
                <Button type="submit">Post</Button>
              </form>
              {open.mine && (
                <Button variant="ghost" className="text-red-600" onClick={async () => {
                  await api(`/api/photos/${open.id}`, { method: "DELETE" });
                  setPhotos((list) => list?.filter((x) => x.id !== open.id) ?? null);
                  setOpen(null);
                }}>Delete my photo</Button>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={!!addTarget} onOpenChange={(o) => !o && setAddTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add {addTarget?.place_name} to a trip</DialogTitle>
            <DialogDescription>We will check it fits your schedule before anything changes.</DialogDescription>
          </DialogHeader>
          {trips.length === 0 ? <p className="text-sm">You have no trips yet. <Link className="text-primary underline" to="/trips">Plan one</Link>.</p> : (
            <Select value={addTrip} onValueChange={setAddTrip}>
              <SelectTrigger><SelectValue placeholder="Choose a trip" /></SelectTrigger>
              <SelectContent>{trips.map((t) => <SelectItem key={t.id} value={String(t.id)}>{t.destination} · {t.start_date}</SelectItem>)}</SelectContent>
            </Select>
          )}
          <DialogFooter><Button onClick={proposeAdd} disabled={!addTrip}>Check fit</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <ProposalDialog tripId={proposal?.tripId ?? ""} proposal={proposal?.p ?? null} title="Add to your itinerary"
                      onClose={() => setProposal(null)} onApplied={(t: Trip) => navigate(`/trips/${t.id}`)} />
    </div>
    </>
  );
}

interface UploadProps {
  open: boolean;
  onClose: () => void;
  trips: TripSummary[];
  initialTrip: string;
  initialItem: string;
  onUploaded: (p: Photo, awards: Award[]) => void;
}

function UploadDialog({ open, onClose, trips, initialTrip, initialItem, onUploaded }: UploadProps) {
  const { toast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [caption, setCaption] = useState("");
  const [hashtags, setHashtags] = useState("");
  const [place, setPlace] = useState("");
  const [city, setCity] = useState("");
  const [tripId, setTripId] = useState(initialTrip);
  const [itemId, setItemId] = useState(initialItem);
  const [stops, setStops] = useState<{ id: number; name: string }[]>([]);
  const [shareLocation, setShareLocation] = useState(false);
  const [visibility, setVisibility] = useState("public");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!tripId) { setStops([]); return; }
    api<Trip>(`/api/itinerary/${tripId}`).then((t) => {
      setCity(t.destination);
      setStops(t.days.flatMap((d) => d.time_slots.filter((s) => s.kind === "visit").map((s) => ({ id: s.item_id, name: `Day ${d.day}: ${s.activity.name}` }))));
    }).catch(() => setStops([]));
  }, [tripId]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setSending(true);
    try {
      const form = new FormData();
      form.append("file", file);
      Object.entries({ caption, hashtags, place_name: place, city, visibility }).forEach(([k, v]) => form.append(k, v));
      if (tripId) form.append("trip_id", tripId);
      if (itemId) form.append("item_id", itemId);
      if (shareLocation) {
        form.append("share_location", "true");
        const pos = await currentPosition();
        if (pos) { form.append("lat", String(pos.lat)); form.append("lng", String(pos.lng)); }
      }
      const res = await api<{ photo: Photo; awards: Award[] }>("/api/photos", { method: "POST", body: form });
      onUploaded(res.photo, res.awards);
      setFile(null); setCaption(""); setHashtags(""); setPlace("");
      onClose();
    } catch (err) {
      toast({ title: "Upload failed", description: (err as Error).message, variant: "destructive" });
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Share a travel photo</DialogTitle>
          <DialogDescription>Public photos tagged with a place earn points and help others discover it.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          <Input type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={(e) => setFile(e.target.files?.[0] ?? null)} required />
          {trips.length > 0 && (
            <div className="grid grid-cols-2 gap-2">
              <Select value={tripId || "none"} onValueChange={(v) => { setTripId(v === "none" ? "" : v); setItemId(""); }}>
                <SelectTrigger><SelectValue placeholder="Trip" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No trip</SelectItem>
                  {trips.map((t) => <SelectItem key={t.id} value={String(t.id)}>{t.destination}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={itemId || "none"} onValueChange={(v) => setItemId(v === "none" ? "" : v)} disabled={!stops.length}>
                <SelectTrigger><SelectValue placeholder="Itinerary stop" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No stop</SelectItem>
                  {stops.map((s) => <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          )}
          {!itemId && (
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder="Place (e.g. Hawa Mahal)" value={place} onChange={(e) => setPlace(e.target.value)} maxLength={200} />
              <Input placeholder="City" value={city} onChange={(e) => setCity(e.target.value)} maxLength={120} />
            </div>
          )}
          <Textarea placeholder="Caption" value={caption} onChange={(e) => setCaption(e.target.value)} maxLength={1000} />
          <Input placeholder="#hashtags" value={hashtags} onChange={(e) => setHashtags(e.target.value)} maxLength={300} />
          <div className="flex items-center justify-between gap-2">
            <Label htmlFor="loc" className="text-sm">Attach my precise location<span className="block text-xs text-muted-foreground">Others only ever see an approximate area.</span></Label>
            <Switch id="loc" checked={shareLocation} onCheckedChange={setShareLocation} />
          </div>
          <Select value={visibility} onValueChange={setVisibility}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="public">Public</SelectItem>
              <SelectItem value="group" disabled={!tripId}>Trip group only</SelectItem>
              <SelectItem value="private">Only me</SelectItem>
            </SelectContent>
          </Select>
          <DialogFooter><Button type="submit" disabled={!file || sending}>{sending ? "Uploading..." : "Share"}</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
