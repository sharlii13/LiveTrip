import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

type HealthResponse = {
  status: string;
  timestamp: string;
  components?: Record<string, any>;
  version?: string;
};

export default function HealthPanel() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let aborted = false;
    async function run() {
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/api/itinerary/health`);
        if (!res.ok) throw new Error(`Health failed: ${res.status}`);
        const json = (await res.json()) as HealthResponse;
        if (!aborted) setHealth(json);
      } catch (e: any) {
        if (!aborted) setError(e?.message || "Failed to fetch health");
      }
    }
    run();
    return () => { aborted = true; };
  }, []);

  const clearLocal = () => {
    try {
      localStorage.clear();
      alert("localStorage cleared.");
    } catch (e) {
      alert("Failed to clear localStorage: " + (e as any)?.message);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "2rem auto", padding: "1rem", border: "1px solid #ddd", borderRadius: 8 }}>
      <h2 style={{ marginBottom: 8 }}>Live Health Panel</h2>
      <div style={{ marginBottom: 12 }}>
        <strong>API Base:</strong> <code>{API_BASE}</code>
      </div>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button onClick={() => window.location.reload()} style={{ padding: "6px 10px" }}>Refresh</button>
        <button onClick={clearLocal} style={{ padding: "6px 10px" }}>Clear localStorage</button>
      </div>
      {error && (
        <div style={{ color: "#b00020", marginBottom: 12 }}>Error: {error}</div>
      )}
      {health ? (
        <div>
          <div><strong>Status:</strong> {health.status}</div>
          <div><strong>Version:</strong> {health.version || "-"}</div>
          <div><strong>Timestamp:</strong> {health.timestamp}</div>
          <div style={{ marginTop: 12 }}>
            <strong>Components:</strong>
            <pre style={{ background: "#f7f7f7", padding: 12, borderRadius: 6, overflow: "auto" }}>
              {JSON.stringify(health.components ?? {}, null, 2)}
            </pre>
          </div>
        </div>
      ) : !error ? (
        <div>Loading...</div>
      ) : null}

      <div style={{ marginTop: 16, fontSize: 14, color: "#555" }}>
        Tips:
        <ul>
          <li>Ensure VITE_API_BASE is set to http://127.0.0.1:8000 and restart the dev server.</li>
          <li>Use this page to verify the backend health without leaving the app.</li>
        </ul>
      </div>
    </div>
  );
}