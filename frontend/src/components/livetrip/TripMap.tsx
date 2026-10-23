import { useEffect, useMemo } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Slot } from "@/lib/livetrip";

interface Props {
  slots: Slot[];
  selectedId: number | null;
  onSelect: (itemId: number) => void;
  start?: { lat: number; lng: number };
}

function markerIcon(label: string, slot: Slot, selected: boolean) {
  const color = slot.status === "completed" ? "#16a34a" : slot.status === "skipped" ? "#9ca3af"
    : slot.kind === "meal" ? "#ea580c" : "#0f766e";
  const size = selected ? 38 : 30;
  return L.divIcon({
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<div style="width:${size}px;height:${size}px;border-radius:9999px;background:${color};color:#fff;
      display:flex;align-items:center;justify-content:center;font:600 ${selected ? 15 : 13}px system-ui,sans-serif;
      border:3px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.35);${selected ? "outline:3px solid #facc15;" : ""}">${label}</div>`,
  });
}

/** Keeps the whole day in view, and pans to the selected stop. */
function Fit({ points, focus }: { points: [number, number][]; focus: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 1) map.setView(points[0], 14);
    else if (points.length > 1) map.fitBounds(L.latLngBounds(points), { padding: [40, 40] });
  }, [JSON.stringify(points)]);
  useEffect(() => {
    if (focus) map.panTo(focus, { animate: true });
  }, [focus?.[0], focus?.[1]]);
  return null;
}

/** Live OpenStreetMap map of one day's stops, numbered in visiting order, with the route between them. */
export default function TripMap({ slots, selectedId, onSelect, start }: Props) {
  const located = useMemo(
    () => slots.filter((s) => s.activity.location.latitude != null && s.activity.location.longitude != null),
    [slots],
  );
  const points = located.map((s) => [s.activity.location.latitude, s.activity.location.longitude] as [number, number]);
  const route = located.filter((s) => s.status !== "skipped")
    .map((s) => [s.activity.location.latitude, s.activity.location.longitude] as [number, number]);
  const selected = located.find((s) => s.item_id === selectedId);
  const visitNumber = new Map(slots.filter((s) => s.kind === "visit").map((s, i) => [s.item_id, i + 1]));
  const center: [number, number] = points[0] ?? (start ? [start.lat, start.lng] : [20.59, 78.96]);

  return (
    <MapContainer center={center} zoom={12} scrollWheelZoom className="h-full w-full rounded-lg z-0">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Fit points={points} focus={selected ? [selected.activity.location.latitude, selected.activity.location.longitude] : null} />
      {route.length > 1 && <Polyline positions={route} pathOptions={{ color: "#0f766e", weight: 3, opacity: 0.7, dashArray: "6 6" }} />}
      {located.map((s) => (
        <Marker
          key={s.item_id}
          position={[s.activity.location.latitude, s.activity.location.longitude]}
          icon={markerIcon(s.kind === "meal" ? "🍽" : String(visitNumber.get(s.item_id)), s, s.item_id === selectedId)}
          zIndexOffset={s.item_id === selectedId ? 1000 : 0}
          eventHandlers={{ click: () => onSelect(s.item_id) }}
        >
          <Popup>
            <strong translate="no">{s.activity.name}</strong><br />
            {s.start_time}–{s.end_time}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
