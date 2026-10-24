import { useEffect } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Destination } from "@shared/schema";

const COLORS: Record<string, string> = { attraction: "#2563eb", city: "#16a34a", hotel: "#9333ea", restaurant: "#ea580c" };

function pin(category: string, selected: boolean) {
  const color = COLORS[category] || "#0f766e";
  const s = selected ? 44 : 34;
  return L.divIcon({
    className: "",
    iconSize: [s, s],
    iconAnchor: [s / 2, s],
    popupAnchor: [0, -s],
    html: `<svg viewBox="0 0 24 24" width="${s}" height="${s}" style="filter:drop-shadow(0 3px 4px rgba(0,0,0,.35))">
      <path d="M12 23s-8-7.2-8-13a8 8 0 1 1 16 0c0 5.8-8 13-8 13z" fill="${color}" stroke="#fff" stroke-width="1.6"/>
      <circle cx="12" cy="10" r="3.2" fill="#fff"/></svg>`,
  });
}

/** Fits all destinations in view, and flies to the selected one. */
function Fit({ points, focus }: { points: [number, number][]; focus: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 1) map.setView(points[0], 12);
    else if (points.length > 1) map.fitBounds(L.latLngBounds(points), { padding: [40, 40] });
  }, [JSON.stringify(points)]);
  useEffect(() => {
    if (focus) map.flyTo(focus, 13, { duration: 1.2 });
  }, [focus?.[0], focus?.[1]]);
  return null;
}

interface Props {
  destinations: Destination[];
  selectedId?: string | null;
  onSelect?: (d: Destination) => void;
  onPlan?: (d: Destination) => void;
  className?: string;
}

/** A real (OpenStreetMap) map of destinations: coloured pins by category, popups, fly-to on select. */
export default function DestinationsMap({ destinations, selectedId, onSelect, onPlan, className = "h-96" }: Props) {
  const placed = destinations.filter((d) => d.lat != null && d.lng != null);
  const points = placed.map((d) => [Number(d.lat), Number(d.lng)] as [number, number]);
  const selected = placed.find((d) => d.id === selectedId);

  return (
    <div className={`relative rounded-2xl overflow-hidden border shadow-lg ${className}`}>
      <MapContainer center={[22.5, 79]} zoom={4} scrollWheelZoom className="h-full w-full z-0">
        <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                   url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <Fit points={points} focus={selected ? [Number(selected.lat), Number(selected.lng)] : null} />
        {placed.map((d) => (
          <Marker key={d.id} position={[Number(d.lat), Number(d.lng)]} icon={pin(d.category, d.id === selectedId)}
                  eventHandlers={{ click: () => onSelect?.(d) }}>
            <Popup>
              <p className="font-semibold text-sm" translate="no">{d.name}</p>
              <p className="text-xs text-gray-500">{d.location}, {d.country}</p>
              {d.shortDescription && <p className="text-xs mt-1">{d.shortDescription}</p>}
              {onPlan && (
                <button type="button" onClick={() => onPlan(d)}
                        className="mt-2 text-xs font-semibold text-white bg-brand-700 hover:bg-brand-800 rounded-full px-3 py-1">
                  Plan a trip here
                </button>
              )}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      <div className="absolute bottom-3 left-3 z-[400] bg-white/90 backdrop-blur rounded-xl shadow px-3 py-2 text-xs space-y-1">
        {Object.entries(COLORS).filter(([c]) => placed.some((d) => d.category === c)).map(([c, color]) => (
          <p key={c} className="flex items-center gap-2 capitalize text-gray-700">
            <span className="w-3 h-3 rounded-full" style={{ background: color }} />{c}
          </p>
        ))}
      </div>
    </div>
  );
}
