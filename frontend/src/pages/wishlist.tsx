import { FormEvent, useEffect, useState } from "react";
import { Bookmark, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/livetrip";

interface Wish { id: number; name: string; city: string; source: string; created_at: string }

export default function Wishlist() {
  const { toast } = useToast();
  const [items, setItems] = useState<Wish[]>([]);
  const [name, setName] = useState("");
  const [city, setCity] = useState("");

  const load = () => { api<Wish[]>("/api/wishlist").then(setItems); };
  useEffect(load, []);

  const add = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api("/api/wishlist", { method: "POST", json: { name, city } });
      setName("");
      load();
    } catch (err) {
      toast({ title: "Could not save", description: (err as Error).message, variant: "destructive" });
    }
  };

  const remove = async (w: Wish) => {
    await api(`/api/wishlist/${w.id}`, { method: "DELETE" });
    load();
  };

  const byCity = items.reduce<Record<string, Wish[]>>((acc, w) => {
    (acc[w.city || "Anywhere"] ??= []).push(w);
    return acc;
  }, {});

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Saved places</h1>
        <p className="text-muted-foreground">Places you save here are suggested automatically when you plan a trip to that city.</p>
      </div>
      <form onSubmit={add} className="flex flex-wrap gap-2">
        <Input className="flex-1 min-w-48" placeholder="Place (e.g. Jal Mahal)" value={name} onChange={(e) => setName(e.target.value)} required />
        <Input className="w-40" placeholder="City" value={city} onChange={(e) => setCity(e.target.value)} />
        <Button type="submit"><Bookmark className="w-4 h-4 mr-1" />Save</Button>
      </form>
      {items.length === 0 && <p className="text-muted-foreground">Nothing saved yet. Save places from the photo feed or add them above.</p>}
      {Object.entries(byCity).map(([c, list]) => (
        <Card key={c}>
          <CardHeader className="pb-2"><CardTitle className="text-lg">{c}</CardTitle></CardHeader>
          <CardContent className="divide-y">
            {list.map((w) => (
              <div key={w.id} className="flex items-center justify-between py-2">
                <span>{w.name} <Badge variant="secondary" className="ml-2 capitalize">{w.source}</Badge></span>
                <Button size="sm" variant="ghost" onClick={() => remove(w)} aria-label={`Remove ${w.name}`}><Trash2 className="w-4 h-4" /></Button>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
