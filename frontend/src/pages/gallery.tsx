import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Lock, Globe, Users, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api, Photo } from "@/lib/livetrip";
import PageHero from "@/components/PageHero";

interface Album { key: string; title: string; trip_id: number | null; photos: Photo[] }

const ICON = { public: Globe, group: Users, private: Lock } as const;

export default function Gallery() {
  const [albums, setAlbums] = useState<Album[] | null>(null);

  useEffect(() => {
    api<{ albums: Album[] }>("/api/gallery/me").then((r) => setAlbums(r.albums)).catch(() => setAlbums([]));
  }, []);

  return (
    <>
    <PageHero title="My travel gallery" clip="sights" icon={<Globe className="w-6 h-6" />} subtitle="Your photos, sorted into trip albums automatically.">
      <Button asChild variant="secondary"><Link to="/feed">Share a photo</Link></Button>
    </PageHero>
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      {albums === null && <RefreshCw className="w-6 h-6 animate-spin text-primary" />}
      {albums?.length === 0 && <p className="text-muted-foreground">No photos yet.</p>}
      {albums?.map((a) => (
        <Card key={a.key}>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center justify-between text-xl">
              {a.title}
              {a.trip_id && <Link to={`/trips/${a.trip_id}`} className="text-sm font-normal text-primary underline">View itinerary</Link>}
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
            {a.photos.map((p) => {
              const Icon = ICON[p.visibility as keyof typeof ICON] ?? Globe;
              return (
                <figure key={p.id} className="relative">
                  <img src={p.url} alt={p.caption || p.place_name || "Travel photo"} className="w-full h-40 object-cover rounded" loading="lazy" />
                  <span className="absolute top-1 right-1 bg-black/60 text-white rounded p-1" title={p.visibility}><Icon className="w-3 h-3" /></span>
                  <figcaption className="text-xs mt-1 truncate">{p.place_name || p.caption || new Date(p.created_at).toLocaleDateString()}</figcaption>
                </figure>
              );
            })}
          </CardContent>
        </Card>
      ))}
    </div>
    </>
  );
}
