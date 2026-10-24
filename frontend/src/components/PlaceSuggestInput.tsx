import { InputHTMLAttributes, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { MapPin } from "lucide-react";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/livetrip";

interface Suggestion { name: string; detail: string }

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange"> {
  value: string;
  onValueChange: (value: string) => void;
  onPick?: (place: string) => void;  // a suggestion was chosen (click or Enter on a highlighted one)
  onSubmit?: () => void;             // Enter with nothing highlighted
}

/** A destination box that suggests places as you type ("pu" -> Pune, Puri, Puducherry...). */
export default function PlaceSuggestInput({ value, onValueChange, onPick, onSubmit, className, ...rest }: Props) {
  const [items, setItems] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const listId = useId();
  const typed = useRef(false);  // only suggest for what the traveller typed, not for a value set by picking
  const box = useRef<HTMLDivElement>(null);
  const [rect, setRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    const q = value.trim();
    if (!typed.current || q.length < 2) { setItems([]); return; }
    let alive = true;
    const t = window.setTimeout(() => {
      api<{ suggestions: Suggestion[] }>(`/api/places/suggest?q=${encodeURIComponent(q)}`)
        .then((r) => { if (alive) { setItems(r.suggestions); setActive(-1); setOpen(true); } })
        .catch(() => alive && setItems([]));
    }, 200);
    return () => { alive = false; window.clearTimeout(t); };
  }, [value]);

  const pick = (s: Suggestion) => {
    typed.current = false;
    onValueChange(s.name);
    setOpen(false);
    onPick?.(s.name);
  };
  const shown = open && items.length > 0;

  // the list lives at the top of the page (fixed under the box) so a parent with overflow hidden can't clip it
  useLayoutEffect(() => {
    if (!shown) return;
    const place = () => box.current && setRect(box.current.getBoundingClientRect());
    place();
    window.addEventListener("scroll", place, true);
    window.addEventListener("resize", place);
    return () => { window.removeEventListener("scroll", place, true); window.removeEventListener("resize", place); };
  }, [shown]);

  return (
    <div ref={box} className="relative flex-1">
      <Input {...rest} value={value} className={className} autoComplete="off" role="combobox"
             aria-expanded={shown} aria-controls={listId} aria-autocomplete="list"
             aria-activedescendant={shown && active >= 0 ? `${listId}-${active}` : undefined}
             onChange={(e) => { typed.current = true; onValueChange(e.target.value); }}
             onFocus={() => items.length && setOpen(true)}
             onBlur={() => window.setTimeout(() => setOpen(false), 150)}  // lets a click on a suggestion land first
             onKeyDown={(e) => {
               if (e.key === "ArrowDown" && shown) { e.preventDefault(); setActive((i) => Math.min(items.length - 1, i + 1)); }
               else if (e.key === "ArrowUp" && shown) { e.preventDefault(); setActive((i) => Math.max(-1, i - 1)); }
               else if (e.key === "Escape") setOpen(false);
               else if (e.key === "Enter") {
                 if (shown && active >= 0) { e.preventDefault(); pick(items[active]); }
                 else { setOpen(false); onSubmit?.(); }
               }
             }} />
      {shown && rect && createPortal(
        <ul id={listId} role="listbox" style={{ position: "fixed", left: rect.left, top: rect.bottom + 8, width: rect.width }}
            className="z-[60] max-h-72 overflow-y-auto rounded-2xl border bg-popover text-popover-foreground shadow-xl py-1 text-left">
          {items.map((s, i) => (
            <li key={`${s.name}-${s.detail}`} id={`${listId}-${i}`} role="option" aria-selected={i === active}
                onMouseDown={(e) => { e.preventDefault(); pick(s); }} onMouseEnter={() => setActive(i)}
                className={`flex items-center gap-3 px-4 py-2 cursor-pointer ${i === active ? "bg-accent" : ""}`}>
              <MapPin className="w-4 h-4 shrink-0 text-brand-700" />
              <span className="min-w-0">
                <span className="block font-medium truncate" translate="no">{s.name}</span>
                {s.detail && <span className="block text-xs text-muted-foreground truncate">{s.detail}</span>}
              </span>
            </li>
          ))}
        </ul>,
        document.body,
      )}
    </div>
  );
}
