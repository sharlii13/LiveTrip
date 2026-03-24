import { useEffect, useMemo, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Minimal Leaflet icon fix for default marker assets (not required if using emoji divIcons)
// We'll use divIcon with emojis, so no image assets are needed

function categoryToEmoji(category) {
  const c = (category || '').toLowerCase();
  if (c.includes('temple')) return '🛕';
  if (c.includes('park') || c.includes('nature')) return '🌳';
  if (c.includes('museum') || c.includes('fort') || c.includes('historic')) return '🏰';
  if (c.includes('restaurant') || c.includes('food')) return '🍴';
  return '📍';
}

function categoryToColor(category) {
  const c = (category || '').toLowerCase();
  if (c.includes('temple')) return '#8b5cf6'; // purple
  if (c.includes('park') || c.includes('nature')) return '#10b981'; // green
  if (c.includes('museum') || c.includes('fort') || c.includes('historic')) return '#3b82f6'; // blue
  if (c.includes('restaurant') || c.includes('food')) return '#f59e0b'; // amber
  return '#ef4444'; // red
}

function createEmojiIcon(category) {
  const emoji = categoryToEmoji(category);
  const color = categoryToColor(category);
  return L.divIcon({
    className: 'itinerary-emoji-marker',
    html: `<div style="font-size:22px; line-height:22px; filter: drop-shadow(0 1px 1px rgba(0,0,0,0.3))">${emoji}</div>` ,
    iconSize: [22, 22],
    iconAnchor: [11, 22],
    popupAnchor: [0, -18]
  });
}

function FitBounds({ points }) {
  const map = useMap();
  useEffect(() => {
    if (!points || points.length === 0) return;
    const bounds = L.latLngBounds(points.map(p => [p.lat, p.lng]));
    map.fitBounds(bounds, { padding: [30, 30] });
  }, [points, map]);
  return null;
}

export default function ItineraryMap({ daySchedule, dayNumber }) {
  const items = Array.isArray(daySchedule) ? daySchedule.filter(it => typeof it.lat === 'number' && typeof it.lng === 'number') : [];

  if (items.length === 0) {
    return (
      <div className="bg-white rounded-2xl shadow-lg p-6 h-[400px] flex items-center justify-center">
        <div className="text-center text-gray-600">
          <div className="text-xl font-semibold mb-1">No locations available for Day {dayNumber}</div>
          <div className="text-sm">Add POIs with coordinates to view them on the map.</div>
        </div>
      </div>
    );
  }

  const center = useMemo(() => {
    const lat = items.reduce((s, it) => s + it.lat, 0) / items.length;
    const lng = items.reduce((s, it) => s + it.lng, 0) / items.length;
    return [lat, lng];
  }, [items]);

  const pathPositions = items.map(it => [it.lat, it.lng]);
  const pathColor = ['#0ea5e9','#f97316','#10b981','#8b5cf6','#ef4444'][((dayNumber || 1) - 1) % 5];

  return (
    <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
      <MapContainer center={center} zoom={13} className="h-[400px] w-full" scrollWheelZoom={true}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
        />

        <FitBounds points={items} />

        {items.map((it, idx) => (
          <Marker key={`${it.lat}-${it.lng}-${idx}`} position={[it.lat, it.lng]} icon={createEmojiIcon(it.category)}>
            <Popup>
              <div className="space-y-1">
                <div className="font-semibold text-gray-900">{it.poi || it.name || 'POI'}</div>
                <div className="text-xs text-gray-600 capitalize">{(it.category || '').toString()}</div>
                {(it.start || it.arrive_at) && (
                  <div className="text-xs text-gray-700">{(it.start || it.arrive_at) + ' → ' + (it.end || it.depart_at || '')}</div>
                )}
              </div>
            </Popup>
          </Marker>
        ))}

        {pathPositions.length > 1 && (
          <Polyline positions={pathPositions} color={pathColor} weight={4} opacity={0.8} />
        )}
      </MapContainer>
    </div>
  );
}



