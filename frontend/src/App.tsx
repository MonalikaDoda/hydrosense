import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Gauge,
  MapPin,
  RefreshCw,
  Waves,
} from "lucide-react";

import {
  getDashboardSummary,
  getIncidents,
  getLatestReadings,
  updateIncidentStatus,
} from "./api/client";
import type {
  DashboardSummary,
  Incident,
  IncidentStatus,
  SensorReading,
} from "./types/api";
import "./styles.css";

const statusTransitions: Record<IncidentStatus, IncidentStatus[]> = {
  open: ["assigned", "verified", "dismissed"],
  assigned: ["verified", "resolved", "dismissed"],
  verified: ["resolved", "dismissed"],
  resolved: [],
  dismissed: [],
};

function formatTime(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function sourceLabel(source: SensorReading["source"] | Incident["source"]) {
  return source === "simulated_sensor" ? "SIMULATED" : source.toUpperCase();
}

export default function App() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [readings, setReadings] = useState<SensorReading[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    Promise.all([
      getDashboardSummary(controller.signal),
      getLatestReadings(controller.signal),
      getIncidents(controller.signal),
    ])
      .then(([nextSummary, nextReadings, nextIncidents]) => {
        setSummary(nextSummary);
        setReadings(nextReadings);
        setIncidents(nextIncidents);
        setSelectedId((current) => current ?? nextIncidents[0]?.incident_id ?? null);
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof Error && requestError.name !== "AbortError") {
          setError(requestError.message);
        }
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [reloadKey]);

  const selectedIncident =
    incidents.find((incident) => incident.incident_id === selectedId) ?? null;

  async function changeStatus(status: IncidentStatus) {
    if (!selectedIncident || status === selectedIncident.status) return;
    setUpdating(true);
    setError(null);
    try {
      const updated = await updateIncidentStatus(selectedIncident.incident_id, status);
      setIncidents((current) =>
        current.map((incident) =>
          incident.incident_id === updated.incident_id ? updated : incident,
        ),
      );
      setReloadKey((value) => value + 1);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Update failed");
    } finally {
      setUpdating(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark"><Waves size={20} /></span>
          <div><strong>HydroSense</strong><span>Delhi operations preview</span></div>
        </div>
        <div className="header-actions">
          <span className="demo-badge">DEMO SCENARIO</span>
          <button className="icon-button" onClick={() => setReloadKey((value) => value + 1)} title="Refresh dashboard" aria-label="Refresh dashboard"><RefreshCw size={18} /></button>
        </div>
      </header>

      <section className="page-heading">
        <div>
          <p className="eyebrow">Water response desk</p>
          <h1>Prototype water-level monitor</h1>
          <p>Simulator readings and incidents for a clearly labelled central Delhi demo location.</p>
        </div>
        <span className="location-label"><MapPin size={16} /> Demo Zone 01 · Delhi</span>
      </section>

      {error && <div className="error-banner" role="alert"><AlertTriangle size={18} /> {error}. Confirm the backend is running, then refresh.</div>}
      {loading && <div className="loading-state" aria-live="polite"><RefreshCw className="spin" size={20} /> Loading live demo data...</div>}

      {!loading && (
        <>
          <section className="summary-grid" aria-label="Risk summary">
            <article className="summary-card"><span><AlertTriangle size={18} /> Open incidents</span><strong>{summary?.open_incidents ?? 0}</strong><small>Awaiting operator action</small></article>
            <article className="summary-card"><span><Gauge size={18} /> High priority</span><strong>{summary?.high_priority_incidents ?? 0}</strong><small>Prototype threshold based</small></article>
            <article className="summary-card"><span><Waves size={18} /> Latest depth</span><strong>{readings[0] ? `${readings[0].water_depth_cm.toFixed(1)} cm` : "--"}</strong><small>Alert threshold · 24.0 cm</small></article>
            <article className="summary-card"><span><Clock3 size={18} /> Last signal</span><strong className="time-value">{readings[0] ? formatTime(readings[0].timestamp) : "No signal"}</strong><small>AWS cloud persistence</small></article>
          </section>

          <section className="workspace-grid">
            <div className="panel readings-panel">
              <div className="panel-heading"><div><p className="eyebrow">Sensor stream</p><h2>Latest readings</h2></div><span>{readings.length} records</span></div>
              {readings.length === 0 ? <div className="empty-state"><Waves size={28} /><h3>No readings yet</h3><p>Run the simulator to populate this stream.</p></div> : (
                <div className="reading-list">
                  {readings.map((reading) => (
                    <article className="reading-row" key={`${reading.device_id}-${reading.timestamp}`}>
                      <span className={reading.water_depth_cm >= 24 ? "depth-indicator alert" : "depth-indicator"} />
                      <div><strong>{reading.water_depth_cm.toFixed(1)} cm</strong><small>{reading.location_id} · {formatTime(reading.timestamp)}</small></div>
                      <span className="source-tag">{sourceLabel(reading.source)}</span>
                    </article>
                  ))}
                </div>
              )}
            </div>

            <div className="panel incidents-panel">
              <div className="panel-heading"><div><p className="eyebrow">Response queue</p><h2>Incidents</h2></div><span>{incidents.length} total</span></div>
              {incidents.length === 0 ? <div className="empty-state"><CheckCircle2 size={28} /><h3>No active incidents</h3><p>Readings above the demo threshold appear here.</p></div> : (
                <div className="incident-list">
                  {incidents.map((incident) => (
                    <button className={incident.incident_id === selectedId ? "incident-row selected" : "incident-row"} key={incident.incident_id} onClick={() => setSelectedId(incident.incident_id)}>
                      <span className={`severity-dot ${incident.severity}`} />
                      <span><strong>{incident.title}</strong><small>{incident.location_id} · {incident.status}</small></span>
                      <span className="source-tag">{sourceLabel(incident.source)}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <aside className="panel detail-panel">
              <div className="panel-heading"><div><p className="eyebrow">Evidence review</p><h2>Incident detail</h2></div></div>
              {!selectedIncident ? <div className="empty-state"><h3>Select an incident</h3><p>Evidence and controls will appear here.</p></div> : (
                <div className="incident-detail">
                  <div className="detail-status"><span className={`severity-pill ${selectedIncident.severity}`}>{selectedIncident.severity}</span><span className="source-tag">{sourceLabel(selectedIncident.source)}</span></div>
                  <h3>{selectedIncident.title}</h3>
                  <p><MapPin size={15} /> {selectedIncident.location_id} · DEMO LOCATION</p>
                  <dl>
                    <div><dt>Water depth</dt><dd>{String(selectedIncident.evidence.water_depth_cm)} cm</dd></div>
                    <div><dt>Threshold</dt><dd>{String(selectedIncident.evidence.threshold_cm)} cm</dd></div>
                    <div><dt>Confidence</dt><dd>{Math.round(selectedIncident.confidence * 100)}%</dd></div>
                    <div><dt>Created</dt><dd>{formatTime(selectedIncident.created_at)}</dd></div>
                  </dl>
                  <label htmlFor="incident-status">Incident status</label>
                  <select id="incident-status" value={selectedIncident.status} disabled={updating || ["resolved", "dismissed"].includes(selectedIncident.status)} onChange={(event) => void changeStatus(event.target.value as IncidentStatus)}>
                    <option value={selectedIncident.status}>{selectedIncident.status}</option>
                    {statusTransitions[selectedIncident.status].map((status) => <option key={status} value={status}>{status}</option>)}
                  </select>
                  <small>Only valid lifecycle transitions are accepted by the API.</small>
                </div>
              )}
            </aside>
          </section>
        </>
      )}
    </main>
  );
}
