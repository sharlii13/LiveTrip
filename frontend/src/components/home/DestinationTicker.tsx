import { Plane } from "lucide-react";

const PLACES = ["Jaipur", "Goa", "Munnar", "Udaipur", "Hyderabad", "Leh", "Varanasi", "Alleppey", "Rishikesh", "Mumbai",
                "Darjeeling", "Hampi", "Coorg", "Shillong", "Pondicherry", "Mysuru"];

/** An endless strip of destinations; hovering pauses it, clicking one starts planning a trip there. */
export default function DestinationTicker({ onPick }: { onPick: (place: string) => void }) {
  const row = (hidden: boolean) => (
    <div className="flex shrink-0 items-center gap-3 pr-3" aria-hidden={hidden || undefined}>
      {PLACES.map((p) => (
        <button key={p} type="button" tabIndex={hidden ? -1 : 0} onClick={() => onPick(p)} translate="no"
                className="group flex items-center gap-2 rounded-full border border-white/40 bg-white/10 px-5 py-2 text-white font-semibold
                           backdrop-blur hover:bg-white hover:text-brand-700 transition-colors whitespace-nowrap">
          <Plane className="w-4 h-4 group-hover:translate-x-1 transition-transform" />{p}
        </button>
      ))}
    </div>
  );
  return (
    <div className="ticker overflow-hidden py-2 [mask-image:linear-gradient(to_right,transparent,black_8%,black_92%,transparent)]">
      <div className="ticker-track flex w-max">{row(false)}{row(true)}</div>
    </div>
  );
}
